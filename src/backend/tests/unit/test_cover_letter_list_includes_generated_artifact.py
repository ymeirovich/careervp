"""
Unit tests verifying the list endpoint includes generated cover letter artifacts.

Validates:
- AC-CL-001: Generated cover letter appears in list after save
- List materializes IDs from artifactId / job_id fields
- Both async-path (submit handler) and sync-path (save_cover_letter) items appear

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
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-cl-list-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('ENV', 'local')
    monkeypatch.setenv('TABLE_NAME', 'test-artifacts-list-table')
    yield


@pytest.fixture
def artifacts_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-artifacts-list-table',
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
        table.meta.client.get_waiter('table_exists').wait(TableName='test-artifacts-list-table')
        yield table


def _list_event(user_id: str = 'user-test') -> dict[str, Any]:
    return {
        'resource': '/cover-letters',
        'path': '/cover-letters',
        'httpMethod': 'GET',
        'headers': {'Content-Type': 'application/json'},
        'queryStringParameters': None,
        'pathParameters': None,
        'requestContext': {
            'httpMethod': 'GET',
            'authorizer': {'claims': {'sub': user_id}},
        },
        'body': None,
        'isBase64Encoded': False,
    }


def _context() -> Any:
    ctx = MagicMock()
    ctx.aws_request_id = 'req-list-test'
    ctx.function_name = 'cover-letter-handler'
    return ctx


@pytest.mark.unit
def test_list_empty_when_no_artifacts(artifacts_table: Any) -> None:
    """List returns empty array when no cover letter artifacts exist."""
    from careervp.handlers.cover_letter_handler import lambda_handler

    response = lambda_handler(_list_event(), _context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['cover_letters'] == []


@pytest.mark.unit
def test_list_includes_async_artifact_by_job_id(artifacts_table: Any) -> None:
    """Generated async-path artifact (job_id UUID) appears in list with id == job_id.

    AC-CL-001: request_id from POST must appear in GET /cover-letters list.
    """
    from careervp.handlers.cover_letter_handler import lambda_handler

    user_id = 'user-test'
    job_id = 'uuid-async-artifact-1234'

    # Simulate what cover_letter_submit_handler.py writes to DynamoDB
    artifacts_table.put_item(
        Item={
            'pk': user_id,
            'sk': f'ARTIFACT#COVER_LETTER#{job_id}',
            'applicationId': user_id,
            'artifactId': f'ARTIFACT#COVER_LETTER#{job_id}',
            'artifactType': 'cover_letter',
            'user_id': user_id,
            'job_id': job_id,
            'status': 'COMPLETED',
            'created_at': '2026-03-04T00:00:00+00:00',
            'updated_at': '2026-03-04T00:00:00+00:00',
        }
    )

    response = lambda_handler(_list_event(user_id), _context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert len(body['cover_letters']) == 1, f'Expected 1 cover letter in list, got {len(body["cover_letters"])}'
    assert body['cover_letters'][0]['id'] == job_id, f'Expected id == job_id ({job_id}), got {body["cover_letters"][0].get("id")}'


@pytest.mark.unit
def test_list_includes_sync_artifact_with_cover_letter_id(artifacts_table: Any) -> None:
    """Sync-path artifact (saved by DAL save_cover_letter) appears in list."""
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler
    from careervp.handlers.cover_letter_handler import lambda_handler

    user_id = 'user-test'
    cv_id = 'cv-111'
    job_id = 'job-222'
    cover_letter_id = 'cl-uuid-sync-9999'

    dal = DynamoDalHandler('test-artifacts-list-table')
    result = dal.save_cover_letter(
        cover_letter={'cover_letter_id': cover_letter_id, 'full_text': 'Dear Hiring Manager...'},
        user_id=user_id,
        cv_id=cv_id,
        job_id=job_id,
    )
    assert result.success, f'save_cover_letter failed: {result.error}'

    response = lambda_handler(_list_event(user_id), _context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert len(body['cover_letters']) >= 1, 'Expected at least 1 cover letter after save'
    ids = [item['id'] for item in body['cover_letters']]
    assert cover_letter_id in ids, f'Expected cover_letter_id {cover_letter_id} in list ids {ids}'


@pytest.mark.unit
def test_list_only_returns_current_user_artifacts(artifacts_table: Any) -> None:
    """List scoped to authenticated user - other users' artifacts not returned."""
    from careervp.handlers.cover_letter_handler import lambda_handler

    user_a = 'user-a-id'
    user_b = 'user-b-id'
    job_id_a = 'uuid-user-a-job'
    job_id_b = 'uuid-user-b-job'

    for uid, jid in [(user_a, job_id_a), (user_b, job_id_b)]:
        artifacts_table.put_item(
            Item={
                'pk': uid,
                'sk': f'ARTIFACT#COVER_LETTER#{jid}',
                'user_id': uid,
                'job_id': jid,
                'status': 'COMPLETED',
            }
        )

    response = lambda_handler(_list_event(user_a), _context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    ids = [item['id'] for item in body['cover_letters']]
    assert job_id_a in ids, 'Expected user A artifact in list'
    assert job_id_b not in ids, 'User B artifact must not appear in user A list'
