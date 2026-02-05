"""
Unit tests for CV Tailoring Data Access Layer (DAL).

Tests the DAL methods for saving and retrieving tailored CV artifacts from DynamoDB,
including versioning, TTL handling, and GSI queries.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from careervp.dal.cv_tailoring_dal import CVTailoringDAL
from botocore.exceptions import ClientError


@pytest.fixture
def dal():
    """Create DAL instance with mocked DynamoDB client."""
    with patch("boto3.resource"):
        dal = CVTailoringDAL()
        dal.table = MagicMock()
        return dal


def test_save_tailored_cv_artifact(dal, sample_tailored_cv):
    """Test saving tailored CV artifact with TTL."""
    # Arrange
    user_id = "user-123"
    cv_id = "cv-123"
    job_description = "Looking for a software engineer"

    # Act
    _result = dal.save_tailored_cv_artifact(
        user_id=user_id,
        cv_id=cv_id,
        job_description=job_description,
        tailored_cv=sample_tailored_cv,
    )

    # Assert
    dal.table.put_item.assert_called_once()
    call_args = dal.table.put_item.call_args[1]
    item = call_args["Item"]
    assert item["user_id"] == user_id
    assert item["cv_id"] == cv_id
    assert "ttl" in item
    assert item["ttl"] > int(datetime.now().timestamp())


def test_save_tailored_cv_artifact_with_version(dal, sample_tailored_cv):
    """Test saving tailored CV artifact with versioning."""
    # Arrange
    user_id = "user-123"
    cv_id = "cv-123"
    job_description = "Looking for a software engineer"
    version = 2

    # Act
    _result = dal.save_tailored_cv_artifact(
        user_id=user_id,
        cv_id=cv_id,
        job_description=job_description,
        tailored_cv=sample_tailored_cv,
        version=version,
    )

    # Assert
    dal.table.put_item.assert_called_once()
    call_args = dal.table.put_item.call_args[1]
    item = call_args["Item"]
    assert item["version"] == version


def test_get_tailored_cv_artifact(dal, sample_tailored_cv):
    """Test retrieving tailored CV artifact by keys."""
    # Arrange
    user_id = "user-123"
    artifact_id = "artifact-123"
    dal.table.get_item.return_value = {
        "Item": {
            "user_id": user_id,
            "artifact_id": artifact_id,
            "tailored_cv": sample_tailored_cv.dict(),
            "created_at": datetime.now().isoformat(),
        }
    }

    # Act
    _result = dal.get_tailored_cv_artifact(user_id, artifact_id)

    # Assert
    dal.table.get_item.assert_called_once()
    assert _result is not None
    assert _result["user_id"] == user_id
    assert _result["artifact_id"] == artifact_id


def test_get_tailored_cv_artifact_not_found(dal):
    """Test get_tailored_cv_artifact returns None when artifact not found."""
    # Arrange
    user_id = "user-123"
    artifact_id = "non-existent"
    dal.table.get_item.return_value = {}  # No Item key

    # Act
    _result = dal.get_tailored_cv_artifact(user_id, artifact_id)

    # Assert
    assert _result is None


def test_query_tailored_cvs_by_user(dal):
    """Test querying tailored CVs by user ID using GSI."""
    # Arrange
    user_id = "user-123"
    dal.table.query.return_value = {
        "Items": [
            {
                "user_id": user_id,
                "artifact_id": "artifact-1",
                "created_at": "2024-01-01",
            },
            {
                "user_id": user_id,
                "artifact_id": "artifact-2",
                "created_at": "2024-01-02",
            },
        ]
    }

    # Act
    _result = dal.query_tailored_cvs_by_user(user_id)

    # Assert
    dal.table.query.assert_called_once()
    assert len(_result) == 2
    assert all(item["user_id"] == user_id for item in _result)


def test_query_tailored_cvs_by_cv_id(dal):
    """Test querying tailored CVs by CV ID."""
    # Arrange
    cv_id = "cv-123"
    dal.table.query.return_value = {
        "Items": [
            {"cv_id": cv_id, "artifact_id": "artifact-1"},
            {"cv_id": cv_id, "artifact_id": "artifact-2"},
        ]
    }

    # Act
    _result = dal.query_tailored_cvs_by_cv_id(cv_id)

    # Assert
    dal.table.query.assert_called_once()
    assert len(_result) == 2
    assert all(item["cv_id"] == cv_id for item in _result)


def test_save_artifact_with_custom_ttl(dal, sample_tailored_cv):
    """Test saving artifact with custom TTL duration."""
    # Arrange
    user_id = "user-123"
    cv_id = "cv-123"
    job_description = "Looking for a software engineer"
    ttl_days = 90

    # Act
    _result = dal.save_tailored_cv_artifact(
        user_id=user_id,
        cv_id=cv_id,
        job_description=job_description,
        tailored_cv=sample_tailored_cv,
        ttl_days=ttl_days,
    )

    # Assert
    dal.table.put_item.assert_called_once()
    call_args = dal.table.put_item.call_args[1]
    item = call_args["Item"]
    expected_ttl = int((datetime.now() + timedelta(days=ttl_days)).timestamp())
    assert abs(item["ttl"] - expected_ttl) < 60  # Within 1 minute


def test_delete_tailored_cv_artifact(dal):
    """Test deleting tailored CV artifact."""
    # Arrange
    user_id = "user-123"
    artifact_id = "artifact-123"

    # Act
    _result = dal.delete_tailored_cv_artifact(user_id, artifact_id)

    # Assert
    dal.table.delete_item.assert_called_once()
    call_args = dal.table.delete_item.call_args[1]
    assert call_args["Key"]["user_id"] == user_id
    assert call_args["Key"]["artifact_id"] == artifact_id


def test_update_artifact_metadata(dal):
    """Test updating artifact metadata."""
    # Arrange
    user_id = "user-123"
    artifact_id = "artifact-123"
    metadata = {"tags": ["resume", "senior-engineer"], "notes": "For FAANG application"}

    # Act
    _result = dal.update_artifact_metadata(user_id, artifact_id, metadata)

    # Assert
    dal.table.update_item.assert_called_once()


def test_save_artifact_handles_dynamodb_error(dal, sample_tailored_cv):
    """Test save_artifact handles DynamoDB errors gracefully."""
    # Arrange
    user_id = "user-123"
    cv_id = "cv-123"
    job_description = "Looking for a software engineer"
    dal.table.put_item.side_effect = ClientError(
        {
            "Error": {
                "Code": "ProvisionedThroughputExceededException",
                "Message": "Throttled",
            }
        },
        "PutItem",
    )

    # Act & Assert
    with pytest.raises(ClientError):
        dal.save_tailored_cv_artifact(
            user_id=user_id,
            cv_id=cv_id,
            job_description=job_description,
            tailored_cv=sample_tailored_cv,
        )


def test_get_artifact_handles_dynamodb_error(dal):
    """Test get_artifact handles DynamoDB errors gracefully."""
    # Arrange
    user_id = "user-123"
    artifact_id = "artifact-123"
    dal.table.get_item.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError", "Message": "Service error"}},
        "GetItem",
    )

    # Act & Assert
    with pytest.raises(ClientError):
        dal.get_tailored_cv_artifact(user_id, artifact_id)


def test_query_with_pagination(dal):
    """Test querying with pagination support."""
    # Arrange
    user_id = "user-123"
    dal.table.query.return_value = {
        "Items": [{"user_id": user_id, "artifact_id": "artifact-1"}],
        "LastEvaluatedKey": {"user_id": user_id, "artifact_id": "artifact-1"},
    }

    # Act
    _result = dal.query_tailored_cvs_by_user(user_id, limit=1)

    # Assert
    assert len(_result) == 1
    assert "LastEvaluatedKey" in _result or len(_result) == 1


def test_save_artifact_includes_timestamps(dal, sample_tailored_cv):
    """Test saved artifacts include created_at and updated_at timestamps."""
    # Arrange
    user_id = "user-123"
    cv_id = "cv-123"
    job_description = "Looking for a software engineer"

    # Act
    _result = dal.save_tailored_cv_artifact(
        user_id=user_id,
        cv_id=cv_id,
        job_description=job_description,
        tailored_cv=sample_tailored_cv,
    )

    # Assert
    dal.table.put_item.assert_called_once()
    call_args = dal.table.put_item.call_args[1]
    item = call_args["Item"]
    assert "created_at" in item
    assert "updated_at" in item


def test_list_artifacts_sorted_by_date(dal):
    """Test listing artifacts returns _results sorted by creation date."""
    # Arrange
    user_id = "user-123"
    dal.table.query.return_value = {
        "Items": [
            {
                "user_id": user_id,
                "artifact_id": "artifact-1",
                "created_at": "2024-01-01",
            },
            {
                "user_id": user_id,
                "artifact_id": "artifact-2",
                "created_at": "2024-01-03",
            },
            {
                "user_id": user_id,
                "artifact_id": "artifact-3",
                "created_at": "2024-01-02",
            },
        ]
    }

    # Act
    _result = dal.query_tailored_cvs_by_user(user_id, sort_by_date=True)

    # Assert
    # Results should be sorted by created_at descending (newest first)
    assert _result[0]["created_at"] == "2024-01-03"
    assert _result[1]["created_at"] == "2024-01-02"
    assert _result[2]["created_at"] == "2024-01-01"
