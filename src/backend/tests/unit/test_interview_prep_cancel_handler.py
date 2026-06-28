"""Unit tests for Interview Prep cancel endpoint — RED phase (cancel not yet implemented)."""

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
        function_name='interview-prep-handler',
        memory_limit_in_mb=256,
        invoked_function_arn='arn:aws:lambda:us-east-1:123456789:function:interview-prep-handler',
    )


def _mock_table(status: str = 'PENDING', prep_id: str = 'ip-1', user_id: str = 'user-123') -> MagicMock:
    table = MagicMock()
    table.get_item.return_value = {
        'Item': {
            'applicationId': user_id,
            'artifactId': f'ARTIFACT#INTERVIEW_PREP#{prep_id}',
            'status': status,
        }
    }
    return table


def test_interview_prep_cancel_no_auth_returns_401() -> None:
    from careervp.handlers import interview_prep_handler as module

    event: dict[str, object] = {
        'httpMethod': 'POST',
        'path': '/interview-prep/ip-1/cancel',
        'pathParameters': {'interviewPrepId': 'ip-1'},
        'requestContext': {},
        'body': None,
    }
    mock_table = _mock_table()
    with patch('boto3.resource') as mock_resource:
        mock_resource.return_value.Table.return_value = mock_table
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 401


def test_interview_prep_cancel_task_not_found_returns_404() -> None:
    from careervp.handlers import interview_prep_handler as module

    event = _cancel_event('/interview-prep/missing-id/cancel', {'interviewPrepId': 'missing-id'})
    mock_table = MagicMock()
    mock_table.get_item.return_value = {'Item': None}
    mock_table.query.return_value = {'Items': []}
    with patch('boto3.resource') as mock_resource:
        mock_resource.return_value.Table.return_value = mock_table
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 404


def test_interview_prep_cancel_pending_returns_200_and_updates() -> None:
    from careervp.handlers import interview_prep_handler as module

    event = _cancel_event('/interview-prep/ip-1/cancel', {'interviewPrepId': 'ip-1'})
    mock_table = _mock_table(status='PENDING')
    with patch('boto3.resource') as mock_resource:
        mock_resource.return_value.Table.return_value = mock_table
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 200
    mock_table.update_item.assert_called_once_with(
        Key={'applicationId': 'user-123', 'artifactId': 'ARTIFACT#INTERVIEW_PREP#ip-1'},
        UpdateExpression='SET #s = :status',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':status': 'CANCELLED'},
    )


def test_interview_prep_cancel_processing_returns_200_and_updates() -> None:
    from careervp.handlers import interview_prep_handler as module

    event = _cancel_event('/interview-prep/ip-1/cancel', {'interviewPrepId': 'ip-1'})
    mock_table = _mock_table(status='PROCESSING')
    with patch('boto3.resource') as mock_resource:
        mock_resource.return_value.Table.return_value = mock_table
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 200
    mock_table.update_item.assert_called_once()


def test_interview_prep_cancel_completed_returns_409_no_update() -> None:
    from careervp.handlers import interview_prep_handler as module

    event = _cancel_event('/interview-prep/ip-1/cancel', {'interviewPrepId': 'ip-1'})
    mock_table = _mock_table(status='COMPLETED')
    with patch('boto3.resource') as mock_resource:
        mock_resource.return_value.Table.return_value = mock_table
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 409
    body = json.loads(response['body'])
    assert 'Cannot cancel terminal task' in body.get('error', '')
    mock_table.update_item.assert_not_called()


def test_interview_prep_cancel_failed_returns_409_no_update() -> None:
    from careervp.handlers import interview_prep_handler as module

    event = _cancel_event('/interview-prep/ip-1/cancel', {'interviewPrepId': 'ip-1'})
    mock_table = _mock_table(status='FAILED')
    with patch('boto3.resource') as mock_resource:
        mock_resource.return_value.Table.return_value = mock_table
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 409
    mock_table.update_item.assert_not_called()


def test_interview_prep_cancel_dynamodb_raises_returns_500() -> None:
    from careervp.handlers import interview_prep_handler as module

    event = _cancel_event('/interview-prep/ip-1/cancel', {'interviewPrepId': 'ip-1'})
    mock_table = MagicMock()
    mock_table.get_item.side_effect = Exception('DynamoDB error')
    with patch('boto3.resource') as mock_resource:
        mock_resource.return_value.Table.return_value = mock_table
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 500
