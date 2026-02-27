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
            ),
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
