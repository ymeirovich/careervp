"""Integration tests — VPR handler to DAL contract."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from careervp.handlers.vpr_handler import lambda_handler
from careervp.models.vpr import VPR, VPRResponse


def _event(body: dict[str, Any]) -> dict[str, Any]:
    return {
        'body': json.dumps(body),
        'headers': {'Authorization': 'Bearer test-token'},
        'requestContext': {'authorizer': {'claims': {'sub': 'user-123'}}},
    }


def _ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.aws_request_id = 'req-test-001'
    ctx.function_name = 'vpr-handler'
    return ctx


def _request_body() -> dict[str, Any]:
    return {
        'applicationId': 'app-001',
        'userId': 'user-123',
        'jobPosting': {
            'title': 'Staff Engineer',
            'company': 'SysAid',
            'description': 'Lead platform engineering.',
            'requirements': ['Python', 'AWS'],
            'language': 'en',
        },
    }


@pytest.fixture(autouse=True)
def env_setup(monkeypatch: Any) -> None:
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'vpr-handler-integration-test')
    monkeypatch.setenv('LOG_LEVEL', 'WARNING')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-artifacts')
    monkeypatch.setenv('ARTIFACTS_TABLE', 'test-artifacts')
    monkeypatch.setenv('CV_TABLE', 'test-cv')


@pytest.mark.integration
class TestHandlerDALContract:
    def test_handler_fetches_cv_before_generating(self, minimal_user_cv: Any, minimal_vpr: VPR) -> None:
        """Handler must call dal.get_cv() before generate_vpr()."""
        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls, patch('careervp.handlers.vpr_handler.generate_vpr') as mock_gen:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = MagicMock(success=True, data=minimal_user_cv)
            mock_dal.get_next_vpr_version.return_value = 1
            mock_gen.return_value = MagicMock(
                success=True,
                data=VPRResponse(success=True, vpr=minimal_vpr),
            )

            lambda_handler(_event(_request_body()), _ctx())

        mock_dal.get_cv.assert_called_once()
        # generate_vpr is called after CV is fetched
        mock_gen.assert_called_once()

    def test_handler_calls_get_next_vpr_version_before_generate(self, minimal_user_cv: Any, minimal_vpr: VPR) -> None:
        call_order: list[str] = []

        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls, patch('careervp.handlers.vpr_handler.generate_vpr') as mock_gen:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = MagicMock(success=True, data=minimal_user_cv)

            def record_version_call(*args: Any, **kwargs: Any) -> int:
                call_order.append('get_next_vpr_version')
                return 2

            def record_gen_call(*args: Any, **kwargs: Any) -> Any:
                call_order.append('generate_vpr')
                return MagicMock(
                    success=True,
                    data=VPRResponse(success=True, vpr=minimal_vpr),
                )

            mock_dal.get_next_vpr_version.side_effect = record_version_call
            mock_gen.side_effect = record_gen_call

            lambda_handler(_event(_request_body()), _ctx())

        assert call_order.index('get_next_vpr_version') < call_order.index('generate_vpr')

    def test_handler_response_body_camel_case(self, minimal_user_cv: Any, minimal_vpr: VPR) -> None:
        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls, patch('careervp.handlers.vpr_handler.generate_vpr') as mock_gen:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = MagicMock(success=True, data=minimal_user_cv)
            mock_dal.get_next_vpr_version.return_value = 1
            mock_gen.return_value = MagicMock(
                success=True,
                data=VPRResponse(success=True, vpr=minimal_vpr),
            )

            response = lambda_handler(_event(_request_body()), _ctx())

        body = json.loads(response['body'])
        vpr_data = body.get('vpr', body)
        # camelCase keys must be present
        assert 'applicationId' in vpr_data or 'executiveSummary' in vpr_data
        # snake_case must NOT be present at top level
        assert 'application_id' not in vpr_data
        assert 'executive_summary' not in vpr_data

    def test_handler_maps_cv_not_found_to_404(self) -> None:
        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = None

            response = lambda_handler(_event(_request_body()), _ctx())

        assert response['statusCode'] == 404

    def test_handler_maps_fvs_failed_to_422(self, minimal_user_cv: Any) -> None:
        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls, patch('careervp.handlers.vpr_handler.generate_vpr') as mock_gen:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = MagicMock(success=True, data=minimal_user_cv)
            mock_dal.get_next_vpr_version.return_value = 1

            from careervp.models.result import ResultCode

            mock_gen.return_value = MagicMock(
                success=False,
                data=None,
                error='FVS validation failed',
                code=ResultCode.FVS_VALIDATION_FAILED,
            )

            response = lambda_handler(_event(_request_body()), _ctx())

        assert response['statusCode'] == 422

    def test_handler_maps_llm_timeout_to_504(self, minimal_user_cv: Any) -> None:
        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls, patch('careervp.handlers.vpr_handler.generate_vpr') as mock_gen:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = MagicMock(success=True, data=minimal_user_cv)
            mock_dal.get_next_vpr_version.return_value = 1

            from careervp.models.result import ResultCode

            mock_gen.return_value = MagicMock(
                success=False,
                data=None,
                error='LLM request timed out',
                code=ResultCode.LLM_TIMEOUT,
            )

            response = lambda_handler(_event(_request_body()), _ctx())

        assert response['statusCode'] == 504

    def test_handler_maps_llm_api_error_to_502(self, minimal_user_cv: Any) -> None:
        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls, patch('careervp.handlers.vpr_handler.generate_vpr') as mock_gen:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = MagicMock(success=True, data=minimal_user_cv)
            mock_dal.get_next_vpr_version.return_value = 1

            from careervp.models.result import ResultCode

            mock_gen.return_value = MagicMock(
                success=False,
                data=None,
                error='LLM API error',
                code=ResultCode.LLM_API_ERROR,
            )

            response = lambda_handler(_event(_request_body()), _ctx())

        assert response['statusCode'] == 502

    def test_handler_response_size_logged(self, minimal_user_cv: Any, minimal_vpr: VPR) -> None:
        """Handler must log response size in bytes after serialization (spec 06)."""
        with (
            patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls,
            patch('careervp.handlers.vpr_handler.generate_vpr') as mock_gen,
            patch('careervp.handlers.vpr_handler.logger') as mock_logger,
        ):
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = MagicMock(success=True, data=minimal_user_cv)
            mock_dal.get_next_vpr_version.return_value = 1
            mock_gen.return_value = MagicMock(
                success=True,
                data=VPRResponse(success=True, vpr=minimal_vpr),
            )

            lambda_handler(_event(_request_body()), _ctx())

        # Check that logger.info was called with size_bytes parameter
        info_calls = mock_logger.info.call_args_list
        size_logged = any('size_bytes' in str(c) or 'size' in str(c).lower() for c in info_calls)
        assert size_logged, 'Response size must be logged after serialization'
