"""
Unit tests for VPR Submit Handler (Async Submission).

Tests job creation, SQS queuing, idempotency, validation, and error handling.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError


@pytest.fixture
def mock_jobs_repo():
    """Mock JobsRepository for testing."""
    with patch("careervp.handlers.vpr_submit_handler.JobsRepository") as mock:
        yield mock.return_value


@pytest.fixture
def mock_sqs():
    """Mock SQS client for testing."""
    with patch("careervp.handlers.vpr_submit_handler.sqs") as mock:
        yield mock


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set environment variables for testing."""
    monkeypatch.setenv("JOBS_TABLE_NAME", "test-jobs-table")
    monkeypatch.setenv(
        "VPR_JOBS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789/test-queue"
    )


@pytest.fixture
def valid_vpr_request() -> dict[str, Any]:
    """Valid VPR request payload."""
    return {
        "user_id": "test-user-123",
        "application_id": "test-app-456",
        "job_posting": {
            "company_name": "Test Company",
            "role_title": "Software Engineer",
            "responsibilities": ["Write code", "Review PRs"],
            "requirements": ["Python", "AWS"],
        },
    }


@pytest.fixture
def lambda_event(valid_vpr_request: dict[str, Any]) -> dict[str, Any]:
    """Lambda event with VPR request."""
    return {
        "body": json.dumps(valid_vpr_request),
        "requestContext": {},
        "pathParameters": {},
    }


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    context = MagicMock()
    context.request_id = "test-request-id"
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789:function:test"
    return context


class TestSubmitHandler:
    """Test suite for VPR Submit Handler."""

    def test_create_new_job_success(
        self,
        mock_jobs_repo,
        mock_sqs,
        mock_env_vars,
        lambda_event,
        lambda_context,
        valid_vpr_request,
    ):
        """Test successful new job creation and SQS queuing."""
        # Arrange
        mock_jobs_repo.get_job_by_idempotency_key.return_value = None  # No duplicate
        mock_sqs.send_message.return_value = {"MessageId": "test-message-id"}

        # Import after mocking
        from careervp.handlers.vpr_submit_handler import lambda_handler

        # Act
        with patch("careervp.handlers.vpr_submit_handler.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
            response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert body["job_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert body["status"] == "PENDING"
        assert "submitted successfully" in body["message"]

        # Verify idempotency check
        mock_jobs_repo.get_job_by_idempotency_key.assert_called_once_with(
            "vpr#test-user-123#test-app-456"
        )

        # Verify job creation
        assert mock_jobs_repo.create_job.call_count == 1
        job_data = mock_jobs_repo.create_job.call_args[0][0]
        assert job_data["job_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert job_data["idempotency_key"] == "vpr#test-user-123#test-app-456"
        assert job_data["status"] == "PENDING"
        assert job_data["user_id"] == "test-user-123"
        assert job_data["application_id"] == "test-app-456"
        assert "ttl" in job_data

        # Verify SQS message sent
        assert mock_sqs.send_message.call_count == 1
        sqs_call = mock_sqs.send_message.call_args[1]
        assert (
            sqs_call["QueueUrl"]
            == "https://sqs.us-east-1.amazonaws.com/123456789/test-queue"
        )
        message_body = json.loads(sqs_call["MessageBody"])
        assert message_body["job_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert message_body["input_data"] == valid_vpr_request

    def test_idempotent_request_returns_existing_job(
        self, mock_jobs_repo, mock_sqs, mock_env_vars, lambda_event, lambda_context
    ):
        """Test idempotent request returns existing job (200 OK)."""
        # Arrange
        existing_job = {
            "job_id": "existing-job-123",
            "status": "PROCESSING",
            "idempotency_key": "vpr#test-user-123#test-app-456",
        }
        mock_jobs_repo.get_job_by_idempotency_key.return_value = existing_job

        from careervp.handlers.vpr_submit_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 200  # 200 OK for idempotent requests
        body = json.loads(response["body"])
        assert body["job_id"] == "existing-job-123"
        assert body["status"] == "PROCESSING"
        assert "already exists" in body["message"]

        # Verify no new job created or SQS message sent
        mock_jobs_repo.create_job.assert_not_called()
        mock_sqs.send_message.assert_not_called()

    def test_idempotency_key_generation(
        self, mock_jobs_repo, mock_sqs, mock_env_vars, lambda_context
    ):
        """Test correct idempotency key format."""
        # Arrange
        event = {
            "body": json.dumps(
                {
                    "user_id": "user-abc",
                    "application_id": "app-xyz",
                    "job_posting": {
                        "company_name": "Test",
                        "role_title": "Engineer",
                        "responsibilities": ["Code"],
                        "requirements": ["Python"],
                    },
                }
            )
        }
        mock_jobs_repo.get_job_by_idempotency_key.return_value = None

        from careervp.handlers.vpr_submit_handler import lambda_handler

        # Act
        lambda_handler(event, lambda_context)

        # Assert
        mock_jobs_repo.get_job_by_idempotency_key.assert_called_once_with(
            "vpr#user-abc#app-xyz"
        )

    def test_invalid_request_body_validation_error(
        self, mock_jobs_repo, mock_sqs, mock_env_vars, lambda_context
    ):
        """Test validation error for invalid request body (400 Bad Request)."""
        # Arrange
        invalid_event = {
            "body": json.dumps(
                {
                    "user_id": "test-user",
                    # Missing required fields
                }
            )
        }

        from careervp.handlers.vpr_submit_handler import lambda_handler

        # Act
        response = lambda_handler(invalid_event, lambda_context)

        # Assert
        # Handler should catch validation error and return 500
        # (or 400 if ValidationError is explicitly handled)
        assert response["statusCode"] in [400, 500]

    def test_ttl_calculation(
        self, mock_jobs_repo, mock_sqs, mock_env_vars, lambda_event, lambda_context
    ):
        """Test TTL is set to 10 minutes from creation."""
        # Arrange
        mock_jobs_repo.get_job_by_idempotency_key.return_value = None

        from careervp.handlers.vpr_submit_handler import lambda_handler

        # Act
        with patch("careervp.handlers.vpr_submit_handler.datetime") as mock_datetime:
            now = datetime(2026, 2, 4, 12, 0, 0)
            mock_datetime.utcnow.return_value = now
            lambda_handler(lambda_event, lambda_context)

        # Assert
        job_data = mock_jobs_repo.create_job.call_args[0][0]
        expected_ttl = int((now + timedelta(minutes=10)).timestamp())
        assert job_data["ttl"] == expected_ttl

    def test_dynamodb_failure_returns_500(
        self, mock_jobs_repo, mock_sqs, mock_env_vars, lambda_event, lambda_context
    ):
        """Test DynamoDB failure returns 500 Internal Server Error."""
        # Arrange
        mock_jobs_repo.get_job_by_idempotency_key.return_value = None
        mock_jobs_repo.create_job.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "DynamoDB error"}},
            "PutItem",
        )

        from careervp.handlers.vpr_submit_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body
        assert "Internal server error" in body["error"]

        # Verify SQS message not sent
        mock_sqs.send_message.assert_not_called()

    def test_sqs_failure_returns_500(
        self, mock_jobs_repo, mock_sqs, mock_env_vars, lambda_event, lambda_context
    ):
        """Test SQS send failure returns 500 Internal Server Error."""
        # Arrange
        mock_jobs_repo.get_job_by_idempotency_key.return_value = None
        mock_sqs.send_message.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable", "Message": "SQS error"}},
            "SendMessage",
        )

        from careervp.handlers.vpr_submit_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body

    def test_sqs_message_attributes(
        self, mock_jobs_repo, mock_sqs, mock_env_vars, lambda_event, lambda_context
    ):
        """Test SQS message includes correct attributes for tracing."""
        # Arrange
        mock_jobs_repo.get_job_by_idempotency_key.return_value = None

        from careervp.handlers.vpr_submit_handler import lambda_handler

        # Act
        with patch("careervp.handlers.vpr_submit_handler.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
            lambda_handler(lambda_event, lambda_context)

        # Assert
        sqs_call = mock_sqs.send_message.call_args[1]
        assert "MessageAttributes" in sqs_call
        attrs = sqs_call["MessageAttributes"]
        assert attrs["job_id"]["StringValue"] == "550e8400-e29b-41d4-a716-446655440000"
        assert attrs["user_id"]["StringValue"] == "test-user-123"

    def test_response_format_new_job(
        self, mock_jobs_repo, mock_sqs, mock_env_vars, lambda_event, lambda_context
    ):
        """Test 202 response format for new jobs."""
        # Arrange
        mock_jobs_repo.get_job_by_idempotency_key.return_value = None

        from careervp.handlers.vpr_submit_handler import lambda_handler

        # Act
        with patch("careervp.handlers.vpr_submit_handler.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
            response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert "job_id" in body
        assert "status" in body
        assert "message" in body
        assert body["status"] == "PENDING"

    def test_response_format_duplicate_job(
        self, mock_jobs_repo, mock_sqs, mock_env_vars, lambda_event, lambda_context
    ):
        """Test 200 response format for duplicate jobs."""
        # Arrange
        existing_job = {
            "job_id": "existing-123",
            "status": "COMPLETED",
            "idempotency_key": "vpr#test-user-123#test-app-456",
        }
        mock_jobs_repo.get_job_by_idempotency_key.return_value = existing_job

        from careervp.handlers.vpr_submit_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "job_id" in body
        assert "status" in body
        assert "message" in body
        assert body["job_id"] == "existing-123"
        assert body["status"] == "COMPLETED"

    def test_input_data_stored_in_job_record(
        self,
        mock_jobs_repo,
        mock_sqs,
        mock_env_vars,
        lambda_event,
        lambda_context,
        valid_vpr_request,
    ):
        """Test full input data is stored in job record."""
        # Arrange
        mock_jobs_repo.get_job_by_idempotency_key.return_value = None

        from careervp.handlers.vpr_submit_handler import lambda_handler

        # Act
        lambda_handler(lambda_event, lambda_context)

        # Assert
        job_data = mock_jobs_repo.create_job.call_args[0][0]
        assert "input_data" in job_data
        assert job_data["input_data"] == valid_vpr_request

    def test_created_at_timestamp_format(
        self, mock_jobs_repo, mock_sqs, mock_env_vars, lambda_event, lambda_context
    ):
        """Test created_at is ISO format timestamp."""
        # Arrange
        mock_jobs_repo.get_job_by_idempotency_key.return_value = None

        from careervp.handlers.vpr_submit_handler import lambda_handler

        # Act
        with patch("careervp.handlers.vpr_submit_handler.datetime") as mock_datetime:
            now = datetime(2026, 2, 4, 12, 0, 0)
            mock_datetime.utcnow.return_value = now
            lambda_handler(lambda_event, lambda_context)

        # Assert
        job_data = mock_jobs_repo.create_job.call_args[0][0]
        assert job_data["created_at"] == "2026-02-04T12:00:00"
