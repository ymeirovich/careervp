"""
Infrastructure tests for gap analysis CDK stack.
Tests CDK infrastructure: SQS queues, DLQs, Lambda functions, API Gateway routes.

RED PHASE: These tests will FAIL until infrastructure is implemented.
"""

import aws_cdk as cdk
import aws_cdk.assertions as assertions
import pytest

# This import will fail until the stack is updated
from careervp_infra.api_construct import ApiConstruct


class TestGapAnalysisInfrastructure:
    """Test gap analysis infrastructure components."""

    @pytest.fixture
    def stack(self):
        """Create CDK stack for testing."""
        app = cdk.App()
        stack = cdk.Stack(app, "TestStack")
        # ApiConstruct should include gap analysis infrastructure
        ApiConstruct(stack, "Api", environment="test")
        return stack

    def test_sqs_queue_exists(self, stack):
        """Test that gap analysis SQS queue is created."""
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::SQS::Queue",
            {
                "QueueName": "careervp-gap-analysis-queue-test",
                "VisibilityTimeout": 900,  # 15 minutes
            },
        )

    def test_dlq_exists(self, stack):
        """Test that dead letter queue is created."""
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::SQS::Queue",
            {
                "QueueName": "careervp-gap-analysis-dlq-test",
                "MessageRetentionPeriod": 1209600,  # 14 days
            },
        )

    def test_submit_lambda_exists(self, stack):
        """Test that submit handler Lambda is created."""
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "careervp-gap-submit-test",
                "Runtime": "python3.12",
                "Timeout": 30,
                "Handler": "careervp.handlers.gap_submit_handler.lambda_handler",
            },
        )

    def test_worker_lambda_exists(self, stack):
        """Test that worker handler Lambda is created."""
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "careervp-gap-worker-test",
                "Runtime": "python3.12",
                "Timeout": 900,  # 15 minutes
                "MemorySize": 1024,
                "Handler": "careervp.handlers.gap_analysis_worker.lambda_handler",
            },
        )

    def test_status_lambda_exists(self, stack):
        """Test that status handler Lambda is created."""
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": "careervp-gap-status-test",
                "Runtime": "python3.12",
                "Timeout": 30,
                "Handler": "careervp.handlers.gap_status_handler.lambda_handler",
            },
        )

    def test_dynamodb_gsi_exists(self, stack):
        """Test that DynamoDB GSI for job queries is created."""
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "GlobalSecondaryIndexes": assertions.Match.array_with(
                    [
                        {
                            "IndexName": "gsi1",
                            "KeySchema": [
                                {"AttributeName": "gsi1pk", "KeyType": "HASH"},
                                {"AttributeName": "gsi1sk", "KeyType": "RANGE"},
                            ],
                        }
                    ]
                )
            },
        )

    def test_api_gateway_submit_route(self, stack):
        """Test that POST /api/gap-analysis/submit route is created."""
        template = assertions.Template.from_stack(stack)

        # API Gateway REST API resource for /gap-analysis/submit
        template.resource_count_is(
            "AWS::ApiGateway::Resource", assertions.Match.any_value()
        )
        template.resource_count_is(
            "AWS::ApiGateway::Method", assertions.Match.any_value()
        )

    def test_api_gateway_status_route(self, stack):
        """Test that GET /api/gap-analysis/status/{job_id} route is created."""
        template = assertions.Template.from_stack(stack)

        # Should have API Gateway methods
        template.resource_count_is(
            "AWS::ApiGateway::Method", assertions.Match.any_value()
        )

    def test_sqs_event_source_mapping(self, stack):
        """Test that worker Lambda has SQS event source mapping."""
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::Lambda::EventSourceMapping",
            {
                "BatchSize": 1,
                "MaximumBatchingWindowInSeconds": 0,
            },
        )

    def test_lambda_has_required_permissions(self, stack):
        """Test that Lambdas have required IAM permissions."""
        template = assertions.Template.from_stack(stack)

        # Should have IAM roles with necessary permissions
        template.resource_count_is("AWS::IAM::Role", assertions.Match.any_value())
        template.resource_count_is("AWS::IAM::Policy", assertions.Match.any_value())
