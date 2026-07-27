"""Pure artifact dependency resolution for downstream generation handlers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from typing import Any, Literal, Protocol

ArtifactType = Literal['gap_analysis', 'company_research', 'vpr', 'cv_tailored', 'cover_letter', 'interview_prep']
ResolutionStatus = Literal['ready', 'dependency_generating', 'upstream_required']


class ArtifactDependencyRepos(Protocol):
    """Repository surface required by the pure resolver."""

    def get_application(self, application_id: str, user_id: str) -> dict[str, Any] | None:
        """Return application state for the authenticated user."""

    def get_artifact(self, artifact_type: str, application_id: str) -> Any | None:
        """Return the latest artifact candidate for an application."""


StartChain = Callable[..., str | None]


@dataclass(frozen=True)
class ArtifactRef:
    """Owned upstream artifact accepted by the resolver."""

    artifact_type: str
    artifact: Any
    artifact_id: str | None = None


@dataclass(frozen=True)
class DependencyResolution:
    """Result returned to handlers before generation starts."""

    status: ResolutionStatus
    resolved_upstream: dict[str, ArtifactRef] = field(default_factory=dict)
    generating: list[str] = field(default_factory=list)
    chain_execution_arn: str | None = None
    requested_artifact: str | None = None
    missing: list[str] = field(default_factory=list)
    http_status: int = int(HTTPStatus.OK)


DEPENDENCIES: dict[str, tuple[str, ...]] = {
    'company_research': ('gap_analysis',),
    'vpr': ('company_research',),
    'cv_tailored': ('vpr',),
    'cover_letter': ('vpr', 'company_research'),
    'interview_prep': ('vpr',),
}

GENERATION_ORDER: tuple[str, ...] = ('gap_analysis', 'company_research', 'vpr', 'cv_tailored', 'cover_letter', 'interview_prep')


def vpr_access_denied_envelope() -> dict[str, str]:
    """Shared public denial shape for downstream VPR ownership failures."""
    return {
        'error': 'VPR is not available for this application',
        'classification': 'access_denied',
        'error_code': 'forbidden',
        'field': 'vpr_id',
    }


def resolve_dependencies(
    *,
    artifact_type: str,
    application_id: str,
    user_id: str,
    repos: ArtifactDependencyRepos,
    start_chain: StartChain,
    chain_enabled: bool,
) -> DependencyResolution:
    """Resolve required upstream artifacts or trigger upstream generation.

    The resolver performs no direct I/O. Artifact/application reads and Step
    Functions execution are supplied by the caller so handlers can adapt their
    existing repositories without coupling this module to boto3 or DynamoDB.
    """
    required = DEPENDENCIES.get(artifact_type, ())
    if not required:
        return DependencyResolution(status='ready', requested_artifact=artifact_type)

    application = repos.get_application(application_id, user_id)
    resolved: dict[str, ArtifactRef] = {}
    missing: list[str] = []

    for upstream_type in required:
        candidate = repos.get_artifact(upstream_type, application_id)
        if candidate is None or not _is_owned_by(candidate, user_id) or _is_stale(repos, upstream_type, candidate, application):
            missing.append(upstream_type)
            continue
        resolved[upstream_type] = ArtifactRef(
            artifact_type=upstream_type,
            artifact=candidate,
            artifact_id=_artifact_id(candidate),
        )

    if not missing:
        return DependencyResolution(
            status='ready',
            resolved_upstream=resolved,
            requested_artifact=artifact_type,
        )

    generating = _ordered_artifacts(missing)
    if not chain_enabled:
        return DependencyResolution(
            status='upstream_required',
            resolved_upstream=resolved,
            generating=[],
            requested_artifact=artifact_type,
            missing=generating,
            http_status=int(HTTPStatus.CONFLICT),
        )

    if _chain_is_running(application):
        return DependencyResolution(
            status='dependency_generating',
            resolved_upstream=resolved,
            generating=generating,
            chain_execution_arn=None,
            requested_artifact=artifact_type,
            missing=generating,
            http_status=int(HTTPStatus.ACCEPTED),
        )

    start_node = generating[0]
    execution_arn = start_chain(node=start_node, application_id=application_id, user_id=user_id, requested_artifact=artifact_type)
    return DependencyResolution(
        status='dependency_generating',
        resolved_upstream=resolved,
        generating=generating,
        chain_execution_arn=execution_arn,
        requested_artifact=artifact_type,
        missing=generating,
        http_status=int(HTTPStatus.ACCEPTED),
    )


def _ordered_artifacts(artifact_types: list[str]) -> list[str]:
    order = {artifact_type: index for index, artifact_type in enumerate(GENERATION_ORDER)}
    return sorted(dict.fromkeys(artifact_types), key=lambda artifact_type: order.get(artifact_type, len(order)))


def _chain_is_running(application: dict[str, Any] | None) -> bool:
    if not isinstance(application, dict):
        return False
    return str(application.get('chain_execution_status') or '').strip().upper() == 'RUNNING'


def _is_owned_by(candidate: Any, user_id: str) -> bool:
    owner = _field(candidate, 'user_id') or _field(candidate, 'userId')
    return str(owner or '').strip() == user_id


def _is_stale(repos: ArtifactDependencyRepos, artifact_type: str, candidate: Any, application: dict[str, Any] | None) -> bool:
    stale_hook = getattr(repos, 'is_artifact_stale', None)
    if callable(stale_hook):
        return bool(stale_hook(artifact_type, candidate, application))

    if artifact_type != 'vpr' or not isinstance(application, dict):
        return False
    responses_submitted_at = _coerce_datetime(
        application.get('gap_responses_updated_at') or application.get('responses_submitted_at') or application.get('gap_responses_submitted_at')
    )
    created_at = _coerce_datetime(_field(candidate, 'created_at'))
    return responses_submitted_at is not None and created_at is not None and responses_submitted_at > created_at


def _artifact_id(candidate: Any) -> str | None:
    return resolve_artifact_id(candidate)


def resolve_artifact_id(candidate: Any) -> str | None:
    """Return the sole canonical opaque artifact_id; aliases are not ids."""
    value = _field(candidate, 'artifact_id')
    if value:
        return str(value)
    return None


def _field(candidate: Any, field_name: str) -> Any:
    if isinstance(candidate, dict):
        return candidate.get(field_name)
    return getattr(candidate, field_name, None)


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None
