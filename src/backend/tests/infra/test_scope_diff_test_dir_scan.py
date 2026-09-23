"""RED-first test for scope-diff.py's test-directory blind spot.

scope-diff.py's tests-dir auto-detection only ever pointed at src/backend/tests, so
clauses tested exclusively under infra/tests/ were invisible to the drift board and
reported spec_written instead of test_written even though passing tests exist there.
This exercises the actual CLI auto-detection path (no --tests-dir override).

Deliberately avoids writing the target clause IDs as literal tokens in this file's own
source: scope-diff.py's clause regex scans every .py file under the tests dir it's
given, including this one, so a hardcoded literal would make the (buggy) single-dir
scan pass for the wrong reason — it would "find" the clause reference sitting right
here, not the real coverage under infra/tests/. The IDs are instead read at runtime
from the retain-stateful spec's frontmatter, which lives outside any tests dir scope-diff
scans.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
PROJECT_DIR = REPO_ROOT / 'docs' / 'db-redesign' / 'code' / 'code-analysis' / 'project'
SCOPE_DIFF_PATH = PROJECT_DIR / 'scope-diff.py'


def _find_retain_spec_path() -> Path:
    matches = list((PROJECT_DIR / 'specs').glob('*retain-stateful-spec.md'))
    assert len(matches) == 1, f'expected exactly one retain-stateful spec, found {matches}'
    return matches[0]


def _target_clause_ids() -> list[str]:
    spec_path = _find_retain_spec_path()
    text = spec_path.read_text(encoding='utf-8')
    m = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    assert m, f'no frontmatter found in {spec_path}'
    fm = yaml.safe_load(m.group(1)) or {}
    clause_field = fm['scope_lock_clause']
    return [clause_field] if isinstance(clause_field, str) else list(clause_field)


def _run_scope_diff_json() -> dict:
    result = subprocess.run(
        [sys.executable, str(SCOPE_DIFF_PATH), '--json'],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_retain_spec_clauses_resolve_test_written_via_cli_auto_detection():
    clause_ids = _target_clause_ids()
    assert len(clause_ids) == 2  # the retain-stateful spec covers exactly two clauses

    board = _run_scope_diff_json()['board']
    by_id = {r['id']: r for r in board}

    for clause_id in clause_ids:
        assert clause_id in by_id
        assert by_id[clause_id]['impl_state'] == 'test_written', (
            f'{clause_id} should resolve to test_written via infra/tests/ coverage '
            f'(scope-diff.py must scan infra/tests/ in addition to '
            f'src/backend/tests/), got {by_id[clause_id]["impl_state"]!r}'
        )
