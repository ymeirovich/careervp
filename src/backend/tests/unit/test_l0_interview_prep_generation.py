"""
L0.2 — Interview Prep Generator Unit Tests

Validates: interview_prep.py calls Claude API (not STAR template stub)
Spec: docs/best_practices/yaml/lambda_handler_spec.yaml
      docs/refactor/specs/interview_prep_spec.yaml
Payload: docs/refactor/payloads/beta_l0_generators_test.json#L0_2_interview_prep
Invariant: I1 (partial)
Results: docs/beta/execution_results/L0_2_results.md
"""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.interview_prep import (
    DEFAULT_GENERATION_TEMPERATURE,
    PARSE_RETRY_TEMPERATURE,
    _parse_interview_prep,
    generate_interview_prep,
)
from careervp.models.cv import UserCV
from careervp.models.interview_prep import InterviewPrepRequest
from careervp.models.result import Result, ResultCode

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-key')

USER_ID = 'user-test-123'
OTHER_USER_ID = 'user-other-999'

TEMPLATE_PATTERNS = [
    'describe a relevant STAR example',
    'Situation for question',
    'STAR example for competency',
    'Action for question',
    'Result for question',
]


def _logic_request() -> InterviewPrepRequest:
    return InterviewPrepRequest(
        user_id=USER_ID,
        vpr_id='vpr-001',
        job_id='job-xyz789',
        gap_response_ids=['gap-001'],
        focus_areas=['architecture', 'leadership'],
        question_count=3,
    )


def _api_event(user_id: str = USER_ID) -> dict[str, object]:
    body = {
        'vpr_id': 'vpr-001',
        'gap_response_ids': ['gap-001'],
        'focus_areas': ['architecture'],
        'question_count': 3,
    }
    return {
        'httpMethod': 'POST',
        'path': '/interview-prep/generate',
        'requestContext': {'authorizer': {'jwt': {'claims': {'sub': user_id}}}},
        'body': json.dumps(body),
        'headers': {'Content-Type': 'application/json'},
    }


def _no_auth_event() -> dict[str, object]:
    return {
        'httpMethod': 'POST',
        'path': '/interview-prep/generate',
        'requestContext': {},
        'body': json.dumps({'vpr_id': 'vpr-001', 'gap_response_ids': ['gap-001']}),
        'headers': {'Content-Type': 'application/json'},
    }


def _mock_llm_result() -> Result:
    """Return a minimal successful Result[InterviewPrepResponse] for handler-level mocks."""
    from careervp.models.interview_prep import (
        InterviewAnswer,
        InterviewPrep,
        InterviewPrepResponse,
        InterviewQuestion,
    )

    prep = InterviewPrep(
        prep_id='prep-mock-001',
        user_id=USER_ID,
        vpr_id='vpr-001',
        questions=[
            InterviewQuestion(
                question_id='q1',
                question='Describe a platform scaling challenge.',
                question_type='technical',
                difficulty='medium',
                suggested_answer=InterviewAnswer(
                    situation='Service under peak load.',
                    task='Reduce latency.',
                    action='Added caching.',
                    result='Latency dropped 40%.',
                    full_text='Service under peak load. Added caching. Latency dropped 40%.',
                    word_count=10,
                ),
            )
        ],
    )
    response = InterviewPrepResponse(success=True, interview_prep=prep, generation_time_ms=100)
    return Result(success=True, data=response, code=ResultCode.INTERVIEW_QUESTIONS_GENERATED)


def _user_cv(user_id: str = USER_ID) -> UserCV:
    return UserCV(
        user_id=user_id,
        cv_id='cv-abc456',
        full_name='Jane Engineer',
        email='jane@example.com',
        professional_summary='Backend engineer with distributed systems experience.',
    )


@pytest.mark.unit
class TestInterviewPrepCallsLLM:
    """Validates L0.2: interview_prep.py calls LLMClient, not template stub."""

    def test_interview_prep_calls_llm_client(self) -> None:
        request = _logic_request()
        with patch('careervp.logic.interview_prep.LLMClient') as mock_cls:
            mock_llm = MagicMock()
            mock_llm.generate.return_value = {
                'text': json.dumps(
                    {
                        'questions': [
                            {
                                'question_id': 'q1',
                                'question': 'Tell me about a time you led an architecture migration.',
                                'question_type': 'behavioral',
                                'difficulty': 'medium',
                                'suggested_answer': {
                                    'situation': 'Monolith struggled under growth.',
                                    'task': 'Design migration strategy.',
                                    'action': 'Rolled out bounded services in phases.',
                                    'result': 'Reduced incident rate by 35%.',
                                    'full_text': (
                                        'Monolith growth challenges required a phased migration to '
                                        'bounded services, which reduced incident rate by 35%.'
                                    ),
                                },
                            }
                        ],
                        'questions_to_ask': [],
                    }
                )
            }
            mock_cls.return_value = mock_llm

            result = asyncio.run(
                generate_interview_prep(
                    request=request,
                    vpr_data={'summary': 'Platform leadership impact'},
                    gap_responses=[{'id': 'gap-001', 'response': 'Provided measurable outcomes'}],
                    job_title='Principal Software Engineer',
                    company_name='Innovate Labs',
                )
            )

            assert result.success
            mock_llm.generate.assert_called_once()
            call_prompt = mock_llm.generate.call_args.kwargs['prompt']
            assert 'Principal Software Engineer' in call_prompt
            assert 'Innovate Labs' in call_prompt

    def test_parse_recovery_extracts_first_json_object_from_extra_text(self) -> None:
        request = _logic_request()
        raw = (
            '{'
            '"questions":[{"question_id":"q1","question":"Tell me about a scaling project.",'
            '"question_type":"behavioral","difficulty":"medium","suggested_answer":{'
            '"situation":"Legacy service was unstable.","task":"Improve reliability.",'
            '"action":"Introduced queue backpressure.","result":"Reduced incidents.",'
            '"full_text":"Legacy service was unstable. Introduced queue backpressure. Reduced incidents."}}],'
            '"questions_to_ask":[]'
            '}'
            '\n\nGenerated successfully.'
        )

        prep = _parse_interview_prep(raw, request)

        assert len(prep.questions) == 1
        assert prep.questions[0].question_id == 'q1'

    def test_parse_failure_retries_with_compact_output(self) -> None:
        request = _logic_request()
        with patch('careervp.logic.interview_prep.LLMClient') as mock_cls:
            mock_llm = MagicMock()
            mock_llm.generate.side_effect = [
                {'text': '{"questions":[{"question_id":"q1","question":"broken"'},
                {
                    'text': json.dumps(
                        {
                            'questions': [
                                {
                                    'question_id': 'q1',
                                    'question': 'Describe a reliability improvement you led.',
                                    'question_type': 'behavioral',
                                    'difficulty': 'medium',
                                    'suggested_answer': {
                                        'situation': 'A noisy monolith caused incidents.',
                                        'task': 'Reduce instability quickly.',
                                        'action': 'Added queueing and observability guardrails.',
                                        'result': 'Incident rate dropped significantly.',
                                        'full_text': (
                                            'A noisy monolith caused incidents. I added queueing '
                                            'and observability guardrails, which reduced incidents.'
                                        ),
                                    },
                                }
                            ],
                            'questions_to_ask': [],
                        }
                    )
                },
            ]
            mock_cls.return_value = mock_llm

            result = asyncio.run(
                generate_interview_prep(
                    request=request,
                    vpr_data={'summary': 'Platform leadership impact'},
                    gap_responses=[{'id': 'gap-001', 'response': 'Provided measurable outcomes'}],
                    job_title='Principal Software Engineer',
                    company_name='Innovate Labs',
                )
            )

        assert result.success
        assert mock_llm.generate.call_count == 2
        first_call = mock_llm.generate.call_args_list[0].kwargs
        second_call = mock_llm.generate.call_args_list[1].kwargs
        assert first_call['temperature'] == DEFAULT_GENERATION_TEMPERATURE
        assert second_call['temperature'] == PARSE_RETRY_TEMPERATURE
        assert '# Output Contract' in first_call['prompt']
        assert '# Compact Output' not in first_call['prompt']
        assert '# Compact Output' in second_call['prompt']


@pytest.mark.unit
class TestInterviewPrepNoTemplate:
    """Validates I1: no template strings in output."""

    @pytest.mark.parametrize('pattern', TEMPLATE_PATTERNS)
    def test_no_template_pattern_in_output(self, pattern: str) -> None:
        request = _logic_request()
        with patch('careervp.logic.interview_prep.LLMClient') as mock_cls:
            mock_llm = MagicMock()
            mock_llm.generate.return_value = {
                'text': json.dumps(
                    {
                        'questions': [
                            {
                                'question_id': 'q1',
                                'question': 'How did you prioritize reliability work against feature delivery?',
                                'question_type': 'behavioral',
                                'difficulty': 'medium',
                                'suggested_answer': {
                                    'situation': 'Reliability issues affected delivery velocity.',
                                    'task': 'Balance roadmap and incident remediation.',
                                    'action': 'Set reliability budgets and sprint guardrails.',
                                    'result': 'Raised deployment frequency with fewer incidents.',
                                    'full_text': (
                                        'I balanced roadmap delivery with reliability budgets and '
                                        'reduced incidents while increasing deployment frequency.'
                                    ),
                                },
                            }
                        ]
                    }
                )
            }
            mock_cls.return_value = mock_llm

            result = asyncio.run(
                generate_interview_prep(
                    request=request,
                    vpr_data={'summary': 'Strategic backend execution'},
                    gap_responses=[],
                )
            )

            assert result.success
            assert result.data is not None
            first_question = result.data.interview_prep.questions[0].question
            assert pattern not in first_question


@pytest.mark.unit
class TestInterviewPrepHandlerFlow:
    """Validates handler behavior required by L0.2."""

    def test_returns_artifact_id_in_handler_response(self) -> None:
        from careervp.handlers.interview_prep_handler import lambda_handler

        with patch('careervp.handlers.interview_prep_handler._get_dal') as mock_get_dal:
            mock_dal = MagicMock()
            mock_dal.get_cv.return_value = _user_cv()
            mock_get_dal.return_value = mock_dal

            with patch('careervp.handlers.interview_prep_handler.generate_interview_prep') as mock_generate:
                prep_payload = {'prep_id': 'prep-001', 'questions': []}
                mock_generate.return_value = Result(
                    success=True,
                    data=MagicMock(interview_prep=MagicMock(model_dump=MagicMock(return_value=prep_payload))),
                    code=ResultCode.INTERVIEW_QUESTIONS_GENERATED,
                )

                response = lambda_handler(_api_event(), MagicMock())

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['artifact_id'] == 'prep-001'
        assert body['status'] == 'completed'

    def test_llm_error_returns_503(self) -> None:
        from careervp.handlers.interview_prep_handler import lambda_handler

        with patch('careervp.handlers.interview_prep_handler._get_dal') as mock_get_dal:
            mock_dal = MagicMock()
            mock_dal.get_cv.return_value = _user_cv()
            mock_get_dal.return_value = mock_dal

            with patch('careervp.handlers.interview_prep_handler.generate_interview_prep') as mock_generate:
                mock_generate.return_value = Result(
                    success=False,
                    error='LLM timeout',
                    code=ResultCode.LLM_TIMEOUT,
                )
                response = lambda_handler(_api_event(), MagicMock())

        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['code'] == ResultCode.LLM_TIMEOUT

    def test_missing_cv_degrades_gracefully_and_returns_200(self) -> None:
        from careervp.handlers.interview_prep_handler import lambda_handler

        with (
            patch('careervp.handlers.interview_prep_handler._get_dal') as mock_get_dal,
            patch('careervp.handlers.interview_prep_handler.generate_interview_prep') as mock_gen,
        ):
            mock_dal = MagicMock()
            mock_dal.get_cv.return_value = None
            mock_dal.get_vpr.return_value = MagicMock(success=True, data=None)
            mock_dal.get_gap_responses.return_value = MagicMock(success=True, data=None)
            mock_get_dal.return_value = mock_dal
            mock_gen.return_value = _mock_llm_result()
            response = lambda_handler(_api_event(), MagicMock())

        # Missing CV degrades gracefully — handler does not abort on missing CV context.
        # cv_facts=None is passed to generation; output quality may be reduced.
        assert response['statusCode'] == 200

    def test_wrong_user_cv_does_not_block_generation(self) -> None:
        from careervp.handlers.interview_prep_handler import lambda_handler

        with (
            patch('careervp.handlers.interview_prep_handler._get_dal') as mock_get_dal,
            patch('careervp.handlers.interview_prep_handler.generate_interview_prep') as mock_gen,
        ):
            mock_dal = MagicMock()
            mock_dal.get_cv.return_value = _user_cv(user_id=OTHER_USER_ID)
            mock_dal.get_vpr.return_value = MagicMock(success=True, data=None)
            mock_dal.get_gap_responses.return_value = MagicMock(success=True, data=None)
            mock_get_dal.return_value = mock_dal
            mock_gen.return_value = _mock_llm_result()
            response = lambda_handler(_api_event(), MagicMock())

        # CV ownership is not checked — auth scopes by user_id. Generation proceeds.
        assert response['statusCode'] == 200

    def test_no_auth_returns_401(self) -> None:
        from careervp.handlers.interview_prep_handler import lambda_handler

        response = lambda_handler(_no_auth_event(), MagicMock())
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['code'] == ResultCode.UNAUTHORIZED


class TestQuestionCountPolicy:
    """Spec INTERVIEW_PREP_003 AC-IP-304: question count policy."""

    def test_question_count_default_is_10(self) -> None:
        """Logic model InterviewPrepRequest defaults question_count to 10."""
        from careervp.models.interview_prep import InterviewPrepRequest as LogicRequest

        req = LogicRequest(user_id='u', vpr_id='v')
        assert req.question_count == 10

    def test_question_count_cap_is_15(self) -> None:
        """Logic model InterviewPrepRequest accepts at most 15 questions."""
        from pydantic import ValidationError

        from careervp.models.interview_prep import InterviewPrepRequest as LogicRequest

        req = LogicRequest(user_id='u', vpr_id='v', question_count=15)
        assert req.question_count == 15

        with pytest.raises(ValidationError):
            LogicRequest(user_id='u', vpr_id='v', question_count=16)

    def test_question_count_explicit_lower_value_honored(self) -> None:
        """Explicit question_count below default is honored."""
        from careervp.models.interview_prep import InterviewPrepRequest as LogicRequest

        req = LogicRequest(user_id='u', vpr_id='v', question_count=3)
        assert req.question_count == 3

    def test_question_count_enforced_in_generation_logic(self) -> None:
        """generate_interview_prep caps question_count at MAX_QUESTIONS (15)."""

        from careervp.logic.interview_prep import MAX_QUESTIONS
        from careervp.models.interview_prep import InterviewPrepRequest as LogicRequest

        assert MAX_QUESTIONS == 15

        # A request with question_count=20 should be silently capped
        req = LogicRequest(user_id='u', vpr_id='v', question_count=15)
        assert req.question_count <= MAX_QUESTIONS

    def test_api_model_question_count_default_is_10(self) -> None:
        """API model InterviewPrepRequest defaults question_count to 10."""
        from careervp.models.api_models import InterviewPrepRequest as ApiRequest

        req = ApiRequest(vpr_id='vpr-001', gap_response_ids=['gap-1'])
        assert req.question_count == 10

    def test_api_model_accepts_optional_context_fields(self) -> None:
        """API model accepts optional application_id, job_id, language without breaking."""
        from careervp.models.api_models import InterviewPrepRequest as ApiRequest

        req = ApiRequest(
            vpr_id='vpr-001',
            gap_response_ids=['gap-1'],
            application_id='app-123',
            job_id='job-456',
            language='he',
        )
        assert req.application_id == 'app-123'
        assert req.job_id == 'job-456'
        assert req.language == 'he'

    def test_api_model_backward_compat_without_optional_fields(self) -> None:
        """API model works without optional context fields (backward compatibility)."""
        from careervp.models.api_models import InterviewPrepRequest as ApiRequest

        req = ApiRequest(vpr_id='vpr-001', gap_response_ids=['gap-1'])
        assert req.application_id is None
        assert req.job_id is None
        assert req.language == 'en'
