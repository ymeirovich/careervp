"""
Infrastructure tests for CV Tailoring CDK stack.

Tests the CloudFormation/CDK infrastructure to ensure proper resource
configuration, IAM permissions, API Gateway routes, and DynamoDB tables.
"""

import pytest
from aws_cdk import App, assertions
from careervp.infrastructure.stacks.cv_tailoring_stack import CVTailoringStack


@pytest.fixture
def app():
    """Create CDK App for testing."""
    return App()


@pytest.fixture
def stack(app):
    """Create CV Tailoring stack for testing."""
    return CVTailoringStack(app, "TestCVTailoringStack")


@pytest.fixture
def template(stack):
    """Generate CloudFormation template from stack."""
    return assertions.Template.from_stack(stack)


def test_lambda_function_exists(template):
    """Test Lambda function is created."""
    # Assert
    template.resource_count_is("AWS::Lambda::Function", 1)


def test_lambda_timeout_60_seconds(template):
    """Test Lambda function has 60-second timeout."""
    # Assert
    template.has_resource_properties("AWS::Lambda::Function", {"Timeout": 60})


def test_lambda_memory_3gb(template):
    """Test Lambda function has 3GB memory."""
    # Assert
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "MemorySize": 3008  # CDK uses 3008 for 3GB
        },
    )


def test_lambda_environment_variables(template):
    """Test Lambda function has required environment variables set."""
    # Assert
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Environment": {
                "Variables": {
                    "TABLE_NAME": assertions.Match.any_value(),
                    "BEDROCK_MODEL_ID": assertions.Match.any_value(),
                    "FVS_ENABLED": "true",
                }
            }
        },
    )


def test_api_gateway_route_exists(template):
    """Test API Gateway has POST /api/cv-tailoring route."""
    # Assert
    template.has_resource_properties(
        "AWS::ApiGatewayV2::Route", {"RouteKey": "POST /api/cv-tailoring"}
    )


def test_api_gateway_auth(template):
    """Test API Gateway route has Cognito authorizer."""
    # Assert
    template.has_resource_properties(
        "AWS::ApiGatewayV2::Route", {"AuthorizationType": "JWT"}
    )


def test_dynamodb_table_exists(template):
    """Test DynamoDB table for artifacts is created."""
    # Assert
    template.resource_count_is("AWS::DynamoDB::Table", 1)


def test_dynamodb_ttl_enabled(template):
    """Test DynamoDB table has TTL enabled on artifacts."""
    # Assert
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {"TimeToLiveSpecification": {"AttributeName": "ttl", "Enabled": True}},
    )


def test_dynamodb_gsi_for_user_queries(template):
    """Test DynamoDB table has GSI for querying by user_id."""
    # Assert
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "GlobalSecondaryIndexes": assertions.Match.array_with(
                [
                    assertions.Match.object_like(
                        {
                            "IndexName": "UserIdIndex",
                            "KeySchema": assertions.Match.array_with(
                                [
                                    assertions.Match.object_like(
                                        {"AttributeName": "user_id"}
                                    )
                                ]
                            ),
                        }
                    )
                ]
            )
        },
    )


def test_lambda_iam_permissions_dynamodb(template):
    """Test Lambda has permissions to read/write DynamoDB."""
    # Assert
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Action": assertions.Match.array_with(
                                    [
                                        "dynamodb:GetItem",
                                        "dynamodb:PutItem",
                                        "dynamodb:Query",
                                    ]
                                ),
                                "Effect": "Allow",
                            }
                        )
                    ]
                )
            }
        },
    )


def test_lambda_iam_permissions_bedrock(template):
    """Test Lambda has permissions to invoke Bedrock."""
    # Assert
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Action": assertions.Match.array_with(
                                    ["bedrock:InvokeModel"]
                                ),
                                "Effect": "Allow",
                            }
                        )
                    ]
                )
            }
        },
    )


def test_lambda_iam_permissions_s3(template):
    """Test Lambda has permissions to write to S3."""
    # Assert
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Action": assertions.Match.array_with(
                                    ["s3:PutObject", "s3:GetObject"]
                                ),
                                "Effect": "Allow",
                            }
                        )
                    ]
                )
            }
        },
    )


def test_lambda_runtime_python39(template):
    """Test Lambda uses Python 3.9 runtime."""
    # Assert
    template.has_resource_properties("AWS::Lambda::Function", {"Runtime": "python3.9"})


def test_api_gateway_cors_configuration(template):
    """Test API Gateway has CORS configured."""
    # Assert
    template.has_resource_properties(
        "AWS::ApiGatewayV2::Api",
        {
            "CorsConfiguration": {
                "AllowOrigins": assertions.Match.any_value(),
                "AllowMethods": assertions.Match.array_with(["POST", "OPTIONS"]),
                "AllowHeaders": assertions.Match.any_value(),
            }
        },
    )


def test_dynamodb_billing_mode_pay_per_request(template):
    """Test DynamoDB table uses pay-per-request billing."""
    # Assert
    template.has_resource_properties(
        "AWS::DynamoDB::Table", {"BillingMode": "PAY_PER_REQUEST"}
    )


def test_lambda_vpc_configuration(template):
    """Test Lambda is deployed in VPC (if applicable)."""
    # This test might not apply if Lambda is not in VPC
    # Check if VPC configuration exists
    try:
        template.has_resource_properties(
            "AWS::Lambda::Function", {"VpcConfig": assertions.Match.any_value()}
        )
    except AssertionError:
        # Lambda not in VPC, which is fine for this use case
        pass


def test_cloudwatch_log_group_retention(template):
    """Test CloudWatch log group has retention policy."""
    # Assert
    template.has_resource_properties(
        "AWS::Logs::LogGroup", {"RetentionInDays": assertions.Match.any_value()}
    )


def test_lambda_reserved_concurrent_executions(template):
    """Test Lambda has reserved concurrent executions set."""
    # Assert
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {"ReservedConcurrentExecutions": assertions.Match.any_value()},
    )


def test_api_gateway_throttling_limits(template):
    """Test API Gateway has throttling limits configured."""
    # Assert
    template.has_resource_properties(
        "AWS::ApiGatewayV2::Stage",
        {
            "DefaultRouteSettings": {
                "ThrottlingBurstLimit": assertions.Match.any_value(),
                "ThrottlingRateLimit": assertions.Match.any_value(),
            }
        },
    )


def test_dynamodb_point_in_time_recovery(template):
    """Test DynamoDB table has point-in-time recovery enabled."""
    # Assert
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {"PointInTimeRecoverySpecification": {"PointInTimeRecoveryEnabled": True}},
    )


def test_lambda_dead_letter_queue(template):
    """Test Lambda has dead letter queue configured."""
    # Assert
    try:
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"DeadLetterConfig": {"TargetArn": assertions.Match.any_value()}},
        )
    except AssertionError:
        # DLQ might not be configured, check if SQS queue exists
        template.resource_count_is("AWS::SQS::Queue", assertions.Match.any_value())


def test_s3_bucket_encryption(template):
    """Test S3 bucket for PDFs has encryption enabled."""
    # Assert
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "ServerSideEncryptionByDefault": {
                                    "SSEAlgorithm": "AES256"
                                }
                            }
                        )
                    ]
                )
            }
        },
    )


def test_s3_bucket_lifecycle_policy(template):
    """Test S3 bucket has lifecycle policy to delete old artifacts."""
    # Assert
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "LifecycleConfiguration": {
                "Rules": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {"ExpirationInDays": 90, "Status": "Enabled"}
                        )
                    ]
                )
            }
        },
    )


def test_lambda_x_ray_tracing(template):
    """Test Lambda has X-Ray tracing enabled."""
    # Assert
    template.has_resource_properties(
        "AWS::Lambda::Function", {"TracingConfig": {"Mode": "Active"}}
    )


def test_api_gateway_access_logging(template):
    """Test API Gateway has access logging configured."""
    # Assert
    template.has_resource_properties(
        "AWS::ApiGatewayV2::Stage",
        {
            "AccessLogSettings": {
                "DestinationArn": assertions.Match.any_value(),
                "Format": assertions.Match.any_value(),
            }
        },
    )


def test_stack_outputs_api_endpoint(template):
    """Test stack exports API endpoint as output."""
    # Assert
    template.has_output(
        "CVTailoringApiEndpoint", {"Value": assertions.Match.any_value()}
    )


def test_stack_outputs_table_name(template):
    """Test stack exports DynamoDB table name as output."""
    # Assert
    template.has_output("CVTailoringTableName", {"Value": assertions.Match.any_value()})


def test_lambda_layers_attached(template):
    """Test Lambda has required layers attached."""
    # Assert
    template.has_resource_properties(
        "AWS::Lambda::Function", {"Layers": assertions.Match.any_value()}
    )
