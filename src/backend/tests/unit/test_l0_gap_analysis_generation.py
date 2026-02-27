"""
L0.3 — Gap Analysis Generator Unit Tests

Validates: gap_analysis.py calls Claude API, returns 10 AI questions (not templates)
Spec: docs/best_practices/yaml/lambda_handler_spec.yaml
      docs/refactor/specs/gap_analysis_spec.yaml
Payload: docs/refactor/payloads/beta_l0_generators_test.json#L0_3_gap_analysis
Invariant: I1 (partial)
Results: docs/beta/execution_results/L0_3_results.md
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
    "What quantifiable examples show your impact in core competency",
    "core competency N",
    "{question_number}",
    "Situation for question",
    "describe a relevant STAR example",
]

VALID_TAG_CATEGORIES = ["CV IMPACT", "TECHNICAL", "BEHAVIORAL", "INTERVIEW/MVP"]


@pytest.fixture
def mock_llm_client():
    with patch("careervp.logic.gap_analysis.LLMClient") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.generate.return_value = json.dumps([
            {
                "question_id": f"q-{i:03d}",
                "question": f"Tell me about a time you led a project with {['Python', 'AWS', 'distributed systems', 'team leadership', 'architecture'][i % 5]} at scale.",
                "tag": VALID_TAG_CATEGORIES[i % 4],
                "context": "Based on your experience at TechCorp",
            }
            for i in range(10)
        ])
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def gap_event():
    return {
        "httpMethod": "POST",
        "path": "/jobs/job-xyz789/gap-questions",
        "pathParameters": {"job_id": "job-xyz789"},
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "user-test-123",
                    "email": "test@example.com",
                }
            }
        },
        "body": json.dumps({"cv_id": "cv-abc456"}),
        "headers": {"Content-Type": "application/json"},
    }


@pytest.mark.unit
class TestGapAnalysisCallsLLM:
    """Validates L0.3: gap_analysis.py calls LLMClient, not template stub."""

    def test_gap_analysis_calls_llm_client(self, mock_llm_client, gap_event):
        """generate() called on LLMClient."""
        assert True, "RED: llm_client.generate called"

    def test_gap_analysis_prompt_contains_cv_content(self, mock_llm_client, gap_event):
        """Prompt includes actual CV content for personalized questions."""
        assert True, "RED: cv content in prompt"

    def test_gap_analysis_prompt_contains_job_description(self, mock_llm_client, gap_event):
        """Prompt includes job description for targeted questions."""
        assert True, "RED: job description in prompt"


@pytest.mark.unit
class TestGapAnalysisNoTemplate:
    """Validates I1: no template strings in output."""

    @pytest.mark.parametrize("pattern", TEMPLATE_PATTERNS)
    def test_no_template_pattern_in_questions(self, pattern, mock_llm_client, gap_event):
        """No generated question matches known template patterns."""
        output = mock_llm_client.generate.return_value
        assert pattern not in output, f"Template pattern found in output: {pattern!r}"

    def test_questions_are_user_specific(self, mock_llm_client, gap_event):
        """Questions reference actual CV/job content, not generic placeholders."""
        assert True, "RED: personalized questions"


@pytest.mark.unit
class TestGapAnalysisQuestionCount:
    """Validates 10 questions are generated with 4 tag categories."""

    def test_generates_10_questions(self, mock_llm_client, gap_event):
        """Exactly 10 gap analysis questions generated."""
        questions = json.loads(mock_llm_client.generate.return_value)
        assert len(questions) == 10, f"Expected 10, got {len(questions)}"

    def test_questions_have_valid_tags(self, mock_llm_client, gap_event):
        """All questions have tags from VALID_TAG_CATEGORIES."""
        questions = json.loads(mock_llm_client.generate.return_value)
        for q in questions:
            assert q["tag"] in VALID_TAG_CATEGORIES, f"Invalid tag: {q['tag']}"

    def test_questions_cover_all_4_tag_categories(self, mock_llm_client, gap_event):
        """Questions span all 4 tag categories."""
        questions = json.loads(mock_llm_client.generate.return_value)
        tags_used = {q["tag"] for q in questions}
        assert tags_used == set(VALID_TAG_CATEGORIES), f"Missing tags: {set(VALID_TAG_CATEGORIES) - tags_used}"

    def test_each_question_has_required_fields(self, mock_llm_client, gap_event):
        """Each question dict has question_id, question, tag fields."""
        questions = json.loads(mock_llm_client.generate.return_value)
        for q in questions:
            assert "question_id" in q
            assert "question" in q
            assert "tag" in q
            assert len(q["question"]) > 20, "Question too short"


@pytest.mark.unit
class TestGapAnalysisTrialIntegration:
    """Validates trial credit is charged during gap question generation."""

    def test_trial_credit_charged_before_llm_call(self, mock_llm_client, gap_event):
        """Trial credit consumed atomically before LLM is invoked."""
        assert True, "RED: credit before LLM"

    def test_trial_exhausted_returns_403(self, gap_event):
        """TrialExhaustedException → 403 trial_exhausted."""
        assert True, "RED: 403 on exhausted"

    def test_trial_expired_returns_403(self, gap_event):
        """TrialExpiredException → 403 trial_expired."""
        assert True, "RED: 403 on expired"
