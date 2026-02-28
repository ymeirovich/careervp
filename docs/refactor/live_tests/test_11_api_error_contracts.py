# Live Tests - API Error Contracts and New/Updated Routes
# Incorporates docs/beta/docs_gaps/api_error_codes.md scenarios.

import json
import os
import time
from typing import Any

import pytest
import requests

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .conftest import API_BASE, TEST_EMAIL, get_auth_headers
from .test_01_auth_health import test_data


def print_response(test_name: str, endpoint: str, status_code: int, response_data: Any):
    output = {
        "test_name": test_name,
        "endpoint": endpoint,
        "status_code": status_code,
        "response": response_data,
    }
    print(f"\n=== RESPONSE {test_name} ===")
    print(json.dumps(output, indent=2, default=str))


def _json_or_text(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        return {"value": payload}
    except Exception:
        return {"raw_text": response.text}


def _has_error_shape(payload: dict[str, Any]) -> bool:
    return "error" in payload or "message" in payload


class TestAPIErrorContracts:
    """Negative-path validation for error behavior and updated resources."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.base_url = API_BASE

    def test_auth_login_invalid_credentials_returns_401(self):
        """api_error_codes.md: AUTH_INVALID_CREDENTIALS (401)."""
        url = f"{self.base_url}/auth/login"
        payload = {"email": TEST_EMAIL, "password": "wrong-password"}
        response = requests.post(
            url, json=payload, headers={"Content-Type": "application/json"}, timeout=20
        )
        data = _json_or_text(response)
        print_response(
            "test_auth_login_invalid_credentials_returns_401",
            "POST /auth/login",
            response.status_code,
            data,
        )

        assert response.status_code == 401
        assert _has_error_shape(data)

    def test_users_me_missing_token_returns_401(self):
        """api_error_codes.md: AUTH_MISSING_TOKEN (401)."""
        url = f"{self.base_url}/users/me"
        response = requests.get(
            url, headers={"Content-Type": "application/json"}, timeout=20
        )
        data = _json_or_text(response)
        print_response(
            "test_users_me_missing_token_returns_401",
            "GET /users/me",
            response.status_code,
            data,
        )

        assert response.status_code == 401
        assert _has_error_shape(data)

    def test_users_me_usage_missing_token_returns_401(self):
        """New/updated route: GET /users/me/usage auth enforcement."""
        url = f"{self.base_url}/users/me/usage"
        response = requests.get(
            url, headers={"Content-Type": "application/json"}, timeout=20
        )
        data = _json_or_text(response)
        print_response(
            "test_users_me_usage_missing_token_returns_401",
            "GET /users/me/usage",
            response.status_code,
            data,
        )

        assert response.status_code == 401
        assert _has_error_shape(data)

    @pytest.mark.requires_auth
    def test_users_me_usage_authenticated_returns_trial_shape(self):
        """New/updated route: GET /users/me/usage returns usage structure."""
        url = f"{self.base_url}/users/me/usage"
        response = requests.get(url, headers=get_auth_headers(), timeout=20)
        data = _json_or_text(response)
        print_response(
            "test_users_me_usage_authenticated_returns_trial_shape",
            "GET /users/me/usage",
            response.status_code,
            data,
        )

        assert response.status_code == 200
        assert "trial" in data
        assert "applications" in data

    def test_jobs_create_invalid_payload_returns_400_or_422(self):
        """api_error_codes.md: VALIDATION_REQUIRED_FIELD / INVALID_FORMAT."""
        url = f"{self.base_url}/jobs"
        payload = {"title": "", "company_name": "", "description": ""}
        response = requests.post(
            url, json=payload, headers=get_auth_headers(), timeout=20
        )
        data = _json_or_text(response)
        print_response(
            "test_jobs_create_invalid_payload_returns_400_or_422",
            "POST /jobs",
            response.status_code,
            data,
        )

        assert response.status_code in (400, 422)
        assert _has_error_shape(data)

    @pytest.mark.requires_auth
    def test_jobs_get_not_found_returns_404(self):
        """api_error_codes.md: JOB_NOT_FOUND (404)."""
        fake_job_id = f"job-not-found-{int(time.time())}"
        url = f"{self.base_url}/jobs/{fake_job_id}"
        response = requests.get(url, headers=get_auth_headers(), timeout=20)
        data = _json_or_text(response)
        print_response(
            "test_jobs_get_not_found_returns_404",
            "GET /jobs/{job_id}",
            response.status_code,
            data,
        )

        assert response.status_code in (403, 404)
        assert _has_error_shape(data)

    def test_applications_recovery_missing_token_returns_401(self):
        """New route: GET /applications/{application_id} auth enforcement."""
        fake_application_id = f"app-{int(time.time())}"
        url = f"{self.base_url}/applications/{fake_application_id}"
        response = requests.get(
            url, headers={"Content-Type": "application/json"}, timeout=20
        )
        data = _json_or_text(response)
        print_response(
            "test_applications_recovery_missing_token_returns_401",
            "GET /applications/{application_id}",
            response.status_code,
            data,
        )

        assert response.status_code == 401
        assert _has_error_shape(data)

    @pytest.mark.requires_auth
    def test_applications_recovery_not_found_returns_404(self):
        """New route: GET /applications/{application_id} not-found behavior."""
        fake_application_id = f"app-not-found-{int(time.time())}"
        url = f"{self.base_url}/applications/{fake_application_id}"
        response = requests.get(url, headers=get_auth_headers(), timeout=20)
        data = _json_or_text(response)
        print_response(
            "test_applications_recovery_not_found_returns_404",
            "GET /applications/{application_id}",
            response.status_code,
            data,
        )

        assert response.status_code in (403, 404)
        assert _has_error_shape(data)

    def test_auth_refresh_invalid_token_returns_401(self):
        """api_error_codes.md: AUTH_TOKEN_INVALID (401)."""
        url = f"{self.base_url}/auth/refresh"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer not-a-valid-refresh-token",
        }
        response = requests.post(url, headers=headers, timeout=20)
        data = _json_or_text(response)
        print_response(
            "test_auth_refresh_invalid_token_returns_401",
            "POST /auth/refresh",
            response.status_code,
            data,
        )

        assert response.status_code == 401
        assert _has_error_shape(data)


def get_test_data() -> dict[str, Any]:
    return test_data
