from __future__ import annotations

from aws_cdk import Duration
from aws_cdk import aws_cognito as cognito
from constructs import Construct


class CognitoConstruct(Construct):
    """Provision Cognito User Pool resources for API authentication."""

    def __init__(self, scope: Construct, id_: str, environment: str) -> None:
        super().__init__(scope, id_)

        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"careervp-users-{environment}",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
        )

        self.user_pool_client = self.user_pool.add_client(
            "UserPoolClient",
            user_pool_client_name=f"careervp-client-{environment}",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(
                user_srp=True,
                user_password=True,
            ),
            # FE-UI-037 step 0: callback/logout URLs captured from the live dev
            # User Pool Client so a parent `cdk deploy` does not revert live auth.
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
                callback_urls=[
                    "http://localhost:3000/callback",
                    "https://app.careervp.com/callback",
                    "https://dev.careervp.com/callback",
                    "https://front-ui-update-amplify1.d3j2wnm8g5clnw.amplifyapp.com/callback",
                    "https://stage.careervp.com/callback",
                ],
                logout_urls=[
                    "http://localhost:3000/",
                    "https://app.careervp.com/",
                    "https://dev.careervp.com/",
                    "https://front-ui-update-amplify1.d3j2wnm8g5clnw.amplifyapp.com/",
                    "https://stage.careervp.com/",
                ],
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
