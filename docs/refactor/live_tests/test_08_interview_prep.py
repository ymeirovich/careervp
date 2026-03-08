# Live Tests - Interview Prep Endpoints
# Tests: POST /interview-prep/generate, GET /interview-prep/{interviewPrepId}/status

import os
import json
import time
import pytest
import requests
from typing import Any

# Import configuration
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .conftest import API_BASE, TEST_USER_ID, get_auth_headers, save_test_ids
from .quality_assertions import assert_interview_prep_quality

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


class TestInterviewPrepEndpoints:
    """Test Interview Prep endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data."""
        self.base_url = API_BASE

    def test_generate_interview_prep(self):
        """Test POST /interview-prep/generate - generate interview prep questions."""
        url = f"{self.base_url}/interview-prep/generate"
        headers = get_auth_headers()

        # Build payload using test data
        vpr_id = test_data.get("vpr_id") or f"vpr_{TEST_USER_ID}"
        gap_response_ids = test_data.get("gap_response_ids") or ["gap_test_001"]

        payload = {
            "vpr_id": vpr_id,
            "gap_response_ids": gap_response_ids,
            "focus_areas": ["technical", "behavioral", "situational"],
            "question_count": 10,
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60)

        # Accept 202 (accepted/async), 200 (sync), or 422 (prerequisites not met)
        if response.status_code in [200, 202]:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_generate_interview_prep",
                "POST /interview-prep/generate",
                response.status_code,
                data,
            )

            if "request_id" in data:
                test_data["interview_prep_id"] = data["request_id"]
            elif "artifact_id" in data:
                test_data["interview_prep_id"] = data["artifact_id"]
            elif "id" in data:
                test_data["interview_prep_id"] = data["id"]
            save_test_ids(test_data)
            print(
                f"✓ POST /interview-prep/generate - Interview prep submitted, ID: {test_data.get('interview_prep_id')}"
            )
        elif response.status_code == 422:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_generate_interview_prep",
                "POST /interview-prep/generate",
                response.status_code,
                data,
            )
            print(
                "⚠ POST /interview-prep/generate - Prerequisites not met (need VPR + Gap responses)"
            )
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_generate_interview_prep",
                "POST /interview-prep/generate",
                response.status_code,
                data,
            )
            print(
                f"⚠ POST /interview-prep/generate - Status {response.status_code}: {response.text[:200]}"
            )

    def test_get_interview_prep_status(self):
        """Test GET /interview-prep/{interviewPrepId}/status - get interview prep status."""
        # Auto-generate interview prep if none exists
        if not test_data.get("interview_prep_id"):
            print("No interview prep found, generating first...")
            self.test_generate_interview_prep()
            # Wait for async processing
            time.sleep(15)

        interview_prep_id = test_data.get("interview_prep_id")
        if not interview_prep_id:
            pytest.skip("No interview prep ID available - generation may have failed")

        url = f"{self.base_url}/interview-prep/{interview_prep_id}/status"
        headers = get_auth_headers()
        max_attempts = 12
        poll_interval = 5
        last_status = 0
        last_data: Any = {}

        for attempt in range(max_attempts):
            response = requests.get(url, headers=headers, timeout=10)
            last_status = response.status_code
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}
            last_data = data

            print_response(
                "test_get_interview_prep_status",
                f"GET /interview-prep/{interview_prep_id}/status",
                response.status_code,
                data,
            )

            if response.status_code == 200:
                status = data.get("status", "unknown")
                if status in ["pending", "processing"]:
                    if attempt < max_attempts - 1:
                        print(
                            f"  Interview prep status: {status} "
                            f"(attempt {attempt + 1}/{max_attempts})"
                        )
                        time.sleep(poll_interval)
                        continue
                    pytest.fail(
                        f"Interview prep remained {status!r} after "
                        f"{max_attempts * poll_interval}s"
                    )
                if status in ["failed", "error"]:
                    error = data.get("error")
                    code = data.get("code")
                    stage = data.get("failure_stage")
                    pytest.fail(
                        f"Interview prep failed for id={interview_prep_id}: "
                        f"error={error}, code={code}, failure_stage={stage}, body={data}"
                    )
                assert_interview_prep_quality(data)
                questions = data.get("result", {}).get("questions", [])
                print(
                    f"✓ GET /interview-prep/{interview_prep_id}/status - "
                    f"Status: {status}, Questions: {len(questions)}"
                )
                return

            if attempt < max_attempts - 1:
                print(
                    f"  Interview prep status endpoint returned {response.status_code} "
                    f"(attempt {attempt + 1}/{max_attempts})"
                )
                time.sleep(poll_interval)

        pytest.fail(
            f"GET /interview-prep/{interview_prep_id}/status did not return 200 after "
            f"{max_attempts * poll_interval}s (last status={last_status}, last body={last_data})"
        )

    def test_interview_prep_async_polling(self):
        """Test interview prep async polling lifecycle."""
        # First, submit an interview prep request
        self.test_generate_interview_prep()

        interview_prep_id = test_data.get("interview_prep_id")
        if not interview_prep_id:
            pytest.skip("No interview prep ID available for polling test")

        url = f"{self.base_url}/interview-prep/{interview_prep_id}/status"
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
                    "test_interview_prep_async_polling",
                    f"GET /interview-prep/{interview_prep_id}/status",
                    response.status_code,
                    data,
                )

                status = data.get("status", "")

                if status == "completed":
                    assert_interview_prep_quality(data)
                    questions = data.get("result", {}).get("questions", [])
                    print(
                        f"✓ Interview prep polling - Completed after {attempt * poll_interval}s, Questions: {len(questions)}"
                    )
                    return
                elif status in ["failed", "error"]:
                    error = data.get("error")
                    code = data.get("code")
                    stage = data.get("failure_stage")
                    pytest.fail(
                        f"Interview prep polling failed for id={interview_prep_id}: "
                        f"error={error}, code={code}, failure_stage={stage}, body={data}"
                    )
                else:
                    print(
                        f"  Interview prep status: {status} (attempt {attempt + 1}/{max_attempts})"
                    )
            else:
                try:
                    error_data = response.json()
                except Exception:
                    error_data = {"raw_text": response.text}
                print_response(
                    "test_interview_prep_async_polling",
                    f"GET /interview-prep/{interview_prep_id}/status",
                    response.status_code,
                    error_data,
                )
                print(
                    f"  Interview prep polling received HTTP {response.status_code} "
                    f"(attempt {attempt + 1}/{max_attempts})"
                )

            time.sleep(poll_interval)

        pytest.fail(
            f"Interview prep polling timed out after {max_attempts * poll_interval}s"
        )
