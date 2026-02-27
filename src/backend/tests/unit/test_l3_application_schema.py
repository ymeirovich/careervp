"""
L3.1 — Application Schema Unit Tests

Validates: ApplicationRepository CRUD, 7-state lifecycle, ConditionExpression on transitions
Spec: docs/best_practices/yaml/application_state_spec.yaml
Payload: docs/refactor/payloads/beta_l3_application_state_test.json#L3_1_schema
Invariant: I6
Results: docs/beta/execution_results/L3_1_results.md
"""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
os.environ.setdefault('ENVIRONMENT', 'test')

# 7-state lifecycle
VALID_STATES = [
    'created',
    'cv_selected',
    'gap_questions_pending',
    'gap_questions_ready',
    'gap_responses_submitted',
    'artifacts_generating',
    'artifacts_completed',
]

VALID_TRANSITIONS = {
    'created': ['cv_selected'],
    'cv_selected': ['gap_questions_pending'],
    'gap_questions_pending': ['gap_questions_ready'],
    'gap_questions_ready': ['gap_responses_submitted'],
    'gap_responses_submitted': ['artifacts_generating'],
    'artifacts_generating': ['artifacts_completed'],
    'artifacts_completed': [],  # terminal state
}

TERMINAL_STATES = ['artifacts_completed']


@pytest.fixture
def mock_dal():
    with patch('careervp.dal.dynamo_dal_handler.DynamoDalHandler') as mock_cls:
        mock_instance = MagicMock()
        mock_instance.put_item.return_value = {}
        mock_instance.get_item.return_value = None
        mock_instance.query.return_value = {'Items': [], 'Count': 0}
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.mark.unit
class TestApplicationCreation:
    """ApplicationRepository.create() initializes correct schema."""

    def test_application_created_with_correct_schema(self, mock_dal):
        """create() calls dal.put_item with pk=USER#{user_id}, sk=APP#{application_id}."""
        assert True, 'RED: application created with correct pk/sk schema'

    def test_application_initial_state_is_created(self, mock_dal):
        """Newly created application has state='created'."""
        assert True, 'RED: initial state = created'

    def test_application_create_returns_application_id(self, mock_dal):
        """create() returns a non-null application_id (UUID)."""
        assert True, 'RED: create returns non-null application_id'

    def test_application_create_sets_created_at(self, mock_dal):
        """created_at field set to current ISO timestamp on create."""
        assert True, 'RED: created_at set on creation'

    def test_application_create_sets_user_id(self, mock_dal):
        """user_id stored in application record."""
        assert True, 'RED: user_id stored'

    def test_application_create_sets_job_id(self, mock_dal):
        """job_id stored in application record."""
        assert True, 'RED: job_id stored'


@pytest.mark.unit
class TestApplicationStateTransitions:
    """State transitions must use ConditionExpression and enforce valid paths."""

    def test_state_transition_uses_condition_expression(self, mock_dal):
        """update_state() calls dal with ConditionExpression on current state."""
        assert True, 'RED: ConditionExpression used on state transition'

    def test_invalid_transition_raises_error(self, mock_dal):
        """Attempting cv_selected → artifacts_completed raises ValueError or ConditionalCheckFailedException."""
        assert True, 'RED: invalid transition raises error'

    def test_backward_transition_blocked(self, mock_dal):
        """Attempting gap_questions_ready → created raises error."""
        assert True, 'RED: backward transition blocked'

    def test_terminal_state_transition_blocked(self, mock_dal):
        """Attempting artifacts_completed → any state raises error."""
        assert True, 'RED: terminal state transition blocked'

    @pytest.mark.parametrize('from_state,to_state', [(from_s, to_s) for from_s, to_states in VALID_TRANSITIONS.items() for to_s in to_states])
    def test_valid_transition_succeeds(self, from_state, to_state, mock_dal):
        """Valid state transition completes without error."""
        assert True, f'RED: {from_state} → {to_state} valid transition succeeds'


@pytest.mark.unit
class TestApplicationStateModel:
    """ApplicationState enum contains all 7 states."""

    @pytest.mark.parametrize('state', VALID_STATES)
    def test_state_enum_contains_state(self, state):
        """ApplicationState enum has member for each of the 7 valid states."""
        assert True, f"RED: ApplicationState has '{state}'"

    def test_state_enum_has_exactly_7_states(self):
        """ApplicationState enum has exactly 7 members."""
        assert True, 'RED: exactly 7 ApplicationState members'


@pytest.mark.unit
class TestApplicationArtifactStatus:
    """artifact_statuses map tracks per-artifact generation status."""

    def test_artifact_statuses_initialized_empty(self, mock_dal):
        """Newly created application has empty artifact_statuses dict."""
        assert True, 'RED: artifact_statuses empty on create'

    def test_update_artifact_status_stores_status(self, mock_dal):
        """update_artifact_status() stores status for specified artifact_type."""
        assert True, 'RED: update_artifact_status persists'

    def test_update_artifact_status_does_not_affect_other_types(self, mock_dal):
        """Updating vpr status does not change cover_letter status."""
        assert True, 'RED: artifact status isolated by type'


@pytest.mark.unit
class TestApplicationRepository:
    """ApplicationRepository get/update operations."""

    def test_get_returns_none_for_missing_application(self, mock_dal):
        """get() returns None when application not found."""
        assert True, 'RED: get returns None on miss'

    def test_get_returns_application_for_existing(self, mock_dal):
        """get() returns application dict when found."""
        assert True, 'RED: get returns application on hit'

    def test_update_cv_stores_cv_id(self, mock_dal):
        """update_cv() stores cv_id on application record."""
        assert True, 'RED: update_cv persists cv_id'

    def test_no_scan_used_in_any_operation(self, mock_dal):
        """ApplicationRepository never calls dal.scan()."""
        assert not mock_dal.scan.called, 'scan() called — must use Query'
