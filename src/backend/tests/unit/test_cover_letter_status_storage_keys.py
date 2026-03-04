"""
Unit tests for cover letter status storage key correctness.

Validates:
- AC-CL-002: Missing cover letter id returns 404 (no synthetic success)
- List queries use canonical pk/sk key schema
- Status lookup finds persisted artifacts via job_id matching

Spec: docs/beta/fix-api/yaml2/cover_letter_list_roundtrip.yaml
"""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-cl-storage-keys-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('ENV', 'local')
    monkeypatch.setenv('TABLE_NAME', 'test-artifacts-table')
    yield


@pytest.fixture
def artifacts_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-artifacts-table',
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
        table.meta.client.get_waiter('table_exists').wait(TableName='test-artifacts-table')
        yield table


def _make_event(
    path: str,
    method: str,
    user_id: str = 'user-abc',
    path_parameters: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        'resource': path,
        'path': path,
        'httpMethod': method,
        'headers': {'Content-Type': 'application/json'},
        'queryStringParameters': None,
        'pathParameters': path_parameters,
        'requestContext': {
            'httpMethod': method,
            'authorizer': {'claims': {'sub': user_id}},
        },
        'body': None,
        'isBase64Encoded': False,
    }


def _context() -> Any:
    ctx = MagicMock()
    ctx.aws_request_id = 'req-test-1'
    ctx.function_name = 'cover-letter-handler'
    return ctx


@pytest.mark.unit
def test_missing_returns_404(artifacts_table: Any) -> None:
    """Status of unknown cover letter id returns 404, not synthetic 200.

    AC-CL-002: No synthetic success path in production code.
    """
    from careervp.handlers.cover_letter_handler import lambda_handler

    event = _make_event(
        path='/cover-letter/does-not-exist-uuid',
        method='GET',
        path_parameters={'coverLetterId': 'does-not-exist-uuid'},
    )

    response = lambda_handler(event, _context())

    assert response['statusCode'] == 404, f'Expected 404 for unknown id, got {response["statusCode"]}'
    body = json.loads(response['body'])
    assert body['code'] == 'COVER_LETTER_NOT_FOUND', f'Expected domain-specific COVER_LETTER_NOT_FOUND code, got {body.get("code")}'


@pytest.mark.unit
def test_status_found_after_persist(artifacts_table: Any) -> None:
    """Status returns 200 when artifact is present in DynamoDB under pk/sk keys."""
    from careervp.handlers.cover_letter_handler import lambda_handler

    user_id = 'user-abc'
    job_id = 'uuid-1111-2222-3333'

    artifacts_table.put_item(
        Item={
            'pk': user_id,
            'sk': f'ARTIFACT#COVER_LETTER#{job_id}',
            'applicationId': user_id,
            'artifactId': f'ARTIFACT#COVER_LETTER#{job_id}',
            'user_id': user_id,
            'job_id': job_id,
            'status': 'COMPLETED',
            'created_at': '2026-03-04T00:00:00+00:00',
            'updated_at': '2026-03-04T00:00:00+00:00',
        }
    )

    event = _make_event(
        path=f'/cover-letter/{job_id}',
        method='GET',
        path_parameters={'coverLetterId': job_id},
    )

    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200, f'Expected 200 for persisted artifact, got {response["statusCode"]}'
    body = json.loads(response['body'])
    assert body['id'] == job_id, f'Expected id == request_id ({job_id}), got {body.get("id")}'


@pytest.mark.unit
def test_list_uses_pk_sk_keys(artifacts_table: Any) -> None:
    """List query uses canonical pk/sk key schema and returns persisted artifacts."""
    from careervp.handlers.cover_letter_handler import lambda_handler

    user_id = 'user-abc'
    job_id = 'uuid-aaaa-bbbb-cccc'

    artifacts_table.put_item(
        Item={
            'pk': user_id,
            'sk': f'ARTIFACT#COVER_LETTER#{job_id}',
            'applicationId': user_id,
            'artifactId': f'ARTIFACT#COVER_LETTER#{job_id}',
            'user_id': user_id,
            'job_id': job_id,
            'status': 'COMPLETED',
            'created_at': '2026-03-04T00:00:00+00:00',
            'updated_at': '2026-03-04T00:00:00+00:00',
        }
    )

    event = _make_event(path='/cover-letters', method='GET')

    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    ids = [item['id'] for item in body['cover_letters']]
    assert job_id in ids, f'Expected job_id {job_id} in list ids {ids} after pk/sk save'


@pytest.mark.unit
def test_user_cannot_read_other_user_artifact(artifacts_table: Any) -> None:
    """User A cannot read User B artifacts via status endpoint."""
    from careervp.handlers.cover_letter_handler import lambda_handler

    user_b = 'user-b-id'
    job_id = 'uuid-user-b-job'

    artifacts_table.put_item(
        Item={
            'pk': user_b,
            'sk': f'ARTIFACT#COVER_LETTER#{job_id}',
            'user_id': user_b,
            'job_id': job_id,
            'status': 'COMPLETED',
        }
    )

    # User A tries to GET User B's artifact
    event = _make_event(
        path=f'/cover-letter/{job_id}',
        method='GET',
        user_id='user-a-id',
        path_parameters={'coverLetterId': job_id},
    )

    response = lambda_handler(event, _context())

    # User A cannot see User B's artifact - pk lookup scoped to user-a-id
    assert response['statusCode'] == 404, f'User A should not see User B artifact, got {response["statusCode"]}'
