"""FE-UI-038 ownership security tests for the artifact dependency resolver."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from careervp.logic.artifact_dependency_resolver import resolve_dependencies
from tests.unit.test_artifact_dependency_resolver import FakeRepos, _application, _artifact


def test_cross_user_vpr_treated_as_missing() -> None:
    repos = FakeRepos(
        artifacts={
            'vpr': _artifact('vpr', user_id='user-2'),
            'company_research': _artifact('company_research', user_id='user-1'),
        },
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

    assert 'vpr' not in resolution.resolved_upstream
    assert resolution.status == 'dependency_generating'
    assert resolution.generating == ['vpr']


def test_cross_user_cr_not_leaked_into_resolution() -> None:
    other_user_cr: dict[str, Any] = {
        **_artifact('company_research', user_id='user-2'),
        'private_research': 'confidential-user-2-company-context',
    }
    repos = FakeRepos(
        artifacts={
            'vpr': _artifact('vpr', user_id='user-1'),
            'company_research': other_user_cr,
        },
        application=_application(),
    )
    start_chain = MagicMock(return_value='arn:aws:states:us-east-1:123456789012:execution:chain:cr')

    resolution = resolve_dependencies(
        artifact_type='cover_letter',
        application_id='app-1',
        user_id='user-1',
        repos=repos,
        start_chain=start_chain,
        chain_enabled=True,
    )

    assert 'company_research' not in resolution.resolved_upstream
    assert resolution.status == 'dependency_generating'
    assert resolution.generating == ['company_research']
    assert 'confidential-user-2-company-context' not in repr(resolution)


def test_owned_artifacts_resolve_normally() -> None:
    repos = FakeRepos(
        artifacts={
            'vpr': _artifact('vpr', user_id='user-1'),
            'company_research': _artifact('company_research', user_id='user-1'),
        },
        application=_application(),
    )
    start_chain = MagicMock()

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
    start_chain.assert_not_called()
