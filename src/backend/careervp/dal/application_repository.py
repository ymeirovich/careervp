"""Application state repository for L3 workflow state recovery."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.models.exceptions import InvalidStateTransitionError

APPLICATION_STATES: tuple[str, ...] = (
    'created',
    'cv_selected',
    'gap_questions_pending',
    'gap_questions_ready',
    'gap_responses_submitted',
    'cr_pending',
    'cr_failed',
    'artifacts_generating',
    'artifacts_completed',
    'artifacts_failed',
)

# Company Research confidence gate (FE-UI-029): cr_pending / cr_failed are
# intermediate states reached only when the auto-chain feature flag is ON. When
# the flag is OFF, gap_responses_submitted advances directly to
# artifacts_generating and the additive states are never entered.
VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
    'created': ('cv_selected',),
    'cv_selected': ('gap_questions_pending',),
    'gap_questions_pending': ('gap_questions_ready',),
    'gap_questions_ready': ('gap_responses_submitted',),
    'gap_responses_submitted': ('cr_pending', 'artifacts_generating'),
    'cr_pending': ('artifacts_generating', 'cr_failed'),
    'cr_failed': ('cr_pending',),
    'artifacts_generating': ('artifacts_completed', 'artifacts_failed'),
    'artifacts_completed': (),
    'artifacts_failed': ('artifacts_generating',),
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

    def update_gap_responses(self, application_id: str, user_id: str, responses: list[dict[str, Any]]) -> None:
        """Write gap responses into the application record, creating it if it doesn't exist.

        Uses a DynamoDB upsert (update_item without a condition) so that the record is
        created on the fly when the application was never explicitly initialised.
        if_not_exists() ensures initialisation fields are only written on creation.
        """
        now = self._now_iso()
        self._table().update_item(
            Key={
                'userId': user_id,
                'applicationId': application_id,
            },
            UpdateExpression=(
                'SET gap_responses = :responses, '
                'updated_at = :now, '
                '#st = if_not_exists(#st, :submitted), '
                '#status = if_not_exists(#status, :submitted), '
                'application_id = if_not_exists(application_id, :app_id), '
                'user_id = if_not_exists(user_id, :user_id_val), '
                'job_id = if_not_exists(job_id, :app_id), '
                'entity_type = if_not_exists(entity_type, :entity_type), '
                'artifact_statuses = if_not_exists(artifact_statuses, :empty_map), '
                'trial_credit_consumed = if_not_exists(trial_credit_consumed, :false_val), '
                'created_at = if_not_exists(created_at, :now)'
            ),
            ExpressionAttributeNames={'#st': 'state', '#status': 'status'},
            ExpressionAttributeValues={
                ':responses': responses,
                ':now': now,
                ':submitted': 'gap_responses_submitted',
                ':app_id': application_id,
                ':user_id_val': user_id,
                ':entity_type': 'APPLICATION',
                ':empty_map': {},
                ':false_val': False,
            },
        )
        # For existing records in gap_questions_ready, advance state.
        # For new or already-submitted records this conditional update will fail
        # (expected_state mismatch) and is safely ignored.
        try:
            self.update_state(
                application_id=application_id,
                user_id=user_id,
                new_state='gap_responses_submitted',
                expected_state='gap_questions_ready',
            )
        except Exception:
            pass

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

    def update_artifact_with_id(
        self,
        application_id: str,
        user_id: str,
        artifact_type: str,
        status: str,
        artifact_id: str,
    ) -> None:
        """Write both artifact status and artifact_id into artifact_statuses.

        The hub reads ``artifact_statuses.<type>`` for status and
        ``artifact_statuses.<type>_artifact_id`` for the artifact ID.  This
        method writes both atomically so the hub reflects the completed
        artifact across page reloads.

        Uses a two-step approach to handle legacy application records that
        pre-date the artifact_statuses field: step 1 initialises the map if
        absent, step 2 sets the nested keys.  If the application record does
        not exist at all, step 1 raises ConditionalCheckFailedException and
        we return early (non-fatal).
        """
        key = {'userId': user_id, 'applicationId': application_id}
        item_exists_condition = 'attribute_exists(userId) AND attribute_exists(applicationId)'
        try:
            # Step 1: ensure artifact_statuses exists as a map.
            # DynamoDB raises ValidationException when setting a nested path
            # on a missing/null parent attribute, so we initialise it first.
            self._table().update_item(
                Key=key,
                UpdateExpression='SET artifact_statuses = if_not_exists(artifact_statuses, :empty)',
                ConditionExpression=item_exists_condition,
                ExpressionAttributeValues={':empty': {}},
            )
        except Exception:
            # Application record absent — create a minimal stub so artifact_id persists
            # across page reloads (jobs are created before applications in the v1 flow).
            try:
                now = self._now_iso()
                self._table().put_item(
                    Item={
                        'userId': user_id,
                        'applicationId': application_id,
                        'application_id': application_id,
                        'user_id': user_id,
                        'artifact_statuses': {},
                        'state': 'created',
                        'status': 'created',
                        'created_at': now,
                        'updated_at': now,
                        'entity_type': 'APPLICATION',
                    },
                    ConditionExpression='attribute_not_exists(userId)',
                )
            except Exception:
                return  # Concurrent write or permanent error — localStorage fallback handles it
        try:
            # Step 2: set the nested artifact keys now that the map is guaranteed to exist.
            self._table().update_item(
                Key=key,
                UpdateExpression='SET artifact_statuses.#at = :status, artifact_statuses.#at_id = :artifact_id, updated_at = :updated_at',
                ExpressionAttributeNames={
                    '#at': artifact_type,
                    '#at_id': f'{artifact_type}_artifact_id',
                },
                ExpressionAttributeValues={
                    ':status': status,
                    ':artifact_id': artifact_id,
                    ':updated_at': self._now_iso(),
                },
            )
        except Exception:
            pass  # Non-fatal — frontend localStorage fallback handles missing artifact_id

    def set_company_research_error(self, application_id: str, user_id: str, error: bool) -> None:
        """Persist the company_research_error flag on the application record.

        Set when Company Research hard-fails (3 retries exhausted) so the frontend
        can recover the error state across reloads. Also marks
        artifact_statuses.company_research as 'failed' (or 'pending' when cleared)
        so the recovery payload reflects the CR artifact state.

        Idempotent: uses a plain UpdateExpression with no conditional write, so a
        double-call is safe. The artifact_statuses map is initialised via
        if_not_exists to support legacy records that pre-date the field.
        """
        cr_status = 'failed' if error else 'pending'
        self._table().update_item(
            Key={
                'userId': user_id,
                'applicationId': application_id,
            },
            UpdateExpression=(
                'SET company_research_error = :error, artifact_statuses = if_not_exists(artifact_statuses, :empty_map), updated_at = :updated_at'
            ),
            ConditionExpression='attribute_exists(userId) AND attribute_exists(applicationId)',
            ExpressionAttributeValues={
                ':error': error,
                ':empty_map': {},
                ':updated_at': self._now_iso(),
            },
        )
        # Second step sets the nested artifact key once the map is guaranteed to exist
        # (DynamoDB rejects nested-path writes when the parent map is absent).
        self._table().update_item(
            Key={
                'userId': user_id,
                'applicationId': application_id,
            },
            UpdateExpression='SET artifact_statuses.#cr = :cr_status, updated_at = :updated_at',
            ConditionExpression='attribute_exists(userId) AND attribute_exists(applicationId)',
            ExpressionAttributeNames={'#cr': 'company_research'},
            ExpressionAttributeValues={
                ':cr_status': cr_status,
                ':updated_at': self._now_iso(),
            },
        )

    def _ensure_valid_transition(self, expected_state: str, new_state: str) -> None:
        if expected_state not in VALID_TRANSITIONS:
            raise InvalidStateTransitionError(f'Invalid state transition: unknown from_state={expected_state}')
        allowed_states = VALID_TRANSITIONS[expected_state]
        if new_state not in allowed_states:
            raise InvalidStateTransitionError(f'Invalid state transition: {expected_state} -> {new_state}')

    def _table(self) -> Any:
        return self._dal._get_db_handler(self._dal.table_name)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


__all__ = ['ApplicationRepository', 'APPLICATION_STATES', 'VALID_TRANSITIONS', 'InvalidStateTransitionError']
