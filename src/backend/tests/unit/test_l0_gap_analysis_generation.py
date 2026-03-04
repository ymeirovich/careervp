"""
L0.3 — Gap Analysis Generator Unit Tests

Validates: gap_analysis.py calls Claude API, returns 10 AI questions (not templates)
Spec: docs/best_practices/yaml/lambda_handler_spec.yaml
      docs/refactor/specs/gap_analysis_spec.yaml
Payload: docs/refactor/payloads/beta_l0_generators_test.json#L0_3_gap_analysis
Invariant: I1 (partial)
Results: docs/beta/execution_results/L0_3_results.md
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.gap_analysis import generate_gap_questions
from careervp.models.result import Result, ResultCode

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-key')

USER_ID = 'user-test-123'
VALID_TAG_CATEGORIES = ['[CV IMPACT]', '[TECHNICAL]', '[BEHAVIORAL]', '[INTERVIEW/MVP ONLY]']

TEMPLATE_PATTERNS = [
    'What quantifiable examples show your impact in core competency',
    'core competency N',
    '{question_number}',
    'Situation for question',
    'describe a relevant STAR example',
]

GAP_HANDLER_PATH = Path(__file__).resolve().parents[2] / 'careervp' / 'handlers' / 'gap_handler.py'


def _cv_payload() -> dict[str, object]:
    return {
        'personal_info': {'full_name': 'Jane Engineer'},
        'skills': ['Python', 'AWS', 'Distributed Systems'],
        'work_experience': [{'company': 'TechCorp', 'role': 'Senior Engineer'}],
    }


def _job_payload() -> dict[str, object]:
    return {
        'company_name': 'Innovate Labs',
        'role_title': 'Principal Software Engineer',
        'requirements': ['Scale distributed systems', 'Lead backend teams'],
        'responsibilities': ['Architecture ownership', 'Mentorship'],
    }


def _gap_questions_json() -> str:
    questions = []
    for i in range(10):
        tag = VALID_TAG_CATEGORIES[i % 4]
        questions.append(
            {
                'question_id': f'q-{i + 1}',
                'question': f'Describe a real project outcome for requirement {i + 1} tied to distributed systems work.',
                'impact': 'HIGH' if i < 4 else 'MEDIUM',
                'probability': 'MEDIUM',
                'tags': [tag],
            }
        )
    return json.dumps({'questions': questions})


def _api_event() -> dict[str, object]:
    return {
        'httpMethod': 'POST',
        'path': '/gap-analysis/questions',
        'requestContext': {
            'authorizer': {'jwt': {'claims': {'sub': USER_ID}}},
        },
        'body': json.dumps(
            {
                'cv_id': 'cv-abc456',
                'job_id': 'job-xyz789',
                'max_questions': 10,
                'focus_areas': ['python', 'system design'],
            }
        ),
        'headers': {'Content-Type': 'application/json'},
    }


@pytest.mark.unit
class TestGapAnalysisCallsLLM:
    def test_gap_analysis_calls_llm_client(self) -> None:
        with patch('careervp.logic.gap_analysis.LLMClient') as mock_cls:
            llm = MagicMock()
            llm.generate.return_value = {'text': _gap_questions_json()}
            mock_cls.return_value = llm

            result = asyncio.run(
                generate_gap_questions(
                    user_cv=_cv_payload(),
                    job_posting=_job_payload(),
                    dal=None,
                )
            )

            assert result.success
            llm.generate.assert_called_once()
            prompt = llm.generate.call_args.kwargs['prompt']
            assert 'Jane Engineer' in prompt
            assert 'Principal Software Engineer' in prompt


@pytest.mark.unit
class TestGapAnalysisNoTemplate:
    @pytest.mark.parametrize('pattern', TEMPLATE_PATTERNS)
    def test_no_template_pattern_in_questions(self, pattern: str) -> None:
        with patch('careervp.logic.gap_analysis.LLMClient') as mock_cls:
            llm = MagicMock()
            llm.generate.return_value = {'text': _gap_questions_json()}
            mock_cls.return_value = llm

            result = asyncio.run(
                generate_gap_questions(
                    user_cv=_cv_payload(),
                    job_posting=_job_payload(),
                    dal=None,
                )
            )

            assert result.success
            assert result.data is not None
            serialized = json.dumps(result.data)
            assert pattern not in serialized


@pytest.mark.unit
class TestGapAnalysisOutputShape:
    def test_generates_10_questions_with_valid_tags(self) -> None:
        with patch('careervp.logic.gap_analysis.LLMClient') as mock_cls:
            llm = MagicMock()
            llm.generate.return_value = {'text': _gap_questions_json()}
            mock_cls.return_value = llm

            result = asyncio.run(
                generate_gap_questions(
                    user_cv=_cv_payload(),
                    job_posting=_job_payload(),
                    dal=None,
                )
            )

            assert result.success
            assert result.data is not None
            assert len(result.data) == 10
            assert all('question_id' in q and 'question' in q for q in result.data)

    def test_handler_returns_questions_from_llm_generation(self) -> None:
        from careervp.handlers.gap_handler import lambda_handler

        with patch('careervp.handlers.gap_handler.generate_gap_questions') as mock_generate:
            generated_questions = [
                {
                    'question_id': f'q-{i + 1}',
                    'question': 'Describe a measurable achievement.',
                    'impact': 'HIGH',
                    'probability': 'MEDIUM',
                    'tags': [VALID_TAG_CATEGORIES[i % 4]],
                }
                for i in range(10)
            ]
            mock_generate.return_value = Result(
                success=True,
                data=generated_questions,
                code=ResultCode.GAP_QUESTIONS_GENERATED,
            )

            with (
                patch('careervp.handlers.gap_handler._get_questions_dal') as mock_get_dal,
                patch('careervp.handlers.gap_handler._get_trial_service') as mock_trial_service,
                patch('careervp.handlers.gap_handler._get_application_repository') as mock_application_repository,
            ):
                dal = MagicMock()
                dal.save_gap_questions.return_value = Result(success=True, data=None, code=ResultCode.GAP_QUESTIONS_GENERATED)
                mock_get_dal.return_value = dal
                trial_service = MagicMock()
                trial_service.check_trial_status.return_value = {'is_active': True}
                trial_service.consume_credit.return_value = None
                mock_trial_service.return_value = trial_service
                mock_application_repository.return_value = MagicMock()
                response = lambda_handler(_api_event(), MagicMock())

        assert response['statusCode'] in (200, 201)
        body = json.loads(response['body'])
        assert len(body['questions']) == 10
        assert body['job_id'] == 'job-xyz789'

    def test_llm_error_maps_to_503(self) -> None:
        from careervp.handlers.gap_handler import lambda_handler

        with (
            patch('careervp.handlers.gap_handler.generate_gap_questions') as mock_generate,
            patch('careervp.handlers.gap_handler._get_trial_service') as mock_trial_service,
            patch('careervp.handlers.gap_handler._get_application_repository') as mock_application_repository,
        ):
            mock_generate.return_value = Result(
                success=False,
                error='LLM timeout',
                code=ResultCode.LLM_TIMEOUT,
            )
            trial_service = MagicMock()
            trial_service.check_trial_status.return_value = {'is_active': True}
            trial_service.consume_credit.return_value = None
            mock_trial_service.return_value = trial_service
            mock_application_repository.return_value = MagicMock()
            response = lambda_handler(_api_event(), MagicMock())

        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['code'] == ResultCode.LLM_TIMEOUT


@pytest.mark.unit
def test_gap_handler_has_no_template_fallback_markers() -> None:
    source = GAP_HANDLER_PATH.read_text(encoding='utf-8')
    forbidden_markers = (
        'What quantifiable examples show your impact in',
        'core competency',
    )
    for marker in forbidden_markers:
        assert marker not in source
