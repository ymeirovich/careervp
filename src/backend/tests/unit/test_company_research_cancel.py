"""TEST-CANCEL-001 § unit-cr-cancel: new CR cancel endpoint (4 tests).

The company_research_handler must expose:
  POST /company-research/{jobId}/cancel

with ownership check, CONFLICT on terminal, and shared cancel orchestration —
mirroring _handle_vpr_cancel, _handle_cover_letter_cancel, etc.

All 4 tests are RED until _handle_company_research_cancel is added.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

_ENV = {
    'POWERTOOLS_SERVICE_NAME': 'test',
    'LOG_LEVEL': 'WARNING',
    'DYNAMODB_TABLE_NAME': 'test-table',
    'ARTIFACTS_TABLE_NAME': 'test-artifacts',
    'APPLICATIONS_TABLE_NAME': 'test-apps',
    'VPR_RESULTS_BUCKET_NAME': 'test-bucket',
    'KNOWLEDGE_TABLE_NAME': 'test-knowledge',
}

_USER_ID = 'user-42'
_JOB_ID = 'cr-job-abc'


def _make_cancel_event(
    job_id: str = _JOB_ID,
    *,
    user_id: str | None = _USER_ID,
) -> dict:
    return {
        'httpMethod': 'POST',
        'path': f'/company-research/{job_id}/cancel',
        'pathParameters': {'jobId': job_id},
        'requestContext': {'authorizer': {'principalId': user_id} if user_id else {}},
        'headers': {'Authorization': f'Bearer tok-{user_id}' if user_id else ''},
        'body': '{}',
    }


def _item(
    *,
    status: str = 'PROCESSING',
    owner: str = _USER_ID,
    job_id: str = _JOB_ID,
) -> dict:
    """Build a minimal CR DynamoDB item."""
    return {
        'pk': owner,
        'sk': f'COMPANY_RESEARCH#{job_id}',
        'job_id': job_id,
        'user_id': owner,
        'status': status,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch.dict(os.environ, _ENV)
def test_cr_cancel_happy_path_returns_cancelled() -> None:
    """POST /company-research/{jobId}/cancel by the owner returns 200 {'status':'cancelled'}."""
    from careervp.handlers.company_research_handler import lambda_handler

    with (
        patch('careervp.handlers.company_research_handler._get_company_research_item') as mock_get,
        patch('careervp.handlers.company_research_handler.extract_user_id', return_value=_USER_ID),
        patch('boto3.resource') as mock_boto3,
        patch('careervp.handlers.company_research_handler.cancel_artifact') as mock_cancel,
    ):
        mock_get.return_value = _item()
        mock_table = MagicMock()
        mock_boto3.return_value.Table.return_value = mock_table
        mock_cancel.return_value = MagicMock(status='cancelled')

        response = lambda_handler(_make_cancel_event(), MagicMock())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body.get('status') == 'cancelled'


@patch.dict(os.environ, _ENV)
def test_cr_cancel_conflict_on_terminal_status() -> None:
    """If the CR job is already COMPLETED / FAILED / CANCELLED the endpoint
    must return 409 CONFLICT."""
    from careervp.handlers.company_research_handler import lambda_handler

    for terminal in ('COMPLETED', 'FAILED', 'CANCELLED'):
        with (
            patch('careervp.handlers.company_research_handler._get_company_research_item') as mock_get,
            patch('careervp.handlers.company_research_handler.extract_user_id', return_value=_USER_ID),
        ):
            mock_get.return_value = _item(status=terminal)

            response = lambda_handler(_make_cancel_event(), MagicMock())

        assert response['statusCode'] == 409, f'Expected 409 CONFLICT for terminal status {terminal!r}, got {response["statusCode"]}'
        body = json.loads(response['body'])
        assert 'cancel' in body.get('error', '').lower() or 'terminal' in body.get('error', '').lower()


@patch.dict(os.environ, _ENV)
def test_cr_cancel_forbidden_for_non_owner() -> None:
    """A user who does not own the CR job must receive 403 FORBIDDEN."""
    from careervp.handlers.company_research_handler import lambda_handler

    other_user = 'user-99'
    with (
        patch('careervp.handlers.company_research_handler._get_company_research_item') as mock_get,
        patch('careervp.handlers.company_research_handler.extract_user_id', return_value='user-1'),
    ):
        # Item owned by other_user
        mock_get.return_value = _item(owner=other_user)

        response = lambda_handler(_make_cancel_event(user_id='user-1'), MagicMock())

    assert response['statusCode'] == 403


@patch.dict(os.environ, _ENV)
def test_cr_cancel_returns_400_when_job_id_missing() -> None:
    """POST /company-research//cancel (missing jobId) must return 400."""
    from careervp.handlers.company_research_handler import lambda_handler

    bad_event = {
        'httpMethod': 'POST',
        'path': '/company-research//cancel',
        'pathParameters': {},
        'requestContext': {'authorizer': {'principalId': _USER_ID}},
        'headers': {},
        'body': '{}',
    }

    with patch('careervp.handlers.company_research_handler.extract_user_id', return_value=_USER_ID):
        response = lambda_handler(bad_event, MagicMock())

    assert response['statusCode'] == 400
