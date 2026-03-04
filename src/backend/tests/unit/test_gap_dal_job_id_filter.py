"""Unit tests: DAL list_gap_questions_by_prefix job_id filtering.

Traceability: AC-GAP-002 — GET returns persisted questions for same job_id.
Spec: docs/beta/fix-api/yaml2/gap_questions_read_after_write.yaml
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('POWERTOOLS_SERVICE_NAME', 'careervp-gap-dal-test')
os.environ.setdefault('LOG_LEVEL', 'INFO')


def _make_gap_item(
    user_id: str,
    cv_id: str,
    job_id: str,
    questions: list[dict[str, Any]] | None = None,
    created_at: str = '2026-03-04T10:00:00+00:00',
) -> dict[str, Any]:
    """Build a DynamoDB item matching the gap analysis storage schema."""
    return {
        'pk': user_id,
        'sk': f'ARTIFACT#GAP_ANALYSIS#{cv_id}#{job_id}',
        'artifact_type': 'gap_analysis',
        'user_id': user_id,
        'cv_id': cv_id,
        'job_id': job_id,
        'questions': questions or [{'question_id': 'q1', 'question': 'Describe impact.'}],
        'created_at': created_at,
        'updated_at': created_at,
    }


def _dal(table_name: str = 'test-table') -> Any:
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    return DynamoDalHandler(table_name=table_name)


@pytest.mark.unit
def test_filter_by_job_id_field_match() -> None:
    """Items with matching job_id field are returned; others are excluded."""
    dal = _dal()
    items = [
        _make_gap_item('u1', 'cv1', 'job-target'),
        _make_gap_item('u1', 'cv1', 'job-other'),
    ]

    mock_table = MagicMock()
    mock_table.query.return_value = {'Items': items}

    with patch.object(dal, '_get_db_handler', return_value=mock_table):
        result = dal.list_gap_questions_by_prefix(user_id='u1', job_id='job-target')

    assert result.success, 'Expected successful result'
    assert result.data is not None, 'Expected non-None data'
    assert len(result.data) == 1, f'Expected 1 item but got {len(result.data)}'
    assert result.data[0]['job_id'] == 'job-target'


@pytest.mark.unit
def test_filter_by_sk_suffix_match() -> None:
    """Items matching via sk suffix (#{job_id}) are included even if job_id field differs."""
    dal = _dal()
    target_job = 'job-suffix-match'
    item_with_sk = {
        'pk': 'u2',
        'sk': f'ARTIFACT#GAP_ANALYSIS#cv2#{target_job}',
        'artifact_type': 'gap_analysis',
        'user_id': 'u2',
        'cv_id': 'cv2',
        'job_id': target_job,
        'questions': [],
        'created_at': '2026-03-04T10:00:00+00:00',
        'updated_at': '2026-03-04T10:00:00+00:00',
    }
    unrelated_item = _make_gap_item('u2', 'cv2', 'job-unrelated')

    mock_table = MagicMock()
    mock_table.query.return_value = {'Items': [item_with_sk, unrelated_item]}

    with patch.object(dal, '_get_db_handler', return_value=mock_table):
        result = dal.list_gap_questions_by_prefix(user_id='u2', job_id=target_job)

    assert result.success
    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0]['sk'].endswith(f'#{target_job}')


@pytest.mark.unit
def test_filter_is_case_insensitive() -> None:
    """job_id matching is case-insensitive via casefold normalization."""
    dal = _dal()
    item = _make_gap_item('u3', 'cv3', 'JOB-CASE')

    mock_table = MagicMock()
    mock_table.query.return_value = {'Items': [item]}

    with patch.object(dal, '_get_db_handler', return_value=mock_table):
        result = dal.list_gap_questions_by_prefix(user_id='u3', job_id='job-case')

    assert result.success
    assert result.data is not None
    assert len(result.data) == 1, 'Case-insensitive match should return item'


@pytest.mark.unit
def test_no_job_id_returns_all_items() -> None:
    """When job_id is None, all gap items are returned without filtering."""
    dal = _dal()
    items = [
        _make_gap_item('u4', 'cv4', 'job-a'),
        _make_gap_item('u4', 'cv4', 'job-b'),
    ]

    mock_table = MagicMock()
    mock_table.query.return_value = {'Items': items}

    with patch.object(dal, '_get_db_handler', return_value=mock_table):
        result = dal.list_gap_questions_by_prefix(user_id='u4', job_id=None)

    assert result.success
    assert result.data is not None
    assert len(result.data) == 2


@pytest.mark.unit
def test_no_matching_items_returns_none() -> None:
    """When no items match the job_id filter, result.data is None (empty sentinel)."""
    dal = _dal()
    items = [_make_gap_item('u5', 'cv5', 'job-other')]

    mock_table = MagicMock()
    mock_table.query.return_value = {'Items': items}

    with patch.object(dal, '_get_db_handler', return_value=mock_table):
        result = dal.list_gap_questions_by_prefix(user_id='u5', job_id='job-missing')

    assert result.success
    assert result.data is None, 'No matches should yield None data (empty sentinel)'


@pytest.mark.unit
def test_sk_suffix_includes_job_id_segment() -> None:
    """Persisted sk ends with #{job_id} per AC-GAP-002 data-level requirement."""
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    dal = DynamoDalHandler(table_name='test')
    sk = dal._build_gap_analysis_sort_key(cv_id='cv-x', job_id='job-y')
    assert sk.endswith('#job-y'), f'Expected sk to end with #job-y, got: {sk}'


@pytest.mark.unit
def test_paginated_results_are_collected() -> None:
    """list_gap_questions_by_prefix handles DynamoDB pagination correctly."""
    dal = _dal()
    page1_item = _make_gap_item('u6', 'cv6', 'job-pg')
    page2_item = _make_gap_item('u6', 'cv7', 'job-pg')

    mock_table = MagicMock()
    mock_table.query.side_effect = [
        {'Items': [page1_item], 'LastEvaluatedKey': {'pk': 'u6', 'sk': 'cursor'}},
        {'Items': [page2_item]},
    ]

    with patch.object(dal, '_get_db_handler', return_value=mock_table):
        result = dal.list_gap_questions_by_prefix(user_id='u6', job_id='job-pg')

    assert result.success
    assert result.data is not None
    assert len(result.data) == 2, 'Both pages should be collected'
