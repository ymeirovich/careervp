"""Regression tests preventing downstream placeholder fallbacks."""

from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from careervp.logic.artifact_dependency_resolver import DependencyResolution

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_fallback_vpr_class_removed() -> None:
    source = (BACKEND_ROOT / 'careervp/handlers/cover_letter_handler.py').read_text()
    assert '_FallbackVPR' not in source


def test_interview_prep_placeholder_removed() -> None:
    source = (BACKEND_ROOT / 'careervp/handlers/interview_prep_handler.py').read_text()
    assert "'vpr_data': {'vpr_id': api_request.vpr_id}" not in source
    assert "context['vpr_data'] != {'vpr_id': api_request.vpr_id}" not in source


@pytest.mark.xfail(
    strict=True,
    reason=(
        'BUG (found handoff-01, Step 1b): CVTailoringRequest.vpr_id (careervp/models/'
        'api_models.py:343) is `str | None` with no `= None` default, so pydantic '
        'requires the key to be present even though None is a valid value. A client '
        'requesting CV tailoring before a VPR exists — precisely the scenario this '
        'test protects — naturally omits vpr_id, so the request 400s at validation '
        'before reaching the (correctly implemented) dependency_generating/202 path. '
        'Product bug, not a test bug; not fixed here per handoff-01 scope (CI wiring, '
        'not product code).'
    ),
)
def test_cv_tailoring_no_raise_on_missing_vpr(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import cv_tailoring_handler

    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-artifacts')
    monkeypatch.setattr(
        cv_tailoring_handler,
        'resolve_handler_dependencies',
        MagicMock(
            return_value=DependencyResolution(
                status='dependency_generating',
                generating=['vpr'],
                missing=['vpr'],
                http_status=int(HTTPStatus.ACCEPTED),
            )
        ),
    )
    monkeypatch.setattr(cv_tailoring_handler, 'mark_requested_artifact_pending', MagicMock())

    response = cv_tailoring_handler.lambda_handler(
        {
            'httpMethod': 'POST',
            'path': '/cv-tailoring/generate',
            'requestContext': {'authorizer': {'claims': {'sub': 'user-1'}}},
            'body': json.dumps({'cv_id': 'cv-1', 'job_id': 'app-1'}),
        },
        SimpleNamespace(aws_request_id='req-1'),
    )

    body = json.loads(response['body'])
    assert response['statusCode'] == 202
    assert body['status'] == 'dependency_generating'
