"""
Unit tests for cover letter status storage key correctness.

Validates:
- AC-CL-301: generated request_id resolves on status endpoint via canonical keys
- AC-CL-303: Missing cover letter id returns 404 (no synthetic success)
- Canonical applicationId/artifactId key usage
- Legacy fallback only invoked on canonical miss when enabled

Spec: docs/beta/fix-api/yaml3/step_003_cover_letter_artifact_roundtrip_recovery.yaml
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
    monkeypatch.setenv('COVER_LETTER_LEGACY_READ_ENABLED', 'false')
    monkeypatch.delenv('DYNAMODB_TABLE_NAME', raising=False)
    monkeypatch.delenv('ARTIFACTS_TABLE_NAME', raising=False)
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

    AC-CL-303: No synthetic success path in production code.
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
def test_status_found_via_canonical_keys(artifacts_table: Any) -> None:
    """Status returns 200 when artifact is found via canonical applicationId/artifactId keys.

    AC-CL-301: request_id resolves on status endpoint via canonical key path.
    """
    from careervp.handlers.cover_letter_handler import lambda_handler

    user_id = 'user-abc'
    job_id = 'uuid-1111-2222-3333'

    # Write with canonical keys: pk=applicationId, sk=artifactId
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
def test_list_uses_canonical_keys(artifacts_table: Any) -> None:
    """List query uses canonical applicationId/artifactId key schema and returns persisted artifacts."""
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
    assert job_id in ids, f'Expected job_id {job_id} in list ids {ids} after canonical key save'


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
            'applicationId': user_b,
            'artifactId': f'ARTIFACT#COVER_LETTER#{job_id}',
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


@pytest.mark.unit
def test_legacy_fallback_not_invoked_for_new_canonical_records(
    artifacts_table: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """For new records written with canonical keys, legacy fallback should not be needed.

    With COVER_LETTER_LEGACY_READ_ENABLED=false, canonical read must still find new records.
    """
    monkeypatch.setenv('COVER_LETTER_LEGACY_READ_ENABLED', 'false')

    from careervp.handlers.cover_letter_handler import lambda_handler

    user_id = 'user-abc'
    job_id = 'uuid-canonical-only-1234'

    # Write canonical record (pk=applicationId, sk=artifactId)
    artifacts_table.put_item(
        Item={
            'pk': user_id,
            'sk': f'ARTIFACT#COVER_LETTER#{job_id}',
            'applicationId': user_id,
            'artifactId': f'ARTIFACT#COVER_LETTER#{job_id}',
            'user_id': user_id,
            'job_id': job_id,
            'status': 'COMPLETED',
            'created_at': '2026-03-05T00:00:00+00:00',
            'updated_at': '2026-03-05T00:00:00+00:00',
        }
    )

    event = _make_event(
        path=f'/cover-letter/{job_id}',
        method='GET',
        path_parameters={'coverLetterId': job_id},
    )

    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200, f'Canonical record must be readable even with legacy fallback disabled, got {response["statusCode"]}'
    body = json.loads(response['body'])
    assert body['id'] == job_id


@pytest.mark.unit
def test_dal_canonical_read_method(artifacts_table: Any) -> None:
    """DAL read_cover_letter_by_artifact_id returns item via canonical key."""
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    user_id = 'user-abc'
    job_id = 'uuid-dal-read-test'
    artifact_id = f'ARTIFACT#COVER_LETTER#{job_id}'

    artifacts_table.put_item(
        Item={
            'pk': user_id,
            'sk': artifact_id,
            'applicationId': user_id,
            'artifactId': artifact_id,
            'job_id': job_id,
            'status': 'COMPLETED',
        }
    )

    dal = DynamoDalHandler('test-artifacts-table')
    result = dal.read_cover_letter_by_artifact_id(user_id, artifact_id)

    assert result.success, f'canonical read failed: {result.error}'
    assert result.data is not None, 'canonical read returned None for existing record'
    assert result.data['job_id'] == job_id


@pytest.mark.unit
def test_dal_legacy_read_disabled_returns_none(
    artifacts_table: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When COVER_LETTER_LEGACY_READ_ENABLED=false, legacy_read_cover_letter returns None."""
    monkeypatch.setenv('COVER_LETTER_LEGACY_READ_ENABLED', 'false')

    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    artifacts_table.put_item(
        Item={
            'pk': 'user-abc',
            'sk': 'ARTIFACT#COVER_LETTER#cv-1#job-1#v1',
            'status': 'COMPLETED',
        }
    )

    dal = DynamoDalHandler('test-artifacts-table')
    result = dal.legacy_read_cover_letter('user-abc', 'ARTIFACT#COVER_LETTER#cv-1#job-1#v1')

    assert result.success
    assert result.data is None, 'Legacy read should return None when disabled'


@pytest.mark.unit
def test_failed_status_includes_error_diagnostics(artifacts_table: Any) -> None:
    """Failed status payload surfaces stored worker diagnostics."""
    from careervp.handlers.cover_letter_handler import lambda_handler

    user_id = 'user-abc'
    job_id = 'uuid-failed-job-1'
    artifact_id = f'ARTIFACT#COVER_LETTER#{job_id}'

    artifacts_table.put_item(
        Item={
            'pk': user_id,
            'sk': artifact_id,
            'applicationId': user_id,
            'artifactId': artifact_id,
            'job_id': job_id,
            'status': 'FAILED',
            'error': 'AccessDeniedException: not authorized to call ssm:GetParameter',
            'code': 'AccessDeniedException',
            'error_type': 'ClientError',
        }
    )

    event = _make_event(
        path=f'/cover-letter/{job_id}',
        method='GET',
        path_parameters={'coverLetterId': job_id},
    )

    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['status'] == 'failed'
    assert body['error'] == 'AccessDeniedException: not authorized to call ssm:GetParameter'
    assert body['code'] == 'AccessDeniedException'
    assert isinstance(body.get('result'), dict)
    assert body['result']['error_type'] == 'ClientError'
