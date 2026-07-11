#!/usr/bin/env python3
"""Enforce db-redesign differentiated line and branch coverage gates."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CoverageGate:
    """Minimum line and branch percentages for a coverage tier."""

    line_percent: float
    branch_percent: float


@dataclass(frozen=True)
class CoverageTotals:
    """Aggregated coverage counters for one coverage tier."""

    covered_lines: int = 0
    num_statements: int = 0
    covered_branches: int = 0
    num_branches: int = 0

    @property
    def line_percent(self) -> float:
        return _percent(self.covered_lines, self.num_statements)

    @property
    def branch_percent(self) -> float:
        return _percent(self.covered_branches, self.num_branches)


COVERAGE_GATES: dict[str, CoverageGate] = {
    'core': CoverageGate(line_percent=71.0, branch_percent=53.0),
    'supporting': CoverageGate(line_percent=70.0, branch_percent=48.0),
    'overall': CoverageGate(line_percent=70.0, branch_percent=51.0),
}

CORE_PATTERNS: tuple[str, ...] = (
    'careervp/logic/artifact_dependency_resolver.py',
    'careervp/logic/gap_analysis.py',
    'careervp/logic/vpr_generator.py',
    'careervp/logic/cover_letter.py',
    'careervp/logic/interview_prep.py',
    'careervp/logic/cv_tailoring*.py',
    'careervp/handlers/gap_handler.py',
    'careervp/handlers/vpr_submit_handler.py',
    'careervp/handlers/vpr_worker_handler.py',
    'careervp/handlers/cover_letter_handler.py',
    'careervp/handlers/cover_letter_submit_handler.py',
    'careervp/handlers/interview_prep_handler.py',
    'careervp/handlers/interview_prep_submit_handler.py',
    'careervp/handlers/cv_tailoring_handler.py',
)

SUPPORTING_PATTERNS: tuple[str, ...] = (
    'careervp/dal/*.py',
    'careervp/models/*.py',
    'careervp/payment_providers/*.py',
    'careervp/validation/*.py',
    'careervp/logic/auth_service.py',
    'careervp/logic/billing_service.py',
    'careervp/logic/cancellation.py',
    'careervp/logic/circuit_breaker.py',
    'careervp/logic/company_*.py',
    'careervp/logic/cv_parser.py',
    'careervp/logic/cv_summarizer.py',
    'careervp/logic/fvs_validator.py',
    'careervp/logic/llm_*.py',
    'careervp/logic/quota_service.py',
    'careervp/logic/reconciliation_service.py',
    'careervp/logic/trial_service.py',
    'careervp/logic/webhook_service.py',
)


def load_coverage_json(path: Path) -> dict[str, Any]:
    """Load coverage.py JSON output."""
    with path.open(encoding='utf-8') as coverage_file:
        data = json.load(coverage_file)
    if not isinstance(data, dict):
        raise ValueError('Coverage JSON root must be an object')
    return data


def collect_totals(data: dict[str, Any]) -> dict[str, CoverageTotals]:
    """Aggregate coverage totals for overall, core, and supporting tiers."""
    files = data.get('files', {})
    if not isinstance(files, dict):
        raise ValueError('Coverage JSON must contain a files object')

    overall_totals = _totals_from_mapping(data.get('totals', {}))
    core_totals = CoverageTotals()
    supporting_totals = CoverageTotals()

    for filename, payload in files.items():
        if not isinstance(filename, str) or not isinstance(payload, dict):
            continue
        normalized = filename.replace('\\', '/')
        summary = payload.get('summary', {})
        if not isinstance(summary, dict):
            continue
        file_totals = _totals_from_mapping(summary)
        if _matches_any(normalized, CORE_PATTERNS):
            core_totals = _add_totals(core_totals, file_totals)
        elif _matches_any(normalized, SUPPORTING_PATTERNS):
            supporting_totals = _add_totals(supporting_totals, file_totals)

    return {
        'overall': overall_totals,
        'core': core_totals,
        'supporting': supporting_totals,
    }


def check_gates(totals_by_gate: dict[str, CoverageTotals]) -> list[str]:
    """Return human-readable gate failures."""
    failures: list[str] = []
    for gate_name, gate in COVERAGE_GATES.items():
        totals = totals_by_gate[gate_name]
        if totals.num_branches <= 0:
            failures.append(f'{gate_name}: branch coverage data is missing')
            continue
        if totals.line_percent < gate.line_percent:
            failures.append(f'{gate_name}: line {totals.line_percent:.2f}% < {gate.line_percent:.2f}%')
        if totals.branch_percent < gate.branch_percent:
            failures.append(f'{gate_name}: branch {totals.branch_percent:.2f}% < {gate.branch_percent:.2f}%')
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description='Check CareerVP differentiated coverage gates.')
    parser.add_argument('coverage_json', type=Path, help='coverage.py JSON output path')
    args = parser.parse_args()

    data = load_coverage_json(args.coverage_json)
    totals_by_gate = collect_totals(data)
    failures = check_gates(totals_by_gate)

    for gate_name in ('overall', 'core', 'supporting'):
        totals = totals_by_gate[gate_name]
        print(f'{gate_name}: line={totals.line_percent:.2f}% branch={totals.branch_percent:.2f}%')

    if failures:
        print('Coverage gate failures:', file=sys.stderr)
        for failure in failures:
            print(f'  - {failure}', file=sys.stderr)
        return 1
    return 0


def _totals_from_mapping(summary: object) -> CoverageTotals:
    if not isinstance(summary, dict):
        return CoverageTotals()
    return CoverageTotals(
        covered_lines=_int_value(summary.get('covered_lines')),
        num_statements=_int_value(summary.get('num_statements')),
        covered_branches=_int_value(summary.get('covered_branches')),
        num_branches=_int_value(summary.get('num_branches')),
    )


def _add_totals(left: CoverageTotals, right: CoverageTotals) -> CoverageTotals:
    return CoverageTotals(
        covered_lines=left.covered_lines + right.covered_lines,
        num_statements=left.num_statements + right.num_statements,
        covered_branches=left.covered_branches + right.covered_branches,
        num_branches=left.num_branches + right.num_branches,
    )


def _matches_any(filename: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)


def _percent(covered: int, total: int) -> float:
    if total <= 0:
        return 100.0
    return covered / total * 100


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


if __name__ == '__main__':
    sys.exit(main())
