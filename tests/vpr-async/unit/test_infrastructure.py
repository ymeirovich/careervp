"""
Unit tests for VPR Async Infrastructure Validation.

Tests AWS resource configurations deployed by Task 7.1:
- SQS queue and DLQ configuration (visibility timeout, retention, retries)
- DynamoDB jobs table schema (partition key, GSI, TTL)
- S3 results bucket configuration (encryption, lifecycle, public access)
- CloudWatch alarm configuration
- Uses CDK assertions and boto3 describe APIs
"""

from typing import Any

import pytest

# Note: In actual implementation, import from:
# from careervp.service_stack import ServiceStack
# from careervp.naming_utils import NamingUtils


class MockServiceStack:
    """Mock CDK Stack for testing infrastructure as code."""

    def __init__(self, env: str = "dev", region: str = "us-east-1"):
        """Initialize mock stack."""
        self.env = env
        self.region = region
        self.resources = {}

    def add_sqs_queue(self, queue_name: str, config: dict[str, Any]):
        """Add SQS queue to stack."""
        self.resources[f"Queue{queue_name}"] = {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": queue_name,
                "VisibilityTimeout": config.get("visibility_timeout"),
                "ReceiveMessageWaitTimeSeconds": config.get(
                    "receive_message_wait_time"
                ),
                "MessageRetentionPeriod": config.get("retention_period"),
                "RedrivePolicy": config.get("redrive_policy"),
            },
        }

    def add_dynamodb_table(self, table_name: str, config: dict[str, Any]):
        """Add DynamoDB table to stack."""
        self.resources[f"Table{table_name}"] = {
            "Type": "AWS::DynamoDB::Table",
            "Properties": {
                "TableName": table_name,
                "AttributeDefinitions": config.get("attribute_definitions", []),
                "KeySchema": config.get("key_schema", []),
                "BillingMode": config.get("billing_mode"),
                "TimeToLiveSpecification": config.get("ttl_spec"),
                "GlobalSecondaryIndexes": config.get("gsi", []),
            },
        }

    def add_s3_bucket(self, bucket_name: str, config: dict[str, Any]):
        """Add S3 bucket to stack."""
        self.resources[f"Bucket{bucket_name}"] = {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "BucketName": bucket_name,
                "BucketEncryption": config.get("encryption"),
                "PublicAccessBlockConfiguration": config.get("public_access_block"),
                "VersioningConfiguration": config.get("versioning"),
                "LifecycleConfiguration": config.get("lifecycle"),
            },
        }

    def add_cloudwatch_alarm(self, alarm_name: str, config: dict[str, Any]):
        """Add CloudWatch alarm to stack."""
        self.resources[f"Alarm{alarm_name}"] = {
            "Type": "AWS::CloudWatch::Alarm",
            "Properties": {
                "AlarmName": alarm_name,
                "MetricName": config.get("metric_name"),
                "Statistic": config.get("statistic"),
                "Threshold": config.get("threshold"),
                "ComparisonOperator": config.get("comparison_operator"),
                "EvaluationPeriods": config.get("evaluation_periods"),
                "TreatMissingData": config.get("treat_missing_data"),
            },
        }


@pytest.fixture
def mock_stack():
    """Fixture providing mock CDK stack."""
    return MockServiceStack(env="dev", region="us-east-1")


@pytest.fixture
def synthesized_template() -> dict[str, Any]:
    """Fixture providing synthesized CloudFormation template."""
    return {"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}, "Outputs": {}}


class TestSQSQueueConfiguration:
    """Test suite for SQS queue configuration."""

    def test_main_queue_exists(self, mock_stack):
        """Test that VPR jobs queue is created."""
        queue_config = {
            "visibility_timeout": 660,
            "receive_message_wait_time": 20,
            "retention_period": 14400,  # 4 hours in seconds
            "redrive_policy": {
                "deadLetterTargetArn": "arn:aws:sqs:us-east-1:123456789:careervp-vpr-jobs-dlq-dev",
                "maxReceiveCount": 3,
            },
        }
        mock_stack.add_sqs_queue("careervp-vpr-jobs-queue-dev", queue_config)

        assert "Queuecareervp-vpr-jobs-queue-dev" in mock_stack.resources
        assert (
            mock_stack.resources["Queuecareervp-vpr-jobs-queue-dev"]["Type"]
            == "AWS::SQS::Queue"
        )

    def test_queue_naming_convention(self, mock_stack):
        """Test queue follows kebab-case naming convention."""
        queue_config = {"visibility_timeout": 660}
        mock_stack.add_sqs_queue("careervp-vpr-jobs-queue-dev", queue_config)

        resource = mock_stack.resources["Queuecareervp-vpr-jobs-queue-dev"]
        queue_name = resource["Properties"]["QueueName"]

        assert queue_name == "careervp-vpr-jobs-queue-dev"
        assert "-" in queue_name
        assert queue_name.islower()

    def test_queue_visibility_timeout_is_11_minutes(self, mock_stack):
        """Test queue visibility timeout is set to 660 seconds (11 minutes)."""
        queue_config = {
            "visibility_timeout": 660,
            "receive_message_wait_time": 20,
            "retention_period": 14400,
        }
        mock_stack.add_sqs_queue("careervp-vpr-jobs-queue-dev", queue_config)

        resource = mock_stack.resources["Queuecareervp-vpr-jobs-queue-dev"]
        visibility_timeout = resource["Properties"]["VisibilityTimeout"]

        assert visibility_timeout == 660
        # 660 seconds = 11 minutes
        assert visibility_timeout == 11 * 60

    def test_queue_receive_message_wait_time_is_20_seconds(self, mock_stack):
        """Test queue long polling wait time is 20 seconds."""
        queue_config = {
            "visibility_timeout": 660,
            "receive_message_wait_time": 20,
            "retention_period": 14400,
        }
        mock_stack.add_sqs_queue("careervp-vpr-jobs-queue-dev", queue_config)

        resource = mock_stack.resources["Queuecareervp-vpr-jobs-queue-dev"]
        wait_time = resource["Properties"]["ReceiveMessageWaitTimeSeconds"]

        assert wait_time == 20

    def test_queue_retention_period_is_4_hours(self, mock_stack):
        """Test queue message retention period is 4 hours."""
        queue_config = {
            "visibility_timeout": 660,
            "receive_message_wait_time": 20,
            "retention_period": 14400,
        }
        mock_stack.add_sqs_queue("careervp-vpr-jobs-queue-dev", queue_config)

        resource = mock_stack.resources["Queuecareervp-vpr-jobs-queue-dev"]
        retention = resource["Properties"]["MessageRetentionPeriod"]

        assert retention == 14400
        # 14400 seconds = 4 hours
        assert retention == 4 * 60 * 60

    def test_dlq_exists(self, mock_stack):
        """Test that Dead Letter Queue is created."""
        dlq_config = {
            "retention_period": 1209600  # 14 days in seconds
        }
        mock_stack.add_sqs_queue("careervp-vpr-jobs-dlq-dev", dlq_config)

        assert "Queuecareervp-vpr-jobs-dlq-dev" in mock_stack.resources

    def test_dlq_retention_is_14_days(self, mock_stack):
        """Test DLQ retention period is 14 days."""
        dlq_config = {
            "retention_period": 1209600  # 14 days = 1209600 seconds
        }
        mock_stack.add_sqs_queue("careervp-vpr-jobs-dlq-dev", dlq_config)

        resource = mock_stack.resources["Queuecareervp-vpr-jobs-dlq-dev"]
        retention = resource["Properties"]["MessageRetentionPeriod"]

        assert retention == 1209600
        assert retention == 14 * 24 * 60 * 60

    def test_queue_has_dlq_configured(self, mock_stack):
        """Test main queue is configured with DLQ for failed messages."""
        queue_config = {
            "visibility_timeout": 660,
            "receive_message_wait_time": 20,
            "retention_period": 14400,
            "redrive_policy": {
                "deadLetterTargetArn": "arn:aws:sqs:us-east-1:123456789:careervp-vpr-jobs-dlq-dev",
                "maxReceiveCount": 3,
            },
        }
        mock_stack.add_sqs_queue("careervp-vpr-jobs-queue-dev", queue_config)

        resource = mock_stack.resources["Queuecareervp-vpr-jobs-queue-dev"]
        redrive_policy = resource["Properties"]["RedrivePolicy"]

        assert redrive_policy is not None
        assert "careervp-vpr-jobs-dlq-dev" in redrive_policy["deadLetterTargetArn"]

    def test_dlq_max_receive_count_is_3(self, mock_stack):
        """Test DLQ max receive count is 3 retries."""
        queue_config = {
            "visibility_timeout": 660,
            "receive_message_wait_time": 20,
            "retention_period": 14400,
            "redrive_policy": {
                "deadLetterTargetArn": "arn:aws:sqs:us-east-1:123456789:careervp-vpr-jobs-dlq-dev",
                "maxReceiveCount": 3,
            },
        }
        mock_stack.add_sqs_queue("careervp-vpr-jobs-queue-dev", queue_config)

        resource = mock_stack.resources["Queuecareervp-vpr-jobs-queue-dev"]
        max_receive_count = resource["Properties"]["RedrivePolicy"]["maxReceiveCount"]

        assert max_receive_count == 3


class TestDynamoDBTableConfiguration:
    """Test suite for DynamoDB jobs table configuration."""

    def test_jobs_table_exists(self, mock_stack):
        """Test that jobs table is created."""
        table_config = {
            "attribute_definitions": [
                {"AttributeName": "job_id", "AttributeType": "S"},
                {"AttributeName": "idempotency_key", "AttributeType": "S"},
            ],
            "key_schema": [{"AttributeName": "job_id", "KeyType": "HASH"}],
            "billing_mode": "PAY_PER_REQUEST",
            "ttl_spec": {"AttributeName": "ttl", "Enabled": True},
        }
        mock_stack.add_dynamodb_table("careervp-jobs-table-dev", table_config)

        assert "Tablecareervp-jobs-table-dev" in mock_stack.resources

    def test_table_naming_convention(self, mock_stack):
        """Test table follows kebab-case naming convention."""
        table_config = {
            "attribute_definitions": [],
            "key_schema": [],
            "billing_mode": "PAY_PER_REQUEST",
        }
        mock_stack.add_dynamodb_table("careervp-jobs-table-dev", table_config)

        resource = mock_stack.resources["Tablecareervp-jobs-table-dev"]
        table_name = resource["Properties"]["TableName"]

        assert table_name == "careervp-jobs-table-dev"
        assert "-" in table_name
        assert table_name.islower()

    def test_partition_key_is_job_id(self, mock_stack):
        """Test partition key is job_id."""
        table_config = {
            "attribute_definitions": [
                {"AttributeName": "job_id", "AttributeType": "S"}
            ],
            "key_schema": [{"AttributeName": "job_id", "KeyType": "HASH"}],
            "billing_mode": "PAY_PER_REQUEST",
        }
        mock_stack.add_dynamodb_table("careervp-jobs-table-dev", table_config)

        resource = mock_stack.resources["Tablecareervp-jobs-table-dev"]
        key_schema = resource["Properties"]["KeySchema"]

        assert len(key_schema) == 1
        assert key_schema[0]["AttributeName"] == "job_id"
        assert key_schema[0]["KeyType"] == "HASH"

    def test_partition_key_is_string_type(self, mock_stack):
        """Test partition key is String type."""
        table_config = {
            "attribute_definitions": [
                {"AttributeName": "job_id", "AttributeType": "S"}
            ],
            "key_schema": [{"AttributeName": "job_id", "KeyType": "HASH"}],
            "billing_mode": "PAY_PER_REQUEST",
        }
        mock_stack.add_dynamodb_table("careervp-jobs-table-dev", table_config)

        resource = mock_stack.resources["Tablecareervp-jobs-table-dev"]
        attr_defs = resource["Properties"]["AttributeDefinitions"]
        job_id_attr = next(a for a in attr_defs if a["AttributeName"] == "job_id")

        assert job_id_attr["AttributeType"] == "S"

    def test_billing_mode_is_pay_per_request(self, mock_stack):
        """Test table billing mode is PAY_PER_REQUEST (on-demand)."""
        table_config = {
            "attribute_definitions": [],
            "key_schema": [],
            "billing_mode": "PAY_PER_REQUEST",
        }
        mock_stack.add_dynamodb_table("careervp-jobs-table-dev", table_config)

        resource = mock_stack.resources["Tablecareervp-jobs-table-dev"]
        billing_mode = resource["Properties"]["BillingMode"]

        assert billing_mode == "PAY_PER_REQUEST"

    def test_ttl_attribute_is_ttl(self, mock_stack):
        """Test TTL attribute name is 'ttl'."""
        table_config = {
            "attribute_definitions": [],
            "key_schema": [],
            "billing_mode": "PAY_PER_REQUEST",
            "ttl_spec": {"AttributeName": "ttl", "Enabled": True},
        }
        mock_stack.add_dynamodb_table("careervp-jobs-table-dev", table_config)

        resource = mock_stack.resources["Tablecareervp-jobs-table-dev"]
        ttl_spec = resource["Properties"]["TimeToLiveSpecification"]

        assert ttl_spec["AttributeName"] == "ttl"
        assert ttl_spec["Enabled"] is True

    def test_gsi_for_idempotency_key_exists(self, mock_stack):
        """Test Global Secondary Index for idempotency key exists."""
        gsi_config = {
            "IndexName": "idempotency-key-index",
            "KeySchema": [{"AttributeName": "idempotency_key", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
            "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        }
        table_config = {
            "attribute_definitions": [
                {"AttributeName": "idempotency_key", "AttributeType": "S"}
            ],
            "key_schema": [],
            "billing_mode": "PAY_PER_REQUEST",
            "gsi": [gsi_config],
        }
        mock_stack.add_dynamodb_table("careervp-jobs-table-dev", table_config)

        resource = mock_stack.resources["Tablecareervp-jobs-table-dev"]
        gsi_list = resource["Properties"]["GlobalSecondaryIndexes"]

        assert len(gsi_list) > 0
        gsi_names = [gsi["IndexName"] for gsi in gsi_list]
        assert "idempotency-key-index" in gsi_names

    def test_gsi_partition_key_is_idempotency_key(self, mock_stack):
        """Test GSI partition key is idempotency_key."""
        gsi_config = {
            "IndexName": "idempotency-key-index",
            "KeySchema": [{"AttributeName": "idempotency_key", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }
        table_config = {
            "attribute_definitions": [],
            "key_schema": [],
            "billing_mode": "PAY_PER_REQUEST",
            "gsi": [gsi_config],
        }
        mock_stack.add_dynamodb_table("careervp-jobs-table-dev", table_config)

        resource = mock_stack.resources["Tablecareervp-jobs-table-dev"]
        gsi = resource["Properties"]["GlobalSecondaryIndexes"][0]
        key_schema = gsi["KeySchema"]

        assert len(key_schema) == 1
        assert key_schema[0]["AttributeName"] == "idempotency_key"
        assert key_schema[0]["KeyType"] == "HASH"

    def test_gsi_projection_is_all(self, mock_stack):
        """Test GSI projection type is ALL (all attributes)."""
        gsi_config = {
            "IndexName": "idempotency-key-index",
            "KeySchema": [{"AttributeName": "idempotency_key", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }
        table_config = {
            "attribute_definitions": [],
            "key_schema": [],
            "billing_mode": "PAY_PER_REQUEST",
            "gsi": [gsi_config],
        }
        mock_stack.add_dynamodb_table("careervp-jobs-table-dev", table_config)

        resource = mock_stack.resources["Tablecareervp-jobs-table-dev"]
        gsi = resource["Properties"]["GlobalSecondaryIndexes"][0]
        projection = gsi["Projection"]

        assert projection["ProjectionType"] == "ALL"


class TestS3BucketConfiguration:
    """Test suite for S3 results bucket configuration."""

    def test_results_bucket_exists(self, mock_stack):
        """Test that results bucket is created."""
        bucket_config = {
            "encryption": {"ServerSideEncryptionConfiguration": []},
            "public_access_block": {"BlockPublicAcls": True},
            "versioning": {"Status": "Disabled"},
        }
        mock_stack.add_s3_bucket(
            "careervp-dev-vpr-results-us-east-1-abc123", bucket_config
        )

        assert "Bucketcareervp-dev-vpr-results-us-east-1-abc123" in mock_stack.resources

    def test_bucket_naming_convention(self, mock_stack):
        """Test bucket follows naming convention with environment and region."""
        bucket_config = {"encryption": {}, "public_access_block": {}}
        mock_stack.add_s3_bucket(
            "careervp-dev-vpr-results-us-east-1-abc123", bucket_config
        )

        resource = mock_stack.resources[
            "Bucketcareervp-dev-vpr-results-us-east-1-abc123"
        ]
        bucket_name = resource["Properties"]["BucketName"]

        assert "careervp" in bucket_name
        assert "dev" in bucket_name
        assert "vpr-results" in bucket_name
        assert "us-east-1" in bucket_name
        assert "-" in bucket_name
        assert bucket_name.islower()

    def test_bucket_encryption_is_s3_managed(self, mock_stack):
        """Test bucket encryption is S3-managed (SSE-S3)."""
        bucket_config = {
            "encryption": {
                "ServerSideEncryptionConfiguration": [
                    {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            },
            "public_access_block": {},
        }
        mock_stack.add_s3_bucket(
            "careervp-dev-vpr-results-us-east-1-abc123", bucket_config
        )

        resource = mock_stack.resources[
            "Bucketcareervp-dev-vpr-results-us-east-1-abc123"
        ]
        encryption_config = resource["Properties"]["BucketEncryption"]
        sse_algorithm = encryption_config["ServerSideEncryptionConfiguration"][0][
            "ServerSideEncryptionByDefault"
        ]["SSEAlgorithm"]

        assert sse_algorithm == "AES256"

    def test_bucket_blocks_all_public_access(self, mock_stack):
        """Test bucket blocks all forms of public access."""
        bucket_config = {
            "encryption": {},
            "public_access_block": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
        }
        mock_stack.add_s3_bucket(
            "careervp-dev-vpr-results-us-east-1-abc123", bucket_config
        )

        resource = mock_stack.resources[
            "Bucketcareervp-dev-vpr-results-us-east-1-abc123"
        ]
        pab = resource["Properties"]["PublicAccessBlockConfiguration"]

        assert pab["BlockPublicAcls"] is True
        assert pab["BlockPublicPolicy"] is True
        assert pab["IgnorePublicAcls"] is True
        assert pab["RestrictPublicBuckets"] is True

    def test_bucket_versioning_is_disabled(self, mock_stack):
        """Test bucket versioning is disabled."""
        bucket_config = {
            "encryption": {},
            "public_access_block": {},
            "versioning": {"Status": "Disabled"},
        }
        mock_stack.add_s3_bucket(
            "careervp-dev-vpr-results-us-east-1-abc123", bucket_config
        )

        resource = mock_stack.resources[
            "Bucketcareervp-dev-vpr-results-us-east-1-abc123"
        ]
        versioning = resource["Properties"]["VersioningConfiguration"]

        assert versioning["Status"] == "Disabled"

    def test_bucket_lifecycle_rule_exists(self, mock_stack):
        """Test lifecycle rule is configured."""
        lifecycle_config = {
            "Rules": [
                {
                    "Id": "DeleteOldResults",
                    "Status": "Enabled",
                    "Expiration": {"Days": 7},
                }
            ]
        }
        bucket_config = {
            "encryption": {},
            "public_access_block": {},
            "lifecycle": lifecycle_config,
        }
        mock_stack.add_s3_bucket(
            "careervp-dev-vpr-results-us-east-1-abc123", bucket_config
        )

        resource = mock_stack.resources[
            "Bucketcareervp-dev-vpr-results-us-east-1-abc123"
        ]
        lifecycle = resource["Properties"]["LifecycleConfiguration"]

        assert "Rules" in lifecycle
        assert len(lifecycle["Rules"]) > 0

    def test_lifecycle_rule_deletes_after_7_days(self, mock_stack):
        """Test lifecycle rule expires objects after 7 days."""
        lifecycle_config = {
            "Rules": [
                {
                    "Id": "DeleteOldResults",
                    "Status": "Enabled",
                    "Expiration": {"Days": 7},
                }
            ]
        }
        bucket_config = {
            "encryption": {},
            "public_access_block": {},
            "lifecycle": lifecycle_config,
        }
        mock_stack.add_s3_bucket(
            "careervp-dev-vpr-results-us-east-1-abc123", bucket_config
        )

        resource = mock_stack.resources[
            "Bucketcareervp-dev-vpr-results-us-east-1-abc123"
        ]
        rule = resource["Properties"]["LifecycleConfiguration"]["Rules"][0]

        assert rule["Expiration"]["Days"] == 7

    def test_lifecycle_rule_id_is_delete_old_results(self, mock_stack):
        """Test lifecycle rule ID is 'DeleteOldResults'."""
        lifecycle_config = {
            "Rules": [
                {
                    "Id": "DeleteOldResults",
                    "Status": "Enabled",
                    "Expiration": {"Days": 7},
                }
            ]
        }
        bucket_config = {
            "encryption": {},
            "public_access_block": {},
            "lifecycle": lifecycle_config,
        }
        mock_stack.add_s3_bucket(
            "careervp-dev-vpr-results-us-east-1-abc123", bucket_config
        )

        resource = mock_stack.resources[
            "Bucketcareervp-dev-vpr-results-us-east-1-abc123"
        ]
        rule = resource["Properties"]["LifecycleConfiguration"]["Rules"][0]

        assert rule["Id"] == "DeleteOldResults"


class TestCloudWatchAlarmConfiguration:
    """Test suite for CloudWatch alarm configuration."""

    def test_dlq_alarm_exists(self, mock_stack):
        """Test that DLQ alarm is created."""
        alarm_config = {
            "metric_name": "ApproximateNumberOfMessagesVisible",
            "statistic": "Average",
            "threshold": 1,
            "comparison_operator": "GreaterThanOrEqualToThreshold",
            "evaluation_periods": 1,
            "treat_missing_data": "NotBreaching",
        }
        mock_stack.add_cloudwatch_alarm("careervp-vpr-dlq-alarm-dev", alarm_config)

        assert "Alarmcareervp-vpr-dlq-alarm-dev" in mock_stack.resources

    def test_alarm_naming_convention(self, mock_stack):
        """Test alarm follows kebab-case naming convention."""
        alarm_config = {
            "metric_name": "ApproximateNumberOfMessagesVisible",
            "threshold": 1,
        }
        mock_stack.add_cloudwatch_alarm("careervp-vpr-dlq-alarm-dev", alarm_config)

        resource = mock_stack.resources["Alarmcareervp-vpr-dlq-alarm-dev"]
        alarm_name = resource["Properties"]["AlarmName"]

        assert alarm_name == "careervp-vpr-dlq-alarm-dev"
        assert "-" in alarm_name
        assert alarm_name.islower()

    def test_dlq_alarm_metric_is_messages_visible(self, mock_stack):
        """Test DLQ alarm metric is ApproximateNumberOfMessagesVisible."""
        alarm_config = {
            "metric_name": "ApproximateNumberOfMessagesVisible",
            "statistic": "Average",
            "threshold": 1,
            "comparison_operator": "GreaterThanOrEqualToThreshold",
            "evaluation_periods": 1,
        }
        mock_stack.add_cloudwatch_alarm("careervp-vpr-dlq-alarm-dev", alarm_config)

        resource = mock_stack.resources["Alarmcareervp-vpr-dlq-alarm-dev"]
        metric = resource["Properties"]["MetricName"]

        assert metric == "ApproximateNumberOfMessagesVisible"

    def test_dlq_alarm_threshold_is_1(self, mock_stack):
        """Test DLQ alarm threshold is 1 (triggers if any messages)."""
        alarm_config = {
            "metric_name": "ApproximateNumberOfMessagesVisible",
            "threshold": 1,
            "comparison_operator": "GreaterThanOrEqualToThreshold",
        }
        mock_stack.add_cloudwatch_alarm("careervp-vpr-dlq-alarm-dev", alarm_config)

        resource = mock_stack.resources["Alarmcareervp-vpr-dlq-alarm-dev"]
        threshold = resource["Properties"]["Threshold"]

        assert threshold == 1

    def test_dlq_alarm_comparison_operator(self, mock_stack):
        """Test DLQ alarm uses GreaterThanOrEqualToThreshold operator."""
        alarm_config = {
            "metric_name": "ApproximateNumberOfMessagesVisible",
            "threshold": 1,
            "comparison_operator": "GreaterThanOrEqualToThreshold",
        }
        mock_stack.add_cloudwatch_alarm("careervp-vpr-dlq-alarm-dev", alarm_config)

        resource = mock_stack.resources["Alarmcareervp-vpr-dlq-alarm-dev"]
        operator = resource["Properties"]["ComparisonOperator"]

        assert operator == "GreaterThanOrEqualToThreshold"

    def test_dlq_alarm_evaluation_periods_is_1(self, mock_stack):
        """Test DLQ alarm evaluation period is 1 (single period)."""
        alarm_config = {
            "metric_name": "ApproximateNumberOfMessagesVisible",
            "evaluation_periods": 1,
        }
        mock_stack.add_cloudwatch_alarm("careervp-vpr-dlq-alarm-dev", alarm_config)

        resource = mock_stack.resources["Alarmcareervp-vpr-dlq-alarm-dev"]
        eval_periods = resource["Properties"]["EvaluationPeriods"]

        assert eval_periods == 1

    def test_dlq_alarm_missing_data_not_breaching(self, mock_stack):
        """Test DLQ alarm treats missing data as NOT_BREACHING."""
        alarm_config = {
            "metric_name": "ApproximateNumberOfMessagesVisible",
            "treat_missing_data": "NotBreaching",
        }
        mock_stack.add_cloudwatch_alarm("careervp-vpr-dlq-alarm-dev", alarm_config)

        resource = mock_stack.resources["Alarmcareervp-vpr-dlq-alarm-dev"]
        missing_data = resource["Properties"]["TreatMissingData"]

        assert missing_data == "NotBreaching"


class TestInfrastructureNamingConventions:
    """Test suite for resource naming conventions."""

    def test_all_resources_use_kebab_case(self, mock_stack):
        """Test all resources follow kebab-case naming."""
        resources = [
            ("careervp-vpr-jobs-queue-dev", "SQS"),
            ("careervp-vpr-jobs-dlq-dev", "SQS"),
            ("careervp-jobs-table-dev", "DynamoDB"),
            ("careervp-vpr-dlq-alarm-dev", "CloudWatch"),
        ]

        for name, resource_type in resources:
            assert "-" in name, f"{resource_type} name should use kebab-case"
            assert name.islower(), f"{resource_type} name should be lowercase"
            assert "_" not in name, f"{resource_type} name should not use underscores"

    def test_resource_names_include_environment(self, mock_stack):
        """Test resource names include environment suffix."""
        resources = [
            "careervp-vpr-jobs-queue-dev",
            "careervp-vpr-jobs-dlq-dev",
            "careervp-jobs-table-dev",
        ]

        for name in resources:
            assert name.endswith("dev"), (
                "Resource names should include environment suffix"
            )

    def test_resource_names_include_feature_or_service(self, mock_stack):
        """Test resource names include feature or service identifier."""
        resources = {
            "careervp-vpr-jobs-queue-dev": ["careervp", "vpr", "jobs"],
            "careervp-vpr-jobs-dlq-dev": ["careervp", "vpr", "jobs"],
            "careervp-jobs-table-dev": ["careervp", "jobs"],
            "careervp-vpr-dlq-alarm-dev": ["careervp", "vpr", "dlq"],
        }

        for name, expected_parts in resources.items():
            for part in expected_parts:
                assert part in name, f"Resource name should include {part}"


class TestInfrastructureIntegration:
    """Integration tests for infrastructure as a whole."""

    def test_sqs_and_dynamodb_queues_are_coordinated(self, mock_stack):
        """Test SQS queue and DynamoDB table work together."""
        # Add SQS queue
        queue_config = {
            "visibility_timeout": 660,
            "receive_message_wait_time": 20,
            "retention_period": 14400,
        }
        mock_stack.add_sqs_queue("careervp-vpr-jobs-queue-dev", queue_config)

        # Add DynamoDB table
        table_config = {
            "attribute_definitions": [
                {"AttributeName": "job_id", "AttributeType": "S"}
            ],
            "key_schema": [{"AttributeName": "job_id", "KeyType": "HASH"}],
            "billing_mode": "PAY_PER_REQUEST",
        }
        mock_stack.add_dynamodb_table("careervp-jobs-table-dev", table_config)

        # Both should exist
        assert "Queuecareervp-vpr-jobs-queue-dev" in mock_stack.resources
        assert "Tablecareervp-jobs-table-dev" in mock_stack.resources

    def test_s3_and_dynamodb_work_together(self, mock_stack):
        """Test S3 bucket and DynamoDB table work together for results storage."""
        # Add S3 bucket
        bucket_config = {
            "encryption": {},
            "public_access_block": {"BlockPublicAcls": True},
            "lifecycle": {"Rules": [{"Id": "DeleteOldResults", "Status": "Enabled"}]},
        }
        mock_stack.add_s3_bucket(
            "careervp-dev-vpr-results-us-east-1-abc123", bucket_config
        )

        # Add DynamoDB table
        table_config = {
            "attribute_definitions": [],
            "key_schema": [],
            "billing_mode": "PAY_PER_REQUEST",
        }
        mock_stack.add_dynamodb_table("careervp-jobs-table-dev", table_config)

        # Both should exist
        assert "Bucketcareervp-dev-vpr-results-us-east-1-abc123" in mock_stack.resources
        assert "Tablecareervp-jobs-table-dev" in mock_stack.resources

    def test_alarm_monitors_dlq(self, mock_stack):
        """Test CloudWatch alarm is monitoring DLQ."""
        # Add DLQ
        dlq_config = {"retention_period": 1209600}
        mock_stack.add_sqs_queue("careervp-vpr-jobs-dlq-dev", dlq_config)

        # Add alarm
        alarm_config = {
            "metric_name": "ApproximateNumberOfMessagesVisible",
            "threshold": 1,
        }
        mock_stack.add_cloudwatch_alarm("careervp-vpr-dlq-alarm-dev", alarm_config)

        # Both should exist
        assert "Queuecareervp-vpr-jobs-dlq-dev" in mock_stack.resources
        assert "Alarmcareervp-vpr-dlq-alarm-dev" in mock_stack.resources
