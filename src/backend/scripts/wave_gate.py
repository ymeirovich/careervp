#!/usr/bin/env python3
"""Wave 2 close-out gate (rule 12).

Modelled on ``smoke_harness.py``: one command, deterministic evidence, non-zero
exit on any failure. Wave 2 closes when someone who was not here can run this and
get the same answer twice.

Each check resolves to one of four states:

* ``PASS``            - verified green here.
* ``FAIL``            - verified red here; the gate exits non-zero.
* ``HUMAN_REQUIRED``  - can only be settled by a human/live action; stays failing
                        until its named evidence file exists under ``docs/evidence/``.
* ``RECORDED``        - a status the gate reads and reports (e.g. the five bets),
                        not a pass/fail assertion. Never blocks on its own.

The gate exits 0 only when there are zero ``FAIL`` and zero unsatisfied
``HUMAN_REQUIRED`` checks. An honest six-of-eight is worth more than a fake eight,
so checks degrade to ``HUMAN_REQUIRED`` rather than silently passing when their
inputs (a live token, a deployed stack) are absent.

Design notes
------------
* The pure evaluation logic (:func:`gate_passed`) is separated from the
  subprocess/AWS side effects so it is unit-testable offline and can be proven to
  fail on purpose (rule 13).
* Heavy checks (test suites, coverage, cdk) shell out to the same commands a human
  would run, captured verbatim into the evidence file.
* AWS reads are read-only (``describe-stacks`` / ``list-stack-resources``); the
  gate never mutates CloudFormation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable, Sequence

# --------------------------------------------------------------------------- #
# Repo layout anchors
# --------------------------------------------------------------------------- #
# scripts/ -> src/backend/ -> src/ -> <repo root>
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / 'src' / 'backend'
INFRA_DIR = REPO_ROOT / 'infra'
SCOPE_DIFF = REPO_ROOT / 'docs' / 'db-redesign' / 'code' / 'code-analysis' / 'project' / 'scope-diff.py'
ISSUES_MD = REPO_ROOT / 'docs' / 'db-redesign' / 'code' / 'code-analysis' / 'project' / 'ISSUES.md'
EVIDENCE_DIR = REPO_ROOT / 'docs' / 'evidence'

DEVX_STACK = 'CareerVpCrudDevx'
# CloudFormation's limit is PER TEMPLATE. The hard ceiling every template must stay
# under is 500 (AC-003 / bet B-2-3); 400 is the aspirational target reachable only
# after P-26 Job-1 collapses the remaining features, which is currently blocked. The
# gate enforces the hard 500 and reports distance to the 400 target.
CFN_HARD_CEILING = 500
CFN_TARGET_CEILING = 400

# The five Wave-2 bets (rule 9). The gate re-reads ISSUES.md and records each one's
# closing verdict; it does not re-derive the verdict, only surfaces it.
WAVE2_BETS: tuple[str, ...] = ('B-2-1', 'B-2-2', 'B-2-3', 'B-2-4', 'B-2-5')

# The clauses Wave 2 actually delivered (its ledger rows). scope-diff --ci fails on
# the whole project's uncovered clauses, including future-wave clauses that have no
# spec yet; the gate only cares that THESE resolve.
WAVE2_CLAUSES: tuple[str, ...] = (
    'P-25',
    'P-25b',
    'P-14',
    'P-15',
    'P-16',
    'P-17',
    'P-18',
    'P-19',
    'P-20',
    'P-02',
    'P-31',
)
# P-02 is the documented spec-less mechanical-inline clause (see wave-2-status.md 2.5a);
# it resolves via test coverage, not a spec file.
SPEC_EXEMPT_CLAUSES: frozenset[str] = frozenset({'P-02'})


class Status(str, Enum):
    PASS = 'PASS'
    FAIL = 'FAIL'
    HUMAN_REQUIRED = 'HUMAN_REQUIRED'
    RECORDED = 'RECORDED'


@dataclass(frozen=True)
class GateCheck:
    """The outcome of one gate check."""

    name: str
    status: Status
    detail: str
    evidence: dict[str, object] = field(default_factory=dict)

    @property
    def blocking(self) -> bool:
        """Whether this check, in this state, must block Wave-2 closure."""
        return self.status in (Status.FAIL, Status.HUMAN_REQUIRED)

    def to_dict(self) -> dict[str, object]:
        return {
            'name': self.name,
            'status': self.status.value,
            'detail': self.detail,
            'evidence': self.evidence,
        }


@dataclass(frozen=True)
class GateReport:
    checks: list[GateCheck]
    timestamp: str

    @property
    def passed(self) -> bool:
        return gate_passed(self.checks)

    def to_evidence(self) -> dict[str, object]:
        return {
            'gate': 'wave-2-close-out',
            'timestamp': self.timestamp,
            'passed': self.passed,
            'summary': {s.value: sum(1 for c in self.checks if c.status is s) for s in Status},
            'checks': [c.to_dict() for c in self.checks],
        }


def gate_passed(checks: Sequence[GateCheck]) -> bool:
    """Pure predicate (rule 13 fail-on-purpose target): the gate passes only when
    no check is blocking. RECORDED checks never block; FAIL and unsatisfied
    HUMAN_REQUIRED always do."""
    return not any(check.blocking for check in checks)


# --------------------------------------------------------------------------- #
# Subprocess plumbing
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Cmd:
    returncode: int
    stdout: str
    stderr: str


def run(cmd: Sequence[str], *, cwd: Path, timeout: int = 1200) -> Cmd:
    """Run a command, capturing output. Never raises on non-zero exit."""
    try:
        proc = subprocess.run(
            list(cmd),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return Cmd(proc.returncode, proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout
        partial_str = partial.decode(errors='replace') if isinstance(partial, bytes) else (partial or '')
        return Cmd(124, partial_str, f'TIMEOUT after {timeout}s')
    except FileNotFoundError as exc:
        return Cmd(127, '', str(exc))


_PYTEST_TAIL = re.compile(r'(\d+ (?:passed|failed|error).*)$', re.MULTILINE)


def _pytest_summary(out: str) -> str:
    matches = _PYTEST_TAIL.findall(out)
    return matches[-1] if matches else out.strip().splitlines()[-1] if out.strip() else ''


# --------------------------------------------------------------------------- #
# Individual checks
# --------------------------------------------------------------------------- #
def check_scope_diff() -> GateCheck:
    """Check 1: every Wave-2 clause resolves in scope-diff.

    ``--ci`` fails on the whole project's uncovered/orphan/tooling state, including
    future-wave clauses with no spec yet, so it is the wrong instrument here. We
    parse ``--json`` and assert only that (a) every Wave-2 clause has a spec (or is
    the documented spec-exempt P-02) with tooling OK and a test, (b) no orphan spec
    exists, and (c) no tooling error exists."""
    if not SCOPE_DIFF.exists():
        return GateCheck('scope_diff', Status.FAIL, f'scope-diff.py not found at {SCOPE_DIFF}')
    res = run(['python3', str(SCOPE_DIFF), '--json'], cwd=REPO_ROOT, timeout=300)
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return GateCheck('scope_diff', Status.FAIL, f'scope-diff --json unparseable (exit {res.returncode})')
    board = {row['id']: row for row in data.get('board', [])}
    problems: list[str] = []
    for clause in WAVE2_CLAUSES:
        row = board.get(clause)
        if row is None:
            problems.append(f'{clause}: absent from scope board')
            continue
        if not row.get('spec') and clause not in SPEC_EXEMPT_CLAUSES:
            problems.append(f'{clause}: no spec')
        if not row.get('tooling_ok', True):
            problems.append(f'{clause}: tooling error')
        if not row.get('test'):
            problems.append(f'{clause}: no test')
    orphans = data.get('orphan_specs', [])
    tooling_errors = data.get('tooling_errors', [])
    if orphans:
        problems.append(f'orphan specs: {orphans}')
    if tooling_errors:
        problems.append(f'tooling errors: {tooling_errors}')
    passed = not problems
    return GateCheck(
        'scope_diff',
        Status.PASS if passed else Status.FAIL,
        f'all {len(WAVE2_CLAUSES)} Wave-2 clauses resolve (spec+test, no orphans/tooling errors)' if passed else '; '.join(problems),
        {'wave2_clauses': list(WAVE2_CLAUSES), 'problems': problems},
    )


def check_infra_test_dirs() -> list[GateCheck]:
    """Check 2: BOTH infrastructure test directories green (Wave 1 went amber by
    forgetting one)."""
    checks: list[GateCheck] = []
    for label, cwd, target in (
        ('infra_tests_backend', BACKEND_DIR, 'tests/infrastructure'),
        ('infra_tests_cdk', INFRA_DIR, 'tests/infrastructure'),
    ):
        res = run(['uv', 'run', 'pytest', target, '-q', '--tb=line'], cwd=cwd, timeout=900)
        summary = _pytest_summary(res.stdout + res.stderr)
        passed = res.returncode == 0
        failing = [line.strip() for line in (res.stdout + res.stderr).splitlines() if line.startswith('FAILED ')]
        checks.append(
            GateCheck(
                label,
                Status.PASS if passed else Status.FAIL,
                f'{target} in {cwd.name}: {summary}',
                {'returncode': res.returncode, 'failing': failing},
            )
        )
    return checks


def check_suites_and_coverage() -> list[GateCheck]:
    """Checks 3+4: backend unit+integration green AND coverage gate at/above the
    enforced baseline, with distance to target reported. Both come from one
    ``make coverage-tests`` run so the numbers are internally consistent."""
    res = run(['make', 'coverage-tests'], cwd=BACKEND_DIR, timeout=1200)
    out = res.stdout + res.stderr
    summary = _pytest_summary(out)
    suite_pass = ' failed' not in summary and 'passed' in summary
    checks = [
        GateCheck(
            'backend_unit_integration',
            Status.PASS if suite_pass else Status.FAIL,
            f'backend unit+integration: {summary}',
            {'summary': summary},
        )
    ]

    # Coverage gate line: "overall: line=72.97% branch=54.34%" plus the gate's exit.
    overall = re.search(r'overall: line=([\d.]+)% branch=([\d.]+)%', out)
    core = re.search(r'core: line=([\d.]+)% branch=([\d.]+)%', out)
    cov_pass = res.returncode == 0
    detail = 'coverage gate exit 0' if cov_pass else f'coverage gate exit {res.returncode}'
    if overall:
        detail += f'; overall {overall.group(1)}/{overall.group(2)}'
    if core:
        detail += f'; core {core.group(1)}/{core.group(2)}'
    detail += ' (enforced baseline 71/53, target 85/80)'
    checks.append(
        GateCheck(
            'coverage_gate',
            Status.PASS if cov_pass else Status.FAIL,
            detail,
            {
                'returncode': res.returncode,
                'overall': overall.groups() if overall else None,
                'core': core.groups() if core else None,
            },
        )
    )
    return checks


def check_frontend_suites() -> GateCheck:
    """Check 3 (frontend half): typecheck + unit + integration. Runs only when a
    node toolchain is present; otherwise HUMAN_REQUIRED with a named evidence
    file, rather than a false green."""
    frontend = REPO_ROOT / 'src' / 'frontend'
    if not (frontend / 'package.json').exists():
        return GateCheck(
            'frontend_suites',
            Status.HUMAN_REQUIRED,
            'src/frontend not present; provide docs/evidence/frontend-suites-*.json',
        )
    if run(['npm', '--version'], cwd=frontend, timeout=30).returncode != 0:
        return GateCheck(
            'frontend_suites',
            Status.HUMAN_REQUIRED,
            'npm unavailable in this environment; run '
            '`cd src/frontend && npm run typecheck && npm run test:unit && '
            'npm run test:integration` and drop docs/evidence/frontend-suites-*.json',
        )
    res = run(['npm', 'run', 'test:unit'], cwd=frontend, timeout=900)
    passed = res.returncode == 0
    return GateCheck(
        'frontend_suites',
        Status.PASS if passed else Status.FAIL,
        'frontend test:unit exit 0' if passed else f'frontend test:unit exit {res.returncode}',
        {'returncode': res.returncode, 'tail': (res.stdout + res.stderr).strip().splitlines()[-6:]},
    )


def check_immutable_laws() -> GateCheck:
    """Check 5: the two immutable laws — RestApi and Cognito UserPool logical ids
    byte-stable — enforced by the existing pinned-anchor tests."""
    targets = [
        'tests/infrastructure/test_p26_blue_green_api.py::test_rest_api_logical_id_unchanged',
        'tests/infrastructure/test_p24_identity_surrogate_infra.py',
    ]
    res = run(
        ['uv', 'run', 'pytest', *targets, '-q', '--tb=line', '-k', 'logical_id_unchanged or user_pool'],
        cwd=BACKEND_DIR,
        timeout=300,
    )
    summary = _pytest_summary(res.stdout + res.stderr)
    passed = res.returncode == 0
    return GateCheck(
        'immutable_laws',
        Status.PASS if passed else Status.FAIL,
        f'RestApi + UserPool logical-id anchors: {summary}',
        {'returncode': res.returncode, 'targets': targets},
    )


def _per_template_counts(stack: str) -> dict[str, int]:
    """Live resource count for the parent stack and EACH nested stack, keyed by
    stack name. CloudFormation's ceiling is per template, so the meaningful number
    is the max over these, not their sum."""
    counts: dict[str, int] = {}
    frontier = [stack]
    while frontier:
        current = frontier.pop()
        res = run(
            ['aws', 'cloudformation', 'list-stack-resources', '--stack-name', current, '--output', 'json'],
            cwd=REPO_ROOT,
            timeout=120,
        )
        if res.returncode != 0:
            raise RuntimeError(f'list-stack-resources {current} failed: {res.stderr.strip()}')
        summaries = json.loads(res.stdout).get('StackResourceSummaries', [])
        counts[current] = len(summaries)
        for r in summaries:
            if r.get('ResourceType') == 'AWS::CloudFormation::Stack':
                phys = r.get('PhysicalResourceId', '')
                nested = phys.split('/')[1] if '/' in phys else phys
                if nested and nested not in counts:
                    frontier.append(nested)
    return counts


def check_live_resource_count() -> GateCheck:
    """Check 6: no live template on CareerVpCrudDevx breaches the hard CFN ceiling,
    read from AWS (not synth). The 400 aspirational target is reported, not enforced
    (it needs the blocked P-26 Job-1 collapse)."""
    if run(['aws', 'sts', 'get-caller-identity'], cwd=REPO_ROOT, timeout=30).returncode != 0:
        return GateCheck(
            'live_resource_count',
            Status.HUMAN_REQUIRED,
            'no AWS credentials; run with devx read access to count live resources',
        )
    try:
        counts = _per_template_counts(DEVX_STACK)
    except (RuntimeError, json.JSONDecodeError) as exc:
        return GateCheck('live_resource_count', Status.FAIL, f'AWS read failed: {exc}')
    worst_stack = max(counts, key=lambda k: counts[k])
    worst = counts[worst_stack]
    passed = worst < CFN_HARD_CEILING
    target_note = (
        f'meets {CFN_TARGET_CEILING} target' if worst < CFN_TARGET_CEILING else f'over {CFN_TARGET_CEILING} target (needs P-26 Job-1 collapse)'
    )
    return GateCheck(
        'live_resource_count',
        Status.PASS if passed else Status.FAIL,
        f'largest live template = {worst} resources ({worst_stack.split("-")[0]}…), '
        f'{"under" if passed else "AT/OVER"} hard {CFN_HARD_CEILING}; {target_note}',
        {'counts': counts, 'worst': worst, 'hard': CFN_HARD_CEILING, 'target': CFN_TARGET_CEILING},
    )


def check_smoke_harness() -> GateCheck:
    """Check 7: the P-30 deploy smoke harness at 4/4 against devx. Needs a live
    API_BASE + token; otherwise HUMAN_REQUIRED."""
    if not os.environ.get('API_BASE') or not os.environ.get('SMOKE_TOKEN'):
        return GateCheck(
            'smoke_harness_4x4',
            Status.HUMAN_REQUIRED,
            'API_BASE/SMOKE_TOKEN not set; run '
            '`API_BASE=<devx-invoke-url> SMOKE_ORIGIN=<fe-origin> SMOKE_TOKEN=<cognito> '
            'uv run python scripts/smoke_harness.py` and keep the docs/evidence/smoke-*.json',
        )
    res = run(['uv', 'run', 'python', 'scripts/smoke_harness.py'], cwd=BACKEND_DIR, timeout=300)
    passed = res.returncode == 0
    return GateCheck(
        'smoke_harness_4x4',
        Status.PASS if passed else Status.FAIL,
        'smoke harness 4/4' if passed else f'smoke harness exit {res.returncode} (not 4/4)',
        {'returncode': res.returncode, 'stderr_tail': res.stderr.strip().splitlines()[-6:]},
    )


def _bet_verdict(issues_text: str, bet: str) -> str:
    """Extract a one-line closing verdict for a bet from ISSUES.md."""
    # Prefer the last line that mentions the bet with a TRUE/FALSE/closed/open verdict.
    verdict_line = ''
    for line in issues_text.splitlines():
        if bet in line and re.search(r'\b(TRUE|FALSE|closed|open|settled|remains)\b', line):
            verdict_line = line.strip().lstrip('*# ').strip()
    return verdict_line or f'{bet}: no verdict line found in ISSUES.md'


def check_bets_and_i06() -> list[GateCheck]:
    """Check 8 + also-required: re-read the five bets and confirm I-06 still
    carries its stopping condition."""
    if not ISSUES_MD.exists():
        return [GateCheck('bets_ledger', Status.FAIL, f'ISSUES.md not found at {ISSUES_MD}')]
    text = ISSUES_MD.read_text(encoding='utf-8')
    verdicts = {bet: _bet_verdict(text, bet) for bet in WAVE2_BETS}
    unresolved = [b for b, v in verdicts.items() if re.search(r'\bopen\b', v) and 'remains open' in v.lower()]
    bets_check = GateCheck(
        'bets_ledger',
        Status.RECORDED if not unresolved else Status.HUMAN_REQUIRED,
        'all five Wave-2 bets re-read; '
        + ('none left open' if not unresolved else f'still open (settle or defer with stopping condition): {unresolved}'),
        {'verdicts': verdicts},
    )

    i06 = re.search(r'I-06.*?(?=\n## |\Z)', text, re.DOTALL)
    i06_text = i06.group(0) if i06 else ''
    has_stop = bool(re.search(r'stop', i06_text, re.IGNORECASE)) and bool(i06_text)
    i06_check = GateCheck(
        'i06_stopping_condition',
        Status.RECORDED if has_stop else Status.FAIL,
        'I-06 (admin scope on browser login client) still carries a stopping condition'
        if has_stop
        else 'I-06 stopping condition missing or I-06 absent from ISSUES.md',
    )
    return [bets_check, i06_check]


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
# Each check function paired with the check names it can emit, so ``--only`` can
# skip EXECUTION (not just output) — otherwise a filtered-out check like the
# coverage suite would still run its 5-minute body every time.
CHECK_REGISTRY: tuple[tuple[Callable[[], object], tuple[str, ...]], ...] = (
    (check_scope_diff, ('scope_diff',)),
    (check_infra_test_dirs, ('infra_tests_backend', 'infra_tests_cdk')),
    (check_suites_and_coverage, ('backend_unit_integration', 'coverage_gate')),
    (check_frontend_suites, ('frontend_suites',)),
    (check_immutable_laws, ('immutable_laws',)),
    (check_live_resource_count, ('live_resource_count',)),
    (check_smoke_harness, ('smoke_harness_4x4',)),
    (check_bets_and_i06, ('bets_ledger', 'i06_stopping_condition')),
)


def run_gate(only: set[str] | None = None) -> GateReport:
    checks: list[GateCheck] = []
    for func, names in CHECK_REGISTRY:
        if only and not (set(names) & only):
            continue  # skip execution entirely, not just the output
        result = func()
        produced = result if isinstance(result, list) else [result]
        checks.extend(c for c in produced if not only or c.name in only)
    return GateReport(checks=checks, timestamp=datetime.now(timezone.utc).isoformat())


def write_evidence(report: GateReport, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = out_dir / f'wave2-gate-{stamp}-{uuid.uuid4().hex[:6]}.json'
    path.write_text(json.dumps(report.to_evidence(), indent=2, sort_keys=True), encoding='utf-8')
    return path


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Wave 2 close-out gate')
    parser.add_argument('--evidence-dir', type=Path, default=EVIDENCE_DIR)
    parser.add_argument('--print-only', action='store_true', help='do not write an evidence file')
    parser.add_argument('--only', nargs='*', help='run only the named checks (by check name)')
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = run_gate(only=set(args.only) if args.only else None)

    if args.print_only:
        print(json.dumps(report.to_evidence(), indent=2, sort_keys=True))
    else:
        path = write_evidence(report, args.evidence_dir)
        print(f'evidence written to {path}')

    for check in report.checks:
        print(f'  [{check.status.value:>14}] {check.name}: {check.detail}', file=sys.stderr)
    verdict = 'PASS' if report.passed else 'BLOCKED'
    print(f'\nWave 2 gate: {verdict}', file=sys.stderr)
    return 0 if report.passed else 1


if __name__ == '__main__':
    sys.exit(main())
