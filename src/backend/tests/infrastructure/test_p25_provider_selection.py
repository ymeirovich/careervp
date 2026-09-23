"""P-25 synth contract for devx billing provider selection."""

from __future__ import annotations

import os
import secrets
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Template

_BILLING_FUNCTION_NAMES = (
    'careervp-billing-lambda-devx',
    'careervp-billing-reconcile-lambda-devx',
)

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')


def _synthesized_lambda_resources() -> dict[str, list[Mapping[str, Any]]]:
    if INFRA_SRC not in sys.path:
        sys.path.insert(0, INFRA_SRC)

    from careervp.naming_utils import NamingUtils  # type: ignore[import-not-found]
    from careervp.service_stack import ServiceStack  # type: ignore[import-not-found]

    app = App(context={'p26_rehome_features': 'true'})
    naming = NamingUtils(
        environment='devx',
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

    resources: dict[str, list[Mapping[str, Any]]] = {function_name: [] for function_name in _BILLING_FUNCTION_NAMES}
    for template in templates:
        for resource in template.find_resources('AWS::Lambda::Function').values():
            properties = resource.get('Properties', {})
            function_name = properties.get('FunctionName')
            if function_name in resources:
                resources[function_name].append(resource)
    return resources


def test_p25_devx_billing_lambdas_configure_mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both devx billing Lambdas select MockProvider without embedding a secret."""
    generated_provider_secret = f'p25-{secrets.token_urlsafe(32)}'
    monkeypatch.setenv('STRIPE_SECRET_KEY', generated_provider_secret)
    resources = _synthesized_lambda_resources()

    for function_name in _BILLING_FUNCTION_NAMES:
        matches = resources[function_name]
        assert len(matches) == 1, f'AC-P25-1 expected exactly one {function_name}, found {len(matches)}'
        environment = matches[0].get('Properties', {}).get('Environment')
        assert isinstance(environment, dict), f'AC-P25-1 {function_name} must synthesize an Environment mapping'
        variables = environment.get('Variables')
        assert isinstance(variables, dict), f'AC-P25-1 {function_name} must synthesize an Environment.Variables mapping'

        assert variables.get('PAYMENT_PROVIDER') == 'mock', (
            f'AC-P25-1 {function_name} PAYMENT_PROVIDER must equal "mock", got {variables.get("PAYMENT_PROVIDER")!r}'
        )
        assert 'PAYMENT_PROVIDER_PLACEHOLDER' not in variables
        assert 'PAYMENT_PROVIDER_API_KEY_SSM_PARAM' not in variables
        assert 'STRIPE_SECRET_KEY' not in variables
        assert generated_provider_secret not in variables.values()
