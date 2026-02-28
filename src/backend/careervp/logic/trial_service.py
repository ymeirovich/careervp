"""Trial enforcement service for 14-day / 3-application limits."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from botocore.exceptions import ClientError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler

TRIAL_LIMIT_DAYS = 14
TRIAL_LIMIT_APPLICATIONS = 3


class TrialExpiredException(Exception):
    """Raised when a trial has passed the allowed duration."""

    def __init__(self, user_id: str, days_elapsed: int):
        super().__init__(f'trial_expired: user={user_id} days_elapsed={days_elapsed}')
        self.user_id = user_id
        self.days_elapsed = days_elapsed


class TrialExhaustedException(Exception):
    """Raised when a trial has no remaining application credits."""

    def __init__(self, user_id: str, application_count: int):
        super().__init__(f'trial_exhausted: user={user_id} application_count={application_count}')
        self.user_id = user_id
        self.application_count = application_count


class TrialService:
    """Manages trial status, usage, and atomic credit consumption."""

    def __init__(self, dal: DynamoDalHandler, now_fn: Callable[[], datetime] | None = None):
        self._dal = dal
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def check_trial_status(self, user_id: str) -> dict[str, bool | int]:
        record = self._load_trial_record(user_id=user_id)
        now = self._now_fn()
        created_at = self._parse_created_at(record.get('created_at'), default=now)
        days_elapsed = (now - created_at).days
        application_count = self._coerce_non_negative_int(record.get('application_count'))
        trial_active = bool(record.get('trial_active', True))

        if not trial_active or days_elapsed >= TRIAL_LIMIT_DAYS:
            raise TrialExpiredException(user_id=user_id, days_elapsed=days_elapsed)
        if application_count >= TRIAL_LIMIT_APPLICATIONS:
            raise TrialExhaustedException(user_id=user_id, application_count=application_count)

        return {
            'is_active': True,
            'days_remaining': max(0, TRIAL_LIMIT_DAYS - days_elapsed),
            'applications_used': application_count,
            'applications_remaining': max(0, TRIAL_LIMIT_APPLICATIONS - application_count),
        }

    def consume_credit(self, user_id: str) -> None:
        try:
            self._table().update_item(
                Key={'pk': self._pk(user_id), 'sk': 'TRIAL'},
                UpdateExpression=('SET application_count = if_not_exists(application_count, :zero) + :inc, updated_at = :updated_at'),
                ConditionExpression=('attribute_exists(pk) AND attribute_exists(sk) AND trial_active = :trial_active AND application_count < :max'),
                ExpressionAttributeValues={
                    ':zero': 0,
                    ':inc': 1,
                    ':max': TRIAL_LIMIT_APPLICATIONS,
                    ':trial_active': True,
                    ':updated_at': self._now_fn().isoformat(),
                },
            )
        except ClientError as exc:
            error_code = exc.response.get('Error', {}).get('Code')
            if error_code == 'ConditionalCheckFailedException':
                raise TrialExhaustedException(user_id=user_id, application_count=TRIAL_LIMIT_APPLICATIONS) from exc
            raise

    def get_usage(self, user_id: str) -> dict[str, Any]:
        record = self._load_trial_record(user_id=user_id)
        now = self._now_fn()
        created_at = self._parse_created_at(record.get('created_at'), default=now)
        days_elapsed = max(0, (now - created_at).days)
        application_count = self._coerce_non_negative_int(record.get('application_count'))
        days_remaining = max(0, TRIAL_LIMIT_DAYS - days_elapsed)
        credits_remaining = max(0, TRIAL_LIMIT_APPLICATIONS - application_count)
        trial_active = bool(record.get('trial_active', True)) and days_remaining > 0
        trial_ends_at = created_at + timedelta(days=TRIAL_LIMIT_DAYS)
        return {
            'trial_active': trial_active,
            'days_elapsed': days_elapsed,
            'days_remaining': days_remaining,
            'applications_used': application_count,
            'credits_remaining': credits_remaining,
            'trial_ends_at': trial_ends_at.isoformat(),
        }

    def _load_trial_record(self, user_id: str) -> dict[str, Any]:
        response = self._table().get_item(Key={'pk': self._pk(user_id), 'sk': 'TRIAL'})
        item = response.get('Item')
        if isinstance(item, dict):
            return item
        now = self._now_fn().isoformat()
        return {
            'pk': self._pk(user_id),
            'sk': 'TRIAL',
            'created_at': now,
            'application_count': 0,
            'trial_active': True,
        }

    def _table(self) -> Any:
        return self._dal._get_db_handler(self._dal.table_name)

    @staticmethod
    def _pk(user_id: str) -> str:
        return f'USER#{user_id}'

    @staticmethod
    def _parse_created_at(value: Any, default: datetime) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc)
        if isinstance(value, str) and value.strip():
            normalized = value.strip().replace('Z', '+00:00')
            try:
                parsed = datetime.fromisoformat(normalized)
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except ValueError:
                return default
        return default

    @staticmethod
    def _coerce_non_negative_int(value: Any) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, parsed)


__all__ = ['TrialService', 'TrialExpiredException', 'TrialExhaustedException']
