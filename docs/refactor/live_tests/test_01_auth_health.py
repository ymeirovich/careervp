# Live Tests - Health and Auth Endpoints
# Tests: GET /health, POST /auth/register, POST /auth/login, POST /auth/refresh

import os
import json
import pytest
import requests
from typing import Dict, Any

# Import configuration
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from conftest import (
    API_BASE,
    TEST_USER_ID,
    load_test_ids,
    save_test_ids,
)

# Test data storage for cross-test dependencies
test_data: Dict[str, Any] = {
    "user_id": TEST_USER_ID,
    "tokens": {},
    "cv_id": None,
    "job_id": None,
    "vpr_id": None,
    "gap_response_ids": [],
    "company_research_id": None,
    "cover_letter_id": None,
    "interview_prep_id": None,
}

# Load test IDs from .env file if exists (for cross-run persistence)
_saved_ids = load_test_ids()
for key in [
    "cv_id",
    "job_id",
    "vpr_id",
    "gap_response_ids",
    "company_research_id",
    "cover_letter_id",
    "interview_prep_id",
    "user_id",
]:
    if key in _saved_ids and _saved_ids[key]:
        test_data[key] = _saved_ids[key]

# Ensure TEST_USER_ID is set
if not test_data.get("user_id"):
    test_data["user_id"] = TEST_USER_ID


def print_response(test_name: str, endpoint: str, status_code: int, response_data: Any):
    """Print JSON response for documentation."""
    output = {
        "test_name": test_name,
        "endpoint": endpoint,
        "status_code": status_code,
        "response": response_data,
    }
    print(f"\n=== RESPONSE {test_name} ===")
    print(json.dumps(output, indent=2, default=str))


class TestHealthEndpoint:
    """Test GET /health endpoint."""

    def test_health_check(self):
        """Test health check returns healthy status."""
        url = f"{API_BASE}/health"

        response = requests.get(url, timeout=10)

        # Print response
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response("test_health_check", "GET /health", response.status_code, data)

        # Accept 200 (success) or 404 (not deployed)
        if response.status_code == 404:
            print("⚠ GET /health - Endpoint not deployed (404)")
            pytest.skip("Health endpoint not deployed in current stage")
        elif response.status_code != 200:
            print(f"⚠ GET /health - Status {response.status_code}")

        assert response.status_code == 200, (
            f"Health check failed: {response.status_code}"
        )

        data = response.json()
        assert "status" in data, "Response missing 'status' field"
        assert data["status"] in ["healthy", "degraded", "unhealthy"], (
            f"Invalid health status: {data.get('status')}"
        )

        print(f"✓ GET /health - Status: {data.get('status')}")


class TestAuthEndpoints:
    """Test authentication endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data."""
        self.base_url = API_BASE

    def test_auth_register(self):
        """Test user registration."""
        url = f"{self.base_url}/auth/register"

        # Generate unique email for test
        import time

        test_email = f"test_{int(time.time())}@example.com"

        payload = {"email": test_email, "password": "Test1234!", "name": "Test User"}

        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        # Print response
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_auth_register", "POST /auth/register", response.status_code, data
        )

        # Accept 201 (created) or 200 (success)
        assert response.status_code in [200, 201], (
            f"Registration failed: {response.status_code} - {response.text}"
        )

        if "access_token" in data:
            test_data["tokens"]["access"] = data["access_token"]
            test_data["tokens"]["refresh"] = data.get("refresh_token")
            test_data["user_email"] = test_email
            save_test_ids(test_data)

        print(f"✓ POST /auth/register - Email: {test_email}")

    def test_auth_login(self):
        """Test user login."""
        url = f"{self.base_url}/auth/login"

        # Use test user credentials
        payload = {
            "email": os.environ.get("TEST_EMAIL", "testuser123@example.com"),
            "password": os.environ.get("TEST_PASSWORD", "TestPass123!"),
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        # Print response
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_auth_login", "POST /auth/login", response.status_code, data
        )

        # Accept 200 (success) or 401 (invalid credentials)
        assert response.status_code == 200, (
            f"Login failed: {response.status_code} - {response.text}"
        )

        data = response.json()
        assert "access_token" in data, "Response missing access_token"
        test_data["tokens"]["access"] = data["access_token"]
        test_data["tokens"]["refresh"] = data.get("refresh_token")
        save_test_ids(test_data)
        print("✓ POST /auth/login - Logged in successfully")

    def test_auth_refresh(self):
        """Test token refresh."""
        url = f"{self.base_url}/auth/refresh"

        # Get fresh token via login first to ensure we have valid refresh token

        # Perform fresh login to get valid tokens
        login_url = f"{self.base_url}/auth/login"
        login_payload = {
            "email": os.environ.get("TEST_EMAIL", "testuser123@example.com"),
            "password": os.environ.get("TEST_PASSWORD", "TestPass123!"),
        }
        login_response = requests.post(
            login_url,
            json=login_payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if login_response.status_code != 200:
            pytest.skip(
                f"Cannot get fresh tokens for refresh test: {login_response.status_code}"
            )

        login_data = login_response.json()
        refresh_token_value = login_data.get("refresh_token")

        if not refresh_token_value:
            pytest.skip("No refresh token available")

        # Send refresh token in Authorization header (Bearer token)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {refresh_token_value}",
        }

        response = requests.post(url, headers=headers, timeout=10)

        # Print response
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_auth_refresh", "POST /auth/refresh", response.status_code, data
        )

        assert response.status_code == 200, (
            f"Token refresh failed: {response.status_code} - {response.text}"
        )

        data = response.json()
        assert "access_token" in data, "Response missing access_token"

        print("✓ POST /auth/refresh - Token refreshed")


# Export test data for cross-test dependencies
def get_test_data() -> Dict[str, Any]:
    """Get shared test data."""
    return test_data


def update_test_data(key: str, value: Any):
    """Update shared test data and persist to .env file."""
    test_data[key] = value
    # Persist to .env file for cross-run continuity
    save_test_ids(test_data)
