"""P-07 Cognito hardening and P-11 WAF rate-rule contract tests.

scope_lock_clause: P-07, P-11
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

try:
    from aws_cdk import App, Environment, Stack
    from aws_cdk import aws_apigateway as apigateway
    from aws_cdk.assertions import Template

    CDK_AVAILABLE = True
except Exception:  # pragma: no cover - environment guard
    CDK_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CDK_AVAILABLE, reason='aws-cdk not available')

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')
FRONTEND_ROOT = REPO_ROOT / 'src' / 'frontend'
SCOPE_INVENTORY = FRONTEND_ROOT / 'auth-scope-usage-inventory.json'
EXPECTED_RATE_LIMITS = {'dev': 2_000, 'staging': 1_500, 'prod': 1_000}


def _load_infra_module(module_name: str) -> Any:
    if INFRA_SRC not in sys.path:
        sys.path.insert(0, INFRA_SRC)
    return importlib.import_module(module_name)


def _cognito_template() -> Template:
    cognito_module = _load_infra_module('careervp.cognito_construct')
    app = App()
    stack = Stack(
        app,
        'CareerVpCognitoHardeningDev',
        env=Environment(account='123456789012', region='us-east-1'),
    )
    cognito_module.CognitoConstruct(stack, 'CognitoConstruct', 'dev')
    return Template.from_stack(stack)


def _single_resource(template: Template, resource_type: str) -> dict[str, Any]:
    resources = template.find_resources(resource_type)
    assert len(resources) == 1, f'expected one {resource_type}, found {sorted(resources)}'
    return dict(next(iter(resources.values())))


def test_p07_frontend_scope_usage_inventory_complete() -> None:
    """AC-P07-1: every browser-side admin-scope operation has a disposition."""
    inventory = json.loads(SCOPE_INVENTORY.read_text(encoding='utf-8'))
    entries = {entry['operation']: entry for entry in inventory['operations']}
    expected_operations = {
        'signin.user.admin',
        'AssociateSoftwareToken',
        'UpdateUserAttributes',
        'ChangePassword',
        'TOTP enrollment',
    }
    assert set(entries) == expected_operations

    allowed_classifications = {'none', 'backend_proxy', 'temporarily_allowed'}
    source_files = [
        path
        for path in FRONTEND_ROOT.rglob('*')
        if path.suffix in {'.ts', '.tsx'} and not {'node_modules', 'dist', 'playwright-report'}.intersection(path.parts) and 'tests' not in path.parts
    ]
    sources = {str(path.relative_to(FRONTEND_ROOT)): path.read_text(encoding='utf-8') for path in source_files}

    for operation, entry in entries.items():
        classification = entry['classification']
        assert classification in allowed_classifications, f'{operation} has invalid classification {classification!r}'
        matches = {
            path for path, source in sources.items() if any(re.search(pattern, source, flags=re.IGNORECASE) for pattern in entry['source_patterns'])
        }
        recorded_locations = set(entry['locations'])
        assert matches == recorded_locations, f'{operation} inventory is stale: actual={sorted(matches)}, recorded={sorted(recorded_locations)}'
        if matches:
            assert classification != 'none', f'{operation} is live but classified none'
        if classification == 'temporarily_allowed':
            assert entry.get('migration_plan'), f'{operation} needs a migration plan before COGNITO_ADMIN removal'


def test_p07_app_client_supports_code_pkce_before_implicit_removed() -> None:
    """AC-P07-2: authorization code and implicit coexist during the soak window."""
    client = _single_resource(_cognito_template(), 'AWS::Cognito::UserPoolClient')
    properties = client['Properties']
    assert properties['GenerateSecret'] is False, 'PKCE SPA client must remain public'
    assert set(properties['AllowedOAuthFlows']) >= {'code', 'implicit'}


def test_p07_public_spa_client_has_no_cognito_admin_after_cutover() -> None:
    """AC-P07-1/3: the phase switch makes admin-scope removal an executable gate."""
    cognito_module = _load_infra_module('careervp.cognito_construct')
    phase = cognito_module.P07_AUTH_MIGRATION_PHASE
    assert phase in {'migration_window', 'cutover_complete'}

    client = _single_resource(_cognito_template(), 'AWS::Cognito::UserPoolClient')
    scopes = set(client['Properties']['AllowedOAuthScopes'])
    if phase == 'cutover_complete':
        assert 'aws.cognito.signin.user.admin' not in scopes
        assert 'implicit' not in client['Properties']['AllowedOAuthFlows']
    else:
        assert 'aws.cognito.signin.user.admin' in scopes
        assert 'implicit' in client['Properties']['AllowedOAuthFlows']


def test_p07_mfa_rollout_has_grace_state() -> None:
    """AC-P07-4: TOTP enrollment starts OPTIONAL before later enforcement."""
    user_pool = _single_resource(_cognito_template(), 'AWS::Cognito::UserPool')
    properties = user_pool['Properties']
    assert properties['MfaConfiguration'] == 'OPTIONAL'
    assert 'SOFTWARE_TOKEN_MFA' in properties['EnabledMfas']
    assert properties['UserPoolAddOns']['AdvancedSecurityMode'] == 'ENFORCED'


@pytest.mark.parametrize(('environment', 'expected_limit'), EXPECTED_RATE_LIMITS.items())
def test_p11_waf_rate_rule_exists_all_envs(environment: str, expected_limit: int) -> None:
    """AC-P11-1: every environment has an API-associated, env-tuned rate rule."""
    naming_module = _load_infra_module('careervp.naming_utils')
    waf_module = _load_infra_module('careervp.waf_construct')

    app = App()
    stack = Stack(
        app,
        f'CareerVpWafRate{environment.title()}',
        env=Environment(account='123456789012', region='us-east-1'),
    )
    api = apigateway.RestApi(stack, 'ApiConstruct')
    api.root.add_method('GET')
    naming = naming_module.NamingUtils(
        environment=environment,
        region='us-east-1',
        account_id='123456789012',
    )
    waf_module.WafToApiGatewayConstruct(
        stack,
        'WafConstruct',
        api,
        naming=naming,
        feature='core-api',
    )
    template = Template.from_stack(stack)

    web_acl = _single_resource(template, 'AWS::WAFv2::WebACL')
    rate_rules = [rule for rule in web_acl['Properties']['Rules'] if 'RateBasedStatement' in rule['Statement']]
    assert len(rate_rules) == 1
    assert rate_rules[0]['Statement']['RateBasedStatement'] == {
        'AggregateKeyType': 'IP',
        'Limit': expected_limit,
    }
    assert rate_rules[0]['Action'] == {'Block': {}}

    association = _single_resource(template, 'AWS::WAFv2::WebACLAssociation')
    assert association['Properties']['ResourceArn']
    assert association['Properties']['WebACLArn']
