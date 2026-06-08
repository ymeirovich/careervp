from typing import Any

from aws_cdk import Aspects, CfnOutput, Stack, Tags
from cdk_nag import AwsSolutionsChecks, NagSuppressions
from constructs import Construct

from .api_construct import ApiConstruct
from .cognito_construct import CognitoConstruct
from .configuration.configuration_construct import ConfigurationStore
from .constants import (
    CONFIGURATION_NAME,
    ENVIRONMENT,
    OWNER_TAG,
    SERVICE_NAME,
    SERVICE_NAME_TAG,
    STACK_FEATURE,
)
from .naming_utils import NamingUtils
from .utils import get_construct_name, get_username


class ServiceStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        is_production_env: bool,
        naming: NamingUtils | None = None,
        stack_feature: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        self.naming = naming or NamingUtils(environment=ENVIRONMENT)
        self.stack_feature = stack_feature or STACK_FEATURE
        self._add_stack_tags()

        # This construct should be deployed in a different repo and have its own pipeline so updates can be decoupled
        # from running the service pipeline and without redeploying the service lambdas. For the sake of this blueprint
        # example, it is deployed as part of the service stack
        self.dynamic_configuration = ConfigurationStore(
            self,
            get_construct_name(stack_prefix=id, construct_name="DynamicConf"),
            ENVIRONMENT,
            SERVICE_NAME,
            CONFIGURATION_NAME,
        )
        self.cognito = CognitoConstruct(
            self,
            get_construct_name(stack_prefix=id, construct_name="Cognito"),
            environment=self.naming.environment,
        )
        self.api = ApiConstruct(
            self,
            get_construct_name(stack_prefix=id, construct_name="Crud"),
            self.dynamic_configuration.app_name,
            is_production_env=is_production_env,
            naming=self.naming,
            user_pool=self.cognito.user_pool,
            cognito_client_id=self.cognito.client_id,
        )

        CfnOutput(self, "UserPoolId", value=self.cognito.user_pool_id)
        CfnOutput(self, "ClientId", value=self.cognito.client_id)

        # add security check
        self._add_security_tests()

    def _add_stack_tags(self) -> None:
        # best practice to help identify resources in the console
        Tags.of(self).add(SERVICE_NAME_TAG, SERVICE_NAME)
        Tags.of(self).add(OWNER_TAG, get_username())
        Tags.of(self).add("feature", self.stack_feature)

    def _add_security_tests(self) -> None:
        Aspects.of(self).add(AwsSolutionsChecks(verbose=True))
        # Suppress a specific rule for this resource
        NagSuppressions.add_stack_suppressions(
            self,
            [
                {"id": "AwsSolutions-IAM4", "reason": "policy for cloudwatch logs."},
                {"id": "AwsSolutions-IAM5", "reason": "policy for cloudwatch logs."},
                {"id": "AwsSolutions-APIG2", "reason": "lambda does input validation"},
                {
                    "id": "AwsSolutions-APIG1",
                    "reason": "not mandatory in a sample blueprint",
                },
                {
                    "id": "AwsSolutions-APIG3",
                    "reason": "not mandatory in a sample blueprint",
                },
                {
                    "id": "AwsSolutions-APIG6",
                    "reason": "not mandatory in a sample blueprint",
                },
                {
                    "id": "AwsSolutions-APIG4",
                    "reason": "authorization not mandatory in a sample blueprint",
                },
                {
                    "id": "AwsSolutions-COG1",
                    "reason": "Beta policy intentionally allows no-symbol passwords for UX.",
                },
                {
                    "id": "AwsSolutions-COG3",
                    "reason": "Advanced security mode rollout deferred for beta hardening phase.",
                },
                {
                    "id": "AwsSolutions-COG4",
                    "reason": "Public auth/health/swagger routes are intentionally unauthenticated.",
                },
                {"id": "AwsSolutions-L1", "reason": "False positive"},
                {
                    "id": "AwsSolutions-S1",
                    "reason": "CV bucket access logs not needed in dev; enable in production",
                },
                {
                    "id": "AwsSolutions-SQS4",
                    "reason": "VPR async queues are internal, SSL not required",
                },
                {
                    "id": "AwsSolutions-SQS3",
                    "reason": "Worker DLQs are terminal destinations and should not chain DLQs",
                },
                {
                    "id": "AwsSolutions-SF1",
                    "reason": "Artifact chain logs at ERROR level by design (FE-UI-031) to control CloudWatch costs; execution data logging is intentionally disabled.",
                },
            ],
        )
