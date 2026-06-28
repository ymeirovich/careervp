"""FE-UI-044 unit tests for Company Research dependency gate semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

from careervp.logic.artifact_dependency_resolver import resolve_dependencies

pytestmark = pytest.mark.unit


@dataclass
class FakeRepos:
    artifacts: dict[str, dict[str, Any] | None] = field(default_factory=dict)
    application: dict[str, Any] = field(default_factory=dict)
    stale_artifacts: set[str] = field(default_factory=set)

    def get_application(self, application_id: str, user_id: str) -> dict[str, Any] | None:
        if self.application.get('application_id') not in {None, application_id}:
            return None
        if self.application.get('user_id') not in {None, user_id}:
            return None
        return self.application

    def get_artifact(self, artifact_type: str, application_id: str) -> dict[str, Any] | None:
        artifact = self.artifacts.get(artifact_type)
        if artifact is None:
            return None
        if artifact.get('application_id') not in {None, application_id}:
            return None
        return artifact

    def is_artifact_stale(self, artifact_type: str, artifact: dict[str, Any], application: dict[str, Any] | None) -> bool:
        _ = artifact, application
        return artifact_type in self.stale_artifacts


def _artifact(artifact_type: str, *, user_id: str = 'user-1', created_at: str = '2026-06-14T09:00:00+00:00') -> dict[str, Any]:
    return {
        'artifact_id': f'{artifact_type}-1',
        'artifact_type': artifact_type,
        'application_id': 'app-1',
        'user_id': user_id,
        'created_at': created_at,
    }


def _application() -> dict[str, Any]:
    return {
        'application_id': 'app-1',
        'user_id': 'user-1',
        'artifact_statuses': {},
    }


def _repos_for_ready(artifact_type: str) -> FakeRepos:
    artifacts: dict[str, dict[str, Any] | None] = {'company_research': _artifact('company_research')}
    if artifact_type == 'cover_letter':
        artifacts['vpr'] = _artifact('vpr')
    return FakeRepos(artifacts=artifacts, application=_application())


def _repos_for_missing_cr(artifact_type: str) -> FakeRepos:
    artifacts: dict[str, dict[str, Any] | None] = {}
    if artifact_type == 'cover_letter':
        artifacts['vpr'] = _artifact('vpr')
    return FakeRepos(artifacts=artifacts, application=_application())


@pytest.mark.parametrize('artifact_type', ['vpr', 'cover_letter'])
def test_cr_present_returns_ready(artifact_type: str) -> None:
    start_chain = MagicMock(return_value='arn:aws:states:us-east-1:123456789012:execution:chain:unused')

    resolution = resolve_dependencies(
        artifact_type=artifact_type,
        application_id='app-1',
        user_id='user-1',
        repos=_repos_for_ready(artifact_type),
        start_chain=start_chain,
        chain_enabled=True,
    )

    assert resolution.status == 'ready'
    assert 'company_research' in resolution.resolved_upstream
    if artifact_type == 'cover_letter':
        assert 'vpr' in resolution.resolved_upstream
    assert resolution.generating == []
    assert resolution.http_status == 200
    start_chain.assert_not_called()


@pytest.mark.parametrize('artifact_type', ['vpr', 'cover_letter'])
def test_cr_missing_with_chain_disabled_returns_upstream_required(artifact_type: str) -> None:
    start_chain = MagicMock(return_value='arn:aws:states:us-east-1:123456789012:execution:chain:off')

    resolution = resolve_dependencies(
        artifact_type=artifact_type,
        application_id='app-1',
        user_id='user-1',
        repos=_repos_for_missing_cr(artifact_type),
        start_chain=start_chain,
        chain_enabled=False,
    )

    assert resolution.status == 'upstream_required'
    assert resolution.http_status == 409
    assert 'company_research' in resolution.missing
    assert resolution.generating == []
    start_chain.assert_not_called()


@pytest.mark.parametrize('artifact_type', ['vpr', 'cover_letter'])
def test_cr_missing_with_chain_enabled_starts_company_research_node(artifact_type: str) -> None:
    start_chain = MagicMock(return_value='arn:aws:states:us-east-1:123456789012:execution:chain:cr')

    resolution = resolve_dependencies(
        artifact_type=artifact_type,
        application_id='app-1',
        user_id='user-1',
        repos=_repos_for_missing_cr(artifact_type),
        start_chain=start_chain,
        chain_enabled=True,
    )

    assert resolution.status == 'dependency_generating'
    assert resolution.http_status == 202
    assert 'company_research' in resolution.missing
    assert resolution.generating[0] == 'company_research'
    assert resolution.chain_execution_arn == 'arn:aws:states:us-east-1:123456789012:execution:chain:cr'
    start_chain.assert_called_once_with(
        node='company_research',
        application_id='app-1',
        user_id='user-1',
        requested_artifact=artifact_type,
    )
