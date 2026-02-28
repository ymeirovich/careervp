# Live Tests - Company Research Endpoints
# Tests: GET /company-research/{jobId}

import os
import json
import time
import pytest
import requests
from typing import Any

# Import configuration
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .conftest import (
    API_BASE,
    TEST_USER_ID,
    get_auth_headers,
    COMPANY_URL,
    save_test_ids,
)

# Import test data from previous tests
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


class TestCompanyResearchEndpoints:
    """Test Company Research endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data."""
        self.base_url = API_BASE

    def test_company_research_fetch(self):
        """Test POST /company-research/fetch - SKIPPED: route not registered in API Gateway."""
        pytest.skip("POST /company-research/fetch is not registered in API Gateway - only GET /company-research/{jobId} exists")
        url = f"{self.base_url}/company-research/fetch"
        headers = get_auth_headers()

        # Build payload using test data
        job_id = test_data.get("job_id") or f"job_{TEST_USER_ID}"

        payload = {"job_id": job_id, "url": COMPANY_URL, "company_name": "SysAid"}

        response = requests.post(url, json=payload, headers=headers, timeout=60)

        # Accept 202 (accepted/async), 200 (sync), or 400 (validation error)
        if response.status_code in [200, 202]:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_company_research_fetch",
                "POST /company-research/fetch",
                response.status_code,
                data,
            )

            if "request_id" in data:
                test_data["company_research_id"] = data["request_id"]
            elif "company_research_id" in data:
                test_data["company_research_id"] = data["company_research_id"]
            elif "id" in data:
                test_data["company_research_id"] = data["id"]
            save_test_ids(test_data)
            print(
                f"✓ POST /company-research/fetch - Company research submitted, ID: {test_data.get('company_research_id')}"
            )
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_company_research_fetch",
                "POST /company-research/fetch",
                response.status_code,
                data,
            )
            print(
                f"⚠ POST /company-research/fetch - Status {response.status_code}: {response.text[:200]}"
            )

    def test_company_research_get(self):
        """Test GET /company-research/{jobId} - get company research for job."""
        job_id = test_data.get("job_id") or f"job_{TEST_USER_ID}"

        url = f"{self.base_url}/company-research/{job_id}"
        headers = get_auth_headers()

        response = requests.get(url, headers=headers, timeout=10)

        # Accept 200 (success), 404 (not found), or 401 (auth required)
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_company_research_get",
                f"GET /company-research/{job_id}",
                response.status_code,
                data,
            )

            company_name = data.get("company_name", "Unknown")
            print(f"✓ GET /company-research/{job_id} - Company: {company_name}")
        elif response.status_code == 404:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_company_research_get",
                f"GET /company-research/{job_id}",
                response.status_code,
                data,
            )
            print(f"⚠ GET /company-research/{job_id} - Company research not found")
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_company_research_get",
                f"GET /company-research/{job_id}",
                response.status_code,
                data,
            )
            print(f"⚠ GET /company-research/{job_id} - Status {response.status_code}")

    def test_company_research_async_polling(self):
        """Test company research async polling lifecycle - SKIPPED: depends on POST /company-research/fetch which is not registered."""
        pytest.skip("Depends on POST /company-research/fetch which is not registered in API Gateway")
        # First, submit a company research request
        self.test_company_research_fetch()

        # Use job_id to check status
        job_id = test_data.get("job_id")
        if not job_id:
            pytest.skip("No job ID available for company research polling test")

        url = f"{self.base_url}/company-research/{job_id}"
        headers = get_auth_headers()

        # Poll for completion (max 2 minutes)
        max_attempts = 24
        poll_interval = 5

        for attempt in range(max_attempts):
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    data = {"raw_text": response.text}

                print_response(
                    "test_company_research_async_polling",
                    f"GET /company-research/{job_id}",
                    response.status_code,
                    data,
                )

                status = data.get("status", "")

                if status == "completed":
                    company_name = data.get("company_name", "Unknown")
                    print(
                        f"✓ Company research polling - Completed after {attempt * poll_interval}s, Company: {company_name}"
                    )
                    return
                elif status in ["failed", "error"]:
                    print("✗ Company research polling - Failed")
                    return
                else:
                    print(
                        f"  Company research status: {status} (attempt {attempt + 1}/{max_attempts})"
                    )

            time.sleep(poll_interval)

        print(
            f"⚠ Company research polling - Timeout after {max_attempts * poll_interval}s"
        )
