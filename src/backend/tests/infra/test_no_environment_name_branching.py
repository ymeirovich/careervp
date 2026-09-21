"""Static guard: no new environment-name-coupled branch or default.

Direct answer to "catch future hardcoded bugs" (HANDOFF-09 Step 3.3). A branch
on ``environment == "dev"`` or a default of ``os.environ.get('ENVIRONMENT',
'dev')`` is exactly the pattern that silently disabled the artifact chain
when P-26 renamed ``dev`` to ``devx`` — a capability belongs in
environments.py, and a missing ENVIRONMENT must fail loud via resource_env(),
never guess another live environment's name.

A line may opt out with a trailing or preceding ``# allow-env-literal: <reason>``
comment, so a legitimate exception is visible in review rather than invisible
in a default.
"""

from __future__ import annotations

import re
from pathlib import Path

# src/backend/tests/infra/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_ROOTS = (
    REPO_ROOT / 'src' / 'backend' / 'careervp',
    REPO_ROOT / 'infra' / 'careervp',
)

FORBIDDEN: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"""environment\s*==\s*['"](dev|devx|prod|staging)['"]"""),
        'branch on a capability in environments.py, not an environment name',
    ),
    (
        re.compile(r"""environ\.get\(\s*['"]ENVIRONMENT['"]\s*,\s*['"]\w+['"]\s*\)"""),
        'use resource_env(); never default to another environment',
    ),
)

_ALLOW_MARKER = '# allow-env-literal:'


def _python_files(root: Path) -> list[Path]:
    return [p for p in root.rglob('*.py') if '__pycache__' not in p.parts]


def _has_allow_marker_above(lines: list[str], lineno: int) -> bool:
    """Walk the contiguous ``#``-comment block directly above ``lineno``
    (1-indexed) for an ``# allow-env-literal:`` marker anywhere in it."""
    index = lineno - 2
    while index >= 0 and lines[index].strip().startswith('#'):
        if _ALLOW_MARKER in lines[index]:
            return True
        index -= 1
    return False


def test_no_environment_name_branching() -> None:
    violations: list[str] = []
    for root in SOURCE_ROOTS:
        for path in _python_files(root):
            lines = path.read_text(encoding='utf-8').splitlines()
            for lineno, line in enumerate(lines, start=1):
                for pattern, why in FORBIDDEN:
                    if not pattern.search(line):
                        continue
                    if _ALLOW_MARKER in line or _has_allow_marker_above(lines, lineno):
                        continue
                    violations.append(f'{path.relative_to(REPO_ROOT)}:{lineno}: {why}')
    assert not violations, 'environment-name coupling found:\n' + '\n'.join(violations)
