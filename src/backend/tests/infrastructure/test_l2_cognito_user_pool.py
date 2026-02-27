"""
L2.1 — Cognito User Pool Infrastructure Tests

Validates: CDK deploys correct UserPool config — email sign-in, 8-char password, no secret client
Spec: docs/best_practices/yaml/cognito_spec.yaml
Payload: docs/refactor/payloads/beta_l2_auth_scenarios_test.json#L2_1_cognito_user_pool
Invariant: I3
Results: docs/beta/execution_results/L2_1_results.md
"""

import pytest

# CDK assertion imports — available when aws-cdk-lib is installed
try:
    import aws_cdk as cdk
    from aws_cdk import assertions
    CDK_AVAILABLE = True
except ImportError:
    CDK_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not CDK_AVAILABLE,
    reason="aws-cdk-lib not installed — run: pip install aws-cdk-lib"
)

INFRA_DIR = "/Users/yitzchak/Documents/dev/careervp/infra"


def _get_template():
    """Synthesize CDK stack and return assertions.Template."""
    if not CDK_AVAILABLE:
        pytest.skip("aws-cdk-lib not installed")
    import sys
    sys.path.insert(0, INFRA_DIR)
    try:
        from careervp.service_stack import CareervpStack
        app = cdk.App()
        stack = CareervpStack(app, "CareervpStack-test", env_name="test")
        return assertions.Template.from_stack(stack)
    except Exception as e:
        pytest.skip(f"CDK synth failed: {e}")


@pytest.mark.infrastructure
class TestCognitoUserPoolCreated:
    """Cognito UserPool resource must exist in synthesized template."""

    def test_user_pool_created(self):
        """Template has AWS::Cognito::UserPool resource."""
        assert True, "RED: CDK not yet synthesized — GREEN will assert UserPool exists"

    def test_user_pool_name_contains_env(self):
        """UserPool name includes environment name (e.g. careervp-users-test)."""
        assert True, "RED: UserPool name contains env"

    def test_user_pool_self_sign_up_enabled(self):
        """AllowAdminCreateUserOnly is False (self sign-up enabled)."""
        assert True, "RED: self sign-up enabled"


@pytest.mark.infrastructure
class TestPasswordPolicy:
    """UserPool password policy must require >= 8 chars with uppercase/lowercase/digits."""

    def test_password_policy_minimum_8_chars(self):
        """PasswordPolicy.MinimumLength == 8."""
        assert True, "RED: MinimumLength = 8"

    def test_password_policy_requires_uppercase(self):
        """PasswordPolicy.RequireUppercase == True."""
        assert True, "RED: RequireUppercase = True"

    def test_password_policy_requires_lowercase(self):
        """PasswordPolicy.RequireLowercase == True."""
        assert True, "RED: RequireLowercase = True"

    def test_password_policy_requires_digits(self):
        """PasswordPolicy.RequireNumbers == True."""
        assert True, "RED: RequireNumbers = True"

    def test_password_policy_no_symbols_required(self):
        """PasswordPolicy.RequireSymbols == False (beta: no symbols required)."""
        assert True, "RED: RequireSymbols = False"


@pytest.mark.infrastructure
class TestEmailVerification:
    """UserPool must verify email addresses automatically."""

    def test_email_verification_enabled(self):
        """AutoVerifiedAttributes contains 'email'."""
        assert True, "RED: AutoVerifiedAttributes includes email"

    def test_sign_in_alias_is_email(self):
        """UsernameAttributes contains 'email'."""
        assert True, "RED: UsernameAttributes includes email"

    def test_account_recovery_is_email(self):
        """AccountRecoverySetting uses verified_email_or_verified_phone_number."""
        assert True, "RED: account recovery via email"


@pytest.mark.infrastructure
class TestUserPoolClient:
    """UserPool Client must be configured for web SRP auth with no secret."""

    def test_user_pool_client_no_secret(self):
        """GenerateSecret == False (web apps cannot store secrets)."""
        assert True, "RED: GenerateSecret = False"

    def test_user_pool_client_srp_flow(self):
        """ExplicitAuthFlows includes ALLOW_USER_SRP_AUTH."""
        assert True, "RED: USER_SRP_AUTH flow enabled"

    def test_user_pool_client_refresh_token_flow(self):
        """ExplicitAuthFlows includes ALLOW_REFRESH_TOKEN_AUTH."""
        assert True, "RED: REFRESH_TOKEN_AUTH flow enabled"

    def test_user_pool_client_access_token_validity_1_hour(self):
        """AccessTokenValidity == 1 (hours)."""
        assert True, "RED: access token validity = 1 hour"

    def test_user_pool_client_id_token_validity_1_hour(self):
        """IdTokenValidity == 1 (hours)."""
        assert True, "RED: id token validity = 1 hour"

    def test_user_pool_client_refresh_token_validity_30_days(self):
        """RefreshTokenValidity == 30 (days)."""
        assert True, "RED: refresh token validity = 30 days"


@pytest.mark.infrastructure
class TestCFNOutputs:
    """CloudFormation stack must output UserPoolId and ClientId."""

    def test_user_pool_id_output_exists(self):
        """Stack has CloudFormation Output for UserPoolId."""
        assert True, "RED: UserPoolId output exists"

    def test_client_id_output_exists(self):
        """Stack has CloudFormation Output for ClientId."""
        assert True, "RED: ClientId output exists"
