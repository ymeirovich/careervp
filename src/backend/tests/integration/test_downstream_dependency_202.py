"""FE-UI-038 downstream handler dependency responses."""

from __future__ import annotations

import json
from http import HTTPStatus
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from careervp.logic.artifact_dependency_resolver import DependencyResolution
from careervp.models.result import Result, ResultCode


def _context() -> SimpleNamespace:
    return SimpleNamespace(
        aws_request_id='req-1',
        function_name='test-handler',
        memory_limit_in_mb='256',
        invoked_function_arn='arn:aws:lambda:us-east-1:123456789012:function:test-handler',
    )


def _event(path: str, body: dict[str, Any], user_id: str = 'user-1') -> dict[str, Any]:
    return {
        'httpMethod': 'POST',
        'path': path,
        'headers': {'Content-Type': 'application/json'},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
        'body': json.dumps(body),
    }


def _dependency_generating(*, generating: list[str] | None = None) -> DependencyResolution:
    return DependencyResolution(
        status='dependency_generating',
        generating=generating or ['vpr'],
        missing=generating or ['vpr'],
        chain_execution_arn='arn:aws:states:us-east-1:123456789012:execution:chain:test',
        http_status=int(HTTPStatus.ACCEPTED),
    )


def test_cover_letter_no_vpr_returns_202_dependency_generating(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import cover_letter_handler

    mark_pending = MagicMock()
    monkeypatch.setattr(cover_letter_handler, '_get_dal', MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(cover_letter_handler, 'resolve_handler_dependencies', MagicMock(return_value=_dependency_generating()))
    monkeypatch.setattr(cover_letter_handler, 'mark_requested_artifact_pending', mark_pending)

    response = cover_letter_handler.lambda_handler(
        _event(
            '/cover-letter/generate',
            {
                'cv_id': 'cv-1',
                'job_id': 'app-1',
                'application_id': 'app-1',
                'vpr_id': 'vpr-1',
                'gap_response_ids': ['gap-1'],
            },
        ),
        _context(),
    )

    body = json.loads(response['body'])
    assert response['statusCode'] == 202
    assert body['status'] == 'dependency_generating'
    assert 'vpr' in body['generating']
    assert body['requested_artifact'] == 'cover_letter'
    mark_pending.assert_called_once_with(application_id='app-1', user_id='user-1', artifact_type='cover_letter')


def test_interview_prep_no_vpr_returns_202(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import interview_prep_submit_handler

    mark_pending = MagicMock()
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-artifacts')
    monkeypatch.setattr(interview_prep_submit_handler, 'resolve_handler_dependencies', MagicMock(return_value=_dependency_generating()))
    monkeypatch.setattr(interview_prep_submit_handler, 'mark_requested_artifact_pending', mark_pending)

    response = interview_prep_submit_handler.lambda_handler(
        _event(
            '/interview-prep/generate',
            {
                'application_id': 'app-1',
                'job_id': 'app-1',
                'vpr_id': 'vpr-1',
                'gap_response_ids': ['gap-1'],
            },
        ),
        _context(),
    )

    body = json.loads(response['body'])
    assert response['statusCode'] == 202
    assert body['status'] == 'dependency_generating'
    assert body['requested_artifact'] == 'interview_prep'
    assert body != {'vpr_id': 'vpr-1'}
    mark_pending.assert_called_once_with(application_id='app-1', user_id='user-1', artifact_type='interview_prep')


def test_cv_tailoring_no_vpr_returns_202_not_500(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import cv_tailoring_handler

    mark_pending = MagicMock()
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-artifacts')
    monkeypatch.setattr(cv_tailoring_handler, 'resolve_handler_dependencies', MagicMock(return_value=_dependency_generating()))
    monkeypatch.setattr(cv_tailoring_handler, 'mark_requested_artifact_pending', mark_pending)

    response = cv_tailoring_handler.lambda_handler(
        # scope-lock §3 item 3: CV-tailoring sends `vpr_id: null`, never omitted.
        _event('/cv-tailoring/generate', {'cv_id': 'cv-1', 'job_id': 'app-1', 'vpr_id': None}),
        _context(),
    )

    body = json.loads(response['body'])
    assert response['statusCode'] == 202
    assert body['status'] == 'dependency_generating'
    assert body['requested_artifact'] == 'cv_tailored'
    mark_pending.assert_called_once_with(application_id='app-1', user_id='user-1', artifact_type='cv_tailored')


def test_cover_letter_with_vpr_and_cr_generates_normally(monkeypatch: pytest.MonkeyPatch, minimal_user_cv: Any) -> None:
    from careervp.handlers import cover_letter_handler

    cover_letter_model = MagicMock()
    cover_letter_model.model_dump.return_value = {'cover_letter_id': 'cover-letter-1', 'full_text': 'real cover letter'}
    generation_data = MagicMock(cover_letter=cover_letter_model)
    dal = MagicMock()
    dal.save_cover_letter.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)

    monkeypatch.setattr(cover_letter_handler, '_get_dal', MagicMock(return_value=dal))
    monkeypatch.setattr(
        cover_letter_handler,
        'resolve_handler_dependencies',
        MagicMock(return_value=DependencyResolution(status='ready')),
    )
    monkeypatch.setattr(cover_letter_handler, '_load_user_cv', MagicMock(return_value=minimal_user_cv))
    monkeypatch.setattr(
        cover_letter_handler,
        '_generate_cover_letter_result',
        MagicMock(return_value=Result(success=True, data=generation_data, code=ResultCode.SUCCESS)),
    )
    monkeypatch.setattr(cover_letter_handler, '_update_application_artifact', MagicMock())

    response = cover_letter_handler.lambda_handler(
        _event(
            '/cover-letter/generate',
            {
                'cv_id': 'cv-1',
                'job_id': 'app-1',
                'application_id': 'app-1',
                'vpr_id': 'vpr-1',
                'gap_response_ids': ['gap-1'],
                'company_research_id': 'cr-1',
            },
            user_id='user-123',
        ),
        _context(),
    )

    body = json.loads(response['body'])
    assert response['statusCode'] == 200
    assert body == {'artifact_id': 'cover-letter-1', 'status': 'completed'}
    dal.save_cover_letter.assert_called_once()
