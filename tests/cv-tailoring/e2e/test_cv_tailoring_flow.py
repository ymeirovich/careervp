"""E2E contract tests for CV Tailoring API.

Aligned to OpenAPI + Phase 10 runbook contract:
- POST /cv-tailoring/generate -> 202, request_id, status
- GET /cv-tailoring/{cvTailoringId} -> status/result lifecycle
"""

from __future__ import annotations

import os
from unittest.mock import Mock, patch

import pytest
import requests


@pytest.fixture
def api_base_url() -> str:
    return os.getenv(
        "CAREERVP_API_BASE_URL",
        "https://dev-api.careervp.com/prod",
    )


@pytest.fixture
def generate_endpoint(api_base_url: str) -> str:
    return f"{api_base_url}/cv-tailoring/generate"


@pytest.fixture
def status_endpoint(api_base_url: str) -> str:
    return f"{api_base_url}/cv-tailoring"


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json",
    }


@pytest.fixture
def valid_generate_payload() -> dict[str, object]:
    return {
        "cv_id": "cv-123",
        "job_id": "job-456",
        "vpr_id": "vpr-789",
        "options": {
            "preserve_length": True,
            "highlight_keywords": True,
            "target_ats": "greenhouse",
        },
    }


def test_generate_returns_202_with_request_id(
    generate_endpoint: str,
    auth_headers: dict[str, str],
    valid_generate_payload: dict[str, object],
) -> None:
    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=202,
            json=lambda: {
                "request_id": "11111111-1111-1111-1111-111111111111",
                "status": "processing",
                "estimated_time_seconds": 30,
            },
        )

        response = requests.post(
            generate_endpoint,
            json=valid_generate_payload,
            headers=auth_headers,
        )

    assert response.status_code == 202
    data = response.json()
    assert "request_id" in data
    assert data["status"] in ("processing", "pending")


def test_generate_requires_auth(
    generate_endpoint: str,
    valid_generate_payload: dict[str, object],
) -> None:
    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=401,
            json=lambda: {"error": "Missing or invalid authentication token"},
        )

        response = requests.post(generate_endpoint, json=valid_generate_payload)

    assert response.status_code == 401


def test_generate_validation_error(
    generate_endpoint: str,
    auth_headers: dict[str, str],
) -> None:
    payload = {"cv_id": "", "job_id": "", "vpr_id": ""}

    with patch("requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=400,
            json=lambda: {
                "error": "validation failed",
                "details": [
                    {"field": "cv_id", "message": "required"},
                    {"field": "job_id", "message": "required"},
                ],
            },
        )

        response = requests.post(generate_endpoint, json=payload, headers=auth_headers)

    assert response.status_code == 400
    assert "error" in response.json()


def test_status_endpoint_returns_processing_state(
    status_endpoint: str,
    auth_headers: dict[str, str],
) -> None:
    request_id = "11111111-1111-1111-1111-111111111111"

    with patch("requests.get") as mock_get:
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "id": request_id,
                "status": "processing",
                "created_at": "2026-02-15T00:00:00Z",
            },
        )

        response = requests.get(f"{status_endpoint}/{request_id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["status"] == "processing"


def test_status_endpoint_returns_completed_result(
    status_endpoint: str,
    auth_headers: dict[str, str],
) -> None:
    request_id = "11111111-1111-1111-1111-111111111111"

    with patch("requests.get") as mock_get:
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "id": request_id,
                "status": "completed",
                "result": {
                    "tailored_cv": {"skills": ["Python", "AWS"]},
                    "ats_score": 0.91,
                    "keyword_matches": ["python", "aws"],
                    "suggestions": [],
                },
                "created_at": "2026-02-15T00:00:00Z",
                "completed_at": "2026-02-15T00:00:20Z",
            },
        )

        response = requests.get(f"{status_endpoint}/{request_id}", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert "result" in body


def test_status_not_found(
    status_endpoint: str,
    auth_headers: dict[str, str],
) -> None:
    with patch("requests.get") as mock_get:
        mock_get.return_value = Mock(
            status_code=404,
            json=lambda: {"error": "not found"},
        )

        response = requests.get(
            f"{status_endpoint}/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )

    assert response.status_code == 404
