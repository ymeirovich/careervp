"""Regression tests for the stored gap-response -> GapResponse contract.

The writer (gap_handler._normalize_submitted_response_entry, persisted via
save_gap_responses_raw) stores {question_id, response}. GapResponse requires
{question_id, question, answer}. get_gap_responses read one as the other, so
every call raised ValidationError and was reported as a DAL failure -- and
interview prep generated from CV+VPR alone, without the candidate's answers.

The existing interview-prep context tests all mock the DAL, so none of them
exercised model_validate against the real stored shape. These do: they drive
the real DynamoDalHandler with the exact item shape observed in
careervp-gap-responses-table-devx.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('POWERTOOLS_SERVICE_NAME', 'test')
os.environ.setdefault('LOG_LEVEL', 'INFO')

# The exact shape observed live (2026-09-23): no 'question', answer under 'response'.
STORED_ANSWER = 'I led a three-person team migrating a monolith to Lambda over eight months.'
STORED_ITEM: dict[str, Any] = {
    'userId': 'user-1',
    'questionId': 'ARTIFACT#GAP_RESPONSES#v1',
    'artifact_type': 'gap_responses',
    'version': 1,
    'responses': [
        {'question_id': 'Q1', 'response': STORED_ANSWER},
        {'question_id': 'Q2', 'response': 'Second answer.'},
    ],
}


def _dal_with(item: dict[str, Any]) -> tuple[Any, Any]:
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    table = MagicMock()
    table.get_item.return_value = {'Item': item}
    table.query.return_value = {'Items': [item]}
    return DynamoDalHandler('test-gap-responses-table'), table


def test_stored_shape_is_readable_at_all() -> None:
    """The stored {question_id, response} shape must not fail validation."""
    dal, table = _dal_with(STORED_ITEM)
    with patch.object(type(dal), '_get_db_handler', return_value=table):
        result = dal.get_gap_responses('user-1', version=1)

    assert result.success is True, f'gap response lookup failed: {result.error}'
    assert result.data is not None
    assert len(result.data) == 2


def test_candidate_answer_text_survives_verbatim() -> None:
    """A green lookup is not enough -- the answer text must actually arrive.

    This is the assertion that a passing J8 did not make.
    """
    dal, table = _dal_with(STORED_ITEM)
    with patch.object(type(dal), '_get_db_handler', return_value=table):
        result = dal.get_gap_responses('user-1', version=1)

    assert result.data is not None
    answers = [r.answer for r in result.data]
    assert STORED_ANSWER in answers, 'the candidate answer did not reach the caller'
    assert [r.question_id for r in result.data] == ['Q1', 'Q2']


def test_question_falls_back_to_question_id_when_not_persisted() -> None:
    """'question' is stored nowhere; mirror the VPR worker's existing fallback."""
    dal, table = _dal_with(STORED_ITEM)
    with patch.object(type(dal), '_get_db_handler', return_value=table):
        result = dal.get_gap_responses('user-1', version=1)

    assert result.data is not None
    assert result.data[0].question == 'Q1'


def test_canonical_shape_still_reads_unchanged() -> None:
    """save_gap_responses (typed) writes question/answer; that must keep working."""
    canonical = dict(STORED_ITEM)
    canonical['responses'] = [
        {
            'question_id': 'Q1',
            'question': 'Describe a migration you led.',
            'answer': STORED_ANSWER,
            'destination': 'INTERVIEW_MVP_ONLY',
        }
    ]
    dal, table = _dal_with(canonical)
    with patch.object(type(dal), '_get_db_handler', return_value=table):
        result = dal.get_gap_responses('user-1', version=1)

    assert result.data is not None
    entry = result.data[0]
    assert entry.question == 'Describe a migration you led.'
    assert entry.answer == STORED_ANSWER
    assert entry.destination == 'INTERVIEW_MVP_ONLY'


def test_latest_version_query_path_maps_too() -> None:
    """The version=None branch takes a different code path; cover it as well."""
    dal, table = _dal_with(STORED_ITEM)
    with patch.object(type(dal), '_get_db_handler', return_value=table):
        result = dal.get_gap_responses('user-1')

    assert result.success is True
    assert result.data is not None
    assert result.data[0].answer == STORED_ANSWER
