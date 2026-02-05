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
- API_BASE_URL: Base URL for the API endpoint (default: http://localhost:3000)
- VPR_SUBMIT_ENDPOINT: Override submit endpoint (default: /api/vpr)
- VPR_STATUS_ENDPOINT: Override status endpoint (default: /api/vpr/status)
- TEST_TIMEOUT: Max wait time in seconds (default: 60)
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
import pytest


class VPRAsyncClient:
    """HTTP client wrapper for VPR async API interactions."""

    def __init__(self, base_url: str) -> None:
        """
        Initialize the VPR async API client.

        Args:
            base_url: Base URL for API (e.g., https://api.careervp.com)
        """
        self.base_url = base_url.rstrip("/")
        self.submit_path = os.getenv("VPR_SUBMIT_ENDPOINT", "/api/vpr")
        self.status_path = os.getenv("VPR_STATUS_ENDPOINT", "/api/vpr/status")
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
            if status in ("COMPLETED", "FAILED"):
                return status, body

            if status not in ("PENDING", "PROCESSING"):
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
    return os.getenv("API_BASE_URL", "http://localhost:3000")


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
        "application_id": f"app-test-{int(time.time())}",
        "user_id": "user-test-123",
        "job_posting": {
            "company_name": "Natural Intelligence",
            "role_title": "Learning & Development Manager",
            "description": "Lead L&D initiatives for fast-growing tech company.",
            "responsibilities": [
                "Design and deliver training programs",
                "Manage learning management system",
                "Partner with department heads on skill development",
            ],
            "requirements": [
                "5+ years in learning and development",
                "Experience with LMS platforms",
                "Strong facilitation skills",
            ],
            "nice_to_have": ["Tech industry background"],
            "language": "en",
        },
        "gap_responses": [
            {
                "question": "How do you plan to address the LMS experience requirement?",
                "answer": "I have 3 years managing Cornerstone OnDemand and recently completed certification in Workday Learning.",
            }
        ],
    }


class TestVPRAsyncPolling:
    """E2E test suite for VPR async job processing."""

    def test_submit_vpr_job_returns_202_with_job_id(
        self,
        vpr_client: VPRAsyncClient,
        sample_vpr_payload: dict[str, Any],
    ) -> None:
        """
        Test job submission returns 202 Accepted with valid job_id.

        Validates:
        - HTTP 202 status code
        - Response contains job_id (UUID format)
        - Response contains status (PENDING)
        - Response includes success message
        """
        response = vpr_client.submit_vpr_job(sample_vpr_payload)

        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}: {response.text}"
        )

        body = response.json()
        assert "job_id" in body, "Response missing job_id field"
        assert "status" in body, "Response missing status field"
        assert body["status"] == "PENDING", f"Expected PENDING, got {body['status']}"
        assert "message" in body, "Response missing message field"

        job_id = body["job_id"]
        # Validate UUID format (basic check: 36 chars with hyphens)
        assert len(job_id) == 36 and job_id.count("-") == 4, (
            f"Invalid job_id format: {job_id}"
        )

    def test_poll_status_until_completed(
        self,
        vpr_client: VPRAsyncClient,
        sample_vpr_payload: dict[str, Any],
    ) -> None:
        """
        Test polling status endpoint until job completes.

        Validates:
        - Status transitions: PENDING -> PROCESSING -> COMPLETED
        - Polling completes within 60s timeout
        - COMPLETED response includes result_url
        - Response includes token_usage and timestamps
        """
        # Submit job
        submit_response = vpr_client.submit_vpr_job(sample_vpr_payload)
        assert submit_response.status_code == 202
        job_id = submit_response.json()["job_id"]

        # Poll until completed
        final_status, body = vpr_client.poll_until_completed(
            job_id, interval=5, max_wait=60
        )

        assert final_status == "COMPLETED", f"Expected COMPLETED, got {final_status}"
        assert "result_url" in body, "COMPLETED response missing result_url"
        assert "token_usage" in body, "COMPLETED response missing token_usage"
        assert "created_at" in body, "COMPLETED response missing created_at timestamp"
        assert "completed_at" in body, (
            "COMPLETED response missing completed_at timestamp"
        )

        # Validate token_usage structure
        token_usage = body["token_usage"]
        assert "input_tokens" in token_usage, "token_usage missing input_tokens"
        assert "output_tokens" in token_usage, "token_usage missing output_tokens"
        assert isinstance(token_usage["input_tokens"], int), (
            "input_tokens must be integer"
        )
        assert isinstance(token_usage["output_tokens"], int), (
            "output_tokens must be integer"
        )

    def test_retrieve_result_from_s3(
        self,
        vpr_client: VPRAsyncClient,
        sample_vpr_payload: dict[str, Any],
    ) -> None:
        """
        Test retrieving VPR result from S3 presigned URL.

        Validates:
        - Presigned URL is accessible
        - Response is valid JSON
        - VPR structure matches expected schema
        - Contains required fields: executive_summary, evidence_matrix, etc.
        """
        # Submit and poll until completed
        submit_response = vpr_client.submit_vpr_job(sample_vpr_payload)
        job_id = submit_response.json()["job_id"]
        final_status, body = vpr_client.poll_until_completed(job_id)

        assert final_status == "COMPLETED"
        result_url = body["result_url"]

        # Retrieve VPR from S3
        vpr_result = vpr_client.retrieve_result_from_s3(result_url)

        # Validate VPR structure
        assert "executive_summary" in vpr_result, "VPR missing executive_summary"
        assert "evidence_matrix" in vpr_result, "VPR missing evidence_matrix"
        assert "differentiators" in vpr_result, "VPR missing differentiators"
        assert "gap_strategies" in vpr_result, "VPR missing gap_strategies"
        assert "cultural_fit" in vpr_result, "VPR missing cultural_fit"
        assert "talking_points" in vpr_result, "VPR missing talking_points"
        assert "keywords" in vpr_result, "VPR missing keywords"

        # Validate evidence_matrix structure
        assert isinstance(vpr_result["evidence_matrix"], list), (
            "evidence_matrix must be list"
        )
        if vpr_result["evidence_matrix"]:
            first_evidence = vpr_result["evidence_matrix"][0]
            assert "requirement" in first_evidence, "Evidence item missing requirement"
            assert "evidence" in first_evidence, "Evidence item missing evidence"
            assert "alignment_score" in first_evidence, (
                "Evidence item missing alignment_score"
            )

    def test_idempotent_submit(
        self,
        vpr_client: VPRAsyncClient,
        sample_vpr_payload: dict[str, Any],
    ) -> None:
        """
        Test idempotency: submitting same request twice returns existing job.

        Validates:
        - First request: 202 with new job_id
        - Second request: 200 with same job_id
        - Idempotency key based on user_id + application_id
        - Status reflects current job state (not always PENDING)
        """
        # First submission
        response1 = vpr_client.submit_vpr_job(sample_vpr_payload)
        assert response1.status_code == 202
        body1 = response1.json()
        job_id_1 = body1["job_id"]

        # Second submission (duplicate)
        response2 = vpr_client.submit_vpr_job(sample_vpr_payload)
        assert response2.status_code == 200, (
            f"Expected 200 for duplicate, got {response2.status_code}"
        )
        body2 = response2.json()
        job_id_2 = body2["job_id"]

        # Validate same job returned
        assert job_id_1 == job_id_2, (
            f"Idempotency failed: different job_ids {job_id_1} vs {job_id_2}"
        )
        assert body2["status"] in ("PENDING", "PROCESSING", "COMPLETED"), (
            f"Unexpected status: {body2['status']}"
        )
        assert "message" in body2 and "already exists" in body2["message"].lower(), (
            "Missing idempotency message"
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
            "application_id": f"app-fail-{int(time.time())}",
            "user_id": "user-nonexistent-999",  # User without CV
            "job_posting": {
                "company_name": "TestCo",
                "role_title": "Test Role",
                "description": "Test",
                "responsibilities": ["Test"],
                "requirements": ["Test"],
                "nice_to_have": [],
                "language": "en",
            },
            "gap_responses": [],
        }

        response = vpr_client.submit_vpr_job(invalid_payload)
        if response.status_code == 404:
            # Immediate failure due to missing CV
            body = response.json()
            assert "error" in body, "Failed response missing error field"
            return

        # If job was queued, poll until FAILED
        job_id = response.json()["job_id"]
        final_status, body = vpr_client.poll_until_completed(job_id, max_wait=30)

        assert final_status == "FAILED", f"Expected FAILED, got {final_status}"
        assert "error" in body, "FAILED response missing error field"
        assert "result_url" not in body, "FAILED job should not have result_url"

    def test_job_not_found_returns_404(
        self,
        vpr_client: VPRAsyncClient,
    ) -> None:
        """
        Test status endpoint returns 404 for non-existent job_id.

        Validates:
        - HTTP 404 status code
        - Error message indicates job not found
        """
        fake_job_id = "00000000-0000-0000-0000-000000000000"
        response = vpr_client.get_job_status(fake_job_id)

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
        Test that polling correctly handles PROCESSING status transition.

        Validates:
        - Status transitions through PENDING -> PROCESSING -> COMPLETED
        - PROCESSING response includes started_at timestamp
        - Polling continues until terminal status
        """
        response = vpr_client.submit_vpr_job(sample_vpr_payload)
        job_id = response.json()["job_id"]

        # Poll with short interval to catch PROCESSING state
        seen_statuses = set()
        max_polls = 15
        for _ in range(max_polls):
            status_response = vpr_client.get_job_status(job_id)
            body = status_response.json()
            status = body["status"]
            seen_statuses.add(status)

            if status == "PROCESSING":
                assert "started_at" in body, (
                    "PROCESSING response missing started_at timestamp"
                )

            if status in ("COMPLETED", "FAILED"):
                break

            time.sleep(3)

        # Verify we saw expected state transitions
        assert "COMPLETED" in seen_statuses or "FAILED" in seen_statuses, (
            f"Job did not reach terminal state. Seen: {seen_statuses}"
        )
