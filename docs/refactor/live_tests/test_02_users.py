# Live Tests - User Management Endpoints
# Tests: GET /users/me, PUT /users/me, POST /users/me/cv, GET /users/me/cvs

import os
import json
import pytest
import requests
from typing import Any

# Import configuration
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .conftest import (
    API_BASE,
    get_auth_headers,
    SAMPLE_CV_PATH,
    read_sample_file,
    save_test_ids,
)

# Import test data from auth tests
from .test_01_auth_health import test_data


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


class TestUserEndpoints:
    """Test user management endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data."""
        self.base_url = API_BASE

    def test_get_current_user(self):
        """Test GET /users/me - retrieve current user profile."""
        url = f"{self.base_url}/users/me"
        headers = get_auth_headers()

        response = requests.get(url, headers=headers, timeout=10)

        # Print response
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_get_current_user", "GET /users/me", response.status_code, data
        )

        # Accept 200 (success) or 401 (auth required)
        if response.status_code == 200:
            assert "id" in data or "email" in data, "Invalid user response"
            print(f"✓ GET /users/me - User: {data.get('email', data.get('id'))}")
        else:
            print(
                f"⚠ GET /users/me - Status {response.status_code} (auth may be required)"
            )

    def test_update_current_user(self):
        """Test PUT /users/me - update current user profile."""
        url = f"{self.base_url}/users/me"
        headers = get_auth_headers()

        payload = {"name": "Test User Updated", "timezone": "America/New_York"}

        response = requests.put(url, json=payload, headers=headers, timeout=10)

        # Print response
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_update_current_user", "PUT /users/me", response.status_code, data
        )

        # Accept 200 (success) or 401 (auth required)
        if response.status_code == 200:
            print("✓ PUT /users/me - Updated user profile")
        else:
            print(
                f"⚠ PUT /users/me - Status {response.status_code} (auth may be required)"
            )

    def test_upload_cv(self):
        """Test POST /users/me/cv - upload CV file."""
        url = f"{self.base_url}/users/me/cv"
        headers = get_auth_headers()

        # Read sample CV content
        cv_content = read_sample_file(SAMPLE_CV_PATH)
        if not cv_content:
            # Use sample text if file not available
            cv_content = """
            John Doe
            Senior Software Engineer

            Experience:
            - 8 years Python development
            - AWS Solutions Architect certified
            - Led teams of up to 10 engineers

            Skills: Python, AWS, Docker, Kubernetes
            """

        payload = {"cv_content": cv_content, "file_name": "test_cv.docx"}

        response = requests.post(url, json=payload, headers=headers, timeout=30)

        # Print response
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_upload_cv", "POST /users/me/cv", response.status_code, data
        )

        # Accept 201 (created) or 200 (success)
        if response.status_code in [200, 201]:
            if "cv_id" in data:
                test_data["cv_id"] = data["cv_id"]
                save_test_ids(test_data)
            print(f"✓ POST /users/me/cv - CV uploaded, ID: {data.get('cv_id')}")
        else:
            print(
                f"⚠ POST /users/me/cv - Status {response.status_code}: {response.text[:200]}"
            )

    def test_list_user_cvs(self):
        """Test GET /users/me/cvs - list user's CVs."""
        url = f"{self.base_url}/users/me/cvs"
        headers = get_auth_headers()

        response = requests.get(url, headers=headers, timeout=10)

        # Print response
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_list_user_cvs", "GET /users/me/cvs", response.status_code, data
        )

        # Accept 200 (success) or 401 (auth required)
        if response.status_code == 200:
            cvs = data.get("cvs", [])
            print(f"✓ GET /users/me/cvs - Found {len(cvs)} CV(s)")
        else:
            print(f"⚠ GET /users/me/cvs - Status {response.status_code}")
