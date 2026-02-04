"""
Integration tests for gap analysis submit handler.
Tests for handlers/gap_submit_handler.py (POST /api/gap-analysis/submit).

RED PHASE: These tests will FAIL until gap_submit_handler.py is implemented.
"""

import json
from typing import Any
from unittest.mock import MagicMock, patch

# This import will fail until the module is created
from careervp.handlers.gap_submit_handler import lambda_handler


class TestSubmitHandlerSuccess:
    """Test successful job submission."""

    def test_submit_creates_job_and_returns_202(
        self,
        mock_api_gateway_event: dict[str, Any],
        mock_lambda_context,
        mock_job_id: str,
    ):
        """Test successful job submission returns 202 ACCEPTED."""
        with (
            patch(
                "careervp.handlers.gap_submit_handler.DynamoDalHandler"
            ) as mock_dal_class,
            patch("careervp.handlers.gap_submit_handler.boto3") as mock_boto3,
        ):
            # Mock DAL
            mock_dal = MagicMock()
            mock_dal.create_job.return_value = MagicMock(success=True)
            mock_dal_class.return_value = mock_dal

            # Mock SQS
            mock_sqs = MagicMock()
            mock_boto3.client.return_value = mock_sqs
            mock_sqs.send_message.return_value = {"MessageId": "msg-123"}

            # Execute
            response = lambda_handler(mock_api_gateway_event, mock_lambda_context)

        # Assert HTTP 202
        assert response["statusCode"] == 202

        # Assert response body
        body = json.loads(response["body"])
        assert "job_id" in body
        assert body["status"] == "PENDING"
        assert "created_at" in body

        # Assert DAL called
        mock_dal.create_job.assert_called_once()

        # Assert SQS called
        mock_sqs.send_message.assert_called_once()

    def test_submit_generates_unique_job_id(
        self, mock_api_gateway_event: dict[str, Any], mock_lambda_context
    ):
        """Test that each submission generates a unique job ID."""
        with (
            patch(
                "careervp.handlers.gap_submit_handler.DynamoDalHandler"
            ) as mock_dal_class,
            patch("careervp.handlers.gap_submit_handler.boto3") as mock_boto3,
        ):
            mock_dal = MagicMock()
            mock_dal.create_job.return_value = MagicMock(success=True)
            mock_dal_class.return_value = mock_dal

            mock_sqs = MagicMock()
            mock_boto3.client.return_value = mock_sqs

            # Execute twice
            response1 = lambda_handler(mock_api_gateway_event, mock_lambda_context)
            response2 = lambda_handler(mock_api_gateway_event, mock_lambda_context)

        body1 = json.loads(response1["body"])
        body2 = json.loads(response2["body"])

        # Assert different job IDs
        assert body1["job_id"] != body2["job_id"]

    def test_submit_includes_cors_headers(
        self, mock_api_gateway_event: dict[str, Any], mock_lambda_context
    ):
        """Test that response includes CORS headers."""
        with (
            patch(
                "careervp.handlers.gap_submit_handler.DynamoDalHandler"
            ) as mock_dal_class,
            patch("careervp.handlers.gap_submit_handler.boto3") as mock_boto3,
        ):
            mock_dal = MagicMock()
            mock_dal.create_job.return_value = MagicMock(success=True)
            mock_dal_class.return_value = mock_dal

            mock_sqs = MagicMock()
            mock_boto3.client.return_value = mock_sqs

            response = lambda_handler(mock_api_gateway_event, mock_lambda_context)

        # Assert CORS headers
        assert "headers" in response
        assert "Access-Control-Allow-Origin" in response["headers"]


class TestSubmitHandlerValidation:
    """Test input validation."""

    def test_submit_rejects_missing_user_id(
        self, mock_api_gateway_event: dict[str, Any], mock_lambda_context
    ):
        """Test that missing user_id returns 400."""
        event = mock_api_gateway_event.copy()
        body = json.loads(event["body"])
        del body["user_id"]
        event["body"] = json.dumps(body)

        response = lambda_handler(event, mock_lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert body["code"] == "VALIDATION_ERROR"

    def test_submit_rejects_missing_cv_id(
        self, mock_api_gateway_event: dict[str, Any], mock_lambda_context
    ):
        """Test that missing cv_id returns 400."""
        event = mock_api_gateway_event.copy()
        body = json.loads(event["body"])
        del body["cv_id"]
        event["body"] = json.dumps(body)

        response = lambda_handler(event, mock_lambda_context)

        assert response["statusCode"] == 400

    def test_submit_validates_file_size(
        self, mock_api_gateway_event: dict[str, Any], mock_lambda_context
    ):
        """Test that oversized job postings are rejected."""
        event = mock_api_gateway_event.copy()
        body = json.loads(event["body"])
        # Create huge job posting description
        body["job_posting"]["description"] = "a" * (11 * 1024 * 1024)  # 11MB
        event["body"] = json.dumps(body)

        response = lambda_handler(event, mock_lambda_context)

        assert response["statusCode"] == 413
        body = json.loads(response["body"])
        assert body["code"] == "PAYLOAD_TOO_LARGE"


class TestSubmitHandlerErrors:
    """Test error handling."""

    def test_submit_handles_dynamodb_error(
        self, mock_api_gateway_event: dict[str, Any], mock_lambda_context
    ):
        """Test handling of DynamoDB errors."""
        with patch(
            "careervp.handlers.gap_submit_handler.DynamoDalHandler"
        ) as mock_dal_class:
            mock_dal = MagicMock()
            mock_dal.create_job.return_value = MagicMock(
                success=False, error="DynamoDB throttling"
            )
            mock_dal_class.return_value = mock_dal

            response = lambda_handler(mock_api_gateway_event, mock_lambda_context)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["code"] == "INTERNAL_ERROR"

    def test_submit_handles_sqs_error(
        self, mock_api_gateway_event: dict[str, Any], mock_lambda_context
    ):
        """Test handling of SQS send errors."""
        with (
            patch(
                "careervp.handlers.gap_submit_handler.DynamoDalHandler"
            ) as mock_dal_class,
            patch("careervp.handlers.gap_submit_handler.boto3") as mock_boto3,
        ):
            mock_dal = MagicMock()
            mock_dal.create_job.return_value = MagicMock(success=True)
            mock_dal_class.return_value = mock_dal

            mock_sqs = MagicMock()
            mock_boto3.client.return_value = mock_sqs
            mock_sqs.send_message.side_effect = Exception("SQS error")

            response = lambda_handler(mock_api_gateway_event, mock_lambda_context)

        assert response["statusCode"] == 500


class TestSubmitHandlerAuth:
    """Test authentication and authorization."""

    def test_submit_extracts_user_id_from_jwt(
        self, mock_api_gateway_event: dict[str, Any], mock_lambda_context
    ):
        """Test that user_id is extracted from JWT claims."""
        with (
            patch(
                "careervp.handlers.gap_submit_handler.DynamoDalHandler"
            ) as mock_dal_class,
            patch("careervp.handlers.gap_submit_handler.boto3") as mock_boto3,
        ):
            mock_dal = MagicMock()
            mock_dal.create_job.return_value = MagicMock(success=True)
            mock_dal_class.return_value = mock_dal

            mock_sqs = MagicMock()
            mock_boto3.client.return_value = mock_sqs

            lambda_handler(mock_api_gateway_event, mock_lambda_context)

        # Assert job created with correct user_id from JWT
        call_args = mock_dal.create_job.call_args[1]
        assert call_args["user_id"] == "user_test_123"

    def test_submit_rejects_mismatched_user_id(
        self, mock_api_gateway_event: dict[str, Any], mock_lambda_context
    ):
        """Test that user cannot submit for a different user_id."""
        event = mock_api_gateway_event.copy()
        body = json.loads(event["body"])
        body["user_id"] = "different_user_456"  # Mismatch with JWT claim
        event["body"] = json.dumps(body)

        response = lambda_handler(event, mock_lambda_context)

        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert body["code"] == "FORBIDDEN"
