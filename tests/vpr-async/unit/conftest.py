"""
Pytest configuration and shared fixtures for VPR async tests.

Provides:
- Mock AWS clients (DynamoDB, SQS, S3)
- Mock API responses
- Test data builders
- Environment configuration
"""

import os
import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta
from typing import Dict, Any

# Ensure moto doesn't reach real AWS
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_REGION"] = "us-east-1"

# Lambda Powertools configuration for testing
os.environ["POWERTOOLS_SERVICE_NAME"] = "careervp-vpr-async-test"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["POWERTOOLS_TRACE_DISABLED"] = "true"

# Jobs table configuration
os.environ["JOBS_TABLE_NAME"] = "test-jobs-table"
os.environ["VPR_JOBS_QUEUE_URL"] = (
    "https://sqs.us-east-1.amazonaws.com/123456789012/careervp-vpr-jobs-queue-dev"
)
os.environ["VPR_RESULTS_BUCKET_NAME"] = "careervp-dev-vpr-results-us-east-1-abc123"


# ============================================================================
# ENVIRONMENT FIXTURES
# ============================================================================


@pytest.fixture
def test_environment() -> str:
    """Return test environment (dev)."""
    return "dev"


@pytest.fixture
def aws_account_id() -> str:
    """Return test AWS account ID."""
    return "123456789012"


@pytest.fixture
def aws_region() -> str:
    """Return test AWS region."""
    return "us-east-1"


# ============================================================================
# AWS MOCK FIXTURES
# ============================================================================


@pytest.fixture
def mock_dynamodb_client():
    """Create mock DynamoDB client."""
    client = Mock()
    client.put_item = Mock(return_value={})
    client.get_item = Mock(return_value={"Item": {}})
    client.query = Mock(return_value={"Items": []})
    client.update_item = Mock(return_value={})
    return client


@pytest.fixture
def mock_sqs_client():
    """Create mock SQS client."""
    client = Mock()
    client.send_message = Mock(return_value={"MessageId": "test-message-id-123"})
    client.receive_message = Mock(return_value={"Messages": []})
    client.delete_message = Mock(return_value={})
    return client


@pytest.fixture
def mock_s3_client():
    """Create mock S3 client."""
    client = Mock()
    client.put_object = Mock(return_value={"ETag": '"abc123"'})
    client.get_object = Mock(return_value={"Body": Mock(read=Mock(return_value=b"{}"))})
    client.generate_presigned_url = Mock(
        return_value="https://s3.example.com/presigned"
    )
    return client


@pytest.fixture
def mock_lambda_client():
    """Create mock Lambda client."""
    client = Mock()
    client.invoke = Mock(
        return_value={"StatusCode": 202, "Payload": Mock(read=Mock(return_value=b"{}"))}
    )
    return client


@pytest.fixture
def mock_cloudwatch_client():
    """Create mock CloudWatch client."""
    client = Mock()
    client.put_metric_alarm = Mock(return_value={})
    client.describe_alarms = Mock(return_value={"MetricAlarms": []})
    return client


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture
def valid_vpr_request() -> Dict[str, Any]:
    """Return valid VPR request payload."""
    return {
        "user_id": "test-user-123",
        "application_id": "test-app-456",
        "job_posting": {
            "company_name": "Acme Corp",
            "role_title": "Senior Software Engineer",
            "responsibilities": [
                "Design scalable systems",
                "Mentor junior engineers",
                "Code review and architecture",
            ],
            "requirements": [
                "5+ years Python experience",
                "AWS/Cloud expertise",
                "System design knowledge",
            ],
        },
    }


@pytest.fixture
def valid_job_record() -> Dict[str, Any]:
    """Return valid job DynamoDB record."""
    now = datetime.utcnow()
    return {
        "job_id": "job-123",
        "user_id": "user-123",
        "application_id": "app-456",
        "status": "PENDING",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "idempotency_key": "idempotency-123",
        "ttl": int((now + timedelta(days=1)).timestamp()),
        "request": {"company_name": "Test Co", "role_title": "Test Role"},
    }


@pytest.fixture
def completed_job_record(valid_job_record) -> Dict[str, Any]:
    """Return completed job record."""
    job = valid_job_record.copy()
    job["status"] = "COMPLETED"
    job["result_url"] = "https://s3.example.com/vpr-results/job-123.json"
    job["completed_at"] = datetime.utcnow().isoformat()
    job["token_usage"] = {"input_tokens": 1500, "output_tokens": 800}
    return job


@pytest.fixture
def failed_job_record(valid_job_record) -> Dict[str, Any]:
    """Return failed job record."""
    job = valid_job_record.copy()
    job["status"] = "FAILED"
    job["error"] = "Claude API rate limit exceeded"
    job["failed_at"] = datetime.utcnow().isoformat()
    return job


@pytest.fixture
def vpr_result() -> Dict[str, Any]:
    """Return sample VPR result."""
    return {
        "job_id": "job-123",
        "user_id": "user-123",
        "executive_summary": "Strong match for role based on experience.",
        "evidence_matrix": [
            {
                "category": "Python Experience",
                "requirement": "5+ years Python",
                "evidence": ["8 years at FAANG", "Led Python migration"],
                "match_score": 0.95,
            },
            {
                "category": "AWS Experience",
                "requirement": "AWS expertise",
                "evidence": ["AWS Architect certification", "3 years AWS"],
                "match_score": 0.87,
            },
        ],
        "gap_analysis": [
            {
                "gap": "Kubernetes experience",
                "importance": "Medium",
                "suggestion": "Start Kubernetes course",
            }
        ],
        "token_usage": {"input_tokens": 1500, "output_tokens": 800},
    }


# ============================================================================
# DEPLOYMENT CONFIG FIXTURES
# ============================================================================


@pytest.fixture
def valid_dev_deployment_config() -> Dict[str, Any]:
    """Return valid development deployment configuration."""
    return {
        "environment": "dev",
        "resources": {
            "queue": "careervp-vpr-jobs-queue-dev",
            "dlq": "careervp-vpr-jobs-dlq-dev",
            "lambda_submit": "careervp-vpr-submit-lambda-dev",
            "lambda_worker": "careervp-vpr-worker-lambda-dev",
            "lambda_status": "careervp-vpr-status-lambda-dev",
            "table": "careervp-vpr-jobs-dev",
            "bucket": "careervp-vpr-results-dev",
        },
        "lambdas": {
            "submit": {
                "timeout": 30,
                "memory": 256,
                "ephemeral_storage": 512,
                "reserved_concurrency": 0,
                "environment": {
                    "JOBS_TABLE_NAME": "careervp-vpr-jobs-dev",
                    "VPR_JOBS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/queue",
                    "IDEMPOTENCY_KEY_EXPIRY_HOURS": "24",
                },
            },
            "worker": {
                "timeout": 900,
                "memory": 3008,
                "ephemeral_storage": 10240,
                "reserved_concurrency": 2,
                "environment": {
                    "JOBS_TABLE_NAME": "careervp-vpr-jobs-dev",
                    "VPR_RESULTS_BUCKET": "careervp-vpr-results-dev",
                    "CLAUDE_API_KEY": "sk-ant-test-key-dev",
                    "ENABLE_CLAUDE_CACHING": "true",
                },
            },
            "status": {
                "timeout": 30,
                "memory": 256,
                "ephemeral_storage": 512,
                "reserved_concurrency": 0,
                "environment": {
                    "JOBS_TABLE_NAME": "careervp-vpr-jobs-dev",
                    "VPR_RESULTS_BUCKET": "careervp-vpr-results-dev",
                    "PRESIGNED_URL_EXPIRY_SECONDS": "3600",
                },
            },
        },
        "dynamodb": {
            "name": "careervp-vpr-jobs-dev",
            "partition_key": "job_id",
            "global_secondary_indexes": [{"name": "idempotency-key-index"}],
            "ttl_attribute": "ttl",
            "billing_mode": "PAY_PER_REQUEST",
        },
        "s3": {
            "name": "careervp-vpr-results-dev",
            "block_public_access": True,
            "versioning": True,
            "encryption": True,
            "lifecycle_rules": [{"expiration_days": 7}],
        },
        "sqs": {
            "name": "careervp-vpr-jobs-queue-dev",
            "visibility_timeout_seconds": 900,
            "message_retention_seconds": 86400,
            "dead_letter_queue_url": "https://sqs.us-east-1.amazonaws.com/123/dlq",
            "dead_letter_queue_name": "careervp-vpr-jobs-dlq-dev",
        },
        "oidc": {
            "provider_arn": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com",
            "audience": "sts.amazonaws.com",
            "role_arn": "arn:aws:iam::123456789012:role/github-actions-role",
        },
        "cloudwatch_alarms": [
            {"name": "careervp-vpr-dlq-alarm-dev", "threshold": 1},
            {"name": "careervp-vpr-worker-errors-dev", "threshold": 5},
        ],
    }


# ============================================================================
# HTTP RESPONSE FIXTURES
# ============================================================================


@pytest.fixture
def http_202_accepted() -> Dict[str, Any]:
    """Return HTTP 202 Accepted response."""
    return {"status_code": 202, "data": {"job_id": "job-123", "status": "PENDING"}}


@pytest.fixture
def http_200_ok() -> Dict[str, Any]:
    """Return HTTP 200 OK response."""
    return {"status_code": 200, "data": {"status": "PROCESSING"}}


@pytest.fixture
def http_404_not_found() -> Dict[str, Any]:
    """Return HTTP 404 Not Found response."""
    return {"status_code": 404, "error": "Job not found"}


@pytest.fixture
def http_410_gone() -> Dict[str, Any]:
    """Return HTTP 410 Gone response."""
    return {"status_code": 410, "error": "Result expired"}


@pytest.fixture
def http_500_error() -> Dict[str, Any]:
    """Return HTTP 500 Internal Server Error response."""
    return {"status_code": 500, "error": "Internal server error"}


# ============================================================================
# PYTEST CONFIGURATION HOOKS
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on file location."""
    for item in items:
        if "test_frontend_client" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "test_async_workflow" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "test_deployment_validation" in item.nodeid:
            item.add_marker(pytest.mark.unit)


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment between tests."""
    yield
    # Clean up any test-specific environment variables
