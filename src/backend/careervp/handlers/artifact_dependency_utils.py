"""Handler-side adapters for artifact dependency resolution."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError as BotoClientError

from careervp.dal.application_repository import ApplicationRepository
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.logic.artifact_dependency_resolver import DependencyResolution, resolve_dependencies
from careervp.logic.company_research import load_confident_company_research_artifact


def artifact_chain_enabled() -> bool:
    return os.environ.get('ARTIFACT_CHAIN_ENABLED', '').strip().lower() in {'1', 'true', 'yes', 'on'}


class DynamoArtifactDependencyRepos:
    """Adapt existing DAL/repository methods to the resolver protocol."""

    def __init__(self, *, dal: DynamoDalHandler, application_repo: ApplicationRepository | None, user_id: str):
        self._dal = dal
        self._application_repo = application_repo
        self._user_id = user_id

    def get_application(self, application_id: str, user_id: str) -> dict[str, Any] | None:
        if self._application_repo is None:
            return None
        try:
            return self._application_repo.get(application_id=application_id, user_id=user_id)
        except Exception:
            return None

    def get_artifact(self, artifact_type: str, application_id: str) -> Any | None:
        if artifact_type == 'vpr':
            try:
                result = self._dal.get_vpr(application_id=application_id)
            except Exception:
                return None
            return result.data if getattr(result, 'success', False) else None

        if artifact_type == 'company_research':
            try:
                artifact = load_confident_company_research_artifact(application_id=application_id, user_id=self._user_id)
            except Exception:
                return None
            if artifact is None:
                return None
            return {
                'user_id': self._user_id,
                'application_id': application_id,
                'company_research_id': artifact.company_research_id,
                'created_at': artifact.company_research_at,
                'company_context': artifact.company_context.model_dump(mode='json'),
            }

        if artifact_type == 'gap_analysis':
            application = self.get_application(application_id=application_id, user_id=self._user_id)
            if isinstance(application, dict) and application.get('gap_responses'):
                return {'user_id': self._user_id, 'application_id': application_id, 'gap_responses': application['gap_responses']}
        return None


def build_application_repo() -> ApplicationRepository | None:
    table_name = os.environ.get('APPLICATIONS_TABLE_NAME') or os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME') or ''
    if not table_name:
        return None
    return ApplicationRepository(DynamoDalHandler(table_name))


def resolve_handler_dependencies(
    *,
    artifact_type: str,
    application_id: str,
    user_id: str,
    dal: DynamoDalHandler,
    application_repo: ApplicationRepository | None = None,
    start_chain: Callable[..., str | None] | None = None,
) -> DependencyResolution:
    app_repo = application_repo if application_repo is not None else build_application_repo()
    repos = DynamoArtifactDependencyRepos(dal=dal, application_repo=app_repo, user_id=user_id)
    starter = start_chain or build_start_chain(app_repo)
    return resolve_dependencies(
        artifact_type=artifact_type,
        application_id=application_id,
        user_id=user_id,
        repos=repos,
        start_chain=starter,
        chain_enabled=artifact_chain_enabled(),
    )


def _advance_to_cr_pending(application_repo: ApplicationRepository, application_id: str, user_id: str) -> None:
    """Try to set application state to cr_pending from either valid predecessor state.

    Tries gap_responses_submitted first (initial run), then cr_failed (retry).
    If both CCF the state is already cr_pending or further along — safe to proceed.
    """
    for expected in ('gap_responses_submitted', 'cr_failed'):
        try:
            application_repo.update_state(
                application_id=application_id,
                user_id=user_id,
                new_state='cr_pending',
                expected_state=expected,
            )
            return
        except BotoClientError as exc:
            if exc.response.get('Error', {}).get('Code') != 'ConditionalCheckFailedException':
                raise


def _reset_cr_artifact_status(application_repo: ApplicationRepository, application_id: str, user_id: str) -> None:
    """Reset company_research artifact status to 'pending' when starting a fresh CR chain.

    Clears any stale 'cancelled' status left by a prior cancelled run so the
    worker's fail_if_status='cancelled' guard (FE-UI-043) does not fire on a
    legitimate new execution.
    """
    try:
        application_repo.update_artifact_status(
            application_id=application_id,
            user_id=user_id,
            artifact_type='company_research',
            status='pending',
        )
    except Exception:
        pass  # non-fatal: worker proceeds; stale status handled by idempotency check


def build_start_chain(application_repo: ApplicationRepository | None) -> Callable[..., str | None]:
    def _start_chain(*, node: str, application_id: str, user_id: str, requested_artifact: str) -> str | None:
        chain_arn = os.environ.get('STEP_FUNCTIONS_CHAIN_ARN', '').strip()
        if not chain_arn:
            return None

        # Atomically claim the RUNNING slot before starting Step Functions so
        # two concurrent requests cannot both observe "no chain running" and
        # launch duplicate executions.
        if application_repo is not None:
            try:
                application_repo.claim_chain_execution(application_id=application_id, user_id=user_id)
                if node == 'company_research':
                    _advance_to_cr_pending(application_repo, application_id, user_id)
                    _reset_cr_artifact_status(application_repo, application_id, user_id)
            except BotoClientError as exc:
                if exc.response.get('Error', {}).get('Code') == 'ConditionalCheckFailedException':
                    return None  # Another request already holds the RUNNING lock
                raise

        execution = boto3.client('stepfunctions').start_execution(
            stateMachineArn=chain_arn,
            name=f'chain-{application_id}-{requested_artifact}-{uuid4().hex[:8]}',
            input=json.dumps(
                {
                    'user_id': user_id,
                    'job_id': application_id,
                    'application_id': application_id,
                    'start_at': node,
                    'requested_artifact': requested_artifact,
                }
            ),
        )
        execution_arn = str(execution.get('executionArn') or '').strip() or None
        if execution_arn and application_repo is not None:
            application_repo.set_chain_execution(
                application_id=application_id,
                user_id=user_id,
                execution_arn=execution_arn,
                status='RUNNING',
            )
        return execution_arn

    return _start_chain


def mark_requested_artifact_pending(application_id: str, user_id: str, artifact_type: str) -> None:
    app_repo = build_application_repo()
    if app_repo is None:
        return
    try:
        app_repo.update_artifact_status(
            application_id=application_id,
            user_id=user_id,
            artifact_type=artifact_type,
            status='pending',
        )
    except Exception:
        return


def dependency_response_body(resolution: DependencyResolution, requested_artifact: str) -> dict[str, Any]:
    return {
        'status': resolution.status,
        'generating': resolution.generating,
        'missing': resolution.missing,
        'chain_execution_arn': resolution.chain_execution_arn,
        'requested_artifact': requested_artifact,
    }
