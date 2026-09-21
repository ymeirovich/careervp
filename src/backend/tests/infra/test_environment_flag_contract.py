"""Backend/infra *_ENABLED flag producer/consumer contract.

Catches both directions of flag drift in one test: a flag read in the backend
but never set anywhere in infra (the ARTIFACT_CHAIN_ENABLED bug — read but
never produced for the ``devx`` environment after the P-26 rename), and a
flag set by infra but never read by anything (FVS_ENABLED, set only in an
orphaned CDK stack nothing imports).

Spec: docs/handoff/2026-09-21-HANDOFF-09-environment-coupling.md, Step 3.2.
"""

from __future__ import annotations

import re
from pathlib import Path

# src/backend/tests/infra/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_SRC = REPO_ROOT / 'src' / 'backend' / 'careervp'
INFRA_SRC = REPO_ROOT / 'infra' / 'careervp'

_FLAG_NAME = r'[A-Z][A-Z0-9_]*_ENABLED'
_READ_PATTERN = re.compile(rf"os\.(?:environ\.get|getenv)\(\s*['\"]({_FLAG_NAME})['\"]")
_WRITE_PATTERNS = (
    re.compile(rf"['\"]({_FLAG_NAME})['\"]\s*:"),  # dict literal: "X_ENABLED": ...
    re.compile(rf"add_environment\(\s*['\"]({_FLAG_NAME})['\"]"),  # fn.add_environment("X_ENABLED", ...)
)

# Flags read in the backend with a safe, explicit default baked into the read call
# itself (not a resource-name guess) that no infra stack has needed to override yet.
# Each entry must justify why an unset var is safe, not just silence the test.
KNOWN_UNPRODUCED: frozenset[str] = frozenset(
    {
        # os.environ.get('COMPANY_RESEARCH_LEGACY_READ_ENABLED', 'true') — defaults to
        # the current (legacy-read-on) behavior; no environment has ever needed to flip
        # it off, so no CDK stack sets it. Unlike the Class-A bugs in HANDOFF-09, an
        # unset value here is the intended, safe steady state, not a cross-environment
        # resource-name guess.
        'COMPANY_RESEARCH_LEGACY_READ_ENABLED',
    }
)

# Flags produced by CDK but not (yet) read anywhere in the backend.
KNOWN_UNUSED: frozenset[str] = frozenset(
    {
        # FVS_ENABLED is set only in src/backend/careervp/infrastructure/stacks/
        # cv_tailoring_stack.py, an orphaned CDK stack nothing in app.py/service_stack.py
        # imports (every other repo hit is a cdk.out/.build copy of this same file).
        # Tracked in HANDOFF-09's Class C finding — the real fix is deleting that stack
        # (and its dedicated test at tests/cv-tailoring/infrastructure/
        # test_cv_tailoring_stack.py) once an operator confirms it, not adding a reader
        # for a flag nothing should consume.
        'FVS_ENABLED',
    }
)


def _python_files(root: Path) -> list[Path]:
    return [p for p in root.rglob('*.py') if '__pycache__' not in p.parts]


def _grep_flags(root: Path, patterns: tuple[re.Pattern[str], ...]) -> set[str]:
    flags: set[str] = set()
    for path in _python_files(root):
        text = path.read_text(encoding='utf-8')
        for pattern in patterns:
            flags.update(pattern.findall(text))
    return flags


def test_every_consumed_flag_is_produced_and_vice_versa() -> None:
    consumed = _grep_flags(BACKEND_SRC, (_READ_PATTERN,))
    produced = _grep_flags(INFRA_SRC, _WRITE_PATTERNS)

    unset = consumed - produced - KNOWN_UNPRODUCED
    assert not unset, f'read in backend but never set by infra: {sorted(unset)}'

    unread = produced - consumed - KNOWN_UNUSED
    assert not unread, f'set by infra but never read in backend: {sorted(unread)}'
