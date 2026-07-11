"""
Category G — Manual-endpoint regression suite.

TEST-CHAIN-001 Category G backfill for FE-UI-031.
Characterise-existing mode: tests describe behaviour AS BUILT.

Coverage map
  flag OFF → gap submit no sfn     → test_submit_flag_off_no_sfn_start  (consolidates test_gap_handler_artifact_chain.py)
  flag ON  → gap submit starts sfn → test_submit_flag_on_starts_sfn      (consolidates test_gap_handler_artifact_chain.py)
  manual VPR trigger (SQS, no SFN) → TestManualVPRTrigger
  manual CR retry (no SFN)         → TestManualCRRetry
  manual CV tailoring works        → TestManualCVTailoring
"""

from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('POWERTOOLS_SERVICE_NAME', 'careervp-test')
os.environ.setdefault('LOG_LEVEL', 'ERROR')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok_gap_dal() -> MagicMock:
    from careervp.models.result import Result, ResultCode

    dal = MagicMock()
    dal.save_gap_responses_raw.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)
    return dal


def _gap_submit_event(job_id: str = 'job-001', user_id: str = 'user-abc') -> dict[str, Any]:
    return {
        'resource': '/gap-analysis/responses',
        'path': '/gap-analysis/responses',
        'httpMethod': 'POST',
        'headers': {'Content-Type': 'application/json'},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
        'body': json.dumps(
            {
                'job_id': job_id,
                'responses': [{'question_id': 'q1', 'response': 'Did X to achieve Y.'}],
            }
        ),
        'isBase64Encoded': False,
    }


def _confident_cr_artifact() -> Any:
    """A confidence-gated CR artifact so VPR submit clears its CR dependency gate."""
    from careervp.logic.company_research import ConfidentCompanyResearch
    from careervp.models.job import CompanyContext

    return ConfidentCompanyResearch(
        company_context=CompanyContext(company_name='Acme Corp'),
        company_research_id='cr-001',
        company_research_at='2026-06-28T00:00:00Z',
    )


def _vpr_submit_event(user_id: str = 'user-abc', cv_id: str = 'cv-1', job_id: str = 'job-001') -> dict[str, Any]:
    # gap_response_ids is required to trigger the OpenAPI (non-legacy) code path.
    return {
        'httpMethod': 'POST',
        'path': '/vpr/generate',
        'headers': {'Content-Type': 'application/json'},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
        'body': json.dumps({'cv_id': cv_id, 'job_id': job_id, 'gap_response_ids': []}),
    }


# ---------------------------------------------------------------------------
# Flag gate: consolidates test_gap_handler_artifact_chain.py as single source
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _gap_env(
    monkeypatch: pytest.MonkeyPatch,
    mock_artifact_dependency_resolver: Any,
    mock_company_research_load: Any,
) -> None:
    # These manual-endpoint regressions assert the submit/flag behavior, not
    # upstream dependency resolution, so they opt into the bypass fixtures
    # retired from global autouse (T-02).
    monkeypatch.setenv('USERS_TABLE_NAME', 'test-users-table')
    monkeypatch.setenv('GAP_RESPONSES_TABLE_NAME', 'test-gap-responses-table')
    monteypatch_env_cleaners = ['ARTIFACT_CHAIN_ENABLED', 'STEP_FUNCTIONS_CHAIN_ARN']
    for key in monteypatch_env_cleaners:
        monkeypatch.delenv(key, raising=False)


@pytest.mark.integration
def test_submit_flag_off_no_sfn_start() -> None:
    """Flag OFF (default): gap submit returns 200 and never calls sfn.start_execution."""
    from careervp.handlers import gap_handler

    mock_sfn = MagicMock()
    with (
        patch.object(gap_handler, '_get_responses_dal', return_value=_ok_gap_dal()),
        patch.object(gap_handler, '_get_application_repository', return_value=MagicMock()),
        patch('careervp.handlers.gap_handler.boto3.client', return_value=mock_sfn) as mock_boto,
    ):
        response = gap_handler.submit_response(_gap_submit_event())

    assert response['statusCode'] == 200
    mock_boto.assert_not_called()


@pytest.mark.integration
def test_submit_flag_on_starts_sfn_and_transitions_to_cr_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    """Flag ON: gap submit calls sfn.start_execution and transitions state to cr_pending."""
    from careervp.handlers import gap_handler

    monkeypatch.setenv('ARTIFACT_CHAIN_ENABLED', 'true')
    monkeypatch.setenv('STEP_FUNCTIONS_CHAIN_ARN', 'arn:aws:states:us-east-1:123:stateMachine:chain')

    mock_app_repo = MagicMock()
    mock_jobs_repo = MagicMock()
    mock_jobs_repo.get_job.return_value = {'company_name': 'Acme', 'job_posting_url': 'https://example.com/job'}
    mock_sfn = MagicMock()

    with (
        patch.object(gap_handler, '_get_responses_dal', return_value=_ok_gap_dal()),
        patch.object(gap_handler, '_get_application_repository', return_value=mock_app_repo),
        patch.object(gap_handler, '_get_jobs_repository', return_value=mock_jobs_repo),
        patch('careervp.handlers.gap_handler.boto3.client', return_value=mock_sfn),
    ):
        response = gap_handler.submit_response(_gap_submit_event(job_id='job-xyz'))

    assert response['statusCode'] == 200
    mock_sfn.start_execution.assert_called_once()
    mock_app_repo.update_state.assert_called_once_with(
        application_id='job-xyz',
        user_id='user-abc',
        new_state='cr_pending',
        expected_state='gap_responses_submitted',
    )


# ---------------------------------------------------------------------------
# Manual VPR trigger — must use SQS regardless of artifact chain flag
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestManualVPRTrigger:
    """POST /vpr/generate sends to SQS; Step Functions must never be called."""

    @pytest.fixture(autouse=True)
    def _vpr_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv('APPLICATIONS_TABLE_NAME', 'test-applications-table')
        monkeypatch.setenv('KNOWLEDGE_TABLE_NAME', 'test-knowledge-table')
        monkeypatch.setenv('SQS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123/vpr-jobs')

    def _jobs_repo_mock(self) -> MagicMock:
        mock = MagicMock()
        # Return None = no existing job, so idempotency check passes through.
        mock.get_job_by_idempotency_key.return_value = None
        mock.create_job.return_value = MagicMock(success=True)
        mock.update_job_status.return_value = MagicMock(success=True)
        return mock

    def test_vpr_trigger_enqueues_to_sqs_flag_off(self) -> None:
        """Flag OFF: POST /vpr/generate returns 202 and sends one SQS message."""
        from careervp.handlers.vpr_submit_handler import lambda_handler

        mock_sqs = MagicMock()
        mock_sqs.send_message.return_value = {'MessageId': 'msg-1'}
        mock_sfn = MagicMock()

        with (
            patch('careervp.handlers.vpr_submit_handler.JobsRepository', return_value=self._jobs_repo_mock()),
            patch('careervp.handlers.vpr_submit_handler.sqs', mock_sqs),
            patch('careervp.handlers.vpr_submit_handler.load_confident_company_research_artifact', return_value=_confident_cr_artifact()),
            patch('boto3.client', return_value=mock_sfn),
        ):
            response = lambda_handler(_vpr_submit_event(), MagicMock())

        assert response['statusCode'] == 202
        mock_sqs.send_message.assert_called_once()
        mock_sfn.start_execution.assert_not_called()

    def test_vpr_trigger_enqueues_to_sqs_flag_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Flag ON: POST /vpr/generate still uses SQS — no sfn.start_execution."""
        monkeypatch.setenv('ARTIFACT_CHAIN_ENABLED', 'true')
        monkeypatch.setenv('STEP_FUNCTIONS_CHAIN_ARN', 'arn:aws:states:us-east-1:123:stateMachine:chain')

        from careervp.handlers.vpr_submit_handler import lambda_handler

        mock_sqs = MagicMock()
        mock_sqs.send_message.return_value = {'MessageId': 'msg-2'}
        mock_sfn = MagicMock()

        with (
            patch('careervp.handlers.vpr_submit_handler.JobsRepository', return_value=self._jobs_repo_mock()),
            patch('careervp.handlers.vpr_submit_handler.sqs', mock_sqs),
            patch('careervp.handlers.vpr_submit_handler.load_confident_company_research_artifact', return_value=_confident_cr_artifact()),
            patch('boto3.client', return_value=mock_sfn),
        ):
            response = lambda_handler(_vpr_submit_event(), MagicMock())

        assert response['statusCode'] == 202
        mock_sqs.send_message.assert_called_once()
        mock_sfn.start_execution.assert_not_called()


# ---------------------------------------------------------------------------
# Manual CR retry — POST /company-research works without Step Functions
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestManualCRRetry:
    """POST /company-research works independently of artifact chain flag."""

    @pytest.fixture(autouse=True)
    def _cr_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-cr-table')

    def _make_cr_post_event(self, user_id: str = 'user-abc', job_id: str = 'job-001') -> dict[str, Any]:
        return {
            'httpMethod': 'POST',
            'path': '/company-research',
            'headers': {'Content-Type': 'application/json'},
            'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
            'body': json.dumps(
                {
                    'company_name': 'Acme Corp',
                    'job_id': job_id,
                    'domain': 'acme.com',
                }
            ),
        }

    def test_manual_cr_post_succeeds_with_flag_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Flag OFF: POST /company-research enqueues the async worker and returns 202."""
        monkeypatch.setenv('COMPANY_RESEARCH_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123/cr-jobs')

        from careervp.handlers.company_research_handler import lambda_handler

        mock_sqs = MagicMock()
        mock_sqs.send_message.return_value = {'MessageId': 'cr-msg-1'}

        with (
            patch('careervp.handlers.company_research_handler.boto3.client', return_value=mock_sqs),
            patch('careervp.handlers.company_research_handler.write_cr_processing'),
        ):
            response = lambda_handler(self._make_cr_post_event(), MagicMock())

        assert response['statusCode'] == 202
        body = json.loads(response['body'])
        assert 'request_id' in body
        mock_sqs.send_message.assert_called_once()

    def test_manual_cr_post_succeeds_with_flag_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Flag ON: manual POST /company-research still enqueues; no SFN call."""
        monkeypatch.setenv('ARTIFACT_CHAIN_ENABLED', 'true')
        monkeypatch.setenv('STEP_FUNCTIONS_CHAIN_ARN', 'arn:aws:states:us-east-1:123:stateMachine:chain')
        monkeypatch.setenv('COMPANY_RESEARCH_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123/cr-jobs')

        from careervp.handlers.company_research_handler import lambda_handler

        mock_client = MagicMock()
        mock_client.send_message.return_value = {'MessageId': 'cr-msg-2'}

        with (
            patch('careervp.handlers.company_research_handler.boto3.client', return_value=mock_client),
            patch('careervp.handlers.company_research_handler.write_cr_processing'),
        ):
            response = lambda_handler(self._make_cr_post_event(), MagicMock())

        assert response['statusCode'] == 202
        mock_client.send_message.assert_called_once()
        mock_client.start_execution.assert_not_called()


# ---------------------------------------------------------------------------
# Manual CV tailoring — works independently of artifact chain flag
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestManualCVTailoring:
    """POST /cv-tailoring works independently of artifact chain flag."""

    @pytest.fixture(autouse=True)
    def _cv_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-cv-table')
        monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')
        monkeypatch.setenv('CV_STORAGE_BUCKET', 'test-bucket')

    def _make_cv_tailor_event(self, user_id: str = 'user-abc', cv_id: str = 'cv-1', job_id: str = 'job-001', vpr_id: str = 'vpr-1') -> dict[str, Any]:
        # vpr_id is required to trigger the OpenAPI (non-legacy) code path.
        return {
            'httpMethod': 'POST',
            'path': '/cv-tailoring',
            'headers': {'Content-Type': 'application/json'},
            'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
            'body': json.dumps(
                {
                    'cv_id': cv_id,
                    'job_id': job_id,
                    'vpr_id': vpr_id,
                }
            ),
        }

    def _mock_pipeline_result(self) -> MagicMock:
        from careervp.models.cv_tailoring_models import (
            CVContactSection,
            CVExperienceBullet,
            CVExperienceSection,
            CVSections,
            CVSkillsSection,
            Stage3Result,
        )

        stage3 = Stage3Result(
            cv_sections=CVSections(
                contact=CVContactSection(name='Test User', email='test@example.com'),
                summary='Experienced engineer with deep expertise in Python, cloud systems, and distributed architecture.',
                skills=CVSkillsSection(technical=['Python'], soft=[]),
                experience=[
                    CVExperienceSection(
                        company='Acme',
                        title='Engineer',
                        start_date='01/2020',
                        bullets=[
                            CVExperienceBullet(
                                text='Built reliable systems.',
                                source='parsed_facts',
                                user_edited=False,
                                quantified=False,
                            )
                        ],
                    )
                ],
                education=[],
                certifications=[],
            ),
            fact_verification_passed=True,
            items_corrected=[],
            items_removed=[],
        )
        result = MagicMock()
        result.success = True
        result.data = stage3
        result.error = None
        return result

    def test_cv_tailoring_returns_202_with_flag_off(self) -> None:
        """Flag OFF: POST /cv-tailoring returns 202 and never calls sfn.start_execution."""
        from careervp.handlers.cv_tailoring_handler import lambda_handler

        mock_dal = MagicMock()
        mock_dal.get_cv.return_value = MagicMock()
        mock_dal._get_db_handler.return_value = MagicMock()
        mock_sfn = MagicMock()

        with (
            patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal),
            patch('careervp.handlers.cv_tailoring_handler.JobsRepository') as mock_jobs_cls,
            patch('careervp.handlers.cv_tailoring_handler.LLMClient'),
            patch('careervp.handlers.cv_tailoring_handler.run_cv_tailoring_pipeline', return_value=self._mock_pipeline_result()),
            patch('careervp.handlers.cv_tailoring_handler._update_application_artifact'),
            patch('boto3.client', return_value=mock_sfn),
        ):
            mock_jobs_cls.return_value.get_job.return_value = {'description': 'Job desc', 'title': 'Engineer'}
            response = lambda_handler(self._make_cv_tailor_event(), MagicMock())

        assert response['statusCode'] == 202
        mock_sfn.start_execution.assert_not_called()

    def test_cv_tailoring_returns_202_with_flag_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Flag ON: CV tailoring still returns 202 and never calls sfn.start_execution."""
        monkeypatch.setenv('ARTIFACT_CHAIN_ENABLED', 'true')
        monkeypatch.setenv('STEP_FUNCTIONS_CHAIN_ARN', 'arn:aws:states:us-east-1:123:stateMachine:chain')

        from careervp.handlers.cv_tailoring_handler import lambda_handler

        mock_dal = MagicMock()
        mock_dal.get_cv.return_value = MagicMock()
        mock_dal._get_db_handler.return_value = MagicMock()
        mock_sfn = MagicMock()

        with (
            patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal),
            patch('careervp.handlers.cv_tailoring_handler.JobsRepository') as mock_jobs_cls,
            patch('careervp.handlers.cv_tailoring_handler.LLMClient'),
            patch('careervp.handlers.cv_tailoring_handler.run_cv_tailoring_pipeline', return_value=self._mock_pipeline_result()),
            patch('careervp.handlers.cv_tailoring_handler._update_application_artifact'),
            patch('boto3.client', return_value=mock_sfn),
        ):
            mock_jobs_cls.return_value.get_job.return_value = {'description': 'Job desc', 'title': 'Engineer'}
            response = lambda_handler(self._make_cv_tailor_event(), MagicMock())

        assert response['statusCode'] == 202
        mock_sfn.start_execution.assert_not_called()
