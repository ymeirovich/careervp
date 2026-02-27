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

from careervp.logic.interview_prep import generate_interview_prep
from careervp.models.cv import UserCV
from careervp.models.interview_prep import InterviewPrepRequest
from careervp.models.result import Result, ResultCode

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

USER_ID = "user-test-123"
OTHER_USER_ID = "user-other-999"

TEMPLATE_PATTERNS = [
    "describe a relevant STAR example",
    "Situation for question",
    "STAR example for competency",
    "Action for question",
    "Result for question",
]


def _logic_request() -> InterviewPrepRequest:
    return InterviewPrepRequest(
        user_id=USER_ID,
        vpr_id="vpr-001",
        job_id="job-xyz789",
        gap_response_ids=["gap-001"],
        focus_areas=["architecture", "leadership"],
        question_count=3,
    )


def _api_event(user_id: str = USER_ID) -> dict[str, object]:
    body = {
        "vpr_id": "vpr-001",
        "gap_response_ids": ["gap-001"],
        "focus_areas": ["architecture"],
        "question_count": 3,
    }
    return {
        "httpMethod": "POST",
        "path": "/interview-prep/generate",
        "requestContext": {"authorizer": {"jwt": {"claims": {"sub": user_id}}}},
        "body": json.dumps(body),
        "headers": {"Content-Type": "application/json"},
    }


def _no_auth_event() -> dict[str, object]:
    return {
        "httpMethod": "POST",
        "path": "/interview-prep/generate",
        "requestContext": {},
        "body": json.dumps({"vpr_id": "vpr-001", "gap_response_ids": ["gap-001"]}),
        "headers": {"Content-Type": "application/json"},
    }


def _user_cv(user_id: str = USER_ID) -> UserCV:
    return UserCV(
        user_id=user_id,
        cv_id="cv-abc456",
        full_name="Jane Engineer",
        email="jane@example.com",
        professional_summary="Backend engineer with distributed systems experience.",
    )


@pytest.mark.unit
class TestInterviewPrepCallsLLM:
    """Validates L0.2: interview_prep.py calls LLMClient, not template stub."""

    def test_interview_prep_calls_llm_client(self) -> None:
        request = _logic_request()
        with patch("careervp.logic.interview_prep.LLMClient") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.generate.return_value = {
                "text": json.dumps(
                    {
                        "questions": [
                            {
                                "question_id": "q1",
                                "question": "Tell me about a time you led an architecture migration.",
                                "question_type": "behavioral",
                                "difficulty": "medium",
                                "suggested_answer": {
                                    "situation": "Monolith struggled under growth.",
                                    "task": "Design migration strategy.",
                                    "action": "Rolled out bounded services in phases.",
                                    "result": "Reduced incident rate by 35%.",
                                    "full_text": (
                                        "Monolith growth challenges required a phased migration to "
                                        "bounded services, which reduced incident rate by 35%."
                                    ),
                                },
                            }
                        ],
                        "questions_to_ask": [],
                    }
                )
            }
            mock_cls.return_value = mock_llm

            result = asyncio.run(
                generate_interview_prep(
                    request=request,
                    vpr_data={"summary": "Platform leadership impact"},
                    gap_responses=[{"id": "gap-001", "response": "Provided measurable outcomes"}],
                    job_title="Principal Software Engineer",
                    company_name="Innovate Labs",
                )
            )

            assert result.success
            mock_llm.generate.assert_called_once()
            call_prompt = mock_llm.generate.call_args.kwargs["prompt"]
            assert "Principal Software Engineer" in call_prompt
            assert "Innovate Labs" in call_prompt


@pytest.mark.unit
class TestInterviewPrepNoTemplate:
    """Validates I1: no template strings in output."""

    @pytest.mark.parametrize("pattern", TEMPLATE_PATTERNS)
    def test_no_template_pattern_in_output(self, pattern: str) -> None:
        request = _logic_request()
        with patch("careervp.logic.interview_prep.LLMClient") as mock_cls:
            mock_llm = MagicMock()
            mock_llm.generate.return_value = {
                "text": json.dumps(
                    {
                        "questions": [
                            {
                                "question_id": "q1",
                                "question": "How did you prioritize reliability work against feature delivery?",
                                "question_type": "behavioral",
                                "difficulty": "medium",
                                "suggested_answer": {
                                    "situation": "Reliability issues affected delivery velocity.",
                                    "task": "Balance roadmap and incident remediation.",
                                    "action": "Set reliability budgets and sprint guardrails.",
                                    "result": "Raised deployment frequency with fewer incidents.",
                                    "full_text": (
                                        "I balanced roadmap delivery with reliability budgets and "
                                        "reduced incidents while increasing deployment frequency."
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
                    vpr_data={"summary": "Strategic backend execution"},
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

        with patch("careervp.handlers.interview_prep_handler._get_dal") as mock_get_dal:
            mock_dal = MagicMock()
            mock_dal.get_cv.return_value = _user_cv()
            mock_get_dal.return_value = mock_dal

            with patch("careervp.handlers.interview_prep_handler.generate_interview_prep") as mock_generate:
                prep_payload = {"prep_id": "prep-001", "questions": []}
                mock_generate.return_value = Result(
                    success=True,
                    data=MagicMock(interview_prep=MagicMock(model_dump=MagicMock(return_value=prep_payload))),
                    code=ResultCode.INTERVIEW_QUESTIONS_GENERATED,
                )

                response = lambda_handler(_api_event(), MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["artifact_id"] == "prep-001"
        assert body["status"] == "completed"

    def test_llm_error_returns_503(self) -> None:
        from careervp.handlers.interview_prep_handler import lambda_handler

        with patch("careervp.handlers.interview_prep_handler._get_dal") as mock_get_dal:
            mock_dal = MagicMock()
            mock_dal.get_cv.return_value = _user_cv()
            mock_get_dal.return_value = mock_dal

            with patch("careervp.handlers.interview_prep_handler.generate_interview_prep") as mock_generate:
                mock_generate.return_value = Result(
                    success=False,
                    error="LLM timeout",
                    code=ResultCode.LLM_TIMEOUT,
                )
                response = lambda_handler(_api_event(), MagicMock())

        assert response["statusCode"] == 503
        body = json.loads(response["body"])
        assert body["code"] == ResultCode.LLM_TIMEOUT

    def test_missing_cv_returns_404(self) -> None:
        from careervp.handlers.interview_prep_handler import lambda_handler

        with patch("careervp.handlers.interview_prep_handler._get_dal") as mock_get_dal:
            mock_dal = MagicMock()
            mock_dal.get_cv.return_value = None
            mock_get_dal.return_value = mock_dal
            response = lambda_handler(_api_event(), MagicMock())

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["code"] == ResultCode.CV_NOT_FOUND

    def test_wrong_user_returns_403(self) -> None:
        from careervp.handlers.interview_prep_handler import lambda_handler

        with patch("careervp.handlers.interview_prep_handler._get_dal") as mock_get_dal:
            mock_dal = MagicMock()
            mock_dal.get_cv.return_value = _user_cv(user_id=OTHER_USER_ID)
            mock_get_dal.return_value = mock_dal
            response = lambda_handler(_api_event(), MagicMock())

        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert body["code"] == ResultCode.FORBIDDEN

    def test_no_auth_returns_401(self) -> None:
        from careervp.handlers.interview_prep_handler import lambda_handler

        response = lambda_handler(_no_auth_event(), MagicMock())
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert body["code"] == ResultCode.UNAUTHORIZED
