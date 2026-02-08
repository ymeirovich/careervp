"""
Unit tests for CV Tailoring Lambda handler.

Tests the handler function in isolation with mocked dependencies to verify
request validation, error handling, response formatting, and integration
with the tailoring logic layer.
"""

import json
from unittest.mock import patch
from careervp.handlers.cv_tailoring_handler import handler
from careervp.models.result import Result, ResultCode


def test_handler_success_200(sample_tailor_request, sample_tailored_cv, lambda_context):
    """Test handler returns 200 with tailored CV on success."""
    # Arrange
    event = {
        "body": json.dumps(sample_tailor_request),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with patch(
        "careervp.handlers.cv_tailoring_handler._fetch_and_tailor_cv"
    ) as mock_tailor:
        mock_tailor.return_value = Result(
            success=True, data=sample_tailored_cv, code=ResultCode.CV_TAILORED_SUCCESS
        )

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["success"] is True
    assert "tailored_cv" in body["data"]


def test_handler_invalid_cv_id_404(lambda_context):
    """Test handler returns 404 when CV not found."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "non-existent-cv",
                "job_description": "Looking for a software engineer with Python experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with patch(
        "careervp.handlers.cv_tailoring_handler._fetch_and_tailor_cv"
    ) as mock_tailor:
        mock_tailor.return_value = Result(
            success=False, code=ResultCode.CV_NOT_FOUND, error="CV not found"
        )

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body["success"] is False
    assert body["code"] == "CV_NOT_FOUND"


def test_handler_job_description_too_short_400(lambda_context):
    """Test handler returns 400 when job description is too short."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Short",  # Too short
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    # Act
    response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False
    assert "job_description" in body["message"].lower()


def test_handler_job_description_too_long_400(lambda_context):
    """Test handler returns 400 when job description exceeds 50K characters."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "x" * 51000,  # Exceeds 50K limit
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    # Act
    response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False
    assert "job_description" in body["message"].lower()


def test_handler_fvs_violation_400(lambda_context):
    """Test handler returns 400 when FVS rejects tailored CV."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a software engineer with Python experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with patch(
        "careervp.handlers.cv_tailoring_handler._fetch_and_tailor_cv"
    ) as mock_tailor:
        mock_tailor.return_value = Result(
            success=False,
            code=ResultCode.FVS_HALLUCINATION_DETECTED,
            error="FVS detected hallucinations",
            data={"violations": [{"field": "dates", "severity": "CRITICAL"}]},
        )

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False
    assert body["code"] == "FVS_HALLUCINATION_DETECTED"


def test_handler_llm_timeout_504(lambda_context):
    """Test handler returns 504 when LLM times out."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a software engineer with Python experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with patch(
        "careervp.handlers.cv_tailoring_handler._fetch_and_tailor_cv"
    ) as mock_tailor:
        mock_tailor.return_value = Result(
            success=False, code=ResultCode.LLM_TIMEOUT, error="LLM request timed out"
        )

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 504
    body = json.loads(response["body"])
    assert body["success"] is False
    assert body["code"] == "LLM_TIMEOUT"


def test_handler_rate_limit_exceeded_429(lambda_context):
    """Test handler returns 429 when rate limit is hit."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a software engineer with Python experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with patch(
        "careervp.handlers.cv_tailoring_handler._fetch_and_tailor_cv"
    ) as mock_tailor:
        mock_tailor.return_value = Result(
            success=False,
            code=ResultCode.RATE_LIMIT_EXCEEDED,
            error="Rate limit exceeded",
        )

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 429
    body = json.loads(response["body"])
    assert body["success"] is False
    assert body["code"] == "RATE_LIMIT_EXCEEDED"


def test_handler_unauthorized_401(lambda_context):
    """Test handler returns 401 when JWT is missing."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a software engineer with Python experience.",
            }
        ),
        "requestContext": {},  # Missing authorizer
    }

    # Act
    response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 401
    body = json.loads(response["body"])
    assert body["success"] is False


def test_handler_forbidden_403(lambda_context):
    """Test handler returns 403 when user doesn't own CV."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a software engineer with Python experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-456"}}},
    }

    with patch(
        "careervp.handlers.cv_tailoring_handler._fetch_and_tailor_cv"
    ) as mock_tailor:
        mock_tailor.return_value = Result(
            success=False,
            code=ResultCode.FORBIDDEN,
            error="User does not have access to this CV",
        )

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 403
    body = json.loads(response["body"])
    assert body["success"] is False
    assert body["code"] == "FORBIDDEN"


def test_handler_malformed_json_400(lambda_context):
    """Test handler returns 400 when request body is malformed JSON."""
    # Arrange
    event = {
        "body": "{invalid json",
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    # Act
    response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False


def test_handler_missing_cv_id_400(lambda_context):
    """Test handler returns 400 when cv_id is missing."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "job_description": "Looking for a software engineer with Python experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    # Act
    response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False


def test_handler_missing_job_description_400(lambda_context):
    """Test handler returns 400 when job_description is missing."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    # Act
    response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False


def test_handler_with_preferences(sample_tailored_cv, lambda_context):
    """Test handler accepts and passes through tailoring preferences."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a software engineer with Python experience.",
                "preferences": {
                    "tone": "formal",
                    "length": "concise",
                },
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with patch(
        "careervp.handlers.cv_tailoring_handler._fetch_and_tailor_cv"
    ) as mock_tailor:
        mock_tailor.return_value = Result(
            success=True, data=sample_tailored_cv, code=ResultCode.CV_TAILORED_SUCCESS
        )

        # Act
        response = handler(event, lambda_context)

        # Assert
        assert response["statusCode"] == 200
        mock_tailor.assert_called_once()
        call_args = mock_tailor.call_args[0][0]
        assert call_args.preferences.tone == "formal"
        assert call_args.preferences.length == "concise"


def test_handler_internal_error_500(lambda_context):
    """Test handler returns 500 on unexpected internal error."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a software engineer with Python experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with patch(
        "careervp.handlers.cv_tailoring_handler._fetch_and_tailor_cv"
    ) as mock_tailor:
        mock_tailor.side_effect = Exception("Unexpected error")

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body["success"] is False


def test_handler_response_includes_download_url(sample_tailored_cv, lambda_context):
    """Test handler response includes S3 download URL."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a software engineer with Python experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    tailored_result = {
        "tailored_cv": sample_tailored_cv,
        "download_url": "https://s3.amazonaws.com/bucket/cv-123-tailored.pdf",
    }

    with patch(
        "careervp.handlers.cv_tailoring_handler._fetch_and_tailor_cv"
    ) as mock_tailor:
        mock_tailor.return_value = Result(
            success=True, data=tailored_result, code=ResultCode.CV_TAILORED_SUCCESS
        )

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "download_url" in body["data"]


def test_handler_logs_request_id(sample_tailored_cv, lambda_context):
    """Test handler logs AWS request ID for tracing."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a software engineer with Python experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with (
        patch(
            "careervp.handlers.cv_tailoring_handler._fetch_and_tailor_cv"
        ) as mock_tailor,
        patch("careervp.handlers.cv_tailoring_handler.logger") as mock_logger,
    ):
        mock_tailor.return_value = Result(
            success=True, data=sample_tailored_cv, code=ResultCode.CV_TAILORED_SUCCESS
        )

        # Act
        _response = handler(event, lambda_context)

    # Assert
    mock_logger.info.assert_called()
    assert any(
        lambda_context.aws_request_id in str(call)
        for call in mock_logger.info.call_args_list
    )


def test_handler_validates_preferences_structure(lambda_context):
    """Test handler validates preferences structure."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a software engineer with Python experience.",
                "preferences": "invalid",  # Should be object, not string
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    # Act
    response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False


def test_handler_cors_headers_present(sample_tailored_cv, lambda_context):
    """Test handler includes CORS headers in response."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a software engineer with Python experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with patch(
        "careervp.handlers.cv_tailoring_handler._fetch_and_tailor_cv"
    ) as mock_tailor:
        mock_tailor.return_value = Result(
            success=True, data=sample_tailored_cv, code=ResultCode.CV_TAILORED_SUCCESS
        )

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert "headers" in response
    assert "Access-Control-Allow-Origin" in response["headers"]


def test_handler_validation_error_details(lambda_context):
    """Test handler returns detailed validation errors."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "",  # Empty string
                "job_description": "x" * 51000,  # Too long
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    # Act
    response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False
    # Should include details about both validation errors
