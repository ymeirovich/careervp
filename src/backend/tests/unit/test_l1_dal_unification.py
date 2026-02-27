"""
L1.2 — DAL Unification Unit Tests

Validates: CVTable fully replaced by DynamoDalHandler across all handlers/DAL files
Spec: docs/best_practices/yaml/dynamodb_modeling_spec.yaml
Payload: docs/refactor/payloads/beta_l1_persistence_test.json#L1_2_dal_unification
Invariant: I2
Results: docs/beta/execution_results/L1_2_results.md
"""
import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("DYNAMODB_TABLE_NAME", "careervp-users-table-test")
os.environ.setdefault("ENVIRONMENT", "test")

BACKEND_DIR = "/Users/yitzchak/Documents/dev/careervp/src/backend"


@pytest.fixture
def mock_dal():
    with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.get_item.return_value = {"pk": "USER#u1", "sk": "CV#cv1", "content": "test"}
        mock_instance.put_item.return_value = {}
        mock_instance.query.return_value = {"Items": [], "Count": 0}
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.mark.unit
class TestNoCVTableImports:
    """CVTable must not be imported anywhere in handlers or DAL (except cv_dal.py itself)."""

    def test_no_cvtable_imports_in_handlers(self):
        """grep for CVTable in handlers/ .py files returns 0 matches."""
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "CVTable", "careervp/handlers/"],
            capture_output=True, text=True, cwd=BACKEND_DIR
        )
        assert result.returncode != 0, (
            f"CVTable still imported in handlers:\n{result.stdout.strip()}"
        )

    def test_no_cvtable_imports_in_logic(self):
        """grep for CVTable in logic/ .py files returns 0 matches."""
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "CVTable", "careervp/logic/"],
            capture_output=True, text=True, cwd=BACKEND_DIR
        )
        assert result.returncode != 0, (
            f"CVTable still used in logic:\n{result.stdout.strip()}"
        )

    def test_no_cv_table_module_imports(self):
        """grep for 'from careervp.dal.cv_dal import CVTable' returns 0 matches outside cv_dal.py."""
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "from careervp.dal.cv_dal import CVTable", "careervp/"],
            capture_output=True, text=True, cwd=BACKEND_DIR
        )
        lines = [
            line for line in result.stdout.splitlines()
            if "cv_dal.py" not in line
        ]
        assert lines == [], (
            "CVTable imported outside cv_dal.py:\n" + "\n".join(lines)
        )

    def test_cover_letter_handler_no_cvtable(self):
        """cover_letter_handler.py has no CVTable references."""
        result = subprocess.run(
            ["grep", "--include=*.py", "CVTable", "careervp/handlers/cover_letter_handler.py"],
            capture_output=True, text=True, cwd=BACKEND_DIR
        )
        assert result.returncode != 0, (
            f"CVTable still in cover_letter_handler:\n{result.stdout.strip()}"
        )

    def test_interview_prep_handler_no_cvtable(self):
        """interview_prep_handler.py has no CVTable references."""
        result = subprocess.run(
            ["grep", "--include=*.py", "CVTable", "careervp/handlers/interview_prep_handler.py"],
            capture_output=True, text=True, cwd=BACKEND_DIR
        )
        assert result.returncode != 0, (
            f"CVTable still in interview_prep_handler:\n{result.stdout.strip()}"
        )

    def test_cv_tailoring_handler_no_cvtable(self):
        """cv_tailoring_handler.py has no CVTable references."""
        result = subprocess.run(
            ["grep", "--include=*.py", "CVTable", "careervp/handlers/cv_tailoring_handler.py"],
            capture_output=True, text=True, cwd=BACKEND_DIR
        )
        assert result.returncode != 0, (
            f"CVTable still in cv_tailoring_handler:\n{result.stdout.strip()}"
        )


@pytest.mark.unit
class TestCVDalUsesDynamoDalHandler:
    """DynamoDalHandler is used for CV persistence (not CVTable)."""

    def test_dynamo_dal_handler_has_save_cv(self):
        """DynamoDalHandler has save_cv() method."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        assert hasattr(DynamoDalHandler, 'save_cv'), "DynamoDalHandler missing save_cv()"

    def test_dynamo_dal_handler_has_get_cv(self):
        """DynamoDalHandler has get_cv() method."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        assert hasattr(DynamoDalHandler, 'get_cv'), "DynamoDalHandler missing get_cv()"

    def test_dynamo_dal_handler_has_list_cover_letters(self):
        """DynamoDalHandler has list_cover_letters() method."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        assert hasattr(DynamoDalHandler, 'list_cover_letters'), (
            "DynamoDalHandler missing list_cover_letters()"
        )

    def test_dynamo_dal_handler_has_list_tailored_cvs(self):
        """DynamoDalHandler has list_tailored_cvs() method."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        assert hasattr(DynamoDalHandler, 'list_tailored_cvs'), (
            "DynamoDalHandler missing list_tailored_cvs()"
        )

    def test_dynamo_dal_handler_has_save_cover_letter(self):
        """DynamoDalHandler has save_cover_letter() method."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        assert hasattr(DynamoDalHandler, 'save_cover_letter'), (
            "DynamoDalHandler missing save_cover_letter()"
        )

    def test_cv_save_calls_put_item(self):
        """save_cv() calls dal.put_item with correct pk/sk schema."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        from careervp.models.cv import UserCV
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_table:
            mock_tbl = MagicMock()
            mock_table.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            user_cv = UserCV(
                user_id="USER#user-test-123",
                cv_id="cv-abc456",
                full_name="Test User",
            )
            dal.save_cv(user_cv)
            mock_tbl.put_item.assert_called_once()
            item = mock_tbl.put_item.call_args[1]["Item"]
            assert item["pk"] == "USER#user-test-123", f"Wrong pk: {item.get('pk')}"

    def test_cv_list_calls_query_not_scan(self):
        """list_tailored_cvs() calls table.query(), never table.scan()."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_table:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {"Items": [], "Count": 0}
            mock_table.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            dal.list_tailored_cvs("user-test-123")
            mock_tbl.query.assert_called_once()
            mock_tbl.scan.assert_not_called()


@pytest.mark.unit
class TestDynamoDalHandlerSchema:
    """DynamoDalHandler uses correct single-table pk/sk schema."""

    def test_cover_letter_sk_prefix(self):
        """save_cover_letter() sk starts with 'ARTIFACT#COVER_LETTER#'."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_table:
            mock_tbl = MagicMock()
            mock_table.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            dal.save_cover_letter(
                cover_letter={"text": "Dear Hiring Manager,"},
                user_id="user-test-123",
                cv_id="cv-abc456",
                job_id="job-xyz789",
            )
            mock_tbl.put_item.assert_called_once()
            item = mock_tbl.put_item.call_args[1]["Item"]
            assert item["sk"].startswith("ARTIFACT#COVER_LETTER#"), (
                f"Wrong sk prefix: {item.get('sk')}"
            )

    def test_vpr_sk_prefix(self):
        """save_vpr() sk starts with 'ARTIFACT#VPR#'."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        from careervp.models.vpr import VPR
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_table:
            mock_tbl = MagicMock()
            mock_table.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            vpr = VPR(
                user_id="user-test-123",
                application_id="app-001",
                vpr_text="Value Proposition Report content",
                executive_summary="Senior Python engineer delivering 40% cost reduction.",
            )
            dal.save_vpr(vpr)
            mock_tbl.put_item.assert_called_once()
            item = mock_tbl.put_item.call_args[1]["Item"]
            assert item["sk"].startswith("ARTIFACT#VPR#"), (
                f"Wrong sk prefix: {item.get('sk')}"
            )

    def test_gap_questions_sk_prefix(self):
        """save_gap_questions() sk starts with 'ARTIFACT#GAP_ANALYSIS#'."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        with patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler") as mock_table:
            mock_tbl = MagicMock()
            mock_table.return_value = mock_tbl
            dal = DynamoDalHandler("test-table")
            dal.save_gap_questions(
                user_id="user-test-123",
                cv_id="cv-abc456",
                job_id="job-xyz789",
                questions=[{"question": "Tell me about yourself"}],
            )
            mock_tbl.put_item.assert_called_once()
            item = mock_tbl.put_item.call_args[1]["Item"]
            assert item["sk"].startswith("ARTIFACT#GAP_ANALYSIS#"), (
                f"Wrong sk prefix: {item.get('sk')}"
            )
