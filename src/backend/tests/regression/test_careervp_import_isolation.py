"""Regression cover for the `careervp` package-identity contamination.

The bug (found handoff-01 Step 1b, fixed handoff-02): CDK-synth tests evicted
the backend's `careervp*` modules from `sys.modules` to force a clean import of
`infra/careervp`, and never put them back. `sys.modules['careervp']` stayed
bound to infra's package — which has no `handlers` subpackage — for the rest of
the process, so every later `import careervp.handlers.*` raised
`ModuleNotFoundError`. `tests/unit/test_p17_worker_batch_item_failures.py` ran
the same dance in the opposite direction, so the two fought and the winner
depended on run order.

Three layers here, cheapest first:

1. `test_no_unrestored_sys_modules_eviction` — static. Fails if any test file
   reintroduces a raw `sys.modules.pop` / `del sys.modules[...]`. This is the
   one that catches the bug coming back, which inline fixes in ten files cannot.
2. `test_careervp_root_round_trips_*` — behavioral, no CDK. Proves the helper
   restores both the package identity and `sys.path`, in both directions.
3. `test_real_cdk_synth_leaves_backend_careervp_intact` — the real call path,
   through an actual CDK-synth test's own helper.

Full real-synth coverage of all eight CDK-synth files is not duplicated here:
`tests/infrastructure/test_p02_billing_reconcile_entrypoint.py` needs infra's
`careervp` and then the backend's `careervp.handlers` in the same test, so it
already fails if any file in that directory leaks.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest

from tests.import_isolation import BACKEND_SRC, INFRA_SRC, backend_careervp, careervp_root, infra_careervp

TESTS_ROOT = Path(__file__).resolve().parents[1]


def _mutates_sys_modules(tree: ast.AST) -> list[str]:
    """Return a description of every `sys.modules` mutation in `tree`."""
    offenders: list[str] = []
    for node in ast.walk(tree):
        # sys.modules.pop(...)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'pop'
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == 'modules'
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == 'sys'
        ):
            offenders.append(f'line {node.lineno}: sys.modules.pop(...)')
        # del sys.modules[...]
        if isinstance(node, ast.Delete):
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Attribute)
                    and target.value.attr == 'modules'
                    and isinstance(target.value.value, ast.Name)
                    and target.value.value.id == 'sys'
                ):
                    offenders.append(f'line {node.lineno}: del sys.modules[...]')
    return offenders


@pytest.mark.static
@pytest.mark.parametrize('test_file', sorted(TESTS_ROOT.rglob('test_*.py')), ids=lambda p: str(p.relative_to(TESTS_ROOT)))
def test_no_unrestored_sys_modules_eviction(test_file: Path) -> None:
    """No test file may evict from `sys.modules` by hand.

    Evicting is fine; evicting without restoring is what broke the suite. The
    only place allowed to do it is `tests/import_isolation.py`, which restores
    in a `finally`. Everything else goes through `careervp_root()`.
    """
    offenders = _mutates_sys_modules(ast.parse(test_file.read_text()))
    assert not offenders, (
        f'{test_file.relative_to(TESTS_ROOT)} mutates sys.modules directly: {offenders}. '
        'Use tests.import_isolation.careervp_root() / infra_careervp() / backend_careervp() '
        'instead — a hand-rolled eviction that does not restore in a finally pins '
        "sys.modules['careervp'] to the wrong package for the rest of the process "
        '(see this module docstring).'
    )


def test_careervp_root_round_trips_to_infra_and_back() -> None:
    """After an infra block, the backend's `careervp` owns the name again."""
    before_file = importlib.import_module('careervp').__file__
    before_path = list(sys.path)
    assert before_file is not None and before_file.startswith(BACKEND_SRC), (
        f'precondition: tests/conftest.py should leave the backend careervp cached, got {before_file!r}'
    )

    with infra_careervp():
        inside = importlib.import_module('careervp')
        assert inside.__file__ is not None and inside.__file__.startswith(INFRA_SRC), (
            f'careervp_root(INFRA_SRC) did not bind infra package, got {inside.__file__!r}'
        )
        assert sys.path[0] == INFRA_SRC, f'infra root should lead sys.path inside the block, got {sys.path[0]!r}'

    after = importlib.import_module('careervp')
    assert after.__file__ == before_file, f'backend careervp not restored: {before_file!r} -> {after.__file__!r}'
    assert sys.path == before_path, 'sys.path not restored after the block'
    # The exact failure the bug produced.
    importlib.import_module('careervp.handlers.vpr_worker_handler')


def test_careervp_root_round_trips_to_backend_and_back() -> None:
    """The mirror direction restores too, including from inside an infra block."""
    with infra_careervp():
        with backend_careervp():
            inner = importlib.import_module('careervp')
            assert inner.__file__ is not None and inner.__file__.startswith(BACKEND_SRC), (
                f'careervp_root(BACKEND_SRC) did not bind backend package, got {inner.__file__!r}'
            )
        restored_to_infra = importlib.import_module('careervp')
        assert restored_to_infra.__file__ is not None and restored_to_infra.__file__.startswith(INFRA_SRC), (
            'nested backend block should restore the enclosing infra block, got ' + repr(restored_to_infra.__file__)
        )

    outer = importlib.import_module('careervp')
    assert outer.__file__ is not None and outer.__file__.startswith(BACKEND_SRC)


def test_careervp_root_restores_on_exception() -> None:
    """A test that raises inside the block must not leak the switch."""
    before_file = importlib.import_module('careervp').__file__
    before_path = list(sys.path)

    with pytest.raises(RuntimeError, match='forced'):
        with careervp_root(INFRA_SRC):
            importlib.import_module('careervp.naming_utils')
            raise RuntimeError('forced')

    assert importlib.import_module('careervp').__file__ == before_file, 'careervp not restored after an exception'
    assert sys.path == before_path, 'sys.path not restored after an exception'
    importlib.import_module('careervp.handlers.vpr_worker_handler')


def test_real_cdk_synth_leaves_backend_careervp_intact() -> None:
    """The end-to-end shape of the original bug, through a real synth helper.

    `test_k9_artifact_cleanup_env._all_resources()` is the exact function that
    produced the confirmed minimal reproduction:

        uv run pytest tests/infrastructure/test_k9_artifact_cleanup_env.py \
                      tests/infrastructure/test_p02_billing_reconcile_entrypoint.py

    used to fail with `ModuleNotFoundError: No module named 'careervp.handlers'`.
    """
    k9 = importlib.import_module('tests.infrastructure.test_k9_artifact_cleanup_env')
    before_file = importlib.import_module('careervp').__file__

    resources = k9._all_resources()
    assert resources, 'precondition: the synth helper should return CDK resources'

    after = importlib.import_module('careervp')
    assert after.__file__ == before_file, (
        f'a real CDK synth left careervp bound to {after.__file__!r} instead of {before_file!r} — the contamination this module exists to prevent'
    )
    importlib.import_module('careervp.handlers.vpr_worker_handler')
