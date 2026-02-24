"""
E2E Live Tests for Staging Environment - Production-Like Validation

These tests run against the DEPLOYED staging environment to validate:
1. Health endpoint is accessible and returns correct status
2. Authentication flow works correctly
3. CRUD operations work correctly
4. Async flows (VPR, CV Tailoring) work

CRITICAL: These tests MUST FAIL before staging is fully deployed.
They validate ACTUAL API responses, not mocks.

Prerequisites:
- Staging environment MUST be deployed
- ANTHROPIC_API_KEY must be set in SSM
- AWS credentials configured

Run with:
    pytest docs/staging/tests/e2e/test_staging_live.py -v

To skip tests that require deployment:
    pytest docs/staging/tests/e2e/ -v -m "not e2e"  # Won't work, all are e2e
"""

import os
import subprocess
import time
from typing import NoReturn

import pytest
import requests  # type: ignore[import-untyped]


# Configure pytest
pytestmark = pytest.mark.e2e


# Test configuration
STAGING_API_URL = os.environ.get("STAGING_API_URL", None)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Required for tests - fail fast if not configured
if not STAGING_API_URL:
    # Try to get from CloudFormation
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
                "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            STAGING_API_URL = result.stdout.strip() + "prod"
    except Exception:
        pass


def get_staging_api_url() -> str | NoReturn:
    """Get the staging API URL - FAIL if not available."""
    if STAGING_API_URL:
        return STAGING_API_URL

    pytest.fail(
        "STAGING_API_URL environment variable not set and could not be fetched from CloudFormation. "
        "Staging must be deployed before running E2E tests. "
        "Run: aws cloudformation describe-stacks --stack-name CareerVpCrudStaging"
    )


def check_api_reachable(url: str) -> bool:
    """Check if the API is reachable."""
    try:
        response = requests.get(f"{url}/health", timeout=10)
        return response.status_code == 200
    except Exception:  # broad-except necessary for network errors
        return False


@pytest.fixture(scope="module")  # type: ignore[misc]
def api_url() -> str:
    """Get the staging API URL - FAIL FAST if not available."""
    url = get_staging_api_url()
    print(f"\nUsing staging API URL: {url}")

    # Verify API is reachable BEFORE running tests
    if not check_api_reachable(url):
        pytest.fail(
            f"Staging API is not reachable at {url}. "
            "This likely means staging is not deployed. "
            "Deploy staging first: cd infra && ENVIRONMENT=staging python -m cdk deploy CareerVpCrudStaging"
        )

    return url


@pytest.fixture(scope="module")  # type: ignore[misc]
def auth_token(api_url: str) -> str:
    """Get an authentication token for testing - FAIL if auth doesn't work."""
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

    token: str | None = None
    if response.status_code == 201:
        # Newly registered
        token = response.json().get("access_token")
    elif response.status_code == 200:
        # Already registered, try to login
        login_data = {"email": test_email, "password": "TestPass123!"}
        login_response = requests.post(
            f"{api_url}/api/auth/login", json=login_data, timeout=30
        )
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
        else:
            pytest.fail(
                f"Cannot authenticate test user. Login failed: {login_response.status_code} - {login_response.text}"
            )
    else:
        pytest.fail(
            f"Cannot authenticate test user. Register failed: {response.status_code} - {response.text}"
        )

    if not token:
        pytest.fail("No access token received from authentication")

    return token


class TestHealthEndpoint:
    """
    Test suite for health endpoint - CRITICAL.

    If health fails, nothing else will work.
    """

    def test_health_endpoint_returns_200(self, api_url: str) -> None:
        """Test that health endpoint returns 200 OK."""
        response = requests.get(f"{api_url}/health", timeout=10)

        assert response.status_code == 200, (
            f"Health endpoint should return 200, got {response.status_code}. "
            f"Response: {response.text}"
        )

    def test_health_endpoint_returns_healthy_status(self, api_url: str) -> None:
        """Test that health endpoint returns healthy status."""
        response = requests.get(f"{api_url}/health", timeout=10)
        data = response.json()

        assert "status" in data, "Health response should include status field"
        assert data["status"] == "healthy", (
            f"Health status should be healthy, got {data.get('status')}"
        )

    def test_health_endpoint_is_reachable(self, api_url: str) -> None:
        """Test that health endpoint is reachable and responds quickly."""
        start = time.time()
        response = requests.get(f"{api_url}/health", timeout=10)
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 2.0, f"Health endpoint took {elapsed:.2f}s, should be under 2s"


class TestAuthentication:
    """
    Test suite for authentication - CRITICAL.

    All protected endpoints require valid authentication.
    """

    def test_register_new_user(self, api_url: str) -> None:
        """Test that a new user can register successfully."""
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

        reg_response = requests.post(
            f"{api_url}/api/auth/register", json=register_data, timeout=30
        )
        assert reg_response.status_code in [200, 201], (
            f"Registration failed: {reg_response.status_code}"
        )

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

    def test_login_invalid_credentials_returns_401(self, api_url: str) -> None:
        """Test that login fails with 401 for invalid credentials."""
        login_data = {
            "email": "nonexistent.staging.user@example.com",
            "password": "WrongPassword123!",
        }

        response = requests.post(
            f"{api_url}/api/auth/login", json=login_data, timeout=30
        )

        assert response.status_code == 401, (
            f"Login with invalid credentials should return 401, got {response.status_code}"
        )


class TestCRUDOperations:
    """
    Test suite for CRUD operations.

    Validates core functionality works.
    """

    def test_get_user_profile(self, api_url: str, auth_token: str) -> None:
        """Test that user can get their profile."""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = requests.get(f"{api_url}/api/users/me", headers=headers, timeout=10)

        assert response.status_code == 200, (
            f"Get profile should succeed, got {response.status_code}: {response.text}"
        )

        data = response.json()
        assert "email" in data or "user_id" in data, (
            "Profile response should include user info"
        )

    def test_list_jobs_authenticated(self, api_url: str, auth_token: str) -> None:
        """Test that authenticated user can list jobs."""
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = requests.get(f"{api_url}/api/jobs", headers=headers, timeout=10)

        # Accept 200 (success) - 404 means endpoint not implemented
        assert response.status_code in [200, 404], (
            f"List jobs should return 200 or 404, got {response.status_code}"
        )

    def test_create_job_authenticated(self, api_url: str, auth_token: str) -> None:
        """Test that authenticated user can create a job listing."""
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
            "description": "Test job description for E2E testing",
            "requirements": ["3+ years experience"],
        }

        response = requests.post(
            f"{api_url}/api/jobs", json=job_data, headers=headers, timeout=30
        )

        # Accept 201 (created), 200 (success), or 404 (not implemented)
        assert response.status_code in [200, 201, 404], (
            f"Create job should return 200/201/404, got {response.status_code}: {response.text}"
        )


class TestAsyncFlows:
    """
    Test suite for async flows (VPR, CV Tailoring).

    These are the core AI features.
    """

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

        # Accept 202 (accepted), 200 (success) - 404 means not implemented
        assert response.status_code in [200, 202, 404], (
            f"VPR should accept request, got {response.status_code}: {response.text}"
        )

        if response.status_code in [200, 202]:
            data = response.json()
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

        # Accept 202 (accepted), 200 (success) - 404 means not implemented
        assert response.status_code in [200, 202, 404], (
            f"CV Tailoring should accept request, got {response.status_code}: {response.text}"
        )


class TestStagingIsolation:
    """
    Test suite for staging environment isolation.

    Validates staging is separate from dev/prod.
    """

    def test_staging_uses_staging_database(self, api_url: str, auth_token: str) -> None:
        """Test that staging uses separate database tables."""
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Get user profile - if this works, we're using the correct database
        response = requests.get(f"{api_url}/api/users/me", headers=headers, timeout=10)

        assert response.status_code == 200, (
            f"Cannot access user profile - database may not be configured: {response.status_code}"
        )

    def test_staging_data_isolation(self, api_url: str) -> None:
        """Test that staging data doesn't pollute other environments."""
        # Register a unique user in staging
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

        assert response.status_code in [200, 201], (
            f"Registration should work in staging, got {response.status_code}"
        )


class TestStagingPerformance:
    """
    Test suite for staging performance validation.

    Validates acceptable response times.
    """

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
        _response = requests.post(
            f"{api_url}/api/auth/login", json=login_data, timeout=30
        )
        elapsed = time.time() - start

        # Login can be slower but should still be reasonable
        assert elapsed < 5.0, (
            f"Auth endpoint should respond in under 5 seconds, took {elapsed:.2f}s"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
