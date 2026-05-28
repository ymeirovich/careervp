"""
L5 trial enforcement integration tests for invariant I5.

Spec: docs/best_practices/yaml/trial_enforcement_spec.yaml
Payload: docs/refactor/payloads/beta_l5_trial_enforcement_test.json
Evidence target: docs/beta/evidence/I5_trial/trial-enforcement-report.json
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from careervp.logic.trial_service import TrialExhaustedException, TrialExpiredException, TrialService

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
os.environ.setdefault('ENVIRONMENT', 'test')

USER_ID = 'user-trial-integration-123'


class _InMemoryTrialTable:
    """Thread-safe trial table stub used to validate atomic counter semantics."""

    def __init__(
        self,
        *,
        user_id: str = USER_ID,
        days_elapsed: int = 0,
        application_count: int = 0,
        trial_active: bool = True,
    ) -> None:
        created_at = datetime.now(timezone.utc) - timedelta(days=days_elapsed)
        self.item: dict[str, object] = {
            'pk': f'USER#{user_id}',
            'sk': 'TRIAL',
            'user_id': user_id,
            'created_at': created_at.isoformat(),
            'application_count': application_count,
            'trial_active': trial_active,
        }
        self._lock = threading.Lock()

    def get_item(self, Key: dict[str, str]) -> dict[str, dict[str, object]]:  # noqa: N803 - AWS naming
        _ = Key
        with self._lock:
            return {'Item': dict(self.item)}

    def update_item(self, **kwargs: object) -> dict[str, object]:
        _ = kwargs
        with self._lock:
            application_value = self.item.get('application_count', 0)
            application_count = int(application_value) if isinstance(application_value, (int, str)) else 0
            trial_active = bool(self.item.get('trial_active', True))
            if not trial_active or application_count >= 3:
                raise ClientError(
                    {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'limit reached'}},
                    'UpdateItem',
                )
            self.item['application_count'] = application_count + 1
            return {'Attributes': {'application_count': self.item['application_count']}}


def _build_service(table: object) -> TrialService:
    dal = MagicMock()
    dal.table_name = 'users-table'
    dal._get_db_handler.return_value = table
    return TrialService(dal=dal, now_fn=lambda: datetime.now(timezone.utc))


def _gap_event(
    *,
    user_id: str = USER_ID,
    job_id: str = 'job-123',
    cv_id: str = 'cv-123',
) -> dict[str, object]:
    return {
        'httpMethod': 'POST',
        'path': f'/jobs/{job_id}/gap-questions',
        'pathParameters': {'jobId': job_id},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'cv_id': cv_id, 'job_id': job_id, 'application_id': job_id}),
    }


def _usage_event(user_id: str | None = USER_ID) -> dict[str, object]:
    request_context: dict[str, object] = {}
    if user_id is not None:
        request_context = {'authorizer': {'claims': {'sub': user_id}}}
    return {
        'httpMethod': 'GET',
        'path': '/users/me/usage',
        'resource': '/users/me/usage',
        'requestContext': request_context,
        'headers': {'Content-Type': 'application/json'},
        'body': None,
    }


@pytest.mark.integration
class TestTrialExpiryEnforcement:
    """14-day trial window is enforced before protected operations."""

    def test_day_1_trial_active(self) -> None:
        service = _build_service(_InMemoryTrialTable(days_elapsed=1))
        status = service.check_trial_status(USER_ID)
        assert status['is_active'] is True
        assert status['days_remaining'] == 13

    def test_day_13_trial_active(self) -> None:
        service = _build_service(_InMemoryTrialTable(days_elapsed=13, application_count=2))
        status = service.check_trial_status(USER_ID)
        assert status['days_remaining'] == 1
        assert status['applications_remaining'] == 1

    def test_day_14_trial_expired(self) -> None:
        service = _build_service(_InMemoryTrialTable(days_elapsed=14, application_count=0))
        with pytest.raises(TrialExpiredException):
            service.check_trial_status(USER_ID)

    def test_day_15_trial_expired(self) -> None:
        service = _build_service(_InMemoryTrialTable(days_elapsed=15, application_count=0))
        with pytest.raises(TrialExpiredException):
            service.check_trial_status(USER_ID)

    def test_expired_trial_returns_403(self) -> None:
        from careervp.handlers import gap_handler

        mock_llm = AsyncMock(return_value=SimpleNamespace(success=True, data=['Q1'], error=None, code=None))
        with (
            patch.object(gap_handler, '_get_trial_service', return_value=_build_service(_InMemoryTrialTable(days_elapsed=15))),
            patch.object(gap_handler, '_get_application_repository', return_value=MagicMock()),
            patch.object(gap_handler, 'generate_gap_questions', mock_llm),
        ):
            response = gap_handler.lambda_handler(_gap_event(), MagicMock())

        payload = json.loads(response['body'])
        assert response['statusCode'] == 403
        assert payload['code'] == 'trial_expired'

    def test_expired_trial_blocks_llm_call(self) -> None:
        from careervp.handlers import gap_handler

        mock_llm = AsyncMock(return_value=SimpleNamespace(success=True, data=['Q1'], error=None, code=None))
        with (
            patch.object(gap_handler, '_get_trial_service', return_value=_build_service(_InMemoryTrialTable(days_elapsed=15))),
            patch.object(gap_handler, '_get_application_repository', return_value=MagicMock()),
            patch.object(gap_handler, 'generate_gap_questions', mock_llm),
        ):
            _ = gap_handler.lambda_handler(_gap_event(), MagicMock())

        mock_llm.assert_not_awaited()


@pytest.mark.integration
class TestApplicationCounterEnforcement:
    """3-application cap is enforced and blocks exhausted users."""

    def test_first_application_succeeds(self) -> None:
        table = _InMemoryTrialTable(application_count=0)
        service = _build_service(table)
        service.consume_credit(USER_ID)
        assert table.item['application_count'] == 1

    def test_third_application_succeeds(self) -> None:
        table = _InMemoryTrialTable(application_count=2)
        service = _build_service(table)
        service.consume_credit(USER_ID)
        assert table.item['application_count'] == 3

    def test_fourth_application_rejected(self) -> None:
        from careervp.handlers import gap_handler

        mock_llm = AsyncMock(return_value=SimpleNamespace(success=True, data=['Q1'], error=None, code=None))
        with (
            patch.object(gap_handler, '_get_trial_service', return_value=_build_service(_InMemoryTrialTable(application_count=3))),
            patch.object(gap_handler, '_get_application_repository', return_value=MagicMock()),
            patch.object(gap_handler, 'generate_gap_questions', mock_llm),
        ):
            response = gap_handler.lambda_handler(_gap_event(), MagicMock())

        payload = json.loads(response['body'])
        assert response['statusCode'] == 403
        assert payload['code'] == 'trial_exhausted'
        mock_llm.assert_not_awaited()

    def test_exhausted_trial_returns_403(self) -> None:
        from careervp.handlers import gap_handler

        with (
            patch.object(gap_handler, '_get_trial_service', return_value=_build_service(_InMemoryTrialTable(application_count=3))),
            patch.object(gap_handler, '_get_application_repository', return_value=MagicMock()),
        ):
            response = gap_handler.lambda_handler(_gap_event(), MagicMock())

        assert response['statusCode'] == 403


@pytest.mark.integration
class TestAtomicCounterIncrement:
    """Counter increment remains atomic at the limit boundary."""

    def test_concurrent_requests_only_one_succeeds(self) -> None:
        service = _build_service(_InMemoryTrialTable(application_count=2))

        def attempt() -> str:
            try:
                service.consume_credit(USER_ID)
                return 'success'
            except TrialExhaustedException:
                return 'trial_exhausted'

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            outcomes = list(executor.map(lambda _: attempt(), range(5)))

        assert outcomes.count('success') == 1
        assert outcomes.count('trial_exhausted') == 4

    def test_counter_uses_condition_expression(self) -> None:
        table = MagicMock()
        table.get_item.return_value = {'Item': _InMemoryTrialTable().item}
        table.update_item.return_value = {}
        service = _build_service(table)
        service.consume_credit(USER_ID)

        kwargs = table.update_item.call_args.kwargs
        assert 'application_count < :max' in kwargs['ConditionExpression']
        assert 'trial_active = :trial_active' in kwargs['ConditionExpression']

    def test_condition_check_failed_returns_trial_exhausted(self) -> None:
        conditional_error = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'limit reached'}},
            'UpdateItem',
        )
        table = MagicMock()
        table.get_item.return_value = {'Item': _InMemoryTrialTable().item}
        table.update_item.side_effect = conditional_error
        service = _build_service(table)

        with pytest.raises(TrialExhaustedException):
            service.consume_credit(USER_ID)

    def test_counter_incremented_atomically(self) -> None:
        table = _InMemoryTrialTable(application_count=1)
        service = _build_service(table)
        service.consume_credit(USER_ID)
        service.consume_credit(USER_ID)
        assert table.item['application_count'] == 3


@pytest.mark.integration
class TestUsageEndpoint:
    """Usage endpoint reflects TrialService usage values and auth requirements."""

    def test_usage_endpoint_returns_trial_status(self) -> None:
        from careervp.handlers import user_handler

        mock_trial_service = MagicMock()
        mock_trial_service.get_usage.return_value = {
            'trial_active': True,
            'days_elapsed': 5,
            'days_remaining': 9,
            'applications_used': 1,
            'credits_remaining': 2,
            'trial_ends_at': '2026-03-10T00:00:00+00:00',
        }
        with patch.object(user_handler, '_get_trial_service', return_value=mock_trial_service):
            response = user_handler.lambda_handler(_usage_event(), MagicMock())

        payload = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert payload['trial']['days_remaining'] == 9
        assert payload['applications']['used'] == 1

    def test_usage_endpoint_requires_auth(self) -> None:
        from careervp.handlers import user_handler

        response = user_handler.lambda_handler(_usage_event(user_id=None), MagicMock())
        assert response['statusCode'] == 401

    def test_usage_endpoint_trial_active_false_when_expired(self) -> None:
        from careervp.handlers import user_handler

        mock_trial_service = MagicMock()
        mock_trial_service.get_usage.return_value = {
            'trial_active': False,
            'days_elapsed': 15,
            'days_remaining': 0,
            'applications_used': 3,
            'credits_remaining': 0,
            'trial_ends_at': '2026-03-10T00:00:00+00:00',
        }
        with patch.object(user_handler, '_get_trial_service', return_value=mock_trial_service):
            response = user_handler.lambda_handler(_usage_event(), MagicMock())

        payload = json.loads(response['body'])
        assert payload['trial']['active'] is False
        assert payload['applications']['remaining'] == 0


@pytest.mark.integration
class TestTrialIntegration:
    """I5 sign-off scenarios used for evidence generation."""

    def test_exhaust_3_applications_block_4th(self) -> None:
        service = _build_service(_InMemoryTrialTable(application_count=0))
        service.consume_credit(USER_ID)
        service.consume_credit(USER_ID)
        service.consume_credit(USER_ID)
        with pytest.raises(TrialExhaustedException):
            service.consume_credit(USER_ID)

    def test_day_15_user_blocked_on_any_route(self) -> None:
        from careervp.handlers import gap_handler

        with (
            patch.object(gap_handler, '_get_trial_service', return_value=_build_service(_InMemoryTrialTable(days_elapsed=15))),
            patch.object(gap_handler, '_get_application_repository', return_value=MagicMock()),
        ):
            response = gap_handler.lambda_handler(_gap_event(), MagicMock())

        payload = json.loads(response['body'])
        assert response['statusCode'] == 403
        assert payload['code'] == 'trial_expired'

    def test_concurrent_boundary_no_overcount(self) -> None:
        service = _build_service(_InMemoryTrialTable(application_count=2))

        def attempt() -> str:
            try:
                service.consume_credit(USER_ID)
                return 'success'
            except TrialExhaustedException:
                return 'trial_exhausted'

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            outcomes = list(executor.map(lambda _: attempt(), range(5)))

        assert outcomes.count('success') == 1
        assert outcomes.count('trial_exhausted') == 4
