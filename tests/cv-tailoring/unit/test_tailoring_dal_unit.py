"""
Unit tests for CV Tailoring DAL methods on DynamoDalHandler.

Verifies SK construction, TTL handling, and basic CRUD behavior.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.models.result import ResultCode


@pytest.fixture
def dal_with_table():
    """Create DAL instance with mocked DynamoDB table."""
    table = MagicMock()
    dal = DynamoDalHandler(table_name="test-table")
    dal._get_db_handler = MagicMock(return_value=table)
    return dal, table


def test_save_tailored_cv_artifact(dal_with_table, sample_tailored_cv):
    """Test saving tailored CV artifact with TTL."""
    dal, table = dal_with_table

    result = dal.save_tailored_cv(sample_tailored_cv, job_id="job-123")

    assert result.success is True
    table.put_item.assert_called_once()
    item = table.put_item.call_args[1]["Item"]
    assert item["pk"] == sample_tailored_cv.user_id
    assert item["cv_id"] == sample_tailored_cv.cv_id
    assert item["sk"] == "ARTIFACT#CV_TAILORED#cv_123#job-123#v1"
    assert "ttl" in item
    assert item["ttl"] > int(datetime.now(timezone.utc).timestamp())


def test_save_tailored_cv_artifact_with_version(dal_with_table, sample_tailored_cv):
    """Test saving tailored CV artifact with explicit version."""
    dal, table = dal_with_table

    result = dal.save_tailored_cv(sample_tailored_cv, job_id="job-123", version=2)

    assert result.success is True
    item = table.put_item.call_args[1]["Item"]
    assert item["sk"] == "ARTIFACT#CV_TAILORED#cv_123#job-123#v2"
    assert item["version"] == 2


def test_get_tailored_cv(dal_with_table, sample_tailored_cv):
    """Test retrieving tailored CV artifact by keys."""
    dal, table = dal_with_table
    table.get_item.return_value = {
        "Item": {
            "pk": sample_tailored_cv.user_id,
            "sk": "ARTIFACT#CV_TAILORED#cv_123#job-123#v1",
            "tailored_cv": sample_tailored_cv.model_dump(mode="json"),
        }
    }

    result = dal.get_tailored_cv(
        user_id=sample_tailored_cv.user_id,
        cv_id=sample_tailored_cv.cv_id,
        job_id="job-123",
        version=1,
    )

    assert result.success is True
    assert result.data is not None
    assert result.data.cv_id == sample_tailored_cv.cv_id


def test_get_tailored_cv_not_found(dal_with_table, sample_tailored_cv):
    """Test get_tailored_cv returns None when artifact not found."""
    dal, table = dal_with_table
    table.get_item.return_value = {}

    result = dal.get_tailored_cv(
        user_id=sample_tailored_cv.user_id,
        cv_id=sample_tailored_cv.cv_id,
        job_id="job-123",
        version=1,
    )

    assert result.success is True
    assert result.data is None


def test_list_tailored_cvs(dal_with_table, sample_tailored_cv):
    """Test listing tailored CVs by user ID."""
    dal, table = dal_with_table
    table.query.return_value = {
        "Items": [
            {
                "pk": sample_tailored_cv.user_id,
                "sk": "ARTIFACT#CV_TAILORED#cv_123#job-123#v1",
                "tailored_cv": sample_tailored_cv.model_dump(mode="json"),
            }
        ]
    }

    result = dal.list_tailored_cvs(sample_tailored_cv.user_id)

    assert result.success is True
    assert result.data is not None
    assert len(result.data) == 1


def test_list_tailored_cvs_pagination(dal_with_table, sample_tailored_cv):
    """Test list_tailored_cvs handles pagination."""
    dal, table = dal_with_table
    first_page = {
        "Items": [
            {
                "pk": sample_tailored_cv.user_id,
                "sk": "ARTIFACT#CV_TAILORED#cv_123#job-123#v1",
                "tailored_cv": sample_tailored_cv.model_dump(mode="json"),
            }
        ],
        "LastEvaluatedKey": {"pk": sample_tailored_cv.user_id, "sk": "next"},
    }
    second_page = {
        "Items": [
            {
                "pk": sample_tailored_cv.user_id,
                "sk": "ARTIFACT#CV_TAILORED#cv_123#job-123#v2",
                "tailored_cv": sample_tailored_cv.model_dump(mode="json"),
            }
        ]
    }
    table.query.side_effect = [first_page, second_page]

    result = dal.list_tailored_cvs(sample_tailored_cv.user_id)

    assert result.success is True
    assert result.data is not None
    assert len(result.data) == 2


def test_save_tailored_cv_handles_dynamodb_error(dal_with_table, sample_tailored_cv):
    """Test save_tailored_cv handles DynamoDB errors gracefully."""
    dal, table = dal_with_table
    table.put_item.side_effect = ClientError(
        {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "Throttled"}},
        "PutItem",
    )

    result = dal.save_tailored_cv(sample_tailored_cv, job_id="job-123")

    assert result.success is False
    assert result.code == ResultCode.DYNAMODB_ERROR


def test_get_tailored_cv_handles_dynamodb_error(dal_with_table, sample_tailored_cv):
    """Test get_tailored_cv handles DynamoDB errors gracefully."""
    dal, table = dal_with_table
    table.get_item.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError", "Message": "Service error"}},
        "GetItem",
    )

    result = dal.get_tailored_cv(
        user_id=sample_tailored_cv.user_id,
        cv_id=sample_tailored_cv.cv_id,
        job_id="job-123",
        version=1,
    )

    assert result.success is False
    assert result.code == ResultCode.DYNAMODB_ERROR
