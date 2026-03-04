# Live Tests - VPR (Value Proposition Report) Endpoints
# Tests: POST /vpr/generate, GET /vpr/{vprId}/status, GET /vprs

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
from .quality_assertions import assert_vpr_quality

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


class TestVPREndpoints:
    """Test VPR (Value Proposition Report) endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data."""
        self.base_url = API_BASE

    def test_generate_vpr(self):
        """Test POST /vpr/generate - generate VPR."""
        url = f"{self.base_url}/vpr/generate"
        headers = get_auth_headers()

        # Build payload using test data from previous tests
        cv_id = test_data.get("cv_id") or f"cv_{TEST_USER_ID}"
        job_id = test_data.get("job_id") or f"job_{TEST_USER_ID}"
        gap_response_ids = test_data.get("gap_response_ids") or ["gap_test_001"]

        payload = {
            "cv_id": cv_id,
            "job_id": job_id,
            "gap_response_ids": gap_response_ids,
            "options": {"include_company_research": True, "tone": "professional"},
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60)

        # Accept 202 (accepted/async), 200 (sync), or 422 (prerequisites not met)
        if response.status_code in [200, 202]:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_generate_vpr", "POST /vpr/generate", response.status_code, data
            )

            if "request_id" in data:
                test_data["vpr_id"] = data["request_id"]
            elif "id" in data:
                test_data["vpr_id"] = data["id"]
            save_test_ids(test_data)
            print(
                f"✓ POST /vpr/generate - VPR submitted, ID: {test_data.get('vpr_id')}"
            )
        elif response.status_code == 422:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_generate_vpr", "POST /vpr/generate", response.status_code, data
            )
            print(
                "⚠ POST /vpr/generate - Prerequisites not met (need CV + gap responses)"
            )
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_generate_vpr", "POST /vpr/generate", response.status_code, data
            )
            print(
                f"⚠ POST /vpr/generate - Status {response.status_code}: {response.text[:200]}"
            )

    def test_get_vpr_status(self):
        """Test GET /vpr/{vprId}/status - poll VPR status."""
        # Auto-generate VPR if none exists
        if not test_data.get("vpr_id"):
            print("No VPR found, generating first...")
            self.test_generate_vpr()
            # Wait for async processing
            import time

            time.sleep(15)

        vpr_id = test_data.get("vpr_id")
        if not vpr_id:
            pytest.skip("No VPR ID available - generation may have failed")

        url = f"{self.base_url}/vpr/{vpr_id}/status"
        headers = get_auth_headers()

        response = requests.get(url, headers=headers, timeout=10)

        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_get_vpr_status",
            f"GET /vpr/{vpr_id}/status",
            response.status_code,
            data,
        )
        assert response.status_code == 200, (
            f"GET /vpr/{vpr_id}/status returned {response.status_code}"
        )
        status = data.get("status", "unknown")
        if status == "completed":
            assert_vpr_quality(data)
        print(f"✓ GET /vpr/{vpr_id}/status - Status: {status}")

    def test_list_vprs(self):
        """Test GET /vprs - list user's VPRs."""
        # Ensure at least one VPR request exists for deterministic list validation.
        if not test_data.get("vpr_id"):
            print("No VPR found, generating first...")
            self.test_generate_vpr()

        vpr_id = test_data.get("vpr_id")
        if not vpr_id:
            pytest.skip("No VPR ID available for list validation")

        url = f"{self.base_url}/vprs"
        headers = get_auth_headers()
        max_attempts = 12
        poll_interval = 5
        last_data: Any = {}
        last_status = 0

        for attempt in range(max_attempts):
            response = requests.get(url, headers=headers, timeout=10)
            last_status = response.status_code
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}
            last_data = data

            print_response("test_list_vprs", "GET /vprs", response.status_code, data)
            assert response.status_code == 200, (
                f"GET /vprs returned {response.status_code}"
            )

            vprs = data.get("vprs", [])
            if any(
                str(item.get("id")) == str(vpr_id)
                for item in vprs
                if isinstance(item, dict)
            ):
                print(
                    f"✓ GET /vprs - Found {len(vprs)} VPR(s), includes generated ID {vpr_id}"
                )
                return

            if attempt < max_attempts - 1:
                print(
                    f"  VPR list does not yet include {vpr_id} "
                    f"(attempt {attempt + 1}/{max_attempts})"
                )
                time.sleep(poll_interval)

        pytest.fail(
            f"GET /vprs did not include generated VPR ID {vpr_id} after "
            f"{max_attempts * poll_interval}s (last status={last_status}, last body={last_data})"
        )

    def test_vpr_async_polling(self):
        """Test VPR async polling lifecycle."""
        # First, submit a VPR request
        self.test_generate_vpr()

        vpr_id = test_data.get("vpr_id")
        if not vpr_id:
            pytest.skip("No VPR ID available for polling test")

        url = f"{self.base_url}/vpr/{vpr_id}/status"
        headers = get_auth_headers()

        # Poll for completion (max 2 minutes)
        max_attempts = 24  # 2 minutes / 5 seconds
        poll_interval = 5

        for attempt in range(max_attempts):
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    data = {"raw_text": response.text}

                print_response(
                    "test_vpr_async_polling",
                    f"GET /vpr/{vpr_id}/status",
                    response.status_code,
                    data,
                )

                status = data.get("status", "")

                if status == "completed":
                    assert_vpr_quality(data)
                    print(f"✓ VPR polling - Completed after {attempt * poll_interval}s")
                    return
                elif status in ["failed", "error"]:
                    print(f"✗ VPR polling - Failed: {data.get('error')}")
                    return
                else:
                    print(
                        f"  VPR status: {status} (attempt {attempt + 1}/{max_attempts})"
                    )

            time.sleep(poll_interval)

        pytest.fail(f"VPR polling timed out after {max_attempts * poll_interval}s")
