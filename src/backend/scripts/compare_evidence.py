"""Compare two proofs and say what *kind* of problem you have.

A proof on its own tells you where you are. Two proofs, subtracted, tell you
what changed — and that decides which investigation is worth starting. Getting
this wrong is expensive: hunting through commits for a problem that was really
a configuration change finds nothing, slowly.

The four verdicts
-----------------
    CODE          the commit changed. Bisect between the two SHAs.
    DEPLOYMENT    same commit, different code running. A deploy shipped
                  something unexpected, or did not ship at all.
    CONFIGURATION same code, same deploy, different stack/context. Nothing in
                  your source caused this.
    EXTERNAL      nothing observable changed but the result did. Suspect data,
                  a third-party API, credentials, or flakiness.

Usage
-----
    uv run python scripts/compare_evidence.py OLD.json NEW.json
    uv run python scripts/compare_evidence.py --kind journey     # latest two
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_stamp import DEFAULT_EVIDENCE_DIR  # noqa: E402

# Fields compared for every proof, in the order a human should read them.
STAMP_FIELDS: Final[tuple[str, ...]] = (
    'timestamp',
    'git_short',
    'git_dirty',
    'deployed_sha',
    'deployed_matches_head',
    'stack',
)

CODE: Final[str] = 'CODE'
DEPLOYMENT: Final[str] = 'DEPLOYMENT'
CONFIGURATION: Final[str] = 'CONFIGURATION'
EXTERNAL: Final[str] = 'EXTERNAL'


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def two_latest(kind: str, evidence_dir: Path) -> tuple[Path, Path]:
    candidates = sorted(evidence_dir.glob(f'{kind}-*.json'))
    if len(candidates) < 2:
        raise SystemExit(f'need at least two {kind} proofs in {evidence_dir}, found {len(candidates)}')
    return candidates[-2], candidates[-1]


def outcome_of(proof: dict[str, Any]) -> str | None:
    """The headline result, whatever kind of proof this is."""
    if 'journey_reached' in proof:
        return f'reached {proof["journey_reached"]}'
    if 'premises' in proof:
        fails = sum(1 for p in proof['premises'] if p.get('status') == 'FAIL')
        return f'{fails} failing premise(s)'
    if 'passed' in proof:
        return f'passed={proof["passed"]}'
    return None


def classify(old: dict[str, Any], new: dict[str, Any]) -> tuple[str, str]:
    """Decide which investigation the difference justifies."""
    if old.get('git_sha') != new.get('git_sha'):
        return CODE, (
            f'The commit changed ({str(old.get("git_short"))} → {str(new.get("git_short"))}). '
            f'Bisect: git bisect start {str(new.get("git_sha"))} {str(old.get("git_sha"))}'
        )

    if old.get('deployed_sha') != new.get('deployed_sha'):
        return DEPLOYMENT, (
            f'Same commit, but the stack is running different code '
            f'({str(old.get("deployed_sha"))} → {str(new.get("deployed_sha"))}). Check what the last deploy actually shipped.'
        )

    for key in ('stack', 'cdk_context', 'api_base'):
        if key in old or key in new:
            if old.get(key) != new.get(key):
                return CONFIGURATION, f'Code and deployment are identical; {key} differs. Your source did not cause this.'

    return EXTERNAL, 'Nothing observable changed. Suspect data, a third-party API, an expired credential, or a flaky test.'


def diff_rows(old: dict[str, Any], new: dict[str, Any]) -> list[tuple[str, str, str, bool]]:
    rows: list[tuple[str, str, str, bool]] = []

    old_outcome, new_outcome = outcome_of(old), outcome_of(new)
    if old_outcome or new_outcome:
        rows.append(('outcome', str(old_outcome), str(new_outcome), old_outcome != new_outcome))

    for fieldname in STAMP_FIELDS:
        old_value, new_value = old.get(fieldname), new.get(fieldname)
        if old_value is None and new_value is None:
            continue
        rows.append((fieldname, str(old_value), str(new_value), old_value != new_value))

    return rows


def step_changes(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    """For journey proofs, name the steps whose result moved."""
    old_steps = old.get('steps') or {}
    new_steps = new.get('steps') or {}
    if not isinstance(old_steps, dict) or not isinstance(new_steps, dict):
        return []
    changed = []
    for key in sorted(set(old_steps) | set(new_steps)):
        before, after = old_steps.get(key, '—'), new_steps.get(key, '—')
        if before != after:
            changed.append(f'  {key}: {before} → {after}')
    return changed


def render(old_path: Path, new_path: Path, old: dict[str, Any], new: dict[str, Any]) -> str:
    rows = diff_rows(old, new)
    label_width = max(len(r[0]) for r in rows)
    old_width = max(max((len(r[1]) for r in rows), default=0), len('older'))

    lines = [
        f'older: {old_path.name}',
        f'newer: {new_path.name}',
        '',
        f'{"field".ljust(label_width)}  {"older".ljust(old_width)}  newer',
        f'{"-" * label_width}  {"-" * old_width}  {"-" * old_width}',
    ]
    for name, before, after, differs in rows:
        marker = '  ← DIFFERS' if differs else ''
        lines.append(f'{name.ljust(label_width)}  {before.ljust(old_width)}  {after}{marker}')

    steps = step_changes(old, new)
    if steps:
        lines += ['', 'journey steps that moved:', *steps]

    verdict, guidance = classify(old, new)
    lines += ['', f'VERDICT: {verdict}', guidance]

    if old.get('git_dirty') or new.get('git_dirty'):
        lines += [
            '',
            'WARNING: at least one proof was taken from a dirty tree. It describes code',
            'that is not in git, so this comparison may be meaningless.',
        ]

    return '\n'.join(lines)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Subtract two proofs')
    parser.add_argument('old', nargs='?', type=Path)
    parser.add_argument('new', nargs='?', type=Path)
    parser.add_argument('--kind', help='compare the two most recent proofs of this kind (e.g. journey, preflight)')
    parser.add_argument('--dir', type=Path, default=DEFAULT_EVIDENCE_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.kind:
        old_path, new_path = two_latest(args.kind, args.dir)
    elif args.old and args.new:
        old_path, new_path = args.old, args.new
    else:
        raise SystemExit('give two proof paths, or --kind to take the latest two')

    print(render(old_path, new_path, load(old_path), load(new_path)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
