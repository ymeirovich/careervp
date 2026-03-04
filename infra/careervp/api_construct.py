import json
from typing import cast

from aws_cdk import CfnOutput, Duration, RemovalPolicy, aws_apigateway, aws_sqs
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_lambda_event_sources as eventsources
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ssm as ssm
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from constructs import Construct

from . import constants
from .api_db_construct import ApiDbConstruct
from .monitoring import CrudMonitoring
from .naming_utils import NamingUtils
from .waf_construct import WafToApiGatewayConstruct


class ApiConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        appconfig_app_name: str,
        is_production_env: bool,
        naming: NamingUtils,
        user_pool: cognito.IUserPool,
        cognito_client_id: str,
    ) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.naming = naming
        self.cognito_client_id = cognito_client_id
        self.cognito_user_pool = user_pool
        self.api_db = ApiDbConstruct(self, f"{id_}db", naming=naming)
        self.llm_cache_table = self._build_llm_cache_table(is_production_env)
        self.logs_kms_key = self._build_logs_kms_key()
        self.rest_api = self._build_api_gw()
        self._add_gateway_error_responses(self.rest_api)

        # VPR Async Architecture - DLQ first, then Queue (DLQ must exist first)
        self.vpr_jobs_dlq = self._build_vpr_jobs_dlq()
        self.vpr_jobs_queue = self._build_vpr_jobs_queue(self.vpr_jobs_dlq)

        # Cover Letter Async Architecture
        self.cover_letter_jobs_dlq = self._build_cover_letter_jobs_dlq()
        self.cover_letter_jobs_queue = self._build_cover_letter_jobs_queue(
            self.cover_letter_jobs_dlq
        )

        # Interview Prep Async Architecture
        self.interview_prep_jobs_dlq = self._build_interview_prep_jobs_dlq()
        self.interview_prep_jobs_queue = self._build_interview_prep_jobs_queue(
            self.interview_prep_jobs_dlq
        )

        # Create Lambda role BEFORE lambdas that need it
        self.lambda_role = self._build_lambda_role(
            self.api_db.db,
            self.api_db.idempotency_db,
            self.api_db.cv_bucket,
            self.api_db.jobs_table,
            self.api_db.vpr_results_bucket,
            self.vpr_jobs_queue,
            self.api_db.cvs_table,
            self.api_db.applications_table,
            self.api_db.gap_responses_table,
            self.api_db.knowledge_table,
            self.api_db.artifacts_table,
            self.api_db.company_research_cache_table,
            self.api_db.static_bucket,
            self.api_db.backups_bucket,
            self.api_db.logs_bucket,
            self.api_db.artifacts_bucket,
        )
        self.api_authorizer = self._build_api_authorizer(user_pool)

        api_resource: aws_apigateway.Resource = self.rest_api.root.add_resource(
            constants.API_ROOT_RESOURCE
        )
        cv_resource = api_resource.add_resource(constants.GW_RESOURCE)
        vpr_resource = api_resource.add_resource(constants.GW_RESOURCE_VPR)
        company_research_resource = api_resource.add_resource(
            constants.GW_RESOURCE_COMPANY_RESEARCH
        )
        self.cv_upload_func = self._add_post_lambda_integration(
            cv_resource,
            self.lambda_role,
            self.api_db.db,
            appconfig_app_name,
            self.api_db.idempotency_db,
            self.api_db.cv_bucket,
        )
        # Note: Original synchronous VPR generator removed - using async VPR architecture instead
        self.vpr_generator_func = None  # Placeholder for backward compatibility

        # VPR Submit Lambda - POST /api/vpr (async architecture)
        self.vpr_submit_func = self._add_vpr_submit_lambda_integration(
            vpr_resource,
            self.lambda_role,
            self.api_db.jobs_table,
            self.api_db.vpr_results_bucket,
            self.vpr_jobs_queue,
            appconfig_app_name,
        )

        # VPR Status Lambda - GET /api/vpr/status/{job_id}
        vpr_status_resource = vpr_resource.add_resource("status").add_resource(
            "{job_id}"
        )
        self.vpr_status_func = self._add_vpr_status_lambda_integration(
            vpr_status_resource,
            self.lambda_role,
            self.api_db.jobs_table,
            self.api_db.vpr_results_bucket,
            appconfig_app_name,
        )

        # Keep the original SQS worker for existing queue-based VPR flow.
        self.vpr_sqs_worker_func = self._add_vpr_sqs_worker_lambda_integration(
            self.lambda_role,
            self.api_db.jobs_table,
            self.api_db.vpr_results_bucket,
            self.api_db.db,
            self.vpr_jobs_queue,
            appconfig_app_name,
        )
        self.company_research_func = self._add_company_research_lambda_integration(
            company_research_resource,
            self.lambda_role,
            self.api_db.db,
            appconfig_app_name,
        )
        self.auth_api_func = self._add_auth_lambda()
        self.health_api_func = self._add_health_lambda()
        self.user_api_func = self._add_user_lambda()
        self.job_api_func = self._add_job_lambda()
        self.application_api_func = self._add_application_lambda()
        self.gap_api_func = self._add_gap_lambda()
        self.cover_letter_api_func = self._add_cover_letter_lambda()
        self.cover_letter_status_func = self._add_cover_letter_status_lambda()
        self.interview_prep_api_func = self._add_interview_prep_lambda()
        self.interview_prep_status_func = self._add_interview_prep_status_lambda()

        # CV Tailoring - POST /api/cv-tailoring
        cv_tailoring_resource = api_resource.add_resource(
            constants.GW_RESOURCE_CV_TAILORING
        )
        self.cv_tailoring_func = self._add_cv_tailoring_lambda_integration(
            cv_tailoring_resource,
            self.lambda_role,
            self.api_db.db,
            appconfig_app_name,
            self.api_db.idempotency_db,
        )

        # Async worker DLQs (ASYNC_004): one DLQ per worker for failed events.
        self.cv_upload_worker_dlq = self._build_worker_dlq("cv-upload-worker")
        self.vpr_worker_dlq = self._build_worker_dlq("vpr-worker")
        self.cv_tailor_worker_dlq = self._build_worker_dlq("cv-tailor-worker")
        self.cover_letter_worker_dlq = self._build_worker_dlq("cover-letter-worker")
        self.interview_prep_worker_dlq = self._build_worker_dlq("interview-prep-worker")

        # Async workers required by Phase 11 infrastructure remediation.
        self.cv_upload_worker_func = self._add_cv_upload_worker_lambda(
            cv_bucket=self.api_db.cv_bucket,
            cvs_table=self.api_db.cvs_table,
            idempotency_table=self.api_db.idempotency_db,
            dlq=self.cv_upload_worker_dlq,
        )
        self.vpr_worker_func = self._add_vpr_worker_stream_lambda(
            jobs_table=self.api_db.jobs_table,
            artifacts_table=self.api_db.artifacts_table,
            dlq=self.vpr_worker_dlq,
        )
        self.cv_tailor_worker_func = self._add_cv_tailor_worker_lambda(
            artifacts_table=self.api_db.artifacts_table,
            cvs_table=self.api_db.cvs_table,
            dlq=self.cv_tailor_worker_dlq,
        )
        self.cover_letter_worker_func = self._add_cover_letter_worker_lambda(
            artifacts_table=self.api_db.artifacts_table,
            applications_table=self.api_db.applications_table,
            dlq=self.cover_letter_worker_dlq,
        )
        self.interview_prep_worker_func = self._add_interview_prep_worker_lambda(
            artifacts_table=self.api_db.artifacts_table,
            applications_table=self.api_db.applications_table,
            dlq=self.interview_prep_worker_dlq,
        )
        self._add_openapi_contract_routes()

        self._build_swagger_endpoints(
            rest_api=self.rest_api, dest_func=self.cv_upload_func
        )
        self.monitoring = CrudMonitoring(
            self,
            id_,
            self.rest_api,
            self.api_db.db,
            self.api_db.idempotency_db,
            [
                self.cv_upload_func,
                self.vpr_submit_func,
                self.company_research_func,
                self.cv_tailoring_func,
                self.gap_api_func,
                self.cover_letter_api_func,
                self.interview_prep_api_func,
            ],
            naming=naming,
        )

        if is_production_env:
            # add WAF
            self.waf = WafToApiGatewayConstruct(
                self,
                f"{id_}waf",
                self.rest_api,
                naming=naming,
                feature=constants.API_FEATURE,
            )

    def _build_swagger_endpoints(
        self, rest_api: aws_apigateway.RestApi, dest_func: _lambda.Function
    ) -> None:
        # GET /swagger
        swagger_resource: aws_apigateway.Resource = rest_api.root.add_resource(
            constants.SWAGGER_RESOURCE
        )
        swagger_resource.add_method(
            http_method="GET",
            integration=aws_apigateway.LambdaIntegration(handler=dest_func),
            authorization_type=aws_apigateway.AuthorizationType.NONE,
        )
        # GET /swagger.css
        swagger_resource_css = rest_api.root.add_resource(
            constants.SWAGGER_CSS_RESOURCE
        )
        swagger_resource_css.add_method(
            http_method="GET",
            integration=aws_apigateway.LambdaIntegration(handler=dest_func),
            authorization_type=aws_apigateway.AuthorizationType.NONE,
        )
        # GET /swagger.js
        swagger_resource_js = rest_api.root.add_resource(constants.SWAGGER_JS_RESOURCE)
        swagger_resource_js.add_method(
            http_method="GET",
            integration=aws_apigateway.LambdaIntegration(handler=dest_func),
            authorization_type=aws_apigateway.AuthorizationType.NONE,
        )

        CfnOutput(
            self, id=constants.SWAGGER_URL, value=f"{rest_api.url}swagger"
        ).override_logical_id(constants.SWAGGER_URL)

    def _build_api_gw(self) -> aws_apigateway.RestApi:
        access_log_group = logs.LogGroup(
            self,
            "ApiGatewayAccessLogGroup",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        rest_api: aws_apigateway.RestApi = aws_apigateway.RestApi(
            self,
            "service-rest-api",
            rest_api_name=self.naming.api_name(constants.API_FEATURE),
            description="CareerVP API - AI-powered job application assistant",
            deploy_options=aws_apigateway.StageOptions(
                throttling_rate_limit=2,
                throttling_burst_limit=10,
                tracing_enabled=True,
                metrics_enabled=True,
                logging_level=aws_apigateway.MethodLoggingLevel.INFO,
                access_log_destination=aws_apigateway.LogGroupLogDestination(
                    access_log_group
                ),
                access_log_format=aws_apigateway.AccessLogFormat.custom(
                    json.dumps(
                        {
                            "requestId": "$context.requestId",
                            "extendedRequestId": "$context.extendedRequestId",
                            "ip": "$context.identity.sourceIp",
                            "caller": "$context.identity.caller",
                            "user": "$context.identity.user",
                            "requestTime": "$context.requestTime",
                            "httpMethod": "$context.httpMethod",
                            "resourcePath": "$context.resourcePath",
                            "status": "$context.status",
                            "protocol": "$context.protocol",
                            "responseLength": "$context.responseLength",
                            "integrationStatus": "$context.integration.status",
                            "integrationErrorMessage": "$context.integrationErrorMessage",
                            "authorizerError": "$context.authorizer.error",
                        }
                    )
                ),
            ),
            cloud_watch_role=True,
        )

        CfnOutput(
            self, id=constants.APIGATEWAY, value=rest_api.url
        ).override_logical_id(constants.APIGATEWAY)
        return rest_api

    def _add_gateway_error_responses(self, rest_api: aws_apigateway.RestApi) -> None:
        response_types = (
            ("Default4xx", aws_apigateway.ResponseType.DEFAULT_4_XX, "DEFAULT_4XX"),
            ("Default5xx", aws_apigateway.ResponseType.DEFAULT_5_XX, "DEFAULT_5XX"),
            ("Unauthorized", aws_apigateway.ResponseType.UNAUTHORIZED, "UNAUTHORIZED"),
            (
                "AccessDenied",
                aws_apigateway.ResponseType.ACCESS_DENIED,
                "ACCESS_DENIED",
            ),
        )
        for response_id, response_type, response_code in response_types:
            aws_apigateway.GatewayResponse(
                self,
                f"GatewayResponse{response_id}",
                rest_api=rest_api,
                type=response_type,
                response_headers={
                    "Access-Control-Allow-Origin": "'*'",
                    "Access-Control-Allow-Headers": "'Content-Type,Authorization'",
                    "Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE,OPTIONS'",
                },
                templates={
                    "application/json": json.dumps(
                        {
                            "error": response_code,
                            "code": response_code,
                            "request_id": "$context.requestId",
                        }
                    )
                },
            )

    def _build_logs_kms_key(self) -> kms.Key:
        key = kms.Key(
            self,
            "CloudWatchLogsKey",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,
        )
        key.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudWatchLogsUseOfKey",
                effect=iam.Effect.ALLOW,
                principals=[
                    iam.ServicePrincipal(f"logs.{self.naming.region}.amazonaws.com")
                ],
                actions=[
                    "kms:Encrypt",
                    "kms:Decrypt",
                    "kms:ReEncrypt*",
                    "kms:GenerateDataKey*",
                    "kms:DescribeKey",
                ],
                resources=["*"],
                conditions={
                    "ArnLike": {
                        "kms:EncryptionContext:aws:logs:arn": (
                            f"arn:aws:logs:{self.naming.region}:"
                            f"{self.naming.account_id}:log-group:*"
                        )
                    }
                },
            )
        )
        return key

    def _build_api_authorizer(
        self,
        user_pool: cognito.IUserPool,
    ) -> aws_apigateway.CognitoUserPoolsAuthorizer:
        return aws_apigateway.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuth",
            cognito_user_pools=[user_pool],
            identity_source="method.request.header.Authorization",
        )

    def _build_llm_cache_table(self, is_production_env: bool) -> dynamodb.TableV2:
        table = dynamodb.TableV2(
            self,
            "llm-cache-table",
            # This table intentionally omits "-table-" per Step 2.2 naming requirement.
            table_name=f"{self.naming.prefix}-{constants.LLM_CACHE_TABLE_NAME}-{self.naming.environment}",
            partition_key=dynamodb.Attribute(
                name="cache_key",
                type=dynamodb.AttributeType.STRING,
            ),
            billing=dynamodb.Billing.on_demand(),
            time_to_live_attribute="expires_at",
            point_in_time_recovery_specification=(
                dynamodb.PointInTimeRecoverySpecification(
                    point_in_time_recovery_enabled=True,
                    recovery_period_in_days=7,
                )
                if is_production_env
                else None
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
        CfnOutput(
            self,
            id=constants.LLM_CACHE_TABLE_OUTPUT,
            value=table.table_name,
        ).override_logical_id(constants.LLM_CACHE_TABLE_OUTPUT)
        return table

    def _build_lambda_role(
        self,
        db: dynamodb.TableV2,
        idempotency_table: dynamodb.TableV2,
        cv_bucket: s3.Bucket,
        jobs_table: dynamodb.TableV2,
        results_bucket: s3.Bucket,
        queue: aws_sqs.Queue,
        cvs_table: dynamodb.TableV2,
        applications_table: dynamodb.TableV2,
        gap_responses_table: dynamodb.TableV2,
        knowledge_table: dynamodb.TableV2,
        artifacts_table: dynamodb.TableV2,
        company_research_cache_table: dynamodb.TableV2,
        static_bucket: s3.Bucket,
        backups_bucket: s3.Bucket,
        logs_bucket: s3.Bucket,
        artifacts_bucket: s3.Bucket,
    ) -> iam.Role:
        return iam.Role(
            self,
            constants.SERVICE_ROLE_ARN,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=self.naming.role_name(
                constants.LAMBDA_SERVICE_NAME, constants.API_FEATURE
            ),
            inline_policies={
                "dynamic_configuration": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "appconfig:GetLatestConfiguration",
                                "appconfig:StartConfigurationSession",
                            ],
                            resources=["*"],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
                "dynamodb_db": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:PutItem",
                                "dynamodb:GetItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:Query",
                            ],
                            resources=[
                                db.table_arn,
                                f"{db.table_arn}/index/email-index",
                                f"{db.table_arn}/index/user_id-index",
                            ],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
                "idempotency_table": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:PutItem",
                                "dynamodb:GetItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:DeleteItem",
                            ],
                            resources=[idempotency_table.table_arn],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
                # IAM_001: scope each table policy to explicit table/index ARNs.
                "cvs_table": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:PutItem",
                                "dynamodb:GetItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:DeleteItem",
                                "dynamodb:Query",
                            ],
                            resources=[cvs_table.table_arn],
                            effect=iam.Effect.ALLOW,
                        ),
                    ]
                ),
                "applications_table": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:PutItem",
                                "dynamodb:GetItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:DeleteItem",
                                "dynamodb:Query",
                            ],
                            resources=[
                                applications_table.table_arn,
                                f"{applications_table.table_arn}/index/status-index",
                            ],
                            effect=iam.Effect.ALLOW,
                        ),
                    ]
                ),
                "gap_responses_table": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:PutItem",
                                "dynamodb:GetItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:DeleteItem",
                                "dynamodb:Query",
                            ],
                            resources=[gap_responses_table.table_arn],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
                "knowledge_table": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:PutItem",
                                "dynamodb:GetItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:DeleteItem",
                                "dynamodb:Query",
                            ],
                            resources=[
                                knowledge_table.table_arn,
                                f"{knowledge_table.table_arn}/index/entity-index",
                            ],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
                "artifacts_table": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:PutItem",
                                "dynamodb:GetItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:DeleteItem",
                                "dynamodb:Query",
                                "dynamodb:Scan",
                            ],
                            resources=[
                                artifacts_table.table_arn,
                                f"{artifacts_table.table_arn}/index/type-index",
                            ],
                            effect=iam.Effect.ALLOW,
                        ),
                    ]
                ),
                "company_research_cache_table": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:DeleteItem",
                                "dynamodb:Query",
                            ],
                            resources=[company_research_cache_table.table_arn],
                            effect=iam.Effect.ALLOW,
                        ),
                    ]
                ),
                "vpr_jobs_table": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:PutItem",
                                "dynamodb:GetItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:Query",
                            ],
                            resources=[
                                jobs_table.table_arn,
                                f"{jobs_table.table_arn}/index/idempotency-key-index",
                                f"{jobs_table.table_arn}/index/user_id-index",
                            ],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
                "llm_cache_table": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:DeleteItem",
                            ],
                            resources=[self.llm_cache_table.table_arn],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
                # IAM_001: scope bucket access to explicit bucket ARNs.
                "cv_bucket": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:DeleteObject",
                            ],
                            resources=[f"{cv_bucket.bucket_arn}/*"],
                            effect=iam.Effect.ALLOW,
                        ),
                        iam.PolicyStatement(
                            actions=["s3:ListBucket"],
                            resources=[cv_bucket.bucket_arn],
                            effect=iam.Effect.ALLOW,
                        ),
                    ]
                ),
                "vpr_results_bucket": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "s3:PutObject",
                                "s3:GetObject",
                            ],
                            resources=[f"{results_bucket.bucket_arn}/*"],
                            effect=iam.Effect.ALLOW,
                        ),
                        iam.PolicyStatement(
                            actions=["s3:ListBucket"],
                            resources=[results_bucket.bucket_arn],
                            effect=iam.Effect.ALLOW,
                        ),
                    ]
                ),
                "static_bucket": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:ListBucket", "s3:GetBucketLocation"],
                            resources=[static_bucket.bucket_arn],
                            effect=iam.Effect.ALLOW,
                        ),
                    ]
                ),
                "backups_bucket": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:ListBucket", "s3:GetBucketLocation"],
                            resources=[backups_bucket.bucket_arn],
                            effect=iam.Effect.ALLOW,
                        ),
                    ]
                ),
                "logs_bucket": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:ListBucket", "s3:GetBucketLocation"],
                            resources=[logs_bucket.bucket_arn],
                            effect=iam.Effect.ALLOW,
                        ),
                    ]
                ),
                "artifacts_bucket": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:ListBucket", "s3:GetBucketLocation"],
                            resources=[artifacts_bucket.bucket_arn],
                            effect=iam.Effect.ALLOW,
                        ),
                    ]
                ),
                "vpr_jobs_queue": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "sqs:SendMessage",
                                "sqs:ReceiveMessage",
                                "sqs:DeleteMessage",
                            ],
                            resources=[queue.queue_arn],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
                "sqs_kms_access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "kms:Decrypt",
                                "kms:GenerateDataKey",
                            ],
                            resources=["*"],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
                "ssm_parameters": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["ssm:GetParameter"],
                            resources=[
                                (
                                    f"arn:aws:ssm:{self.naming.region}:"
                                    f"{self.naming.account_id}:parameter/"
                                    f"{constants.ANTHROPIC_API_KEY_SSM_PARAM.lstrip('/')}"
                                )
                            ],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
                "cognito_admin": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "cognito-idp:AdminConfirmSignUp",
                                "cognito-idp:AdminGetUser",
                            ],
                            resources=[self.cognito_user_pool.user_pool_arn],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    managed_policy_name=(
                        f"service-role/{constants.LAMBDA_BASIC_EXECUTION_ROLE}"
                    )
                )
            ],
        )

    def _build_shared_table_env(self) -> dict[str, str]:
        """Build shared table-name environment variables for Lambda portability."""
        return {
            # LAMBDA_CONFIG_008: inject table names from CDK (no hardcoded names).
            "CVS_TABLE_NAME": self.api_db.cvs_table.table_name,
            "APPLICATIONS_TABLE_NAME": self.api_db.applications_table.table_name,
            "GAP_RESPONSES_TABLE_NAME": self.api_db.gap_responses_table.table_name,
            "KNOWLEDGE_TABLE_NAME": self.api_db.knowledge_table.table_name,
            "ARTIFACTS_TABLE_NAME": self.api_db.artifacts_table.table_name,
            "COMPANY_RESEARCH_CACHE_TABLE_NAME": (
                self.api_db.company_research_cache_table.table_name
            ),
            "ALLOWED_ORIGINS": "https://careervp.app,https://www.careervp.app",
        }

    def _build_common_layer(self) -> PythonLayerVersion:
        return PythonLayerVersion(
            self,
            f"{self.id_}{constants.LAMBDA_LAYER_NAME}",
            entry=constants.COMMON_LAYER_BUILD_FOLDER,
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_13],
            removal_policy=RemovalPolicy.DESTROY,
            description="Common layer for the service",
            compatible_architectures=[_lambda.Architecture.X86_64],
            bundling={
                "platform": "linux/amd64",
            },
        )

    def _add_post_lambda_integration(
        self,
        api_resource: aws_apigateway.Resource,
        role: iam.Role,
        db: dynamodb.TableV2,
        appconfig_app_name: str,
        idempotency_table: dynamodb.TableV2,
        cv_bucket: s3.Bucket,
    ) -> _lambda.Function:
        function_name = self.naming.lambda_name(constants.CV_PARSER_FEATURE)
        log_group = logs.LogGroup(
            self,
            f"{constants.CV_PARSER_LAMBDA}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            self,
            constants.CV_PARSER_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.cv_upload_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "JWT_PRIVATE_KEY": ssm.StringParameter.value_for_string_parameter(
                    self, f"/careervp/{constants.ENVIRONMENT}/jwt-private-key"
                ),
                "JWT_PUBLIC_KEY": ssm.StringParameter.value_for_string_parameter(
                    self, f"/careervp/{constants.ENVIRONMENT}/jwt-public-key"
                ),
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": constants.ENVIRONMENT,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "TABLE_NAME": db.table_name,
                "IDEMPOTENCY_TABLE_NAME": idempotency_table.table_name,
                "CV_BUCKET_NAME": cv_bucket.bucket_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(constants.API_HANDLER_LAMBDA_TIMEOUT),
            memory_size=constants.API_HANDLER_LAMBDA_MEMORY_SIZE,
            # Note: Common layer removed to stay under 250MB Lambda size limit
            # See commit 8dd795e for details - layer caused 283MB > 250MB limit
            # layers=[self._build_common_layer()],
            role=role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        # Legacy /api/* routes removed. Canonical route registration lives in
        # _add_openapi_contract_routes().
        return lambda_function

    def _add_vpr_lambda_integration(
        self,
        api_resource: aws_apigateway.Resource,
        role: iam.Role,
        db: dynamodb.TableV2,
        appconfig_app_name: str,
    ) -> _lambda.Function:
        function_name = self.naming.lambda_name(constants.VPR_GENERATOR_FEATURE)
        log_group = logs.LogGroup(
            self,
            f"{constants.VPR_GENERATOR_LAMBDA}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            self,
            constants.VPR_GENERATOR_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.vpr_handler.lambda_handler",
            function_name=function_name,
            description="Updated for JSON response parsing and improved VPR generation",
            environment={
                "DYNAMODB_TABLE_NAME": db.table_name,
                constants.POWERTOOLS_SERVICE_NAME: "careervp-vpr",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": constants.ENVIRONMENT,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(120),
            memory_size=1024,
            role=role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        # Legacy /api/* routes removed. Canonical route registration lives in
        # _add_openapi_contract_routes().
        return lambda_function

    def _add_company_research_lambda_integration(
        self,
        api_resource: aws_apigateway.Resource,
        role: iam.Role,
        db: dynamodb.TableV2,
        appconfig_app_name: str,
    ) -> _lambda.Function:
        function_name = self.naming.lambda_name(constants.COMPANY_RESEARCH_FEATURE)
        log_group = logs.LogGroup(
            self,
            f"{constants.COMPANY_RESEARCH_LAMBDA}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            self,
            constants.COMPANY_RESEARCH_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.company_research_handler.lambda_handler",
            function_name=function_name,
            environment={
                "DYNAMODB_TABLE_NAME": db.table_name,
                constants.POWERTOOLS_SERVICE_NAME: "careervp-company-research",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": constants.ENVIRONMENT,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(60),
            memory_size=512,
            role=role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        # Legacy /api/* routes removed. Canonical route registration lives in
        # _add_openapi_contract_routes().
        return lambda_function

    def _build_vpr_jobs_queue(self, dlq: aws_sqs.Queue) -> aws_sqs.Queue:
        """Build SQS queue for VPR async job processing."""
        sqs_key = kms.Key(
            self,
            "SQSKey",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,
        )
        queue = aws_sqs.Queue(
            self,
            constants.VPR_JOBS_QUEUE,
            queue_name=self.naming.queue_name(constants.VPR_JOBS_QUEUE),
            visibility_timeout=Duration.seconds(300),  # 5 minutes for worker timeout
            receive_message_wait_time=Duration.seconds(20),  # Long polling
            encryption=aws_sqs.QueueEncryption.KMS,
            encryption_master_key=sqs_key,
            dead_letter_queue=aws_sqs.DeadLetterQueue(
                queue=dlq,
                max_receive_count=3,
            ),
        )
        return queue

    def _build_vpr_jobs_dlq(self) -> aws_sqs.Queue:
        """Build SQS dead letter queue for failed VPR jobs."""
        return aws_sqs.Queue(
            self,
            constants.VPR_JOBS_DLQ,
            queue_name=self.naming.dlq_name(constants.VPR_JOBS_DLQ),
            encryption=aws_sqs.QueueEncryption.SQS_MANAGED,
        )

    def _build_cover_letter_jobs_dlq(self) -> aws_sqs.Queue:
        """Build SQS dead letter queue for failed cover letter jobs."""
        return aws_sqs.Queue(
            self,
            constants.COVER_LETTER_JOBS_DLQ,
            queue_name=self.naming.dlq_name(constants.COVER_LETTER_JOBS_DLQ),
            encryption=aws_sqs.QueueEncryption.SQS_MANAGED,
        )

    def _build_cover_letter_jobs_queue(self, dlq: aws_sqs.Queue) -> aws_sqs.Queue:
        """Build SQS queue for cover letter async job processing."""
        sqs_key = kms.Key(
            self,
            "CoverLetterSQSKey",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,
        )
        return aws_sqs.Queue(
            self,
            constants.COVER_LETTER_JOBS_QUEUE,
            queue_name=self.naming.queue_name(constants.COVER_LETTER_JOBS_QUEUE),
            visibility_timeout=Duration.seconds(300),
            receive_message_wait_time=Duration.seconds(20),
            encryption=aws_sqs.QueueEncryption.KMS,
            encryption_master_key=sqs_key,
            dead_letter_queue=aws_sqs.DeadLetterQueue(
                queue=dlq,
                max_receive_count=3,
            ),
        )

    def _build_interview_prep_jobs_dlq(self) -> aws_sqs.Queue:
        """Build SQS dead letter queue for failed interview prep jobs."""
        return aws_sqs.Queue(
            self,
            constants.INTERVIEW_PREP_JOBS_DLQ,
            queue_name=self.naming.dlq_name(constants.INTERVIEW_PREP_JOBS_DLQ),
            encryption=aws_sqs.QueueEncryption.SQS_MANAGED,
        )

    def _build_interview_prep_jobs_queue(self, dlq: aws_sqs.Queue) -> aws_sqs.Queue:
        """Build SQS queue for interview prep async job processing."""
        sqs_key = kms.Key(
            self,
            "InterviewPrepSQSKey",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,
        )
        return aws_sqs.Queue(
            self,
            constants.INTERVIEW_PREP_JOBS_QUEUE,
            queue_name=self.naming.queue_name(constants.INTERVIEW_PREP_JOBS_QUEUE),
            visibility_timeout=Duration.seconds(300),
            receive_message_wait_time=Duration.seconds(20),
            encryption=aws_sqs.QueueEncryption.KMS,
            encryption_master_key=sqs_key,
            dead_letter_queue=aws_sqs.DeadLetterQueue(
                queue=dlq,
                max_receive_count=3,
            ),
        )

    def _build_worker_dlq(self, worker_feature: str) -> aws_sqs.Queue:
        """Create a dedicated encrypted DLQ for a worker Lambda."""
        worker_id = worker_feature.replace("-", " ").title().replace(" ", "")
        return aws_sqs.Queue(
            self,
            f"{worker_id}Dlq",
            queue_name=self.naming.dlq_name(worker_feature),
            retention_period=Duration.days(14),
            encryption=aws_sqs.QueueEncryption.KMS_MANAGED,
        )

    def _add_vpr_submit_lambda_integration(
        self,
        api_resource: aws_apigateway.Resource,
        role: iam.Role,
        jobs_table: dynamodb.TableV2,
        results_bucket: s3.Bucket,
        queue: aws_sqs.Queue,
        appconfig_app_name: str,
    ) -> _lambda.Function:
        """Add VPR Submit Lambda integration - POST /api/vpr."""
        function_name = self.naming.lambda_name(constants.VPR_SUBMIT_FEATURE)
        log_group = logs.LogGroup(
            self,
            f"{constants.VPR_SUBMIT_LAMBDA}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            self,
            constants.VPR_SUBMIT_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.vpr_submit_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-vpr-submit",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": constants.ENVIRONMENT,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "VPR_JOBS_TABLE_NAME": jobs_table.table_name,
                "VPR_RESULTS_BUCKET_NAME": results_bucket.bucket_name,
                "SQS_QUEUE_URL": queue.queue_url,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(30),
            memory_size=256,
            role=role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        # Legacy /api/* routes removed. Canonical route registration lives in
        # _add_openapi_contract_routes().
        return lambda_function

    def _add_vpr_status_lambda_integration(
        self,
        api_resource: aws_apigateway.Resource,
        role: iam.Role,
        jobs_table: dynamodb.TableV2,
        results_bucket: s3.Bucket,
        appconfig_app_name: str,
    ) -> _lambda.Function:
        """Add VPR Status Lambda integration - GET /api/vpr/status/{job_id}."""
        function_name = self.naming.lambda_name(constants.VPR_STATUS_FEATURE)
        log_group = logs.LogGroup(
            self,
            f"{constants.VPR_STATUS_LAMBDA}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            self,
            constants.VPR_STATUS_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.vpr_status_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-vpr-status",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": constants.ENVIRONMENT,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "VPR_JOBS_TABLE_NAME": jobs_table.table_name,
                "VPR_RESULTS_BUCKET_NAME": results_bucket.bucket_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(10),
            memory_size=128,
            role=role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        # Legacy /api/* routes removed. Canonical route registration lives in
        # _add_openapi_contract_routes().
        return lambda_function

    def _add_vpr_sqs_worker_lambda_integration(
        self,
        role: iam.Role,
        jobs_table: dynamodb.TableV2,
        results_bucket: s3.Bucket,
        users_table: dynamodb.TableV2,
        queue: aws_sqs.Queue,
        appconfig_app_name: str,
    ) -> _lambda.Function:
        """Add legacy VPR SQS worker Lambda integration."""
        function_name = self.naming.lambda_name("vpr-sqs-worker")
        log_group = logs.LogGroup(
            self,
            "VprSqsWorkerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            self,
            "VprSqsWorkerLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.vpr_worker_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-vpr-sqs-worker",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": constants.ENVIRONMENT,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "VPR_JOBS_TABLE_NAME": jobs_table.table_name,
                "VPR_RESULTS_BUCKET_NAME": results_bucket.bucket_name,
                "DYNAMODB_TABLE_NAME": users_table.table_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=2,
            timeout=Duration.seconds(300),  # 5 minutes for VPR generation
            memory_size=1024,
            role=role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        # Add SQS event source
        lambda_function.add_event_source(
            eventsources.SqsEventSource(queue, batch_size=1)
        )

        return lambda_function

    def _add_cv_upload_worker_lambda(
        self,
        cv_bucket: s3.Bucket,
        cvs_table: dynamodb.TableV2,
        idempotency_table: dynamodb.TableV2,
        dlq: aws_sqs.Queue,
    ) -> _lambda.Function:
        """Create cv_upload_worker (S3 event -> Lambda) with an explicit DLQ."""
        function_name = self.naming.lambda_name("cv-upload-worker")
        log_group = logs.LogGroup(
            self,
            "CvUploadWorkerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self,
            "CvUploadWorkerLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.cv_upload_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-cv-upload-worker",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "JWT_PRIVATE_KEY": ssm.StringParameter.value_for_string_parameter(
                    self, f"/careervp/{constants.ENVIRONMENT}/jwt-private-key"
                ),
                "JWT_PUBLIC_KEY": ssm.StringParameter.value_for_string_parameter(
                    self, f"/careervp/{constants.ENVIRONMENT}/jwt-public-key"
                ),
                "TABLE_NAME": cvs_table.table_name,
                "IDEMPOTENCY_TABLE_NAME": idempotency_table.table_name,
                "CV_BUCKET_NAME": cv_bucket.bucket_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            timeout=Duration.seconds(300),
            memory_size=512,
            tracing=_lambda.Tracing.ACTIVE,
            dead_letter_queue_enabled=True,
            dead_letter_queue=dlq,
            retry_attempts=2,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        # S3 object creation starts background parsing/normalization work.
        lambda_function.add_event_source(
            eventsources.S3EventSource(
                cv_bucket,
                events=[s3.EventType.OBJECT_CREATED],
            )
        )

        # Least-privilege data access for this worker's responsibilities.
        cv_bucket.grant_read(lambda_function)
        cvs_table.grant_read_write_data(lambda_function)
        idempotency_table.grant_read_write_data(lambda_function)
        return lambda_function

    def _add_vpr_worker_stream_lambda(
        self,
        jobs_table: dynamodb.TableV2,
        artifacts_table: dynamodb.TableV2,
        dlq: aws_sqs.Queue,
    ) -> _lambda.Function:
        """Create vpr_worker (DynamoDB stream -> Lambda) with stream failure DLQ."""
        function_name = self.naming.lambda_name("vpr-worker")
        log_group = logs.LogGroup(
            self,
            "vpr-workerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self,
            "vpr-worker",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.vpr_worker_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-vpr-worker",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "VPR_JOBS_TABLE_NAME": jobs_table.table_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            timeout=Duration.seconds(300),
            memory_size=1024,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=2,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        # ASYNC_004: failed stream batches are sent to a worker-specific DLQ.
        lambda_function.add_event_source(
            eventsources.DynamoEventSource(
                jobs_table,
                starting_position=_lambda.StartingPosition.LATEST,
                batch_size=1,
                bisect_batch_on_error=True,
                retry_attempts=2,
                on_failure=eventsources.SqsDlq(dlq),
            )
        )

        jobs_table.grant_stream_read(lambda_function)
        jobs_table.grant_read_write_data(lambda_function)
        artifacts_table.grant_read_write_data(lambda_function)
        return lambda_function

    def _add_cv_tailor_worker_lambda(
        self,
        artifacts_table: dynamodb.TableV2,
        cvs_table: dynamodb.TableV2,
        dlq: aws_sqs.Queue,
    ) -> _lambda.Function:
        """Create cv_tailor_worker on artifacts table stream updates."""
        function_name = self.naming.lambda_name("cv-tailor-worker")
        log_group = logs.LogGroup(
            self,
            "CvTailorWorkerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self,
            "CvTailorWorkerLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.cv_tailoring_handler.handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-cv-tailor-worker",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "TABLE_NAME": cvs_table.table_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            timeout=Duration.seconds(300),
            memory_size=512,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=2,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        lambda_function.add_event_source(
            eventsources.DynamoEventSource(
                artifacts_table,
                starting_position=_lambda.StartingPosition.LATEST,
                batch_size=1,
                bisect_batch_on_error=True,
                retry_attempts=2,
                on_failure=eventsources.SqsDlq(dlq),
            )
        )

        artifacts_table.grant_stream_read(lambda_function)
        artifacts_table.grant_read_write_data(lambda_function)
        cvs_table.grant_read_write_data(lambda_function)
        return lambda_function

    def _add_cover_letter_worker_lambda(
        self,
        artifacts_table: dynamodb.TableV2,
        applications_table: dynamodb.TableV2,
        dlq: aws_sqs.Queue,
    ) -> _lambda.Function:
        """Create cover_letter_worker triggered by SQS queue."""
        function_name = self.naming.lambda_name("cover-letter-worker")
        log_group = logs.LogGroup(
            self,
            "CoverLetterWorkerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self,
            "CoverLetterWorkerLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.cover_letter_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-cover-letter-worker",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "DYNAMODB_TABLE_NAME": artifacts_table.table_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            timeout=Duration.seconds(300),
            memory_size=512,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=2,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        lambda_function.add_event_source(
            eventsources.SqsEventSource(
                self.cover_letter_jobs_queue,
                batch_size=1,
            )
        )

        self.cover_letter_jobs_queue.grant_consume_messages(lambda_function)
        artifacts_table.grant_read_write_data(lambda_function)
        applications_table.grant_read_write_data(lambda_function)
        return lambda_function

    def _add_interview_prep_worker_lambda(
        self,
        artifacts_table: dynamodb.TableV2,
        applications_table: dynamodb.TableV2,
        dlq: aws_sqs.Queue,
    ) -> _lambda.Function:
        """Create interview_prep_worker triggered by SQS queue."""
        function_name = self.naming.lambda_name("interview-prep-worker")
        log_group = logs.LogGroup(
            self,
            "InterviewPrepWorkerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self,
            "InterviewPrepWorkerLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.interview_prep_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-interview-prep-worker",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "DYNAMODB_TABLE_NAME": artifacts_table.table_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            timeout=Duration.seconds(300),
            memory_size=512,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=2,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        lambda_function.add_event_source(
            eventsources.SqsEventSource(
                self.interview_prep_jobs_queue,
                batch_size=1,
            )
        )

        self.interview_prep_jobs_queue.grant_consume_messages(lambda_function)
        artifacts_table.grant_read_write_data(lambda_function)
        applications_table.grant_read_write_data(lambda_function)
        return lambda_function

    def _add_cv_tailoring_lambda_integration(
        self,
        api_resource: aws_apigateway.Resource,
        role: iam.Role,
        db: dynamodb.TableV2,
        appconfig_app_name: str,
        idempotency_table: dynamodb.TableV2,
    ) -> _lambda.Function:
        """Add CV Tailoring Lambda integration - POST /api/cv-tailoring."""
        function_name = self.naming.lambda_name(constants.CV_TAILOR_LAMBDA.lower())
        log_group = logs.LogGroup(
            self,
            f"{constants.CV_TAILOR_LAMBDA}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            self,
            constants.CV_TAILOR_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.cv_tailoring_handler.handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-cv-tailoring",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": constants.ENVIRONMENT,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "TABLE_NAME": db.table_name,
                "IDEMPOTENCY_TABLE_NAME": idempotency_table.table_name,
                "AUTHORIZER_DISABLED": "true"
                if constants.ENVIRONMENT != "prod"
                else "false",
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(120),  # 2 minutes for LLM processing
            memory_size=512,
            role=role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        # Legacy /api/* routes removed. Canonical route registration lives in
        # _add_openapi_contract_routes().
        return lambda_function

    def _add_auth_lambda(self) -> _lambda.Function:
        function_name = self.naming.lambda_name("auth-api")
        log_group = logs.LogGroup(
            self,
            "AuthApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self,
            "AuthApiLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.auth_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-auth-api",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "TABLE_NAME": self.api_db.users_table.table_name,
                "TOKEN_BLACKLIST_TABLE_NAME": self.api_db.idempotency_db.table_name,
                "JWT_PRIVATE_KEY": ssm.StringParameter.value_for_string_parameter(
                    self, f"/careervp/{constants.ENVIRONMENT}/jwt-private-key"
                ),
                "JWT_PUBLIC_KEY": ssm.StringParameter.value_for_string_parameter(
                    self, f"/careervp/{constants.ENVIRONMENT}/jwt-public-key"
                ),
                "COGNITO_CLIENT_ID": self.cognito_client_id,
                "COGNITO_USER_POOL_ID": self.cognito_user_pool.user_pool_id,
                "ENVIRONMENT": constants.ENVIRONMENT,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            role=self.lambda_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

    def _add_health_lambda(self) -> _lambda.Function:
        function_name = self.naming.lambda_name("health-api")
        log_group = logs.LogGroup(
            self,
            "HealthApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self,
            "HealthApiLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.health_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-health-api",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                "DYNAMODB_TABLE_NAME": self.api_db.users_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            timeout=Duration.seconds(10),
            memory_size=128,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            role=self.lambda_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

    def _add_user_lambda(self) -> _lambda.Function:
        function_name = self.naming.lambda_name("user-api")
        log_group = logs.LogGroup(
            self,
            "UserApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self,
            "UserApiLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.user_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-user-api",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "TABLE_NAME": self.api_db.users_table.table_name,
                "USERS_TABLE_NAME": self.api_db.users_table.table_name,
                "JWT_PRIVATE_KEY": ssm.StringParameter.value_for_string_parameter(
                    self, f"/careervp/{constants.ENVIRONMENT}/jwt-private-key"
                ),
                "JWT_PUBLIC_KEY": ssm.StringParameter.value_for_string_parameter(
                    self, f"/careervp/{constants.ENVIRONMENT}/jwt-public-key"
                ),
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            role=self.lambda_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

    def _add_job_lambda(self) -> _lambda.Function:
        function_name = self.naming.lambda_name("job-api")
        log_group = logs.LogGroup(
            self,
            "JobApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self,
            "JobApiLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.job_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-job-api",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "JOBS_TABLE_NAME": self.api_db.jobs_table.table_name,
                "JWT_PRIVATE_KEY": ssm.StringParameter.value_for_string_parameter(
                    self, f"/careervp/{constants.ENVIRONMENT}/jwt-private-key"
                ),
                "JWT_PUBLIC_KEY": ssm.StringParameter.value_for_string_parameter(
                    self, f"/careervp/{constants.ENVIRONMENT}/jwt-public-key"
                ),
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            role=self.lambda_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

    def _add_application_lambda(self) -> _lambda.Function:
        function_name = self.naming.lambda_name("application-api")
        log_group = logs.LogGroup(
            self,
            "ApplicationApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self,
            "ApplicationApiLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.application_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-application-api",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "JOBS_TABLE_NAME": self.api_db.jobs_table.table_name,
                "APPLICATIONS_TABLE_NAME": self.api_db.applications_table.table_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            role=self.lambda_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

    def _add_api_authorizer_lambda(self) -> _lambda.Function:
        function_name = self.naming.lambda_name("api-authorizer")
        return _lambda.Function(
            self,
            "ApiAuthorizerLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.api_gateway_authorizer.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-api-authorizer",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                "JWT_PRIVATE_KEY": ssm.StringParameter.value_for_string_parameter(
                    self, f"/careervp/{constants.ENVIRONMENT}/jwt-private-key"
                ),
                "JWT_PUBLIC_KEY": ssm.StringParameter.value_for_string_parameter(
                    self, f"/careervp/{constants.ENVIRONMENT}/jwt-public-key"
                ),
            },
            timeout=Duration.seconds(10),
            memory_size=256,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            role=self.lambda_role,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

    def _add_gap_lambda(self) -> _lambda.Function:
        function_name = self.naming.lambda_name("gap-api")
        log_group = logs.LogGroup(
            self,
            "GapApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self,
            "GapApiLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.gap_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-gap-api",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                # Gap questions use pk/sk keys — must point to the users table, not artifacts_table.
                "USERS_TABLE_NAME": self.api_db.db.table_name,
                "DYNAMODB_TABLE_NAME": self.api_db.db.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            role=self.lambda_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

    def _add_cover_letter_lambda(self) -> _lambda.Function:
        function_name = self.naming.lambda_name("cover-letter-api")
        log_group = logs.LogGroup(
            self,
            "CoverLetterApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self,
            "CoverLetterApiLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.cover_letter_submit_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-cover-letter-api",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "DYNAMODB_TABLE_NAME": self.api_db.artifacts_table.table_name,
                "SQS_QUEUE_URL": self.cover_letter_jobs_queue.queue_url,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            timeout=Duration.seconds(60),
            memory_size=256,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            role=self.lambda_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )
        self.cover_letter_jobs_queue.grant_send_messages(lambda_function)
        return lambda_function

    def _add_interview_prep_lambda(self) -> _lambda.Function:
        function_name = self.naming.lambda_name("interview-prep-api")
        log_group = logs.LogGroup(
            self,
            "InterviewPrepApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self,
            "InterviewPrepApiLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.interview_prep_submit_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-interview-prep-api",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "DYNAMODB_TABLE_NAME": self.api_db.artifacts_table.table_name,
                "SQS_QUEUE_URL": self.interview_prep_jobs_queue.queue_url,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            timeout=Duration.seconds(60),
            memory_size=256,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            role=self.lambda_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )
        self.interview_prep_jobs_queue.grant_send_messages(lambda_function)
        return lambda_function

    def _add_cover_letter_status_lambda(self) -> _lambda.Function:
        """Lambda for GET /cover-letter/* status and list routes."""
        function_name = self.naming.lambda_name("cover-letter-status")
        log_group = logs.LogGroup(
            self,
            "CoverLetterStatusLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self,
            "CoverLetterStatusLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.cover_letter_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-cover-letter-status",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "DYNAMODB_TABLE_NAME": self.api_db.artifacts_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            role=self.lambda_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

    def _add_interview_prep_status_lambda(self) -> _lambda.Function:
        """Lambda for GET /interview-prep/* status and list routes."""
        function_name = self.naming.lambda_name("interview-prep-status")
        log_group = logs.LogGroup(
            self,
            "InterviewPrepStatusLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self,
            "InterviewPrepStatusLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.interview_prep_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-interview-prep-status",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "DYNAMODB_TABLE_NAME": self.api_db.artifacts_table.table_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            role=self.lambda_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

    def _get_or_create_path_resource(self, path: str) -> aws_apigateway.Resource:
        current: aws_apigateway.IResource = self.rest_api.root
        parts = [segment for segment in path.split("/") if segment]
        for segment in parts:
            current = current.get_resource(segment) or current.add_resource(segment)
        return cast(aws_apigateway.Resource, current)

    def _add_route_method(
        self,
        path: str,
        method: str,
        handler: _lambda.Function,
    ) -> None:
        resource = self._get_or_create_path_resource(path)
        # Per auth_and_authorizer_spec.yaml:
        # - Public (unprotected): /health, /auth/register, /auth/login
        # - Protected: /auth/refresh and all other routes
        public_paths = {"/health", "/auth/register", "/auth/login", "/auth/refresh"}
        is_public_route = path in public_paths
        resource.add_method(
            http_method=method,
            integration=aws_apigateway.LambdaIntegration(handler=handler),
            authorizer=None if is_public_route else self.api_authorizer,
            authorization_type=(
                aws_apigateway.AuthorizationType.NONE
                if is_public_route
                else aws_apigateway.AuthorizationType.COGNITO
            ),
        )

    def _add_openapi_contract_routes(self) -> None:
        # Canonical route surface (I7).
        route_map: list[tuple[str, str, _lambda.Function]] = [
            ("/health", "GET", self.health_api_func),
            ("/auth/register", "POST", self.auth_api_func),
            ("/auth/login", "POST", self.auth_api_func),
            ("/auth/refresh", "POST", self.auth_api_func),
            ("/users/me", "GET", self.user_api_func),
            ("/users/me", "PUT", self.user_api_func),
            ("/users/me/usage", "GET", self.user_api_func),
            ("/users/me/trial/reset", "POST", self.user_api_func),
            ("/users/me/cv", "POST", self.cv_upload_func),
            ("/users/me/cv", "GET", self.user_api_func),
            ("/jobs", "POST", self.job_api_func),
            ("/jobs", "GET", self.job_api_func),
            ("/jobs/{jobId}", "GET", self.job_api_func),
            ("/gap-analysis/questions", "POST", self.gap_api_func),
            ("/jobs/{jobId}/gap-questions", "POST", self.gap_api_func),
            ("/jobs/{jobId}/gap-questions", "GET", self.gap_api_func),
            ("/jobs/{jobId}/gap-responses", "POST", self.gap_api_func),
            ("/applications/{application_id}", "GET", self.application_api_func),
            ("/vpr/generate", "POST", self.vpr_submit_func),
            ("/vpr/{vprId}/status", "GET", self.vpr_status_func),
            ("/vprs", "GET", self.vpr_status_func),
            ("/cv-tailoring/generate", "POST", self.cv_tailoring_func),
            ("/cv-tailoring/{cvTailoringId}/status", "GET", self.cv_tailoring_func),
            ("/cv-tailoring/{cvTailoringId}", "DELETE", self.cv_tailoring_func),
            ("/cv-tailorings", "GET", self.cv_tailoring_func),
            ("/cover-letter/generate", "POST", self.cover_letter_api_func),
            (
                "/cover-letter/{coverLetterId}/status",
                "GET",
                self.cover_letter_status_func,
            ),
            ("/cover-letters", "GET", self.cover_letter_status_func),
            ("/interview-prep/generate", "POST", self.interview_prep_api_func),
            (
                "/interview-prep/{interviewPrepId}/status",
                "GET",
                self.interview_prep_status_func,
            ),
            ("/interview-preps", "GET", self.interview_prep_status_func),
            ("/company-research/{jobId}", "GET", self.company_research_func),
            ("/company-research/fetch", "POST", self.company_research_func),
            ("/knowledge-base", "GET", self.company_research_func),
        ]
        for path, method, handler in route_map:
            self._add_route_method(path, method, handler)
