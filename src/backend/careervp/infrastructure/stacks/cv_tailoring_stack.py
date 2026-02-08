"""CDK stack for CV Tailoring infrastructure (test-only)."""

from __future__ import annotations

from typing import Any

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_authorizers as apigw_auth
from aws_cdk import aws_apigatewayv2_integrations as apigw_integrations
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sqs as sqs
from constructs import Construct


class CVTailoringStack(Stack):
    """Stack defining CV tailoring infrastructure."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)

        table = dynamodb.Table(
            self,
            'CVTailoringTable',
            partition_key=dynamodb.Attribute(name='user_id', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='artifact_id', type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute='ttl',
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        table.add_global_secondary_index(
            index_name='UserIdIndex',
            partition_key=dynamodb.Attribute(name='user_id', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='created_at', type=dynamodb.AttributeType.STRING),
        )

        bucket = s3.Bucket(
            self,
            'CVTailoringBucket',
            encryption=s3.BucketEncryption.S3_MANAGED,
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(90))],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        dlq = sqs.Queue(self, 'CVTailoringDLQ')

        lambda_fn = lambda_.Function(
            self,
            'CVTailoringLambda',
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler='careervp.handlers.cv_tailoring_handler.handler',
            code=lambda_.Code.from_inline('def handler(event, context):\n    return {}'),
            memory_size=512,
            timeout=Duration.seconds(60),
            reserved_concurrent_executions=5,
            tracing=lambda_.Tracing.ACTIVE,
            dead_letter_queue=dlq,
            environment={
                'TABLE_NAME': table.table_name,
                'BEDROCK_MODEL_ID': 'claude-haiku-4-5-20251001',
                'FVS_ENABLED': 'true',
            },
            layers=[
                lambda_.LayerVersion.from_layer_version_arn(
                    self,
                    'BaseLayer',
                    layer_version_arn='arn:aws:lambda:us-east-1:123456789012:layer:dummy:1',
                )
            ],
        )

        table.grant_read_write_data(lambda_fn)
        bucket.grant_read_write(lambda_fn)
        lambda_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=['bedrock:InvokeModel'],
                resources=['*'],
            )
        )

        log_group = logs.LogGroup(
            self,
            'CVTailoringLambdaLogGroup',
            retention=logs.RetentionDays.ONE_WEEK,
            log_group_name=f'/aws/lambda/{lambda_fn.function_name}',
            removal_policy=RemovalPolicy.DESTROY,
        )
        _ = log_group

        api = apigwv2.HttpApi(
            self,
            'CVTailoringApi',
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=['*'],
                allow_methods=[apigwv2.CorsHttpMethod.POST, apigwv2.CorsHttpMethod.OPTIONS],
                allow_headers=['Content-Type', 'Authorization'],
            ),
        )

        authorizer = apigw_auth.HttpJwtAuthorizer(
            'CVTailoringAuthorizer',
            jwt_issuer='https://example.com',
            jwt_audience=['careervp'],
        )

        api.add_routes(
            path='/api/cv-tailoring',
            methods=[apigwv2.HttpMethod.POST],
            integration=apigw_integrations.HttpLambdaIntegration('CVTailoringIntegration', lambda_fn),
            authorizer=authorizer,
        )

        access_log_group = logs.LogGroup(
            self,
            'CVTailoringApiAccessLogs',
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        apigwv2.CfnStage(
            self,
            'CVTailoringStage',
            api_id=api.api_id,
            stage_name='$default',
            auto_deploy=True,
            default_route_settings=apigwv2.CfnStage.RouteSettingsProperty(
                throttling_burst_limit=100,
                throttling_rate_limit=50,
            ),
            access_log_settings=apigwv2.CfnStage.AccessLogSettingsProperty(
                destination_arn=access_log_group.log_group_arn,
                format='{"requestId":"$context.requestId"}',
            ),
        )

        CfnOutput(self, 'CVTailoringApiEndpoint', value=api.api_endpoint)
        CfnOutput(self, 'CVTailoringTableName', value=table.table_name)
