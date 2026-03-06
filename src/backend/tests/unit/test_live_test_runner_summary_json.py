"""Tests for summary JSON output in docs/refactor/live_tests/run_all_tests.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
RUNNER_PATH = REPO_ROOT / 'docs' / 'refactor' / 'live_tests' / 'run_all_tests.py'


def test_dry_run_smoke_writes_summary_json(tmp_path: Path) -> None:
    summary_path = tmp_path / 'smoke-summary.json'

    result = subprocess.run(
        [
            sys.executable,
            str(RUNNER_PATH),
            '--mode',
            'smoke',
            '--dry-run',
            '--summary-json',
            str(summary_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert summary_path.exists(), 'Expected --summary-json output file to be created'

    payload = json.loads(summary_path.read_text(encoding='utf-8'))
    assert payload['mode'] == 'smoke-dry-run'
    assert payload['status'] == 'pass'
    assert payload['exit_code'] == 0
    assert payload['totals']['selected'] == 3
    assert payload['totals']['failed'] == 0
    module_names = [module['name'] for module in payload['modules']]
    assert module_names == ['bootstrap', 'health', 'auth']
