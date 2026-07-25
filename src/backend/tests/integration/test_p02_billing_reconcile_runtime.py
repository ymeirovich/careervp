"""P-02/P-25 runtime regressions for scheduled billing reconciliation."""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import boto3
import httpx
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Template

from careervp.dal.subscription_repository import SubscriptionRepository
from careervp.payment_providers.interface import PaymentProviderError

_BILLING_RECONCILE_FUNCTION_NAME = 'careervp-billing-reconcile-lambda-dev'
_SCHEDULE_EVENT = {'detail': {'action': 'reconcile_subscriptions'}}
_TABLE_NAME = 'careervp-p02-runtime-users-table-test'

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')

ReconcileEntrypoint = Callable[[dict[str, Any], Any], dict[str, Any]]


def _create_exact_subscription_rows(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv('TABLE_NAME', _TABLE_NAME)
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName=_TABLE_NAME,
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
    for item in (
        {'pk': 'USER#active', 'sk': 'SUBSCRIPTION#CURRENT', 'status': 'active'},
        {'pk': 'USER#inactive', 'sk': 'SUBSCRIPTION#CURRENT', 'status': 'inactive'},
        {'pk': 'USER#other', 'sk': 'PROFILE', 'status': 'active'},
    ):
        table.put_item(Item=item)
    return dynamodb


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
    assert len(functions) == 1, f'P-25 expected exactly one {_BILLING_RECONCILE_FUNCTION_NAME}, found {sorted(functions)}'
    handler = next(iter(functions.values())).get('Properties', {}).get('Handler')
    assert isinstance(handler, str), f'P-25 {_BILLING_RECONCILE_FUNCTION_NAME} Handler must be a string, got {handler!r}'
    return handler


def _import_configured_module(module_name: str, handler: str) -> ModuleType:
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        pytest.fail(f'P-25 handler resolution failed: configured Handler {handler!r} has unimportable module {module_name!r}: {exc}', pytrace=False)


def _resolve_configured_entrypoint() -> tuple[ModuleType, ReconcileEntrypoint]:
    handler = _configured_handler()
    module_name, separator, attribute_name = handler.rpartition('.')
    assert separator and module_name and attribute_name, f'P-25 handler resolution failed: invalid synthesized Handler {handler!r}'

    module = _import_configured_module(module_name, handler)
    configured_entrypoint: Any = getattr(module, attribute_name, None)
    assert callable(configured_entrypoint), (
        f'P-25 handler resolution failed: module {module_name!r} has no callable attribute {attribute_name!r} for {handler!r}'
    )
    return module, cast(ReconcileEntrypoint, configured_entrypoint)


@mock_aws
def test_p02_scan_active_subscriptions_filters_real_moto_table(monkeypatch: pytest.MonkeyPatch) -> None:
    """A real DynamoDB scan must return only the active current subscription."""
    dynamodb = _create_exact_subscription_rows(monkeypatch)
    repository = SubscriptionRepository(table_name=_TABLE_NAME, dynamodb_resource=dynamodb)

    try:
        subscriptions = repository.scan_active_subscriptions()
    except ClientError as exc:
        error = exc.response.get('Error', {})
        pytest.fail(
            f'P-02 DynamoDB scan failed: {error.get("Code", "unknown")} — {error.get("Message", str(exc))}',
            pytrace=False,
        )

    assert [item['pk'] for item in subscriptions] == ['USER#active']


@mock_aws
def test_p25_active_reconcile_uses_configured_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """The scheduled entrypoint must reconcile one active row through MockProvider."""
    _create_exact_subscription_rows(monkeypatch)
    monkeypatch.setenv('PAYMENT_PROVIDER', 'mock')

    external_http_calls: list[str] = []

    def fail_external_http(*args: Any, **kwargs: Any) -> None:
        external_http_calls.append('httpx.Client')
        raise AssertionError(f'P-25 attempted an external HTTP call: args={args!r}, kwargs={kwargs!r}')

    monkeypatch.setattr(httpx, 'Client', fail_external_http)
    module, configured_entrypoint = _resolve_configured_entrypoint()
    monkeypatch.setattr(module, '_reconciliation_service', None)
    lambda_context = SimpleNamespace(
        function_name=_BILLING_RECONCILE_FUNCTION_NAME,
        memory_limit_in_mb=256,
        invoked_function_arn=f'arn:aws:lambda:us-east-1:788159322332:function:{_BILLING_RECONCILE_FUNCTION_NAME}',
        aws_request_id='p25-active-reconcile-request-id',
    )

    try:
        result = configured_entrypoint(_SCHEDULE_EVENT, lambda_context)
    except ClientError as exc:
        error = exc.response.get('Error', {})
        pytest.fail(
            f'P-25 active reconcile failed at DynamoDB scan layer: {error.get("Code", "unknown")} — {error.get("Message", str(exc))}',
            pytrace=False,
        )
    except NotImplementedError as exc:
        pytest.fail(f'P-25 active reconcile failed at configured-provider layer: {exc}', pytrace=False)
    except PaymentProviderError as exc:
        pytest.fail(f'P-25 active reconcile failed at provider configuration layer: {exc.code} — {exc}', pytrace=False)

    assert external_http_calls == [], f'P-25 active reconcile made external HTTP calls: {external_http_calls}'
    assert result == {'status': 'ok', 'checked': 1, 'updated': 0, 'errors': 0}
