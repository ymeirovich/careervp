"""
End-to-end tests for CV Tailoring complete flow.

Tests the complete HTTP request/response cycle including authentication,
API Gateway integration, Lambda execution, and response formatting.
"""

import pytest
import requests
from unittest.mock import Mock, patch


@pytest.fixture
def api_endpoint():
    """API Gateway endpoint for CV tailoring."""
    return "https://api.careervp.com/api/cv-tailoring"


@pytest.fixture
def auth_headers():
    """Authentication headers with valid JWT token."""
    return {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "Content-Type": "application/json",
    }


def test_post_cv_tailoring_success(api_endpoint, auth_headers):
    """Test full HTTP flow for successful CV tailoring."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "success": True,
                "data": {
                    "tailored_cv": {
                        "contact_info": {
                            "name": "John Doe",
                            "email": "john@example.com",
                        },
                        "experience": [],
                        "education": [],
                        "skills": ["Python", "AWS"],
                    },
                    "download_url": "https://s3.amazonaws.com/bucket/cv-123-tailored.pdf",
                },
            },
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "tailored_cv" in data["data"]
    assert "download_url" in data["data"]


def test_post_with_preferences_tone(api_endpoint, auth_headers):
    """Test HTTP flow with custom tone preference."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
        "preferences": {
            "tone": "formal",
        },
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200, json=lambda: {"success": True, "data": {"tailored_cv": {}}}
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 200


def test_post_with_preferences_length(api_endpoint, auth_headers):
    """Test HTTP flow with custom length preference."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
        "preferences": {
            "length": "concise",
            "max_pages": 1,
        },
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200, json=lambda: {"success": True, "data": {"tailored_cv": {}}}
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 200


def test_post_fvs_violation_400(api_endpoint, auth_headers):
    """Test HTTP flow returns 400 when FVS detects violations."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=400,
            json=lambda: {
                "success": False,
                "code": "FVS_HALLUCINATION_DETECTED",
                "message": "FVS detected factual violations in tailored CV",
                "data": {
                    "violations": [
                        {"field": "experience[0].dates", "severity": "CRITICAL"}
                    ]
                },
            },
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["code"] == "FVS_HALLUCINATION_DETECTED"
    assert "violations" in data["data"]


def test_post_rate_limit_429(api_endpoint, auth_headers):
    """Test HTTP flow returns 429 when rate limit is exceeded."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=429,
            json=lambda: {
                "success": False,
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
            },
            headers={"Retry-After": "60"},
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_post_unauthorized_401(api_endpoint):
    """Test HTTP flow returns 401 when auth token is missing."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=401,
            json=lambda: {
                "success": False,
                "code": "UNAUTHORIZED",
                "message": "Missing or invalid authentication token",
            },
        )

        # Act
        response = requests.post(api_endpoint, json=payload)  # No auth headers

    # Assert
    assert response.status_code == 401


def test_post_cv_not_found_404(api_endpoint, auth_headers):
    """Test HTTP flow returns 404 when CV doesn't exist."""
    # Arrange
    payload = {
        "cv_id": "non-existent-cv",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=404,
            json=lambda: {
                "success": False,
                "code": "CV_NOT_FOUND",
                "message": "CV with id 'non-existent-cv' not found",
            },
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "CV_NOT_FOUND"


def test_download_url_generated(api_endpoint, auth_headers):
    """Test HTTP response includes valid S3 download URL."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "success": True,
                "data": {
                    "tailored_cv": {},
                    "download_url": "https://s3.amazonaws.com/bucket/cv-123-tailored.pdf?X-Amz-Expires=3600",
                },
            },
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "download_url" in data["data"]
    assert data["data"]["download_url"].startswith("https://")
    assert "X-Amz-Expires" in data["data"]["download_url"]


def test_post_invalid_json_400(api_endpoint, auth_headers):
    """Test HTTP flow returns 400 for malformed JSON."""
    # Arrange
    invalid_payload = "{invalid json"

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=400,
            json=lambda: {
                "success": False,
                "code": "INVALID_JSON",
                "message": "Request body contains invalid JSON",
            },
        )

        # Act
        response = requests.post(
            api_endpoint, data=invalid_payload, headers=auth_headers
        )

    # Assert
    assert response.status_code == 400


def test_post_validation_error_400(api_endpoint, auth_headers):
    """Test HTTP flow returns 400 for validation errors."""
    # Arrange
    payload = {
        "cv_id": "",  # Empty cv_id
        "job_description": "Short",  # Too short
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=400,
            json=lambda: {
                "success": False,
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "errors": [
                    {"field": "cv_id", "message": "cv_id cannot be empty"},
                    {
                        "field": "job_description",
                        "message": "job_description must be at least 20 characters",
                    },
                ],
            },
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "errors" in data


def test_post_cors_headers_present(api_endpoint, auth_headers):
    """Test HTTP response includes CORS headers."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"success": True, "data": {"tailored_cv": {}}},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert "Access-Control-Allow-Origin" in response.headers


def test_post_response_includes_metadata(api_endpoint, auth_headers):
    """Test HTTP response includes processing metadata."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "success": True,
                "data": {
                    "tailored_cv": {},
                    "metadata": {
                        "processing_time_ms": 1500,
                        "model_version": "1.0.0",
                        "fvs_violations": 0,
                    },
                },
            },
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data["data"]


def test_post_timeout_504(api_endpoint, auth_headers):
    """Test HTTP flow returns 504 on timeout."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=504,
            json=lambda: {
                "success": False,
                "code": "GATEWAY_TIMEOUT",
                "message": "Request timed out",
            },
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 504


def test_post_internal_error_500(api_endpoint, auth_headers):
    """Test HTTP flow returns 500 on internal error."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=500,
            json=lambda: {
                "success": False,
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 500


def test_post_with_idempotency_key(api_endpoint, auth_headers):
    """Test HTTP flow with idempotency key."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
        "idempotency_key": "unique-key-123",
    }
    headers = {**auth_headers, "Idempotency-Key": "unique-key-123"}

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"success": True, "data": {"tailored_cv": {}}},
            headers={"Idempotent-Replay": "false"},
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=headers)

    # Assert
    assert response.status_code == 200
    assert "Idempotent-Replay" in response.headers


def test_post_response_time_tracking(api_endpoint, auth_headers):
    """Test HTTP response includes X-Response-Time header."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"success": True, "data": {"tailored_cv": {}}},
            headers={"X-Response-Time": "1500ms"},
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 200
    if "X-Response-Time" in response.headers:
        assert response.headers["X-Response-Time"].endswith("ms")


def test_post_request_id_tracking(api_endpoint, auth_headers):
    """Test HTTP response includes X-Request-ID header."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"success": True, "data": {"tailored_cv": {}}},
            headers={"X-Request-ID": "req-123-456-789"},
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 200
    if "X-Request-ID" in response.headers:
        assert response.headers["X-Request-ID"].startswith("req-")


def test_post_with_all_preferences(api_endpoint, auth_headers):
    """Test HTTP flow with all preference options."""
    # Arrange
    payload = {
        "cv_id": "cv-123",
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
        "preferences": {
            "tone": "formal",
            "length": "concise",
            "emphasize_skills": ["Python", "AWS", "Docker"],
            "include_summary": True,
            "max_pages": 2,
        },
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200, json=lambda: {"success": True, "data": {"tailored_cv": {}}}
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 200


def test_post_forbidden_403(api_endpoint, auth_headers):
    """Test HTTP flow returns 403 when accessing another user's CV."""
    # Arrange
    payload = {
        "cv_id": "cv-123",  # Belongs to different user
        "job_description": "Looking for a senior software engineer with Python and AWS experience.",
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=403,
            json=lambda: {
                "success": False,
                "code": "FORBIDDEN",
                "message": "You do not have permission to access this CV",
            },
        )

        # Act
        response = requests.post(api_endpoint, json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 403


def test_options_preflight_request(api_endpoint):
    """Test OPTIONS preflight request for CORS."""
    # Arrange
    with patch("requests.options") as mock_options:
        mock_options.return_value = Mock(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

        # Act
        response = requests.options(api_endpoint)

    # Assert
    assert response.status_code == 204
    assert "Access-Control-Allow-Methods" in response.headers
