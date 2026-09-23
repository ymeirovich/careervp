#!/usr/bin/env python3
"""P-10: gate that blocks the API CORS allow-list cutover until P-30 is green.

RED test cited by specs/P-08-P-10-P-11-cors-waf-spec.md, AC-P10-1/AC-P10-2:
`test_p30_exact_origin_smoke_required_before_cors_cutover`.

The API Gateway CORS cutover (`ALL_ORIGINS` -> explicit allow-list) is a
browser-visible change: a bad allow-list silently breaks every route for real
users. Before it ships, the P-30 4-wire smoke harness (``smoke_harness.py``)
must have produced a passing evidence file that actually exercised the
OPTIONS+GET exact-origin wire against a live deploy.
"""

from __future__ import annotations

import json
from pathlib import Path


class CorsCutoverBlocked(Exception):
    """Raised when the CORS cutover checklist is not satisfied."""


REQUIRED_WIRES = frozenset({'health', 'cors_exact_origin', 'authed_read', 'authed_upload'})


def latest_smoke_evidence(evidence_dir: Path) -> dict[str, object] | None:
    """Return the most recently written P-30 smoke evidence file, if any."""
    files = sorted(evidence_dir.glob('smoke-*.json'))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding='utf-8'))


def check_p30_smoke_required_before_cors_cutover(evidence_dir: Path) -> None:
    """Raise CorsCutoverBlocked unless the latest P-30 smoke evidence is green.

    Checks three things: evidence exists, it reports an overall pass, and the
    exact-origin CORS wire specifically ran (a stale evidence file predating
    that wire must not be treated as a green light).
    """
    evidence = latest_smoke_evidence(evidence_dir)
    if evidence is None:
        raise CorsCutoverBlocked('no P-30 smoke evidence found; run smoke_harness.py against a live deploy before cutting over API Gateway CORS')
    if not evidence.get('passed'):
        raise CorsCutoverBlocked('latest P-30 smoke evidence did not pass; do not cut over CORS')
    checks = {c['name'] for c in evidence.get('checks', []) if isinstance(c, dict)}
    missing = REQUIRED_WIRES - checks
    if missing:
        raise CorsCutoverBlocked(f'latest P-30 smoke evidence is missing required wires: {sorted(missing)}')
    cors_check = next(
        (c for c in evidence.get('checks', []) if isinstance(c, dict) and c['name'] == 'cors_exact_origin'),
        None,
    )
    if cors_check is None or not cors_check.get('passed'):
        raise CorsCutoverBlocked('P-30 exact-origin CORS wire did not pass; do not cut over CORS')
