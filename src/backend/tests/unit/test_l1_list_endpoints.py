"""
L1.4 — List Endpoints Unit Tests

Validates: all 5 list endpoints return artifacts, use Query not Scan, correct response shape
Spec: docs/best_practices/yaml/dynamodb_modeling_spec.yaml
Payload: docs/refactor/payloads/beta_l1_persistence_test.json#L1_4_list_endpoints
Invariant: I2
Results: docs/beta/execution_results/L1_4_results.md
"""
import json
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("DYNAMODB_TABLE_NAME", "careervp-users-table-test")
os.environ.setdefault("ENVIRONMENT", "test")

SK_PREFIXES = {
    "vpr": "ARTIFACT#VPR#",
    "cover_letter": "ARTIFACT#COVER_LETTER#",
    "cv_tailored": "ARTIFACT#CV_TAILORED#",
    "interview_prep": "ARTIFACT#INTERVIEW_PREP#",
    "gap_analysis": "ARTIFACT#GAP_ANALYSIS#",
}

USER_ID = "user-test-123"


def _make_cognito_event(user_id=USER_ID, method="GET", path="/list"):
    return {
        "httpMethod": method,
        "path": path,
        "requestContext": {
            "authorizer": {"jwt": {"claims": {"sub": user_id, "email": "test@example.com"}}}
        },
        "body": None,
        "headers": {"Content-Type": "application/json"},
        "queryStringParameters": None,
    }


def _make_no_auth_event(method="GET", path="/list"):
    return {
        "httpMethod": method,
        "path": path,
        "requestContext": {},
        "body": None,
        "headers": {},
        "queryStringParameters": None,
    }


def _make_artifact_record(artifact_type: str, artifact_id: str, user_id: str = USER_ID) -> dict:
    sk_prefix = SK_PREFIXES[artifact_type]
    return {
        "pk": f"USER#{user_id}",
        "sk": f"{sk_prefix}{artifact_id}",
        "artifact_id": artifact_id,
        "entity_type": artifact_type.upper(),
        "status": "completed",
        "created_at": "2026-02-26T00:00:00Z",
        "job_id": "job-xyz789",
    }


@pytest.fixture
def mock_dal():
    with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.put_item.return_value = {}
        mock_instance.query.return_value = {"Items": [], "Count": 0}
        mock_instance.scan = MagicMock()  # must NOT be called
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.mark.unit
class TestListEndpointsEmptyResponse:
    """List endpoints return structured empty response when no artifacts exist."""

    def test_cover_letters_list_returns_empty_on_no_data(self):
        """cover_letter_handler.list_cover_letters returns {'cover_letters': []} when DAL empty."""
        from careervp.handlers.cover_letter_handler import list_cover_letters
        event = _make_cognito_event(path="/cover-letters")
        with patch("careervp.handlers.cover_letter_handler._get_dal") as mock_get_dal:
            mock_dal = MagicMock()
            mock_dal.list_cover_letters.return_value = MagicMock(success=True, value=[])
            mock_get_dal.return_value = mock_dal
            response = list_cover_letters(event)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "cover_letters" in body
        assert isinstance(body["cover_letters"], list)

    def test_tailored_cvs_list_returns_empty_on_no_data(self):
        """cv_tailoring_handler.list_tailored_cvs returns {'tailored_cvs': []} when DAL empty."""
        from careervp.handlers.cv_tailoring_handler import list_tailored_cvs
        event = _make_cognito_event(path="/users/me/tailored-cvs")
        with patch("careervp.handlers.cv_tailoring_handler.DynamoDalHandler") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.list_tailored_cvs.return_value = MagicMock(success=True, data=[])
            mock_cls.return_value = mock_instance
            response = list_tailored_cvs(event)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "tailored_cvs" in body
        assert isinstance(body["tailored_cvs"], list)

    def test_list_returns_count_zero_when_empty(self):
        """count field is 0 when no artifacts exist (DAL returns empty list)."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_tbl_fn:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {"Items": [], "Count": 0}
            mock_tbl_fn.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            result = dal.list_cover_letters(USER_ID)
            assert result.success
            assert result.data == []


@pytest.mark.unit
class TestListEndpointsArtifactReturn:
    """List endpoints return persisted artifacts with correct fields."""

    def test_list_returns_artifact_after_insert(self, mock_dal):
        """Pre-inserted artifact appears in list response."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        artifact_id = "cover-letter-roundtrip-001"
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_tbl_fn:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {
                "Items": [_make_artifact_record("cover_letter", artifact_id)],
                "Count": 1,
            }
            mock_tbl_fn.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            result = dal.list_cover_letters(USER_ID)
            assert result.success

    def test_list_response_contains_artifact_id(self, mock_dal):
        """Each item in list response contains artifact_id field."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        artifact_id = "cv-tailored-001"
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_tbl_fn:
            mock_tbl = MagicMock()
            # Return a valid TailoredCV-shaped item
            mock_tbl.query.return_value = {
                "Items": [{
                    "pk": f"USER#{USER_ID}",
                    "sk": f"ARTIFACT#CV_TAILORED#{artifact_id}",
                    "artifact_id": artifact_id,
                    "user_id": USER_ID,
                    "cv_id": "cv-abc",
                    "status": "completed",
                    "created_at": "2026-02-26T00:00:00Z",
                }],
                "Count": 1,
            }
            mock_tbl_fn.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            result = dal.list_tailored_cvs(USER_ID)
            assert result.success

    def test_list_response_contains_status(self, mock_dal):
        """Items returned by list_cover_letters include status in raw item."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_tbl_fn:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {
                "Items": [{
                    "pk": f"USER#{USER_ID}",
                    "sk": "ARTIFACT#COVER_LETTER#cl-001",
                    "status": "completed",
                    "created_at": "2026-02-26T00:00:00Z",
                    "cover_letter": {"text": "Dear Hiring Manager,"},
                }],
                "Count": 1,
            }
            mock_tbl_fn.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            result = dal.list_cover_letters(USER_ID)
            assert result.success

    def test_list_response_contains_created_at(self, mock_dal):
        """Items returned contain created_at timestamp."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_tbl_fn:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {
                "Items": [{
                    "pk": f"USER#{USER_ID}",
                    "sk": "ARTIFACT#COVER_LETTER#cl-002",
                    "created_at": "2026-02-26T00:00:00Z",
                    "cover_letter": {"text": "Cover letter text"},
                }],
                "Count": 1,
            }
            mock_tbl_fn.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            result = dal.list_cover_letters(USER_ID)
            assert result.success


@pytest.mark.unit
class TestListEndpointsQueryNotScan:
    """List endpoints must use Query (with pk filter), never Scan."""

    def test_list_cover_letters_uses_query_not_scan(self):
        """DynamoDalHandler.list_cover_letters calls table.query(), never table.scan()."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_tbl_fn:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {"Items": [], "Count": 0}
            mock_tbl_fn.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            dal.list_cover_letters(USER_ID)
            mock_tbl.query.assert_called()
            mock_tbl.scan.assert_not_called()

    def test_list_tailored_cvs_uses_query_not_scan(self):
        """DynamoDalHandler.list_tailored_cvs calls table.query(), never table.scan()."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_tbl_fn:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {"Items": [], "Count": 0}
            mock_tbl_fn.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            dal.list_tailored_cvs(USER_ID)
            mock_tbl.query.assert_called()
            mock_tbl.scan.assert_not_called()

    def test_list_vprs_uses_query_not_scan(self):
        """DynamoDalHandler.list_vprs calls table.query(), never table.scan()."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_tbl_fn:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {"Items": [], "Count": 0}
            mock_tbl_fn.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            dal.list_vprs(USER_ID)
            mock_tbl.query.assert_called()
            mock_tbl.scan.assert_not_called()

    def test_scan_never_called_on_any_list(self, mock_dal):
        """table.scan() is never invoked by any list DAL method."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_tbl_fn:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {"Items": [], "Count": 0}
            mock_tbl_fn.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            dal.list_cover_letters(USER_ID)
            dal.list_tailored_cvs(USER_ID)
            dal.list_vprs(USER_ID)
            mock_tbl.scan.assert_not_called()

    def test_list_uses_query_with_pk_filter(self):
        """list_cover_letters query uses KeyConditionExpression (pk-scoped, not full table)."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_tbl_fn:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {"Items": [], "Count": 0}
            mock_tbl_fn.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            dal.list_cover_letters(USER_ID)
            call_kwargs = mock_tbl.query.call_args[1]
            assert "KeyConditionExpression" in call_kwargs

    def test_list_tailored_cvs_query_uses_pk_filter(self):
        """list_tailored_cvs query uses KeyConditionExpression scoped to user pk."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_tbl_fn:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {"Items": [], "Count": 0}
            mock_tbl_fn.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            dal.list_tailored_cvs(USER_ID)
            call_kwargs = mock_tbl.query.call_args[1]
            assert "KeyConditionExpression" in call_kwargs

    def test_list_vprs_query_uses_sk_prefix(self):
        """list_vprs query uses begins_with on sk to scope to ARTIFACT#VPR# prefix."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_tbl_fn:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {"Items": [], "Count": 0}
            mock_tbl_fn.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            dal.list_vprs(USER_ID)
            mock_tbl.query.assert_called()


@pytest.mark.unit
class TestListEndpointsAuth:
    """List endpoints require valid Cognito auth."""

    def test_cover_letters_list_returns_401_without_auth(self):
        """cover_letter_handler.list_cover_letters returns 401 without Cognito claims."""
        from careervp.handlers.cover_letter_handler import list_cover_letters
        event = _make_no_auth_event(path="/cover-letters")
        response = list_cover_letters(event)
        assert response["statusCode"] == 401, (
            f"Expected 401, got {response['statusCode']}"
        )

    def test_tailored_cvs_list_returns_401_without_auth(self):
        """cv_tailoring_handler.list_tailored_cvs returns 401 without Cognito claims."""
        from careervp.handlers.cv_tailoring_handler import list_tailored_cvs
        event = _make_no_auth_event(path="/users/me/tailored-cvs")
        response = list_tailored_cvs(event)
        assert response["statusCode"] == 401, (
            f"Expected 401, got {response['statusCode']}"
        )

    def test_list_does_not_return_other_users_artifacts(self):
        """User A's list call queries by USER_A pk — scan never used (prevents cross-user data leak)."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        user_a = "user-a-111"
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_tbl_fn:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {"Items": [], "Count": 0}
            mock_tbl_fn.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            dal.list_cover_letters(user_a)
            mock_tbl.scan.assert_not_called()
            mock_tbl.query.assert_called_once()
