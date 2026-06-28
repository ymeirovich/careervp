"""Unit tests for VPR cancel endpoint — RED phase (cancel not yet implemented)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-artifacts-table')
    monkeypatch.setenv('VPR_JOBS_TABLE_NAME', 'test-vpr-jobs-table')


def _cancel_event(path: str, path_params: dict[str, str], user_id: str = 'user-123') -> dict[str, object]:
    return {
        'httpMethod': 'POST',
        'path': path,
        'pathParameters': path_params,
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
        'body': None,
    }


def _context() -> SimpleNamespace:
    return SimpleNamespace(
        aws_request_id='req-test',
        function_name='vpr-handler',
        memory_limit_in_mb=256,
        invoked_function_arn='arn:aws:lambda:us-east-1:123456789:function:vpr-handler',
    )


def test_vpr_cancel_no_auth_returns_401() -> None:
    from careervp.handlers import vpr_status_handler as module

    event: dict[str, object] = {
        'httpMethod': 'POST',
        'path': '/vpr/task-1/cancel',
        'pathParameters': {'vprId': 'task-1'},
        'requestContext': {},
        'body': None,
    }
    mock_jobs_repo = MagicMock()
    with (
        patch.object(module, 'jobs_repo', mock_jobs_repo, create=True),
        patch.object(module, 'JobsRepository', return_value=mock_jobs_repo),
        patch.object(module, 's3'),
    ):
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 401


def test_vpr_cancel_task_not_found_returns_404() -> None:
    from careervp.handlers import vpr_status_handler as module

    event = _cancel_event('/vpr/missing-id/cancel', {'vprId': 'missing-id'})
    mock_jobs_repo = MagicMock()
    mock_jobs_repo.get_job.return_value = None
    mock_s3 = MagicMock()
    mock_s3.head_object.side_effect = Exception('Key not in S3')
    with (
        patch.object(module, 'jobs_repo', mock_jobs_repo, create=True),
        patch.object(module, 'JobsRepository', return_value=mock_jobs_repo),
        patch.object(module, 's3', mock_s3),
    ):
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 404


def test_vpr_cancel_wrong_owner_returns_403() -> None:
    from careervp.handlers import vpr_status_handler as module

    event = _cancel_event('/vpr/task-1/cancel', {'vprId': 'task-1'}, user_id='caller-456')
    mock_jobs_repo = MagicMock()
    mock_jobs_repo.get_job.return_value = {'user_id': 'real-owner-123', 'status': 'PENDING'}
    with (
        patch.object(module, 'jobs_repo', mock_jobs_repo, create=True),
        patch.object(module, 'JobsRepository', return_value=mock_jobs_repo),
        patch.object(module, 's3'),
    ):
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 403


def test_vpr_cancel_pending_returns_200_and_calls_update() -> None:
    from careervp.handlers import vpr_status_handler as module

    event = _cancel_event('/vpr/task-1/cancel', {'vprId': 'task-1'})
    mock_jobs_repo = MagicMock()
    mock_jobs_repo.get_job.return_value = {'user_id': 'user-123', 'status': 'PENDING'}
    with (
        patch.object(module, 'jobs_repo', mock_jobs_repo, create=True),
        patch.object(module, 'JobsRepository', return_value=mock_jobs_repo),
        patch.object(module, 's3'),
    ):
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 200
    mock_jobs_repo.update_job_status.assert_called_once_with('task-1', 'CANCELLED')


def test_vpr_cancel_processing_returns_200_and_calls_update() -> None:
    from careervp.handlers import vpr_status_handler as module

    event = _cancel_event('/vpr/task-1/cancel', {'vprId': 'task-1'})
    mock_jobs_repo = MagicMock()
    mock_jobs_repo.get_job.return_value = {'user_id': 'user-123', 'status': 'PROCESSING'}
    with (
        patch.object(module, 'jobs_repo', mock_jobs_repo, create=True),
        patch.object(module, 'JobsRepository', return_value=mock_jobs_repo),
        patch.object(module, 's3'),
    ):
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 200
    mock_jobs_repo.update_job_status.assert_called_once_with('task-1', 'CANCELLED')


def test_vpr_cancel_completed_returns_409_no_update() -> None:
    from careervp.handlers import vpr_status_handler as module

    event = _cancel_event('/vpr/task-1/cancel', {'vprId': 'task-1'})
    mock_jobs_repo = MagicMock()
    mock_jobs_repo.get_job.return_value = {
        'user_id': 'user-123',
        'status': 'COMPLETED',
        'result': {'uvp': 'value prop'},
    }
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = 'https://s3.example.com/result'
    with (
        patch.object(module, 'jobs_repo', mock_jobs_repo, create=True),
        patch.object(module, 'JobsRepository', return_value=mock_jobs_repo),
        patch.object(module, 's3', mock_s3),
    ):
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 409
    body = json.loads(response['body'])
    assert 'Cannot cancel terminal task' in body['error']
    mock_jobs_repo.update_job_status.assert_not_called()


def test_vpr_cancel_failed_returns_409_no_update() -> None:
    from careervp.handlers import vpr_status_handler as module

    event = _cancel_event('/vpr/task-1/cancel', {'vprId': 'task-1'})
    mock_jobs_repo = MagicMock()
    mock_jobs_repo.get_job.return_value = {
        'user_id': 'user-123',
        'status': 'FAILED',
        'error': 'Something went wrong',
    }
    with (
        patch.object(module, 'jobs_repo', mock_jobs_repo, create=True),
        patch.object(module, 'JobsRepository', return_value=mock_jobs_repo),
        patch.object(module, 's3'),
    ):
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 409
    mock_jobs_repo.update_job_status.assert_not_called()


def test_vpr_cancel_dynamodb_raises_returns_500() -> None:
    from careervp.handlers import vpr_status_handler as module

    event = _cancel_event('/vpr/task-1/cancel', {'vprId': 'task-1'})
    mock_jobs_repo = MagicMock()
    mock_jobs_repo.get_job.side_effect = Exception('DynamoDB connection error')
    with (
        patch.object(module, 'jobs_repo', mock_jobs_repo, create=True),
        patch.object(module, 'JobsRepository', return_value=mock_jobs_repo),
        patch.object(module, 's3'),
    ):
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 500
