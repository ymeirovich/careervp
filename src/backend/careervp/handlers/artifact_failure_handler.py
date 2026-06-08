"""
Artifact Failure Handler.

Thin Lambda invoked by the artifact-chain Step Functions state machine when the
VPR or CV Tailoring task fails (HandleVPRFailure / HandleCVFailure states). It
marks the corresponding artifact status as ``failed`` on the application record.

Invoked with payload ``{"artifact_type": "vpr"|"cv_tailored", "context": <input>}``
where ``context`` is the chain execution input ({user_id, job_id, ...}).

Idempotent and defensive: it never raises.

Per docs/upgrade/specs/FE-UI-031-step-functions-chain.yaml
"""

from __future__ import annotations

import os
from typing import Any

from aws_lambda_powertools.utilities.typing import LambdaContext

from careervp.dal.application_repository import ApplicationRepository
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.utils.observability import logger, metrics, tracer


def _get_app_repo() -> ApplicationRepository:
    table_name = os.environ.get('APPLICATIONS_TABLE_NAME', '')
    return ApplicationRepository(DynamoDalHandler(table_name))


def _extract(event: dict[str, Any]) -> tuple[str, str, str]:
    """Return (artifact_type, user_id, job_id) from the invoke payload."""
    artifact_type = str(event.get('artifact_type') or 'unknown')
    ctx = event.get('context')
    source = ctx if isinstance(ctx, dict) else event
    user_id = str(source.get('user_id') or '')
    job_id = str(source.get('job_id') or source.get('application_id') or '')
    return artifact_type, user_id, job_id


@logger.inject_lambda_context(log_event=False)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    artifact_type, user_id, job_id = _extract(event)
    if not user_id or not job_id:
        logger.warning('Artifact failure handler missing user_id/job_id', event_keys=list(event.keys()))
        return {'status': 'skipped', 'reason': 'missing identifiers'}

    app_repo = _get_app_repo()
    try:
        app_repo.update_artifact_status(
            application_id=job_id,
            user_id=user_id,
            artifact_type=artifact_type,
            status='failed',
        )
    except Exception as exc:  # noqa: BLE001 - defensive: never raise from a failure handler
        logger.error('Failed to mark artifact failed', job_id=job_id, artifact_type=artifact_type, error=str(exc))

    logger.info('Artifact marked failed', user_id=user_id, job_id=job_id, artifact_type=artifact_type)
    return {'status': 'artifact_failed', 'job_id': job_id, 'artifact_type': artifact_type}
