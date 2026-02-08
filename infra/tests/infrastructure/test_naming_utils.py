from __future__ import annotations

from careervp.naming_utils import NamingUtils


def test_lambda_naming_convention() -> None:
    """NamingUtils must emit kebab-case lambda names with env suffix."""
    naming = NamingUtils(
        environment="dev", region="us-east-1", account_id="123456789012"
    )
    lambda_name = naming.lambda_name("company-research")
    assert lambda_name == "careervp-company-research-lambda-dev"


def test_role_naming_convention() -> None:
    """Role names must follow careervp-role-{service}-{feature}-{env}."""
    naming = NamingUtils(
        environment="staging", region="us-east-1", account_id="123456789012"
    )
    role_name = naming.role_name("lambda", "company-research")
    assert role_name == "careervp-role-lambda-company-research-staging"
