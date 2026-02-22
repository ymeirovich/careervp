# Live Tests Configuration
# This file contains shared configuration and fixtures for live tests

import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timedelta

# Add scripts directory to path for resolve_api_base
# Go up 2 levels: conftest.py -> live_tests -> refactor, then into refactor3/scripts
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "refactor3" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from resolve_api_base import resolve_api_base

# Resolve API_BASE using single-source resolver
# Resolution order: ENV API_BASE -> CloudFormation stack output -> fail
API_BASE = resolve_api_base()
TEST_USER_ID = os.environ.get("TEST_USER_ID", "test-user-e2e")
USE_AUTH = os.environ.get("USE_AUTH", "true").lower() == "true"
API_KEY = os.environ.get("API_KEY", "")

# Test credentials - used to generate fresh tokens at runtime
TEST_EMAIL = os.environ.get("TEST_EMAIL", "testuser123@example.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "TestPass123!")

# Path to .env file for persisting test IDs across runs
ENV_FILE_PATH = Path(__file__).parent / ".env.json"

# Token storage - populated at runtime via login
_token_cache: Dict[str, Any] = {
    "access_token": None,
    "refresh_token": None,
    "expires_at": None,
    "token_type": None,
}


def load_test_ids() -> Dict[str, Any]:
    """Load test IDs from .env.json file if it exists."""
    if ENV_FILE_PATH.exists():
        try:
            with open(ENV_FILE_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_test_ids(test_ids: Dict[str, Any]) -> None:
    """Save test IDs to .env.json file for cross-run persistence."""
    # Load existing to preserve any fields we don't track
    existing = load_test_ids()
    existing.update(test_ids)
    try:
        with open(ENV_FILE_PATH, "w") as f:
            json.dump(existing, f, indent=2, default=str)
    except IOError as e:
        print(f"Warning: Could not save test IDs to {ENV_FILE_PATH}: {e}")


# Sample data paths - use absolute paths from docs folder
# live_tests is in docs/refactor/live_tests, so go up 2 levels to docs, then into features
DOCS_ROOT = Path(__file__).parent.parent  # refactor
SAMPLE_CV_PATH = (
    DOCS_ROOT.parent
    / "features"
    / "02_Yitzchak_Meirovich_Learning_Experience_Specialist_SysAid.docx"
)
SAMPLE_JOB_PATH = DOCS_ROOT.parent / "features" / "Sysaid Job Description.txt"
COMPANY_URL = "https://www.sysaid.com"

# Payloads directory
PAYLOADS_DIR = DOCS_ROOT / "payloads"


def _is_token_valid() -> bool:
    """Check if the cached token is still valid."""
    if not _token_cache.get("access_token"):
        return False
    if not _token_cache.get("expires_at"):
        return True  # No expiry info, assume valid
    return datetime.now() < _token_cache["expires_at"]


def login_and_get_token() -> Dict[str, Any]:
    """Generate fresh token via login request.

    Returns:
        Dict with access_token, refresh_token, expires_in, token_type

    Raises:
        RuntimeError: If login fails
    """
    url = f"{API_BASE}/auth/login"
    payload = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(f"Login failed: {response.status_code} - {response.text}")

    data = response.json()

    # Cache the tokens
    _token_cache["access_token"] = data.get("access_token")
    _token_cache["refresh_token"] = data.get("refresh_token")
    _token_cache["token_type"] = data.get("token_type", "Bearer")

    # Calculate expiry
    expires_in = data.get("expires_in", 3600)
    _token_cache["expires_at"] = datetime.now() + timedelta(
        seconds=expires_in - 60
    )  # 60s buffer

    return {
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "expires_in": expires_in,
        "token_type": data.get("token_type", "Bearer"),
    }


def refresh_token() -> Dict[str, Any]:
    """Refresh the access token using the refresh token.

    Returns:
        Dict with new access_token, expires_in, token_type

    Raises:
        RuntimeError: If refresh fails
    """
    if not _token_cache.get("refresh_token"):
        raise RuntimeError("No refresh token available")

    url = f"{API_BASE}/auth/refresh"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_token_cache['refresh_token']}",
    }

    response = requests.post(url, headers=headers, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"Token refresh failed: {response.status_code} - {response.text}"
        )

    data = response.json()

    # Update cache
    _token_cache["access_token"] = data.get("access_token")
    _token_cache["token_type"] = data.get("token_type", "Bearer")

    expires_in = data.get("expires_in", 3600)
    _token_cache["expires_at"] = datetime.now() + timedelta(seconds=expires_in - 60)

    return {
        "access_token": data.get("access_token"),
        "expires_in": expires_in,
        "token_type": data.get("token_type", "Bearer"),
    }


def get_valid_token() -> str:
    """Get a valid access token, refreshing if necessary.

    Returns:
        Valid access token string

    Raises:
        RuntimeError: If unable to get valid token
    """
    # Check if current token is valid
    if _is_token_valid():
        return _token_cache["access_token"]

    # Try to refresh if we have a refresh token
    if _token_cache.get("refresh_token"):
        try:
            result = refresh_token()
            return result["access_token"]
        except RuntimeError:
            pass  # Fall through to login

    # Perform fresh login
    result = login_and_get_token()
    return result["access_token"]


def get_auth_headers() -> Dict[str, str]:
    """Get authorization headers with fresh token.

    Generates a fresh token at runtime and validates it before use.
    """
    headers = {"Content-Type": "application/json"}

    # Get fresh token
    try:
        token = get_valid_token()
        # Token already includes "Bearer " prefix if token_type is "Bearer"
        if token and not token.startswith("Bearer "):
            headers["Authorization"] = f"Bearer {token}"
        else:
            headers["Authorization"] = token
    except RuntimeError as e:
        print(f"Warning: Could not get valid token: {e}")

    if TEST_USER_ID:
        headers["X-User-Id"] = TEST_USER_ID

    return headers


def load_payload(phase: str) -> Dict[str, Any]:
    """Load a test payload by phase name."""
    payload_file = PAYLOADS_DIR / f"phase{phase}_test.json"
    if payload_file.exists():
        with open(payload_file) as f:
            return json.load(f)
    return {}


def read_sample_file(path: Path) -> str:
    """Read a sample file and return its content.

    Handles both text and binary files (.docx).
    For binary files, attempts to extract text or returns a placeholder.
    """
    if not path.exists():
        return ""

    # Try to detect file type and read appropriately
    suffix = path.suffix.lower()

    if suffix == ".docx":
        # Try to read as docx, fall back to placeholder
        try:
            # First check if python-docx is available
            import docx

            doc = docx.Document(str(path))
            text_parts = []
            for para in doc.paragraphs:
                text_parts.append(para.text)
            return "\n".join(text_parts)
        except ImportError:
            # python-docx not available, return placeholder
            return "CV content placeholder - python-docx not installed"
        except Exception:
            return "CV content placeholder - could not parse docx"

    # Default: try to read as text
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Binary file without .docx extension
        return "Binary file content placeholder"


# Test execution order - each test may depend on previous test data
TEST_DEPENDENCIES = {
    # User must register/login first
    "test_health_check": [],
    "test_auth_register": [],
    "test_auth_login": [],
    # CV upload requires auth
    "test_cv_upload": ["test_auth_login"],
    "test_list_cvs": ["test_cv_upload"],
    # Jobs require auth
    "test_create_job": ["test_auth_login"],
    "test_list_jobs": ["test_create_job"],
    "test_get_job": ["test_create_job"],
    # Company research requires job
    "test_company_research_fetch": ["test_create_job"],
    "test_company_research_get": ["test_company_research_fetch"],
    # Gap analysis requires CV and job
    "test_gap_analysis_generate_questions": ["test_cv_upload", "test_create_job"],
    "test_gap_analysis_submit_responses": ["test_gap_analysis_generate_questions"],
    "test_gap_analysis_get_questions": ["test_gap_analysis_generate_questions"],
    # VPR requires gap responses
    "test_vpr_generate": ["test_gap_analysis_submit_responses"],
    "test_vpr_get_status": ["test_vpr_generate"],
    "test_vpr_list": ["test_vpr_generate"],
    # CV tailoring requires VPR
    "test_cv_tailoring_generate": ["test_vpr_generate"],
    "test_cv_tailoring_get_status": ["test_cv_tailoring_generate"],
    "test_cv_tailoring_list": ["test_cv_tailoring_generate"],
    # Cover letter requires company research + VPR + gap responses
    "test_cover_letter_generate": ["test_vpr_generate", "test_company_research_fetch"],
    "test_cover_letter_get_status": ["test_cover_letter_generate"],
    "test_cover_letter_list": ["test_cover_letter_generate"],
    # Interview prep requires VPR + gap responses
    "test_interview_prep_generate": ["test_vpr_generate"],
    "test_interview_prep_get_status": ["test_interview_prep_generate"],
}


# Pytest Fixtures
import pytest


@pytest.fixture(scope="session")
def auth_credentials():
    """Shared test credentials"""
    return {"email": TEST_EMAIL, "password": TEST_PASSWORD}


@pytest.fixture(scope="session")
def auth_token(auth_credentials):
    """Get a valid auth token for the test session"""
    response = requests.post(f"{API_BASE}/auth/login", json=auth_credentials)
    if response.status_code == 200:
        return response.json()["access_token"]
    # If login fails, try register first
    requests.post(f"{API_BASE}/auth/register", json=auth_credentials)
    response = requests.post(f"{API_BASE}/auth/login", json=auth_credentials)
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Headers with authentication"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def test_data():
    """Shared test data across all tests for ID dependencies"""
    return {
        "cv_id": None,
        "job_id": None,
        "vpr_id": None,
        "tailored_cv_id": None,
        "cover_letter_id": None,
        "interview_prep_id": None,
    }
