"""Unit tests for FE-UI-046 InterviewQuestion user-answer fields (AC-015 model layer)."""

from __future__ import annotations

from careervp.models.interview_prep import InterviewQuestion


def test_legacy_question_without_answer_fields_deserializes() -> None:
    """Pre-existing items (no answer fields) load with safe defaults."""
    question = InterviewQuestion.model_validate(
        {
            'question_id': 'q1',
            'question': 'Tell me about yourself.',
            'question_type': 'behavioral',
        }
    )
    assert question.answer is None
    assert question.answer_version == 0
    assert question.answer_updated_at is None
    # suggested_answer remains optional and untouched
    assert question.suggested_answer is None


def test_question_accepts_user_answer_fields() -> None:
    question = InterviewQuestion.model_validate(
        {
            'question_id': 'q1',
            'question': 'Tell me about yourself.',
            'question_type': 'behavioral',
            'answer': '## STAR answer',
            'answer_version': 2,
            'answer_updated_at': '2026-06-20T10:00:00+00:00',
        }
    )
    assert question.answer == '## STAR answer'
    assert question.answer_version == 2
    assert question.answer_updated_at is not None
