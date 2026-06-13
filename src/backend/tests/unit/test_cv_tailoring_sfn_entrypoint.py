from __future__ import annotations

import json
from http import HTTPStatus
from unittest.mock import MagicMock

import pytest

from careervp.handlers import cv_tailoring_handler


def test_sfn_invoke_shape_runs_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    mocked_generate = MagicMock(
        return_value={
            'statusCode': HTTPStatus.ACCEPTED,
            'body': json.dumps({'request_id': 'cv-tail-1', 'status': 'completed'}),
        }
    )
    monkeypatch.setattr(cv_tailoring_handler, '_handle_openapi_async_generate', mocked_generate)

    result = cv_tailoring_handler.handler(
        {
            'user_id': 'user-1',
            'cv_id': 'cv-1',
            'job_id': 'job-1',
            'vpr_id': 'vpr-1',
        },
        MagicMock(),
    )

    assert result == {'request_id': 'cv-tail-1', 'status': 'completed'}
    mocked_generate.assert_called_once()


def test_api_shape_still_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    mocked_generate = MagicMock()
    monkeypatch.setattr(cv_tailoring_handler, '_handle_openapi_async_generate', mocked_generate)

    result = cv_tailoring_handler.handler({'httpMethod': 'OPTIONS', 'path': '/cv-tailoring'}, MagicMock())

    assert result['statusCode'] == HTTPStatus.OK
    mocked_generate.assert_not_called()


def test_pipeline_exception_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    mocked_generate = MagicMock(
        return_value={
            'statusCode': HTTPStatus.INTERNAL_SERVER_ERROR,
            'body': json.dumps({'message': 'pipeline failed'}),
        }
    )
    monkeypatch.setattr(cv_tailoring_handler, '_handle_openapi_async_generate', mocked_generate)

    with pytest.raises(RuntimeError, match='pipeline failed'):
        cv_tailoring_handler.handler(
            {
                'user_id': 'user-1',
                'cv_id': 'cv-1',
                'job_id': 'job-1',
                'vpr_id': 'vpr-1',
            },
            MagicMock(),
        )
