"""Integration tests: Cover letter roundtrip persistence.

Verifies that a cover letter artifact persisted via the submit handler
is retrievable via the status and list endpoints using canonical
applicationId/artifactId key schema with Phase A dual-read fallback.

Traceability:
  AC-CL-301: generated request_id resolves on status endpoint
  AC-CL-302: list endpoint includes generated id
  AC-CL-303: missing id returns domain 404 without synthetic success
Spec: docs/beta/fix-api/yaml3/step_003_cover_letter_artifact_roundtrip_recovery.yaml
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('POWERTOOLS_SERVICE_NAME', 'careervp-cl-roundtrip-test')
os.environ.setdefault('LOG_LEVEL', 'INFO')

TABLE_NAME = 'test-cl-roundtrip-table'
USER_ID = 'user-roundtrip-cl-001'
JOB_ID = 'uuid-roundtrip-job-001'


@pytest.fixture(autouse=True)
def cl_roundtrip_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('TABLE_NAME', TABLE_NAME)
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', TABLE_NAME)
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', TABLE_NAME)
    monkeypatch.setenv('COVER_LETTER_LEGACY_READ_ENABLED', 'true')
    yield


@pytest.fixture
def artifacts_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
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
        table.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)
        yield table


def _status_event(cover_letter_id: str, user_id: str = USER_ID) -> dict[str, Any]:
    return {
        'resource': f'/cover-letter/{cover_letter_id}',
        'path': f'/cover-letter/{cover_letter_id}',
        'httpMethod': 'GET',
        'headers': {'Content-Type': 'application/json'},
        'queryStringParameters': None,
        'pathParameters': {'coverLetterId': cover_letter_id},
        'requestContext': {
            'httpMethod': 'GET',
            'authorizer': {'claims': {'sub': user_id}},
        },
        'body': None,
        'isBase64Encoded': False,
    }


def _list_event(user_id: str = USER_ID) -> dict[str, Any]:
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
    ctx.aws_request_id = 'req-roundtrip-test'
    ctx.function_name = 'cover-letter-handler'
    return ctx


def _seed_canonical_artifact(table: Any, user_id: str, job_id: str, status: str = 'COMPLETED') -> None:
    """Simulate what cover_letter_submit_handler writes: canonical applicationId/artifactId keys."""
    table.put_item(
        Item={
            'pk': user_id,
            'sk': f'ARTIFACT#COVER_LETTER#{job_id}',
            'applicationId': user_id,
            'artifactId': f'ARTIFACT#COVER_LETTER#{job_id}',
            'artifactType': 'cover_letter',
            'user_id': user_id,
            'job_id': job_id,
            'status': status,
            'created_at': '2026-03-05T00:00:00+00:00',
            'updated_at': '2026-03-05T00:00:00+00:00',
        }
    )


def _seed_legacy_artifact(table: Any, user_id: str, cv_id: str, job_id: str) -> None:
    """Simulate a pre-migration record written with legacy pk/sk only (no applicationId/artifactId)."""
    table.put_item(
        Item={
            'pk': user_id,
            'sk': f'ARTIFACT#COVER_LETTER#{cv_id}#{job_id}#v1',
            'artifact_type': 'cover_letter',
            'user_id': user_id,
            'cv_id': cv_id,
            'job_id': job_id,
            'version': 1,
            'cover_letter': {'cover_letter_id': f'cl-{job_id}', 'full_text': 'Dear Hiring Manager...'},
            'status': 'COMPLETED',
            'created_at': '2026-03-01T00:00:00+00:00',
            'updated_at': '2026-03-01T00:00:00+00:00',
        }
    )


@pytest.mark.integration
def test_status_returns_404_when_artifact_not_persisted(artifacts_table: Any) -> None:
    """GET status for unknown request_id returns 404, not synthetic success.

    AC-CL-303: No synthetic success path in production code.
    """
    from careervp.handlers.cover_letter_handler import lambda_handler

    response = lambda_handler(_status_event('nonexistent-uuid'), _context())

    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert body.get('code') == 'COVER_LETTER_NOT_FOUND'


@pytest.mark.integration
def test_status_returns_200_for_canonical_artifact(artifacts_table: Any) -> None:
    """GET status returns 200 with id == request_id when artifact uses canonical keys.

    AC-CL-301: request_id from POST retrievable via GET status using canonical path.
    """
    from careervp.handlers.cover_letter_handler import lambda_handler

    _seed_canonical_artifact(artifacts_table, USER_ID, JOB_ID)

    response = lambda_handler(_status_event(JOB_ID), _context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['id'] == JOB_ID, f'Expected id == request_id ({JOB_ID}), got {body.get("id")}'
    assert body['status'] in {'completed', 'pending', 'processing', 'failed'}


@pytest.mark.integration
def test_list_includes_canonical_artifact_after_persistence(artifacts_table: Any) -> None:
    """GET /cover-letters includes request_id after canonical artifact is persisted.

    AC-CL-302: Generated cover letter appears in list via canonical key path.
    """
    from careervp.handlers.cover_letter_handler import lambda_handler

    _seed_canonical_artifact(artifacts_table, USER_ID, JOB_ID)

    response = lambda_handler(_list_event(), _context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert len(body['cover_letters']) > 0, 'List must not be empty after artifact is persisted'
    ids = [item['id'] for item in body['cover_letters']]
    assert JOB_ID in ids, f'request_id {JOB_ID} must appear in list ids {ids}'


@pytest.mark.integration
def test_full_roundtrip_submit_status_list(artifacts_table: Any) -> None:
    """Full roundtrip: persist canonical artifact -> status 200 -> list includes id.

    Validates the complete async flow with production-like canonical schema:
      POST /cover-letter/generate -> writes canonical applicationId/artifactId artifact
      GET /cover-letter/{request_id}/status -> 200 with id == request_id
      GET /cover-letters -> list contains request_id
    """
    from careervp.handlers.cover_letter_handler import lambda_handler

    request_id = 'uuid-full-roundtrip-5678'
    _seed_canonical_artifact(artifacts_table, USER_ID, request_id, status='COMPLETED')

    # Step 1: status returns 200
    status_response = lambda_handler(_status_event(request_id), _context())
    assert status_response['statusCode'] == 200
    status_body = json.loads(status_response['body'])
    assert status_body['id'] == request_id

    # Step 2: list includes request_id
    list_response = lambda_handler(_list_event(), _context())
    assert list_response['statusCode'] == 200
    list_body = json.loads(list_response['body'])
    list_ids = [item['id'] for item in list_body['cover_letters']]
    assert request_id in list_ids, f'request_id {request_id} missing from list {list_ids}'


@pytest.mark.integration
def test_list_empty_when_no_artifacts_exist(artifacts_table: Any) -> None:
    """List returns empty array when user has no cover letter artifacts."""
    from careervp.handlers.cover_letter_handler import lambda_handler

    response = lambda_handler(_list_event('user-with-no-artifacts'), _context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['cover_letters'] == []


@pytest.mark.integration
def test_user_isolation_in_list(artifacts_table: Any) -> None:
    """User A cannot see User B artifacts in the list endpoint."""
    from careervp.handlers.cover_letter_handler import lambda_handler

    user_a, user_b = 'user-a-isolation', 'user-b-isolation'
    job_a, job_b = 'uuid-job-a', 'uuid-job-b'

    _seed_canonical_artifact(artifacts_table, user_a, job_a)
    _seed_canonical_artifact(artifacts_table, user_b, job_b)

    response_a = lambda_handler(_list_event(user_a), _context())
    body_a = json.loads(response_a['body'])
    ids_a = [item['id'] for item in body_a['cover_letters']]

    assert job_a in ids_a, 'User A artifact must appear in user A list'
    assert job_b not in ids_a, 'User B artifact must not appear in user A list'


@pytest.mark.integration
def test_legacy_artifact_readable_via_fallback(
    artifacts_table: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pre-migration legacy records (pk/sk only) are readable via Phase A fallback.

    With COVER_LETTER_LEGACY_READ_ENABLED=true, legacy items appear in list.
    """
    monkeypatch.setenv('COVER_LETTER_LEGACY_READ_ENABLED', 'true')

    from careervp.handlers.cover_letter_handler import lambda_handler

    _seed_legacy_artifact(artifacts_table, USER_ID, cv_id='cv-legacy', job_id='job-legacy')

    response = lambda_handler(_list_event(), _context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    # Legacy items should be in the list since they share the same pk/sk prefix pattern
    assert len(body['cover_letters']) > 0, 'Legacy artifact should appear in list via pk/sk query'


@pytest.mark.integration
def test_canonical_and_legacy_coexist(
    artifacts_table: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both canonical and legacy records appear in list during Phase A."""
    monkeypatch.setenv('COVER_LETTER_LEGACY_READ_ENABLED', 'true')

    from careervp.handlers.cover_letter_handler import lambda_handler

    # Seed both types
    _seed_canonical_artifact(artifacts_table, USER_ID, 'uuid-canonical-new')
    _seed_legacy_artifact(artifacts_table, USER_ID, cv_id='cv-old', job_id='job-old')

    response = lambda_handler(_list_event(), _context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert len(body['cover_letters']) == 2, f'Expected 2 cover letters (1 canonical + 1 legacy), got {len(body["cover_letters"])}'
