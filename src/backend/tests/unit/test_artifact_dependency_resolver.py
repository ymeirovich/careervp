"""FE-UI-038 unit tests for artifact dependency resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

from careervp.logic.artifact_dependency_resolver import resolve_dependencies


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


def _application(**overrides: Any) -> dict[str, Any]:
    return {
        'application_id': 'app-1',
        'user_id': 'user-1',
        'artifact_statuses': {},
        **overrides,
    }


def test_all_upstream_present_returns_ready() -> None:
    repos = FakeRepos(
        artifacts={
            'vpr': _artifact('vpr'),
            'company_research': _artifact('company_research'),
        },
        application=_application(),
    )
    start_chain = MagicMock(return_value='arn:aws:states:us-east-1:123456789012:execution:chain:ready')

    resolution = resolve_dependencies(
        artifact_type='cover_letter',
        application_id='app-1',
        user_id='user-1',
        repos=repos,
        start_chain=start_chain,
        chain_enabled=True,
    )

    assert resolution.status == 'ready'
    assert set(resolution.resolved_upstream) == {'vpr', 'company_research'}
    assert resolution.generating == []
    assert resolution.chain_execution_arn is None
    start_chain.assert_not_called()


def test_missing_vpr_returns_dependency_generating_and_starts_chain() -> None:
    repos = FakeRepos(
        artifacts={'company_research': _artifact('company_research')},
        application=_application(),
    )
    start_chain = MagicMock(return_value='arn:aws:states:us-east-1:123456789012:execution:chain:vpr')

    resolution = resolve_dependencies(
        artifact_type='cover_letter',
        application_id='app-1',
        user_id='user-1',
        repos=repos,
        start_chain=start_chain,
        chain_enabled=True,
    )

    assert resolution.status == 'dependency_generating'
    assert 'vpr' in resolution.generating
    assert resolution.chain_execution_arn == 'arn:aws:states:us-east-1:123456789012:execution:chain:vpr'
    start_chain.assert_called_once_with(node='vpr', application_id='app-1', user_id='user-1', requested_artifact='cover_letter')


def test_missing_cr_and_vpr_starts_chain_at_cr_node() -> None:
    repos = FakeRepos(application=_application())
    start_chain = MagicMock(return_value='arn:aws:states:us-east-1:123456789012:execution:chain:cr')

    resolution = resolve_dependencies(
        artifact_type='vpr',
        application_id='app-1',
        user_id='user-1',
        repos=repos,
        start_chain=start_chain,
        chain_enabled=True,
    )

    assert resolution.status == 'dependency_generating'
    assert resolution.generating == ['company_research']
    start_chain.assert_called_once_with(
        node='company_research',
        application_id='app-1',
        user_id='user-1',
        requested_artifact='vpr',
    )


def test_stale_upstream_treated_as_needing_regeneration() -> None:
    repos = FakeRepos(
        artifacts={
            'vpr': _artifact('vpr', created_at='2026-06-14T09:00:00+00:00'),
            'company_research': _artifact('company_research'),
        },
        application=_application(gap_responses_updated_at='2026-06-14T10:00:00+00:00'),
        stale_artifacts={'vpr'},
    )
    start_chain = MagicMock(return_value='arn:aws:states:us-east-1:123456789012:execution:chain:stale-vpr')

    resolution = resolve_dependencies(
        artifact_type='cover_letter',
        application_id='app-1',
        user_id='user-1',
        repos=repos,
        start_chain=start_chain,
        chain_enabled=True,
    )

    assert resolution.status == 'dependency_generating'
    assert resolution.generating == ['vpr']
    assert 'vpr' not in resolution.resolved_upstream


def test_chain_already_running_does_not_start_duplicate() -> None:
    repos = FakeRepos(
        artifacts={'company_research': _artifact('company_research')},
        application=_application(
            chain_execution_status='RUNNING',
            chain_execution_arn='arn:aws:states:us-east-1:123456789012:execution:chain:running',
        ),
    )
    start_chain = MagicMock(return_value='arn:aws:states:us-east-1:123456789012:execution:chain:duplicate')

    resolution = resolve_dependencies(
        artifact_type='cover_letter',
        application_id='app-1',
        user_id='user-1',
        repos=repos,
        start_chain=start_chain,
        chain_enabled=True,
    )

    assert resolution.status == 'dependency_generating'
    assert resolution.chain_execution_arn is None
    assert 'vpr' in resolution.generating
    start_chain.assert_not_called()


def test_flag_off_missing_upstream_returns_upstream_required() -> None:
    repos = FakeRepos(
        artifacts={'company_research': _artifact('company_research')},
        application=_application(),
    )
    start_chain = MagicMock(return_value='arn:aws:states:us-east-1:123456789012:execution:chain:off')

    resolution = resolve_dependencies(
        artifact_type='cover_letter',
        application_id='app-1',
        user_id='user-1',
        repos=repos,
        start_chain=start_chain,
        chain_enabled=False,
    )

    assert resolution.status == 'upstream_required'
    assert resolution.http_status == 409
    assert resolution.missing == ['vpr']
    assert resolution.generating == []
    start_chain.assert_not_called()
