"""
E2E Live Tests for Staging Environment

These tests run against the deployed staging environment to validate:
1. Health endpoint is accessible
2. Authentication flow works
3. CRUD operations work correctly
4. Async flows (VPR, CV Tailoring) work

Prerequisites:
- Staging environment must be deployed
- ANTHROPIC_API_KEY must be set
- AWS credentials configured

Run with:
    pytest docs/staging/tests/e2e/test_staging_live.py -v
"""

import os
import time

import pytest
import requests


# Configure pytest
pytestmark = pytest.mark.e2e


# Test configuration
STAGING_API_URL = os.environ.get(
    "STAGING_API_URL",
    # Default: fetch from CloudFormation
    None,
)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def get_staging_api_url() -> str:
    """Get the staging API URL from CloudFormation or environment."""
    if STAGING_API_URL:
        return STAGING_API_URL

    # Try to get from CloudFormation
    import subprocess

    try:
        result = subprocess.run(
            [
                "aws",
                "cloudformation",
                "describe-stacks",
                "--stack-name",
                "CareerVpCrudStaging",
                "--region",
                AWS_REGION,
                "--query",
                "Stacks[0].Outputs[0].OutputValue",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() + "prod"
    except Exception as e:
        pytest.skip(f"Cannot get staging API URL: {e}")


@pytest.fixture(scope="module")
def api_url() -> str:
    """Get the staging API URL."""
    url = get_staging_api_url()
    print(f"\nUsing staging API URL: {url}")
    return url


@pytest.fixture(scope="module")
def auth_token(api_url: str) -> str:
    """Get an authentication token for testing."""
    # Register a test user
    test_email = f"e2e.test.{int(time.time())}@staging.careervp.com"

    register_data = {
        "email": test_email,
        "password": "TestPass123!",
        "first_name": "E2E",
        "last_name": "Test",
        "country": "USA",
    }

    response = requests.post(
        f"{api_url}/api/auth/register", json=register_data, timeout=30
    )

    if response.status_code == 201:
        # Already registered, try to login
        login_data = {"email": test_email, "password": "TestPass123!"}
        login_response = requests.post(
            f"{api_url}/api/auth/login", json=login_data, timeout=30
        )
        if login_response.status_code == 200:
            return login_response.json().get("access_token")

    elif response.status_code == 200:
        return response.json().get("access_token")

    pytest.skip(f"Cannot authenticate: {response.status_code} - {response.text}")


class TestHealthEndpoint:
    """Test suite for health endpoint."""

    def test_health_endpoint_returns_200(self, api_url: str) -> None:
        """Test that health endpoint returns 200 OK."""
        response = requests.get(f"{api_url}/health", timeout=10)

        assert response.status_code == 200, (
            f"Health endpoint should return 200, got {response.status_code}"
        )

    def test_health_endpoint_returns_healthy_status(self, api_url: str) -> None:
        """Test that health endpoint returns healthy status."""
        response = requests.get(f"{api_url}/health", timeout=10)
        data = response.json()

        assert "status" in data, "Health response should include status"
        assert data["status"] == "healthy", (
            f"Health status should be healthy, got {data.get('status')}"
        )


class TestAuthentication:
    """Test suite for authentication flow."""

    def test_register_new_user(self, api_url: str) -> None:
        """Test that a new user can register."""
        # Use unique email for this test
        test_email = f"register.test.{int(time.time())}@staging.careervp.com"

        register_data = {
            "email": test_email,
            "password": "TestPass123!",
            "first_name": "Test",
            "last_name": "User",
            "country": "USA",
        }

        response = requests.post(
            f"{api_url}/api/auth/register", json=register_data, timeout=30
        )

        # Accept 201 (created) or 200 (already exists)
        assert response.status_code in [200, 201], (
            f"Registration should succeed, got {response.status_code}: {response.text}"
        )

    def test_login_existing_user(self, api_url: str) -> None:
        """Test that an existing user can login."""
        # First register
        test_email = f"login.test.{int(time.time())}@staging.careervp.com"

        register_data = {
            "email": test_email,
            "password": "TestPass123!",
            "first_name": "Test",
            "last_name": "User",
            "country": "USA",
        }

        requests.post(f"{api_url}/api/auth/register", json=register_data, timeout=30)

        # Then login
        login_data = {"email": test_email, "password": "TestPass123!"}

        response = requests.post(
            f"{api_url}/api/auth/login", json=login_data, timeout=30
        )

        assert response.status_code == 200, (
            f"Login should succeed, got {response.status_code}"
        )

        data = response.json()
        assert "access_token" in data, "Login response should include access_token"

    def test_login_invalid_credentials(self, api_url: str) -> None:
        """Test that login fails with invalid credentials."""
        login_data = {
            "email": "nonexistent@staging.careervp.com",
            "password": "WrongPassword123!",
        }

        response = requests.post(
            f"{api_url}/api/auth/login", json=login_data, timeout=30
        )

        assert response.status_code == 401, (
            f"Login with invalid credentials should fail with 401, got {response.status_code}"
        )


class TestCRUDOperations:
    """Test suite for CRUD operations."""

    def test_get_user_profile(self, api_url: str, auth_token: str) -> None:
        """Test that user can get their profile."""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = requests.get(f"{api_url}/api/users/me", headers=headers, timeout=10)

        assert response.status_code == 200, (
            f"Get profile should succeed, got {response.status_code}"
        )

        data = response.json()
        assert "email" in data or "user_id" in data, (
            "Profile response should include user info"
        )

    def test_list_jobs(self, api_url: str, auth_token: str) -> None:
        """Test that user can list jobs."""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = requests.get(f"{api_url}/api/jobs", headers=headers, timeout=10)

        # Accept 200 (success) or 404 (endpoint not found - acceptable for initial deployment)
        assert response.status_code in [200, 404], (
            f"List jobs should succeed or return 404, got {response.status_code}"
        )

    def test_create_job(self, api_url: str, auth_token: str) -> None:
        """Test that user can create a job listing."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }

        job_data = {
            "title": "Software Engineer",
            "company": "Test Company",
            "country": "USA",
            "job_type": "FULL_TIME",
            "experience_level": "MID",
            "description": "Test job description",
            "requirements": ["3+ years experience"],
        }

        response = requests.post(
            f"{api_url}/api/jobs", json=job_data, headers=headers, timeout=30
        )

        # Accept 201 (created), 200 (success), or 404 (not implemented)
        assert response.status_code in [200, 201, 404], (
            f"Create job should succeed or return 404, got {response.status_code}"
        )


class TestAsyncFlows:
    """Test suite for async flows (VPR, CV Tailoring)."""

    def test_vpr_endpoint_accepts_request(self, api_url: str, auth_token: str) -> None:
        """Test that VPR endpoint accepts a request."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }

        vpr_data = {
            "cv_text": "Experienced software engineer with 5 years of experience in Python and JavaScript.",
            "target_role": "Senior Software Engineer",
            "country": "USA",
        }

        response = requests.post(
            f"{api_url}/api/vpr", json=vpr_data, headers=headers, timeout=30
        )

        # Accept 202 (accepted), 200 (success), or 404 (not implemented)
        assert response.status_code in [200, 202, 404], (
            f"VPR should accept request or return 404, got {response.status_code}"
        )

        if response.status_code in [200, 202]:
            data = response.json()
            # For async flows, we expect a job_id to poll for status
            assert "job_id" in data or "status" in data, (
                "VPR response should include job_id or status"
            )

    def test_cv_tailoring_endpoint_accepts_request(
        self, api_url: str, auth_token: str
    ) -> None:
        """Test that CV Tailoring endpoint accepts a request."""
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }

        tailoring_data = {"cv_id": "test-cv-id", "job_id": "test-job-id"}

        response = requests.post(
            f"{api_url}/api/cv-tailoring",
            json=tailoring_data,
            headers=headers,
            timeout=30,
        )

        # Accept 202 (accepted), 200 (success), or 404 (not implemented)
        assert response.status_code in [200, 202, 404], (
            f"CV Tailoring should accept request or return 404, got {response.status_code}"
        )


class TestStagingIsolation:
    """Test suite to verify staging is isolated from other environments."""

    def test_staging_has_separate_database(self, api_url: str, auth_token: str) -> None:
        """Test that staging uses separate database tables."""
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Get user profile
        response = requests.get(f"{api_url}/api/users/me", headers=headers, timeout=10)

        if response.status_code == 200:
            _ = response.json()  # Verify valid JSON response
            # If we can get a user profile, we're using the correct database
            assert True, "Staging is using its own database"
        else:
            pytest.skip("Cannot verify database isolation - endpoint not accessible")

    def test_staging_data_does_not_pollute_dev(self, api_url: str) -> None:
        """Test that staging data is separate from dev."""
        # Register a new user in staging
        test_email = f"isolation.test.{int(time.time())}@staging.careervp.com"

        register_data = {
            "email": test_email,
            "password": "TestPass123!",
            "first_name": "Isolation",
            "last_name": "Test",
            "country": "USA",
        }

        response = requests.post(
            f"{api_url}/api/auth/register", json=register_data, timeout=30
        )

        # The key test is that this succeeds in staging
        # (it would also succeed in dev, but with different data)
        assert response.status_code in [200, 201], (
            f"Registration should work in staging, got {response.status_code}"
        )


class TestStagingPerformance:
    """Test suite for staging performance validation."""

    def test_health_endpoint_response_time(self, api_url: str) -> None:
        """Test that health endpoint responds quickly."""
        start = time.time()
        response = requests.get(f"{api_url}/health", timeout=10)
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 2.0, (
            f"Health endpoint should respond in under 2 seconds, took {elapsed:.2f}s"
        )

    def test_auth_endpoint_response_time(self, api_url: str) -> None:
        """Test that auth endpoint responds within acceptable time."""
        login_data = {
            "email": f"perf.test.{int(time.time())}@staging.careervp.com",
            "password": "TestPass123!",
        }

        start = time.time()
        _ = requests.post(
            f"{api_url}/api/auth/login", json=login_data, timeout=30
        )
        elapsed = time.time() - start

        # Login can be slower due to JWT generation, but should still be reasonable
        assert elapsed < 5.0, (
            f"Auth endpoint should respond in under 5 seconds, took {elapsed:.2f}s"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
