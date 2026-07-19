import json
import os
import re
from typing import cast

from aws_cdk import (
    Aws,
    CfnOutput,
    CfnResource,
    Duration,
    RemovalPolicy,
    aws_apigateway,
    aws_sqs,
)
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_codedeploy as codedeploy
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_lambda_event_sources as eventsources
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ssm as ssm
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from constructs import Construct

from . import constants
from .api_db_construct import ApiDbConstruct
from .artifact_chain_construct import ArtifactChainConstruct
from .crud_features_nested_stack import CrudFeaturesNestedStack
from .monitoring import CrudMonitoring
from .naming_utils import NamingUtils
from .rehome_map import rehome_cfn
from .scratch_deployment import (
    ScratchDeploymentSettings,
    ssm_parameter_name,
    validate_scratch_boundary,
)
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
        scratch_settings: ScratchDeploymentSettings | None = None,
    ) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.naming = naming
        if scratch_settings is not None:
            validate_scratch_boundary(
                scratch_settings,
                environment=naming.environment,
                region=naming.region,
                account=naming.account_id,
            )
        self.scratch_mode = scratch_settings is not None
        self.allowed_origins = (
            scratch_settings.allowed_origin
            if scratch_settings is not None
            else self.node.try_get_context("allowed_origins")
            or "https://main.d3j2wnm8g5clnw.amplifyapp.com,https://front-ui-update-amplify1.d3j2wnm8g5clnw.amplifyapp.com,https://ui-upgrade.d3j2wnm8g5clnw.amplifyapp.com,https://app.careervp.com,https://dev.careervp.com,https://stage.careervp.com,http://localhost:3000"
        )
        self.cognito_client_id = cognito_client_id
        self.cognito_user_pool = user_pool
        self._api_permission_scopes: dict[str, set[str]] = {}
        # P-26 Job 1: single nested stack that re-homes every explicitly-named,
        # non-stateful feature resource off the near-limit parent template. Created
        # first so ApiDbConstruct can parent its async queues here too. Empty at
        # construction (no dependencies), so it never introduces a parent->nested
        # cycle. See crud_features_nested_stack.py + rehome_map.py.
        self._crud_features = CrudFeaturesNestedStack(
            self,
            "CrudFeatures",
            naming=naming,
        )
        self._rehome_features_enabled = (
            self.node.try_get_context("p26_rehome_features") == "true"
        )
        self._features: Construct = (
            self._crud_features if self._rehome_features_enabled else self
        )
        self.api_db = ApiDbConstruct(
            self,
            f"{id_}db",
            naming=naming,
            scratch_settings=scratch_settings,
            queue_scope=self._features if self._rehome_features_enabled else None,
        )
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
        self._grant_vpr_jobs_queue_access()
        self.api_authorizer = self._build_api_authorizer(user_pool)
        self.p23_deployment_application = codedeploy.LambdaApplication(
            self,
            "P23CanaryApplication",
            application_name=self.naming.resource_name("api-canary", "application"),
        )
        self.p23_deployment_role = iam.Role(
            self,
            "P23CodeDeployRole",
            assumed_by=iam.ServicePrincipal("codedeploy.amazonaws.com"),
            role_name=self.naming.role_name("codedeploy", "api-canary"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSCodeDeployRoleForLambda"
                )
            ],
        )
        self.p23_rollback_alarms = self._build_p23_rollback_alarms()
        self._p23_canary_alarms: list[cw.Alarm] = []
        self._p23_api_aliases: dict[str, _lambda.Alias] = {}

        root_resource = cast(aws_apigateway.Resource, self.rest_api.root)
        self.cv_upload_func = self._add_post_lambda_integration(
            root_resource,
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
            root_resource,
            self.lambda_role,
            self.api_db.jobs_table,
            self.api_db.vpr_results_bucket,
            self.vpr_jobs_queue,
            appconfig_app_name,
        )

        # VPR Status Lambda - GET /api/vpr/status/{job_id}
        self.vpr_status_func = self._add_vpr_status_lambda_integration(
            root_resource,
            self.lambda_role,
            self.api_db.jobs_table,
            self.api_db.vpr_results_bucket,
            appconfig_app_name,
        )

        # Keep the original SQS worker for existing queue-based VPR flow.
        self.vpr_sqs_worker_func = self._add_vpr_sqs_worker_lambda_integration(
            self._features,
            self.lambda_role,
            self.api_db.jobs_table,
            self.api_db.vpr_results_bucket,
            self.api_db.db,
            self.vpr_jobs_queue,
            appconfig_app_name,
        )
        self.vpr_dlq_handler_func = self._add_vpr_dlq_handler_lambda(
            self._features, self.vpr_jobs_dlq, self.api_db.jobs_table
        )
        self.company_research_func = self._add_company_research_lambda_integration(
            root_resource,
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
        self.cv_tailoring_func = self._add_cv_tailoring_lambda_integration(
            root_resource,
            self.lambda_role,
            self.api_db.db,
            appconfig_app_name,
            self.api_db.idempotency_db,
        )

        # Async worker DLQs (ASYNC_004): one DLQ per worker for failed events.
        self.cv_upload_worker_dlq = self._build_worker_dlq("cv-upload-worker")
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
        self.vpr_worker_func = self._add_vpr_worker_lambda(
            self._features,
            jobs_table=self.api_db.jobs_table,
            artifacts_table=self.api_db.artifacts_table,
            applications_table=self.api_db.applications_table,
            users_table=self.api_db.users_table,
            results_bucket=self.api_db.vpr_results_bucket,
        )
        self.cv_tailor_worker_func = self._add_cv_tailor_worker_lambda(
            self._features,
            artifacts_table=self.api_db.artifacts_table,
            cvs_table=self.api_db.cvs_table,
            dlq=self.cv_tailor_worker_dlq,
        )
        self.cover_letter_worker_func = self._add_cover_letter_worker_lambda(
            self._features,
            artifacts_table=self.api_db.artifacts_table,
            cvs_table=self.api_db.cvs_table,
            users_table=self.api_db.users_table,
            applications_table=self.api_db.applications_table,
            dlq=self.cover_letter_worker_dlq,
        )
        self.interview_prep_worker_func = self._add_interview_prep_worker_lambda(
            self._features,
            artifacts_table=self.api_db.artifacts_table,
            applications_table=self.api_db.applications_table,
            jobs_table=self.api_db.jobs_table,
            dlq=self.interview_prep_worker_dlq,
        )

        # Artifact Chain (FE-UI-031): CR worker + failure handlers + Step Functions.
        self._wire_artifact_chain(appconfig_app_name)

        # Billing infrastructure (S-006)
        self.billing_webhook_dlq = self._build_billing_webhook_dlq()
        self.billing_lambda = self._add_billing_lambda()
        self.billing_reconcile_lambda = self._add_billing_reconcile_lambda()
        self._add_billing_eventbridge_rule()
        self.billing_error_alarm = self._add_billing_error_alarm()

        # Export infrastructure (FE-UI-028)
        self.export_lambda = self._add_export_lambda()

        self._enable_p23_canary_deployments()
        self._add_openapi_contract_routes()

        self._build_swagger_endpoints(
            rest_api=self.rest_api,
            dest_func=self._p23_route_target(self.cv_upload_func),
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
            mode="dashboards",
        )

        # P-21: route the billing-error alarm to the on-call topic so it is not
        # silent (it is built before the topic exists, hence wired here).
        self.billing_error_alarm.add_alarm_action(
            cw_actions.SnsAction(self.monitoring.notification_topic)
        )
        for alarm in [*self.p23_rollback_alarms, *self._p23_canary_alarms]:
            alarm.add_alarm_action(
                cw_actions.SnsAction(self.monitoring.notification_topic)
            )

        if self.naming.environment == "dev":
            self._build_api_custom_domain()

        # P-11: WAF must exist in every environment; rule content is owned by
        # the follow-up WAF prompt.
        self.waf = WafToApiGatewayConstruct(
            self,
            f"{id_}waf",
            self.rest_api,
            naming=naming,
            feature=constants.API_FEATURE,
        )

        # P-26 Job 1: after every re-homed resource exists in CrudFeaturesNestedStack,
        # pin each named resource's deployed logical id so the human-gated cdk refactor
        # is a clean IMPORT (physical id preserved, no delete/create).
        if self._rehome_features_enabled:
            self._rehome_feature_logical_ids()

    def _build_api_custom_domain(self) -> None:
        cert = acm.Certificate.from_certificate_arn(
            self,
            "ApiDevCert",
            "arn:aws:acm:us-east-1:788159322332:certificate/d93bafb3-fe1a-4faa-9335-a9e868646bdb",
        )
        domain = aws_apigateway.DomainName(
            self,
            "ApiDevCustomDomain",
            domain_name="api.dev.careervp.com",
            certificate=cert,
            endpoint_type=aws_apigateway.EndpointType.REGIONAL,
            security_policy=aws_apigateway.SecurityPolicy.TLS_1_2,
        )
        aws_apigateway.BasePathMapping(
            self,
            "ApiDevBasePathMapping",
            domain_name=domain,
            rest_api=self.rest_api,
            stage=self.rest_api.deployment_stage,
        )
        CfnOutput(
            self,
            "ApiDevRegionalDomainName",
            value=domain.domain_name_alias_domain_name,
        ).override_logical_id("ApiDevRegionalDomainName")

    def register_ai_assist_routes(self, ai_assist_lambda: _lambda.IFunction) -> None:
        self.ai_assist_lambda = ai_assist_lambda
        self._add_route_method_with_integration(
            "/ai/assist",
            "POST",
            self._build_lambda_proxy_integration(ai_assist_lambda),
        )
        self._add_route_method(
            "/interview-prep/{interviewPrepId}",
            "PATCH",
            self.interview_prep_status_func,
        )

    def register_error_report_route(
        self, error_report_lambda: _lambda.IFunction
    ) -> None:
        """Wire POST /errors to the nested-stack error-report Lambda.

        Uses an AwsIntegration proxy (not LambdaIntegration) so the invoke
        permission lives in the nested stack and the parent only gains the
        unavoidable API Gateway Resource + POST/OPTIONS methods — keeping the
        near-limit parent stack as lean as possible.
        """
        self._add_route_method_with_integration(
            "/errors",
            "POST",
            self._build_lambda_proxy_integration(error_report_lambda),
        )

    def _build_swagger_endpoints(
        self, rest_api: aws_apigateway.RestApi, dest_func: _lambda.IFunction
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
        if self.scratch_mode:
            deploy_options = aws_apigateway.StageOptions(
                throttling_rate_limit=2,
                throttling_burst_limit=10,
                tracing_enabled=True,
                metrics_enabled=False,
                logging_level=aws_apigateway.MethodLoggingLevel.OFF,
            )
        else:
            access_log_group = logs.LogGroup(
                self,
                "ApiGatewayAccessLogGroup",
                retention=logs.RetentionDays.ONE_DAY,
                removal_policy=RemovalPolicy.DESTROY,
                encryption_key=self.logs_kms_key,
            )
            deploy_options = aws_apigateway.StageOptions(
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
            )
        rest_api: aws_apigateway.RestApi = aws_apigateway.RestApi(
            self,
            "service-rest-api",
            rest_api_name=self.naming.api_name(constants.API_FEATURE),
            description="CareerVP API - AI-powered job application assistant",
            default_cors_preflight_options=aws_apigateway.CorsOptions(
                allow_origins=(
                    [self.allowed_origins]
                    if self.scratch_mode
                    else self.allowed_origins.split(",")
                ),
                allow_methods=aws_apigateway.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "X-Amz-Date",
                    "X-Api-Key",
                    "X-Amz-Security-Token",
                ],
                max_age=Duration.seconds(60),
            ),
            deploy_options=deploy_options,
            cloud_watch_role=not self.scratch_mode,
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
            removal_policy=(
                RemovalPolicy.DESTROY if self.scratch_mode else RemovalPolicy.RETAIN
            ),
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

    def _build_p23_rollback_alarms(self) -> list[cw.Alarm]:
        """Create outcome-specific resolver alarms shared by every API canary.

        These intentionally observe resolver outcomes rather than aggregate HTTP
        401s: an incorrect ``sub -> user_id`` resolution can either look like a
        normal expired token or return an incorrect tenant's successful response.
        The P-24 authorizer remains dormant; these alarms are wired now for its
        eventual metrics and are non-breaching while no data is emitted.
        """
        alarms: list[tuple[str, str, str]] = [
            (
                "P23AuthResolverFailureAlarm",
                "AuthResolverFailure",
                "auth-resolver-failure",
            ),
            (
                "P23AuthResolverStepUpRequiredAlarm",
                "AuthResolverStepUpRequired",
                "auth-resolver-step-up-required",
            ),
        ]
        return [
            cw.Alarm(
                self,
                construct_id,
                alarm_name=self.naming.resource_name(feature, "alarm"),
                metric=cw.Metric(
                    namespace=constants.METRICS_NAMESPACE,
                    metric_name=metric_name,
                    dimensions_map={
                        constants.METRICS_DIMENSION_KEY: "careervp-api-authorizer"
                    },
                    period=Duration.minutes(1),
                    statistic="Sum",
                ),
                threshold=1,
                evaluation_periods=1,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
            for construct_id, metric_name, feature in alarms
        ]

    def _add_p23_canary_alias(
        self,
        function: _lambda.Function,
        *,
        feature: str,
    ) -> _lambda.Alias:
        """Attach a stable alias, error alarm, and CodeDeploy canary to one route Lambda."""
        alias = function.add_alias(f"live-{self.naming.environment}")
        error_alarm = cw.Alarm(
            self,
            f"P23{self._p23_construct_suffix(feature)}CanaryErrorAlarm",
            alarm_name=self.naming.resource_name(f"{feature}-canary-error", "alarm"),
            metric=alias.metric_errors(period=Duration.minutes(1), statistic="Sum"),
            threshold=1,
            evaluation_periods=1,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )
        self._p23_canary_alarms.append(error_alarm)
        codedeploy.LambdaDeploymentGroup(
            self,
            f"P23{self._p23_construct_suffix(feature)}CanaryDeploymentGroup",
            application=self.p23_deployment_application,
            alias=alias,
            deployment_group_name=self.naming.resource_name(
                f"{feature}-canary", "deployment-group"
            ),
            deployment_config=codedeploy.LambdaDeploymentConfig.CANARY_10_PERCENT_5_MINUTES,
            alarms=[error_alarm, *self.p23_rollback_alarms],
            auto_rollback=codedeploy.AutoRollbackConfig(
                deployment_in_alarm=True,
                failed_deployment=True,
                stopped_deployment=True,
            ),
            role=self.p23_deployment_role,
        )
        return alias

    @staticmethod
    def _p23_construct_suffix(feature: str) -> str:
        """Turn a kebab-case feature into a deterministic construct-id suffix."""
        return "".join(segment.title() for segment in feature.split("-"))

    def _enable_p23_canary_deployments(self) -> None:
        """Create P-23 canary aliases for every Lambda serving an API route."""
        route_functions: list[tuple[str, _lambda.Function]] = [
            ("cv-parser", self.cv_upload_func),
            ("vpr-submit", self.vpr_submit_func),
            ("vpr-status", self.vpr_status_func),
            ("company-research", self.company_research_func),
            ("auth-api", self.auth_api_func),
            ("health-api", self.health_api_func),
            ("user-api", self.user_api_func),
            ("job-api", self.job_api_func),
            ("application-api", self.application_api_func),
            ("gap-api", self.gap_api_func),
            ("cover-letter-api", self.cover_letter_api_func),
            ("cover-letter-status", self.cover_letter_status_func),
            ("interview-prep-api", self.interview_prep_api_func),
            ("interview-prep-status", self.interview_prep_status_func),
            ("cvtailor", self.cv_tailoring_func),
            ("billing", self.billing_lambda),
            ("export", self.export_lambda),
        ]
        self._p23_api_aliases = {
            function.node.path: self._add_p23_canary_alias(function, feature=feature)
            for feature, function in route_functions
        }

    def _p23_route_target(self, function: _lambda.IFunction) -> _lambda.IFunction:
        """Use the stable alias where P-23 protects an API-route Lambda."""
        return self._p23_api_aliases.get(function.node.path, function)

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
            removal_policy=(
                RemovalPolicy.DESTROY if self.scratch_mode else RemovalPolicy.RETAIN
            ),
            deletion_protection=not self.scratch_mode,
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
        # P-26 Job 1: the shared service role is re-homed into
        # CrudFeaturesNestedStack alongside every Lambda that assumes it and every
        # queue / state machine it is granted on. Keeping it in the parent while
        # its default policy references re-homed resources (and the nested Lambdas
        # depend on that policy) forms a parent<->nested CloudFormation cycle. Its
        # inline policies reference only PARENT tables/buckets/Cognito, a one-way
        # nested->parent import. Its deployed logical id is preserved for a clean
        # cdk refactor import (it is not in the RED-test map, so pinned here).
        role = iam.Role(
            self._features,
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
                                "dynamodb:DeleteItem",
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
                # P-26 Job 1: the vpr_jobs_queue SendMessage/ReceiveMessage grant
                # is NOT an inline policy here. The queue is re-homed into
                # CrudFeaturesNestedStack; embedding its ARN in this (parent) role
                # resource would make the role depend on the nested stack while the
                # nested stack depends on the role — a CloudFormation cycle. It is
                # instead attached to the role's separate default policy in
                # _grant_vpr_jobs_queue_access() (a distinct AWS::IAM::Policy
                # resource, so no cycle).
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
                                    f"{self._anthropic_parameter_name().lstrip('/')}"
                                ),
                                # P-06: JWT signing key material, fetched at
                                # runtime with decryption, never resolved into
                                # the Lambda env by CloudFormation.
                                self._secret_parameter_arn("jwt-private-key"),
                                self._secret_parameter_arn("jwt-public-key"),
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
                                "cognito-idp:AdminUserGlobalSignOut",
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
        cast(CfnResource, role.node.default_child).override_logical_id(
            "CareerVpCrudDevCrudServiceRoleArn305AAC1B"
        )
        return role

    def _grant_vpr_jobs_queue_access(self) -> None:
        """Grant the shared role SendMessage/ReceiveMessage on the vpr_jobs_queue.

        P-26 Job 1: the queue is re-homed into CrudFeaturesNestedStack, so this
        grant must NOT be an inline policy on the (parent) role — that would make
        the role depend on the nested stack and form a cycle. ``add_to_policy``
        targets the role's separate default policy (a distinct AWS::IAM::Policy),
        which may reference the nested queue ARN without a cycle.
        """
        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sqs:SendMessage",
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                ],
                resources=[self.vpr_jobs_queue.queue_arn],
                effect=iam.Effect.ALLOW,
            )
        )

    def _rehome_feature_logical_ids(self) -> None:
        """Preserve deployed logical ids for every re-homed named resource.

        P-26 Job 1 moves explicitly-named feature resources into
        CrudFeaturesNestedStack. So the move is a clean CloudFormation
        resource-import (``cdk refactor``) with no delete/create, each resource
        keeps its currently-deployed logical id byte-for-byte; only the containing
        template changes. Logical ids are matched by explicit physical name via
        rehome_map.REHOME_LOGICAL_IDS (dev-scoped; a no-op for other environments,
        which are not deployed for this migration). Auxiliary resources (IAM
        policies, permissions, event-source mappings) are not named/imported and
        keep their natural nested logical ids.
        """
        name_attr_by_type: tuple[tuple[type, str], ...] = (
            (_lambda.CfnFunction, "function_name"),
            (logs.CfnLogGroup, "log_group_name"),
            (aws_sqs.CfnQueue, "queue_name"),
            (sfn.CfnStateMachine, "state_machine_name"),
        )
        for node in self._features.node.find_all():
            if not isinstance(node, CfnResource):
                continue
            cfn_node: CfnResource = node
            for cfn_type, attr in name_attr_by_type:
                if isinstance(cfn_node, cfn_type):
                    physical = getattr(cfn_node, attr, None)
                    if isinstance(physical, str):
                        rehome_cfn(cfn_node, physical)
                    break

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
            "USERS_TABLE_NAME": self.api_db.users_table.table_name,
            "ALLOWED_ORIGINS": self.allowed_origins,
        }

    def _build_llm_env(self) -> dict[str, str]:
        """Build LLM-related environment variables (API key + model IDs).

        Spread this into every Lambda that calls the LLM client so model IDs
        can be changed with a cdk deploy rather than a code change.
        """
        return {
            constants.ANTHROPIC_API_KEY_ENV_VAR: self._anthropic_parameter_name(),
            constants.STRATEGIC_MODEL_ID_ENV_VAR: constants.STRATEGIC_MODEL_ID,
            constants.TEMPLATE_MODEL_ID_ENV_VAR: constants.TEMPLATE_MODEL_ID,
        }

    def _anthropic_parameter_name(self) -> str:
        return ssm_parameter_name(self.naming.environment, "anthropic-api-key")

    def _parameter_value(self, suffix: str) -> str:
        """Resolve live SSM values while keeping scratch synthesis lookup-free.

        Scratch authenticates with its isolated Cognito authorizer, so the retired
        self-managed JWT values and disabled payment-provider values are explicit
        non-secret placeholders. This avoids borrowing or creating live-tier SSM
        values outside the runbook's mutation approvals.
        """
        if self.scratch_mode:
            return f"scratch-disabled-{suffix}"
        return ssm.StringParameter.value_for_string_parameter(
            self, ssm_parameter_name(self.naming.environment, suffix)
        )

    def _secret_parameter_name(self, suffix: str) -> str:
        """Name-only SSM reference for secret material fetched at runtime (P-06).

        Unlike `_parameter_value`, this never resolves to the underlying
        secret in the synthesized template. The Lambda fetches the
        SecureString value itself at runtime with decryption
        (`careervp.logic.utils.secret_provider.get_ssm_secret`). Scratch mode
        keeps the same non-secret placeholder convention as `_parameter_value`.
        """
        if self.scratch_mode:
            return f"scratch-disabled-{suffix}"
        return ssm_parameter_name(self.naming.environment, suffix)

    def _secret_parameter_arn(self, suffix: str) -> str:
        return (
            f"arn:aws:ssm:{self.naming.region}:"
            f"{self.naming.account_id}:parameter/"
            f"{ssm_parameter_name(self.naming.environment, suffix).lstrip('/')}"
        )

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
            self._features,
            f"{constants.CV_PARSER_LAMBDA}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            self._features,
            constants.CV_PARSER_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.cv_upload_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                constants.JWT_PRIVATE_KEY_ENV_VAR: self._secret_parameter_name(
                    "jwt-private-key"
                ),
                constants.JWT_PUBLIC_KEY_ENV_VAR: self._secret_parameter_name(
                    "jwt-public-key"
                ),
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": self.naming.environment,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "TABLE_NAME": db.table_name,
                "IDEMPOTENCY_TABLE_NAME": idempotency_table.table_name,
                "CV_BUCKET_NAME": cv_bucket.bucket_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                **self._build_llm_env(),
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
                "CONFIGURATION_ENV": self.naming.environment,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                **self._build_llm_env(),
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
            self._features,
            f"{constants.COMPANY_RESEARCH_LAMBDA}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            self._features,
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
                "CONFIGURATION_ENV": self.naming.environment,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                **self._build_llm_env(),
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
            removal_policy=(
                RemovalPolicy.DESTROY if self.scratch_mode else RemovalPolicy.RETAIN
            ),
        )
        queue = aws_sqs.Queue(
            self._features,
            constants.VPR_JOBS_QUEUE,
            queue_name=self.naming.queue_name(constants.VPR_JOBS_QUEUE),
            visibility_timeout=Duration.minutes(10),  # must be >= Lambda timeout
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
            self._features,
            constants.VPR_JOBS_DLQ,
            queue_name=self.naming.dlq_name(constants.VPR_JOBS_DLQ),
            encryption=aws_sqs.QueueEncryption.SQS_MANAGED,
        )

    def _build_cover_letter_jobs_dlq(self) -> aws_sqs.Queue:
        """Build SQS dead letter queue for failed cover letter jobs."""
        return aws_sqs.Queue(
            self._features,
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
            removal_policy=(
                RemovalPolicy.DESTROY if self.scratch_mode else RemovalPolicy.RETAIN
            ),
        )
        return aws_sqs.Queue(
            self._features,
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
            self._features,
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
            removal_policy=(
                RemovalPolicy.DESTROY if self.scratch_mode else RemovalPolicy.RETAIN
            ),
        )
        return aws_sqs.Queue(
            self._features,
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
            self._features,
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
            self._features,
            f"{constants.VPR_SUBMIT_LAMBDA}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            self._features,
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
                "CONFIGURATION_ENV": self.naming.environment,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "VPR_JOBS_TABLE_NAME": jobs_table.table_name,
                "VPR_RESULTS_BUCKET_NAME": results_bucket.bucket_name,
                "SQS_QUEUE_URL": queue.queue_url,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                **self._build_llm_env(),
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
            self._features,
            f"{constants.VPR_STATUS_LAMBDA}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            self._features,
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
                "CONFIGURATION_ENV": self.naming.environment,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "VPR_JOBS_TABLE_NAME": jobs_table.table_name,
                "VPR_RESULTS_BUCKET_NAME": results_bucket.bucket_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                **self._build_llm_env(),
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
        scope: Construct,
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
            scope,
            "VprSqsWorkerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            scope,
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
                "CONFIGURATION_ENV": self.naming.environment,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "VPR_JOBS_TABLE_NAME": jobs_table.table_name,
                "VPR_RESULTS_BUCKET_NAME": results_bucket.bucket_name,
                "DYNAMODB_TABLE_NAME": users_table.table_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                **self._build_llm_env(),
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=2,
            timeout=Duration.minutes(
                10
            ),  # 10 minutes for VPR generation (single LLM call ~2:20 min)
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

    def _add_vpr_dlq_handler_lambda(
        self,
        scope: Construct,
        dlq: aws_sqs.Queue,
        jobs_table: dynamodb.TableV2,
    ) -> _lambda.Function:
        """Add Lambda triggered by VPR jobs DLQ to mark orphaned jobs FAILED."""
        function_name = self.naming.lambda_name("vpr-dlq-handler")
        log_group = logs.LogGroup(
            scope,
            "VprDlqHandlerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            scope,
            "VprDlqHandlerLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.vpr_dlq_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-vpr-dlq-handler",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "VPR_JOBS_TABLE_NAME": jobs_table.table_name,
            },
            tracing=_lambda.Tracing.ACTIVE,
            timeout=Duration.seconds(30),
            memory_size=128,
            role=self.lambda_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        lambda_function.add_event_source(eventsources.SqsEventSource(dlq, batch_size=1))

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
            self._features,
            "CvUploadWorkerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self._features,
            "CvUploadWorkerLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.cv_upload_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-cv-upload-worker",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                constants.JWT_PRIVATE_KEY_ENV_VAR: self._secret_parameter_name(
                    "jwt-private-key"
                ),
                constants.JWT_PUBLIC_KEY_ENV_VAR: self._secret_parameter_name(
                    "jwt-public-key"
                ),
                "TABLE_NAME": cvs_table.table_name,
                "IDEMPOTENCY_TABLE_NAME": idempotency_table.table_name,
                "CV_BUCKET_NAME": cv_bucket.bucket_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                **self._build_llm_env(),
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
        if not self.scratch_mode:
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
        # P-06: this Lambda has its own auto-generated role (no role= above),
        # so the shared lambda_role's JWT SSM grant does not cover it.
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    self._secret_parameter_arn("jwt-private-key"),
                    self._secret_parameter_arn("jwt-public-key"),
                ],
                effect=iam.Effect.ALLOW,
            )
        )
        return lambda_function

    def _add_vpr_worker_lambda(
        self,
        scope: Construct,
        jobs_table: dynamodb.TableV2,
        artifacts_table: dynamodb.TableV2,
        applications_table: dynamodb.TableV2,
        users_table: dynamodb.TableV2,
        results_bucket: s3.Bucket,
    ) -> _lambda.Function:
        """Create vpr_worker Lambda. Triggered exclusively by the SQS worker DLQ recovery
        path; the authoritative trigger is vpr-sqs-worker via the VPR jobs SQS queue."""
        function_name = self.naming.lambda_name("vpr-worker")
        log_group = logs.LogGroup(
            scope,
            "vpr-workerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            scope,
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
                "VPR_RESULTS_BUCKET_NAME": results_bucket.bucket_name,
                "DYNAMODB_TABLE_NAME": users_table.table_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                **self._build_llm_env(),
            },
            timeout=Duration.minutes(10),  # keep in sync with SQS worker — same handler
            memory_size=1024,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=2,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

        jobs_table.grant_read_write_data(lambda_function)
        artifacts_table.grant_read_write_data(lambda_function)
        applications_table.grant_read_write_data(lambda_function)
        users_table.grant_read_data(lambda_function)
        results_bucket.grant_read_write(lambda_function)
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    (
                        f"arn:aws:ssm:{self.naming.region}:"
                        f"{self.naming.account_id}:parameter/"
                        f"{self._anthropic_parameter_name().lstrip('/')}"
                    )
                ],
                effect=iam.Effect.ALLOW,
            )
        )
        return lambda_function

    def _add_cv_tailor_worker_lambda(
        self,
        scope: Construct,
        artifacts_table: dynamodb.TableV2,
        cvs_table: dynamodb.TableV2,
        dlq: aws_sqs.Queue,
    ) -> _lambda.Function:
        """Create cv_tailor_worker on artifacts table stream updates."""
        function_name = self.naming.lambda_name("cv-tailor-worker")
        log_group = logs.LogGroup(
            scope,
            "CvTailorWorkerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            scope,
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
                **self._build_llm_env(),
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
        scope: Construct,
        artifacts_table: dynamodb.TableV2,
        cvs_table: dynamodb.TableV2,
        users_table: dynamodb.TableV2,
        applications_table: dynamodb.TableV2,
        dlq: aws_sqs.Queue,
    ) -> _lambda.Function:
        """Create cover_letter_worker triggered by SQS queue."""
        function_name = self.naming.lambda_name("cover-letter-worker")
        log_group = logs.LogGroup(
            scope,
            "CoverLetterWorkerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            scope,
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
                "JOBS_TABLE_NAME": self.api_db.jobs_table.table_name,
                "COVER_LETTER_LEGACY_READ_ENABLED": "true",
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                **self._build_llm_env(),
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
        cvs_table.grant_read_data(lambda_function)
        users_table.grant_read_data(lambda_function)
        applications_table.grant_read_write_data(lambda_function)
        self.api_db.jobs_table.grant_read_data(lambda_function)
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    (
                        f"arn:aws:ssm:{self.naming.region}:"
                        f"{self.naming.account_id}:parameter/"
                        f"{self._anthropic_parameter_name().lstrip('/')}"
                    )
                ],
                effect=iam.Effect.ALLOW,
            )
        )
        return lambda_function

    def _add_interview_prep_worker_lambda(
        self,
        scope: Construct,
        artifacts_table: dynamodb.TableV2,
        applications_table: dynamodb.TableV2,
        jobs_table: dynamodb.TableV2,
        dlq: aws_sqs.Queue,
    ) -> _lambda.Function:
        """Create interview_prep_worker triggered by SQS queue."""
        function_name = self.naming.lambda_name("interview-prep-worker")
        log_group = logs.LogGroup(
            scope,
            "InterviewPrepWorkerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            scope,
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
                "VPR_JOBS_TABLE_NAME": jobs_table.table_name,
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                **self._build_llm_env(),
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
        jobs_table.grant_read_data(lambda_function)
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    (
                        f"arn:aws:ssm:{self.naming.region}:"
                        f"{self.naming.account_id}:parameter/"
                        f"{self._anthropic_parameter_name().lstrip('/')}"
                    )
                ],
                effect=iam.Effect.ALLOW,
            )
        )
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
            self._features,
            f"{constants.CV_TAILOR_LAMBDA}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )

        lambda_function = _lambda.Function(
            self._features,
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
                "CONFIGURATION_ENV": self.naming.environment,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                "CONFIGURATION_MAX_AGE_MINUTES": constants.CONFIGURATION_MAX_AGE_MINUTES,
                "TABLE_NAME": db.table_name,
                "IDEMPOTENCY_TABLE_NAME": idempotency_table.table_name,
                "VPR_JOBS_TABLE_NAME": self.api_db.jobs_table.table_name,
                "AUTHORIZER_DISABLED": "true"
                if self.naming.environment != "prod"
                else "false",
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                **self._build_llm_env(),
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

        self.api_db.jobs_table.grant_read_data(lambda_function)
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    (
                        f"arn:aws:ssm:{self.naming.region}:"
                        f"{self.naming.account_id}:parameter/"
                        f"{self._anthropic_parameter_name().lstrip('/')}"
                    )
                ],
                effect=iam.Effect.ALLOW,
            )
        )
        # Legacy /api/* routes removed. Canonical route registration lives in
        # _add_openapi_contract_routes().
        return lambda_function

    def _add_auth_lambda(self) -> _lambda.Function:
        function_name = self.naming.lambda_name("auth-api")
        log_group = logs.LogGroup(
            self._features,
            "AuthApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self._features,
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
                constants.JWT_PRIVATE_KEY_ENV_VAR: self._secret_parameter_name(
                    "jwt-private-key"
                ),
                constants.JWT_PUBLIC_KEY_ENV_VAR: self._secret_parameter_name(
                    "jwt-public-key"
                ),
                "COGNITO_CLIENT_ID": self.cognito_client_id,
                "COGNITO_USER_POOL_ID": self.cognito_user_pool.user_pool_id,
                "ENVIRONMENT": self.naming.environment,
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
            self._features,
            "HealthApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self._features,
            "HealthApiLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.health_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-health-api",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                "DYNAMODB_TABLE_NAME": self.api_db.users_table.table_name,
                **self._build_llm_env(),
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
            self._features,
            "UserApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self._features,
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
                constants.JWT_PRIVATE_KEY_ENV_VAR: self._secret_parameter_name(
                    "jwt-private-key"
                ),
                constants.JWT_PUBLIC_KEY_ENV_VAR: self._secret_parameter_name(
                    "jwt-public-key"
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
            self._features,
            "JobApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self._features,
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
                constants.JWT_PRIVATE_KEY_ENV_VAR: self._secret_parameter_name(
                    "jwt-private-key"
                ),
                constants.JWT_PUBLIC_KEY_ENV_VAR: self._secret_parameter_name(
                    "jwt-public-key"
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
            self._features,
            "ApplicationApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self._features,
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
        authorizer = _lambda.Function(
            self._features,
            "ApiAuthorizerLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.api_gateway_authorizer.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-api-authorizer",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                constants.JWT_PRIVATE_KEY_ENV_VAR: self._secret_parameter_name(
                    "jwt-private-key"
                ),
                constants.JWT_PUBLIC_KEY_ENV_VAR: self._secret_parameter_name(
                    "jwt-public-key"
                ),
                # P-24: presence of this env activates sub -> user_id surrogate
                # resolution at the edge; USERS_TABLE_NAME feeds the
                # link-by-verified-email owner lookup (email-index).
                constants.IDENTITY_MAP_TABLE_NAME_ENV: self.api_db.identity_map_table.table_name,
                "USERS_TABLE_NAME": self.api_db.users_table.table_name,
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
        # JIT conditional-put on the mapping + email-index read for linking.
        self.api_db.identity_map_table.grant_read_write_data(authorizer)
        self.api_db.users_table.grant_read_data(authorizer)
        return authorizer

    def _add_gap_lambda(self) -> _lambda.Function:
        function_name = self.naming.lambda_name("gap-api")
        log_group = logs.LogGroup(
            self._features,
            "GapApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self._features,
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
                "GAP_QUESTIONS_TABLE_NAME": self.api_db.db.table_name,
                "USERS_TABLE_NAME": self.api_db.db.table_name,
                "DYNAMODB_TABLE_NAME": self.api_db.db.table_name,
                "JOBS_TABLE_NAME": self.api_db.jobs_table.table_name,
                **self._build_llm_env(),
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

    def _wire_artifact_chain(self, appconfig_app_name: str) -> None:
        """Create the artifact-chain workers, failure handlers, and state machine.

        Additive (FE-UI-031): gated behind ARTIFACT_CHAIN_ENABLED (default "false").
        The CR worker is wired to consume company_research_queue; VPR/CV workers'
        task-token handling is deferred to their own tickets.
        """
        # The artifact-chain failure handlers, their dedicated role, and the
        # Step Functions state machine are created in the PARENT stack. These
        # resources carry explicit physical names (the two failure-handler
        # Lambdas, their log groups, and careervp-artifact-chain-statemachine-dev)
        # and are already deployed in CareerVpCrudDev, so relocating them into a
        # nested stack makes CloudFormation try to CREATE new resources under the
        # same physical names — a "resource already exists" failure. Only the
        # Monitoring nested stack (auto-named alarms/dashboards) is split out for
        # the 500-resource ceiling; explicitly-named resources must stay put
        # absent a CloudFormation resource-import migration.

        # FE-UI-035: build the dedicated failure-handler role once, before the
        # handlers, so neither reuses the shared role that holds states:* grants.
        self.failure_handler_role = self._build_failure_handler_role(self._features)
        self.cr_failure_handler_func = self._add_cr_failure_handler_lambda(
            self._features
        )
        self.artifact_failure_handler_func = self._add_artifact_failure_handler_lambda(
            self._features
        )
        self.company_research_worker_func = self._add_company_research_worker_lambda(
            appconfig_app_name
        )

        cv_tailoring_chain_target = _lambda.Function.from_function_arn(
            self,
            "ArtifactChainCvTailoringTarget",
            f"arn:{Aws.PARTITION}:lambda:{Aws.REGION}:{Aws.ACCOUNT_ID}:function:{self.naming.lambda_name('cvtailor')}",
        )

        self.artifact_chain = ArtifactChainConstruct(
            self._features,
            "ArtifactChain",
            naming=self.naming,
            company_research_queue=self.api_db.company_research_queue,
            vpr_jobs_queue=self.vpr_jobs_queue,
            cover_letter_queue=self.cover_letter_jobs_queue,
            interview_prep_queue=self.interview_prep_jobs_queue,
            cv_tailoring_func=cv_tailoring_chain_target,
            cr_failure_handler=self.cr_failure_handler_func,
            artifact_failure_handler=self.artifact_failure_handler_func,
            logs_kms_key=self.logs_kms_key,
        )
        chain_arn = self.artifact_chain.state_machine.state_machine_arn

        # Submit handlers start the artifact chain when dependency resolution
        # finds a genuinely absent upstream artifact.
        for submit_func in (
            self.vpr_submit_func,
            self.cover_letter_api_func,
            self.interview_prep_api_func,
            self.cv_tailoring_func,
        ):
            self.artifact_chain.state_machine.grant_start_execution(submit_func)
            submit_func.add_environment("STEP_FUNCTIONS_CHAIN_ARN", chain_arn)
            submit_func.add_environment(
                "ARTIFACT_CHAIN_ENABLED", self._artifact_chain_enabled()
            )

        # gap_handler starts the chain when the flag is on.
        self.artifact_chain.state_machine.grant_start_execution(self.gap_api_func)
        self.gap_api_func.add_environment("STEP_FUNCTIONS_CHAIN_ARN", chain_arn)
        self.gap_api_func.add_environment(
            "ARTIFACT_CHAIN_ENABLED", self._artifact_chain_enabled()
        )

        # CR worker signals task success/failure back to the chain.
        self.company_research_worker_func.add_environment(
            "STEP_FUNCTIONS_CHAIN_ARN", chain_arn
        )
        self.artifact_chain.state_machine.grant_task_response(
            self.company_research_worker_func
        )

        # FE-UI-053: the CR API handler enqueues research jobs onto the worker queue
        # instead of running research synchronously on the request path. Grant only
        # sqs:SendMessage scoped to the CR queue (no wildcard — FE-UI-035 invariant).
        self.api_db.company_research_queue.grant_send_messages(
            self.company_research_func
        )
        self.company_research_func.add_environment(
            "COMPANY_RESEARCH_QUEUE_URL",
            self.api_db.company_research_queue.queue_url,
        )
        self.artifact_chain.state_machine.grant_task_response(self.vpr_sqs_worker_func)
        self.artifact_chain.state_machine.grant_task_response(
            self.cover_letter_worker_func
        )
        self.artifact_chain.state_machine.grant_task_response(
            self.interview_prep_worker_func
        )

        CfnOutput(
            self,
            constants.ARTIFACT_CHAIN_ARN_OUTPUT,
            value=chain_arn,
        ).override_logical_id(constants.ARTIFACT_CHAIN_ARN_OUTPUT)

        # FE-UI-043: cancel handlers need states:StopExecution + DescribeExecution
        # scoped to the chain ARN (no states:* wildcard — FE-UI-035 invariant).
        cancel_sfn_statement = iam.PolicyStatement(
            actions=["states:StopExecution", "states:DescribeExecution"],
            resources=[chain_arn],
        )
        for cancel_func in (
            self.vpr_status_func,
            self.cover_letter_status_func,
            self.interview_prep_status_func,
            self.cv_tailoring_func,
            self.company_research_func,
        ):
            cancel_func.add_to_role_policy(cancel_sfn_statement)
            cancel_func.add_environment("STEP_FUNCTIONS_CHAIN_ARN", chain_arn)

        # FE-UI-043: orphan-cleanup reaper Lambda + hourly EventBridge schedule.
        self.artifact_cleanup_func = self._add_artifact_cleanup_lambda()
        self.api_db.applications_table.grant_read_write_data(self.artifact_cleanup_func)
        self.artifact_cleanup_func.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:DeleteObject"],
                resources=[self.api_db.vpr_results_bucket.arn_for_objects("results/*")],
            )
        )
        cleanup_rule = events.Rule(
            self,
            "ArtifactCleanupSchedule",
            schedule=events.Schedule.rate(Duration.hours(1)),
        )
        cleanup_rule.add_target(targets.LambdaFunction(self.artifact_cleanup_func))

    def _artifact_chain_enabled(self) -> str:
        """Resolve the ARTIFACT_CHAIN_ENABLED flag at synth time (default off)."""
        default = "true" if self.naming.environment == "dev" else "false"
        return os.environ.get("ARTIFACT_CHAIN_ENABLED", default)

    def _add_artifact_cleanup_lambda(self) -> _lambda.Function:
        """Orphan-cleanup reaper triggered hourly by EventBridge (FE-UI-043)."""
        function_name = self.naming.lambda_name(constants.ARTIFACT_CLEANUP_FEATURE)
        log_group = logs.LogGroup(
            self._features,
            "ArtifactCleanupLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self._features,
            constants.ARTIFACT_CLEANUP_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.artifact_cleanup_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-artifact-cleanup",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "VPR_RESULTS_BUCKET_NAME": self.api_db.vpr_results_bucket.bucket_name,
            },
            timeout=Duration.minutes(5),
            memory_size=256,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

    def _build_failure_handler_role(self, scope: Construct) -> iam.Role:
        """Dedicated least-privilege role for the artifact-chain failure handlers.

        FE-UI-035: the CR/artifact failure handlers previously reused the shared
        service role, which holds states:* grants (StartExecution / SendTaskResponse).
        Because the state machine must invoke these handlers, that shared edge closed
        a CloudFormation dependency cycle. This role grants ONLY what the handlers
        need: CloudWatch Logs (basic execution) and read/write on the applications
        table. X-Ray write perms are auto-added by CDK because tracing=ACTIVE; log
        KMS encryption is covered by the logs key's resource policy. It carries NO
        states:* permission, so it cannot re-form the cycle.
        """
        role = iam.Role(
            scope,
            constants.FAILURE_HANDLER_ROLE,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=self.naming.role_name(
                constants.LAMBDA_SERVICE_NAME, constants.FAILURE_HANDLER_FEATURE
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    managed_policy_name=(
                        f"service-role/{constants.LAMBDA_BASIC_EXECUTION_ROLE}"
                    )
                )
            ],
        )
        # Both handlers only UpdateItem/GetItem on the applications table.
        self.api_db.applications_table.grant_read_write_data(role)
        return role

    def _add_cr_failure_handler_lambda(self, scope: Construct) -> _lambda.Function:
        """Thin Lambda invoked by the chain when Company Research hard-fails."""
        function_name = self.naming.lambda_name(constants.CR_FAILURE_HANDLER_FEATURE)
        log_group = logs.LogGroup(
            scope,
            "CrFailureHandlerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            scope,
            "CrFailureHandlerLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.cr_failure_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-cr-failure-handler",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
            },
            timeout=Duration.seconds(30),
            memory_size=128,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            # FE-UI-035: dedicated role (no states:*) breaks the dependency cycle.
            role=self.failure_handler_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

    def _add_artifact_failure_handler_lambda(
        self, scope: Construct
    ) -> _lambda.Function:
        """Thin Lambda invoked by the chain when VPR or CV Tailoring fails."""
        function_name = self.naming.lambda_name(
            constants.ARTIFACT_FAILURE_HANDLER_FEATURE
        )
        log_group = logs.LogGroup(
            scope,
            "ArtifactFailureHandlerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            scope,
            "ArtifactFailureHandlerLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.artifact_failure_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-artifact-failure-handler",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
            },
            timeout=Duration.seconds(30),
            memory_size=128,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            # FE-UI-035: dedicated role (no states:*) breaks the dependency cycle.
            role=self.failure_handler_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )

    def _add_company_research_worker_lambda(
        self, appconfig_app_name: str
    ) -> _lambda.Function:
        """SQS worker that consumes company_research_queue (FE-UI-030/031).

        Signals the Step Functions chain via task tokens when running in the
        chain, or enqueues VPR directly in standalone mode.
        """
        function_name = self.naming.lambda_name(
            constants.COMPANY_RESEARCH_WORKER_FEATURE
        )
        log_group = logs.LogGroup(
            self._features,
            "CompanyResearchWorkerLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self._features,
            "CompanyResearchWorkerLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.company_research_worker_handler.lambda_handler",
            function_name=function_name,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: "careervp-company-research-worker",
                constants.POWER_TOOLS_LOG_LEVEL: "INFO",
                **self._build_shared_table_env(),
                "CONFIGURATION_APP": appconfig_app_name,
                "CONFIGURATION_ENV": self.naming.environment,
                "CONFIGURATION_NAME": constants.CONFIGURATION_NAME,
                # Standalone fallback target when the chain flag is off.
                "VPR_JOBS_QUEUE_URL": self.vpr_jobs_queue.queue_url,
                "VPR_JOBS_TABLE_NAME": self.api_db.jobs_table.table_name,
                "ARTIFACT_CHAIN_ENABLED": self._artifact_chain_enabled(),
                constants.LLM_CACHE_TABLE_NAME_ENV: self.llm_cache_table.table_name,
                **self._build_llm_env(),
            },
            # Aligned with the chain CR heartbeat (180s).
            timeout=Duration.seconds(120),
            memory_size=512,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            role=self.lambda_role,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )
        lambda_function.add_event_source(
            eventsources.SqsEventSource(
                self.api_db.company_research_queue, batch_size=1
            )
        )
        return lambda_function

    def _add_cover_letter_lambda(self) -> _lambda.Function:
        function_name = self.naming.lambda_name("cover-letter-api")
        log_group = logs.LogGroup(
            self._features,
            "CoverLetterApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self._features,
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
                "COVER_LETTER_LEGACY_READ_ENABLED": "true",
                **self._build_llm_env(),
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
            self._features,
            "InterviewPrepApiLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self._features,
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
                **self._build_llm_env(),
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
            self._features,
            "CoverLetterStatusLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self._features,
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
                "COVER_LETTER_LEGACY_READ_ENABLED": "true",
                **self._build_llm_env(),
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
            self._features,
            "InterviewPrepStatusLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        return _lambda.Function(
            self._features,
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
                **self._build_llm_env(),
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

    def _build_billing_webhook_dlq(self) -> aws_sqs.Queue:
        """Dead-letter queue for failed billing webhook events."""
        return aws_sqs.Queue(
            self._features,
            "BillingWebhookDlq",
            queue_name=self.naming.dlq_name(constants.BILLING_WEBHOOK_DLQ),
            retention_period=Duration.days(14),
            encryption=aws_sqs.QueueEncryption.KMS_MANAGED,
        )

    def _add_billing_lambda(self) -> _lambda.Function:
        """Billing handler Lambda for payment webhooks and checkout flows."""
        function_name = self.naming.lambda_name(constants.BILLING_FEATURE)
        log_group = logs.LogGroup(
            self._features,
            "BillingLambdaLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self._features,
            "BillingLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.billing_handler.handler",
            function_name=function_name,
            environment={
                "TABLE_NAME": self.api_db.db.table_name,
                "IDEMPOTENCY_TABLE_NAME": self.api_db.idempotency_db.table_name,
                "ALLOWED_ORIGINS": self.allowed_origins,
                constants.WEBHOOK_SECRET_ENV_VAR: self._secret_parameter_name(
                    "payment-provider-webhook-secret"
                ),
                constants.WEBHOOK_SECRET_PREVIOUS_ENV_VAR: self._secret_parameter_name(
                    "payment-provider-webhook-secret-previous"
                ),
                "PRICE_ID_MONTHLY": self._parameter_value(
                    "payment-provider-price-monthly"
                ),
                "PRICE_ID_QUARTERLY": self._parameter_value(
                    "payment-provider-price-quarterly"
                ),
                "PAYMENT_PROVIDER": "placeholder",
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )
        self.api_db.db.grant_read_write_data(lambda_function)
        self.api_db.idempotency_db.grant_read_write_data(lambda_function)
        # P-06: webhook signing secrets, fetched at runtime with decryption;
        # this Lambda has its own auto-generated role (no role= above).
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    self._secret_parameter_arn("payment-provider-webhook-secret"),
                    self._secret_parameter_arn(
                        "payment-provider-webhook-secret-previous"
                    ),
                ],
                effect=iam.Effect.ALLOW,
            )
        )
        return lambda_function

    def _add_export_lambda(self) -> _lambda.Function:
        """Export handler Lambda — generates DOCX artifacts and returns presigned URLs (FE-UI-028)."""
        function_name = self.naming.lambda_name(constants.EXPORT_FEATURE)
        log_group = logs.LogGroup(
            self._features,
            "ExportLambdaLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self._features,
            "ExportLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.export_handler.lambda_handler",
            function_name=function_name,
            environment={
                "TABLE_NAME": self.api_db.db.table_name,
                "ARTIFACTS_TABLE_NAME": self.api_db.artifacts_table.table_name,
                "VPR_RESULTS_BUCKET_NAME": self.api_db.vpr_results_bucket.bucket_name,
                "ARTIFACTS_BUCKET_NAME": self.api_db.artifacts_bucket.bucket_name,
                "ALLOWED_ORIGINS": self.allowed_origins,
            },
            timeout=Duration.seconds(29),
            memory_size=512,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )
        self.api_db.vpr_results_bucket.grant_read(lambda_function)
        self.api_db.artifacts_bucket.grant_read_write(lambda_function)
        self.api_db.artifacts_table.grant(lambda_function, "dynamodb:GetItem")
        self.api_db.db.grant(lambda_function, "dynamodb:GetItem", "dynamodb:Query")
        return lambda_function

    def _add_billing_reconcile_lambda(self) -> _lambda.Function:
        """Billing reconciliation Lambda triggered nightly by EventBridge."""
        function_name = self.naming.lambda_name(constants.BILLING_RECONCILE_FEATURE)
        log_group = logs.LogGroup(
            self._features,
            "BillingReconcileLambdaLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=self.logs_kms_key,
        )
        lambda_function = _lambda.Function(
            self._features,
            "BillingReconcileLambda",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.billing_reconcile_handler.handler",
            function_name=function_name,
            environment={
                "TABLE_NAME": self.api_db.db.table_name,
                "PAYMENT_PROVIDER": "placeholder",
            },
            timeout=Duration.seconds(300),
            memory_size=256,
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            log_group=log_group,
            logging_format=_lambda.LoggingFormat.JSON,
            system_log_level_v2=_lambda.SystemLogLevel.INFO,
            architecture=_lambda.Architecture.X86_64,
        )
        self.api_db.db.grant_read_write_data(lambda_function)
        return lambda_function

    def _add_billing_eventbridge_rule(self) -> events.Rule:
        """EventBridge scheduled rule — triggers billing reconciliation at 02:00 UTC."""
        return events.Rule(
            self,
            "BillingReconcileScheduleRule",
            schedule=events.Schedule.cron(hour="2", minute="0"),
            targets=[
                targets.LambdaFunction(
                    handler=self.billing_reconcile_lambda,
                    event=events.RuleTargetInput.from_object(
                        {"detail": {"action": "reconcile_subscriptions"}}
                    ),
                )
            ],
        )

    def _add_billing_error_alarm(self) -> cw.Alarm:
        """CloudWatch alarm fires on any billing Lambda error within 5 minutes."""
        return cw.Alarm(
            self,
            "BillingLambdaErrorAlarm",
            metric=self.billing_lambda.metric_errors(
                period=Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=1,
            evaluation_periods=1,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
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
        handler: _lambda.IFunction,
    ) -> None:
        handler = self._p23_route_target(handler)
        handler_key = handler.node.path
        permission_scope = self._permission_scope(path)
        handler_scopes = self._api_permission_scopes.setdefault(handler_key, set())
        scope_is_covered = any(
            permission_scope == existing_scope
            or (
                existing_scope.endswith("*")
                and permission_scope.startswith(existing_scope[:-1])
            )
            for existing_scope in handler_scopes
        )
        if not scope_is_covered:
            handler.add_permission(
                self._permission_id(permission_scope, "Routes"),
                principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
                action="lambda:InvokeFunction",
                source_arn=self.rest_api.arn_for_execute_api(
                    method="*",
                    path=permission_scope,
                    stage="*",
                ),
            )
            handler_scopes.add(permission_scope)
        self._add_route_method_with_integration(
            path,
            method,
            self._build_lambda_proxy_integration(handler),
        )

    @staticmethod
    def _permission_id(path: str, method: str) -> str:
        # Preserve trailing wildcard as "All" so "/jobs" and "/jobs/*" get distinct IDs.
        suffix = "All" if path.endswith("*") else ""
        normalized_path = (
            re.sub(r"[^A-Za-z0-9]+", " ", path.rstrip("*")).title().replace(" ", "")
        )
        return f"AllowApiGateway{method.title()}{normalized_path}{suffix}Invoke"

    @staticmethod
    def _permission_scope(path: str) -> str:
        segments = [segment for segment in path.split("/") if segment]
        if len(segments) <= 1:
            return path
        return f"/{segments[0]}/*"

    def _register_feature_proxy(
        self,
        path: str,
        handler: _lambda.IFunction,
        *,
        authorized: bool,
    ) -> None:
        """Register root and greedy ANY Lambda-proxy methods for one feature."""
        handler = self._p23_route_target(handler)
        resource = self._get_or_create_path_resource(path)
        proxy_resource = cast(
            aws_apigateway.Resource,
            resource.get_resource("{proxy+}") or resource.add_resource("{proxy+}"),
        )
        authorization_type = (
            aws_apigateway.AuthorizationType.COGNITO
            if authorized
            else aws_apigateway.AuthorizationType.NONE
        )
        authorizer = self.api_authorizer if authorized else None

        permission_scope = f"{path}*"
        handler.add_permission(
            self._permission_id(path, "ANY"),
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=self.rest_api.arn_for_execute_api(
                method="*",
                path=permission_scope,
                stage="*",
            ),
        )
        for target_resource in (resource, proxy_resource):
            target_resource.add_method(
                http_method="ANY",
                integration=self._build_lambda_proxy_integration(handler),
                authorizer=authorizer,
                authorization_type=authorization_type,
            )
        self._api_permission_scopes.setdefault(handler.node.path, set()).add(
            permission_scope
        )

    def _add_route_method_with_integration(
        self,
        path: str,
        method: str,
        integration: aws_apigateway.Integration,
    ) -> None:
        resource = self._get_or_create_path_resource(path)
        # Per auth_and_authorizer_spec.yaml:
        # - Public (unprotected): /health, /auth/register, /auth/login
        # - Protected: /auth/refresh and all other routes
        # - billing/webhook is public: verifies webhook signature itself (S-006)
        public_paths = {
            "/health",
            "/auth/register",
            "/auth/login",
            "/auth/refresh",
            "/billing/webhook",
            # Client error reports are forwarded by the Next.js SSR route with no
            # user token (errors fire on pre-auth pages); bounded by stage throttle.
            "/errors",
        }
        is_public_route = path in public_paths
        resource.add_method(
            http_method=method,
            integration=integration,
            authorizer=None if is_public_route else self.api_authorizer,
            authorization_type=(
                aws_apigateway.AuthorizationType.NONE
                if is_public_route
                else aws_apigateway.AuthorizationType.COGNITO
            ),
        )

    @staticmethod
    def _build_lambda_proxy_integration(
        handler: _lambda.IFunction,
    ) -> aws_apigateway.AwsIntegration:
        return aws_apigateway.AwsIntegration(
            service="lambda",
            proxy=True,
            integration_http_method="POST",
            path=f"2015-03-31/functions/{handler.function_arn}/invocations",
        )

    def _add_openapi_contract_routes(self) -> None:
        # Phase 1: collapse only features whose live-stack sub-resources are all
        # literal path segments (no variable {paramId} siblings that would conflict
        # with {proxy+} during a CloudFormation UPDATE).
        #
        # Features with variable-path siblings in the deployed stack
        # (vpr/{vprId}, cover-letter/{coverLetterId}, cv-tailoring/{cvTailoringId},
        #  interview-prep/{interviewPrepId}, applications/{application_id},
        #  company-research/{jobId}, jobs/{jobId}) require a two-phase deploy:
        # Phase 2 (separate deploy): first let CloudFormation delete those resources,
        # then add {proxy+}. See FE-UI-048 for the full phased plan.
        #
        # /jobs is permanently excluded: multiple Lambdas own sub-paths under it
        # (job_api_func, gap_api_func, export_lambda), so {jobId} explicit routes
        # must coexist with greedy routing — {proxy+} and {jobId} cannot be siblings.
        feature_proxies: list[tuple[str, _lambda.Function, bool]] = [
            ("/auth", self.auth_api_func, False),
            ("/users", self.user_api_func, True),
            ("/gap-analysis", self.gap_api_func, True),
            ("/billing", self.billing_lambda, True),
        ]
        for path, handler, authorized in feature_proxies:
            self._register_feature_proxy(path, handler, authorized=authorized)

        # Explicit routes: cross-Lambda exceptions under collapsed prefixes, and
        # features deferred to Phase 2 (still using per-path methods until their
        # {paramId} siblings are removed from the live stack).
        route_map: list[tuple[str, str, _lambda.Function]] = [
            ("/health", "GET", self.health_api_func),
            # users — cross-Lambda exceptions below the /users proxy
            ("/users/me", "GET", self.user_api_func),
            ("/users/me", "PUT", self.user_api_func),
            ("/users/me/usage", "GET", self.user_api_func),
            ("/users/me/trial/reset", "POST", self.user_api_func),
            ("/users/me/cv", "POST", self.cv_upload_func),
            ("/users/me/cv", "GET", self.user_api_func),
            ("/users/me/subscription", "GET", self.billing_lambda),
            # jobs — permanent explicit (multi-Lambda prefix)
            ("/jobs", "POST", self.job_api_func),
            ("/jobs", "GET", self.job_api_func),
            ("/jobs/{jobId}", "GET", self.job_api_func),
            ("/jobs/{jobId}/gap-questions", "POST", self.gap_api_func),
            ("/jobs/{jobId}/gap-questions", "GET", self.gap_api_func),
            ("/jobs/{jobId}/gap-responses", "POST", self.gap_api_func),
            # applications — Phase 2 pending
            ("/applications/{application_id}", "GET", self.application_api_func),
            # vpr — Phase 2 pending
            ("/vpr/generate", "POST", self.vpr_submit_func),
            ("/vpr/{vprId}/status", "GET", self.vpr_status_func),
            ("/vpr/{vprId}/cancel", "POST", self.vpr_status_func),
            ("/vprs", "GET", self.vpr_status_func),
            # cv-tailoring — Phase 2 pending
            ("/cv-tailoring/generate", "POST", self.cv_tailoring_func),
            ("/cv-tailoring/{cvTailoringId}/status", "GET", self.cv_tailoring_func),
            ("/cv-tailoring/{cvTailoringId}/cancel", "POST", self.cv_tailoring_func),
            ("/cv-tailoring/{cvTailoringId}", "DELETE", self.cv_tailoring_func),
            ("/cv-tailoring/{cvTailoringId}", "PATCH", self.cv_tailoring_func),
            ("/cv-tailorings", "GET", self.cv_tailoring_func),
            # cover-letter — Phase 2 pending
            ("/cover-letter/generate", "POST", self.cover_letter_api_func),
            (
                "/cover-letter/{coverLetterId}/status",
                "GET",
                self.cover_letter_status_func,
            ),
            (
                "/cover-letter/{coverLetterId}/cancel",
                "POST",
                self.cover_letter_status_func,
            ),
            ("/cover-letter/{coverLetterId}", "PATCH", self.cover_letter_status_func),
            ("/cover-letters", "GET", self.cover_letter_status_func),
            # interview-prep — Phase 2 pending (PATCH registered in register_ai_assist_routes)
            ("/interview-prep/generate", "POST", self.interview_prep_api_func),
            (
                "/interview-prep/{interviewPrepId}/status",
                "GET",
                self.interview_prep_status_func,
            ),
            (
                "/interview-prep/{interviewPrepId}/cancel",
                "POST",
                self.interview_prep_status_func,
            ),
            ("/interview-preps", "GET", self.interview_prep_status_func),
            # company-research — Phase 2 pending
            ("/company-research/{jobId}", "GET", self.company_research_func),
            ("/company-research/{jobId}/cancel", "POST", self.company_research_func),
            ("/company-research/fetch", "POST", self.company_research_func),
            ("/knowledge-base", "GET", self.company_research_func),
            # Billing webhook (public exception under /billing proxy)
            ("/billing/webhook", "POST", self.billing_lambda),
            # Export route (FE-UI-028)
            (
                "/jobs/{jobId}/artifacts/{moduleType}/export",
                "GET",
                self.export_lambda,
            ),
        ]
        for path, method, handler in route_map:
            self._add_route_method(path, method, handler)
