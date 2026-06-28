from __future__ import annotations

from aws_cdk import Aws, Duration, NestedStack, RemovalPolicy
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_logs as logs
from cdk_nag import NagSuppressions
from constructs import Construct

from . import constants
from .naming_utils import NamingUtils


class AiAssistNestedStack(NestedStack):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        *,
        naming: NamingUtils,
        logs_kms_key: kms.IKey,
        artifacts_table: dynamodb.TableV2,
        cvs_table: dynamodb.TableV2,
        applications_table: dynamodb.TableV2,
        jobs_table: dynamodb.TableV2,
        gap_responses_table: dynamodb.TableV2,
        users_table: dynamodb.TableV2,
        llm_cache_table: dynamodb.TableV2,
        allowed_origins: str,
    ) -> None:
        super().__init__(scope, id_)
        self.naming = naming

        function_name = naming.lambda_name(constants.AI_ASSIST_FEATURE)
        log_group = logs.LogGroup(
            self,
            "AiAssistLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=logs_kms_key,
        )

        self.role = iam.Role(
            self,
            "AiAssistRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=naming.role_name(
                constants.LAMBDA_SERVICE_NAME, constants.AI_ASSIST_FEATURE
            ),
        )

        self.ai_assist_lambda = _lambda.Function(
            self,
            constants.AI_ASSIST_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.ai_assist_handler.lambda_handler",
            function_name=function_name,
            role=self.role,
            timeout=Duration.seconds(25),
            memory_size=512,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-ai-assist",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                # CV, VPR, tailored CV and gap responses are persisted in the
                # single-table users_table (pk/sk design). The dedicated
                # cvs/gap_responses tables are unused by the write path, so
                # AI-assist reads those cross-artifact contexts from users_table —
                # otherwise upstream lookups resolve against empty tables and
                # return spurious 409 "missing upstream artifact".
                "ARTIFACTS_TABLE_NAME": users_table.table_name,
                "CVS_TABLE_NAME": users_table.table_name,
                "APPLICATIONS_TABLE_NAME": applications_table.table_name,
                # The application row is created lazily, so early in the flow the
                # ownership check must fall back to the JOB record (matching
                # application_handler). JobsRepository reads JOBS_TABLE_NAME, so it
                # must point at the same dedicated vpr-jobs table the API writes to —
                # otherwise the fallback queries a non-existent table and AI-assist
                # 403s ("Application not found for this user") on new applications.
                "JOBS_TABLE_NAME": jobs_table.table_name,
                # Gap responses are written by gap_handler to the dedicated
                # gap_responses_table (userId/questionId key schema), which is what
                # get_gap_responses queries. Pointing this at users_table makes the
                # query fail with "missed key schema element: pk" and silently drops
                # gap-response context from every AI-assist prompt.
                "GAP_RESPONSES_TABLE_NAME": gap_responses_table.table_name,
                "USERS_TABLE_NAME": users_table.table_name,
                "VPR_TABLE_NAME": users_table.table_name,
                # Company Research is the ONE artifact NOT in users_table: the CR
                # worker writes it to the dedicated artifacts_table with an
                # applicationId/artifactId key schema (see company_research_store).
                # AI-assist must therefore read CR from artifacts_table, not
                # users_table, or the canonical GetItem fails with a schema
                # ValidationException and the read 409s as "missing company_research".
                "COMPANY_RESEARCH_TABLE_NAME": artifacts_table.table_name,
                "ALLOWED_ORIGINS": allowed_origins,
                constants.LLM_CACHE_TABLE_NAME_ENV: llm_cache_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
                constants.STRATEGIC_MODEL_ID_ENV_VAR: constants.STRATEGIC_MODEL_ID,
                constants.TEMPLATE_MODEL_ID_ENV_VAR: constants.TEMPLATE_MODEL_ID,
                constants.AI_ASSIST_MODEL_ENV_VAR: constants.TEMPLATE_MODEL_ID,
                constants.AI_ASSIST_TIMEOUT_ENV_VAR: "25",
            },
        )

        log_group.grant_write(self.role)
        self.role.add_to_policy(
            iam.PolicyStatement(
                actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
                resources=["*"],
            )
        )
        # All cross-artifact reads (CV, VPR, gap responses, company research)
        # resolve against users_table, which uses both base-table (pk/sk) and
        # GSI access patterns — so Query on the table and its indexes is required.
        self.role.add_to_policy(
            iam.PolicyStatement(
                actions=["dynamodb:GetItem", "dynamodb:Query"],
                resources=[
                    users_table.table_arn,
                    f"{users_table.table_arn}/index/*",
                ],
            )
        )
        self.role.add_to_policy(
            iam.PolicyStatement(
                actions=["dynamodb:GetItem", "dynamodb:Query"],
                resources=[applications_table.table_arn],
            )
        )
        # Ownership fallback: when the application row is absent, validate against
        # the JOB record (GetItem by job_id == application_id) in the jobs table.
        self.role.add_to_policy(
            iam.PolicyStatement(
                actions=["dynamodb:GetItem"],
                resources=[jobs_table.table_arn],
            )
        )
        # Company Research lives in artifacts_table (applicationId/artifactId
        # schema), read via canonical GetItem and the type-index GSI.
        self.role.add_to_policy(
            iam.PolicyStatement(
                actions=["dynamodb:GetItem", "dynamodb:Query"],
                resources=[
                    artifacts_table.table_arn,
                    f"{artifacts_table.table_arn}/index/*",
                ],
            )
        )
        # Gap responses live in the dedicated gap_responses_table
        # (userId/questionId schema), queried by get_gap_responses.
        self.role.add_to_policy(
            iam.PolicyStatement(
                actions=["dynamodb:GetItem", "dynamodb:Query"],
                resources=[gap_responses_table.table_arn],
            )
        )
        self.role.add_to_policy(
            iam.PolicyStatement(
                actions=["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"],
                resources=[llm_cache_table.table_arn],
            )
        )
        self.role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    (
                        f"arn:aws:ssm:{naming.region}:{naming.account_id}:parameter/"
                        f"{constants.ANTHROPIC_API_KEY_SSM_PARAM.lstrip('/')}"
                    )
                ],
            )
        )

        self.ai_assist_lambda.add_permission(
            "AllowAiAssistApiInvoke",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=(
                f"arn:{Aws.PARTITION}:execute-api:{Aws.REGION}:{Aws.ACCOUNT_ID}:"
                "*/POST/ai/assist"
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
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": (
                        "AI-assist queries users_table via its GSIs (CV/VPR lookups); "
                        "DynamoDB index ARNs are dynamic so an index/* wildcard is required."
                    ),
                    "appliesTo": [
                        {
                            "regex": "/^Resource::.*\\/index\\/\\*$/g",
                        },
                    ],
                },
            ],
            apply_to_children=True,
        )
        NagSuppressions.add_resource_suppressions(
            self.ai_assist_lambda,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": "PYTHON_3_13 is the latest supported runtime; cdk-nag false positive.",
                }
            ],
        )
