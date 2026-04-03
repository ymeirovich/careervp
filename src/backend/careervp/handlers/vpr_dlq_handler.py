"""DLQ handler for VPR jobs — marks orphaned jobs FAILED after SQS exhausts retries."""

from __future__ import annotations

import json
from typing import Any

from aws_lambda_powertools.utilities.typing import LambdaContext

from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.utils.observability import logger

_TERMINAL_STATUSES = {'COMPLETED', 'FAILED'}


def lambda_handler(event: dict[str, Any], context: LambdaContext) -> None:
    jobs_repo = JobsRepository()
    for record in event.get('Records', []):
        try:
            body = json.loads(record.get('body', '{}'))
            job_id = str(body.get('job_id', ''))
            if not job_id:
                logger.warning('DLQ record missing job_id', record=record)
                continue
            job = jobs_repo.get_job(job_id)
            if job is None:
                logger.warning('DLQ: job not found', job_id=job_id)
                continue
            current_status = str(job.get('status', '')).upper()
            if current_status in _TERMINAL_STATUSES:
                logger.info(
                    'DLQ: job already terminal, skipping',
                    job_id=job_id,
                    status=current_status,
                )
                continue
            jobs_repo.update_job_status(
                job_id,
                'FAILED',
                error='Job exhausted retry attempts — see DLQ for details',
            )
            logger.info('DLQ: marked job FAILED', job_id=job_id)
        except Exception as exc:
            logger.error('DLQ handler error', error=str(exc), record=record)
