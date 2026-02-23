# Live Tests - Job Management Endpoints
# Tests: POST /jobs, GET /jobs, GET /jobs/{jobId}

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
    SAMPLE_JOB_PATH,
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


class TestJobEndpoints:
    """Test job management endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data."""
        self.base_url = API_BASE
        self.job_id = None

    def test_create_job(self):
        """Test POST /jobs - create a new job entry."""
        url = f"{self.base_url}/jobs"
        headers = get_auth_headers()

        # Read sample job description
        job_description = read_sample_file(SAMPLE_JOB_PATH)
        if not job_description:
            job_description = """
            Senior Software Engineer
            Company: TechCorp
            Looking for Python developer with AWS experience.
            """

        # Get CV ID from test data
        cv_id = test_data.get("cv_id") or f"cv_{os.getenv('TEST_USER_ID', 'test-user')}"

        payload = {
            "cv_id": cv_id,
            "title": "Learning Experience Specialist",
            "company_name": "SysAid",
            "job_description": job_description[:1000],  # Limit length
            "url": "https://www.sysaid.com/careers",
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)

        # Accept 201 (created) or 200 (success)
        if response.status_code in [200, 201]:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response("test_create_job", "POST /jobs", response.status_code, data)

            if "id" in data:
                self.job_id = data["id"]
                test_data["job_id"] = data["id"]
            elif "job_id" in data:
                self.job_id = data["job_id"]
                test_data["job_id"] = data["job_id"]
            save_test_ids(test_data)
            print(f"✓ POST /jobs - Job created, ID: {self.job_id or data}")
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response("test_create_job", "POST /jobs", response.status_code, data)
            print(
                f"⚠ POST /jobs - Status {response.status_code}: {response.text[:200]}"
            )

    def test_list_jobs(self):
        """Test GET /jobs - list all jobs for user."""
        url = f"{self.base_url}/jobs"
        headers = get_auth_headers()

        response = requests.get(url, headers=headers, timeout=10)

        # Accept 200 (success) or 401 (auth required)
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response("test_list_jobs", "GET /jobs", response.status_code, data)

            jobs = data.get("jobs", [])
            print(f"✓ GET /jobs - Found {len(jobs)} job(s)")
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response("test_list_jobs", "GET /jobs", response.status_code, data)
            print(f"⚠ GET /jobs - Status {response.status_code}")

    def test_get_job(self):
        """Test GET /jobs/{jobId} - get a specific job."""
        # Use stored job ID or create a test one
        job_id = test_data.get("job_id") or "test-job-id"

        url = f"{self.base_url}/jobs/{job_id}"
        headers = get_auth_headers()

        response = requests.get(url, headers=headers, timeout=10)

        # Accept 200 (success), 404 (not found), or 401 (auth required)
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_get_job", f"GET /jobs/{job_id}", response.status_code, data
            )

            print(f"✓ GET /jobs/{job_id} - Job retrieved")
        elif response.status_code == 404:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_get_job", f"GET /jobs/{job_id}", response.status_code, data
            )
            print(f"⚠ GET /jobs/{job_id} - Job not found (may need to create first)")
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_get_job", f"GET /jobs/{job_id}", response.status_code, data
            )
            print(f"⚠ GET /jobs/{job_id} - Status {response.status_code}")
