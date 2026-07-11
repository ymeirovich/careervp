"""Integration tests for interview prep async roundtrip.

Spec: INTERVIEW_PREP_002
Validates:
  - POST /interview-prep/generate returns 202 with request_id
  - GET /interview-prep/{request_id}/status returns 200 immediately (pending/processing)
  - Artifacts table operations use Key={applicationId, artifactId}
  - artifactId format is ARTIFACT#INTERVIEW_PREP#{request_id}
  - Status polling reaches completed terminal state
  - Unknown request_id returns 404 with INTERVIEW_PREP_NOT_FOUND code
  - Cross-user access returns 404
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _env(
    monkeypatch: pytest.MonkeyPatch,
    mock_artifact_dependency_resolver: Any,
    mock_company_research_load: Any,
) -> Generator[None, None, None]:
    # This roundtrip exercises the submit/status seam, not upstream VPR/CR
    # resolution, so it opts into the dependency-bypass fixtures retired from
    # global autouse (T-02).
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-interview-prep-integration-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('ENV', 'local')
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'test-artifacts-table')
    monkeypatch.setenv('SQS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue')
    yield


@pytest.fixture
def artifacts_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-artifacts-table',
            KeySchema=[
                {'AttributeName': 'applicationId', 'KeyType': 'HASH'},
                {'AttributeName': 'artifactId', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'applicationId', 'AttributeType': 'S'},
                {'AttributeName': 'artifactId', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        table.meta.client.get_waiter('table_exists').wait(TableName='test-artifacts-table')
        yield table


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ARTIFACT_ID_PREFIX = 'ARTIFACT#INTERVIEW_PREP#'


def _post_event(user_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return {
        'path': '/interview-prep/generate',
        'httpMethod': 'POST',
        'headers': {'Content-Type': 'application/json'},
        'requestContext': {
            'requestId': 'req-test',
            'authorizer': {'claims': {'sub': user_id}},
        },
        'body': json.dumps(body),
        'pathParameters': None,
    }


def _get_status_event(user_id: str, request_id: str) -> dict[str, Any]:
    return {
        'path': f'/interview-prep/{request_id}/status',
        'httpMethod': 'GET',
        'headers': {'Content-Type': 'application/json'},
        'requestContext': {
            'requestId': 'req-test',
            'authorizer': {'claims': {'sub': user_id}},
        },
        'body': None,
        'pathParameters': {'interviewPrepId': request_id},
    }


def _context() -> Any:
    ctx = MagicMock()
    ctx.aws_request_id = 'req-test'
    ctx.function_name = 'interview-prep-test'
    return ctx


def _valid_request_body() -> dict[str, Any]:
    return {
        'vpr_id': 'vpr-integration-001',
        'gap_response_ids': ['gap-001'],
        'focus_areas': ['technical', 'behavioral'],
        'question_count': 5,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_submit_returns_202_with_request_id(artifacts_table: Any) -> None:
    """POST /interview-prep/generate returns 202 Accepted with request_id."""
    from careervp.handlers import interview_prep_submit_handler as submit_module

    mock_sqs = MagicMock()

    with patch.object(submit_module, 'sqs', mock_sqs), patch.object(submit_module, 'dynamodb_resource') as mock_dynamo:
        mock_dynamo.Table.return_value = artifacts_table

        event = _post_event('user-integration-1', _valid_request_body())
        response = submit_module.lambda_handler(event, _context())

    assert response['statusCode'] == 202
    body = json.loads(response['body'])
    assert 'request_id' in body
    assert body['request_id']
    assert body.get('status') == 'processing'
    mock_sqs.send_message.assert_called_once()


def test_submit_writes_pending_artifact_with_artifacts_schema(artifacts_table: Any) -> None:
    """POST /interview-prep/generate writes artifact with applicationId/artifactId key schema."""
    from careervp.handlers import interview_prep_submit_handler as submit_module

    user_id = 'user-integration-2'
    mock_sqs = MagicMock()

    with patch.object(submit_module, 'sqs', mock_sqs), patch.object(submit_module, 'dynamodb_resource') as mock_dynamo:
        mock_dynamo.Table.return_value = artifacts_table

        event = _post_event(user_id, _valid_request_body())
        response = submit_module.lambda_handler(event, _context())

    assert response['statusCode'] == 202
    request_id = json.loads(response['body'])['request_id']

    # Verify artifact written using applicationId/artifactId key schema
    expected_artifact_id = f'{ARTIFACT_ID_PREFIX}{request_id}'
    stored = artifacts_table.get_item(Key={'applicationId': user_id, 'artifactId': expected_artifact_id})
    item = stored.get('Item')
    assert item is not None, f'Expected artifact at Key={{applicationId={user_id!r}, artifactId={expected_artifact_id!r}}}; not found.'
    assert item['applicationId'] == user_id
    assert item['artifactId'] == expected_artifact_id
    assert item['status'].upper() == 'PENDING'


def test_status_readable_immediately_after_submit(artifacts_table: Any) -> None:
    """GET /interview-prep/{request_id}/status returns 200 immediately after submit."""
    from careervp.handlers import interview_prep_handler as status_module
    from careervp.handlers import interview_prep_submit_handler as submit_module

    user_id = 'user-integration-3'
    mock_sqs = MagicMock()

    with patch.object(submit_module, 'sqs', mock_sqs), patch.object(submit_module, 'dynamodb_resource') as mock_dynamo:
        mock_dynamo.Table.return_value = artifacts_table
        submit_response = submit_module.lambda_handler(_post_event(user_id, _valid_request_body()), _context())

    assert submit_response['statusCode'] == 202
    request_id = json.loads(submit_response['body'])['request_id']

    # Immediately poll status
    status_response = status_module.lambda_handler(_get_status_event(user_id, request_id), _context())

    assert status_response['statusCode'] == 200, (
        f'Expected 200 for status lookup of request_id={request_id!r}. Got {status_response["statusCode"]}: {status_response["body"]}'
    )
    payload = json.loads(status_response['body'])
    assert payload['id'] == request_id
    assert payload['status'] in {'pending', 'processing', 'completed', 'failed'}


def test_request_id_suffix_matches_artifact_id_format(artifacts_table: Any) -> None:
    """The request_id from POST is exactly the suffix after ARTIFACT#INTERVIEW_PREP# in artifactId."""
    from careervp.handlers import interview_prep_submit_handler as submit_module

    user_id = 'user-integration-4'
    mock_sqs = MagicMock()

    with patch.object(submit_module, 'sqs', mock_sqs), patch.object(submit_module, 'dynamodb_resource') as mock_dynamo:
        mock_dynamo.Table.return_value = artifacts_table
        response = submit_module.lambda_handler(_post_event(user_id, _valid_request_body()), _context())

    request_id = json.loads(response['body'])['request_id']
    expected_artifact_id = f'{ARTIFACT_ID_PREFIX}{request_id}'

    stored = artifacts_table.get_item(Key={'applicationId': user_id, 'artifactId': expected_artifact_id})
    item = stored.get('Item')
    assert item is not None
    assert item['artifactId'] == expected_artifact_id
    assert item['job_id'] == request_id


def test_unknown_request_id_returns_404_with_domain_code(artifacts_table: Any) -> None:
    """GET /interview-prep/{unknown_id}/status returns 404 with INTERVIEW_PREP_NOT_FOUND code."""
    from careervp.handlers import interview_prep_handler as status_module
    from careervp.models.result import ResultCode

    response = status_module.lambda_handler(_get_status_event('user-any', 'does-not-exist-xyzabc'), _context())

    assert response['statusCode'] == 404
    payload = json.loads(response['body'])
    assert payload['code'] == ResultCode.INTERVIEW_PREP_NOT_FOUND
    assert payload['code'] != 'CV_NOT_FOUND'


def test_cross_user_status_returns_404(artifacts_table: Any) -> None:
    """GET /interview-prep/{request_id}/status returns 404 for a different user's artifact."""
    from careervp.handlers import interview_prep_handler as status_module
    from careervp.handlers import interview_prep_submit_handler as submit_module
    from careervp.models.result import ResultCode

    owner_id = 'user-owner-5'
    other_id = 'user-other-5'
    mock_sqs = MagicMock()

    with patch.object(submit_module, 'sqs', mock_sqs), patch.object(submit_module, 'dynamodb_resource') as mock_dynamo:
        mock_dynamo.Table.return_value = artifacts_table
        submit_response = submit_module.lambda_handler(_post_event(owner_id, _valid_request_body()), _context())

    request_id = json.loads(submit_response['body'])['request_id']

    # Different user tries to access owner's artifact
    response = status_module.lambda_handler(_get_status_event(other_id, request_id), _context())

    assert response['statusCode'] == 404
    payload = json.loads(response['body'])
    assert payload['code'] == ResultCode.INTERVIEW_PREP_NOT_FOUND


def test_completed_artifact_status_returns_full_payload(artifacts_table: Any) -> None:
    """Status endpoint returns questions/result payload when artifact is COMPLETED."""
    from careervp.handlers import interview_prep_handler as status_module

    user_id = 'user-integration-6'
    request_id = str(uuid.uuid4())
    artifact_id = f'{ARTIFACT_ID_PREFIX}{request_id}'
    now = datetime.now(timezone.utc).isoformat()

    artifacts_table.put_item(
        Item={
            'applicationId': user_id,
            'artifactId': artifact_id,
            'artifactType': 'interview_prep',
            'user_id': user_id,
            'job_id': request_id,
            'status': 'COMPLETED',
            'interview_prep': {
                'prep_id': request_id,
                'questions': [
                    {
                        'question_id': 'q1',
                        'question': 'Describe a distributed systems design challenge.',
                        'question_type': 'technical',
                        'suggested_answer': {
                            'format': 'STAR',
                            'situation': 'Latency spikes under peak load.',
                            'task': 'Reduce p99 under tight deadline.',
                            'action': 'Introduced async workers and caching layer.',
                            'result': 'p99 dropped 40%, on-time delivery.',
                        },
                    }
                ],
                'questions_to_ask': [{'question': 'What defines success in first 90 days?', 'purpose': 'Aligns expectations.'}],
                'pre_interview_checklist': ['Prepare STAR answers with metrics.'],
                'readiness_summary': 'Well-prepared for technical and behavioral rounds.',
            },
            'created_at': now,
            'updated_at': now,
            'expiration': 9999999999,
        }
    )

    response = status_module.lambda_handler(_get_status_event(user_id, request_id), _context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['id'] == request_id
    assert payload['status'] == 'completed'
    result = payload.get('result', {})
    questions = result.get('questions', [])
    assert len(questions) == 1
    assert questions[0]['id'] == 'q1'
    assert questions[0]['text'] == 'Describe a distributed systems design challenge.'
    assert questions[0]['suggested_answer']['format'] == 'STAR'
