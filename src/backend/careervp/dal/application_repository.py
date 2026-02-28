"""Application state repository for L3 workflow state recovery."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from careervp.dal.dynamo_dal_handler import DynamoDalHandler

APPLICATION_STATES: tuple[str, ...] = (
    'created',
    'cv_selected',
    'gap_questions_pending',
    'gap_questions_ready',
    'gap_responses_submitted',
    'artifacts_generating',
    'artifacts_completed',
)

VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
    'created': ('cv_selected',),
    'cv_selected': ('gap_questions_pending',),
    'gap_questions_pending': ('gap_questions_ready',),
    'gap_questions_ready': ('gap_responses_submitted',),
    'gap_responses_submitted': ('artifacts_generating',),
    'artifacts_generating': ('artifacts_completed',),
    'artifacts_completed': (),
}


class ApplicationRepository:
    """Persist and mutate application lifecycle records in DynamoDB."""

    def __init__(self, dal: DynamoDalHandler):
        self._dal = dal

    def create(self, user_id: str, job_id: str) -> str:
        application_id = str(uuid4())
        now = self._now_iso()
        item: dict[str, Any] = {
            'userId': user_id,
            'applicationId': application_id,
            'application_id': application_id,
            'user_id': user_id,
            'job_id': job_id,
            'state': 'created',
            'status': 'created',
            'created_at': now,
            'updated_at': now,
            'trial_credit_consumed': False,
            'artifact_statuses': {},
            'entity_type': 'APPLICATION',
        }
        self._table().put_item(Item=item)
        return application_id

    def get(self, application_id: str, user_id: str) -> dict[str, Any] | None:
        response = self._table().get_item(
            Key={
                'userId': user_id,
                'applicationId': application_id,
            }
        )
        item = response.get('Item')
        return item if isinstance(item, dict) else None

    def update_state(self, application_id: str, user_id: str, new_state: str, expected_state: str) -> None:
        self._ensure_valid_transition(expected_state=expected_state, new_state=new_state)
        self._table().update_item(
            Key={
                'userId': user_id,
                'applicationId': application_id,
            },
            UpdateExpression='SET #state = :new_state, #status = :new_state, updated_at = :updated_at',
            ConditionExpression='attribute_exists(userId) AND attribute_exists(applicationId) AND #state = :expected_state',
            ExpressionAttributeNames={'#state': 'state', '#status': 'status'},
            ExpressionAttributeValues={
                ':new_state': new_state,
                ':expected_state': expected_state,
                ':updated_at': self._now_iso(),
            },
        )

    def update_cv(self, application_id: str, user_id: str, cv_id: str) -> None:
        self._table().update_item(
            Key={
                'userId': user_id,
                'applicationId': application_id,
            },
            UpdateExpression='SET cv_id = :cv_id, updated_at = :updated_at',
            ConditionExpression='attribute_exists(userId) AND attribute_exists(applicationId)',
            ExpressionAttributeValues={
                ':cv_id': cv_id,
                ':updated_at': self._now_iso(),
            },
        )

    def update_artifact_status(self, application_id: str, user_id: str, artifact_type: str, status: str) -> None:
        if not artifact_type:
            raise ValueError('artifact_type is required')
        self._table().update_item(
            Key={
                'userId': user_id,
                'applicationId': application_id,
            },
            UpdateExpression='SET artifact_statuses.#artifact_type = :status, updated_at = :updated_at',
            ConditionExpression='attribute_exists(userId) AND attribute_exists(applicationId)',
            ExpressionAttributeNames={'#artifact_type': artifact_type},
            ExpressionAttributeValues={
                ':status': status,
                ':updated_at': self._now_iso(),
            },
        )

    def _ensure_valid_transition(self, expected_state: str, new_state: str) -> None:
        if expected_state not in VALID_TRANSITIONS:
            raise ValueError(f'Invalid state transition: unknown from_state={expected_state}')
        allowed_states = VALID_TRANSITIONS[expected_state]
        if new_state not in allowed_states:
            raise ValueError(f'Invalid state transition: {expected_state} -> {new_state}')

    def _table(self) -> Any:
        return self._dal._get_db_handler(self._dal.table_name)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


__all__ = ['ApplicationRepository', 'APPLICATION_STATES', 'VALID_TRANSITIONS']
