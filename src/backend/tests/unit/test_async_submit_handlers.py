"""Unit tests for async submit handlers (cover letter + interview prep)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-artifacts-table')
    monkeypatch.setenv('SQS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue')


def _event(path: str, body: dict[str, object], user_id: str = 'user-123') -> dict[str, object]:
    return {
        'path': path,
        'httpMethod': 'POST',
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': user_id,
                }
            }
        },
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body),
    }


def _lambda_context(function_name: str) -> SimpleNamespace:
    return SimpleNamespace(
        function_name=function_name,
        function_version='$LATEST',
        invoked_function_arn=f'arn:aws:lambda:us-east-1:123456789012:function:{function_name}',
        memory_limit_in_mb='256',
        aws_request_id='req-123',
        log_group_name=f'/aws/lambda/{function_name}',
        log_stream_name='2026/03/02/[$LATEST]test',
    )


def test_cover_letter_submit_handler_validates_and_queues_with_sqs_queue_url() -> None:
    from careervp.handlers import cover_letter_submit_handler as module

    event = _event(
        '/cover-letter/generate',
        {
            'cv_id': 'cv-1',
            'job_id': 'job-1',
            'vpr_id': 'vpr-1',
            'gap_response_ids': ['gap-1'],
            'company_research_id': 'company-1',
        },
    )
    context = _lambda_context('cover-letter-submit')

    mock_table = MagicMock()
    with (
        patch.object(module, 'sqs') as mock_sqs,
        patch.object(module, 'dynamodb_resource') as mock_dynamo,
        patch.object(module, 'resolve_handler_dependencies', return_value=MagicMock(status='ready', resolved_upstream={})),
    ):
        mock_dynamo.Table.return_value = mock_table
        response = module.lambda_handler(event, context)

    assert response['statusCode'] == 202
    body = json.loads(str(response['body']))
    assert body['status'] == 'processing'
    mock_sqs.send_message.assert_called_once()
    mock_sqs.get_queue_url.assert_not_called()
    mock_table.put_item.assert_called_once()


def test_interview_prep_submit_handler_validates_and_queues_with_sqs_queue_url() -> None:
    from careervp.handlers import interview_prep_submit_handler as module

    event = _event(
        '/interview-prep/generate',
        {
            'vpr_id': 'vpr-1',
            'gap_response_ids': ['gap-1'],
            'focus_areas': ['system design'],
            'question_count': 5,
        },
    )
    context = _lambda_context('interview-prep-submit')

    mock_table = MagicMock()
    with (
        patch.object(module, 'sqs') as mock_sqs,
        patch.object(module, 'dynamodb_resource') as mock_dynamo,
        patch.object(module, 'resolve_handler_dependencies', return_value=MagicMock(status='ready', resolved_upstream={})),
    ):
        mock_dynamo.Table.return_value = mock_table
        response = module.lambda_handler(event, context)

    assert response['statusCode'] == 202
    body = json.loads(str(response['body']))
    assert body['status'] == 'processing'
    assert body['request_id'] == body['artifact_id']
    mock_sqs.send_message.assert_called_once()
    mock_sqs.get_queue_url.assert_not_called()
    mock_table.put_item.assert_called_once()
    item = mock_table.put_item.call_args.kwargs['Item']
    assert item['artifactId'] == f'ARTIFACT#INTERVIEW_PREP#{body["request_id"]}'
    assert item['applicationId'] == 'user-123'


def test_cover_letter_submit_handler_returns_structured_validation_errors() -> None:
    from careervp.handlers import cover_letter_submit_handler as module

    event = _event('/cover-letter/generate', {'cv_id': 'cv-1'})
    event['requestContext']['requestId'] = 'api-req-1'
    context = _lambda_context('cover-letter-submit')

    with (
        patch.object(module, 'sqs') as mock_sqs,
        patch.object(module, 'dynamodb_resource') as mock_dynamo,
    ):
        response = module.lambda_handler(event, context)

    assert response['statusCode'] == 400
    body = json.loads(str(response['body']))
    assert body['error'] == 'Invalid request body'
    assert body['code'] == 'VALIDATION_ERROR'
    assert body['request_id'] == 'api-req-1'
    assert isinstance(body['validation_errors'], list)
    assert body['validation_errors']
    assert body['validation_errors'][0]['code'] == 'VALIDATION_ERROR'
    assert 'field' in body['validation_errors'][0]
    assert 'message' in body['validation_errors'][0]
    mock_sqs.send_message.assert_not_called()
    mock_dynamo.Table.assert_not_called()


def test_interview_prep_submit_handler_returns_structured_validation_errors() -> None:
    from careervp.handlers import interview_prep_submit_handler as module

    event = _event('/interview-prep/generate', {'vpr_id': 'vpr-1'})
    event['requestContext']['requestId'] = 'api-req-2'
    context = _lambda_context('interview-prep-submit')

    with (
        patch.object(module, 'sqs') as mock_sqs,
        patch.object(module, 'dynamodb_resource') as mock_dynamo,
    ):
        response = module.lambda_handler(event, context)

    assert response['statusCode'] == 400
    body = json.loads(str(response['body']))
    assert body['error'] == 'Invalid request body'
    assert body['code'] == 'VALIDATION_ERROR'
    assert body['request_id'] == 'api-req-2'
    assert isinstance(body['validation_errors'], list)
    assert body['validation_errors']
    assert body['validation_errors'][0]['code'] == 'VALIDATION_ERROR'
    mock_sqs.send_message.assert_not_called()
    mock_dynamo.Table.assert_not_called()


def test_interview_prep_submit_handler_marks_failed_with_artifacts_keys_on_sqs_error() -> None:
    from careervp.handlers import interview_prep_submit_handler as module

    event = _event(
        '/interview-prep/generate',
        {
            'vpr_id': 'vpr-1',
            'gap_response_ids': ['gap-1'],
            'focus_areas': ['system design'],
            'question_count': 5,
        },
    )
    context = _lambda_context('interview-prep-submit')

    sqs_error = module.BotoClientError(
        {'Error': {'Code': 'ServiceError', 'Message': 'queue unavailable'}},
        'SendMessage',
    )
    mock_table = MagicMock()

    with (
        patch.object(module, 'sqs') as mock_sqs,
        patch.object(module, 'dynamodb_resource') as mock_dynamo,
        patch.object(module, 'resolve_handler_dependencies', return_value=MagicMock(status='ready', resolved_upstream={})),
    ):
        mock_sqs.send_message.side_effect = sqs_error
        mock_dynamo.Table.return_value = mock_table
        response = module.lambda_handler(event, context)

    assert response['statusCode'] == 500
    put_item = mock_table.put_item.call_args.kwargs['Item']
    expected_artifact_id = put_item['artifactId']
    mock_table.update_item.assert_called_once_with(
        Key={'applicationId': 'user-123', 'artifactId': expected_artifact_id},
        UpdateExpression='SET #s = :status, updated_at = :now',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':status': 'FAILED', ':now': put_item['created_at']},
    )
