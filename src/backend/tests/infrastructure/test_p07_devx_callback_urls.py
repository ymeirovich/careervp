"""P-07 (step 1.6) — devx Amplify branch must be a registered OAuth redirect target.

scope_lock_clause: P-07

Why this exists: ``cognito_construct.py`` hardcodes five callback/logout URLs for every
non-scratch environment. None of them is the ``db-redesign`` Amplify branch that devx is
verified from. Cognito rejects any ``redirect_uri`` that is not on the registered list, so
without this the very first real PKCE login on devx fails at the authorize step.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

try:
    from aws_cdk import App, Environment, Stack
    from aws_cdk.assertions import Template

    CDK_AVAILABLE = True
except Exception:  # pragma: no cover - environment guard
    CDK_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CDK_AVAILABLE, reason='aws-cdk not available')

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')

DEVX_AMPLIFY_ORIGIN = 'https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com'


def _load_infra_module(module_name: str) -> Any:
    if INFRA_SRC not in sys.path:
        sys.path.insert(0, INFRA_SRC)
    return importlib.import_module(module_name)


def _cognito_client_properties(environment: str) -> dict[str, Any]:
    cognito_module = _load_infra_module('careervp.cognito_construct')
    app = App()
    stack = Stack(
        app,
        f'CareerVpCognitoCallback{environment.title()}',
        env=Environment(account='123456789012', region='us-east-1'),
    )
    cognito_module.CognitoConstruct(stack, 'CognitoConstruct', environment)
    template = Template.from_stack(stack)
    resources = template.find_resources('AWS::Cognito::UserPoolClient')
    assert len(resources) == 1, f'expected one UserPoolClient, found {sorted(resources)}'
    return dict(next(iter(resources.values()))['Properties'])


def test_cognito_callback_urls_include_devx_amplify_branch() -> None:
    """AC-P07-5: the devx Amplify origin is a registered callback and logout URL."""
    properties = _cognito_client_properties('devx')

    assert f'{DEVX_AMPLIFY_ORIGIN}/callback' in properties['CallbackURLs'], (
        f'devx PKCE login will be rejected by Cognito: {DEVX_AMPLIFY_ORIGIN}/callback '
        f'is not registered. Registered: {sorted(properties["CallbackURLs"])}'
    )
    assert f'{DEVX_AMPLIFY_ORIGIN}/' in properties['LogoutURLs'], (
        f'devx sign-out will be rejected by Cognito: {DEVX_AMPLIFY_ORIGIN}/ is not registered. Registered: {sorted(properties["LogoutURLs"])}'
    )


def test_cognito_callback_urls_have_no_duplicates() -> None:
    """Registering the same URL twice is a config smell, not a functional failure."""
    properties = _cognito_client_properties('devx')
    for key in ('CallbackURLs', 'LogoutURLs'):
        urls = list(properties[key])
        assert len(urls) == len(set(urls)), f'{key} contains duplicates: {urls}'
