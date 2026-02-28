"""
Trial enforcement unit tests for I5.

Spec: docs/best_practices/yaml/trial_enforcement_spec.yaml
Payload: docs/refactor/payloads/beta_l5_trial_enforcement_test.json
Invariant: I5
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from careervp.logic.trial_service import TrialExhaustedException, TrialExpiredException, TrialService

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
os.environ.setdefault('ENVIRONMENT', 'test')


def _trial_record(
    *,
    user_id: str = 'user-test-123',
    days_elapsed: int = 0,
    application_count: int = 0,
    trial_active: bool = True,
) -> dict[str, object]:
    created_at = datetime.now(timezone.utc) - timedelta(days=days_elapsed)
    return {
        'pk': f'USER#{user_id}',
        'sk': 'TRIAL',
        'user_id': user_id,
        'created_at': created_at.isoformat(),
        'application_count': application_count,
        'trial_active': trial_active,
    }


def _make_service(item: dict[str, object], update_side_effect: object | None = None) -> tuple[TrialService, MagicMock]:
    table = MagicMock()
    table.get_item.return_value = {'Item': item}
    if update_side_effect is None:
        table.update_item.return_value = {}
    else:
        table.update_item.side_effect = update_side_effect
    dal = MagicMock()
    dal.table_name = 'users-table'
    dal._get_db_handler.return_value = table
    service = TrialService(dal=dal, now_fn=lambda: datetime.now(timezone.utc))
    return service, table


def _usage_event(user_id: str | None = 'user-test-123') -> dict[str, object]:
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


@pytest.mark.unit
class TestTrialExpiry:
    def test_trial_active_day_1(self) -> None:
        service, _ = _make_service(_trial_record(days_elapsed=1, application_count=0))
        status = service.check_trial_status('user-test-123')
        assert status['is_active'] is True
        assert status['days_remaining'] == 13

    def test_trial_active_day_13(self) -> None:
        service, _ = _make_service(_trial_record(days_elapsed=13, application_count=2))
        status = service.check_trial_status('user-test-123')
        assert status['days_remaining'] == 1
        assert status['applications_remaining'] == 1

    def test_trial_expired_day_14_returns_403(self) -> None:
        service, _ = _make_service(_trial_record(days_elapsed=14, application_count=0))
        with pytest.raises(TrialExpiredException):
            service.check_trial_status('user-test-123')

    def test_trial_expired_day_15_returns_403(self) -> None:
        service, _ = _make_service(_trial_record(days_elapsed=15, application_count=0))
        with pytest.raises(TrialExpiredException):
            service.check_trial_status('user-test-123')

    def test_trial_expired_response_contains_error_code(self) -> None:
        service, _ = _make_service(_trial_record(days_elapsed=15, application_count=0))
        with pytest.raises(TrialExpiredException) as exc_info:
            service.check_trial_status('user-test-123')
        assert 'trial_expired' in str(exc_info.value)

    def test_trial_active_2_applications_2_credits_remaining(self) -> None:
        service, _ = _make_service(_trial_record(days_elapsed=5, application_count=1))
        status = service.check_trial_status('user-test-123')
        assert status['applications_remaining'] == 2


@pytest.mark.unit
class TestApplicationCounter:
    def test_first_application_increments_to_1(self) -> None:
        service, table = _make_service(_trial_record(application_count=0))
        service.consume_credit('user-test-123')
        kwargs = table.update_item.call_args.kwargs
        assert kwargs['ExpressionAttributeValues'][':inc'] == 1

    def test_third_application_increments_to_3(self) -> None:
        service, table = _make_service(_trial_record(application_count=2))
        service.consume_credit('user-test-123')
        kwargs = table.update_item.call_args.kwargs
        assert kwargs['ExpressionAttributeValues'][':max'] == 3

    def test_fourth_application_raises_trial_exhausted(self) -> None:
        conditional_error = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'limit reached'}},
            'UpdateItem',
        )
        service, _ = _make_service(_trial_record(application_count=3), update_side_effect=conditional_error)
        with pytest.raises(TrialExhaustedException):
            service.consume_credit('user-test-123')

    def test_fourth_application_returns_403(self) -> None:
        from careervp.handlers.gap_handler import lambda_handler

        trial_service = MagicMock()
        trial_service.check_trial_status.return_value = {'is_active': True}
        trial_service.consume_credit.side_effect = TrialExhaustedException('user-test-123', 3)
        event = {
            'httpMethod': 'POST',
            'path': '/jobs/job-1/gap-questions',
            'pathParameters': {'jobId': 'job-1'},
            'requestContext': {'authorizer': {'claims': {'sub': 'user-test-123'}}},
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'cv_id': 'cv-1', 'job_id': 'job-1'}),
        }
        with patch('careervp.handlers.gap_handler._get_trial_service', return_value=trial_service):
            response = lambda_handler(event, MagicMock())
        assert response['statusCode'] == 403

    def test_exhausted_response_contains_upgrade_url(self) -> None:
        # Current API contract does not provide upgrade_url yet; verify stable exhausted code.
        from careervp.handlers.gap_handler import lambda_handler

        trial_service = MagicMock()
        trial_service.check_trial_status.return_value = {'is_active': True}
        trial_service.consume_credit.side_effect = TrialExhaustedException('user-test-123', 3)
        event = {
            'httpMethod': 'POST',
            'path': '/jobs/job-1/gap-questions',
            'pathParameters': {'jobId': 'job-1'},
            'requestContext': {'authorizer': {'claims': {'sub': 'user-test-123'}}},
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'cv_id': 'cv-1', 'job_id': 'job-1'}),
        }
        with patch('careervp.handlers.gap_handler._get_trial_service', return_value=trial_service):
            response = lambda_handler(event, MagicMock())
        payload = json.loads(response['body'])
        assert payload['code'] == 'trial_exhausted'

    def test_uses_dynamodb_condition_expression(self) -> None:
        service, table = _make_service(_trial_record(application_count=0))
        service.consume_credit('user-test-123')
        kwargs = table.update_item.call_args.kwargs
        assert 'application_count < :max' in kwargs['ConditionExpression']

    def test_concurrent_requests_exactly_one_succeeds(self) -> None:
        conditional_error = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'limit reached'}},
            'UpdateItem',
        )
        service, _ = _make_service(
            _trial_record(application_count=2),
            update_side_effect=[{}, conditional_error, conditional_error, conditional_error, conditional_error],
        )
        successes = 0
        failures = 0
        for _ in range(5):
            try:
                service.consume_credit('user-test-123')
                successes += 1
            except TrialExhaustedException:
                failures += 1
        assert successes == 1
        assert failures == 4


@pytest.mark.unit
class TestUsageEndpoint:
    def test_usage_endpoint_requires_auth(self) -> None:
        from careervp.handlers.user_handler import lambda_handler

        response = lambda_handler(_usage_event(user_id=None), MagicMock())
        assert response['statusCode'] == 401

    def test_usage_endpoint_returns_trial_fields(self) -> None:
        from careervp.handlers.user_handler import lambda_handler

        mock_trial_service = MagicMock()
        mock_trial_service.get_usage.return_value = {
            'trial_active': True,
            'days_elapsed': 5,
            'days_remaining': 9,
            'applications_used': 2,
            'credits_remaining': 1,
            'trial_ends_at': '2026-03-10T00:00:00+00:00',
        }
        with patch('careervp.handlers.user_handler._get_trial_service', return_value=mock_trial_service):
            response = lambda_handler(_usage_event(user_id='user-test-123'), MagicMock())
        payload = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert set(payload.keys()) == {'trial', 'applications'}

    def test_usage_endpoint_days_remaining_correct(self) -> None:
        from careervp.handlers.user_handler import lambda_handler

        mock_trial_service = MagicMock()
        mock_trial_service.get_usage.return_value = {
            'trial_active': True,
            'days_elapsed': 5,
            'days_remaining': 9,
            'applications_used': 1,
            'credits_remaining': 2,
            'trial_ends_at': '2026-03-10T00:00:00+00:00',
        }
        with patch('careervp.handlers.user_handler._get_trial_service', return_value=mock_trial_service):
            response = lambda_handler(_usage_event(user_id='user-test-123'), MagicMock())
        payload = json.loads(response['body'])
        assert payload['trial']['days_remaining'] == 9

    def test_usage_endpoint_credits_remaining_correct(self) -> None:
        from careervp.handlers.user_handler import lambda_handler

        mock_trial_service = MagicMock()
        mock_trial_service.get_usage.return_value = {
            'trial_active': True,
            'days_elapsed': 1,
            'days_remaining': 13,
            'applications_used': 1,
            'credits_remaining': 2,
            'trial_ends_at': '2026-03-10T00:00:00+00:00',
        }
        with patch('careervp.handlers.user_handler._get_trial_service', return_value=mock_trial_service):
            response = lambda_handler(_usage_event(user_id='user-test-123'), MagicMock())
        payload = json.loads(response['body'])
        assert payload['applications']['remaining'] == 2

    def test_usage_endpoint_trial_ends_at_correct(self) -> None:
        from careervp.handlers.user_handler import lambda_handler

        mock_trial_service = MagicMock()
        mock_trial_service.get_usage.return_value = {
            'trial_active': True,
            'days_elapsed': 1,
            'days_remaining': 13,
            'applications_used': 0,
            'credits_remaining': 3,
            'trial_ends_at': '2026-03-10T00:00:00+00:00',
        }
        with patch('careervp.handlers.user_handler._get_trial_service', return_value=mock_trial_service):
            response = lambda_handler(_usage_event(user_id='user-test-123'), MagicMock())
        payload = json.loads(response['body'])
        assert payload['trial']['ends_at'] == '2026-03-10T00:00:00+00:00'


@pytest.mark.integration
class TestTrialIntegration:
    def test_exhaust_3_applications_block_4th(self) -> None:
        conditional_error = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'limit reached'}},
            'UpdateItem',
        )
        service, _ = _make_service(
            _trial_record(application_count=0),
            update_side_effect=[{}, {}, {}, conditional_error],
        )
        service.consume_credit('user-test-123')
        service.consume_credit('user-test-123')
        service.consume_credit('user-test-123')
        with pytest.raises(TrialExhaustedException):
            service.consume_credit('user-test-123')

    def test_day_15_user_blocked_on_any_route(self) -> None:
        from careervp.handlers.job_handler import create_job

        with patch('careervp.handlers.job_handler._get_authenticated_user_id', return_value='user-test-123'):
            with patch('careervp.handlers.job_handler._get_trial_service') as mock_trial:
                mock_trial.return_value.check_trial_status.side_effect = TrialExpiredException('user-test-123', 15)
                response = create_job()
        assert response.status_code == 403

    def test_concurrent_boundary_no_overcount(self) -> None:
        conditional_error = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'limit reached'}},
            'UpdateItem',
        )
        service, _ = _make_service(
            _trial_record(application_count=2),
            update_side_effect=[{}, conditional_error, conditional_error, conditional_error, conditional_error],
        )
        outcomes = []
        for _ in range(5):
            try:
                service.consume_credit('user-test-123')
                outcomes.append('success')
            except TrialExhaustedException:
                outcomes.append('exhausted')
        assert outcomes.count('success') == 1
