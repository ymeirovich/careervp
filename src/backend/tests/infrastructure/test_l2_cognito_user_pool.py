"""L2.1 infrastructure tests for Cognito User Pool resources."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("JSII_RUNTIME_PACKAGE_CACHE", "/tmp/jsii-cache")

try:
    from aws_cdk import App, Environment
    from aws_cdk.assertions import Match, Template

    CDK_AVAILABLE = True
except Exception:
    CDK_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CDK_AVAILABLE, reason="aws-cdk not available")

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_DIR = REPO_ROOT / "infra"
INFRA_SRC = str(INFRA_DIR)


def _template() -> Template:
    if INFRA_SRC not in sys.path:
        sys.path.insert(0, INFRA_SRC)

    from careervp.naming_utils import NamingUtils
    from careervp.service_stack import ServiceStack

    app = App()
    naming = NamingUtils(environment="test", region="us-east-1", account_id="123456789012")
    stack = ServiceStack(
        scope=app,
        id=naming.stack_id("crud"),
        env=Environment(account="123456789012", region="us-east-1"),
        is_production_env=False,
        naming=naming,
        stack_feature="crud",
    )
    return Template.from_stack(stack)


def test_user_pool_created() -> None:
    template = _template()
    template.resource_count_is("AWS::Cognito::UserPool", 1)


def test_user_pool_password_policy_and_email_sign_in() -> None:
    template = _template()
    template.has_resource_properties(
        "AWS::Cognito::UserPool",
        {
            "AutoVerifiedAttributes": Match.array_with(["email"]),
            "UsernameAttributes": Match.array_with(["email"]),
            "Policies": {
                "PasswordPolicy": {
                    "MinimumLength": 8,
                    "RequireLowercase": True,
                    "RequireNumbers": True,
                    "RequireUppercase": True,
                    "RequireSymbols": False,
                }
            },
        },
    )


def test_user_pool_client_configured_without_secret() -> None:
    template = _template()
    template.has_resource_properties(
        "AWS::Cognito::UserPoolClient",
        {
            "GenerateSecret": False,
            "ExplicitAuthFlows": Match.array_with(
                [
                    "ALLOW_USER_SRP_AUTH",
                    "ALLOW_REFRESH_TOKEN_AUTH",
                ]
            ),
            "AccessTokenValidity": 60,
            "IdTokenValidity": 60,
            "RefreshTokenValidity": 43200,
        },
    )


def test_user_pool_domain_created() -> None:
    template = _template()
    template.has_resource_properties(
        "AWS::Cognito::UserPoolDomain",
        {
            "Domain": Match.string_like_regexp("^careervp-test"),
        },
    )


def test_stack_outputs_include_user_pool_id_and_client_id() -> None:
    template = _template()
    outputs = template.find_outputs("*")
    output_names = set(outputs.keys())
    assert "UserPoolId" in output_names
    assert "ClientId" in output_names
