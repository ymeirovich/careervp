"""P-02 synth contract for the billing-reconcile Lambda entrypoint."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Template

from tests.import_isolation import careervp_root

_BILLING_RECONCILE_FUNCTION_NAME = 'careervp-billing-reconcile-lambda-dev'

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')


def _configured_handler() -> str:
    # This test is the one that needs BOTH `careervp` packages in sequence:
    # infra's to synthesize the stack, then the backend's to import the
    # Handler string the stack points at. careervp_root() confines the infra
    # half to this block, so the import below is back on the backend's package.
    with careervp_root(INFRA_SRC):
        from careervp.naming_utils import NamingUtils  # type: ignore[import-not-found]
        from careervp.service_stack import ServiceStack  # type: ignore[import-not-found]

        app = App()
        naming = NamingUtils(
            environment='dev',
            region='us-east-1',
            account_id='788159322332',
        )
        stack = ServiceStack(
            scope=app,
            id=naming.stack_id('crud'),
            env=Environment(account='788159322332', region='us-east-1'),
            is_production_env=False,
            naming=naming,
            stack_feature='crud',
        )
        templates = [Template.from_stack(stack)]
        templates.extend(Template.from_stack(construct) for construct in stack.node.find_all() if isinstance(construct, NestedStack))
        functions = {
            logical_id: resource
            for template in templates
            for logical_id, resource in template.find_resources('AWS::Lambda::Function').items()
            if resource.get('Properties', {}).get('FunctionName') == _BILLING_RECONCILE_FUNCTION_NAME
        }
    assert len(functions) == 1, f'P-02 expected exactly one {_BILLING_RECONCILE_FUNCTION_NAME}, found {sorted(functions)}'
    handler = next(iter(functions.values())).get('Properties', {}).get('Handler')
    assert isinstance(handler, str), f'P-02 {_BILLING_RECONCILE_FUNCTION_NAME} Handler must be a string, got {handler!r}'
    return handler


def _import_configured_module(module_name: str, handler: str) -> ModuleType:
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        pytest.fail(f'P-02 configured Handler {handler!r} has an unimportable module {module_name!r}: {exc}', pytrace=False)


# Quarantined xfail(strict=False) from handoff-01 Step 1b/6b removed in
# handoff 02: the contamination it described is fixed, not merely reclassified.
# _configured_handler() now confines infra's `careervp` to a careervp_root()
# block, so the backend's package is back in sys.modules before
# _import_configured_module() runs — regardless of whether any CDK-synth test
# ran earlier in the process. The order-dependence that forced strict=False is
# gone, so the marker is gone rather than flipped to strict=True.
# Regression cover: tests/regression/test_careervp_import_isolation.py.
def test_p02_reconcile_configured_entrypoint_resolves() -> None:
    """The exact synthesized Handler must resolve to a callable attribute."""
    handler = _configured_handler()
    module_name, separator, attribute_name = handler.rpartition('.')
    assert separator and module_name and attribute_name, f'P-02 synthesized an invalid Lambda Handler string: {handler!r}'

    module = _import_configured_module(module_name, handler)
    configured_entrypoint: Any = getattr(module, attribute_name, None)

    assert callable(configured_entrypoint), (
        f'P-02 configured Handler {handler!r} does not resolve: module {module_name!r} has no callable attribute {attribute_name!r}'
    )
