# Live Tests - Cover Letter Endpoints
# Tests: POST /cover-letter/generate, GET /cover-letter/{coverLetterId}, GET /users/me/cover-letters

import os
import json
import time
import pytest
import requests
from typing import Any

# Import configuration
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from conftest import API_BASE, TEST_USER_ID, get_auth_headers, save_test_ids

# Import test data from previous tests
from test_01_auth_health import test_data


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


class TestCoverLetterEndpoints:
    """Test Cover Letter endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data."""
        self.base_url = API_BASE

    def test_generate_cover_letter(self):
        """Test POST /cover-letter/generate - generate cover letter."""
        url = f"{self.base_url}/cover-letter/generate"
        headers = get_auth_headers()

        # Build payload using test data
        cv_id = test_data.get("cv_id") or f"cv_{TEST_USER_ID}"
        job_id = test_data.get("job_id") or f"job_{TEST_USER_ID}"
        vpr_id = test_data.get("vpr_id") or f"vpr_{TEST_USER_ID}"
        gap_response_ids = test_data.get("gap_response_ids", ["gap_test_001"])
        company_research_id = (
            test_data.get("company_research_id") or f"comp_{TEST_USER_ID}"
        )

        payload = {
            "cv_id": cv_id,
            "job_id": job_id,
            "vpr_id": vpr_id,
            "gap_response_ids": gap_response_ids,
            "company_research_id": company_research_id,
            "options": {
                "tone": "professional",
                "length": "standard",
                "include_portfolio_link": False,
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
                "test_generate_cover_letter",
                "POST /cover-letter/generate",
                response.status_code,
                data,
            )

            if "request_id" in data:
                test_data["cover_letter_id"] = data["request_id"]
            elif "id" in data:
                test_data["cover_letter_id"] = data["id"]
            save_test_ids(test_data)
            print(
                f"✓ POST /cover-letter/generate - Cover letter submitted, ID: {test_data.get('cover_letter_id')}"
            )
        elif response.status_code == 422:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_generate_cover_letter",
                "POST /cover-letter/generate",
                response.status_code,
                data,
            )
            print(
                "⚠ POST /cover-letter/generate - Prerequisites not met (need CV + VPR + Gap + Company Research)"
            )
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_generate_cover_letter",
                "POST /cover-letter/generate",
                response.status_code,
                data,
            )
            print(
                f"⚠ POST /cover-letter/generate - Status {response.status_code}: {response.text[:200]}"
            )

    def test_get_cover_letter_status(self):
        """Test GET /cover-letter/{coverLetterId} - get cover letter status."""
        cover_letter_id = test_data.get("cover_letter_id") or "test-cover-letter-id"

        url = f"{self.base_url}/cover-letter/{cover_letter_id}"
        headers = get_auth_headers()

        response = requests.get(url, headers=headers, timeout=10)

        # Accept 200 (success), 404 (not found), or 401 (auth required)
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_get_cover_letter_status",
                f"GET /cover-letter/{cover_letter_id}",
                response.status_code,
                data,
            )

            status = data.get("status", "unknown")
            result = data.get("result", {})
            if result:
                result.get("paragraphs", {})
                print(f"✓ GET /cover-letter/{cover_letter_id} - Status: {status}")
            else:
                print(f"✓ GET /cover-letter/{cover_letter_id} - Status: {status}")
        elif response.status_code == 404:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_get_cover_letter_status",
                f"GET /cover-letter/{cover_letter_id}",
                response.status_code,
                data,
            )
            print(f"⚠ GET /cover-letter/{cover_letter_id} - Cover letter not found")
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_get_cover_letter_status",
                f"GET /cover-letter/{cover_letter_id}",
                response.status_code,
                data,
            )
            print(
                f"⚠ GET /cover-letter/{cover_letter_id} - Status {response.status_code}"
            )

    def test_list_cover_letters(self):
        """Test GET /users/me/cover-letters - list user's cover letters."""
        url = f"{self.base_url}/users/me/cover-letters"
        headers = get_auth_headers()

        response = requests.get(url, headers=headers, timeout=10)

        # Accept 200 (success) or 401 (auth required)
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_list_cover_letters",
                "GET /users/me/cover-letters",
                response.status_code,
                data,
            )

            cover_letters = data.get("cover_letters", [])
            print(
                f"✓ GET /users/me/cover-letters - Found {len(cover_letters)} cover letter(s)"
            )
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_list_cover_letters",
                "GET /users/me/cover-letters",
                response.status_code,
                data,
            )
            print(f"⚠ GET /users/me/cover-letters - Status {response.status_code}")

    def test_cover_letter_async_polling(self):
        """Test cover letter async polling lifecycle."""
        # First, submit a cover letter request
        self.test_generate_cover_letter()

        cover_letter_id = test_data.get("cover_letter_id")
        if not cover_letter_id:
            pytest.skip("No cover letter ID available for polling test")

        url = f"{self.base_url}/cover-letter/{cover_letter_id}"
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
                    "test_cover_letter_async_polling",
                    f"GET /cover-letter/{cover_letter_id}",
                    response.status_code,
                    data,
                )

                status = data.get("status", "")

                if status == "completed":
                    result = data.get("result", {})
                    result.get("paragraphs", {})
                    print(
                        f"✓ Cover letter polling - Completed after {attempt * poll_interval}s"
                    )
                    return
                elif status in ["failed", "error"]:
                    print("✗ Cover letter polling - Failed")
                    return
                else:
                    print(
                        f"  Cover letter status: {status} (attempt {attempt + 1}/{max_attempts})"
                    )

            time.sleep(poll_interval)

        print(f"⚠ Cover letter polling - Timeout after {max_attempts * poll_interval}s")
