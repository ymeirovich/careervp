"""Characterization tests for the D-H2 key authority (3.1-GREEN).

These pin the exact key strings and env-resolution semantics the handlers
built inline before Wave-3 step 3.1 re-homed them into
``careervp.dal.table_registry``. If any of these change, an internal key
convention changed — that is a scope-lock event, not a refactor detail.
"""

from __future__ import annotations

import pytest

from careervp.dal import table_registry
from careervp.dal.table_registry import TableRegistry


def test_key_grammar_matches_pre_rehoming_handler_strings() -> None:
    assert table_registry.cv_sort_key('cv-1') == 'CV#cv-1'
    assert table_registry.cover_letter_artifact_id('job-1') == 'ARTIFACT#COVER_LETTER#job-1'
    assert table_registry.tailored_cv_artifact_id('req-1') == 'ARTIFACT#CV_TAILORED#req-1'
    assert table_registry.interview_prep_artifact_id('job-1') == 'ARTIFACT#INTERVIEW_PREP#job-1'
    assert table_registry.company_research_artifact_sk('job-1') == 'ARTIFACT#COMPANY_RESEARCH#job-1'
    assert table_registry.company_research_kb_sk('job-1') == 'COMPANY_RESEARCH#job-1'
    assert table_registry.user_partition_key('u-1') == 'USER#u-1'
    assert table_registry.user_partition_candidates('u-1') == ('u-1', 'USER#u-1')
    assert table_registry.legacy_item_key('u-1', 'ARTIFACT#COVER_LETTER#job-1') == {
        'pk': 'u-1',
        'sk': 'ARTIFACT#COVER_LETTER#job-1',
    }
    assert table_registry.canonical_item_key('u-1', 'ARTIFACT#COVER_LETTER#job-1') == {
        'applicationId': 'u-1',
        'artifactId': 'ARTIFACT#COVER_LETTER#job-1',
    }


def test_company_research_candidates_match_pre_rehoming_order() -> None:
    assert table_registry.company_research_candidate_keys('u-1', 'job-1') == [
        {'pk': 'u-1', 'sk': 'ARTIFACT#COMPANY_RESEARCH#job-1'},
        {'pk': 'u-1', 'sk': 'COMPANY_RESEARCH#job-1'},
        {'pk': 'USER#u-1', 'sk': 'COMPANY_RESEARCH#job-1'},
    ]
    assert table_registry.company_research_query_candidates('u-1') == [
        ('u-1', 'ARTIFACT#COMPANY_RESEARCH#'),
        ('u-1', 'COMPANY_RESEARCH#'),
        ('USER#u-1', 'COMPANY_RESEARCH#'),
    ]


def test_legacy_key_condition_matches_inline_expression() -> None:
    from boto3.dynamodb.conditions import Key

    inline = Key('pk').eq('u-1') & Key('sk').begins_with('ARTIFACT#CV_TAILORED#')
    homed = table_registry.legacy_key_condition('u-1', 'ARTIFACT#CV_TAILORED#')
    assert homed.get_expression() == inline.get_expression()


def test_artifacts_chain_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ('ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('TABLE_NAME', 'from-table-name')
    assert table_registry.resolve_artifacts_table_name() == 'from-table-name'
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'from-dynamo')
    assert table_registry.resolve_artifacts_table_name() == 'from-dynamo'
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'from-artifacts')
    assert table_registry.resolve_artifacts_table_name() == 'from-artifacts'
    assert table_registry.resolve_artifacts_table_name_with_source() == ('from-artifacts', 'ARTIFACTS_TABLE_NAME')
    # The legacy two-key tail never consults ARTIFACTS_TABLE_NAME.
    assert table_registry.resolve_legacy_artifacts_table_name() == 'from-dynamo'


def test_artifacts_chain_skips_blank_values_and_strips(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ('ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', '   ')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', '  padded-table  ')
    assert table_registry.resolve_artifacts_table_name() == 'padded-table'


def test_required_resolution_raises_the_submit_handler_error(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ('ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME'):
        monkeypatch.delenv(key, raising=False)
    assert table_registry.resolve_artifacts_table_name() == ''
    assert table_registry.resolve_artifacts_table_name_with_source() == ('', 'none')
    with pytest.raises(RuntimeError, match='Artifacts table environment variable is not configured'):
        table_registry.resolve_artifacts_table_name(required=True)


def test_company_research_chain_prefers_dedicated_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ('COMPANY_RESEARCH_TABLE_NAME', 'ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'users-table-via-artifacts')
    monkeypatch.setenv('COMPANY_RESEARCH_TABLE_NAME', 'artifacts-table')
    # ai_assist_nested_stack.py points the two env keys at different tables.
    assert table_registry.resolve_company_research_table_name() == 'artifacts-table'
    assert table_registry.resolve_artifacts_table_name() == 'users-table-via-artifacts'


def test_legacy_candidates_dedupe_in_precedence_order(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ('DYNAMODB_TABLE_NAME', 'TABLE_NAME'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'same-table')
    monkeypatch.setenv('TABLE_NAME', 'same-table')
    assert table_registry.legacy_artifacts_table_candidates() == ['same-table']
    monkeypatch.setenv('TABLE_NAME', 'other-table')
    assert table_registry.legacy_artifacts_table_candidates() == ['same-table', 'other-table']


def test_registry_explicit_name_wins_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'env-table')
    assert TableRegistry(artifacts_table_name='explicit-table').artifacts_table_name == 'explicit-table'
    assert TableRegistry().artifacts_table_name == 'env-table'
