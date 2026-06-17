"""FE-UI-044 red tests for canonical Company Research store resolution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from careervp.models.company import CompanyResearchResult, ResearchSource

pytestmark = pytest.mark.unit


def _confident_result(company_name: str = 'Acme') -> CompanyResearchResult:
    return CompanyResearchResult(
        company_name=company_name,
        overview='Acme builds reliable workflow automation for enterprise teams.',
        mission='Make enterprise work easier to operate.',
        values=['Reliability', 'Customer focus'],
        strategic_priorities=['Workflow automation', 'Enterprise AI'],
        recent_news=['Launched an AI operations suite'],
        financial_summary='Privately held',
        source=ResearchSource.WEBSITE_SCRAPE,
        source_urls=['https://acme.example/about'],
        confidence_score=0.91,
        research_timestamp=datetime(2026, 6, 14, 9, 0, tzinfo=timezone.utc),
    )


def _clear_cr_table_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_key in (
        'ARTIFACTS_TABLE_NAME',
        'KNOWLEDGE_TABLE_NAME',
        'TABLE_NAME',
        'DYNAMODB_TABLE_NAME',
        'COMPANY_RESEARCH_LEGACY_READ_ENABLED',
    ):
        monkeypatch.delenv(env_key, raising=False)


def test_cr_artifact_key_uses_real_application_id_not_generated_uuid() -> None:
    from careervp.logic.company_research_store import cr_artifact_key

    assert cr_artifact_key('app-123') == {
        'applicationId': 'app-123',
        'artifactId': 'ARTIFACT#COMPANY_RESEARCH#app-123',
    }


@pytest.mark.parametrize(
    'env_overrides',
    [
        {'ARTIFACTS_TABLE_NAME': 'artifacts-table'},
        {
            'ARTIFACTS_TABLE_NAME': 'artifacts-table',
            'KNOWLEDGE_TABLE_NAME': 'knowledge-table-empty-wrong-schema',
            'TABLE_NAME': 'legacy-users-table',
            'DYNAMODB_TABLE_NAME': 'legacy-users-table',
        },
        {
            'ARTIFACTS_TABLE_NAME': 'artifacts-table',
            'KNOWLEDGE_TABLE_NAME': 'knowledge-table-empty-wrong-schema',
            'TABLE_NAME': 'other-table',
            'DYNAMODB_TABLE_NAME': 'legacy-users-table',
        },
    ],
)
def test_reader_and_writer_always_use_artifacts_table(monkeypatch: pytest.MonkeyPatch, env_overrides: dict[str, str]) -> None:
    from careervp.logic import company_research_store

    _clear_cr_table_env(monkeypatch)
    for env_key, env_value in env_overrides.items():
        monkeypatch.setenv(env_key, env_value)
    monkeypatch.setenv('COMPANY_RESEARCH_LEGACY_READ_ENABLED', 'false')

    table_calls: list[tuple[str, str]] = []

    class FakeTable:
        def __init__(self, table_name: str) -> None:
            self.table_name = table_name

        def get_item(self, **_: Any) -> dict[str, Any]:
            table_calls.append(('read', self.table_name))
            return {}

        def query(self, **_: Any) -> dict[str, Any]:
            table_calls.append(('read', self.table_name))
            return {'Items': []}

        def put_item(self, **_: Any) -> dict[str, Any]:
            table_calls.append(('write', self.table_name))
            return {}

    monkeypatch.setattr(company_research_store, '_table', lambda table_name: FakeTable(table_name))

    company_research_store.read_cr_artifact(application_id='app-123', user_id='user-1')
    company_research_store.write_cr_artifact(application_id='app-123', user_id='user-1', result=_confident_result('Acme Sync'))
    company_research_store.write_cr_artifact(application_id='app-123', user_id='user-1', result=_confident_result('Acme Worker'))

    assert table_calls
    assert {table_name for _, table_name in table_calls} == {'artifacts-table'}
    assert {operation for operation, _ in table_calls} == {'read', 'write'}
