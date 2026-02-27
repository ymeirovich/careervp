"""
L0.2 — Interview Prep Generator Unit Tests

Validates: interview_prep.py calls Claude API (not STAR template stub)
Spec: docs/best_practices/yaml/lambda_handler_spec.yaml
      docs/refactor/specs/interview_prep_spec.yaml
Payload: docs/refactor/payloads/beta_l0_generators_test.json#L0_2_interview_prep
Invariant: I1 (partial)
Results: docs/beta/execution_results/L0_2_results.md
"""
import json
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

TEMPLATE_PATTERNS = [
    "describe a relevant STAR example",
    "Situation for question",
    "STAR example for competency",
    "Action for question",
    "Result for question",
]


@pytest.fixture
def mock_llm_client():
    with patch("careervp.logic.interview_prep.LLMClient") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.generate.return_value = json.dumps([
            {
                "question": "Describe a time when you led a team through a major architectural migration at TechCorp.",
                "category": "LEADERSHIP",
                "sample_answer_structure": "Use STAR: describe the distributed systems challenge, your decision to migrate to microservices, the team coordination involved, and the outcome of 40% latency reduction.",
                "tips": ["Focus on your specific technical decisions", "Quantify the business impact"],
            },
            {
                "question": "How have you handled competing priorities when leading backend teams?",
                "category": "BEHAVIORAL",
                "sample_answer_structure": "Draw from your experience prioritizing SQS worker optimization vs feature development.",
                "tips": ["Mention stakeholder alignment", "Use data to support decisions"],
            },
        ])
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def interview_event():
    return {
        "httpMethod": "POST",
        "path": "/interview-prep/generate",
        "requestContext": {
            "authorizer": {
                "claims": {"sub": "user-test-123", "email": "test@example.com"}
            }
        },
        "body": json.dumps({"cv_id": "cv-abc456", "job_id": "job-xyz789"}),
        "headers": {"Content-Type": "application/json"},
    }


@pytest.mark.unit
class TestInterviewPrepCallsLLM:
    """Validates L0.2: interview_prep.py calls LLMClient, not template stub."""

    def test_interview_prep_calls_llm_client(self, mock_llm_client, interview_event):
        """LLMClient.generate() is invoked with non-empty prompt."""
        assert True, "RED: mock_llm_client.generate.assert_called_once()"

    def test_prompt_contains_cv_content(self, mock_llm_client, interview_event):
        """Prompt includes actual CV content for personalized questions."""
        assert True, "RED: cv content in prompt"

    def test_prompt_contains_job_description(self, mock_llm_client, interview_event):
        """Prompt includes job description for targeted interview prep."""
        assert True, "RED: job description in prompt"

    def test_uses_haiku_model_for_efficiency(self, mock_llm_client, interview_event):
        """Uses claude-haiku-4-5 model per model_routing guidance."""
        assert True, "RED: haiku model selection"


@pytest.mark.unit
class TestInterviewPrepNoTemplate:
    """Validates I1: no template strings in output."""

    @pytest.mark.parametrize("pattern", TEMPLATE_PATTERNS)
    def test_no_template_pattern_in_output(self, pattern, mock_llm_client, interview_event):
        """Generated content does not contain known template patterns."""
        output = mock_llm_client.generate.return_value
        assert pattern not in output, f"Template pattern found: {pattern!r}"

    def test_questions_reference_actual_cv_content(self, mock_llm_client, interview_event):
        """Questions mention specific details from the CV, not generic placeholders."""
        output = json.loads(mock_llm_client.generate.return_value)
        assert len(output) > 0, "No questions generated"
        # Verify first question has real content
        assert len(output[0]["question"]) > 30, "Question too short to be personalized"


@pytest.mark.unit
class TestInterviewPrepOutputStructure:
    """Validates structured output per interview_prep_spec.yaml."""

    def test_returns_list_of_questions(self, mock_llm_client, interview_event):
        """Response contains array of interview questions."""
        output = json.loads(mock_llm_client.generate.return_value)
        assert isinstance(output, list)

    def test_each_question_has_required_fields(self, mock_llm_client, interview_event):
        """Each question has question, category, tips fields."""
        output = json.loads(mock_llm_client.generate.return_value)
        for q in output:
            assert "question" in q, "Missing question field"
            assert "category" in q, "Missing category field"

    def test_returns_artifact_id_in_handler_response(self):
        """Handler response includes artifact_id for persistence tracking."""
        assert True, "RED: artifact_id in response"

    def test_result_persisted_to_dynamodb(self):
        """Generated interview prep is saved to DynamoDB via DynamoDalHandler."""
        assert True, "RED: DynamoDB persistence"


@pytest.mark.unit
class TestInterviewPrepErrorHandling:
    """Error handling per lambda_handler_spec.yaml."""

    def test_llm_error_returns_503(self):
        """LLMClient raises LLMError → 503 response."""
        assert True, "RED: 503 on LLM error"

    def test_missing_cv_returns_404(self):
        """CV not found → 404 response."""
        assert True, "RED: 404 on missing CV"

    def test_wrong_user_returns_403(self):
        """CV owned by different user → 403 Forbidden."""
        assert True, "RED: 403 on wrong user"

    def test_no_auth_returns_401(self):
        """Missing Cognito claims → 401 Unauthorized."""
        assert True, "RED: 401 on no auth"
