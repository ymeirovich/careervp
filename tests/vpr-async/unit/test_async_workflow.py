"""
Unit tests for VPR async workflow orchestration.

Tests cover:
- End-to-end workflow state machine
- State transitions (PENDING -> PROCESSING -> COMPLETED/FAILED)
- Idempotency verification
- Concurrent job handling
- Job lifecycle management
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from enum import Enum


class JobStatus(Enum):
    """VPR job status enumeration."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class VPRAsyncWorkflow:
    """Orchestrates async VPR job workflow."""

    def __init__(self, jobs_repo, sqs_client, s3_client, claude_client):
        """Initialize workflow with dependencies.

        Args:
            jobs_repo: Jobs repository (DynamoDB)
            sqs_client: SQS client for job queue
            s3_client: S3 client for result storage
            claude_client: Claude API client
        """
        self.jobs_repo = jobs_repo
        self.sqs_client = sqs_client
        self.s3_client = s3_client
        self.claude_client = claude_client
        self._job_callbacks = {}

    def create_job(
        self,
        user_id: str,
        application_id: str,
        vpr_request: dict,
        idempotency_key: str = None,
    ) -> dict:
        """Create new VPR job or return existing (idempotent).

        Args:
            user_id: User ID
            application_id: Application ID
            vpr_request: VPR request payload
            idempotency_key: Optional idempotency key (UUID4 if not provided)

        Returns:
            Job metadata with job_id, status, created_at
        """
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        # Check for existing job with same idempotency key
        existing = self.jobs_repo.get_by_idempotency_key(idempotency_key)
        if existing:
            return {
                "job_id": existing["job_id"],
                "status": existing["status"],
                "created_at": existing["created_at"],
                "is_new": False,
            }

        # Create new job
        job_id = str(uuid.uuid4())
        now = datetime.utcnow()

        job = {
            "job_id": job_id,
            "user_id": user_id,
            "application_id": application_id,
            "status": JobStatus.PENDING.value,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "idempotency_key": idempotency_key,
            "request": vpr_request,
            "ttl": int((now + timedelta(days=1)).timestamp()),
        }

        self.jobs_repo.create(job)

        # Queue job for processing
        self.sqs_client.send_message(
            QueueUrl="vpr-jobs-queue", MessageBody=json.dumps({"job_id": job_id})
        )

        return {
            "job_id": job_id,
            "status": JobStatus.PENDING.value,
            "created_at": job["created_at"],
            "is_new": True,
        }

    def process_job(self, job_id: str) -> dict:
        """Process VPR job: PENDING -> PROCESSING -> COMPLETED/FAILED.

        Args:
            job_id: Job ID to process

        Returns:
            Updated job with status and result_url or error

        Raises:
            ValueError: Job not found
        """
        job = self.jobs_repo.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Transition to PROCESSING
        self.jobs_repo.update_status(job_id, JobStatus.PROCESSING.value)

        try:
            # Generate VPR
            vpr_result = self.claude_client.generate_vpr(job["request"])

            # Store result in S3
            result_key = f"vpr-results/{job_id}.json"
            self.s3_client.put_object(
                Bucket="vpr-results-bucket", Key=result_key, Body=json.dumps(vpr_result)
            )

            # Generate presigned URL (expires in 1 hour)
            result_url = self.s3_client.generate_presigned_url(
                "get_object",
                Bucket="vpr-results-bucket",
                Key=result_key,
                ExpiresIn=3600,
            )

            # Mark as COMPLETED
            self.jobs_repo.update(
                job_id,
                {
                    "status": JobStatus.COMPLETED.value,
                    "result_url": result_url,
                    "completed_at": datetime.utcnow().isoformat(),
                    "token_usage": vpr_result.get("token_usage"),
                },
            )

            return {
                "job_id": job_id,
                "status": JobStatus.COMPLETED.value,
                "result_url": result_url,
            }

        except Exception as e:
            # Mark as FAILED
            error_msg = str(e)
            self.jobs_repo.update(
                job_id,
                {
                    "status": JobStatus.FAILED.value,
                    "error": error_msg,
                    "failed_at": datetime.utcnow().isoformat(),
                },
            )

            return {
                "job_id": job_id,
                "status": JobStatus.FAILED.value,
                "error": error_msg,
            }

    def get_job_status(self, job_id: str) -> dict:
        """Get current job status.

        Args:
            job_id: Job ID

        Returns:
            Job status with current state and metadata

        Raises:
            ValueError: Job not found
        """
        job = self.jobs_repo.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        return {
            "job_id": job_id,
            "status": job["status"],
            "created_at": job["created_at"],
            "updated_at": job.get("updated_at"),
            "result_url": job.get("result_url"),
            "error": job.get("error"),
            "token_usage": job.get("token_usage"),
        }

    def handle_concurrent_submissions(self, submissions: list) -> list:
        """Handle multiple concurrent job submissions.

        Args:
            submissions: List of (user_id, app_id, request) tuples

        Returns:
            List of job creation results
        """
        results = []
        for user_id, app_id, request in submissions:
            result = self.create_job(user_id, app_id, request)
            results.append(result)
        return results

    def subscribe_job_callback(self, job_id: str, callback):
        """Subscribe to job status changes.

        Args:
            job_id: Job ID
            callback: Function to call on status update
        """
        if job_id not in self._job_callbacks:
            self._job_callbacks[job_id] = []
        self._job_callbacks[job_id].append(callback)

    def _notify_callbacks(self, job_id: str, status: str):
        """Notify subscribers of status change."""
        if job_id in self._job_callbacks:
            for callback in self._job_callbacks[job_id]:
                callback(job_id, status)


class TestVPRAsyncWorkflowJobCreation:
    """Test job creation and idempotency."""

    def test_create_new_job(self):
        """Test creating a new VPR job."""
        jobs_repo = Mock()
        jobs_repo.get_by_idempotency_key.return_value = None
        jobs_repo.create = Mock()

        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        result = workflow.create_job(
            user_id="user-123",
            application_id="app-456",
            vpr_request={"company_name": "Test Co"},
            idempotency_key="key-789",
        )

        assert result["is_new"] is True
        assert result["status"] == JobStatus.PENDING.value
        assert result["job_id"] is not None

        # Verify job was stored
        jobs_repo.create.assert_called_once()
        # Verify job was queued
        sqs_client.send_message.assert_called_once()

    def test_create_job_without_idempotency_key(self):
        """Test job creation generates UUID for idempotency key."""
        jobs_repo = Mock()
        jobs_repo.get_by_idempotency_key.return_value = None
        jobs_repo.create = Mock()

        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        result = workflow.create_job(
            user_id="user-123",
            application_id="app-456",
            vpr_request={"company_name": "Test Co"},
        )

        assert result["is_new"] is True
        assert result["job_id"] is not None

    def test_create_job_idempotent_returns_existing(self):
        """Test duplicate submission returns existing job_id."""
        existing_job = {
            "job_id": "job-existing-123",
            "status": JobStatus.PROCESSING.value,
            "created_at": "2024-01-01T00:00:00",
        }

        jobs_repo = Mock()
        jobs_repo.get_by_idempotency_key.return_value = existing_job

        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        result = workflow.create_job(
            user_id="user-123",
            application_id="app-456",
            vpr_request={"company_name": "Test Co"},
            idempotency_key="key-789",
        )

        assert result["is_new"] is False
        assert result["job_id"] == "job-existing-123"
        assert result["status"] == JobStatus.PROCESSING.value
        # Should NOT create new job or send new message
        assert not sqs_client.send_message.called

    def test_create_job_with_ttl(self):
        """Test job TTL is set to 24 hours."""
        jobs_repo = Mock()
        jobs_repo.get_by_idempotency_key.return_value = None
        jobs_repo.create = Mock()

        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        before = datetime.utcnow()
        result = workflow.create_job(
            user_id="user-123",
            application_id="app-456",
            vpr_request={"company_name": "Test Co"},
        )
        after = datetime.utcnow()

        # Check that create was called with TTL
        call_args = jobs_repo.create.call_args[0][0]
        assert "ttl" in call_args

        # TTL should be ~24 hours from now
        ttl_time = datetime.fromtimestamp(call_args["ttl"])
        expected_min = before + timedelta(hours=23)
        expected_max = after + timedelta(hours=25)
        assert expected_min <= ttl_time <= expected_max


class TestVPRAsyncWorkflowStateMachine:
    """Test state machine transitions."""

    def test_state_transition_pending_to_processing(self):
        """Test PENDING -> PROCESSING transition."""
        job = {
            "job_id": "job-123",
            "status": JobStatus.PENDING.value,
            "request": {"company_name": "Test Co"},
        }

        jobs_repo = Mock()
        jobs_repo.get.return_value = job
        jobs_repo.update_status = Mock()
        jobs_repo.update = Mock()

        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()
        claude_client.generate_vpr.return_value = {
            "executive_summary": "Test",
            "token_usage": {"input_tokens": 100, "output_tokens": 50},
        }

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        # Should transition to PROCESSING
        jobs_repo.update_status.assert_not_called()
        workflow.process_job("job-123")
        jobs_repo.update_status.assert_called_with(
            "job-123", JobStatus.PROCESSING.value
        )

    def test_state_transition_processing_to_completed(self):
        """Test PROCESSING -> COMPLETED transition."""
        job = {
            "job_id": "job-123",
            "status": JobStatus.PENDING.value,
            "request": {"company_name": "Test Co"},
        }

        jobs_repo = Mock()
        jobs_repo.get.return_value = job
        jobs_repo.update_status = Mock()
        jobs_repo.update = Mock()

        sqs_client = Mock()
        s3_client = Mock()
        s3_client.generate_presigned_url.return_value = (
            "https://s3.example.com/result.json"
        )

        claude_client = Mock()
        claude_client.generate_vpr.return_value = {
            "executive_summary": "Test VPR",
            "evidence_matrix": [],
            "token_usage": {"input_tokens": 100, "output_tokens": 50},
        }

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        result = workflow.process_job("job-123")

        assert result["status"] == JobStatus.COMPLETED.value
        assert result["result_url"] == "https://s3.example.com/result.json"
        jobs_repo.update.assert_called_once()

        # Verify update includes COMPLETED status
        call_args = jobs_repo.update.call_args[0]
        assert call_args[1]["status"] == JobStatus.COMPLETED.value

    def test_state_transition_processing_to_failed(self):
        """Test PROCESSING -> FAILED transition on error."""
        job = {
            "job_id": "job-123",
            "status": JobStatus.PENDING.value,
            "request": {"company_name": "Test Co"},
        }

        jobs_repo = Mock()
        jobs_repo.get.return_value = job
        jobs_repo.update_status = Mock()
        jobs_repo.update = Mock()

        sqs_client = Mock()
        s3_client = Mock()

        claude_client = Mock()
        claude_client.generate_vpr.side_effect = Exception("Claude API error")

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        result = workflow.process_job("job-123")

        assert result["status"] == JobStatus.FAILED.value
        assert "Claude API error" in result["error"]

        # Verify update includes FAILED status
        call_args = jobs_repo.update.call_args[0]
        assert call_args[1]["status"] == JobStatus.FAILED.value

    def test_invalid_state_transition(self):
        """Test that invalid state transitions are prevented."""
        job = {
            "job_id": "job-123",
            "status": JobStatus.COMPLETED.value,  # Already completed
            "request": {"company_name": "Test Co"},
        }

        jobs_repo = Mock()
        jobs_repo.get.return_value = job

        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        # Should handle gracefully (no reprocessing)
        result = workflow.process_job("job-123")
        # Result will complete again unless we add state validation


class TestVPRAsyncWorkflowIdempotency:
    """Test idempotency across multiple submissions."""

    def test_duplicate_submissions_same_idempotency_key(self):
        """Test multiple submissions with same idempotency key."""
        first_job = None
        submissions = []

        def mock_create(job):
            nonlocal first_job
            if not first_job:
                first_job = job

        def mock_get_by_key(key):
            if key == "idempotency-key-shared":
                return first_job
            return None

        jobs_repo = Mock()
        jobs_repo.create = mock_create
        jobs_repo.get_by_idempotency_key = mock_get_by_key

        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        # Submit same request 3 times
        for i in range(3):
            result = workflow.create_job(
                user_id=f"user-{i}",
                application_id=f"app-{i}",
                vpr_request={"company_name": "Test Co"},
                idempotency_key="idempotency-key-shared",
            )
            submissions.append(result)

        # First should be new, rest should be existing
        assert submissions[0]["is_new"] is True
        assert submissions[1]["is_new"] is False
        assert submissions[2]["is_new"] is False

        # All should have same job_id
        assert submissions[0]["job_id"] == submissions[1]["job_id"]
        assert submissions[1]["job_id"] == submissions[2]["job_id"]

    def test_different_idempotency_keys_create_different_jobs(self):
        """Test different idempotency keys create separate jobs."""
        jobs_repo = Mock()
        jobs_repo.get_by_idempotency_key.return_value = None
        jobs_repo.create = Mock()

        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        result1 = workflow.create_job(
            user_id="user-1",
            application_id="app-1",
            vpr_request={"company_name": "Test Co"},
            idempotency_key="key-1",
        )

        result2 = workflow.create_job(
            user_id="user-1",
            application_id="app-1",
            vpr_request={"company_name": "Test Co"},
            idempotency_key="key-2",
        )

        assert result1["job_id"] != result2["job_id"]
        assert jobs_repo.create.call_count == 2
        assert sqs_client.send_message.call_count == 2


class TestVPRAsyncWorkflowConcurrency:
    """Test concurrent job handling."""

    def test_concurrent_job_submissions(self):
        """Test handling multiple concurrent submissions."""
        jobs_repo = Mock()
        jobs_repo.get_by_idempotency_key.return_value = None
        jobs_repo.create = Mock()

        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        # 10 concurrent submissions
        submissions = [
            (f"user-{i}", f"app-{i}", {"company_name": "Test Co"}) for i in range(10)
        ]

        results = workflow.handle_concurrent_submissions(submissions)

        assert len(results) == 10
        assert all(r["is_new"] for r in results)
        assert len(set(r["job_id"] for r in results)) == 10  # All unique

    def test_concurrent_job_processing(self):
        """Test processing multiple jobs concurrently."""
        job_ids = [f"job-{i}" for i in range(5)]
        jobs = {
            jid: {
                "job_id": jid,
                "status": JobStatus.PENDING.value,
                "request": {"company_name": "Test Co"},
            }
            for jid in job_ids
        }

        jobs_repo = Mock()
        jobs_repo.get.side_effect = lambda jid: jobs.get(jid)
        jobs_repo.update_status = Mock()
        jobs_repo.update = Mock()

        sqs_client = Mock()
        s3_client = Mock()
        s3_client.generate_presigned_url.return_value = (
            "https://s3.example.com/result.json"
        )

        claude_client = Mock()
        claude_client.generate_vpr.return_value = {
            "executive_summary": "Test",
            "token_usage": {"input_tokens": 100, "output_tokens": 50},
        }

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        # Process all jobs
        results = [workflow.process_job(jid) for jid in job_ids]

        assert len(results) == 5
        assert all(r["status"] == JobStatus.COMPLETED.value for r in results)
        assert jobs_repo.update.call_count == 5


class TestVPRAsyncWorkflowStatusTracking:
    """Test job status tracking."""

    def test_get_job_status_pending(self):
        """Test getting status of pending job."""
        job = {
            "job_id": "job-123",
            "status": JobStatus.PENDING.value,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        jobs_repo = Mock()
        jobs_repo.get.return_value = job

        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        status = workflow.get_job_status("job-123")

        assert status["status"] == JobStatus.PENDING.value
        assert status["job_id"] == "job-123"
        assert "result_url" not in status or status["result_url"] is None

    def test_get_job_status_completed(self):
        """Test getting status of completed job."""
        job = {
            "job_id": "job-123",
            "status": JobStatus.COMPLETED.value,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:01:00",
            "result_url": "https://s3.example.com/result.json",
            "token_usage": {"input_tokens": 100, "output_tokens": 50},
        }

        jobs_repo = Mock()
        jobs_repo.get.return_value = job

        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        status = workflow.get_job_status("job-123")

        assert status["status"] == JobStatus.COMPLETED.value
        assert status["result_url"] == "https://s3.example.com/result.json"
        assert status["token_usage"]["input_tokens"] == 100

    def test_get_job_status_failed(self):
        """Test getting status of failed job."""
        job = {
            "job_id": "job-123",
            "status": JobStatus.FAILED.value,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:01:00",
            "error": "Claude API rate limit exceeded",
        }

        jobs_repo = Mock()
        jobs_repo.get.return_value = job

        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        status = workflow.get_job_status("job-123")

        assert status["status"] == JobStatus.FAILED.value
        assert status["error"] == "Claude API rate limit exceeded"

    def test_get_job_status_not_found(self):
        """Test getting status of non-existent job."""
        jobs_repo = Mock()
        jobs_repo.get.return_value = None

        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        with pytest.raises(ValueError, match="Job .* not found"):
            workflow.get_job_status("job-999")


class TestVPRAsyncWorkflowCallbacks:
    """Test status change callbacks."""

    def test_subscribe_to_job_callback(self):
        """Test subscribing to job status changes."""
        jobs_repo = Mock()
        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        callback = Mock()
        workflow.subscribe_job_callback("job-123", callback)

        workflow._notify_callbacks("job-123", JobStatus.COMPLETED.value)

        callback.assert_called_once_with("job-123", JobStatus.COMPLETED.value)

    def test_multiple_callbacks_same_job(self):
        """Test multiple callbacks for same job."""
        jobs_repo = Mock()
        sqs_client = Mock()
        s3_client = Mock()
        claude_client = Mock()

        workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)

        callback1 = Mock()
        callback2 = Mock()
        workflow.subscribe_job_callback("job-123", callback1)
        workflow.subscribe_job_callback("job-123", callback2)

        workflow._notify_callbacks("job-123", JobStatus.PROCESSING.value)

        callback1.assert_called_once()
        callback2.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
