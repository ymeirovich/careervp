import careervp.constants as constants
from aws_cdk import CfnOutput, Duration, RemovalPolicy, aws_apigateway, aws_sqs
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_lambda_event_sources as eventsources
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from careervp.api_db_construct import ApiDbConstruct
from careervp.monitoring import CrudMonitoring
from careervp.naming_utils import NamingUtils
from careervp.waf_construct import WafToApiGatewayConstruct
from constructs import Construct


class ApiConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        appconfig_app_name: str,
        is_production_env: bool,
        naming: NamingUtils,
    ) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.naming = naming
        self.api_db = ApiDbConstruct(self, f"{id_}db", naming=naming)
        self.lambda_role = self._build_lambda_role(
            self.api_db.db, self.api_db.idempotency_db, self.api_db.cv_bucket
        )
        # self.common_layer = self._build_common_layer()  # TODO: Enable when layer is built
        self.rest_api = self._build_api_gw()
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

        # VPR Async Architecture - DLQ first, then Queue (DLQ must exist first)
        self.vpr_jobs_dlq = self._build_vpr_jobs_dlq()
        self.vpr_jobs_queue = self._build_vpr_jobs_queue(self.vpr_jobs_dlq)

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
        vpr_status_resource = vpr_resource.add_resource("status")
        self.vpr_status_func = self._add_vpr_status_lambda_integration(
            vpr_status_resource,
            self.lambda_role,
            self.api_db.jobs_table,
            self.api_db.vpr_results_bucket,
            appconfig_app_name,
        )

        # VPR Worker Lambda - SQS triggered
        self.vpr_worker_func = self._add_vpr_worker_lambda_integration(
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
        )
        # GET /swagger.css
        swagger_resource_css = rest_api.root.add_resource(
            constants.SWAGGER_CSS_RESOURCE
        )
        swagger_resource_css.add_method(
            http_method="GET",
            integration=aws_apigateway.LambdaIntegration(handler=dest_func),
        )
        # GET /swagger.js
        swagger_resource_js = rest_api.root.add_resource(constants.SWAGGER_JS_RESOURCE)
        swagger_resource_js.add_method(
            http_method="GET",
            integration=aws_apigateway.LambdaIntegration(handler=dest_func),
        )

        CfnOutput(
            self, id=constants.SWAGGER_URL, value=f"{rest_api.url}swagger"
        ).override_logical_id(constants.SWAGGER_URL)

    def _build_api_gw(self) -> aws_apigateway.RestApi:
        rest_api: aws_apigateway.RestApi = aws_apigateway.RestApi(
            self,
            "service-rest-api",
            rest_api_name=self.naming.api_name(constants.API_FEATURE),
            description="CareerVP API - AI-powered job application assistant",
            deploy_options=aws_apigateway.StageOptions(
                throttling_rate_limit=2, throttling_burst_limit=10
            ),
            cloud_watch_role=False,
        )

        CfnOutput(
            self, id=constants.APIGATEWAY, value=rest_api.url
        ).override_logical_id(constants.APIGATEWAY)
        return rest_api

    def _build_lambda_role(
        self,
        db: dynamodb.TableV2,
        idempotency_table: dynamodb.TableV2,
        cv_bucket: s3.Bucket,
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
                            resources=[db.table_arn, f"{db.table_arn}/index/*"],
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
                "ssm_parameters": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["ssm:GetParameter"],
                            resources=["arn:aws:ssm:*:*:parameter/careervp/*"],
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

    def _build_common_layer(self) -> PythonLayerVersion:
        return PythonLayerVersion(
            self,
            f"{self.id_}{constants.LAMBDA_LAYER_NAME}",
            entry=constants.COMMON_LAYER_BUILD_FOLDER,
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_14],
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
        )

        lambda_function = _lambda.Function(
            self,
            constants.CV_PARSER_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_14,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.cv_upload_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": constants.ENVIRONMENT,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "TABLE_NAME": db.table_name,
                "IDEMPOTENCY_TABLE_NAME": idempotency_table.table_name,
                "CV_BUCKET_NAME": cv_bucket.bucket_name,
                constants.ANTHROPIC_API_KEY_ENV_VAR: constants.ANTHROPIC_API_KEY_SSM_PARAM,
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(constants.API_HANDLER_LAMBDA_TIMEOUT),
            memory_size=constants.API_HANDLER_LAMBDA_MEMORY_SIZE,
            # layers=[self.common_layer],
            role=role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        # POST /api/cv - CV upload endpoint
        api_resource.add_method(
            http_method="POST",
            integration=aws_apigateway.LambdaIntegration(handler=lambda_function),
        )
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
        )

        lambda_function = _lambda.Function(
            self,
            constants.VPR_GENERATOR_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_14,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.vpr_handler.lambda_handler",
            function_name=function_name,
            description="Updated for JSON response parsing and improved VPR generation",
            environment={
                "DYNAMODB_TABLE_NAME": db.table_name,
                constants.POWERTOOLS_SERVICE_NAME: "careervp-vpr",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": constants.ENVIRONMENT,
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

        api_resource.add_method(
            http_method="POST",
            integration=aws_apigateway.LambdaIntegration(handler=lambda_function),
        )

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
        )

        lambda_function = _lambda.Function(
            self,
            constants.COMPANY_RESEARCH_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_14,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.company_research_handler.lambda_handler",
            function_name=function_name,
            environment={
                "DYNAMODB_TABLE_NAME": db.table_name,
                constants.POWERTOOLS_SERVICE_NAME: "careervp-company-research",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": constants.ENVIRONMENT,
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

        api_resource.add_method(
            http_method="POST",
            integration=aws_apigateway.LambdaIntegration(handler=lambda_function),
        )

        return lambda_function

    def _build_vpr_jobs_queue(self, dlq: aws_sqs.Queue) -> aws_sqs.Queue:
        """Build SQS queue for VPR async job processing."""
        queue = aws_sqs.Queue(
            self,
            constants.VPR_JOBS_QUEUE,
            queue_name=self.naming.queue_name(constants.VPR_JOBS_QUEUE),
            visibility_timeout=Duration.seconds(300),  # 5 minutes for worker timeout
            receive_message_wait_time=Duration.seconds(20),  # Long polling
            encryption=aws_sqs.QueueEncryption.SQS_MANAGED,
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
        )

        lambda_function = _lambda.Function(
            self,
            constants.VPR_SUBMIT_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_14,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.vpr_submit_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-vpr-submit",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": constants.ENVIRONMENT,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "JOBS_TABLE_NAME": jobs_table.table_name,
                "VPR_RESULTS_BUCKET_NAME": results_bucket.bucket_name,
                "SQS_QUEUE_URL": queue.queue_url,
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

        # POST /api/vpr
        api_resource.add_method(
            http_method="POST",
            integration=aws_apigateway.LambdaIntegration(handler=lambda_function),
        )

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
        )

        lambda_function = _lambda.Function(
            self,
            constants.VPR_STATUS_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_14,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.vpr_status_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-vpr-status",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": constants.ENVIRONMENT,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "JOBS_TABLE_NAME": jobs_table.table_name,
                "VPR_RESULTS_BUCKET_NAME": results_bucket.bucket_name,
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

        # GET /api/vpr/status/{job_id}
        api_resource.add_method(
            http_method="GET",
            integration=aws_apigateway.LambdaIntegration(handler=lambda_function),
        )

        return lambda_function

    def _add_vpr_worker_lambda_integration(
        self,
        role: iam.Role,
        jobs_table: dynamodb.TableV2,
        results_bucket: s3.Bucket,
        users_table: dynamodb.TableV2,
        queue: aws_sqs.Queue,
        appconfig_app_name: str,
    ) -> _lambda.Function:
        """Add VPR Worker Lambda integration - SQS triggered for async processing."""
        function_name = self.naming.lambda_name(constants.VPR_WORKER_FEATURE)
        log_group = logs.LogGroup(
            self,
            f"{constants.VPR_WORKER_LAMBDA}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
        )

        lambda_function = _lambda.Function(
            self,
            constants.VPR_WORKER_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_14,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.vpr_worker_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-vpr-worker",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": constants.ENVIRONMENT,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "JOBS_TABLE_NAME": jobs_table.table_name,
                "VPR_RESULTS_BUCKET_NAME": results_bucket.bucket_name,
                "DYNAMODB_TABLE_NAME": users_table.table_name,
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
