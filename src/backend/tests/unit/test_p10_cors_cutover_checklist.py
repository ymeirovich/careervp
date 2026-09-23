"""P-10 RED tests: P-30 smoke must gate the API CORS allow-list cutover.

RED test cited by specs/P-08-P-10-P-11-cors-waf-spec.md, AC-P10-1/AC-P10-2:
``test_p30_exact_origin_smoke_required_before_cors_cutover``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).resolve().parents[2] / 'scripts' / 'cors_cutover_checklist.py'
_spec = importlib.util.spec_from_file_location('cors_cutover_checklist', _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
cors_cutover_checklist = importlib.util.module_from_spec(_spec)
sys.modules['cors_cutover_checklist'] = cors_cutover_checklist
_spec.loader.exec_module(cors_cutover_checklist)

CorsCutoverBlocked = cors_cutover_checklist.CorsCutoverBlocked
check_p30_smoke_required_before_cors_cutover = cors_cutover_checklist.check_p30_smoke_required_before_cors_cutover

PASSING_EVIDENCE = {
    'api_base': 'https://api.dev.careervp.com',
    'origin': 'https://main.d3j2wnm8g5clnw.amplifyapp.com',
    'passed': True,
    'timestamp': '2026-07-17T18:52:28.380004+00:00',
    'checks': [
        {'name': 'health', 'passed': True},
        {'name': 'cors_exact_origin', 'passed': True},
        {'name': 'authed_read', 'passed': True},
        {'name': 'authed_upload', 'passed': True},
    ],
}


def _write_evidence(evidence_dir: Path, name: str, payload: dict[str, object]) -> None:
    (evidence_dir / name).write_text(json.dumps(payload), encoding='utf-8')


def test_p30_exact_origin_smoke_required_before_cors_cutover(tmp_path: Path) -> None:
    """No evidence at all must block the cutover."""
    with pytest.raises(CorsCutoverBlocked):
        check_p30_smoke_required_before_cors_cutover(tmp_path)


def test_p30_smoke_blocks_cutover_when_latest_run_failed(tmp_path: Path) -> None:
    failing = dict(PASSING_EVIDENCE, passed=False)
    _write_evidence(tmp_path, 'smoke-20260101T000000Z-abcdef.json', failing)
    with pytest.raises(CorsCutoverBlocked):
        check_p30_smoke_required_before_cors_cutover(tmp_path)


def test_p30_smoke_blocks_cutover_when_exact_origin_wire_missing(tmp_path: Path) -> None:
    stale = dict(PASSING_EVIDENCE)
    stale['checks'] = [c for c in PASSING_EVIDENCE['checks'] if c['name'] != 'cors_exact_origin']
    _write_evidence(tmp_path, 'smoke-20260101T000000Z-abcdef.json', stale)
    with pytest.raises(CorsCutoverBlocked):
        check_p30_smoke_required_before_cors_cutover(tmp_path)


def test_p30_smoke_allows_cutover_when_latest_run_is_green(tmp_path: Path) -> None:
    _write_evidence(tmp_path, 'smoke-20260101T000000Z-abcdef.json', PASSING_EVIDENCE)
    # Must not raise.
    check_p30_smoke_required_before_cors_cutover(tmp_path)


def test_p30_smoke_checklist_uses_latest_evidence_file(tmp_path: Path) -> None:
    """An older failing run followed by a newer passing run must allow cutover."""
    failing = dict(PASSING_EVIDENCE, passed=False)
    _write_evidence(tmp_path, 'smoke-20260101T000000Z-000001.json', failing)
    _write_evidence(tmp_path, 'smoke-20260102T000000Z-000002.json', PASSING_EVIDENCE)
    check_p30_smoke_required_before_cors_cutover(tmp_path)
