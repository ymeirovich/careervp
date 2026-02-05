"""
Unit tests for VPR Status Handler (Status Polling).

Tests job status retrieval, presigned URL generation, and all status responses.
"""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError


@pytest.fixture
def mock_jobs_repo():
    """Mock JobsRepository for testing."""
    with patch("careervp.handlers.vpr_status_handler.JobsRepository") as mock:
        yield mock.return_value


@pytest.fixture
def mock_s3():
    """Mock S3 client for testing."""
    with patch("careervp.handlers.vpr_status_handler.s3") as mock:
        yield mock


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set environment variables for testing."""
    monkeypatch.setenv("JOBS_TABLE_NAME", "test-jobs-table")
    monkeypatch.setenv("VPR_RESULTS_BUCKET_NAME", "test-results-bucket")


@pytest.fixture
def lambda_event() -> dict[str, Any]:
    """Lambda event with job_id in path parameters."""
    return {"pathParameters": {"job_id": "test-job-123"}, "requestContext": {}}


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    context = MagicMock()
    context.request_id = "test-request-id"
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789:function:test"
    return context


class TestStatusHandler:
    """Test suite for VPR Status Handler."""

    def test_pending_job_returns_202_accepted(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test PENDING job returns 202 Accepted with created_at."""
        # Arrange
        pending_job = {
            "job_id": "test-job-123",
            "status": "PENDING",
            "created_at": "2026-02-04T12:00:00Z",
            "user_id": "test-user-123",
        }
        mock_jobs_repo.get_job.return_value = pending_job

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert body["job_id"] == "test-job-123"
        assert body["status"] == "PENDING"
        assert body["created_at"] == "2026-02-04T12:00:00Z"
        assert "result_url" not in body  # No result yet

        # Verify job fetched
        mock_jobs_repo.get_job.assert_called_once_with("test-job-123")

        # Verify no S3 call
        mock_s3.generate_presigned_url.assert_not_called()

    def test_processing_job_returns_202_accepted(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test PROCESSING job returns 202 Accepted with started_at."""
        # Arrange
        processing_job = {
            "job_id": "test-job-123",
            "status": "PROCESSING",
            "created_at": "2026-02-04T12:00:00Z",
            "started_at": "2026-02-04T12:00:05Z",
            "user_id": "test-user-123",
        }
        mock_jobs_repo.get_job.return_value = processing_job

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert body["job_id"] == "test-job-123"
        assert body["status"] == "PROCESSING"
        assert body["created_at"] == "2026-02-04T12:00:00Z"
        assert body["started_at"] == "2026-02-04T12:00:05Z"
        assert "result_url" not in body

    def test_completed_job_returns_200_with_presigned_url(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test COMPLETED job returns 200 OK with presigned S3 URL."""
        # Arrange
        completed_job = {
            "job_id": "test-job-123",
            "status": "COMPLETED",
            "created_at": "2026-02-04T12:00:00Z",
            "completed_at": "2026-02-04T12:01:00Z",
            "result_key": "results/test-job-123.json",
            "token_usage": {"input_tokens": 7500, "output_tokens": 2200},
            "user_id": "test-user-123",
        }
        mock_jobs_repo.get_job.return_value = completed_job
        mock_s3.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-bucket/results/test-job-123.json?signature=xyz"

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["job_id"] == "test-job-123"
        assert body["status"] == "COMPLETED"
        assert body["completed_at"] == "2026-02-04T12:01:00Z"
        assert (
            body["result_url"]
            == "https://s3.amazonaws.com/test-bucket/results/test-job-123.json?signature=xyz"
        )
        assert body["token_usage"]["input_tokens"] == 7500
        assert body["token_usage"]["output_tokens"] == 2200

        # Verify presigned URL generated
        mock_s3.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={
                "Bucket": "test-results-bucket",
                "Key": "results/test-job-123.json",
            },
            ExpiresIn=3600,  # 1 hour
        )

    def test_failed_job_returns_200_with_error(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test FAILED job returns 200 OK with error message."""
        # Arrange
        failed_job = {
            "job_id": "test-job-123",
            "status": "FAILED",
            "created_at": "2026-02-04T12:00:00Z",
            "error": "Claude API rate limit exceeded",
            "user_id": "test-user-123",
        }
        mock_jobs_repo.get_job.return_value = failed_job

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 200  # 200 OK (job completed, but failed)
        body = json.loads(response["body"])
        assert body["job_id"] == "test-job-123"
        assert body["status"] == "FAILED"
        assert body["error"] == "Claude API rate limit exceeded"
        assert "result_url" not in body

    def test_job_not_found_returns_404(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test non-existent job returns 404 Not Found."""
        # Arrange
        mock_jobs_repo.get_job.return_value = None

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "error" in body
        assert "not found" in body["error"].lower()
        assert "expired" in body["error"].lower()  # Mention TTL expiry

    def test_expired_job_returns_404(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test expired job (past TTL) returns 404."""
        # Arrange - DynamoDB returns None for expired items
        mock_jobs_repo.get_job.return_value = None

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 404

    def test_s3_result_expired_returns_410_gone(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test COMPLETED job with expired S3 result returns 410 Gone."""
        # Arrange
        completed_job = {
            "job_id": "test-job-123",
            "status": "COMPLETED",
            "created_at": "2026-02-04T12:00:00Z",
            "completed_at": "2026-02-04T12:01:00Z",
            "result_key": "results/test-job-123.json",
            "user_id": "test-user-123",
        }
        mock_jobs_repo.get_job.return_value = completed_job
        mock_s3.generate_presigned_url.side_effect = ClientError(
            {
                "Error": {
                    "Code": "NoSuchKey",
                    "Message": "The specified key does not exist",
                }
            },
            "GeneratePresignedUrl",
        )

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 410  # Gone
        body = json.loads(response["body"])
        assert "expired" in body["error"].lower()
        assert "regenerate" in body["message"].lower()

    def test_completed_job_missing_result_key_returns_500(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test COMPLETED job missing result_key returns 500."""
        # Arrange
        completed_job = {
            "job_id": "test-job-123",
            "status": "COMPLETED",
            "created_at": "2026-02-04T12:00:00Z",
            # Missing result_key
            "user_id": "test-user-123",
        }
        mock_jobs_repo.get_job.return_value = completed_job

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body

    def test_presigned_url_expiry_is_one_hour(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test presigned URL expires in 1 hour (3600 seconds)."""
        # Arrange
        completed_job = {
            "job_id": "test-job-123",
            "status": "COMPLETED",
            "result_key": "results/test-job-123.json",
            "created_at": "2026-02-04T12:00:00Z",
            "user_id": "test-user-123",
        }
        mock_jobs_repo.get_job.return_value = completed_job
        mock_s3.generate_presigned_url.return_value = "https://presigned-url"

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        lambda_handler(lambda_event, lambda_context)

        # Assert
        presigned_call = mock_s3.generate_presigned_url.call_args[1]
        assert presigned_call["ExpiresIn"] == 3600

    def test_job_id_extraction_from_path_parameters(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_context
    ):
        """Test job_id is correctly extracted from path parameters."""
        # Arrange
        event = {"pathParameters": {"job_id": "custom-job-456"}}
        mock_jobs_repo.get_job.return_value = {
            "job_id": "custom-job-456",
            "status": "PENDING",
            "created_at": "2026-02-04T12:00:00Z",
        }

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        lambda_handler(event, lambda_context)

        # Assert
        mock_jobs_repo.get_job.assert_called_once_with("custom-job-456")

    def test_all_status_types_handled(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test all status types return appropriate responses."""
        from careervp.handlers.vpr_status_handler import lambda_handler

        # Test PENDING
        mock_jobs_repo.get_job.return_value = {
            "job_id": "test",
            "status": "PENDING",
            "created_at": "2026-02-04T12:00:00Z",
        }
        response = lambda_handler(lambda_event, lambda_context)
        assert response["statusCode"] == 202

        # Test PROCESSING
        mock_jobs_repo.get_job.return_value = {
            "job_id": "test",
            "status": "PROCESSING",
            "created_at": "2026-02-04T12:00:00Z",
            "started_at": "2026-02-04T12:00:05Z",
        }
        response = lambda_handler(lambda_event, lambda_context)
        assert response["statusCode"] == 202

        # Test COMPLETED
        mock_jobs_repo.get_job.return_value = {
            "job_id": "test",
            "status": "COMPLETED",
            "created_at": "2026-02-04T12:00:00Z",
            "result_key": "results/test.json",
        }
        mock_s3.generate_presigned_url.return_value = "https://url"
        response = lambda_handler(lambda_event, lambda_context)
        assert response["statusCode"] == 200

        # Test FAILED
        mock_jobs_repo.get_job.return_value = {
            "job_id": "test",
            "status": "FAILED",
            "created_at": "2026-02-04T12:00:00Z",
            "error": "Error message",
        }
        response = lambda_handler(lambda_event, lambda_context)
        assert response["statusCode"] == 200

    def test_unknown_status_returns_500(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test unknown job status returns 500 Internal Server Error."""
        # Arrange
        job_with_unknown_status = {
            "job_id": "test-job-123",
            "status": "UNKNOWN_STATUS",
            "created_at": "2026-02-04T12:00:00Z",
        }
        mock_jobs_repo.get_job.return_value = job_with_unknown_status

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body

    def test_dynamodb_exception_returns_500(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test DynamoDB exception returns 500 Internal Server Error."""
        # Arrange
        mock_jobs_repo.get_job.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "DynamoDB error"}},
            "GetItem",
        )

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body

    def test_s3_generic_exception_returns_500(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test S3 generic exception (not NoSuchKey) returns 500."""
        # Arrange
        completed_job = {
            "job_id": "test-job-123",
            "status": "COMPLETED",
            "result_key": "results/test-job-123.json",
            "created_at": "2026-02-04T12:00:00Z",
        }
        mock_jobs_repo.get_job.return_value = completed_job
        mock_s3.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Permission denied"}},
            "GeneratePresignedUrl",
        )

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        assert response["statusCode"] == 500

    def test_response_includes_base_fields_for_all_statuses(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test all responses include job_id, status, and created_at."""
        # Arrange
        pending_job = {
            "job_id": "test-job-123",
            "status": "PENDING",
            "created_at": "2026-02-04T12:00:00Z",
        }
        mock_jobs_repo.get_job.return_value = pending_job

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        body = json.loads(response["body"])
        assert "job_id" in body
        assert "status" in body
        assert "created_at" in body

    def test_processing_status_includes_started_at_if_present(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test PROCESSING status includes started_at timestamp."""
        # Arrange
        processing_job = {
            "job_id": "test-job-123",
            "status": "PROCESSING",
            "created_at": "2026-02-04T12:00:00Z",
            "started_at": "2026-02-04T12:00:05Z",
        }
        mock_jobs_repo.get_job.return_value = processing_job

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        body = json.loads(response["body"])
        assert body["started_at"] == "2026-02-04T12:00:05Z"

    def test_completed_status_includes_completed_at(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test COMPLETED status includes completed_at timestamp."""
        # Arrange
        completed_job = {
            "job_id": "test-job-123",
            "status": "COMPLETED",
            "created_at": "2026-02-04T12:00:00Z",
            "completed_at": "2026-02-04T12:01:00Z",
            "result_key": "results/test-job-123.json",
        }
        mock_jobs_repo.get_job.return_value = completed_job
        mock_s3.generate_presigned_url.return_value = "https://url"

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        body = json.loads(response["body"])
        assert body["completed_at"] == "2026-02-04T12:01:00Z"

    def test_failed_status_handles_missing_error_field(
        self, mock_jobs_repo, mock_s3, mock_env_vars, lambda_event, lambda_context
    ):
        """Test FAILED status with missing error field uses default message."""
        # Arrange
        failed_job = {
            "job_id": "test-job-123",
            "status": "FAILED",
            "created_at": "2026-02-04T12:00:00Z",
            # No error field
        }
        mock_jobs_repo.get_job.return_value = failed_job

        from careervp.handlers.vpr_status_handler import lambda_handler

        # Act
        response = lambda_handler(lambda_event, lambda_context)

        # Assert
        body = json.loads(response["body"])
        assert "error" in body
        assert body["error"] == "Unknown error"
