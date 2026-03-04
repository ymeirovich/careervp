"""Unit tests for endpoint-level trial credit attribution and charging boundaries."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from careervp.models.result import Result, ResultCode


@pytest.fixture(autouse=True)
def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'trial-attribution-tests')
    monkeypatch.setenv('GAP_RESPONSES_TABLE_NAME', 'gap-responses-table')


def _gap_event(path: str, method: str, body: dict[str, object], user_id: str = 'user-1') -> dict[str, object]:
    return {
        'path': path,
        'httpMethod': method,
        'headers': {'Content-Type': 'application/json'},
        'pathParameters': {'jobId': 'job-1'},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
        'body': json.dumps(body),
    }


def _job_event(body: dict[str, object], user_id: str = 'user-1') -> dict[str, object]:
    return {
        'version': '1.0',
        'resource': '/jobs',
        'path': '/jobs',
        'httpMethod': 'POST',
        'headers': {'Content-Type': 'application/json'},
        'multiValueHeaders': {},
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'requestContext': {
            'httpMethod': 'POST',
            'path': '/jobs',
            'authorizer': {'claims': {'sub': user_id}},
        },
        'pathParameters': None,
        'stageVariables': None,
        'body': json.dumps(body),
        'isBase64Encoded': False,
    }


def _context() -> SimpleNamespace:
    return SimpleNamespace(
        function_name='test-handler',
        aws_request_id='req-1',
        memory_limit_in_mb=256,
        invoked_function_arn='arn:aws:lambda:us-east-1:123456789012:function:test-handler',
    )


@pytest.mark.unit
def test_gap_questions_consumes_credit_and_logs_attribution() -> None:
    from careervp.handlers.gap_handler import lambda_handler

    trial_service = MagicMock()
    trial_service.check_trial_status.return_value = {'is_active': True, 'applications_used': 0}
    trial_service.consume_credit.return_value = None
    trial_service.get_usage.return_value = {'applications_used': 1}

    generated_questions = [
        {
            'id': 'gap-q-1',
            'question': 'Describe your measurable impact.',
            'tags': ['impact'],
            'strategic_intent': 'Assess outcomes',
            'evidence_gap': 'Needs metrics',
        }
    ]

    questions_dal = MagicMock()
    questions_dal.save_gap_questions.return_value = Result(
        success=True,
        data=None,
        code=ResultCode.GAP_QUESTIONS_GENERATED,
    )
    app_repo = MagicMock()

    event = _gap_event(
        '/jobs/job-1/gap-questions',
        'POST',
        {'cv_id': 'cv-1', 'job_id': 'job-1'},
    )

    with (
        patch('careervp.handlers.gap_handler._get_trial_service', return_value=trial_service),
        patch('careervp.handlers.gap_handler._get_questions_dal', return_value=questions_dal),
        patch('careervp.handlers.gap_handler._get_application_repository', return_value=app_repo),
        patch('careervp.handlers.gap_handler.generate_gap_questions') as mock_generate,
        patch('careervp.handlers.gap_handler.logger.info') as mock_log_info,
        patch('careervp.handlers.gap_handler.metrics.add_metric') as mock_add_metric,
    ):
        mock_generate.return_value = Result(
            success=True,
            data=generated_questions,
            code=ResultCode.GAP_QUESTIONS_GENERATED,
        )
        response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    trial_service.consume_credit.assert_called_once_with('user-1')

    attribution_calls = [call for call in mock_log_info.call_args_list if call.args and call.args[0] == 'Trial credit attribution']
    assert attribution_calls, 'Expected trial attribution log entry'
    attribution_kwargs = attribution_calls[-1].kwargs
    assert attribution_kwargs['endpoint'] == 'POST /jobs/{jobId}/gap-questions'
    assert attribution_kwargs['user_id'] == 'user-1'
    assert attribution_kwargs['usage_before'] == 0
    assert attribution_kwargs['usage_after'] == 1
    assert attribution_kwargs['consumed'] is True

    metric_names = [call.kwargs.get('name') for call in mock_add_metric.call_args_list]
    assert 'TrialCreditAttributionEvents' in metric_names
    assert 'TrialCreditConsumed' in metric_names


@pytest.mark.unit
def test_gap_responses_submit_does_not_check_or_consume_trial_credit() -> None:
    from careervp.handlers.gap_handler import lambda_handler

    responses_dal = MagicMock()
    responses_dal.save_gap_responses_raw.return_value = Result(
        success=True,
        data=None,
        code=ResultCode.GAP_RESPONSES_SAVED,
    )

    event = _gap_event(
        '/jobs/job-1/gap-responses',
        'POST',
        {
            'job_id': 'job-1',
            'responses': [{'question_id': 'gap-q-1', 'response': 'STAR example with numbers'}],
        },
    )

    with (
        patch('careervp.handlers.gap_handler._get_responses_dal', return_value=responses_dal),
        patch('careervp.handlers.gap_handler._get_trial_service') as mock_get_trial_service,
    ):
        response = lambda_handler(event, _context())

    assert response['statusCode'] == 201
    mock_get_trial_service.assert_not_called()


@pytest.mark.unit
def test_jobs_create_checks_trial_status_without_consuming_credit() -> None:
    from careervp.handlers.job_handler import _reset_handler_caches, lambda_handler

    trial_service = MagicMock()
    trial_service.check_trial_status.return_value = {
        'is_active': True,
        'applications_used': 0,
        'applications_remaining': 3,
    }

    job_record = {
        'job_id': 'job-1',
        'user_id': 'user-1',
        'title': 'Backend Engineer',
        'company_name': 'Acme Corp',
        'description': 'Build APIs',
        'status': 'active',
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    jobs_repo = MagicMock()
    jobs_repo.create_job.return_value = SimpleNamespace(success=True, data=job_record, error=None)

    event = _job_event(
        {
            'title': 'Backend Engineer',
            'company_name': 'Acme Corp',
            'description': 'Build APIs',
        }
    )

    _reset_handler_caches()
    with (
        patch('careervp.handlers.job_handler._get_trial_service', return_value=trial_service),
        patch('careervp.handlers.job_handler._get_jobs_repository', return_value=jobs_repo),
    ):
        response = lambda_handler(event, _context())
    _reset_handler_caches()

    assert response['statusCode'] == 201
    trial_service.check_trial_status.assert_called_once_with('user-1')
    trial_service.consume_credit.assert_not_called()
