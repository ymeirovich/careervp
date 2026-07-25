"""RED infrastructure contract for P-15 money-path Scan removal."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

from aws_cdk import App, Environment, NestedStack
from aws_cdk.assertions import Template

_BILLING_CONSTRUCT_ID = 'BillingLambda'
_BILLING_FUNCTION_NAME = 'careervp-billing-lambda-dev'
_BILLING_HANDLER = 'careervp.handlers.billing_handler.handler'
_SCAN_ACTION = 'dynamodb:Scan'

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')


def _all_resources() -> dict[str, dict[str, Any]]:
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
    return {logical_id: resource for template in templates for logical_id, resource in template.to_json().get('Resources', {}).items()}


def _role_logical_id(role_value: Any) -> str:
    if not isinstance(role_value, dict):
        raise AssertionError(f'{_BILLING_CONSTRUCT_ID} must reference an IAM role by Fn::GetAtt')
    get_att = role_value.get('Fn::GetAtt')
    if not isinstance(get_att, list) or not get_att:
        raise AssertionError(f'{_BILLING_CONSTRUCT_ID} must reference an IAM role by Fn::GetAtt')
    return str(get_att[0])


def _statement_actions(document: dict[str, Any]) -> set[str]:
    actions: set[str] = set()
    for statement in document.get('Statement', []):
        value = statement.get('Action', [])
        if isinstance(value, str):
            actions.add(value)
        else:
            actions.update(str(action) for action in value)
    return actions


def _role_policy_actions(
    resources: dict[str, dict[str, Any]],
    role_logical_id: str,
) -> set[str]:
    actions: set[str] = set()
    role = resources[role_logical_id]
    for policy in role.get('Properties', {}).get('Policies', []) or []:
        actions.update(_statement_actions(policy.get('PolicyDocument', {})))

    for resource in resources.values():
        if resource.get('Type') != 'AWS::IAM::Policy':
            continue
        properties = resource.get('Properties', {})
        attached_roles = properties.get('Roles', []) or []
        if {'Ref': role_logical_id} not in attached_roles:
            continue
        actions.update(_statement_actions(properties.get('PolicyDocument', {})))
    return actions


def test_p15_iam_money_path_has_no_scan_permission() -> None:
    """AC-P15-1: BillingLambda's execution role must not permit dynamodb:Scan."""
    resources = _all_resources()
    billing_functions = {
        logical_id: resource
        for logical_id, resource in resources.items()
        if resource.get('Type') == 'AWS::Lambda::Function' and resource.get('Properties', {}).get('FunctionName') == _BILLING_FUNCTION_NAME
    }
    assert len(billing_functions) == 1, (
        f'AC-P15-1 expected exactly one {_BILLING_CONSTRUCT_ID} ({_BILLING_FUNCTION_NAME}), found {sorted(billing_functions)}'
    )
    logical_id, billing_function = next(iter(billing_functions.items()))
    assert billing_function['Properties']['Handler'] == _BILLING_HANDLER, f'AC-P15-1 {logical_id} is not the billing/webhook money-path handler'
    role_logical_id = _role_logical_id(billing_function['Properties']['Role'])
    actions = _role_policy_actions(resources, role_logical_id)

    assert _SCAN_ACTION not in actions, (
        f'AC-P15-1 {_BILLING_CONSTRUCT_ID} ({logical_id}) role {role_logical_id} still permits {_SCAN_ACTION}: {sorted(actions)}'
    )
