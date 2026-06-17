"""FE-UI-040 tests for VPR binding to confident Company Research."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from careervp.models.job import CompanyContext
from careervp.models.result import Result, ResultCode


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-vpr-cr-binding-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('POWERTOOLS_TRACE_DISABLED', 'true')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-vpr-cr-binding')
    monkeypatch.setenv('TABLE_NAME', 'test-vpr-cr-binding')
    monkeypatch.setenv('KNOWLEDGE_TABLE_NAME', 'test-vpr-cr-binding')
    monkeypatch.setenv('SQS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123456789012/test-vpr-queue')


@pytest.fixture
def cr_table() -> Any:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-vpr-cr-binding',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        table.meta.client.get_waiter('table_exists').wait(TableName='test-vpr-cr-binding')
        yield table


def _cr_research_data(*, confidence: float = 0.9, company_name: str = 'Acme') -> dict[str, Any]:
    return {
        'company_name': company_name,
        'overview': 'Acme builds reliable workflow automation for enterprise teams.',
        'mission': 'Make enterprise work easier to operate.',
        'values': ['Reliability', 'Customer focus'],
        'strategic_priorities': ['Workflow automation', 'Enterprise AI'],
        'recent_news': ['Launched an AI operations suite'],
        'financial_summary': 'Privately held',
        'source': 'website_scrape',
        'source_urls': ['https://acme.example/about'],
        'confidence_score': Decimal(str(confidence)),
        'research_timestamp': '2026-06-14T09:00:00+00:00',
    }


def _put_cr(
    table: Any,
    *,
    application_id: str = 'app-1',
    user_id: str = 'user-1',
    confidence: float = 0.9,
    company_research_id: str = 'cr-1',
    created_at: str = '2026-06-14T09:05:00+00:00',
) -> None:
    table.put_item(
        Item={
            'pk': user_id,
            'sk': f'COMPANY_RESEARCH#{application_id}',
            'user_id': user_id,
            'job_id': application_id,
            'company_research_id': company_research_id,
            'company_name': 'Acme',
            'research_data': _cr_research_data(confidence=confidence),
            'created_at': created_at,
            'entity_type': 'COMPANY_RESEARCH',
        }
    )


def _context() -> Any:
    context = MagicMock()
    context.aws_request_id = 'req-1'
    context.function_name = 'test-handler'
    return context


def _submit_event(user_id: str = 'user-1') -> dict[str, Any]:
    return {
        'httpMethod': 'POST',
        'path': '/vpr/generate',
        'headers': {'Content-Type': 'application/json', 'x-user-id': user_id},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
        'body': json.dumps(
            {
                'cv_id': 'cv-1',
                'job_id': 'app-1',
                'application_id': 'app-1',
                'gap_response_ids': ['gap-1'],
                'force': True,
            }
        ),
    }


def test_load_confident_cr_returns_context_when_present(cr_table: Any) -> None:
    from careervp.logic.company_research import load_confident_company_research

    _put_cr(cr_table)

    context = load_confident_company_research(application_id='app-1', user_id='user-1')

    assert isinstance(context, CompanyContext)
    assert context.company_name == 'Acme'
    assert context.mission == 'Make enterprise work easier to operate.'
    assert context.strategic_priorities == ['Workflow automation', 'Enterprise AI']


def test_load_confident_cr_returns_none_for_low_confidence(cr_table: Any) -> None:
    from careervp.logic.company_research import load_confident_company_research

    _put_cr(cr_table, confidence=0.7)

    assert load_confident_company_research(application_id='app-1', user_id='user-1') is None


def test_load_confident_cr_ownership_enforced(cr_table: Any) -> None:
    from careervp.logic.company_research import load_confident_company_research

    _put_cr(cr_table, user_id='other-user')

    assert load_confident_company_research(application_id='app-1', user_id='user-1') is None


def test_vpr_submit_injects_company_context(cr_table: Any) -> None:
    from careervp.handlers import vpr_submit_handler

    _put_cr(cr_table, company_research_id='cr-submit-1')

    with (
        patch('careervp.handlers.vpr_submit_handler.JobsRepository') as repo_cls,
        patch('careervp.handlers.vpr_submit_handler.uuid.uuid4', return_value='vpr-job-1'),
        patch.object(vpr_submit_handler.sqs, 'send_message') as send_message,
    ):
        repo = repo_cls.return_value
        repo.get_job_by_idempotency_key.return_value = None
        repo.create_job.return_value = Result(success=True, data={'job_id': 'vpr-job-1'}, code=ResultCode.SUCCESS)
        send_message.return_value = {'MessageId': 'msg-1'}

        response = vpr_submit_handler.lambda_handler(_submit_event(), _context())

    assert response['statusCode'] == 202
    job_record = repo.create_job.call_args.args[0]
    input_data = job_record['input_data']
    assert input_data['company_research_id'] == 'cr-submit-1'
    assert input_data['company_research_at'] == '2026-06-14T09:05:00+00:00'
    assert input_data['company_context']['company_name'] == 'Acme'
    assert input_data['company_context']['mission'] == 'Make enterprise work easier to operate.'


def test_worker_loads_cr_when_message_lacks_context(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import vpr_worker_handler

    repo = MagicMock()
    repo.update_job_status.return_value = Result(success=True, data={}, code=ResultCode.SUCCESS)
    repo.update_job.return_value = Result(success=True, data={}, code=ResultCode.SUCCESS)
    cv_dal = MagicMock()
    cv_dal.get_cv.return_value = {'parsed': 'cv'}
    cv_dal.get_next_vpr_version.return_value = 3
    loaded = MagicMock(
        company_context=CompanyContext(
            company_name='Acme',
            mission='Make enterprise work easier to operate.',
            values=['Reliability'],
            strategic_priorities=['Enterprise AI'],
            recent_news=['Launched an AI operations suite'],
        ),
        company_research_id='cr-worker-1',
        company_research_at='2026-06-14T09:05:00+00:00',
    )
    vpr = MagicMock(version=3, word_count=250)
    vpr.company_insights = MagicMock()
    vpr.model_dump_json.return_value = '{"ok": true}'
    vpr_response = MagicMock(vpr=vpr, token_usage=None)

    monkeypatch.setattr(vpr_worker_handler, 'DynamoDalHandler', MagicMock(return_value=cv_dal))
    monkeypatch.setattr(vpr_worker_handler, 'load_confident_company_research_artifact', MagicMock(return_value=loaded), raising=False)
    monkeypatch.setattr(vpr_worker_handler, 'generate_vpr', MagicMock(return_value=Result(success=True, data=vpr_response, code=ResultCode.SUCCESS)))
    monkeypatch.setattr(vpr_worker_handler, '_generate_presigned_url', MagicMock(return_value='https://example.test/result'))
    monkeypatch.setattr(vpr_worker_handler.s3, 'put_object', MagicMock())

    vpr_worker_handler._execute_job(
        repo,
        {
            'status': 'PENDING',
            'user_id': 'user-1',
            'application_id': 'app-1',
            'input_data': {
                'job_posting': {
                    'company_name': 'Acme',
                    'role_title': 'Platform Engineer',
                    'description': 'Build reliable systems.',
                    'requirements': ['Python'],
                },
                'gap_responses': [],
            },
        },
        'vpr-job-1',
        'bucket-1',
    )

    request = vpr_worker_handler.generate_vpr.call_args.args[0]
    assert request.company_context is not None
    assert request.company_context.company_name == 'Acme'
    # The COMPLETED write is the atomic, guarded update_job_status (FE-UI-043);
    # provenance fields are passed as flat kwargs alongside status='COMPLETED'.
    completed_calls = [c for c in repo.update_job_status.call_args_list if c.kwargs.get('status') == 'COMPLETED']
    assert completed_calls, 'VPR worker did not perform the COMPLETED write'
    update_payload = completed_calls[0].kwargs
    assert update_payload['expected_current_status'] == 'PROCESSING'
    assert update_payload['company_research_id'] == 'cr-worker-1'
    assert update_payload['company_research_at'] == '2026-06-14T09:05:00+00:00'
    assert update_payload['company_context_included'] is True


def test_status_endpoint_exposes_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import vpr_status_handler

    monkeypatch.setattr(vpr_status_handler, '_s3_object_exists', MagicMock(return_value=True))
    monkeypatch.setattr(vpr_status_handler, '_get_or_cache_presigned_url', MagicMock(return_value='https://example.test/result'))

    response = vpr_status_handler._build_completed_response(
        {
            'status': 'COMPLETED',
            'created_at': datetime(2026, 6, 14, tzinfo=timezone.utc).isoformat(),
            'completed_at': datetime(2026, 6, 14, 9, 30, tzinfo=timezone.utc).isoformat(),
            'result_key': 'results/vpr-job-1.json',
            'result': {
                'uvp': 'Strategic platform engineer',
                'differentiators': [{'text': 'Reliable systems delivery', 'source': 'cv'}],
            },
            'company_research_id': 'cr-status-1',
            'company_research_at': '2026-06-14T09:05:00+00:00',
            'company_context_included': True,
        },
        'vpr-job-1',
        MagicMock(),
    )

    assert response['company_research_id'] == 'cr-status-1'
    assert response['company_research_at'] == '2026-06-14T09:05:00+00:00'
    assert response['company_context_included'] is True
    assert response['result']['company_research_id'] == 'cr-status-1'
    assert response['result']['company_context_included'] is True
