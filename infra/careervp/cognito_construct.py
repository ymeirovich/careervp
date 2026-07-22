from __future__ import annotations

from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_cognito as cognito
from constructs import Construct

from .scratch_deployment import ScratchDeploymentSettings, validate_scratch_boundary

P07_AUTH_MIGRATION_PHASE = "migration_window"

# Amplify branch that the devx stack is verified from (P-07 step 1.6). Cognito rejects any
# redirect_uri not on the registered list, so this must be registered before the first login.
DEVX_AMPLIFY_ORIGIN = "https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com"


class CognitoConstruct(Construct):
    """Provision Cognito User Pool resources for API authentication."""

    def __init__(
        self,
        scope: Construct,
        id_: str,
        environment: str,
        *,
        scratch_settings: ScratchDeploymentSettings | None = None,
    ) -> None:
        super().__init__(scope, id_)
        if scratch_settings is not None:
            validate_scratch_boundary(scratch_settings, environment=environment)
        callback_urls = (
            [f"{scratch_settings.allowed_origin.rstrip('/')}/callback"]
            if scratch_settings is not None
            else [
                "http://localhost:3000/callback",
                "https://app.careervp.com/callback",
                "https://dev.careervp.com/callback",
                "https://front-ui-update-amplify1.d3j2wnm8g5clnw.amplifyapp.com/callback",
                f"{DEVX_AMPLIFY_ORIGIN}/callback",
                "https://stage.careervp.com/callback",
            ]
        )
        logout_urls = (
            [f"{scratch_settings.allowed_origin.rstrip('/')}/"]
            if scratch_settings is not None
            else [
                "http://localhost:3000/",
                "https://app.careervp.com/",
                "https://dev.careervp.com/",
                "https://front-ui-update-amplify1.d3j2wnm8g5clnw.amplifyapp.com/",
                f"{DEVX_AMPLIFY_ORIGIN}/",
                "https://stage.careervp.com/",
            ]
        )

        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"careervp-users-{environment}",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            feature_plan=cognito.FeaturePlan.PLUS,
            standard_threat_protection_mode=cognito.StandardThreatProtectionMode.FULL_FUNCTION,
            mfa=cognito.Mfa.OPTIONAL,
            mfa_second_factor=cognito.MfaSecondFactor(sms=False, otp=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
        )
        if scratch_settings is not None:
            self.user_pool.apply_removal_policy(RemovalPolicy.DESTROY)

        self.user_pool_client = self.user_pool.add_client(
            "UserPoolClient",
            user_pool_client_name=f"careervp-client-{environment}",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(
                user_srp=True,
                user_password=True,
            ),
            # P-07 migration window: code+PKCE is the frontend default, while
            # implicit and COGNITO_ADMIN remain until the deployed frontend has
            # soaked and browser-side password change moves behind a proxy.
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=True,
                ),
                scopes=[
                    cognito.OAuthScope.COGNITO_ADMIN,
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PHONE,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=callback_urls,
                logout_urls=logout_urls,
            ),
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO,
            ],
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
        )

        self.user_pool.add_domain(
            "UserPoolDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f"careervp-{environment}",
            ),
        )

        self.user_pool_id = self.user_pool.user_pool_id
        self.client_id = self.user_pool_client.user_pool_client_id
