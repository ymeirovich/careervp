"""P-02 integration contract for the scheduled billing-reconcile entrypoint."""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Template

_BILLING_RECONCILE_FUNCTION_NAME = 'careervp-billing-reconcile-lambda-dev'
_SCHEDULE_EVENT = {'detail': {'action': 'reconcile_subscriptions'}}

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')

ReconcileEntrypoint = Callable[[dict[str, Any], Any], dict[str, Any]]


def _configured_handler() -> str:
    if INFRA_SRC not in sys.path:
        sys.path.insert(0, INFRA_SRC)

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


def _resolve_configured_entrypoint(handler: str) -> ReconcileEntrypoint:
    module_name, separator, attribute_name = handler.rpartition('.')
    assert separator and module_name and attribute_name, f'P-02 synthesized an invalid Lambda Handler string: {handler!r}'

    module = _import_configured_module(module_name, handler)
    configured_entrypoint: Any = getattr(module, attribute_name, None)
    assert callable(configured_entrypoint), (
        f'P-02 configured Handler {handler!r} cannot run: module {module_name!r} has no callable attribute {attribute_name!r}'
    )
    return cast(ReconcileEntrypoint, configured_entrypoint)


@mock_aws
def test_p02_reconcile_runs_via_configured_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invoke the exact synthesized Handler with the schedule's exact event."""
    table_name = 'careervp-p02-users-table-test'
    monkeypatch.setenv('TABLE_NAME', table_name)
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.wait_until_exists()

    configured_entrypoint = _resolve_configured_entrypoint(_configured_handler())
    lambda_context = SimpleNamespace(
        function_name=_BILLING_RECONCILE_FUNCTION_NAME,
        memory_limit_in_mb=256,
        invoked_function_arn=f'arn:aws:lambda:us-east-1:788159322332:function:{_BILLING_RECONCILE_FUNCTION_NAME}',
        aws_request_id='p02-request-id',
    )
    result = configured_entrypoint(_SCHEDULE_EVENT, lambda_context)

    assert result == {'status': 'ok', 'checked': 0, 'updated': 0, 'errors': 0}
