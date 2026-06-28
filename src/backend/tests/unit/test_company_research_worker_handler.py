"""
Unit tests for careervp.handlers.company_research_worker_handler.

TEST-CHAIN-001 § unit-cr-worker: confidence gate pass/retry/hard-fail
TEST-CHAIN-001 § unit-cr-worker: idempotency key uniqueness
TEST-CHAIN-001 § unit-cr-worker: task_token signal (mock sfn client)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from careervp.handlers.company_research_worker_handler import (
    CRWorkerInput,
    RetryableError,
    _async_process_record,
    _hard_fail,
    _process_record,
    lambda_handler,
)
from careervp.models.company import CompanyResearchResult, ResearchSource
from careervp.models.result import Result, ResultCode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cr_result(
    source: ResearchSource = ResearchSource.WEBSITE_SCRAPE,
    confidence: float = 0.9,
) -> CompanyResearchResult:
    return CompanyResearchResult(
        company_name='Acme Corp',
        overview='Acme overview',
        values=['Innovation'],
        mission=None,
        strategic_priorities=[],
        recent_news=[],
        financial_summary=None,
        source=source,
        source_urls=['https://acme.com'],
        confidence_score=confidence,
        research_timestamp=datetime.now(timezone.utc),
    )


def _make_input(task_token: str | None = None) -> CRWorkerInput:
    return CRWorkerInput(
        user_id='user-1',
        job_id='job-1',
        company_name='Acme Corp',
        job_posting_url=None,
        domain='acme.com',
        task_token=task_token,
    )


def _sqs_record(
    user_id: str = 'user-1',
    job_id: str = 'job-1',
    company_name: str = 'Acme Corp',
    task_token: str | None = None,
    receive_count: int = 1,
) -> dict[str, object]:
    body = {
        'user_id': user_id,
        'job_id': job_id,
        'company_name': company_name,
        'domain': 'acme.com',
        'task_token': task_token,
    }
    return {
        'messageId': f'msg-{job_id}',
        'body': json.dumps(body),
        'attributes': {'ApproximateReceiveCount': str(receive_count)},
    }


def _sqs_event(*records: dict[str, object]) -> dict[str, object]:
    return {'Records': list(records)}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('APPLICATIONS_TABLE_NAME', 'applications-table')
    monkeypatch.setenv('KNOWLEDGE_TABLE_NAME', 'knowledge-table')
    monkeypatch.setenv('VPR_JOBS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123/vpr-jobs')
    monkeypatch.setenv('ARTIFACT_CHAIN_ENABLED', 'false')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'test')
    monkeypatch.setenv('POWERTOOLS_METRICS_NAMESPACE', 'careervp')


# ---------------------------------------------------------------------------
# _async_process_record — confidence gate
# ---------------------------------------------------------------------------


class TestConfidenceGate:
    """TEST-CHAIN-001 § unit-cr-worker: confidence gate pass/retry/hard-fail"""

    @pytest.mark.asyncio
    async def test_website_scrape_passes_gate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """WEBSITE_SCRAPE confidence 0.9 → persists CR + transitions state."""
        cr_result = _make_cr_result(ResearchSource.WEBSITE_SCRAPE, confidence=0.9)
        input_data = _make_input()

        mock_app_repo = MagicMock()
        mock_app_repo.get.return_value = {'artifact_statuses': {}}

        with (
            patch('careervp.handlers.company_research_worker_handler.research_company', new_callable=AsyncMock) as mock_research,
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=mock_app_repo),
            patch('careervp.handlers.company_research_worker_handler._persist_cr_result') as mock_persist,
            patch('careervp.handlers.company_research_worker_handler._enqueue_vpr_standalone') as mock_enqueue,
        ):
            mock_research.return_value = Result(success=True, data=cr_result, code=ResultCode.SUCCESS)
            await _async_process_record(input_data, receive_count=1)

        mock_persist.assert_called_once_with('user-1', 'job-1', cr_result)
        mock_app_repo.update_artifact_status.assert_called_once_with(
            application_id='job-1',
            user_id='user-1',
            artifact_type='company_research',
            status='completed',
            fail_if_status='cancelled',
        )
        mock_app_repo.update_state.assert_called_once_with(
            application_id='job-1',
            user_id='user-1',
            new_state='artifacts_generating',
            expected_state='cr_pending',
        )
        mock_enqueue.assert_called_once()

    @pytest.mark.asyncio
    async def test_web_search_below_threshold_retries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """WEB_SEARCH confidence 0.6 < 0.85 → raises RetryableError when receive_count < 3."""
        cr_result = _make_cr_result(ResearchSource.WEB_SEARCH, confidence=0.6)
        input_data = _make_input()

        with (
            patch('careervp.handlers.company_research_worker_handler.research_company', new_callable=AsyncMock) as mock_research,
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=MagicMock()),
        ):
            mock_research.return_value = Result(success=True, data=cr_result, code=ResultCode.SUCCESS)
            with pytest.raises(RetryableError):
                await _async_process_record(input_data, receive_count=1)

    @pytest.mark.asyncio
    async def test_web_search_below_threshold_hard_fails_at_max_retries(self) -> None:
        """WEB_SEARCH confidence 0.6 after 3 attempts → hard-fail (no exception)."""
        cr_result = _make_cr_result(ResearchSource.WEB_SEARCH, confidence=0.6)
        input_data = _make_input()

        mock_app_repo = MagicMock()

        with (
            patch('careervp.handlers.company_research_worker_handler.research_company', new_callable=AsyncMock) as mock_research,
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=mock_app_repo),
        ):
            mock_research.return_value = Result(success=True, data=cr_result, code=ResultCode.SUCCESS)
            # receive_count=3 means max retries exhausted — should NOT raise
            await _async_process_record(input_data, receive_count=3)

        mock_app_repo.set_company_research_error.assert_called_once_with(application_id='job-1', user_id='user-1', error=True)
        mock_app_repo.update_state.assert_called_once_with(
            application_id='job-1',
            user_id='user-1',
            new_state='cr_failed',
            expected_state='cr_pending',
        )

    @pytest.mark.asyncio
    async def test_llm_fallback_always_hard_fails_immediately(self) -> None:
        """LLM_FALLBACK source → hard-fail immediately, no retry regardless of receive_count."""
        cr_result = _make_cr_result(ResearchSource.LLM_FALLBACK, confidence=0.45)
        input_data = _make_input()

        mock_app_repo = MagicMock()

        with (
            patch('careervp.handlers.company_research_worker_handler.research_company', new_callable=AsyncMock) as mock_research,
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=mock_app_repo),
        ):
            mock_research.return_value = Result(success=True, data=cr_result, code=ResultCode.SUCCESS)
            # Even on first attempt (receive_count=1), LLM_FALLBACK must hard-fail
            await _async_process_record(input_data, receive_count=1)

        # Must not raise RetryableError and must set error flag
        mock_app_repo.set_company_research_error.assert_called_once_with(application_id='job-1', user_id='user-1', error=True)
        mock_app_repo.update_state.assert_called_once_with(
            application_id='job-1',
            user_id='user-1',
            new_state='cr_failed',
            expected_state='cr_pending',
        )


# ---------------------------------------------------------------------------
# Task-token / Step Functions signal
# ---------------------------------------------------------------------------


class TestTaskTokenSignal:
    """TEST-CHAIN-001 § unit-cr-worker: task_token signal (mock sfn client)"""

    @pytest.mark.asyncio
    async def test_sends_task_success_when_token_and_chain_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv('ARTIFACT_CHAIN_ENABLED', 'true')
        monkeypatch.setenv('STEP_FUNCTIONS_CHAIN_ARN', 'arn:aws:states:us-east-1:123:stateMachine:test')

        cr_result = _make_cr_result(ResearchSource.WEBSITE_SCRAPE, confidence=0.9)
        input_data = _make_input(task_token='sfn-token-abc')

        mock_app_repo = MagicMock()
        mock_sfn = MagicMock()

        with (
            patch('careervp.handlers.company_research_worker_handler.research_company', new_callable=AsyncMock) as mock_research,
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=mock_app_repo),
            patch('careervp.handlers.company_research_worker_handler._persist_cr_result'),
            patch('boto3.client', return_value=mock_sfn),
        ):
            mock_research.return_value = Result(success=True, data=cr_result, code=ResultCode.SUCCESS)
            await _async_process_record(input_data, receive_count=1)

        mock_sfn.send_task_success.assert_called_once_with(
            taskToken='sfn-token-abc',
            output=json.dumps({'job_id': 'job-1', 'company_context': cr_result.model_dump(mode='json')}),
        )

    @pytest.mark.asyncio
    async def test_enqueues_vpr_standalone_when_no_task_token(self) -> None:
        cr_result = _make_cr_result(ResearchSource.WEBSITE_SCRAPE, confidence=0.9)
        input_data = _make_input(task_token=None)

        mock_app_repo = MagicMock()

        with (
            patch('careervp.handlers.company_research_worker_handler.research_company', new_callable=AsyncMock) as mock_research,
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=mock_app_repo),
            patch('careervp.handlers.company_research_worker_handler._persist_cr_result'),
            patch('careervp.handlers.company_research_worker_handler._enqueue_vpr_standalone') as mock_enqueue,
        ):
            mock_research.return_value = Result(success=True, data=cr_result, code=ResultCode.SUCCESS)
            await _async_process_record(input_data, receive_count=1)

        mock_enqueue.assert_called_once_with('user-1', 'job-1', cr_result)

    def test_hard_fail_calls_write_cr_failed(self) -> None:
        """SC5, SC8: _hard_fail calls write_cr_failed with application_id=job_id, user_id."""
        input_data = _make_input()

        mock_app_repo = MagicMock()
        mock_sfn = MagicMock()

        with (
            patch('careervp.handlers.company_research_worker_handler.write_cr_failed') as mock_write_failed,
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=mock_app_repo),
            patch('boto3.client', return_value=mock_sfn),
        ):
            _hard_fail(input_data, 'test cause')

        mock_write_failed.assert_called_once_with(
            application_id=input_data.job_id,
            user_id=input_data.user_id,
        )

    def test_hard_fail_tolerates_state_conditional_check_failure(self) -> None:
        """A ConditionalCheckFailedException on the state transition is benign.

        When CR hard-fails on an application that is no longer in cr_pending (e.g.
        a re-run on an advanced application), update_state's conditional guard
        raises ConditionalCheckFailedException. _hard_fail must still mark the
        artifact failed and signal the chain, without raising.
        """
        from botocore.exceptions import ClientError

        input_data = _make_input()

        mock_app_repo = MagicMock()
        mock_app_repo.update_state.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'failed'}},
            'UpdateItem',
        )
        mock_sfn = MagicMock()

        with (
            patch('careervp.handlers.company_research_worker_handler.write_cr_failed') as mock_write_failed,
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=mock_app_repo),
            patch('boto3.client', return_value=mock_sfn),
        ):
            # Must not raise despite the CCF on update_state.
            _hard_fail(input_data, 'confidence below threshold')

        mock_write_failed.assert_called_once()
        mock_app_repo.update_artifact_status.assert_called_once_with(
            application_id=input_data.job_id,
            user_id=input_data.user_id,
            artifact_type='company_research',
            status='failed',
        )
        mock_app_repo.update_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_hard_fail_sends_task_failure_to_sfn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv('STEP_FUNCTIONS_CHAIN_ARN', 'arn:aws:states:us-east-1:123:stateMachine:test')
        input_data = _make_input(task_token='sfn-token-xyz')

        mock_app_repo = MagicMock()
        mock_sfn = MagicMock()

        with (
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=mock_app_repo),
            patch('boto3.client', return_value=mock_sfn),
        ):
            _hard_fail(input_data, 'confidence=0.45 below threshold')

        mock_sfn.send_task_failure.assert_called_once()
        call_kwargs = mock_sfn.send_task_failure.call_args[1]
        assert call_kwargs['taskToken'] == 'sfn-token-xyz'
        assert call_kwargs['error'] == 'CRHardFail'

    @pytest.mark.asyncio
    async def test_cancel_ccf_sends_task_success_not_hard_fail(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When update_artifact_status raises CCF (cancelled guard), send task_success
        so the chain does not route to handle_cr_failure and no UI error is shown."""
        from botocore.exceptions import ClientError

        monkeypatch.setenv('ARTIFACT_CHAIN_ENABLED', 'true')
        monkeypatch.setenv('STEP_FUNCTIONS_CHAIN_ARN', 'arn:aws:states:us-east-1:123:stateMachine:test')

        cr_result = _make_cr_result(ResearchSource.WEBSITE_SCRAPE, confidence=0.9)
        input_data = _make_input(task_token='sfn-token-cancel')

        mock_app_repo = MagicMock()
        mock_app_repo.update_artifact_status.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'cancelled'}},
            'UpdateItem',
        )
        mock_sfn = MagicMock()

        with (
            patch('careervp.handlers.company_research_worker_handler.research_company', new_callable=AsyncMock) as mock_research,
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=mock_app_repo),
            patch('careervp.handlers.company_research_worker_handler._persist_cr_result'),
            patch('boto3.client', return_value=mock_sfn),
        ):
            mock_research.return_value = Result(success=True, data=cr_result, code=ResultCode.SUCCESS)
            await _async_process_record(input_data, receive_count=1)

        mock_sfn.send_task_success.assert_called_once()
        mock_sfn.send_task_failure.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_ccf_suppresses_signal_error_when_execution_stopped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """If the chain execution is already stopped (stop_execution called by cancel_artifact),
        send_task_success raises — the error must be swallowed and the worker must not raise."""
        from botocore.exceptions import ClientError

        monkeypatch.setenv('ARTIFACT_CHAIN_ENABLED', 'true')
        monkeypatch.setenv('STEP_FUNCTIONS_CHAIN_ARN', 'arn:aws:states:us-east-1:123:stateMachine:test')

        cr_result = _make_cr_result(ResearchSource.WEBSITE_SCRAPE, confidence=0.9)
        input_data = _make_input(task_token='sfn-token-stopped')

        mock_app_repo = MagicMock()
        mock_app_repo.update_artifact_status.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'cancelled'}},
            'UpdateItem',
        )
        mock_sfn = MagicMock()
        mock_sfn.send_task_success.side_effect = ClientError(
            {'Error': {'Code': 'ExecutionDoesNotExist', 'Message': 'execution stopped'}},
            'SendTaskSuccess',
        )

        with (
            patch('careervp.handlers.company_research_worker_handler.research_company', new_callable=AsyncMock) as mock_research,
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=mock_app_repo),
            patch('careervp.handlers.company_research_worker_handler._persist_cr_result'),
            patch('boto3.client', return_value=mock_sfn),
        ):
            mock_research.return_value = Result(success=True, data=cr_result, code=ResultCode.SUCCESS)
            # Must not raise even though send_task_success raised
            await _async_process_record(input_data, receive_count=1)


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    """TEST-CHAIN-001 § unit-cr-worker: idempotency key uniqueness"""

    def test_skips_if_cr_already_completed(self) -> None:
        """Second call with same user_id:job_id is a no-op when artifact is completed."""
        record = _sqs_record(receive_count=1)
        mock_app_repo = MagicMock()
        mock_app_repo.get.return_value = {'artifact_statuses': {'company_research': 'completed'}}

        with (
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=mock_app_repo),
            patch('careervp.handlers.company_research_worker_handler.asyncio') as mock_asyncio,
        ):
            _process_record(record)  # type: ignore[arg-type]

        # asyncio.run should never be called — idempotency guard returns early
        mock_asyncio.run.assert_not_called()

    def test_processes_if_cr_not_yet_completed(self) -> None:
        """Record is processed when artifact_statuses.company_research != completed."""
        record = _sqs_record(receive_count=1)
        mock_app_repo = MagicMock()
        mock_app_repo.get.return_value = {'artifact_statuses': {'company_research': 'pending'}}

        with (
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=mock_app_repo),
            patch('careervp.handlers.company_research_worker_handler.asyncio') as mock_asyncio,
        ):
            _process_record(record)  # type: ignore[arg-type]

        mock_asyncio.run.assert_called_once()

    def test_process_record_hydrates_company_fields_for_chain_payload(self) -> None:
        """Resolver-started chains send only IDs; CR worker hydrates company fields."""
        captured: dict[str, object] = {}

        async def _capture(input_data: CRWorkerInput, receive_count: int) -> None:
            captured['input_data'] = input_data
            captured['receive_count'] = receive_count

        record = {
            'body': json.dumps(
                {
                    'user_id': 'user-1',
                    'job_id': 'job-1',
                    'application_id': 'app-1',
                    'task_token': 'token-1',
                }
            ),
            'attributes': {'ApproximateReceiveCount': '2'},
        }
        mock_app_repo = MagicMock()
        mock_app_repo.get.return_value = {'artifact_statuses': {'company_research': 'pending'}, 'job_id': 'job-1'}
        mock_jobs_repo = MagicMock()
        mock_jobs_repo.get_job.return_value = {
            'company_name': 'Acme Corp',
            'url': 'https://example.com/jobs/1',
            'domain': 'example.com',
        }

        with (
            patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=mock_app_repo),
            patch('careervp.handlers.company_research_worker_handler._get_jobs_repository', return_value=mock_jobs_repo),
            patch('careervp.handlers.company_research_worker_handler._async_process_record', side_effect=_capture),
        ):
            _process_record(record)

        input_data = captured['input_data']
        assert isinstance(input_data, CRWorkerInput)
        assert input_data.company_name == 'Acme Corp'
        assert input_data.job_posting_url == 'https://example.com/jobs/1'
        assert input_data.domain == 'example.com'
        assert captured['receive_count'] == 2


# ---------------------------------------------------------------------------
# lambda_handler — batch item failures
# ---------------------------------------------------------------------------


class TestLambdaHandler:
    def test_returns_empty_failures_on_success(self) -> None:
        event = _sqs_event(_sqs_record())
        context = MagicMock()

        with patch('careervp.handlers.company_research_worker_handler._process_record') as mock_proc:
            mock_proc.return_value = None
            result = lambda_handler(event, context)  # type: ignore[arg-type]

        assert result == {'batchItemFailures': []}

    def test_retryable_error_appends_batch_item_failure(self) -> None:
        event = _sqs_event(_sqs_record(job_id='job-retry'))
        context = MagicMock()

        with patch('careervp.handlers.company_research_worker_handler._process_record', side_effect=RetryableError('low confidence')):
            result = lambda_handler(event, context)  # type: ignore[arg-type]

        assert result == {'batchItemFailures': [{'itemIdentifier': 'msg-job-retry'}]}

    def test_unexpected_error_appends_batch_item_failure(self) -> None:
        event = _sqs_event(_sqs_record(job_id='job-err'))
        context = MagicMock()

        with patch('careervp.handlers.company_research_worker_handler._process_record', side_effect=RuntimeError('boom')):
            result = lambda_handler(event, context)  # type: ignore[arg-type]

        assert result == {'batchItemFailures': [{'itemIdentifier': 'msg-job-err'}]}

    def test_partial_batch_failure(self) -> None:
        """One good record + one retryable → only the retryable is in failures."""
        good = _sqs_record(job_id='job-good')
        bad = _sqs_record(job_id='job-bad')
        event = _sqs_event(good, bad)
        context = MagicMock()

        def side_effect(record: dict[str, object]) -> None:
            body = json.loads(str(record['body']))
            if body['job_id'] == 'job-bad':
                raise RetryableError('low confidence')

        with patch('careervp.handlers.company_research_worker_handler._process_record', side_effect=side_effect):
            result = lambda_handler(event, context)  # type: ignore[arg-type]

        assert result == {'batchItemFailures': [{'itemIdentifier': 'msg-job-bad'}]}

    def test_no_records_returns_empty_failures(self) -> None:
        result = lambda_handler({'Records': []}, MagicMock())  # type: ignore[arg-type]
        assert result == {'batchItemFailures': []}
