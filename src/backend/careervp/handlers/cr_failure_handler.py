"""
Company Research Failure Handler.

Thin Lambda invoked by the artifact-chain Step Functions state machine when the
Company Research task hard-fails or times out (HandleCRFailure state). It marks
the application's company_research_error flag and transitions the application
state to ``cr_failed``.

Idempotent and defensive: it never raises, so a failure here cannot cascade into
a Step Functions retry storm.

Per docs/upgrade/specs/FE-UI-031-step-functions-chain.yaml
"""

from __future__ import annotations

import os
from typing import Any

from aws_lambda_powertools.utilities.typing import LambdaContext

from careervp.dal.application_repository import (
    ApplicationRepository,
    InvalidStateTransitionError,
)
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.utils.observability import logger, metrics, tracer


def _get_app_repo() -> ApplicationRepository:
    table_name = os.environ.get('APPLICATIONS_TABLE_NAME', '')
    return ApplicationRepository(DynamoDalHandler(table_name))


def _extract_ids(event: dict[str, Any]) -> tuple[str, str]:
    """Pull user_id/job_id from the raw Step Functions execution input ($)."""
    user_id = str(event.get('user_id') or '')
    job_id = str(event.get('job_id') or event.get('application_id') or '')
    return user_id, job_id


@logger.inject_lambda_context(log_event=False)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    user_id, job_id = _extract_ids(event)
    if not user_id or not job_id:
        logger.warning('CR failure handler missing user_id/job_id', event_keys=list(event.keys()))
        return {'status': 'skipped', 'reason': 'missing identifiers'}

    app_repo = _get_app_repo()
    try:
        app_repo.set_company_research_error(application_id=job_id, user_id=user_id, error=True)
    except Exception as exc:  # noqa: BLE001 - defensive: never raise from a failure handler
        logger.error('Failed to set company_research_error', job_id=job_id, error=str(exc))

    try:
        app_repo.update_state(
            application_id=job_id,
            user_id=user_id,
            new_state='cr_failed',
            expected_state='cr_pending',
        )
    except InvalidStateTransitionError as exc:
        # The application may already be past cr_pending; record and move on.
        logger.warning('CR failure state transition skipped', job_id=job_id, error=str(exc))
    except Exception as exc:  # noqa: BLE001 - defensive: never raise from a failure handler
        logger.error('Failed to transition application to cr_failed', job_id=job_id, error=str(exc))

    logger.info('Company research marked failed', user_id=user_id, job_id=job_id)
    return {'status': 'cr_failed', 'job_id': job_id}
