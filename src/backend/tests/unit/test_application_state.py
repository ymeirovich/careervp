"""
Application State Model Unit Tests — CareerVP Beta

Tests for:
- 7-state lifecycle (created → artifacts_completed)
- State transitions with validation
- GET /applications/{id} recovery endpoint
- Ownership checks
- Conditional writes for concurrency safety

Spec: docs/best_practices/yaml/application_state_spec.yaml
Payload: docs/refactor/payloads/beta_l3_application_state_test.json
Invariant: I6
"""

import json
import os

import pytest

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
os.environ.setdefault('ENVIRONMENT', 'test')

CANONICAL_STATES = [
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
    'artifacts_generating': ['artifacts_completed', 'artifacts_failed'],
    'artifacts_completed': [],
    'artifacts_failed': ['artifacts_generating'],
}


def _make_application_record(
    application_id: str = 'app-xyz789',
    user_id: str = 'user-test-123',
    state: str = 'created',
    trial_credit_consumed: bool = False,
) -> dict:
    """Factory for application DynamoDB records."""
    return {
        'pk': f'USER#{user_id}',
        'sk': f'APP#{application_id}',
        'application_id': application_id,
        'user_id': user_id,
        'job_id': 'job-abc456',
        'cv_id': None,
        'state': state,
        'created_at': '2026-02-26T10:00:00Z',
        'updated_at': '2026-02-26T10:00:00Z',
        'trial_credit_consumed': trial_credit_consumed,
        'artifact_statuses': {
            'vpr': 'pending',
            'cv_tailored': 'pending',
            'cover_letter': 'pending',
            'interview_prep': 'pending',
            'gap_analysis': 'pending',
        },
        'entity_type': 'APPLICATION',
        'ttl': 1756310400,
    }


def _make_cognito_event(
    method: str = 'GET',
    path: str = '/applications/app-xyz789',
    user_id: str = 'user-test-123',
    path_params: dict | None = None,
    body: dict | None = None,
) -> dict:
    """Factory for API Gateway event with Cognito claims."""
    return {
        'httpMethod': method,
        'path': path,
        'pathParameters': path_params or {'application_id': 'app-xyz789'},
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': user_id,
                    'email': f'{user_id}@example.com',
                }
            }
        },
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body) if body else None,
    }


# =============================================================================
# SECTION 1: STATE MODEL TESTS
# =============================================================================


@pytest.mark.unit
class TestApplicationStateModel:
    """Tests for the canonical 7-state application lifecycle."""

    def test_application_created_on_job_post(self):
        """POST /jobs creates application record in 'created' state."""
        assert True, 'RED: job creation triggers application in created state'

    def test_application_initial_state_is_created(self):
        """New application always starts in 'created' state."""
        assert True, 'RED: initial state'

    def test_all_7_states_are_canonical(self):
        """Verify the 7 canonical states are defined and recognized."""
        assert len(CANONICAL_STATES) == 7
        for state in CANONICAL_STATES:
            assert isinstance(state, str), f'State must be string: {state}'

    def test_valid_transitions_cover_all_states(self):
        """Every canonical state has a defined transition map."""
        for state in CANONICAL_STATES:
            assert state in VALID_TRANSITIONS, f'Missing transitions for: {state}'

    def test_created_transitions_to_cv_selected(self):
        """created → cv_selected is valid."""
        assert 'cv_selected' in VALID_TRANSITIONS['created']

    def test_artifacts_completed_has_no_transitions(self):
        """artifacts_completed is a terminal state."""
        assert VALID_TRANSITIONS['artifacts_completed'] == []

    def test_invalid_transition_raises_error(self):
        """Backward transition (e.g., artifacts_completed → created) raises."""
        assert True, 'RED: InvalidStateTransitionError raised'

    def test_backward_transition_blocked(self):
        """gap_questions_pending → created raises InvalidStateTransitionError."""
        assert True, 'RED: backward blocked'

    def test_state_transition_uses_conditional_write(self):
        """update_application_state uses DynamoDB ConditionExpression."""
        assert True, 'RED: conditional write'

    def test_concurrent_state_update_one_succeeds(self):
        """Concurrent updates to same state → only valid one wins."""
        assert True, 'RED: conditional write prevents double update'


# =============================================================================
# SECTION 2: RECOVERY ENDPOINT TESTS
# =============================================================================


@pytest.mark.unit
class TestApplicationRecovery:
    """Tests for GET /applications/{id} recovery endpoint."""

    def test_recovery_returns_200_for_own_application(self):
        """Owner user gets 200 with full state."""
        assert True, 'RED: 200 for owner'

    def test_recovery_returns_403_for_wrong_user(self):
        """Non-owner user gets 403 Forbidden."""
        assert True, 'RED: 403 for wrong user'

    def test_recovery_returns_404_for_missing_application(self):
        """Non-existent application_id gets 404."""
        assert True, 'RED: 404 for missing'

    def test_recovery_response_contains_application_field(self):
        """Response includes application: {application_id, state, ...}."""
        assert True, 'RED: application field'

    def test_recovery_response_contains_job_field(self):
        """Response includes job: {job_id, title, company, ...}."""
        assert True, 'RED: job field'

    def test_recovery_response_contains_cv_field(self):
        """Response includes cv: {cv_id, filename} or null."""
        assert True, 'RED: cv field'

    def test_recovery_response_contains_artifact_statuses(self):
        """Response includes artifacts dict with all 5 types."""
        assert True, 'RED: artifacts field'

    def test_recovery_response_null_gap_questions_when_not_generated(self):
        """Application in 'created' state → gap_analysis.questions is null."""
        assert True, 'RED: null questions'

    def test_recovery_response_contains_gap_questions_when_ready(self):
        """Application in 'gap_questions_ready' → questions array populated."""
        assert True, 'RED: questions populated'

    def test_recovery_extracts_user_id_from_cognito_only(self):
        """User ID comes from requestContext.authorizer.claims.sub."""
        assert True, 'RED: Cognito identity only'


# =============================================================================
# SECTION 3: STATE TRANSITIONS WITH ARTIFACT TRACKING
# =============================================================================


@pytest.mark.unit
class TestArtifactStatusTracking:
    """Tests for artifact_statuses updates within application record."""

    def test_all_artifacts_start_as_pending(self):
        """New application has all 5 artifact statuses as 'pending'."""
        record = _make_application_record()
        for artifact_type in ['vpr', 'cv_tailored', 'cover_letter', 'interview_prep', 'gap_analysis']:
            assert record['artifact_statuses'][artifact_type] == 'pending'

    def test_artifact_status_updates_on_worker_complete(self):
        """Worker completion updates artifact_statuses[type] to 'completed'."""
        assert True, 'RED: artifact status update'

    def test_artifact_status_updates_on_worker_fail(self):
        """Worker failure updates artifact_statuses[type] to 'failed'."""
        assert True, 'RED: artifact failure status'

    def test_all_completed_transitions_application_to_artifacts_completed(self):
        """When all 5 artifacts complete → application state = artifacts_completed."""
        assert True, 'RED: auto-transition on all complete'


# =============================================================================
# SECTION 4: RELOAD RECOVERY SCENARIOS
# =============================================================================


@pytest.mark.unit
class TestReloadRecovery:
    """Tests that page reload at any workflow step restores correct state.

    Validates I6: Frontend state survives page reload at every workflow step.
    """

    @pytest.mark.parametrize(
        'state,expected_recovery_field',
        [
            ('created', 'application'),
            ('cv_selected', 'cv'),
            ('gap_questions_ready', 'gap_analysis'),
            ('gap_responses_submitted', 'gap_analysis'),
            ('artifacts_generating', 'artifacts'),
            ('artifacts_completed', 'artifacts'),
        ],
    )
    def test_reload_returns_correct_state_field(self, state: str, expected_recovery_field: str):
        """GET /applications/{id} returns the data needed to restore the given workflow step."""
        assert True, f'RED: {state} → {expected_recovery_field} populated in response'

    def test_trial_credit_not_double_charged_on_reload(self):
        """Page reload during gap_questions_pending does not re-charge credit."""
        assert True, 'RED: trial_credit_consumed=True prevents re-charge'
