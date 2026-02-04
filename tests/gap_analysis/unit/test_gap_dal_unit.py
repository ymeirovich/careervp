"""
Unit tests for gap analysis DAL methods.
Tests for dal/dynamo_dal_handler.py gap analysis extensions.

RED PHASE: These tests will FAIL until DAL methods are implemented.

NOTE: Task 06 (DAL extensions) is OPTIONAL for Phase 11.
These tests only apply if you choose to implement DAL storage.
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

# These imports will fail until the module is created
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.models import ResultCode


class TestSaveGapAnalysis:
    """Test save_gap_analysis DAL method (OPTIONAL)."""

    def test_save_gap_analysis_success(
        self,
        mock_user_id: str,
        mock_cv_id: str,
        mock_gap_questions: list[dict[str, Any]],
    ):
        """Test successful gap analysis save."""
        with patch("careervp.dal.dynamo_dal_handler.boto3.resource") as mock_boto3:
            mock_table = MagicMock()
            mock_boto3.return_value.Table.return_value = mock_table
            mock_table.put_item.return_value = {}

            dal = DynamoDalHandler(table_name="test-table")
            result = dal.save_gap_analysis(
                user_id=mock_user_id,
                cv_id=mock_cv_id,
                job_posting_id="job_123",
                questions=mock_gap_questions,
                version=1,
            )

        assert result.success is True
        assert result.code == ResultCode.GAP_RESPONSES_SAVED
        mock_table.put_item.assert_called_once()

    def test_save_gap_analysis_creates_correct_item(
        self,
        mock_user_id: str,
        mock_cv_id: str,
        mock_gap_questions: list[dict[str, Any]],
    ):
        """Test that save creates item with correct structure."""
        with patch("careervp.dal.dynamo_dal_handler.boto3.resource") as mock_boto3:
            mock_table = MagicMock()
            mock_boto3.return_value.Table.return_value = mock_table

            dal = DynamoDalHandler(table_name="test-table")
            dal.save_gap_analysis(
                user_id=mock_user_id,
                cv_id=mock_cv_id,
                job_posting_id="job_123",
                questions=mock_gap_questions,
                version=1,
            )

            # Verify item structure
            call_args = mock_table.put_item.call_args
            item = call_args[1]["Item"]

            assert item["pk"] == mock_user_id
            assert item["sk"] == f"ARTIFACT#GAP#{mock_cv_id}#job_123#v1"
            assert item["artifact_type"] == "gap_analysis"
            assert item["user_id"] == mock_user_id
            assert item["cv_id"] == mock_cv_id
            assert item["questions"] == mock_gap_questions
            assert item["version"] == 1
            assert "created_at" in item
            assert "ttl" in item

    def test_save_gap_analysis_sets_ttl_90_days(
        self,
        mock_user_id: str,
        mock_cv_id: str,
        mock_gap_questions: list[dict[str, Any]],
    ):
        """Test that save sets TTL to 90 days."""
        with patch("careervp.dal.dynamo_dal_handler.boto3.resource") as mock_boto3:
            mock_table = MagicMock()
            mock_boto3.return_value.Table.return_value = mock_table

            dal = DynamoDalHandler(table_name="test-table")
            dal.save_gap_analysis(
                user_id=mock_user_id,
                cv_id=mock_cv_id,
                job_posting_id="job_123",
                questions=mock_gap_questions,
            )

            call_args = mock_table.put_item.call_args
            item = call_args[1]["Item"]
            ttl = item["ttl"]

            # TTL should be ~90 days from now (7776000 seconds)
            now = int(datetime.now(timezone.utc).timestamp())
            assert ttl > now
            assert ttl < now + (91 * 24 * 60 * 60)  # Less than 91 days

    def test_save_gap_analysis_handles_dynamodb_error(
        self,
        mock_user_id: str,
        mock_cv_id: str,
        mock_gap_questions: list[dict[str, Any]],
    ):
        """Test handling of DynamoDB errors."""
        with patch("careervp.dal.dynamo_dal_handler.boto3.resource") as mock_boto3:
            mock_table = MagicMock()
            mock_boto3.return_value.Table.return_value = mock_table
            mock_table.put_item.side_effect = Exception("DynamoDB error")

            dal = DynamoDalHandler(table_name="test-table")
            result = dal.save_gap_analysis(
                user_id=mock_user_id,
                cv_id=mock_cv_id,
                job_posting_id="job_123",
                questions=mock_gap_questions,
            )

        assert result.success is False
        assert result.code == ResultCode.INTERNAL_ERROR
        assert "Failed to save gap analysis" in result.error


class TestGetGapAnalysis:
    """Test get_gap_analysis DAL method (OPTIONAL)."""

    def test_get_gap_analysis_success(
        self,
        mock_user_id: str,
        mock_cv_id: str,
        mock_gap_questions: list[dict[str, Any]],
    ):
        """Test successful gap analysis retrieval."""
        mock_item = {
            "pk": mock_user_id,
            "sk": f"ARTIFACT#GAP#{mock_cv_id}#job_123#v1",
            "questions": mock_gap_questions,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("careervp.dal.dynamo_dal_handler.boto3.resource") as mock_boto3:
            mock_table = MagicMock()
            mock_boto3.return_value.Table.return_value = mock_table
            mock_table.get_item.return_value = {"Item": mock_item}

            dal = DynamoDalHandler(table_name="test-table")
            result = dal.get_gap_analysis(
                user_id=mock_user_id,
                cv_id=mock_cv_id,
                job_posting_id="job_123",
                version=1,
            )

        assert result.success is True
        assert result.code == ResultCode.SUCCESS
        assert result.data == mock_item

    def test_get_gap_analysis_not_found(self, mock_user_id: str, mock_cv_id: str):
        """Test gap analysis not found."""
        with patch("careervp.dal.dynamo_dal_handler.boto3.resource") as mock_boto3:
            mock_table = MagicMock()
            mock_boto3.return_value.Table.return_value = mock_table
            mock_table.get_item.return_value = {}  # No Item

            dal = DynamoDalHandler(table_name="test-table")
            result = dal.get_gap_analysis(
                user_id=mock_user_id,
                cv_id=mock_cv_id,
                job_posting_id="job_123",
                version=1,
            )

        assert result.success is False
        assert result.code == ResultCode.NOT_FOUND
        assert "not found" in result.error.lower()

    def test_get_gap_analysis_uses_correct_key(
        self, mock_user_id: str, mock_cv_id: str
    ):
        """Test that get uses correct DynamoDB key."""
        with patch("careervp.dal.dynamo_dal_handler.boto3.resource") as mock_boto3:
            mock_table = MagicMock()
            mock_boto3.return_value.Table.return_value = mock_table
            mock_table.get_item.return_value = {"Item": {}}

            dal = DynamoDalHandler(table_name="test-table")
            dal.get_gap_analysis(
                user_id=mock_user_id,
                cv_id=mock_cv_id,
                job_posting_id="job_123",
                version=1,
            )

            call_args = mock_table.get_item.call_args
            key = call_args[1]["Key"]

            assert key["pk"] == mock_user_id
            assert key["sk"] == f"ARTIFACT#GAP#{mock_cv_id}#job_123#v1"

    def test_get_gap_analysis_handles_dynamodb_error(
        self, mock_user_id: str, mock_cv_id: str
    ):
        """Test handling of DynamoDB errors."""
        with patch("careervp.dal.dynamo_dal_handler.boto3.resource") as mock_boto3:
            mock_table = MagicMock()
            mock_boto3.return_value.Table.return_value = mock_table
            mock_table.get_item.side_effect = Exception("DynamoDB error")

            dal = DynamoDalHandler(table_name="test-table")
            result = dal.get_gap_analysis(
                user_id=mock_user_id,
                cv_id=mock_cv_id,
                job_posting_id="job_123",
                version=1,
            )

        assert result.success is False
        assert result.code == ResultCode.INTERNAL_ERROR
        assert "Failed to retrieve gap analysis" in result.error
