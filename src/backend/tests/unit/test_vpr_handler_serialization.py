"""Unit tests for VPR handler camelCase serialization and version plumbing (spec 06)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from careervp.handlers.vpr_handler import lambda_handler


def _make_event(body: dict[str, Any]) -> dict[str, Any]:
    return {
        'body': json.dumps(body),
        'headers': {'Authorization': 'Bearer test-token'},
        'requestContext': {'authorizer': {'claims': {'sub': 'user-123'}}},
    }


def _make_lambda_context() -> MagicMock:
    ctx = MagicMock()
    ctx.function_name = 'vpr-handler-test'
    ctx.aws_request_id = 'test-request-id'
    return ctx


def _sample_request_body() -> dict[str, Any]:
    """Create a sample VPRRequest body in snake_case (as Pydantic expects)."""
    return {
        'application_id': 'app-001',
        'user_id': 'user-123',
        'job_posting': {
            'title': 'Staff Engineer',
            'company': 'SysAid',
            'description': 'Lead platform engineering.',
            'requirements': ['Python', 'AWS'],
            'language': 'en',
        },
        'gap_responses': [
            {
                'question_id': 'q1',
                'question': 'Describe your leadership experience.',
                'answer': 'Led 8 engineers at Acme Corp for 3 years.',
                'destination': 'CV_IMPACT',
            }
        ],
    }


@pytest.fixture(autouse=True)
def env_setup(monkeypatch: Any) -> None:
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'vpr-test')
    monkeypatch.setenv('LOG_LEVEL', 'WARNING')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-dynamodb-table')


@pytest.mark.unit
class TestCamelCaseResponseSerialization:
    def test_response_body_uses_camel_case_keys(self, minimal_vpr: Any, minimal_user_cv: Any) -> None:
        """API response must have camelCase keys (executiveSummary, not executive_summary)."""
        event = _make_event(_sample_request_body())
        ctx = _make_lambda_context()

        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls, patch('careervp.handlers.vpr_handler.generate_vpr') as mock_gen:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = minimal_user_cv
            mock_dal.get_next_vpr_version.return_value = 1

            from careervp.models.result import Result
            from careervp.models.vpr import VPRResponse

            # generate_vpr returns Result[VPRResponse]
            mock_gen.return_value = Result(
                success=True,
                data=VPRResponse(success=True, vpr=minimal_vpr),
                code='VPR_GENERATED',
            )

            response = lambda_handler(event, ctx)

        body = json.loads(response['body'])
        # Response must have success and vpr fields
        assert 'success' in body
        assert 'vpr' in body
        # VPR should have camelCase keys from alias_generator
        vpr_body = body.get('vpr', {})
        # Check that the VPR uses camelCase aliases (not snake_case)
        # The VPR has executiveSummary (camelCase) not executive_summary (snake_case)
        if isinstance(vpr_body, dict) and vpr_body:
            # At least one of these camelCase keys should be present
            has_camel_case = any(
                k in vpr_body for k in ['executiveSummary', 'roleAlignment', 'experienceMapping', 'skillsAnalysis', 'evidenceGaps', 'differentiators']
            )
            assert has_camel_case, f'VPR should have camelCase keys, got: {list(vpr_body.keys())}'

    def test_response_body_is_valid_json(self, minimal_vpr: Any, minimal_user_cv: Any) -> None:
        event = _make_event(_sample_request_body())
        ctx = _make_lambda_context()

        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls, patch('careervp.handlers.vpr_handler.generate_vpr') as mock_gen:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = minimal_user_cv
            mock_dal.get_next_vpr_version.return_value = 1

            from careervp.models.result import Result
            from careervp.models.vpr import VPRResponse

            # generate_vpr returns Result[VPRResponse]
            mock_gen.return_value = Result(
                success=True,
                data=VPRResponse(success=True, vpr=minimal_vpr),
                code='VPR_GENERATED',
            )

            response = lambda_handler(event, ctx)

        # Must not raise
        parsed = json.loads(response['body'])
        assert parsed is not None


@pytest.mark.unit
class TestVersionPlumbing:
    def test_handler_passes_dal_to_generate_vpr(self, minimal_user_cv: Any, minimal_vpr: Any) -> None:
        """Handler must pass DAL instance to generate_vpr() for version management."""
        event = _make_event(_sample_request_body())
        ctx = _make_lambda_context()

        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls, patch('careervp.handlers.vpr_handler.generate_vpr') as mock_gen:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = minimal_user_cv

            from careervp.models.result import Result
            from careervp.models.vpr import VPRResponse

            # generate_vpr returns Result[VPRResponse]
            mock_gen.return_value = Result(
                success=True,
                data=VPRResponse(success=True, vpr=minimal_vpr),
                code='VPR_GENERATED',
            )

            lambda_handler(event, ctx)

        # Handler must call generate_vpr with request, user_cv, and DAL
        assert mock_gen.called
        call_args = mock_gen.call_args
        assert call_args is not None
        # Third argument should be the DAL instance
        assert len(call_args[0]) == 3 or 'dal' in call_args[1]


@pytest.mark.unit
class TestHTTPStatusCodes:
    def test_returns_200_on_success(self, minimal_user_cv: Any, minimal_vpr: Any) -> None:
        event = _make_event(_sample_request_body())
        ctx = _make_lambda_context()

        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls, patch('careervp.handlers.vpr_handler.generate_vpr') as mock_gen:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = minimal_user_cv
            mock_dal.get_next_vpr_version.return_value = 1

            from careervp.models.result import Result
            from careervp.models.vpr import VPRResponse

            # generate_vpr returns Result[VPRResponse]
            mock_gen.return_value = Result(
                success=True,
                data=VPRResponse(success=True, vpr=minimal_vpr),
                code='VPR_GENERATED',
            )

            response = lambda_handler(event, ctx)

        assert response['statusCode'] == 200

    def test_returns_404_when_cv_not_found(self) -> None:
        event = _make_event(_sample_request_body())
        ctx = _make_lambda_context()

        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = None  # CV not found
            mock_dal.get_next_vpr_version.return_value = 1

            response = lambda_handler(event, ctx)

        assert response['statusCode'] == 404

    def test_returns_422_on_fvs_validation_failed(self, minimal_user_cv: Any) -> None:
        event = _make_event(_sample_request_body())
        ctx = _make_lambda_context()

        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls, patch('careervp.handlers.vpr_handler.generate_vpr') as mock_gen:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = minimal_user_cv
            mock_dal.get_next_vpr_version.return_value = 1

            from careervp.models.result import Result, ResultCode

            mock_gen.return_value = Result(
                success=False,
                data=None,
                code=ResultCode.FVS_VALIDATION_FAILED,
                error='FVS validation failed: claims not traceable to CV',
            )

            response = lambda_handler(event, ctx)

        assert response['statusCode'] == 422

    def test_returns_502_on_llm_error(self, minimal_user_cv: Any) -> None:
        event = _make_event(_sample_request_body())
        ctx = _make_lambda_context()

        with patch('careervp.handlers.vpr_handler.DynamoDalHandler') as mock_dal_cls, patch('careervp.handlers.vpr_handler.generate_vpr') as mock_gen:
            mock_dal = mock_dal_cls.return_value
            mock_dal.get_cv.return_value = minimal_user_cv
            mock_dal.get_next_vpr_version.return_value = 1

            from careervp.models.result import Result, ResultCode

            mock_gen.return_value = Result(
                success=False,
                data=None,
                code=ResultCode.LLM_API_ERROR,
                error='LLM API error: rate limit exceeded',
            )

            response = lambda_handler(event, ctx)

        assert response['statusCode'] == 502

    def test_returns_400_on_invalid_request_body(self) -> None:
        event = _make_event({'invalid': 'body_missing_required_fields'})
        ctx = _make_lambda_context()

        with patch('careervp.handlers.vpr_handler.DynamoDalHandler'):
            response = lambda_handler(event, ctx)

        assert response['statusCode'] == 400
