"""P-23 canary/rollback infrastructure contract tests.

scope_lock_clause: P-23

The P-04 handler-auth cleanup must have a fast Lambda rollback path before it
can land.  These tests synthesize every template because API-route functions
span the parent and the AI-assist nested stack.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

try:
    from aws_cdk import App, Environment, NestedStack
    from aws_cdk.assertions import Template

    CDK_AVAILABLE = True
except Exception:  # pragma: no cover - environment guard
    CDK_AVAILABLE = False

from careervp.logic.identity_resolver import (
    IdentityResolver,
    LinkDecision,
    ResolvedIdentity,
)

pytestmark = pytest.mark.skipif(not CDK_AVAILABLE, reason='aws-cdk not available')

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')
REVERT_RUNBOOK = REPO_ROOT / 'docs' / 'db-redesign' / 'code' / 'code-analysis' / 'project' / 'runbooks' / 'p23-canary-rollback-runbook.md'

# Public/API-route Lambda functions, including the AI-assist route that lives
# in its own nested stack.  Workers deliberately do not appear here.
API_ROUTE_FUNCTION_NAMES = frozenset(
    {
        'careervp-ai-assist-lambda-dev',
        'careervp-auth-api-lambda-dev',
        'careervp-billing-lambda-dev',
        'careervp-company-research-lambda-dev',
        'careervp-cover-letter-api-lambda-dev',
        'careervp-cover-letter-status-lambda-dev',
        'careervp-cv-parser-lambda-dev',
        'careervp-cvtailor-lambda-dev',
        'careervp-error-report-lambda-dev',
        'careervp-export-lambda-dev',
        'careervp-gap-api-lambda-dev',
        'careervp-health-api-lambda-dev',
        'careervp-interview-prep-api-lambda-dev',
        'careervp-interview-prep-status-lambda-dev',
        'careervp-job-api-lambda-dev',
        'careervp-application-api-lambda-dev',
        'careervp-user-api-lambda-dev',
        'careervp-vpr-status-lambda-dev',
        'careervp-vpr-submit-lambda-dev',
    }
)


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


@pytest.fixture(scope='module')
def synthesized_resources() -> dict[str, dict[str, Any]]:
    """Return resources from the parent plus every nested stack template."""
    stack = _dev_stack()
    templates = [Template.from_stack(stack)]
    templates.extend(Template.from_stack(construct) for construct in stack.node.find_all() if isinstance(construct, NestedStack))
    resources: dict[str, dict[str, Any]] = {}
    for template in templates:
        resources.update(template.to_json().get('Resources', {}))
    return resources


def _referenced_logical_id(value: Any) -> str | None:
    """Read the target logical id from a CloudFormation Ref/GetAtt value."""
    if not isinstance(value, dict):
        return None
    ref = value.get('Ref')
    if isinstance(ref, str):
        return ref
    get_att = value.get('Fn::GetAtt')
    if isinstance(get_att, list) and get_att and isinstance(get_att[0], str):
        return get_att[0]
    return None


def _api_route_functions(resources: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Map each P-23 API-route function's physical name to its logical id."""
    functions = {
        logical_id: resource.get('Properties', {}) for logical_id, resource in resources.items() if resource.get('Type') == 'AWS::Lambda::Function'
    }
    by_name = {
        props.get('FunctionName'): logical_id for logical_id, props in functions.items() if props.get('FunctionName') in API_ROUTE_FUNCTION_NAMES
    }
    assert set(by_name) == API_ROUTE_FUNCTION_NAMES, (
        f'the P-23 route-Lambda inventory drifted; update the canary coverage explicitly (found {sorted(by_name)})'
    )
    return by_name


def test_p23_api_lambdas_have_alias_and_version(synthesized_resources: dict[str, dict[str, Any]]) -> None:
    """AC-P23-1: every API Lambda routes deployments through a published stable alias."""
    functions = _api_route_functions(synthesized_resources)
    aliases = {logical_id: resource for logical_id, resource in synthesized_resources.items() if resource.get('Type') == 'AWS::Lambda::Alias'}
    versions = {
        logical_id: resource.get('Properties', {})
        for logical_id, resource in synthesized_resources.items()
        if resource.get('Type') == 'AWS::Lambda::Version'
    }

    aliased_functions = {
        _referenced_logical_id(resource.get('Properties', {}).get('FunctionName')): logical_id for logical_id, resource in aliases.items()
    }
    assert set(aliased_functions) == set(functions.values()), (
        'every public/API-route Lambda must have exactly one stable deployment alias '
        f'(found aliases for {sorted(function_id for function_id in aliased_functions if function_id)})'
    )
    for function_id, alias_id in aliased_functions.items():
        assert function_id is not None
        version_id = _referenced_logical_id(aliases[alias_id].get('Properties', {}).get('FunctionVersion'))
        assert version_id in versions, f'alias {alias_id} must target a published Lambda Version'
        assert _referenced_logical_id(versions[version_id].get('FunctionName')) == function_id


def test_p23_codedeploy_groups_exist_for_api_lambdas(synthesized_resources: dict[str, dict[str, Any]]) -> None:
    """AC-P23-1: each API alias uses CodeDeploy's canary rollout and alarm rollback."""
    functions = _api_route_functions(synthesized_resources)
    aliases = {logical_id: resource for logical_id, resource in synthesized_resources.items() if resource.get('Type') == 'AWS::Lambda::Alias'}
    deployment_groups = [
        resource.get('Properties', {}) for resource in synthesized_resources.values() if resource.get('Type') == 'AWS::CodeDeploy::DeploymentGroup'
    ]

    assert len(aliases) == len(functions)
    assert len(deployment_groups) == len(functions)
    for alias in aliases.values():
        update_policy = alias.get('UpdatePolicy', {}).get('CodeDeployLambdaAliasUpdate', {})
        assert update_policy, 'the stable alias must delegate updates to CodeDeploy'
    for group in deployment_groups:
        assert group.get('DeploymentConfigName') == 'CodeDeployDefault.LambdaCanary10Percent5Minutes'
        assert group.get('AutoRollbackConfiguration', {}).get('Enabled') is True
        assert set(group.get('AutoRollbackConfiguration', {}).get('Events', [])) == {
            'DEPLOYMENT_FAILURE',
            'DEPLOYMENT_STOP_ON_ALARM',
            'DEPLOYMENT_STOP_ON_REQUEST',
        }
        assert group.get('AlarmConfiguration', {}).get('Enabled') is True
        assert group.get('AlarmConfiguration', {}).get('Alarms'), 'canary rollback needs alarms'


def test_p23_rollback_alarms_include_auth_resolver_failure(synthesized_resources: dict[str, dict[str, Any]]) -> None:
    """AC-P23-1: rollback observes resolver outcomes, not an aggregate 401-rate."""
    alarms = {
        logical_id: resource.get('Properties', {})
        for logical_id, resource in synthesized_resources.items()
        if resource.get('Type') == 'AWS::CloudWatch::Alarm'
    }
    resolver_alarm_ids = {
        logical_id
        for logical_id, props in alarms.items()
        if isinstance(props.get('MetricName'), str) and props['MetricName'] in {'AuthResolverFailure', 'AuthResolverStepUpRequired'}
    }
    assert len(resolver_alarm_ids) == 2, 'P-23 needs distinct resolver-failure and step-up outcome alarms'
    assert not any('401' in str(props.get('MetricName', '')) for props in alarms.values()), (
        'an aggregate 401-rate is not a resolver-correctness signal'
    )

    resolver_alarm_markers = {
        'P23AuthResolverFailureAlarm',
        'P23AuthResolverStepUpRequiredAlarm',
    }
    for resource in synthesized_resources.values():
        if resource.get('Type') != 'AWS::CodeDeploy::DeploymentGroup':
            continue
        configured_alarms = repr(resource.get('Properties', {}).get('AlarmConfiguration', {}).get('Alarms', []))
        for resolver_alarm_marker in resolver_alarm_markers:
            assert resolver_alarm_marker in configured_alarms, 'each canary must roll back on resolver outcome alarms'


def test_p23_revert_runbook_distinguishes_lambda_from_api_gateway() -> None:
    """AC-P23-2: Lambda and API Gateway configuration changes have separate revert levers."""
    text = REVERT_RUNBOOK.read_text(encoding='utf-8').lower()
    assert 'codedeploy' in text and 'alias rollback' in text
    assert 'api gateway' in text and 'stage-level' in text and 'redeploy' in text
    assert 'not a lambda-alias canary' in text


def test_p23_known_sub_synthetic_canary_resolves_expected_user_id() -> None:
    """AC-P23-1 probe: a known P-24 sub resolves to its expected internal user_id."""
    identity_map = Mock()
    identity_map.get_user_id.return_value = 'p23-known-user-id'
    resolver = IdentityResolver(identity_map=identity_map, email_lookup=lambda _email: [])

    result = resolver.resolve({'sub': 'p23-known-sub'})

    assert result == ResolvedIdentity(user_id='p23-known-user-id', decision=LinkDecision.EXISTING_MAPPING)
