"""
Unit tests for careervp.handlers.company_research_handler.

TEST-FE-053 Categories A and B.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ENV', 'local')
    monkeypatch.setenv('COMPANY_RESEARCH_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123/cr-queue')
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'artifacts-table')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'test')
    monkeypatch.setenv('POWERTOOLS_METRICS_NAMESPACE', 'careervp')


def _post_event(body: dict[str, object], user_id: str = 'user-1') -> dict[str, object]:
    return {
        'httpMethod': 'POST',
        'path': '/company-research/fetch',
        'body': json.dumps(body),
        'headers': {'x-user-id': user_id},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
    }


def _get_event(job_id: str, user_id: str = 'user-1') -> dict[str, object]:
    return {
        'httpMethod': 'GET',
        'path': f'/company-research/{job_id}',
        'pathParameters': {'jobId': job_id},
        'headers': {'x-user-id': user_id},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
    }


# ---------------------------------------------------------------------------
# Category A: post_enqueue — SC1, SC2, SC3
# ---------------------------------------------------------------------------


class TestPostEnqueue:
    """TEST-FE-053 Category A: POST enqueues SQS and writes processing row."""

    def test_post_sends_one_sqs_message(self) -> None:
        """SC1: POST sends exactly one SQS message with a valid CRWorkerInput body."""
        from careervp.handlers.company_research_handler import lambda_handler
        from careervp.handlers.company_research_worker_handler import CRWorkerInput

        event = _post_event({'company_name': 'Acme Corp', 'domain': 'acme.com', 'job_id': 'job-123'})
        context = MagicMock()

        mock_sqs = MagicMock()
        with (
            patch('careervp.handlers.company_research_handler.boto3') as mock_boto3,
            patch('careervp.handlers.company_research_handler.write_cr_processing'),
        ):
            mock_boto3.client.return_value = mock_sqs
            lambda_handler(event, context)

        mock_sqs.send_message.assert_called_once()
        call_kwargs = mock_sqs.send_message.call_args[1]
        body = json.loads(call_kwargs['MessageBody'])
        # Validates as CRWorkerInput — all required fields present
        parsed = CRWorkerInput.model_validate(body)
        assert parsed.user_id == 'user-1'
        assert parsed.job_id == 'job-123'

    def test_post_returns_202_no_research_call(self) -> None:
        """SC2: POST returns 202; research_company is not imported and cannot be called."""
        import careervp.handlers.company_research_handler as handler_mod

        # Confirm research_company is not importable from the handler module
        assert not hasattr(handler_mod, 'research_company'), 'research_company must not be imported in company_research_handler'

        from careervp.handlers.company_research_handler import lambda_handler

        event = _post_event({'company_name': 'Acme Corp'})
        context = MagicMock()

        mock_sqs = MagicMock()
        with (
            patch('careervp.handlers.company_research_handler.boto3') as mock_boto3,
            patch('careervp.handlers.company_research_handler.write_cr_processing'),
        ):
            mock_boto3.client.return_value = mock_sqs
            response = lambda_handler(event, context)

        assert response['statusCode'] == HTTPStatus.ACCEPTED.value

    def test_post_writes_processing_row(self) -> None:
        """SC3: POST calls write_cr_processing once with correct application_id and user_id."""
        from careervp.handlers.company_research_handler import lambda_handler

        event = _post_event({'company_name': 'Acme Corp', 'job_id': 'job-abc'})
        context = MagicMock()

        mock_sqs = MagicMock()
        with (
            patch('careervp.handlers.company_research_handler.boto3') as mock_boto3,
            patch('careervp.handlers.company_research_handler.write_cr_processing') as mock_write,
        ):
            mock_boto3.client.return_value = mock_sqs
            lambda_handler(event, context)

        mock_write.assert_called_once()
        call_kwargs = mock_write.call_args[1]
        assert call_kwargs['application_id'] == 'job-abc'
        assert call_kwargs['user_id'] == 'user-1'


# ---------------------------------------------------------------------------
# Category B: get_status — SC4
# ---------------------------------------------------------------------------


class TestGetStatus:
    """TEST-FE-053 Category B: GET returns correct status based on artifact row."""

    def test_get_processing(self) -> None:
        """SC4: processing row → {status:'processing', company_research:null}."""
        from careervp.handlers.company_research_handler import lambda_handler

        item = {
            'applicationId': 'job-1',
            'artifactId': 'ARTIFACT#COMPANY_RESEARCH#job-1',
            'artifactType': 'company_research',
            'user_id': 'user-1',
            'status': 'processing',
        }

        event = _get_event('job-1')
        context = MagicMock()

        with patch('careervp.handlers.company_research_handler.read_cr_artifact', return_value=item):
            response = lambda_handler(event, context)

        assert response['statusCode'] == HTTPStatus.OK.value
        body = json.loads(response['body'])
        assert body['status'] == 'processing'
        assert body['company_research'] is None

    def test_get_completed(self) -> None:
        """Confidence-gated completed row → {status:'completed', company_research present}."""
        from careervp.handlers.company_research_handler import lambda_handler

        item = {
            'applicationId': 'job-1',
            'artifactId': 'ARTIFACT#COMPANY_RESEARCH#job-1',
            'artifactType': 'company_research',
            'user_id': 'user-1',
            'company_name': 'Acme Corp',
            'mission': 'To innovate',
            'confidence_score': 0.95,
            'research_data': {'company_name': 'Acme Corp'},
        }

        event = _get_event('job-1')
        context = MagicMock()

        with patch('careervp.handlers.company_research_handler.read_cr_artifact', return_value=item):
            response = lambda_handler(event, context)

        assert response['statusCode'] == HTTPStatus.OK.value
        body = json.loads(response['body'])
        assert body['status'] == 'completed'

    def test_get_failed(self) -> None:
        """Failed row → {status:'failed', company_research:null}."""
        from careervp.handlers.company_research_handler import lambda_handler

        item = {
            'applicationId': 'job-1',
            'artifactId': 'ARTIFACT#COMPANY_RESEARCH#job-1',
            'artifactType': 'company_research',
            'user_id': 'user-1',
            'status': 'failed',
        }

        event = _get_event('job-1')
        context = MagicMock()

        with patch('careervp.handlers.company_research_handler.read_cr_artifact', return_value=item):
            response = lambda_handler(event, context)

        assert response['statusCode'] == HTTPStatus.OK.value
        body = json.loads(response['body'])
        assert body['status'] == 'failed'
        assert body['company_research'] is None

    def test_get_not_generated(self) -> None:
        """No artifact row → {status:'not_generated', company_research:null}."""
        from careervp.handlers.company_research_handler import lambda_handler

        event = _get_event('job-1')
        context = MagicMock()

        with patch('careervp.handlers.company_research_handler.read_cr_artifact', return_value=None):
            response = lambda_handler(event, context)

        assert response['statusCode'] == HTTPStatus.OK.value
        body = json.loads(response['body'])
        assert body['status'] == 'not_generated'
        assert body['company_research'] is None


# ---------------------------------------------------------------------------
# Basic validation (still valid after async refactor)
# ---------------------------------------------------------------------------


class TestValidation:
    def test_invalid_json_returns_400(self) -> None:
        from careervp.handlers.company_research_handler import lambda_handler

        event = _post_event({})
        event['body'] = '{bad json'
        response = lambda_handler(event, MagicMock())
        assert response['statusCode'] == HTTPStatus.BAD_REQUEST.value

    def test_missing_company_name_returns_400(self) -> None:
        from careervp.handlers.company_research_handler import lambda_handler

        event = _post_event({'domain': 'acme.com'})
        response = lambda_handler(event, MagicMock())
        assert response['statusCode'] == HTTPStatus.BAD_REQUEST.value
