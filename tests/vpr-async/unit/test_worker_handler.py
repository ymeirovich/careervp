"""
Unit tests for VPR Worker Handler (Async Processing).

Tests SQS message processing, VPR generation, status updates, S3 storage, and error handling.
"""

import json
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError


@pytest.fixture
def mock_jobs_repo():
    """Mock JobsRepository for testing."""
    with patch("careervp.handlers.vpr_worker_handler.JobsRepository") as mock:
        yield mock.return_value


@pytest.fixture
def mock_dal():
    """Mock DynamoDalHandler for testing."""
    with patch("careervp.handlers.vpr_worker_handler.DynamoDalHandler") as mock:
        yield mock.return_value


@pytest.fixture
def mock_vpr_gen():
    """Mock VPRGenerator for testing."""
    with patch("careervp.handlers.vpr_worker_handler.VPRGenerator") as mock:
        yield mock.return_value


@pytest.fixture
def mock_s3():
    """Mock S3 client for testing."""
    with patch("careervp.handlers.vpr_worker_handler.s3") as mock:
        yield mock


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set environment variables for testing."""
    monkeypatch.setenv("JOBS_TABLE_NAME", "test-jobs-table")
    monkeypatch.setenv("USERS_TABLE_NAME", "test-users-table")
    monkeypatch.setenv("VPR_RESULTS_BUCKET_NAME", "test-results-bucket")


@pytest.fixture
def vpr_request_data() -> dict[str, Any]:
    """Valid VPR request data."""
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
def sqs_record(vpr_request_data: dict[str, Any]) -> dict[str, Any]:
    """SQS record with VPR job."""
    return {
        "messageId": "test-message-id",
        "receiptHandle": "test-receipt-handle",
        "body": json.dumps({"job_id": "test-job-123", "input_data": vpr_request_data}),
        "attributes": {"ApproximateReceiveCount": "1"},
    }


@pytest.fixture
def sqs_event(sqs_record: dict[str, Any]) -> dict[str, Any]:
    """Lambda SQS event."""
    return {"Records": [sqs_record]}


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    context = MagicMock()
    context.request_id = "test-request-id"
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789:function:test"
    return context


@pytest.fixture
def mock_vpr_result():
    """Mock successful VPR result."""
    result = MagicMock()
    result.success = True
    result.data = MagicMock()
    result.data.model_dump.return_value = {
        "vpr": {"title": "Tailored Resume", "content": "Resume content..."},
        "token_usage": {"input_tokens": 7500, "output_tokens": 2200},
    }
    result.data.token_usage = {"input_tokens": 7500, "output_tokens": 2200}
    return result


@pytest.fixture
def mock_user_cv():
    """Mock user CV data."""
    return {
        "user_id": "test-user-123",
        "cv_data": {
            "personal_info": {"name": "Test User"},
            "experience": [],
            "education": [],
        },
    }


class TestWorkerHandler:
    """Test suite for VPR Worker Handler."""

    def test_process_job_success(
        self,
        mock_jobs_repo,
        mock_dal,
        mock_vpr_gen,
        mock_s3,
        mock_env_vars,
        sqs_event,
        lambda_context,
        mock_vpr_result,
        mock_user_cv,
    ):
        """Test successful VPR job processing end-to-end."""
        # Arrange
        mock_dal.get_user_cv.return_value = mock_user_cv
        mock_vpr_gen.generate_vpr.return_value = mock_vpr_result
        mock_s3.put_object.return_value = {"ETag": "test-etag"}

        from careervp.handlers.vpr_worker_handler import lambda_handler

        # Act
        response = lambda_handler(sqs_event, lambda_context)

        # Assert - successful processing
        assert "batchItemFailures" in response
        assert len(response["batchItemFailures"]) == 0  # No failures

        # Verify status updated to PROCESSING
        assert mock_jobs_repo.update_job_status.call_count == 1
        status_call = mock_jobs_repo.update_job_status.call_args[1]
        assert status_call["job_id"] == "test-job-123"
        assert status_call["status"] == "PROCESSING"
        assert "started_at" in status_call

        # Verify VPR generated
        assert mock_vpr_gen.generate_vpr.call_count == 1
        vpr_call = mock_vpr_gen.generate_vpr.call_args[1]
        assert vpr_call["user_cv"] == mock_user_cv
        assert vpr_call["dal"] == mock_dal

        # Verify S3 storage
        assert mock_s3.put_object.call_count == 1
        s3_call = mock_s3.put_object.call_args[1]
        assert s3_call["Bucket"] == "test-results-bucket"
        assert s3_call["Key"] == "results/test-job-123.json"
        assert s3_call["ContentType"] == "application/json"
        assert s3_call["Metadata"]["job_id"] == "test-job-123"
        assert s3_call["Metadata"]["user_id"] == "test-user-123"

        # Verify job updated to COMPLETED
        assert mock_jobs_repo.update_job.call_count == 1
        update_call = mock_jobs_repo.update_job.call_args[1]
        assert update_call["job_id"] == "test-job-123"
        assert update_call["updates"]["status"] == "COMPLETED"
        assert "completed_at" in update_call["updates"]
        assert update_call["updates"]["result_key"] == "results/test-job-123.json"
        assert "token_usage" in update_call["updates"]

        # Verify VPR persisted to users table
        assert mock_dal.store_vpr_artifact.call_count == 1

    def test_status_transitions_pending_to_processing_to_completed(
        self,
        mock_jobs_repo,
        mock_dal,
        mock_vpr_gen,
        mock_s3,
        mock_env_vars,
        sqs_event,
        lambda_context,
        mock_vpr_result,
        mock_user_cv,
    ):
        """Test job status transitions correctly through states."""
        # Arrange
        mock_dal.get_user_cv.return_value = mock_user_cv
        mock_vpr_gen.generate_vpr.return_value = mock_vpr_result

        from careervp.handlers.vpr_worker_handler import lambda_handler

        # Act
        lambda_handler(sqs_event, lambda_context)

        # Assert - verify status progression
        # 1. PENDING → PROCESSING
        status_update = mock_jobs_repo.update_job_status.call_args[1]
        assert status_update["status"] == "PROCESSING"

        # 2. PROCESSING → COMPLETED
        final_update = mock_jobs_repo.update_job.call_args[1]
        assert final_update["updates"]["status"] == "COMPLETED"

    def test_user_cv_not_found_raises_error(
        self,
        mock_jobs_repo,
        mock_dal,
        mock_vpr_gen,
        mock_s3,
        mock_env_vars,
        sqs_event,
        lambda_context,
    ):
        """Test error when user CV not found."""
        # Arrange
        mock_dal.get_user_cv.return_value = None

        from careervp.handlers.vpr_worker_handler import lambda_handler

        # Act
        response = lambda_handler(sqs_event, lambda_context)

        # Assert - failure reported
        assert "batchItemFailures" in response
        assert len(response["batchItemFailures"]) == 1
        assert response["batchItemFailures"][0]["itemIdentifier"] == "test-message-id"

        # Verify status updated to FAILED
        update_call = mock_jobs_repo.update_job.call_args[1]
        assert update_call["updates"]["status"] == "FAILED"
        assert "User CV not found" in update_call["updates"]["error"]

    def test_vpr_generation_failure_updates_status_to_failed(
        self,
        mock_jobs_repo,
        mock_dal,
        mock_vpr_gen,
        mock_s3,
        mock_env_vars,
        sqs_event,
        lambda_context,
        mock_user_cv,
    ):
        """Test VPR generation failure updates job to FAILED."""
        # Arrange
        mock_dal.get_user_cv.return_value = mock_user_cv
        mock_vpr_result = MagicMock()
        mock_vpr_result.success = False
        mock_vpr_result.error = "Claude API timeout"
        mock_vpr_gen.generate_vpr.return_value = mock_vpr_result

        from careervp.handlers.vpr_worker_handler import lambda_handler

        # Act
        response = lambda_handler(sqs_event, lambda_context)

        # Assert
        assert len(response["batchItemFailures"]) == 1

        # Verify FAILED status
        update_call = mock_jobs_repo.update_job.call_args[1]
        assert update_call["updates"]["status"] == "FAILED"
        assert "Claude API timeout" in update_call["updates"]["error"]

    def test_claude_api_exception_triggers_retry(
        self,
        mock_jobs_repo,
        mock_dal,
        mock_vpr_gen,
        mock_s3,
        mock_env_vars,
        sqs_event,
        lambda_context,
        mock_user_cv,
    ):
        """Test Claude API exception triggers SQS retry."""
        # Arrange
        mock_dal.get_user_cv.return_value = mock_user_cv
        mock_vpr_gen.generate_vpr.side_effect = Exception("API rate limit exceeded")

        from careervp.handlers.vpr_worker_handler import lambda_handler

        # Act
        response = lambda_handler(sqs_event, lambda_context)

        # Assert - batch item failure reported for retry
        assert len(response["batchItemFailures"]) == 1
        assert response["batchItemFailures"][0]["itemIdentifier"] == "test-message-id"

        # Verify FAILED status set
        update_call = mock_jobs_repo.update_job.call_args[1]
        assert update_call["updates"]["status"] == "FAILED"

    def test_s3_result_storage_format(
        self,
        mock_jobs_repo,
        mock_dal,
        mock_vpr_gen,
        mock_s3,
        mock_env_vars,
        sqs_event,
        lambda_context,
        mock_vpr_result,
        mock_user_cv,
    ):
        """Test S3 result stored with correct format and metadata."""
        # Arrange
        mock_dal.get_user_cv.return_value = mock_user_cv
        mock_vpr_gen.generate_vpr.return_value = mock_vpr_result

        from careervp.handlers.vpr_worker_handler import lambda_handler

        # Act
        lambda_handler(sqs_event, lambda_context)

        # Assert
        s3_call = mock_s3.put_object.call_args[1]

        # Verify key format
        assert s3_call["Key"] == "results/test-job-123.json"

        # Verify content type
        assert s3_call["ContentType"] == "application/json"

        # Verify metadata
        assert s3_call["Metadata"]["job_id"] == "test-job-123"
        assert s3_call["Metadata"]["user_id"] == "test-user-123"
        assert s3_call["Metadata"]["application_id"] == "test-app-456"

        # Verify body is JSON
        body = json.loads(s3_call["Body"])
        assert "vpr" in body
        assert "token_usage" in body

    def test_s3_put_failure_triggers_retry(
        self,
        mock_jobs_repo,
        mock_dal,
        mock_vpr_gen,
        mock_s3,
        mock_env_vars,
        sqs_event,
        lambda_context,
        mock_vpr_result,
        mock_user_cv,
    ):
        """Test S3 put failure triggers SQS retry."""
        # Arrange
        mock_dal.get_user_cv.return_value = mock_user_cv
        mock_vpr_gen.generate_vpr.return_value = mock_vpr_result
        mock_s3.put_object.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable", "Message": "S3 error"}},
            "PutObject",
        )

        from careervp.handlers.vpr_worker_handler import lambda_handler

        # Act
        response = lambda_handler(sqs_event, lambda_context)

        # Assert - failure triggers retry
        assert len(response["batchItemFailures"]) == 1

    def test_token_usage_stored_in_job_record(
        self,
        mock_jobs_repo,
        mock_dal,
        mock_vpr_gen,
        mock_s3,
        mock_env_vars,
        sqs_event,
        lambda_context,
        mock_vpr_result,
        mock_user_cv,
    ):
        """Test token usage is stored in job record."""
        # Arrange
        mock_dal.get_user_cv.return_value = mock_user_cv
        mock_vpr_gen.generate_vpr.return_value = mock_vpr_result

        from careervp.handlers.vpr_worker_handler import lambda_handler

        # Act
        lambda_handler(sqs_event, lambda_context)

        # Assert
        update_call = mock_jobs_repo.update_job.call_args[1]
        token_usage = update_call["updates"]["token_usage"]
        assert token_usage["input_tokens"] == 7500
        assert token_usage["output_tokens"] == 2200

    def test_result_key_stored_in_job_record(
        self,
        mock_jobs_repo,
        mock_dal,
        mock_vpr_gen,
        mock_s3,
        mock_env_vars,
        sqs_event,
        lambda_context,
        mock_vpr_result,
        mock_user_cv,
    ):
        """Test result_key is stored in job record for status handler."""
        # Arrange
        mock_dal.get_user_cv.return_value = mock_user_cv
        mock_vpr_gen.generate_vpr.return_value = mock_vpr_result

        from careervp.handlers.vpr_worker_handler import lambda_handler

        # Act
        lambda_handler(sqs_event, lambda_context)

        # Assert
        update_call = mock_jobs_repo.update_job.call_args[1]
        assert update_call["updates"]["result_key"] == "results/test-job-123.json"

    def test_vpr_persisted_to_users_table(
        self,
        mock_jobs_repo,
        mock_dal,
        mock_vpr_gen,
        mock_s3,
        mock_env_vars,
        sqs_event,
        lambda_context,
        mock_vpr_result,
        mock_user_cv,
    ):
        """Test VPR is persisted to users table (existing pattern)."""
        # Arrange
        mock_dal.get_user_cv.return_value = mock_user_cv
        mock_vpr_gen.generate_vpr.return_value = mock_vpr_result

        from careervp.handlers.vpr_worker_handler import lambda_handler

        # Act
        lambda_handler(sqs_event, lambda_context)

        # Assert
        assert mock_dal.store_vpr_artifact.call_count == 1
        store_call = mock_dal.store_vpr_artifact.call_args[0]
        assert store_call[0] == "test-app-456"  # application_id
        assert store_call[1] == mock_vpr_result.data

    def test_batch_processor_partial_failures(
        self,
        mock_jobs_repo,
        mock_dal,
        mock_vpr_gen,
        mock_s3,
        mock_env_vars,
        lambda_context,
        vpr_request_data,
    ):
        """Test batch processor handles partial failures correctly."""
        # Arrange - 2 records, 1 succeeds, 1 fails
        event = {
            "Records": [
                {
                    "messageId": "success-msg",
                    "body": json.dumps(
                        {"job_id": "success-job", "input_data": vpr_request_data}
                    ),
                },
                {
                    "messageId": "fail-msg",
                    "body": json.dumps(
                        {"job_id": "fail-job", "input_data": vpr_request_data}
                    ),
                },
            ]
        }

        mock_user_cv = {"user_id": "test-user"}
        mock_dal.get_user_cv.return_value = mock_user_cv

        # First call succeeds, second fails
        mock_vpr_result = MagicMock()
        mock_vpr_result.success = True
        mock_vpr_result.data = MagicMock()
        mock_vpr_result.data.model_dump.return_value = {"vpr": "data"}
        mock_vpr_result.data.token_usage = {"input_tokens": 100, "output_tokens": 50}

        mock_vpr_gen.generate_vpr.side_effect = [
            mock_vpr_result,  # Success
            Exception("API error"),  # Failure
        ]

        from careervp.handlers.vpr_worker_handler import lambda_handler

        # Act
        response = lambda_handler(event, lambda_context)

        # Assert - only failed message reported
        assert len(response["batchItemFailures"]) == 1
        assert response["batchItemFailures"][0]["itemIdentifier"] == "fail-msg"

    def test_gap_responses_passed_to_vpr_generator(
        self,
        mock_jobs_repo,
        mock_dal,
        mock_vpr_gen,
        mock_s3,
        mock_env_vars,
        lambda_context,
        mock_vpr_result,
        mock_user_cv,
    ):
        """Test gap_responses are passed to VPR generator if provided."""
        # Arrange
        input_data = {
            "user_id": "test-user",
            "application_id": "test-app",
            "job_posting": {
                "company_name": "Test",
                "role_title": "Engineer",
                "responsibilities": ["Code"],
                "requirements": ["Python"],
            },
            "gap_responses": [{"question": "Q1", "answer": "A1"}],
        }

        event = {
            "Records": [
                {
                    "messageId": "test-msg",
                    "body": json.dumps(
                        {"job_id": "test-job", "input_data": input_data}
                    ),
                }
            ]
        }

        mock_dal.get_user_cv.return_value = mock_user_cv
        mock_vpr_gen.generate_vpr.return_value = mock_vpr_result

        from careervp.handlers.vpr_worker_handler import lambda_handler

        # Act
        lambda_handler(event, lambda_context)

        # Assert
        vpr_call = mock_vpr_gen.generate_vpr.call_args[1]
        assert vpr_call["gap_responses"] == [{"question": "Q1", "answer": "A1"}]

    def test_completed_at_timestamp_format(
        self,
        mock_jobs_repo,
        mock_dal,
        mock_vpr_gen,
        mock_s3,
        mock_env_vars,
        sqs_event,
        lambda_context,
        mock_vpr_result,
        mock_user_cv,
    ):
        """Test completed_at is ISO format timestamp."""
        # Arrange
        mock_dal.get_user_cv.return_value = mock_user_cv
        mock_vpr_gen.generate_vpr.return_value = mock_vpr_result

        from careervp.handlers.vpr_worker_handler import lambda_handler

        # Act
        with patch("careervp.handlers.vpr_worker_handler.datetime") as mock_datetime:
            now = datetime(2026, 2, 4, 13, 30, 0)
            mock_datetime.utcnow.return_value = now
            lambda_handler(sqs_event, lambda_context)

        # Assert
        update_call = mock_jobs_repo.update_job.call_args[1]
        assert update_call["updates"]["completed_at"] == "2026-02-04T13:30:00"
