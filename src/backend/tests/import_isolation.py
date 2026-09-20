"""Restore-on-exit switching between the repo's two `careervp` packages.

This repo contains two distinct, unrelated packages both named `careervp`:

* ``src/backend/careervp`` — handlers, logic, DAL. Has a ``handlers`` subpackage.
* ``infra/careervp``      — CDK stacks (``service_stack``, ``naming_utils``).
  Has no ``handlers`` subpackage.

Only one of them can own ``sys.modules['careervp']`` at a time. CDK-synth tests
need infra's; every other test needs the backend's. ``tests/conftest.py``
imports the backend's at collection time, so the backend's is what a process
starts with.

The historical way to switch was written inline in each CDK-synth test::

    sys.path = [p for p in sys.path if p != INFRA_SRC]
    sys.path.insert(0, INFRA_SRC)
    for name, module in list(sys.modules.items()):
        if name == 'careervp' or name.startswith('careervp.'):
            if not str(getattr(module, '__file__', '') or '').startswith(INFRA_SRC):
                sys.modules.pop(name, None)
    from careervp.service_stack import ServiceStack

That is correct for the test doing it and permanently destructive for every
test that runs after it in the same process: nothing puts the evicted backend
modules back, and because ``infra/`` is now at ``sys.path[0]`` the next
``import careervp`` binds ``sys.modules['careervp']`` to infra's package for
the rest of the process. Any later ``import careervp.handlers.*`` then raises
``ModuleNotFoundError: No module named 'careervp.handlers'``.

``tests/unit/test_p17_worker_batch_item_failures.py`` ran the mirror image of
the same dance in the opposite direction (prefer ``BACKEND_SRC``, evict
everything resolved from elsewhere), so the two clobbered each other and the
winner depended purely on which ran last — which is why whole-suite failure
counts moved by ~200 between runs once ``pytest-randomly`` was enabled.

``careervp_root()`` does the same switch and then puts everything back:
``sys.path`` is restored wholesale and the ``careervp*`` entries in
``sys.modules`` are restored to the exact module objects that were cached on
entry. Use it as a context manager around the import *and* every use of what
was imported.

See ``docs/handoff/2026-09-20-HANDOFF-02-test-isolation.md`` and
``tests/regression/test_careervp_import_isolation.py``, which fails if any test
file reintroduces the raw pattern.
"""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_SRC = str(REPO_ROOT / 'src' / 'backend')
INFRA_SRC = str(REPO_ROOT / 'infra')


def _cached_careervp_modules() -> dict[str, ModuleType]:
    """Every currently-cached module belonging to either `careervp` package."""
    return {name: module for name, module in sys.modules.items() if name == 'careervp' or name.startswith('careervp.')}


def _resolved_from(module: ModuleType, root: str) -> bool:
    return str(getattr(module, '__file__', '') or '').startswith(root)


@contextlib.contextmanager
def careervp_root(root: str) -> Iterator[None]:
    """Make `root` the package root a bare `import careervp` resolves against.

    Inside the block, ``root`` sits at ``sys.path[0]`` and any cached
    ``careervp*`` module resolved from a different root has been evicted, so a
    fresh import binds to ``root``'s package. On exit — including on exception
    — ``sys.path`` and every ``careervp*`` entry in ``sys.modules`` are put back
    exactly as they were, so the switch is invisible to the next test.

    Objects imported inside the block stay usable after it (Python objects
    outlive their ``sys.modules`` entry), but a *new* import of the same name
    afterwards resolves against the restored root — so do the work that needs
    ``root``'s package inside the block.
    """
    saved_path = list(sys.path)
    saved_modules = _cached_careervp_modules()

    sys.path = [entry for entry in sys.path if entry != root]
    sys.path.insert(0, root)
    for name, module in saved_modules.items():
        if not _resolved_from(module, root):
            del sys.modules[name]

    try:
        yield
    finally:
        for name in _cached_careervp_modules():
            del sys.modules[name]
        sys.modules.update(saved_modules)
        sys.path = saved_path


def infra_careervp() -> contextlib.AbstractContextManager[None]:
    """`careervp` resolves to `infra/careervp` (CDK stacks) inside the block."""
    return careervp_root(INFRA_SRC)


def backend_careervp() -> contextlib.AbstractContextManager[None]:
    """`careervp` resolves to `src/backend/careervp` (handlers) inside the block."""
    return careervp_root(BACKEND_SRC)
