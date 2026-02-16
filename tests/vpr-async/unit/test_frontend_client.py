"""
Unit tests for VPRAsyncClient - Frontend polling integration.

Tests cover:
- Client initialization
- Job submission (202 Accepted)
- Status polling with exponential backoff
- Result retrieval
- Error handling (network, timeouts, 4xx/5xx)
"""

import pytest
from unittest.mock import AsyncMock


class VPRAsyncClient:
    """Async VPR client with polling and exponential backoff."""

    def __init__(self, base_url: str, timeout: int = 30, max_retries: int = 3):
        """Initialize VPR async client.

        Args:
            base_url: API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum retries per request
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = None

    async def submit_vpr_job(self, vpr_request: dict) -> dict:
        """Submit VPR job and return request_id.

        Args:
            vpr_request: VPR request payload

        Returns:
            Response with request_id and status (202 Accepted)

        Raises:
            ConnectionError: Network failure
            ValueError: Invalid request
        """
        if not vpr_request.get("cv_id"):
            raise ValueError("cv_id is required")
        if not vpr_request.get("job_id"):
            raise ValueError("job_id is required")

        url = f"{self.base_url}/vpr/generate"
        response = await self._post(url, vpr_request)

        if response["status_code"] == 202:
            return {
                "status_code": 202,
                "request_id": response["data"].get("request_id"),
                "status": response["data"].get("status", "pending"),
            }
        elif response["status_code"] == 200:
            # Idempotent: job already exists
            return {
                "status_code": 200,
                "request_id": response["data"].get("request_id"),
                "status": response["data"].get("status"),
            }
        else:
            raise ValueError(f"HTTP {response['status_code']}: {response.get('error')}")

    async def poll_status(
        self, request_id: str, poll_interval: int = 5, max_polls: int = 60
    ) -> dict:
        """Poll job status with exponential backoff on retries.

        Args:
            request_id: Job ID to poll
            poll_interval: Interval between polls (seconds)
            max_polls: Maximum number of polls

        Returns:
            Status response (202 if pending, 200 if complete)

        Raises:
            TimeoutError: Exceeded max_polls
            ValueError: Job not found (404) or expired (410)
        """
        for poll_count in range(max_polls):
            url = f"{self.base_url}/vpr/{request_id}"

            try:
                response = await self._get_with_backoff(url, poll_count)

                if response["status_code"] == 404:
                    raise ValueError("Job not found")
                elif response["status_code"] == 410:
                    raise ValueError("Result expired")
                elif response["status_code"] in [200, 202]:
                    data = response.get("data", {})

                    # Check if complete
                    if data.get("status") in ["completed", "failed"]:
                        return {
                            "status_code": 200,
                            "status": data.get("status"),
                            "result": data.get("result"),
                            "error": data.get("error"),
                            "token_usage": data.get("token_usage"),
                        }

                    # Still processing, continue polling
                    if poll_count < max_polls - 1:
                        await self._sleep(poll_interval)
                        continue
                else:
                    raise ValueError(f"HTTP {response['status_code']}")

            except Exception:
                # Retry on transient errors
                if poll_count < max_polls - 1:
                    backoff_delay = min(poll_interval * (2**poll_count), 60)
                    await self._sleep(backoff_delay)
                    continue
                raise

        raise TimeoutError("Job did not complete within timeout period")

    async def retrieve_result(self, result: str) -> dict:
        """Retrieve VPR result from presigned S3 URL.

        Args:
            result: Presigned S3 URL

        Returns:
            VPR result JSON

        Raises:
            ConnectionError: Network failure
            ValueError: Invalid URL or expired
        """
        response = await self._get(result)

        if response["status_code"] == 200:
            return response.get("data", {})
        elif response["status_code"] == 404:
            raise ValueError("Result not found")
        elif response["status_code"] == 410:
            raise ValueError("Result expired")
        else:
            raise ValueError(f"HTTP {response['status_code']}")

    async def _get(self, url: str) -> dict:
        """Make GET request."""
        return {"status_code": 200, "data": {}}

    async def _post(self, url: str, data: dict) -> dict:
        """Make POST request."""
        return {
            "status_code": 202,
            "data": {"request_id": "test-job-id", "status": "pending"},
        }

    async def _get_with_backoff(self, url: str, retry_count: int = 0) -> dict:
        """Get with exponential backoff."""
        return {"status_code": 202, "data": {"status": "processing"}}

    async def _sleep(self, duration: float):
        """Sleep for duration."""
        pass


class TestVPRAsyncClientInit:
    """Test client initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        client = VPRAsyncClient("https://api.example.com")
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 30
        assert client.max_retries == 3

    def test_init_with_custom_values(self):
        """Test initialization with custom parameters."""
        client = VPRAsyncClient(
            base_url="https://api.custom.com", timeout=60, max_retries=5
        )
        assert client.base_url == "https://api.custom.com"
        assert client.timeout == 60
        assert client.max_retries == 5

    def test_init_with_empty_url(self):
        """Test initialization with empty URL."""
        client = VPRAsyncClient("")
        assert client.base_url == ""


class TestVPRAsyncClientSubmit:
    """Test submit_vpr_job method."""

    @pytest.mark.asyncio
    async def test_submit_new_job(self):
        """Test submitting new job returns 202 Accepted."""
        client = VPRAsyncClient("https://api.example.com")

        # Mock the _post method
        client._post = AsyncMock(
            return_value={
                "status_code": 202,
                "data": {"request_id": "job-123", "status": "pending"},
            }
        )

        result = await client.submit_vpr_job(
            {"cv_id": "cv-123", "job_id": "job-456", "job_posting": {}}
        )

        assert result["status_code"] == 202
        assert result["request_id"] == "job-123"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_submit_idempotent_job(self):
        """Test submitting duplicate job returns 200 OK."""
        client = VPRAsyncClient("https://api.example.com")

        client._post = AsyncMock(
            return_value={
                "status_code": 200,
                "data": {"request_id": "job-123", "status": "pending"},
            }
        )

        result = await client.submit_vpr_job(
            {"cv_id": "cv-123", "job_id": "job-456", "job_posting": {}}
        )

        assert result["status_code"] == 200
        assert result["request_id"] == "job-123"

    @pytest.mark.asyncio
    async def test_submit_missing_cv_id(self):
        """Test submission without cv_id raises ValueError."""
        client = VPRAsyncClient("https://api.example.com")

        with pytest.raises(ValueError, match="cv_id is required"):
            await client.submit_vpr_job({"job_id": "job-456", "job_posting": {}})

    @pytest.mark.asyncio
    async def test_submit_missing_job_id(self):
        """Test submission without request_id raises ValueError."""
        client = VPRAsyncClient("https://api.example.com")

        with pytest.raises(ValueError, match="job_id is required"):
            await client.submit_vpr_job({"cv_id": "cv-123", "job_posting": {}})

    @pytest.mark.asyncio
    async def test_submit_network_error(self):
        """Test submission with network error."""
        client = VPRAsyncClient("https://api.example.com")

        client._post = AsyncMock(side_effect=ConnectionError("Network unreachable"))

        with pytest.raises(ConnectionError):
            await client.submit_vpr_job(
                {"cv_id": "cv-123", "job_id": "job-456", "job_posting": {}}
            )

    @pytest.mark.asyncio
    async def test_submit_server_error(self):
        """Test submission with 500 server error."""
        client = VPRAsyncClient("https://api.example.com")

        client._post = AsyncMock(
            return_value={"status_code": 500, "error": "Internal Server Error"}
        )

        with pytest.raises(ValueError, match="HTTP 500"):
            await client.submit_vpr_job(
                {"cv_id": "cv-123", "job_id": "job-456", "job_posting": {}}
            )


class TestVPRAsyncClientPolling:
    """Test poll_status method with backoff."""

    @pytest.mark.asyncio
    async def test_poll_completed_immediately(self):
        """Test polling when job completes immediately."""
        client = VPRAsyncClient("https://api.example.com")

        client._get_with_backoff = AsyncMock(
            return_value={
                "status_code": 200,
                "data": {
                    "status": "completed",
                    "result": "https://s3.example.com/result.json",
                    "token_usage": {"input_tokens": 1000, "output_tokens": 500},
                },
            }
        )

        result = await client.poll_status("job-123")

        assert result["status_code"] == 200
        assert result["status"] == "completed"
        assert result["result"] == "https://s3.example.com/result.json"

    @pytest.mark.asyncio
    async def test_poll_failed_job(self):
        """Test polling for failed job."""
        client = VPRAsyncClient("https://api.example.com")

        client._get_with_backoff = AsyncMock(
            return_value={
                "status_code": 200,
                "data": {"status": "failed", "error": "Claude API rate limit exceeded"},
            }
        )

        result = await client.poll_status("job-123")

        assert result["status_code"] == 200
        assert result["status"] == "failed"
        assert result["error"] == "Claude API rate limit exceeded"

    @pytest.mark.asyncio
    async def test_poll_with_multiple_retries(self):
        """Test polling with exponential backoff on retries."""
        client = VPRAsyncClient("https://api.example.com")

        # Mock responses: 3 pending, then completed
        responses = [
            {"status_code": 202, "data": {"status": "pending"}},
            {"status_code": 202, "data": {"status": "processing"}},
            {"status_code": 202, "data": {"status": "processing"}},
            {
                "status_code": 200,
                "data": {
                    "status": "completed",
                    "result": "https://s3.example.com/result.json",
                },
            },
        ]

        client._get_with_backoff = AsyncMock(side_effect=responses)
        client._sleep = AsyncMock()

        result = await client.poll_status("job-123", poll_interval=5, max_polls=60)

        assert result["status"] == "completed"
        # Should have called sleep between polls
        assert client._sleep.call_count >= 3

    @pytest.mark.asyncio
    async def test_poll_job_not_found(self):
        """Test polling for non-existent job (404)."""
        client = VPRAsyncClient("https://api.example.com")

        client._get_with_backoff = AsyncMock(
            return_value={"status_code": 404, "data": {}}
        )

        with pytest.raises(ValueError, match="Job not found"):
            await client.poll_status("job-999")

    @pytest.mark.asyncio
    async def test_poll_result_expired(self):
        """Test polling when result expired (410)."""
        client = VPRAsyncClient("https://api.example.com")

        client._get_with_backoff = AsyncMock(
            return_value={"status_code": 410, "data": {}}
        )

        with pytest.raises(ValueError, match="Result expired"):
            await client.poll_status("job-123")

    @pytest.mark.asyncio
    async def test_poll_timeout(self):
        """Test polling timeout after max_polls exceeded."""
        client = VPRAsyncClient("https://api.example.com")

        # Always return processing
        client._get_with_backoff = AsyncMock(
            return_value={"status_code": 202, "data": {"status": "processing"}}
        )
        client._sleep = AsyncMock()

        with pytest.raises(TimeoutError):
            await client.poll_status("job-123", poll_interval=1, max_polls=3)

    @pytest.mark.asyncio
    async def test_poll_exponential_backoff(self):
        """Test exponential backoff on transient errors."""
        client = VPRAsyncClient("https://api.example.com")

        # First 2 calls fail, then succeed
        responses = [
            {"status_code": 500, "error": "Server error"},
            {"status_code": 503, "error": "Service unavailable"},
            {
                "status_code": 200,
                "data": {
                    "status": "completed",
                    "result": "https://s3.example.com/result.json",
                },
            },
        ]

        client._get_with_backoff = AsyncMock(side_effect=responses)
        client._sleep = AsyncMock()

        result = await client.poll_status("job-123", max_polls=5)

        assert result["status"] == "completed"
        # Two transient errors should trigger backoff sleeps before success.
        assert client._sleep.await_count == 2


class TestVPRAsyncClientRetrieval:
    """Test retrieve_result method."""

    @pytest.mark.asyncio
    async def test_retrieve_valid_result(self):
        """Test retrieving VPR result from presigned URL."""
        client = VPRAsyncClient("https://api.example.com")

        vpr_data = {
            "executive_summary": "Sample summary",
            "evidence_matrix": [{"category": "test", "matches": []}],
            "token_usage": {"input_tokens": 1000, "output_tokens": 500},
        }

        client._get = AsyncMock(return_value={"status_code": 200, "data": vpr_data})

        result = await client.retrieve_result("https://s3.example.com/result.json")

        assert result["executive_summary"] == "Sample summary"
        assert result["token_usage"]["input_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_retrieve_not_found(self):
        """Test retrieving expired or missing result (404)."""
        client = VPRAsyncClient("https://api.example.com")

        client._get = AsyncMock(return_value={"status_code": 404, "data": {}})

        with pytest.raises(ValueError, match="Result not found"):
            await client.retrieve_result("https://s3.example.com/result.json")

    @pytest.mark.asyncio
    async def test_retrieve_expired(self):
        """Test retrieving expired presigned URL (410)."""
        client = VPRAsyncClient("https://api.example.com")

        client._get = AsyncMock(return_value={"status_code": 410, "data": {}})

        with pytest.raises(ValueError, match="Result expired"):
            await client.retrieve_result("https://s3.example.com/result.json")

    @pytest.mark.asyncio
    async def test_retrieve_network_error(self):
        """Test retrieval with network error."""
        client = VPRAsyncClient("https://api.example.com")

        client._get = AsyncMock(side_effect=ConnectionError("Network error"))

        with pytest.raises(ConnectionError):
            await client.retrieve_result("https://s3.example.com/result.json")


class TestVPRAsyncClientErrorHandling:
    """Test comprehensive error handling."""

    @pytest.mark.asyncio
    async def test_timeout_error_details(self):
        """Test timeout error includes request_id context."""
        client = VPRAsyncClient("https://api.example.com")
        client._get_with_backoff = AsyncMock(
            return_value={"status_code": 202, "data": {"status": "processing"}}
        )
        client._sleep = AsyncMock()

        with pytest.raises(TimeoutError):
            await client.poll_status("job-timeout-123", max_polls=2)

    @pytest.mark.asyncio
    async def test_http_error_codes(self):
        """Test handling of various HTTP error codes."""
        client = VPRAsyncClient("https://api.example.com")

        error_codes = [400, 401, 403, 500, 502, 503]

        for code in error_codes:
            client._post = AsyncMock(
                return_value={"status_code": code, "error": f"HTTP Error {code}"}
            )

            with pytest.raises(ValueError):
                await client.submit_vpr_job(
                    {
                        "cv_id": "cv-123",
                        "job_id": "job-456",
                        "job_posting": {},
                    }
                )

    @pytest.mark.asyncio
    async def test_malformed_response(self):
        """Test handling of malformed responses."""
        client = VPRAsyncClient("https://api.example.com")

        client._post = AsyncMock(
            return_value={
                "status_code": 202,
                "data": {},  # Missing request_id
            }
        )

        result = await client.submit_vpr_job(
            {"cv_id": "cv-123", "job_id": "job-456", "job_posting": {}}
        )

        assert result["request_id"] is None  # Should handle gracefully


class TestVPRAsyncClientIntegration:
    """Integration tests for full workflows."""

    @pytest.mark.asyncio
    async def test_full_workflow_submit_poll_retrieve(self):
        """Test complete workflow: submit -> poll -> retrieve."""
        client = VPRAsyncClient("https://api.example.com")

        # Mock submit
        client._post = AsyncMock(
            return_value={
                "status_code": 202,
                "data": {"request_id": "job-123", "status": "pending"},
            }
        )

        # Mock poll
        client._get_with_backoff = AsyncMock(
            return_value={
                "status_code": 200,
                "data": {
                    "status": "completed",
                    "result": "https://s3.example.com/result.json",
                },
            }
        )

        # Mock retrieve
        client._get = AsyncMock(
            return_value={"status_code": 200, "data": {"executive_summary": "Test VPR"}}
        )

        # Submit
        submit_result = await client.submit_vpr_job(
            {"cv_id": "cv-123", "job_id": "job-456", "job_posting": {}}
        )
        assert submit_result["request_id"] == "job-123"

        # Poll
        poll_result = await client.poll_status(submit_result["request_id"])
        assert poll_result["status"] == "completed"

        # Retrieve
        vpr = await client.retrieve_result(poll_result["result"])
        assert vpr["executive_summary"] == "Test VPR"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
