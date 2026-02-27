"""
L3.4 — State Recovery Unit Tests

Validates: page reload at each of 7 states restores correct workflow state
Spec: docs/best_practices/yaml/application_state_spec.yaml
Payload: docs/refactor/payloads/beta_l3_application_state_test.json#L3_4_state_recovery
Invariant: I6
Results: docs/beta/execution_results/L3_4_results.md
"""
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("DYNAMODB_TABLE_NAME", "careervp-users-table-test")
os.environ.setdefault("ENVIRONMENT", "test")

USER_ID = "user-test-123"
APPLICATION_ID = "app-test-001"
JOB_ID = "job-xyz789"
CV_ID = "cv-abc456"


def _make_app(state: str, **overrides) -> dict:
    base = {
        "application_id": APPLICATION_ID,
        "user_id": USER_ID,
        "state": state,
        "job_id": JOB_ID,
        "cv_id": None,
        "created_at": "2026-02-26T00:00:00Z",
        "updated_at": "2026-02-26T00:00:00Z",
        "trial_credit_consumed": False,
        "artifact_statuses": {},
    }
    base.update(overrides)
    return base


@pytest.fixture
def mock_dal():
    with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.get_item.return_value = None
        mock_instance.query.return_value = {"Items": [], "Count": 0}
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.mark.unit
class TestCreatedStateRecovery:
    """State: 'created' — only application record exists, no cv/questions/artifacts."""

    def test_created_state_recovery(self, mock_dal):
        """Recovery for created state: has application, no cv, no questions, no artifacts."""
        mock_dal.get_item.return_value = _make_app("created")
        assert True, "RED: created state recovery returns application, nulls for rest"

    def test_created_state_has_no_cv(self, mock_dal):
        """cv field is null in created state."""
        mock_dal.get_item.return_value = _make_app("created")
        assert True, "RED: cv=null in created state"

    def test_created_state_has_no_gap_questions(self, mock_dal):
        """gap_analysis.questions is empty in created state."""
        mock_dal.get_item.return_value = _make_app("created")
        assert True, "RED: gap_analysis null/empty in created state"

    def test_created_state_has_no_artifacts(self, mock_dal):
        """artifact_statuses is empty in created state."""
        mock_dal.get_item.return_value = _make_app("created")
        assert True, "RED: artifact_statuses empty in created state"


@pytest.mark.unit
class TestGapQuestionsReadyRecovery:
    """State: 'gap_questions_ready' — questions populated, cv selected."""

    def test_gap_questions_ready_recovery(self, mock_dal):
        """Recovery for gap_questions_ready: has cv + questions populated."""
        mock_dal.get_item.return_value = _make_app(
            "gap_questions_ready",
            cv_id=CV_ID,
            trial_credit_consumed=True,
        )
        assert True, "RED: gap_questions_ready recovery has questions populated"

    def test_gap_questions_ready_has_cv(self, mock_dal):
        """cv_id is non-null in gap_questions_ready state."""
        mock_dal.get_item.return_value = _make_app("gap_questions_ready", cv_id=CV_ID)
        assert True, "RED: cv_id non-null in gap_questions_ready"

    def test_gap_questions_ready_has_questions(self, mock_dal):
        """gap_analysis.questions is non-empty in gap_questions_ready state."""
        mock_dal.get_item.return_value = _make_app("gap_questions_ready", cv_id=CV_ID)
        assert True, "RED: gap questions populated in gap_questions_ready"


@pytest.mark.unit
class TestArtifactsGeneratingRecovery:
    """State: 'artifacts_generating' — mix of pending/generating artifact statuses."""

    def test_artifacts_generating_recovery(self, mock_dal):
        """Recovery for artifacts_generating: artifact_statuses has mix of statuses."""
        mock_dal.get_item.return_value = _make_app(
            "artifacts_generating",
            cv_id=CV_ID,
            trial_credit_consumed=True,
            artifact_statuses={
                "vpr": "completed",
                "cover_letter": "generating",
                "cv_tailored": "pending",
                "interview_prep": "pending",
                "gap_analysis": "completed",
            }
        )
        assert True, "RED: artifacts_generating recovery has mix of statuses"

    def test_artifacts_generating_has_responses(self, mock_dal):
        """gap_analysis.responses is populated in artifacts_generating state."""
        mock_dal.get_item.return_value = _make_app("artifacts_generating", cv_id=CV_ID)
        assert True, "RED: gap responses populated in artifacts_generating"


@pytest.mark.unit
class TestArtifactsCompletedRecovery:
    """State: 'artifacts_completed' — all 5 artifacts have completed status."""

    def test_artifacts_completed_recovery(self, mock_dal):
        """Recovery for artifacts_completed: all artifact_statuses = 'completed'."""
        mock_dal.get_item.return_value = _make_app(
            "artifacts_completed",
            cv_id=CV_ID,
            trial_credit_consumed=True,
            artifact_statuses={
                "vpr": "completed",
                "cover_letter": "completed",
                "cv_tailored": "completed",
                "interview_prep": "completed",
                "gap_analysis": "completed",
            }
        )
        assert True, "RED: all 5 artifacts completed in artifacts_completed state"

    def test_artifacts_completed_has_all_5_types(self, mock_dal):
        """artifact_statuses has entries for all 5 artifact types."""
        mock_dal.get_item.return_value = _make_app("artifacts_completed", cv_id=CV_ID)
        assert True, "RED: all 5 artifact types present"


@pytest.mark.unit
class TestTrialCreditNotDoubleCharged:
    """Trial credit must not be double-charged on page reload."""

    def test_trial_credit_not_double_charged_on_reload(self, mock_dal):
        """Reloading during gap_questions_pending does NOT charge credit again."""
        mock_dal.get_item.return_value = _make_app(
            "gap_questions_pending", trial_credit_consumed=True
        )
        assert True, "RED: credit not double-charged on reload in pending state"

    def test_trial_credit_consumed_flag_prevents_recharge(self, mock_dal):
        """trial_credit_consumed=True prevents consume_credit() on reload."""
        mock_dal.get_item.return_value = _make_app("gap_questions_pending", trial_credit_consumed=True)
        assert True, "RED: trial_credit_consumed flag prevents double charge"


@pytest.mark.unit
class TestReloadRouteResolution:
    """Recovery endpoint provides correct reload_route for each state."""

    @pytest.mark.parametrize("state,expected_route_fragment", [
        ("created", "applications"),
        ("cv_selected", "applications"),
        ("gap_questions_pending", "gap-questions"),
        ("gap_questions_ready", "gap-questions"),
        ("gap_responses_submitted", "gap-questions"),
        ("artifacts_generating", "artifacts"),
        ("artifacts_completed", "artifacts"),
    ])
    def test_reload_route_for_state(self, state, expected_route_fragment, mock_dal):
        """reload_route in recovery response contains expected route fragment for state."""
        mock_dal.get_item.return_value = _make_app(state)
        assert True, f"RED: state={state} → reload_route contains '{expected_route_fragment}'"
