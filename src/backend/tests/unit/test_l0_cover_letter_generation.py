"""
L0.1 — Cover Letter Generator Unit Tests

Validates: cover_letter.py calls Claude API (not template stub)
Spec: docs/best_practices/yaml/lambda_handler_spec.yaml
      docs/refactor/specs/cover_letter_spec.yaml
Payload: docs/refactor/payloads/beta_l0_generators_test.json#L0_1_cover_letter
Invariant: I1 (partial)
Results: docs/beta/execution_results/L0_1_results.md
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.cover_letter import generate_cover_letter
from careervp.models.cover_letter import CoverLetterRequest
from careervp.models.cv import UserCV
from careervp.models.result import Result, ResultCode

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-key')

USER_ID = 'user-test-123'
OTHER_USER_ID = 'user-other-999'

TEMPLATE_PATTERNS = [
    'Generated cover letter for request',
    '{id}',
    '[YOUR_NAME]',
    '[COMPANY_NAME]',
    '{job_title}',
    '{company}',
]


def _logic_request() -> CoverLetterRequest:
    return CoverLetterRequest(
        user_id=USER_ID,
        cv_id='cv-abc456',
        job_id='job-xyz789',
        vpr_id='vpr-001',
        company_name='Innovate Labs',
        job_title='Principal Software Engineer',
        job_description='Lead backend architecture and mentor engineering teams.',
        gap_response_ids=['gap-001'],
    )


def _api_event(
    user_id: str = USER_ID,
    cv_id: str = 'cv-abc456',
    job_id: str = 'job-xyz789',
) -> dict[str, object]:
    body = {
        'cv_id': cv_id,
        'job_id': job_id,
        'vpr_id': 'vpr-001',
        'gap_response_ids': ['gap-001'],
        'company_research_id': 'company-r-001',
        'options': {'tone': 'professional', 'length': 'standard', 'include_portfolio_link': False},
    }
    return {
        'httpMethod': 'POST',
        'path': '/cover-letter/generate',
        'requestContext': {'authorizer': {'jwt': {'claims': {'sub': user_id}}}},
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body),
    }


def _user_cv(user_id: str = USER_ID) -> UserCV:
    return UserCV(
        user_id=user_id,
        cv_id='cv-abc456',
        full_name='Jane Engineer',
        email='jane@example.com',
        professional_summary='Backend engineer with distributed systems experience.',
    )


def _mock_vpr_response() -> MagicMock:
    vpr = MagicMock()
    vpr.model_dump.return_value = {
        'summary': 'Strong distributed systems experience with measurable impact.',
    }
    return vpr


def _resolved_context() -> dict[str, object]:
    return {
        'company_name': 'Innovate Labs',
        'job_title': 'Principal Software Engineer',
        'job_description': 'Lead backend architecture and mentor engineering teams.',
        'gap_responses': [{'question_id': 'gap-001', 'answer': 'I reduced incident volume by 40%.'}],
        'vpr': _mock_vpr_response(),
    }


@pytest.fixture(autouse=True)
def _bypass_artifact_dependencies(
    mock_artifact_dependency_resolver: object,
    mock_company_research_load: object,
) -> None:
    """Opt into the dependency-bypass fixtures retired from global autouse (T-02).

    This module exercises LLM cover-letter generation, not resolver/routing
    behavior, so it declares the upstream bypass explicitly.
    """


@pytest.mark.unit
class TestCoverLetterCallsLLM:
    """Validates L0.1: cover_letter.py calls LLMClient, not a stub."""

    def test_cover_letter_calls_llm_client_generate(self) -> None:
        request = _logic_request()
        with patch('careervp.logic.cover_letter.LLMClient') as mock_cls:
            mock_llm = MagicMock()
            mock_llm.generate.return_value = {
                'text': (
                    'Dear Hiring Manager,\n\nI led backend platform modernization initiatives '
                    'that reduced deployment time by 45% while improving reliability.\n\n'
                    'I would welcome the opportunity to contribute this experience to Innovate Labs.'
                )
            }
            mock_cls.return_value = mock_llm

            result = asyncio.run(
                generate_cover_letter(
                    request=request,
                    user_cv=_user_cv(),
                    vpr=_mock_vpr_response(),
                )
            )

            assert result.success
            mock_llm.generate.assert_called_once()
            call_prompt = mock_llm.generate.call_args.kwargs['prompt']
            assert 'Jane Engineer' in call_prompt
            assert 'Lead backend architecture' in call_prompt


@pytest.mark.unit
class TestCoverLetterNoTemplate:
    """Validates I1: output contains no known template strings."""

    @pytest.mark.parametrize('pattern', TEMPLATE_PATTERNS)
    def test_output_does_not_match_template_pattern(self, pattern: str) -> None:
        request = _logic_request()
        with patch('careervp.logic.cover_letter.LLMClient') as mock_cls:
            mock_llm = MagicMock()
            mock_llm.generate.return_value = {
                'text': (
                    'Dear Hiring Manager,\n\nI am excited to apply for the Principal Software '
                    'Engineer role and bring proven impact in reliability and throughput.\n\n'
                    'Thank you for your consideration.'
                )
            }
            mock_cls.return_value = mock_llm

            result = asyncio.run(
                generate_cover_letter(
                    request=request,
                    user_cv=_user_cv(),
                    vpr=_mock_vpr_response(),
                )
            )

            assert result.success
            assert result.data is not None
            assert pattern not in result.data.cover_letter.full_text


@pytest.mark.unit
class TestCoverLetterHandlerFlow:
    """Validates handler behavior required by L0.1."""

    def test_returns_artifact_id(self) -> None:
        from careervp.handlers.cover_letter_handler import lambda_handler

        with patch('careervp.handlers.cover_letter_handler._get_dal') as mock_get_dal:
            mock_dal = MagicMock()
            mock_dal.get_cv.return_value = _user_cv()
            mock_get_dal.return_value = mock_dal

            with patch('careervp.handlers.cover_letter_handler.generate_cover_letter') as mock_generate:
                cover_letter_payload = {
                    'cover_letter_id': 'cl-001',
                    'full_text': 'Real generated cover letter text.',
                    'word_count': 120,
                    'paragraphs': [],
                }
                mock_generate.return_value = Result(
                    success=True,
                    data=MagicMock(cover_letter=MagicMock(model_dump=MagicMock(return_value=cover_letter_payload))),
                    code=ResultCode.COVER_LETTER_GENERATED,
                )
                with patch('careervp.handlers.cover_letter_handler._resolve_cover_letter_context', return_value=_resolved_context()):
                    response = lambda_handler(_api_event(), MagicMock())

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['artifact_id'] == 'cl-001'
        assert body['status'] == 'completed'

    def test_llm_error_returns_503(self) -> None:
        from careervp.handlers.cover_letter_handler import lambda_handler

        with patch('careervp.handlers.cover_letter_handler._get_dal') as mock_get_dal:
            mock_dal = MagicMock()
            mock_dal.get_cv.return_value = _user_cv()
            mock_get_dal.return_value = mock_dal

            with patch('careervp.handlers.cover_letter_handler.generate_cover_letter') as mock_generate:
                mock_generate.return_value = Result(
                    success=False,
                    error='LLM timed out',
                    code=ResultCode.LLM_TIMEOUT,
                )
                with patch('careervp.handlers.cover_letter_handler._resolve_cover_letter_context', return_value=_resolved_context()):
                    response = lambda_handler(_api_event(), MagicMock())

        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['code'] == ResultCode.LLM_TIMEOUT

    def test_wrong_user_cv_returns_403(self) -> None:
        from careervp.handlers.cover_letter_handler import lambda_handler

        with patch('careervp.handlers.cover_letter_handler._get_dal') as mock_get_dal:
            mock_dal = MagicMock()
            mock_dal.get_cv.return_value = _user_cv(user_id=OTHER_USER_ID)
            mock_get_dal.return_value = mock_dal

            response = lambda_handler(_api_event(), MagicMock())

        # Returns 404 for security (doesn't reveal whether resource exists)
        assert response['statusCode'] == 404

    def test_cover_letter_generated_metric_emitted(self) -> None:
        from careervp.handlers.cover_letter_handler import lambda_handler

        with patch('careervp.handlers.cover_letter_handler._get_dal') as mock_get_dal:
            mock_dal = MagicMock()
            mock_dal.get_cv.return_value = _user_cv()
            mock_get_dal.return_value = mock_dal

            with patch('careervp.handlers.cover_letter_handler.generate_cover_letter') as mock_generate:
                cover_letter_payload = {
                    'cover_letter_id': 'cl-001',
                    'full_text': 'Generated text',
                    'word_count': 100,
                    'paragraphs': [],
                    'created_at': datetime.now(timezone.utc).isoformat(),
                }
                mock_generate.return_value = Result(
                    success=True,
                    data=MagicMock(cover_letter=MagicMock(model_dump=MagicMock(return_value=cover_letter_payload))),
                    code=ResultCode.COVER_LETTER_GENERATED,
                )

                with patch('careervp.handlers.cover_letter_handler.metrics.add_metric') as mock_metric:
                    with patch(
                        'careervp.handlers.cover_letter_handler._resolve_cover_letter_context',
                        return_value=_resolved_context(),
                    ):
                        response = lambda_handler(_api_event(), MagicMock())

        assert response['statusCode'] == 200
        metric_names = [call.kwargs.get('name') for call in mock_metric.call_args_list]
        assert 'CoverLetterGenerated' in metric_names
