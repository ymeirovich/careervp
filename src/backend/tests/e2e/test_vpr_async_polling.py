"""E2E-style tests for VPR async submit and polling lifecycle."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from careervp.models.result import Result, ResultCode


class InMemoryJobsRepository:
    """In-memory repository used to simulate async VPR lifecycle transitions."""

    def __init__(self) -> None:
        self.jobs: dict[str, dict[str, Any]] = {}
        self.poll_counts: dict[str, int] = {}

    def create_job(self, job_data: dict[str, Any]) -> Result[dict[str, Any]]:
        job_id = str(job_data['job_id'])
        record = dict(job_data)
        record.setdefault('status', 'PENDING')
        record.setdefault('created_at', datetime.now(timezone.utc).isoformat())
        record.setdefault('_processing_after', 2)
        record.setdefault('_complete_after', 4)
        self.jobs[job_id] = record
        return Result(success=True, data=record, code=ResultCode.SUCCESS)

    def get_job_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        for job in self.jobs.values():
            if str(job.get('idempotency_key', '')) == idempotency_key:
                return dict(job)
        return None

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None

        if not bool(job.get('_disable_auto_progress')):
            self._auto_progress(job_id, job)

        return dict(job)

    def _auto_progress(self, job_id: str, job: dict[str, Any]) -> None:
        poll_count = self.poll_counts.get(job_id, 0) + 1
        self.poll_counts[job_id] = poll_count

        status = str(job.get('status', 'PENDING')).upper()
        processing_after = int(job.get('_processing_after', 2))
        complete_after = int(job.get('_complete_after', 4))

        if status == 'PENDING' and poll_count >= processing_after:
            job['status'] = 'PROCESSING'
            job['started_at'] = datetime.now(timezone.utc).isoformat()
            return

        if status == 'PROCESSING' and poll_count >= complete_after:
            job['status'] = 'COMPLETED'
            job['completed_at'] = datetime.now(timezone.utc).isoformat()
            job.setdefault(
                'result',
                {
                    'uvp': 'Test UVP',
                    'strategic_narrative': 'Test strategic narrative',
                },
            )


def _lambda_context() -> Any:
    context = MagicMock()
    context.function_name = 'test-vpr-async'
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-vpr-async'
    context.aws_request_id = 'req-vpr-async-1'
    return context


def _submit_event(user_id: str = 'user-123') -> dict[str, Any]:
    return {
        'httpMethod': 'POST',
        'path': '/vpr/generate',
        'headers': {'Content-Type': 'application/json'},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
        'body': json.dumps(
            {
                'cv_id': 'cv-123',
                'job_id': 'job-123',
                'gap_response_ids': ['gap-1'],
                'options': {'include_company_research': True, 'tone': 'professional'},
            }
        ),
    }


def _status_event(vpr_id: str, user_id: str = 'user-123') -> dict[str, Any]:
    return {
        'httpMethod': 'GET',
        'path': f'/vpr/{vpr_id}',
        'pathParameters': {'vprId': vpr_id},
        'headers': {'Content-Type': 'application/json'},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
    }


def _poll_until_terminal(
    status_handler: Any,
    event: dict[str, Any],
    *,
    max_wait_seconds: float,
    interval_seconds: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    start = time.monotonic()
    while time.monotonic() - start < max_wait_seconds:
        response = status_handler(event, _lambda_context())
        body = json.loads(response['body'])
        if body.get('status') in {'completed', 'failed'}:
            return response, body
        time.sleep(interval_seconds)

    raise TimeoutError(f'Polling exceeded {max_wait_seconds:.2f}s without terminal status')


@pytest.fixture(autouse=True)
def vpr_async_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-vpr-async-e2e-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('POWERTOOLS_TRACE_DISABLED', 'true')
    monkeypatch.setenv('SQS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue')

    import careervp.handlers.vpr_status_handler as vpr_status_handler
    import careervp.handlers.vpr_submit_handler as vpr_submit_handler

    vpr_submit_handler._auth_service = None
    vpr_status_handler._auth_service = None


def test_submit_vpr_job_returns_202() -> None:
    from careervp.handlers.vpr_submit_handler import lambda_handler as submit_handler

    fake_repo = InMemoryJobsRepository()

    with (
        patch('careervp.handlers.vpr_submit_handler.JobsRepository', return_value=fake_repo),
        patch('careervp.handlers.vpr_submit_handler.uuid.uuid4', return_value='vpr-job-202'),
        patch('careervp.handlers.vpr_submit_handler.sqs.send_message', return_value={'MessageId': 'msg-1'}),
    ):
        response = submit_handler(_submit_event(), _lambda_context())

    assert response['statusCode'] == 202
    body = json.loads(response['body'])
    assert body['request_id'] == 'vpr-job-202'
    assert body['job_id'] == 'vpr-job-202'
    assert body['status'] == 'processing'


def test_poll_vpr_status_pending_to_completed() -> None:
    from careervp.handlers.vpr_status_handler import lambda_handler as status_handler
    from careervp.handlers.vpr_submit_handler import lambda_handler as submit_handler

    fake_repo = InMemoryJobsRepository()

    with (
        patch('careervp.handlers.vpr_submit_handler.JobsRepository', return_value=fake_repo),
        patch('careervp.handlers.vpr_status_handler.JobsRepository', return_value=fake_repo),
        patch('careervp.handlers.vpr_submit_handler.uuid.uuid4', return_value='vpr-job-lifecycle'),
        patch('careervp.handlers.vpr_submit_handler.sqs.send_message', return_value={'MessageId': 'msg-2'}),
    ):
        submit_response = submit_handler(_submit_event(), _lambda_context())
        assert submit_response['statusCode'] == 202

        poll_event = _status_event('vpr-job-lifecycle')
        statuses: list[str] = []
        for _ in range(8):
            poll_response = status_handler(poll_event, _lambda_context())
            assert poll_response['statusCode'] == 200
            poll_body = json.loads(poll_response['body'])
            statuses.append(str(poll_body['status']))
            if poll_body['status'] == 'completed':
                assert 'result' in poll_body
                break

        assert statuses[0] == 'pending'
        assert 'processing' in statuses
        assert statuses[-1] == 'completed'


def test_poll_vpr_status_handles_errors() -> None:
    from careervp.handlers.vpr_status_handler import lambda_handler as status_handler
    from careervp.handlers.vpr_submit_handler import lambda_handler as submit_handler

    fake_repo = InMemoryJobsRepository()

    with (
        patch('careervp.handlers.vpr_submit_handler.JobsRepository', return_value=fake_repo),
        patch('careervp.handlers.vpr_status_handler.JobsRepository', return_value=fake_repo),
        patch('careervp.handlers.vpr_submit_handler.uuid.uuid4', return_value='vpr-job-failed'),
        patch('careervp.handlers.vpr_submit_handler.sqs.send_message', return_value={'MessageId': 'msg-3'}),
    ):
        submit_response = submit_handler(_submit_event(), _lambda_context())
        assert submit_response['statusCode'] == 202

        # Force job into FAILED state to validate error handling contract.
        failed_job = fake_repo.jobs['vpr-job-failed']
        failed_job['status'] = 'FAILED'
        failed_job['error'] = 'Synthetic worker failure'
        failed_job['completed_at'] = datetime.now(timezone.utc).isoformat()

        poll_response = status_handler(_status_event('vpr-job-failed'), _lambda_context())

    assert poll_response['statusCode'] == 200
    body = json.loads(poll_response['body'])
    assert body['status'] == 'failed'
    assert body['error'] == 'Synthetic worker failure'


def test_vpr_timeout_handling() -> None:
    from careervp.handlers.vpr_status_handler import lambda_handler as status_handler
    from careervp.handlers.vpr_submit_handler import lambda_handler as submit_handler

    fake_repo = InMemoryJobsRepository()

    with (
        patch('careervp.handlers.vpr_submit_handler.JobsRepository', return_value=fake_repo),
        patch('careervp.handlers.vpr_status_handler.JobsRepository', return_value=fake_repo),
        patch('careervp.handlers.vpr_submit_handler.uuid.uuid4', return_value='vpr-job-timeout'),
        patch('careervp.handlers.vpr_submit_handler.sqs.send_message', return_value={'MessageId': 'msg-4'}),
    ):
        submit_response = submit_handler(_submit_event(), _lambda_context())
        assert submit_response['statusCode'] == 202

        # Keep this job non-terminal to validate timeout handling in poller.
        timeout_job = fake_repo.jobs['vpr-job-timeout']
        timeout_job['_disable_auto_progress'] = True
        timeout_job['status'] = 'PENDING'

        with pytest.raises(TimeoutError):
            _poll_until_terminal(
                status_handler,
                _status_event('vpr-job-timeout'),
                max_wait_seconds=0.05,
                interval_seconds=0.01,
            )
