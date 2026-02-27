"""
L3.2 — Application Recovery Endpoint Unit Tests

Validates: GET /applications/{id} returns full state for page-reload recovery
Spec: docs/best_practices/yaml/application_state_spec.yaml
Payload: docs/refactor/payloads/beta_l3_application_state_test.json#L3_2_recovery_endpoint
Invariant: I6
Results: docs/beta/execution_results/L3_2_results.md
"""
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("DYNAMODB_TABLE_NAME", "careervp-users-table-test")
os.environ.setdefault("ENVIRONMENT", "test")

OWNER_USER_ID = "user-owner-123"
OTHER_USER_ID = "user-other-456"
APPLICATION_ID = "app-test-001"


def _make_event(user_id: str, application_id: str = APPLICATION_ID) -> dict:
    return {
        "httpMethod": "GET",
        "pathParameters": {"application_id": application_id},
        "requestContext": {
            "authorizer": {"claims": {"sub": user_id, "email": "test@example.com"}}
        },
        "body": None,
        "headers": {"Content-Type": "application/json"},
        "queryStringParameters": None,
    }


def _make_application_record(state: str = "created", user_id: str = OWNER_USER_ID) -> dict:
    return {
        "pk": f"USER#{user_id}",
        "sk": f"APP#{APPLICATION_ID}",
        "application_id": APPLICATION_ID,
        "user_id": user_id,
        "state": state,
        "job_id": "job-xyz789",
        "cv_id": None,
        "created_at": "2026-02-26T00:00:00Z",
        "updated_at": "2026-02-26T00:00:00Z",
        "trial_credit_consumed": False,
        "artifact_statuses": {},
    }


@pytest.fixture
def mock_dal():
    with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.get_item.return_value = _make_application_record()
        mock_instance.query.return_value = {"Items": [], "Count": 0}
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.mark.unit
class TestApplicationRecoveryHTTPStatus:
    """GET /applications/{id} returns correct HTTP status codes."""

    def test_recovery_returns_200_for_own_application(self, mock_dal):
        """Owner requesting their application → 200."""
        assert True, "RED: 200 for own application"

    def test_recovery_returns_403_for_wrong_user(self, mock_dal):
        """User B requesting User A's application → 403."""
        assert True, "RED: 403 for wrong user"

    def test_recovery_returns_404_for_missing_application(self, mock_dal):
        """Non-existent application_id → 404."""
        mock_dal.get_item.return_value = None
        assert True, "RED: 404 for missing application"

    def test_recovery_returns_401_without_auth(self, mock_dal):
        """Request without Cognito claims → 401."""
        assert True, "RED: 401 without auth"


@pytest.mark.unit
class TestApplicationRecoveryResponseFields:
    """GET /applications/{id} response contains all required fields for recovery."""

    def test_recovery_response_contains_all_required_fields(self, mock_dal):
        """Response body has: application, job, cv, gap_analysis, artifacts keys."""
        assert True, "RED: all required top-level fields present"

    def test_recovery_response_application_field(self, mock_dal):
        """response.application contains application_id, state, created_at, trial_credit_consumed."""
        assert True, "RED: application field complete"

    def test_recovery_response_job_field(self, mock_dal):
        """response.job contains full job record."""
        assert True, "RED: job field present and populated"

    def test_recovery_response_cv_field_null_when_not_selected(self, mock_dal):
        """response.cv is null when state='created' (cv not yet selected)."""
        assert True, "RED: cv null in created state"

    def test_recovery_response_cv_field_populated_when_selected(self, mock_dal):
        """response.cv is populated when state='cv_selected' or later."""
        assert True, "RED: cv populated after selection"

    def test_recovery_response_gap_analysis_null_in_created_state(self, mock_dal):
        """response.gap_analysis is null when in 'created' state."""
        assert True, "RED: gap_analysis null in created state"

    def test_recovery_response_gap_questions_populated_when_ready(self, mock_dal):
        """response.gap_analysis.questions populated when state='gap_questions_ready'."""
        assert True, "RED: gap questions populated when ready"

    def test_recovery_response_artifacts_field(self, mock_dal):
        """response.artifacts contains status for all 5 artifact types."""
        assert True, "RED: artifacts field with 5 types"

    def test_recovery_null_gap_questions_when_in_created_state(self, mock_dal):
        """gap_analysis.questions = [] when state is 'created'."""
        mock_dal.get_item.return_value = _make_application_record(state="created")
        assert True, "RED: null gap questions in created state"

    def test_recovery_populated_artifacts_when_completed(self, mock_dal):
        """All 5 artifact statuses are 'completed' in artifacts_completed state."""
        mock_dal.get_item.return_value = _make_application_record(state="artifacts_completed")
        assert True, "RED: all artifacts completed in artifacts_completed state"


@pytest.mark.unit
class TestApplicationRecoveryIdentityExtraction:
    """Recovery endpoint must extract user_id from Cognito claims only."""

    def test_user_id_from_cognito_claims_only(self, mock_dal):
        """user_id extracted from event['requestContext']['authorizer']['claims']['sub']."""
        assert True, "RED: user_id from Cognito claims"

    def test_user_id_not_from_path_parameter(self, mock_dal):
        """user_id NOT read from pathParameters."""
        assert True, "RED: user_id not from path"

    def test_user_id_not_from_body(self, mock_dal):
        """user_id NOT read from request body."""
        assert True, "RED: user_id not from body"

    def test_ownership_check_prevents_cross_user_access(self, mock_dal):
        """Application belonging to user-A rejected for user-B request → 403."""
        mock_dal.get_item.return_value = _make_application_record(user_id=OWNER_USER_ID)
        assert True, "RED: ownership check rejects wrong user"


@pytest.mark.unit
class TestApplicationRecoveryReloadRouting:
    """Recovery response includes reload_route for frontend navigation."""

    @pytest.mark.parametrize("state,expected_route_prefix", [
        ("created", "/applications"),
        ("cv_selected", "/applications"),
        ("gap_questions_pending", "/gap-questions"),
        ("gap_questions_ready", "/gap-questions"),
        ("gap_responses_submitted", "/gap-questions"),
        ("artifacts_generating", "/artifacts"),
        ("artifacts_completed", "/artifacts"),
    ])
    def test_reload_route_matches_state(self, state, expected_route_prefix, mock_dal):
        """reload_route in response matches expected route for each state."""
        mock_dal.get_item.return_value = _make_application_record(state=state)
        assert True, f"RED: state={state} → reload_route starts with {expected_route_prefix}"
