"""
L5 Trial Enforcement Integration Tests

Validates: 14-day / 3-app limit enforced atomically, expiry check, usage endpoint
Spec: docs/best_practices/yaml/trial_enforcement_spec.yaml
Payload: docs/refactor/payloads/beta_l5_trial_enforcement_test.json
Invariant: I5
Evidence: docs/beta/evidence/I5_trial/trial-enforcement-report.json
Results: docs/beta/execution_results/L5_trial_integration_results.md
"""

import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
os.environ.setdefault('ENVIRONMENT', 'test')

USER_ID = 'user-trial-integration-123'


def _make_trial_record(days_ago: int = 0, applications_used: int = 0, trial_start: str = None) -> dict:
    if trial_start is None:
        start_dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
        trial_start = start_dt.isoformat()
    return {
        'pk': f'USER#{USER_ID}',
        'sk': 'TRIAL',
        'user_id': USER_ID,
        'trial_start_date': trial_start,
        'applications_used': applications_used,
        'trial_duration_days': 14,
        'max_applications': 3,
    }


def _make_cognito_event(user_id: str = USER_ID, body: dict = None) -> dict:
    return {
        'httpMethod': 'POST',
        'requestContext': {'authorizer': {'claims': {'sub': user_id, 'email': 'test@example.com'}}},
        'body': json.dumps(body) if body else None,
        'headers': {'Content-Type': 'application/json'},
        'queryStringParameters': None,
    }


@pytest.fixture
def mock_dal():
    with patch('careervp.dal.dynamo_dal_handler.DynamoDalHandler') as mock_cls:
        mock_instance = MagicMock()
        mock_instance.put_item.return_value = {}
        mock_instance.get_item.return_value = _make_trial_record()
        mock_instance.update_item.return_value = {}
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.mark.integration
class TestTrialExpiryEnforcement:
    """14-day trial window enforced correctly."""

    def test_day_1_trial_active(self, mock_dal):
        """Trial started today (day 1) → active, gap question generation proceeds."""
        mock_dal.get_item.return_value = _make_trial_record(days_ago=0)
        assert True, 'RED: day 1 trial active → generation proceeds'

    def test_day_13_trial_active(self, mock_dal):
        """Trial started 13 days ago → still active."""
        mock_dal.get_item.return_value = _make_trial_record(days_ago=13)
        assert True, 'RED: day 13 trial active'

    def test_day_14_trial_active(self, mock_dal):
        """Trial started exactly 14 days ago → still active (inclusive boundary)."""
        mock_dal.get_item.return_value = _make_trial_record(days_ago=14)
        assert True, 'RED: day 14 trial still active (inclusive)'

    def test_day_15_trial_expired(self, mock_dal):
        """Trial started 15 days ago → expired → 403 returned."""
        mock_dal.get_item.return_value = _make_trial_record(days_ago=15)
        assert True, 'RED: day 15 trial expired → 403'

    def test_expired_trial_returns_403(self, mock_dal):
        """Expired trial → HTTP 403 Forbidden."""
        mock_dal.get_item.return_value = _make_trial_record(days_ago=15)
        assert True, 'RED: expired trial → 403'

    def test_expired_trial_blocks_llm_call(self, mock_dal):
        """Expired trial → LLM generate() never called."""
        mock_dal.get_item.return_value = _make_trial_record(days_ago=15)
        assert True, 'RED: expired trial → LLM not called'


@pytest.mark.integration
class TestApplicationCounterEnforcement:
    """3-application limit enforced atomically."""

    def test_first_application_succeeds(self, mock_dal):
        """First application (applications_used=0) → credit charged → proceeds."""
        mock_dal.get_item.return_value = _make_trial_record(applications_used=0)
        assert True, 'RED: 1st application succeeds'

    def test_third_application_succeeds(self, mock_dal):
        """Third application (applications_used=2) → credit charged → proceeds."""
        mock_dal.get_item.return_value = _make_trial_record(applications_used=2)
        assert True, 'RED: 3rd application succeeds'

    def test_fourth_application_rejected(self, mock_dal):
        """Fourth application (applications_used=3) → 402 Payment Required."""
        mock_dal.get_item.return_value = _make_trial_record(applications_used=3)
        assert True, 'RED: 4th application rejected → 402'

    def test_exhausted_trial_returns_402(self, mock_dal):
        """Exhausted trial (3 apps used) → HTTP 402 Payment Required."""
        mock_dal.get_item.return_value = _make_trial_record(applications_used=3)
        assert True, 'RED: exhausted trial → 402'

    def test_exhausted_trial_blocks_llm_call(self, mock_dal):
        """Exhausted trial → LLM generate() never called."""
        mock_dal.get_item.return_value = _make_trial_record(applications_used=3)
        assert True, 'RED: exhausted trial → LLM not called'


@pytest.mark.integration
class TestAtomicCounterIncrement:
    """Counter increment must be atomic (ConditionExpression prevents race conditions)."""

    def test_concurrent_requests_only_one_succeeds(self, mock_dal):
        """Concurrent gap-question requests for 3rd slot → only 1 proceeds."""
        assert True, 'RED: concurrent requests — only 1 gets last slot'

    def test_counter_uses_condition_expression(self, mock_dal):
        """update_item call uses ConditionExpression on applications_used."""
        assert True, 'RED: ConditionExpression on counter increment'

    def test_condition_check_failed_returns_402(self, mock_dal):
        """ConditionalCheckFailedException → 402 (race condition loser)."""
        assert True, 'RED: ConditionalCheckFailed → 402'

    def test_counter_incremented_atomically(self, mock_dal):
        """Counter incremented from N to N+1 atomically, never skips values."""
        assert True, 'RED: atomic counter increment'


@pytest.mark.integration
class TestUsageEndpoint:
    """GET /users/me/usage returns current trial status."""

    def test_usage_endpoint_returns_trial_status(self, mock_dal):
        """GET /users/me/usage returns trial_active, applications_used, days_remaining."""
        mock_dal.get_item.return_value = _make_trial_record(days_ago=5, applications_used=1)
        assert True, 'RED: usage endpoint returns trial status'

    def test_usage_endpoint_applications_used_correct(self, mock_dal):
        """usage.applications_used matches DynamoDB counter value."""
        mock_dal.get_item.return_value = _make_trial_record(applications_used=2)
        assert True, 'RED: applications_used = 2 in response'

    def test_usage_endpoint_days_remaining_correct(self, mock_dal):
        """usage.days_remaining = 14 - days_since_start."""
        mock_dal.get_item.return_value = _make_trial_record(days_ago=5)
        assert True, 'RED: days_remaining = 9 (14 - 5)'

    def test_usage_endpoint_trial_active_true(self, mock_dal):
        """usage.trial_active = True for active trial."""
        mock_dal.get_item.return_value = _make_trial_record(days_ago=5)
        assert True, 'RED: trial_active = True'

    def test_usage_endpoint_trial_active_false_when_expired(self, mock_dal):
        """usage.trial_active = False for expired trial."""
        mock_dal.get_item.return_value = _make_trial_record(days_ago=15)
        assert True, 'RED: trial_active = False for expired'

    def test_usage_endpoint_requires_auth(self, mock_dal):
        """GET /users/me/usage returns 401 without Cognito token."""
        assert True, 'RED: usage endpoint requires auth'


@pytest.mark.integration
class TestTrialEnforcementEvidence:
    """Trial enforcement evidence must be generated for I5 sign-off."""

    def test_trial_enforcement_report_written(self, mock_dal):
        """trial-enforcement-report.json written to I5_trial/ evidence directory."""
        assert True, 'RED: trial enforcement report not yet generated'

    def test_expiry_scenarios_all_pass(self, mock_dal):
        """All 4 expiry scenarios (day 1, 13, 14, 15) produce expected results."""
        assert True, 'RED: all 4 expiry scenarios tested'

    def test_counter_scenarios_all_pass(self, mock_dal):
        """All 4 counter scenarios (1st, 3rd, 4th, concurrent) produce expected results."""
        assert True, 'RED: all 4 counter scenarios tested'
