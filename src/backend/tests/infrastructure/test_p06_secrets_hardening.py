"""P-06 secrets-out-of-Lambda-env infrastructure contract tests.

scope_lock_clause: P-06
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

try:
    from aws_cdk import App, Environment, NestedStack
    from aws_cdk.assertions import Template

    CDK_AVAILABLE = True
except Exception:  # pragma: no cover - environment guard
    CDK_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CDK_AVAILABLE, reason='aws-cdk not available')

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')

# The bare (pre-P-06) env-var names that historically carried CDK-resolved
# key material directly. Their mere presence is the vulnerability: CDK's
# `value_for_string_parameter` makes CloudFormation inject the real secret
# value into these keys at deploy time, so they must never be set at all —
# only the *_SSM_PARAM name-only siblings below are allowed (AC-P06-1).
PLAINTEXT_SECRET_ENV_VARS = ('JWT_PRIVATE_KEY', 'JWT_PUBLIC_KEY')

# The env-var names that must carry an SSM parameter *name*, not a value.
SECRET_REFERENCE_ENV_VARS = (
    'JWT_PRIVATE_KEY_SSM_PARAM',
    'JWT_PUBLIC_KEY_SSM_PARAM',
    'PAYMENT_PROVIDER_WEBHOOK_SECRET_SSM_PARAM',
    'PAYMENT_PROVIDER_WEBHOOK_SECRET_PREVIOUS_SSM_PARAM',
)

# Substrings identifying the P-06 secret parameters, to scope the IAM check
# to the grants this clause is actually about (not just "any ssm grant").
SECRET_PARAMETER_NAME_FRAGMENTS = (
    'jwt-private-key',
    'jwt-public-key',
    'payment-provider-webhook-secret',
)

SECRET_ACTIONS = {'ssm:GetParameter', 'secretsmanager:GetSecretValue'}


def _dev_stack() -> Any:
    if INFRA_SRC not in sys.path:
        sys.path.insert(0, INFRA_SRC)

    from careervp.naming_utils import NamingUtils  # type: ignore[import-not-found]
    from careervp.service_stack import ServiceStack  # type: ignore[import-not-found]

    app = App()
    naming = NamingUtils(environment='dev', region='us-east-1', account_id='788159322332')
    return ServiceStack(
        scope=app,
        id=naming.stack_id('crud'),
        env=Environment(account='788159322332', region='us-east-1'),
        is_production_env=False,
        naming=naming,
        stack_feature='crud',
    )


def _all_resources(stack: Any) -> dict[str, Any]:
    templates = [Template.from_stack(stack)]
    templates.extend(Template.from_stack(construct) for construct in stack.node.find_all() if isinstance(construct, NestedStack))
    return {logical_id: resource for template in templates for logical_id, resource in template.to_json().get('Resources', {}).items()}


def _lambda_env_variables(resources: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Map Lambda logical id -> its Environment.Variables dict."""
    out: dict[str, dict[str, str]] = {}
    for logical_id, resource in resources.items():
        if resource.get('Type') != 'AWS::Lambda::Function':
            continue
        variables = resource.get('Properties', {}).get('Environment', {}).get('Variables', {})
        out[logical_id] = variables
    return out


def test_p06_lambda_env_has_no_plaintext_jwt_key_material() -> None:
    """AC-P06-1: no Lambda carries the bare JWT_PRIVATE_KEY/JWT_PUBLIC_KEY env vars.

    Those names are how CDK's `value_for_string_parameter` used to inject the
    actual resolved key value into the Lambda's live environment at deploy
    time. Only the *_SSM_PARAM name-only siblings are allowed post-P-06.
    """
    stack = _dev_stack()
    resources = _all_resources(stack)

    for logical_id, variables in _lambda_env_variables(resources).items():
        for banned in PLAINTEXT_SECRET_ENV_VARS:
            assert banned not in variables, (
                f'{logical_id} sets {banned} directly — this is the pre-P-06 '
                'pattern that lets CloudFormation resolve the actual key '
                'value into the Lambda environment at deploy time'
            )


def test_p06_secret_env_values_are_references_only() -> None:
    """AC-P06-1/AC-P06-3 evidence: JWT/webhook env vars are parameter paths, not values."""
    stack = _dev_stack()
    resources = _all_resources(stack)

    found_any = False
    param_path_re = re.compile(r'^/careervp/dev/[a-z0-9-]+$')

    for logical_id, variables in _lambda_env_variables(resources).items():
        for env_var_name in SECRET_REFERENCE_ENV_VARS:
            if env_var_name not in variables:
                continue
            found_any = True
            value = variables[env_var_name]
            assert isinstance(value, str), f'{logical_id}.{env_var_name} must be a literal parameter path string, got {type(value)}'
            assert '{{resolve:' not in value, (
                f'{logical_id}.{env_var_name} is a CloudFormation dynamic reference '
                '({{resolve:...}}) that resolves to the secret value at deploy time — '
                'must be a bare parameter name fetched at runtime instead'
            )
            assert param_path_re.match(value), f'{logical_id}.{env_var_name} = {value!r} does not look like an SSM parameter path (/careervp/dev/...)'

    assert found_any, 'expected at least one Lambda to carry a JWT/webhook secret reference env var'


def test_p06_iam_secret_access_is_arn_scoped() -> None:
    """AC-P06-3: JWT/webhook secret IAM grants exist and are never Resource: "*".

    Scoped to statements whose resource ARN actually names one of the P-06
    secret parameters — a pre-P-06 stack has zero such statements (the value
    was resolved by CloudFormation, not fetched by the Lambda's own role), so
    this fails on the vulnerable baseline rather than passing on some
    unrelated already-compliant grant (e.g. the Anthropic key).
    """
    stack = _dev_stack()
    resources = _all_resources(stack)

    matching_statements = []
    for logical_id, resource in resources.items():
        if resource.get('Type') not in ('AWS::IAM::Policy', 'AWS::IAM::Role'):
            continue
        props = resource.get('Properties', {})
        documents = []
        if 'PolicyDocument' in props:
            documents.append(props['PolicyDocument'])
        for inline in props.get('Policies', []) or []:
            if 'PolicyDocument' in inline:
                documents.append(inline['PolicyDocument'])

        for document in documents:
            for statement in document.get('Statement', []) or []:
                actions = statement.get('Action', [])
                actions = [actions] if isinstance(actions, str) else actions
                if not SECRET_ACTIONS.intersection(actions):
                    continue
                resource_field = statement.get('Resource', [])
                resource_field = [resource_field] if isinstance(resource_field, str) else resource_field
                rendered_resources = ' '.join(str(r) for r in resource_field)
                if not any(fragment in rendered_resources for fragment in SECRET_PARAMETER_NAME_FRAGMENTS):
                    continue
                matching_statements.append((logical_id, actions, resource_field))
                assert '*' not in resource_field, (
                    f'{logical_id} grants {actions} on the P-06 secret parameters with a wildcard Resource — secret access must be ARN-scoped'
                )

    assert matching_statements, (
        'expected at least one ARN-scoped ssm:GetParameter/secretsmanager:GetSecretValue '
        'statement referencing a jwt-private-key/jwt-public-key/payment-provider-webhook-secret '
        'parameter — found none, so nothing grants the runtime secret provider access'
    )
