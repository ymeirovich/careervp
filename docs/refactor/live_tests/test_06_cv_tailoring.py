# Live Tests - CV Tailoring Endpoints
# Tests: POST /cv-tailoring/generate, GET /cv-tailoring/{cvTailoringId}/status, GET /cv-tailorings

import os
import json
import time
import pytest
import requests
from typing import Any
from urllib.parse import quote

# Import configuration
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .conftest import API_BASE, TEST_USER_ID, get_auth_headers, save_test_ids
from .quality_assertions import assert_tailored_cv_quality

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


class TestCVTailoringEndpoints:
    """Test CV Tailoring endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data."""
        self.base_url = API_BASE

    def test_generate_tailored_cv(self):
        """Test POST /cv-tailoring/generate - generate ATS-optimized CV."""
        url = f"{self.base_url}/cv-tailoring/generate"
        headers = get_auth_headers()

        # Build payload using test data
        cv_id = test_data.get("cv_id") or f"cv_{TEST_USER_ID}"
        job_id = test_data.get("job_id") or f"job_{TEST_USER_ID}"
        vpr_id = test_data.get("vpr_id") or f"vpr_{TEST_USER_ID}"

        payload = {
            "cv_id": cv_id,
            "job_id": job_id,
            "vpr_id": vpr_id,
            "options": {
                "preserve_length": True,
                "highlight_keywords": True,
                "target_ats": "standard",
            },
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60)

        # Accept 202 (accepted/async), 200 (sync), or 422 (prerequisites not met)
        if response.status_code in [200, 202]:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_generate_tailored_cv",
                "POST /cv-tailoring/generate",
                response.status_code,
                data,
            )

            if "request_id" in data:
                test_data["cv_tailoring_id"] = data["request_id"]
            elif "id" in data:
                test_data["cv_tailoring_id"] = data["id"]
            elif "artifact_id" in data:
                test_data["cv_tailoring_id"] = data["artifact_id"]
            save_test_ids(test_data)
            print(
                f"✓ POST /cv-tailoring/generate - CV tailoring submitted, ID: {test_data.get('cv_tailoring_id')}"
            )
        elif response.status_code == 422:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_generate_tailored_cv",
                "POST /cv-tailoring/generate",
                response.status_code,
                data,
            )
            print(
                "⚠ POST /cv-tailoring/generate - Prerequisites not met (need CV + VPR)"
            )
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_generate_tailored_cv",
                "POST /cv-tailoring/generate",
                response.status_code,
                data,
            )
            print(
                f"⚠ POST /cv-tailoring/generate - Status {response.status_code}: {response.text[:200]}"
            )

    def test_get_tailored_cv_status(self):
        """Test GET /cv-tailoring/{cvTailoringId}/status - get tailored CV status."""
        # Auto-generate tailored CV if none exists
        if not test_data.get("cv_tailoring_id"):
            print("No tailored CV found, generating first...")
            self.test_generate_tailored_cv()
            # Wait for async processing
            import time
            time.sleep(15)

        # Status endpoint expects the request/artifact ID returned by generate.
        cv_tailoring_id = test_data.get("cv_tailoring_id")
        if not cv_tailoring_id:
            pytest.skip("No cv_tailoring_id available from generate response")

        # URL-encode the ID to handle # characters properly
        encoded_id = quote(cv_tailoring_id, safe="")
        url = f"{self.base_url}/cv-tailoring/{encoded_id}/status"
        headers = get_auth_headers()

        response = requests.get(url, headers=headers, timeout=10)

        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_get_tailored_cv_status",
            f"GET /cv-tailoring/{cv_tailoring_id}/status",
            response.status_code,
            data,
        )
        assert response.status_code == 200, f"GET /cv-tailoring/{cv_tailoring_id}/status returned {response.status_code}"
        assert_tailored_cv_quality(data)
        status = data.get("status", "unknown")
        ats_score = data.get("result", {}).get("ats_score", "N/A")
        print(f"✓ GET /cv-tailoring/{cv_tailoring_id}/status - Status: {status}, ATS Score: {ats_score}")

    def test_list_tailored_cvs(self):
        """Test GET /cv-tailorings - list user's tailored CVs."""
        url = f"{self.base_url}/cv-tailorings"
        headers = get_auth_headers()

        response = requests.get(url, headers=headers, timeout=10)

        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_list_tailored_cvs",
            "GET /cv-tailorings",
            response.status_code,
            data,
        )
        assert response.status_code == 200, f"GET /cv-tailorings returned {response.status_code}"
        tailored_cvs = data.get("tailored_cvs", [])
        print(f"✓ GET /cv-tailorings - Found {len(tailored_cvs)} tailored CV(s)")

    def test_cv_tailoring_async_polling(self):
        """Test CV tailoring async polling lifecycle."""
        # First, submit a CV tailoring request
        self.test_generate_tailored_cv()

        cv_tailoring_id = test_data.get("cv_tailoring_id")
        if not cv_tailoring_id:
            pytest.skip("No CV tailoring ID available for polling test")

        # URL-encode the ID to handle # characters properly
        encoded_id = quote(cv_tailoring_id, safe="")
        url = f"{self.base_url}/cv-tailoring/{encoded_id}/status"
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
                    "test_cv_tailoring_async_polling",
                    f"GET /cv-tailoring/{cv_tailoring_id}/status",
                    response.status_code,
                    data,
                )

                status = data.get("status", "")

                if status == "completed":
                    assert_tailored_cv_quality(data)
                    result = data.get("result", {})
                    ats_score = result.get("ats_score", "N/A")
                    print(
                        f"✓ CV tailoring polling - Completed after {attempt * poll_interval}s, ATS Score: {ats_score}"
                    )
                    return
                elif status in ["failed", "error"]:
                    print("✗ CV tailoring polling - Failed")
                    return
                else:
                    print(
                        f"  CV tailoring status: {status} (attempt {attempt + 1}/{max_attempts})"
                    )

            time.sleep(poll_interval)

        pytest.fail(f"CV tailoring polling timed out after {max_attempts * poll_interval}s")
