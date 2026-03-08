"""
E2E Tests for VPR Async Polling Architecture.

Tests the complete Submit -> Poll -> Verify flow for VPR async job processing.
Validates the API contract defined in docs/specs/07-vpr-async-architecture.md.

Test Coverage:
- Job submission with 202 Accepted response
- Status polling until COMPLETED (max 60s timeout)
- Result retrieval from S3 presigned URL
- Idempotency key behavior
- Failed job handling

Environment Variables:
- API_BASE_URL: Base URL for the API endpoint
  (default: https://dev-api.careervp.com/prod)
- VPR_SUBMIT_ENDPOINT: Override submit endpoint (default: /vpr/generate)
- VPR_STATUS_ENDPOINT: Override status endpoint (default: /vpr)
- TEST_TIMEOUT: Max wait time in seconds (default: 60)
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
import pytest

RUN_E2E = os.getenv("RUN_E2E", "").lower() in {"1", "true", "yes"}
pytestmark = pytest.mark.skipif(
    not RUN_E2E,
    reason="Set RUN_E2E=true and API_BASE_URL to execute live VPR async E2E tests.",
)


class VPRAsyncClient:
    """HTTP client wrapper for VPR async API interactions."""

    def __init__(self, base_url: str) -> None:
        """
        Initialize the VPR async API client.

        Args:
            base_url: Base URL for API (e.g., https://api.careervp.com)
        """
        self.base_url = base_url.rstrip("/")
        self.submit_path = os.getenv("VPR_SUBMIT_ENDPOINT", "/vpr/generate")
        self.status_path = os.getenv("VPR_STATUS_ENDPOINT", "/vpr")
        self.timeout = int(os.getenv("TEST_TIMEOUT", "60"))

    def submit_vpr_job(self, payload: dict[str, Any]) -> httpx.Response:
        """
        Submit a VPR generation job.

        Args:
            payload: VPR request payload matching VPRRequest schema

        Returns:
            HTTP response with job_id and status
        """
        url = f"{self.base_url}{self.submit_path}"
        with httpx.Client(timeout=30.0) as client:
            return client.post(url, json=payload)

    def get_job_status(self, job_id: str) -> httpx.Response:
        """
        Poll job status by job_id.

        Args:
            job_id: UUID of the submitted job

        Returns:
            HTTP response with job status
        """
        url = f"{self.base_url}{self.status_path}/{job_id}"
        with httpx.Client(timeout=30.0) as client:
            return client.get(url)

    def poll_until_completed(
        self,
        job_id: str,
        interval: int = 5,
        max_wait: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Poll job status until COMPLETED or FAILED, or timeout.

        Args:
            job_id: UUID of the job to poll
            interval: Seconds between polls (default: 5)
            max_wait: Max seconds to wait (default: self.timeout)

        Returns:
            Tuple of (final_status, response_body)

        Raises:
            TimeoutError: If polling exceeds max_wait
        """
        max_wait = max_wait or self.timeout
        start_time = time.time()
        poll_count = 0

        while time.time() - start_time < max_wait:
            poll_count += 1
            response = self.get_job_status(job_id)
            body = response.json()

            status = body.get("status")
            if status in ("completed", "failed"):
                return status, body

            if status not in ("pending", "processing"):
                raise ValueError(f"Unexpected status: {status}")

            time.sleep(interval)

        elapsed = time.time() - start_time
        raise TimeoutError(
            f"Job {job_id} did not complete within {elapsed:.1f}s ({poll_count} polls)"
        )

    def retrieve_result_from_s3(self, presigned_url: str) -> dict[str, Any]:
        """
        Fetch VPR result from S3 presigned URL.

        Args:
            presigned_url: S3 presigned URL from COMPLETED status response

        Returns:
            VPR JSON payload

        Raises:
            httpx.HTTPStatusError: If S3 request fails
        """
        with httpx.Client(timeout=30.0) as client:
            response = client.get(presigned_url)
            response.raise_for_status()
            return response.json()


@pytest.fixture(scope="module")
def api_base_url() -> str:
    """
    Get API base URL from environment or use default.

    Returns:
        Base URL for API Gateway endpoint
    """
    return os.getenv(
        "API_BASE_URL",
        "https://dev-api.careervp.com/prod",
    )


@pytest.fixture(scope="module")
def vpr_client(api_base_url: str) -> VPRAsyncClient:
    """
    Instantiate VPR async API client.

    Args:
        api_base_url: Base URL fixture

    Returns:
        Configured VPRAsyncClient instance
    """
    return VPRAsyncClient(api_base_url)


@pytest.fixture
def sample_vpr_payload() -> dict[str, Any]:
    """
    Generate a valid VPR request payload.

    Returns:
        VPRRequest-compliant dictionary
    """
    return {
        "cv_id": "cv-test-123",
        "job_id": f"job-test-{int(time.time())}",
        "gap_response_ids": [],
        "options": {"include_company_research": True, "tone": "professional"},
    }


class TestVPRAsyncPolling:
    """E2E test suite for VPR async job processing."""

    def test_submit_vpr_job_returns_202_with_job_id(
        self,
        vpr_client: VPRAsyncClient,
        sample_vpr_payload: dict[str, Any],
    ) -> None:
        """
        Test job submission returns 202 Accepted with valid request_id.

        Validates:
        - HTTP 202 status code
        - Response contains request_id
        - Response contains status (processing)
        """
        response = vpr_client.submit_vpr_job(sample_vpr_payload)

        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}: {response.text}"
        )

        body = response.json()
        assert "request_id" in body, "Response missing request_id field"
        assert "status" in body, "Response missing status field"
        assert body["status"] in ("processing", "pending"), (
            f"Expected processing/pending, got {body['status']}"
        )

        request_id = body["request_id"]
        # Validate UUID-ish format (basic check: 36 chars with hyphens)
        assert len(request_id) == 36 and request_id.count("-") == 4, (
            f"Invalid request_id format: {request_id}"
        )

    def test_poll_status_until_completed(
        self,
        vpr_client: VPRAsyncClient,
        sample_vpr_payload: dict[str, Any],
    ) -> None:
        """
        Test polling status endpoint until job completes.

        Validates:
        - Status transitions: pending -> processing -> completed
        - Polling completes within 60s timeout
        - completed response includes result payload and timestamps
        """
        # Submit job
        submit_response = vpr_client.submit_vpr_job(sample_vpr_payload)
        assert submit_response.status_code == 202
        request_id = submit_response.json()["request_id"]

        # Poll until completed
        final_status, body = vpr_client.poll_until_completed(
            request_id, interval=5, max_wait=60
        )

        assert final_status == "completed", f"Expected completed, got {final_status}"
        assert "result" in body, "completed response missing result payload"
        assert "created_at" in body, "completed response missing created_at timestamp"
        assert "completed_at" in body, (
            "completed response missing completed_at timestamp"
        )

        # Validate minimal OpenAPI response structure
        result = body["result"]
        assert isinstance(result, dict), "result must be object"
        assert "uvp" in result or "strategic_narrative" in result

    def test_retrieve_result_payload(
        self,
        vpr_client: VPRAsyncClient,
        sample_vpr_payload: dict[str, Any],
    ) -> None:
        """
        Test retrieving VPR result from status payload.

        Validates:
        - VPR structure matches expected schema
        - Contains required fields in `result`
        """
        # Submit and poll until completed
        submit_response = vpr_client.submit_vpr_job(sample_vpr_payload)
        request_id = submit_response.json()["request_id"]
        final_status, body = vpr_client.poll_until_completed(request_id)

        assert final_status == "completed"
        vpr_result = body["result"]

        # Validate VPR structure
        assert "uvp" in vpr_result, "VPR missing uvp"
        assert "differentiators" in vpr_result, "VPR missing differentiators"
        assert "strategic_narrative" in vpr_result, "VPR missing strategic_narrative"
        assert "meta_evaluation" in vpr_result, "VPR missing meta_evaluation"

        # Validate differentiators structure
        assert isinstance(vpr_result["differentiators"], list), (
            "differentiators must be list"
        )
        if vpr_result["differentiators"]:
            first_item = vpr_result["differentiators"][0]
            assert "text" in first_item, "Differentiator missing text"

    def test_idempotent_submit(
        self,
        vpr_client: VPRAsyncClient,
        sample_vpr_payload: dict[str, Any],
    ) -> None:
        """
        Test idempotency: submitting same request twice returns existing job.

        Validates:
        - First request: 202 with new request_id
        - Second request: 200/202 with same request_id (if idempotent)
        """
        # First submission
        response1 = vpr_client.submit_vpr_job(sample_vpr_payload)
        assert response1.status_code == 202
        body1 = response1.json()
        request_id_1 = body1["request_id"]

        # Second submission (duplicate)
        response2 = vpr_client.submit_vpr_job(sample_vpr_payload)
        assert response2.status_code in (200, 202), (
            f"Expected 200/202 for duplicate, got {response2.status_code}"
        )
        body2 = response2.json()
        request_id_2 = body2["request_id"]

        # Validate same job returned
        assert request_id_1 == request_id_2, (
            f"Idempotency failed: different request_ids {request_id_1} vs {request_id_2}"
        )
        assert body2["status"] in ("pending", "processing", "completed"), (
            f"Unexpected status: {body2['status']}"
        )

    def test_failed_job_status(
        self,
        vpr_client: VPRAsyncClient,
    ) -> None:
        """
        Test handling of failed job status.

        This test verifies the API contract for FAILED jobs but requires
        a mechanism to trigger failure (e.g., invalid input, worker crash).

        In real E2E, this would:
        - Submit a job designed to fail (e.g., malformed gap_responses)
        - Poll until status = FAILED
        - Validate error field presence
        - Ensure no result_url present

        NOTE: This test is SKIPPED in CI unless ENABLE_FAILURE_TESTS=1
        because triggering controlled failures requires special setup.
        """
        if not os.getenv("ENABLE_FAILURE_TESTS"):
            pytest.skip("Failure tests disabled. Set ENABLE_FAILURE_TESTS=1 to run.")

        # Example payload designed to trigger validation failure
        invalid_payload = {
            "cv_id": "cv-does-not-exist",
            "job_id": f"job-fail-{int(time.time())}",
            "gap_response_ids": [],
        }

        response = vpr_client.submit_vpr_job(invalid_payload)
        if response.status_code == 404:
            # Immediate failure due to missing CV
            body = response.json()
            assert "error" in body, "Failed response missing error field"
            return

        # If job was queued, poll until FAILED
        request_id = response.json()["request_id"]
        final_status, body = vpr_client.poll_until_completed(request_id, max_wait=30)

        assert final_status == "failed", f"Expected failed, got {final_status}"
        assert "error" in body, "FAILED response missing error field"
        assert "result" not in body, "FAILED job should not have result payload"

    def test_job_not_found_returns_404(
        self,
        vpr_client: VPRAsyncClient,
    ) -> None:
        """
        Test status endpoint returns 404 for non-existent request_id.

        Validates:
        - HTTP 404 status code
        - Error message indicates job not found
        """
        fake_request_id = "00000000-0000-0000-0000-000000000000"
        response = vpr_client.get_job_status(fake_request_id)

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        body = response.json()
        assert "error" in body, "Response missing error field"
        assert "not found" in body["error"].lower(), (
            "Error message should indicate job not found"
        )

    def test_poll_handles_processing_status(
        self,
        vpr_client: VPRAsyncClient,
        sample_vpr_payload: dict[str, Any],
    ) -> None:
        """
        Test that polling correctly handles processing status transition.

        Validates:
        - Status transitions through pending -> processing -> completed
        - processing response includes created/start timestamps
        - Polling continues until terminal status
        """
        response = vpr_client.submit_vpr_job(sample_vpr_payload)
        request_id = response.json()["request_id"]

        # Poll with short interval to catch PROCESSING state
        seen_statuses = set()
        max_polls = 15
        for _ in range(max_polls):
            status_response = vpr_client.get_job_status(request_id)
            body = status_response.json()
            status = body["status"]
            seen_statuses.add(status)

            if status == "processing":
                assert "created_at" in body, (
                    "processing response missing created_at timestamp"
                )

            if status in ("completed", "failed"):
                break

            time.sleep(3)

        # Verify we saw expected state transitions
        assert "completed" in seen_statuses or "failed" in seen_statuses, (
            f"Job did not reach terminal state. Seen: {seen_statuses}"
        )
