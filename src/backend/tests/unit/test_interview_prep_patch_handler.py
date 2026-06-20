"""Unit tests for FE-UI-046 PATCH /interview-prep handler (AC-013, AC-014, AC-015)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from careervp.handlers import interview_prep_handler as module


@pytest.fixture(autouse=True)
def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-artifacts-table')


def _context() -> SimpleNamespace:
    return SimpleNamespace(
        aws_request_id='req-1',
        function_name='interview-prep-handler',
        memory_limit_in_mb=256,
        invoked_function_arn='arn:aws:lambda:us-east-1:1:function:interview-prep-handler',
    )


def _patch_event(body: dict[str, Any] | None, user_id: str | None = 'user-1', prep_id: str = 'ip-1') -> dict[str, Any]:
    request_context: dict[str, Any] = {}
    if user_id is not None:
        request_context = {'authorizer': {'claims': {'sub': user_id}}}
    return {
        'httpMethod': 'PATCH',
        'path': f'/interview-prep/{prep_id}',
        'pathParameters': {'interviewPrepId': prep_id},
        'requestContext': request_context,
        'body': None if body is None else json.dumps(body),
    }


def _item(answer_version: int | None = None, with_answer: bool = False) -> dict[str, Any]:
    question: dict[str, Any] = {
        'question_id': 'q1',
        'question': 'Tell me about a hard project.',
        'suggested_answer': {'situation': 'S', 'task': 'T', 'action': 'A', 'result': 'R'},
    }
    if with_answer:
        question['answer'] = 'previous'
    if answer_version is not None:
        question['answer_version'] = answer_version
    return {
        'applicationId': 'user-1',
        'artifactId': 'ARTIFACT#INTERVIEW_PREP#ip-1',
        'status': 'completed',
        'interview_prep': {'prep_id': 'ip-1', 'questions': [question]},
    }


def test_patch_no_auth_returns_401() -> None:
    event = _patch_event({'question_id': 'q1', 'answer': 'x'}, user_id=None)
    response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 401


def test_patch_missing_fields_returns_400() -> None:
    event = _patch_event({'question_id': 'q1'})
    with patch.object(module, '_get_interview_prep_item', return_value=_item()):
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 400


def test_patch_prep_not_found_returns_404() -> None:
    event = _patch_event({'question_id': 'q1', 'answer': 'x'})
    with patch.object(module, '_get_interview_prep_item', return_value=None):
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 404


def test_patch_question_not_found_returns_404() -> None:
    event = _patch_event({'question_id': 'missing', 'answer': 'x'})
    with patch.object(module, '_get_interview_prep_item', return_value=_item()):
        response = module.lambda_handler(event, _context())
    assert response['statusCode'] == 404


def test_patch_persists_answer_and_increments_version() -> None:
    # AC-013
    event = _patch_event({'question_id': 'q1', 'answer': '## My STAR answer', 'base_version': 0})
    mock_table = MagicMock()
    with (
        patch.object(module, '_get_interview_prep_item', return_value=_item()),
        patch('boto3.resource') as mock_resource,
    ):
        mock_resource.return_value.Table.return_value = mock_table
        response = module.lambda_handler(event, _context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['status'] == 'completed'
    assert body['question_id'] == 'q1'
    assert body['answer'] == '## My STAR answer'
    assert body['answer_version'] == 1

    # Inspect what was written
    _, kwargs = mock_table.update_item.call_args
    written_prep = kwargs['ExpressionAttributeValues'][':prep']
    written_question = written_prep['questions'][0]
    assert written_question['answer'] == '## My STAR answer'
    assert written_question['answer_version'] == 1
    assert written_question['answer_updated_at']
    # suggested_answer untouched
    assert written_question['suggested_answer'] == {'situation': 'S', 'task': 'T', 'action': 'A', 'result': 'R'}


def test_patch_stale_base_version_returns_409_no_write() -> None:
    # AC-014
    event = _patch_event({'question_id': 'q1', 'answer': 'new', 'base_version': 0})
    mock_table = MagicMock()
    with (
        patch.object(module, '_get_interview_prep_item', return_value=_item(answer_version=3)),
        patch('boto3.resource') as mock_resource,
    ):
        mock_resource.return_value.Table.return_value = mock_table
        response = module.lambda_handler(event, _context())

    assert response['statusCode'] == 409
    mock_table.update_item.assert_not_called()


def test_patch_backcompat_item_without_answer_initializes_version() -> None:
    # AC-015 — legacy item, no answer/answer_version field
    event = _patch_event({'question_id': 'q1', 'answer': 'first answer'})
    mock_table = MagicMock()
    with (
        patch.object(module, '_get_interview_prep_item', return_value=_item()),
        patch('boto3.resource') as mock_resource,
    ):
        mock_resource.return_value.Table.return_value = mock_table
        response = module.lambda_handler(event, _context())

    assert response['statusCode'] == 200
    assert json.loads(response['body'])['answer_version'] == 1
