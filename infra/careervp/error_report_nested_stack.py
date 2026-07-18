from __future__ import annotations

from collections.abc import Sequence

from aws_cdk import Aws, Duration, NestedStack, RemovalPolicy
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_codedeploy as codedeploy
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_logs as logs
from aws_cdk import aws_sns as sns
from cdk_nag import NagSuppressions
from constructs import Construct

from . import constants
from .naming_utils import NamingUtils


class ErrorReportNestedStack(NestedStack):
    """Hosts the client-error-report Lambda off the parent stack.

    The parent (CareerVpCrudDev) sits near the 500-resource CloudFormation limit,
    so only the unavoidable API Gateway Resource + methods for POST /errors live
    in the parent; the Lambda, log group, role and invoke permission live here.
    The route is wired via an AwsIntegration proxy in ApiConstruct, so the invoke
    permission is granted here (no cross-stack LambdaIntegration permission).
    """

    def __init__(
        self,
        scope: Construct,
        id_: str,
        *,
        naming: NamingUtils,
        logs_kms_key: kms.IKey,
        allowed_origins: str,
        deployment_application: codedeploy.ILambdaApplication,
        deployment_role: iam.IRole,
        rollback_alarms: Sequence[cw.IAlarm],
        notification_topic: sns.ITopic,
    ) -> None:
        super().__init__(scope, id_)
        self.naming = naming

        function_name = naming.lambda_name(constants.ERROR_REPORT_FEATURE)
        log_group = logs.LogGroup(
            self,
            "ErrorReportLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=logs_kms_key,
        )

        self.role = iam.Role(
            self,
            "ErrorReportRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=naming.role_name(
                constants.LAMBDA_SERVICE_NAME, constants.ERROR_REPORT_FEATURE
            ),
        )

        self.error_report_lambda = _lambda.Function(
            self,
            constants.ERROR_REPORT_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.error_report_handler.lambda_handler",
            function_name=function_name,
            role=self.role,
            timeout=Duration.seconds(10),
            memory_size=128,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-client-errors",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                "ALLOWED_ORIGINS": allowed_origins,
            },
        )
        self.error_report_alias = self.error_report_lambda.add_alias(
            f"live-{naming.environment}"
        )
        canary_error_alarm = cw.Alarm(
            self,
            "P23ErrorReportCanaryErrorAlarm",
            alarm_name=naming.resource_name("error-report-canary-error", "alarm"),
            metric=self.error_report_alias.metric_errors(
                period=Duration.minutes(1), statistic="Sum"
            ),
            threshold=1,
            evaluation_periods=1,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )
        canary_error_alarm.add_alarm_action(cw_actions.SnsAction(notification_topic))
        codedeploy.LambdaDeploymentGroup(
            self,
            "P23ErrorReportCanaryDeploymentGroup",
            application=deployment_application,
            alias=self.error_report_alias,
            deployment_group_name=naming.resource_name(
                "error-report-canary", "deployment-group"
            ),
            deployment_config=codedeploy.LambdaDeploymentConfig.CANARY_10_PERCENT_5_MINUTES,
            alarms=[canary_error_alarm, *rollback_alarms],
            auto_rollback=codedeploy.AutoRollbackConfig(
                deployment_in_alarm=True,
                failed_deployment=True,
                stopped_deployment=True,
            ),
            role=deployment_role,
        )

        # This handler only logs; it needs CloudWatch Logs + X-Ray and nothing else.
        log_group.grant_write(self.role)
        self.role.add_to_policy(
            iam.PolicyStatement(
                actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
                resources=["*"],
            )
        )

        self.error_report_alias.add_permission(
            "AllowErrorReportApiInvoke",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=(
                f"arn:{Aws.PARTITION}:execute-api:{Aws.REGION}:{Aws.ACCOUNT_ID}:"
                "*/POST/errors"
            ),
        )

        NagSuppressions.add_resource_suppressions(
            self.role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": (
                        "XRay PutTraceSegments/PutTelemetryRecords and CloudWatch Logs "
                        "require Resource::* — no resource-level ARN is supported by these services."
                    ),
                    "appliesTo": [
                        "Action::xray:PutTraceSegments",
                        "Action::xray:PutTelemetryRecords",
                        "Resource::*",
                    ],
                },
            ],
            apply_to_children=True,
        )
        NagSuppressions.add_resource_suppressions(
            self.error_report_lambda,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": "PYTHON_3_13 is the latest supported runtime; cdk-nag false positive.",
                }
            ],
        )
