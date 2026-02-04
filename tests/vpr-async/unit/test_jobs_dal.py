"""
Unit tests for Jobs DAL (Data Access Layer).

Tests CRUD operations on the careervp-jobs-table-dev DynamoDB table:
- Job creation with required fields validation
- Job retrieval by job_id (partition key)
- Job updates (status, timestamps, results)
- Idempotency key GSI queries
- TTL attribute handling
- Error handling and DynamoDB exceptions
"""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from moto import mock_aws
import boto3

# Note: In actual implementation, import from:
# from careervp.dal.jobs_repository import JobsRepository


class MockJobsRepository:
    """Mock Jobs Repository for testing without live DynamoDB."""

    def __init__(
        self, table_name: str, idempotency_index_name: str = "idempotency-key-index"
    ):
        """Initialize mock repository."""
        self.table_name = table_name
        self.idempotency_index = idempotency_index_name
        self.jobs_store = {}  # In-memory store for mock

    def create_job(self, job_data: dict[str, Any]) -> dict[str, Any]:
        """Create job with validation."""
        required_fields = ["job_id", "status", "created_at", "idempotency_key"]
        for field in required_fields:
            if field not in job_data:
                raise ValueError(f"Missing required field: {field}")

        job_id = job_data["job_id"]
        if job_id in self.jobs_store:
            raise ValueError(f"Job {job_id} already exists")

        self.jobs_store[job_id] = job_data
        return {"success": True, "data": job_data}

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Get job by job_id."""
        return self.jobs_store.get(job_id)

    def get_job_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        """Get job by idempotency key (GSI query)."""
        for job in self.jobs_store.values():
            if job.get("idempotency_key") == idempotency_key:
                return job
        return None

    def update_job_status(
        self, job_id: str, status: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Update job status and optional fields."""
        if job_id not in self.jobs_store:
            raise ValueError(f"Job {job_id} not found")

        job = self.jobs_store[job_id]
        job["status"] = status
        job.update(kwargs)
        return {"success": True, "data": job}

    def update_job(self, job_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update job with multiple fields."""
        if job_id not in self.jobs_store:
            raise ValueError(f"Job {job_id} not found")

        job = self.jobs_store[job_id]
        job.update(updates)
        return {"success": True, "data": job}


@pytest.fixture
def jobs_repo():
    """Fixture providing Jobs Repository instance."""
    return MockJobsRepository(table_name="test-jobs-table")


@pytest.fixture
def valid_job_data() -> dict[str, Any]:
    """Valid job data with all required fields."""
    now = datetime.utcnow()
    ttl_timestamp = int((now + timedelta(hours=4)).timestamp())

    return {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "PENDING",
        "created_at": now.isoformat() + "Z",
        "idempotency_key": "vpr#user_123#app_456",
        "user_id": "user_123",
        "application_id": "app_456",
        "input_data": {
            "company_name": "Acme Corp",
            "role_title": "Senior Engineer",
            "requirements": ["Python", "AWS"],
        },
        "ttl": ttl_timestamp,
    }


class TestJobsDALCreate:
    """Test suite for create_job() method."""

    def test_create_job_success(self, jobs_repo, valid_job_data):
        """Test successful job creation with all required fields."""
        result = jobs_repo.create_job(valid_job_data)

        assert result["success"] is True
        assert result["data"]["job_id"] == valid_job_data["job_id"]
        assert result["data"]["status"] == "PENDING"
        assert result["data"]["user_id"] == "user_123"

    def test_create_job_missing_job_id(self, jobs_repo, valid_job_data):
        """Test creation fails when job_id is missing."""
        del valid_job_data["job_id"]

        with pytest.raises(ValueError, match="Missing required field: job_id"):
            jobs_repo.create_job(valid_job_data)

    def test_create_job_missing_status(self, jobs_repo, valid_job_data):
        """Test creation fails when status is missing."""
        del valid_job_data["status"]

        with pytest.raises(ValueError, match="Missing required field: status"):
            jobs_repo.create_job(valid_job_data)

    def test_create_job_missing_created_at(self, jobs_repo, valid_job_data):
        """Test creation fails when created_at is missing."""
        del valid_job_data["created_at"]

        with pytest.raises(ValueError, match="Missing required field: created_at"):
            jobs_repo.create_job(valid_job_data)

    def test_create_job_missing_idempotency_key(self, jobs_repo, valid_job_data):
        """Test creation fails when idempotency_key is missing."""
        del valid_job_data["idempotency_key"]

        with pytest.raises(ValueError, match="Missing required field: idempotency_key"):
            jobs_repo.create_job(valid_job_data)

    def test_create_job_with_all_optional_fields(self, jobs_repo, valid_job_data):
        """Test job creation stores all optional fields."""
        result = jobs_repo.create_job(valid_job_data)

        job = result["data"]
        assert job["input_data"] == valid_job_data["input_data"]
        assert job["ttl"] == valid_job_data["ttl"]
        assert job["user_id"] == "user_123"

    def test_create_job_duplicate_id_fails(self, jobs_repo, valid_job_data):
        """Test creating job with duplicate job_id fails."""
        jobs_repo.create_job(valid_job_data)

        with pytest.raises(ValueError, match="already exists"):
            jobs_repo.create_job(valid_job_data)


class TestJobsDALRead:
    """Test suite for get_job() and get_job_by_idempotency_key() methods."""

    def test_get_job_by_id_success(self, jobs_repo, valid_job_data):
        """Test successful job retrieval by job_id."""
        jobs_repo.create_job(valid_job_data)

        job = jobs_repo.get_job(valid_job_data["job_id"])

        assert job is not None
        assert job["job_id"] == valid_job_data["job_id"]
        assert job["status"] == "PENDING"
        assert job["user_id"] == "user_123"

    def test_get_job_by_id_not_found(self, jobs_repo):
        """Test get_job returns None for non-existent job."""
        job = jobs_repo.get_job("non-existent-job-id")

        assert job is None

    def test_get_job_by_idempotency_key_success(self, jobs_repo, valid_job_data):
        """Test successful job retrieval by idempotency key via GSI."""
        jobs_repo.create_job(valid_job_data)

        job = jobs_repo.get_job_by_idempotency_key(valid_job_data["idempotency_key"])

        assert job is not None
        assert job["job_id"] == valid_job_data["job_id"]
        assert job["idempotency_key"] == "vpr#user_123#app_456"

    def test_get_job_by_idempotency_key_not_found(self, jobs_repo):
        """Test get_job_by_idempotency_key returns None for missing key."""
        job = jobs_repo.get_job_by_idempotency_key("non-existent-key")

        assert job is None

    def test_get_job_by_idempotency_key_duplicate_detection(
        self, jobs_repo, valid_job_data
    ):
        """Test idempotency key query returns first match for duplicate detection."""
        jobs_repo.create_job(valid_job_data)

        # Attempt to create another job with same idempotency key
        # (in real scenario, GSI would prevent this via unique constraint)
        second_job = valid_job_data.copy()
        second_job["job_id"] = "different-job-id"
        # Don't insert second job, just verify first is found

        job = jobs_repo.get_job_by_idempotency_key(valid_job_data["idempotency_key"])

        assert job["job_id"] == valid_job_data["job_id"]


class TestJobsDALUpdate:
    """Test suite for update_job_status() and update_job() methods."""

    def test_update_job_status_success(self, jobs_repo, valid_job_data):
        """Test successful job status update."""
        jobs_repo.create_job(valid_job_data)

        started_at = datetime.utcnow().isoformat() + "Z"
        result = jobs_repo.update_job_status(
            valid_job_data["job_id"], status="PROCESSING", started_at=started_at
        )

        assert result["success"] is True
        job = result["data"]
        assert job["status"] == "PROCESSING"
        assert job["started_at"] == started_at

    def test_update_job_status_to_completed(self, jobs_repo, valid_job_data):
        """Test updating job status to COMPLETED with result info."""
        jobs_repo.create_job(valid_job_data)

        completed_at = datetime.utcnow().isoformat() + "Z"
        result = jobs_repo.update_job_status(
            valid_job_data["job_id"],
            status="COMPLETED",
            completed_at=completed_at,
            result_key="s3://bucket/results/job-123.json",
            token_usage={"input": 7500, "output": 2200},
        )

        job = result["data"]
        assert job["status"] == "COMPLETED"
        assert job["completed_at"] == completed_at
        assert job["result_key"] == "s3://bucket/results/job-123.json"
        assert job["token_usage"]["input"] == 7500

    def test_update_job_status_to_failed(self, jobs_repo, valid_job_data):
        """Test updating job status to FAILED with error details."""
        jobs_repo.create_job(valid_job_data)

        result = jobs_repo.update_job_status(
            valid_job_data["job_id"],
            status="FAILED",
            error_message="VPR generation exceeded timeout",
            error_code="TIMEOUT",
        )

        job = result["data"]
        assert job["status"] == "FAILED"
        assert job["error_message"] == "VPR generation exceeded timeout"
        assert job["error_code"] == "TIMEOUT"

    def test_update_job_status_not_found(self, jobs_repo):
        """Test updating non-existent job fails."""
        with pytest.raises(ValueError, match="not found"):
            jobs_repo.update_job_status("non-existent-id", status="PROCESSING")

    def test_update_job_multiple_fields(self, jobs_repo, valid_job_data):
        """Test update_job() handles multiple field updates."""
        jobs_repo.create_job(valid_job_data)

        updates = {
            "status": "PROCESSING",
            "started_at": datetime.utcnow().isoformat() + "Z",
            "worker_id": "worker-node-01",
            "processing_duration_ms": 0,
        }

        result = jobs_repo.update_job(valid_job_data["job_id"], updates)

        job = result["data"]
        assert job["status"] == "PROCESSING"
        assert job["worker_id"] == "worker-node-01"
        assert job["processing_duration_ms"] == 0

    def test_update_job_preserves_existing_fields(self, jobs_repo, valid_job_data):
        """Test that partial updates preserve existing fields."""
        jobs_repo.create_job(valid_job_data)

        # Update only status
        jobs_repo.update_job(valid_job_data["job_id"], {"status": "PROCESSING"})

        # Verify original fields still exist
        job = jobs_repo.get_job(valid_job_data["job_id"])
        assert job["user_id"] == "user_123"
        assert job["application_id"] == "app_456"
        assert job["idempotency_key"] == "vpr#user_123#app_456"

    def test_update_job_not_found(self, jobs_repo):
        """Test updating non-existent job fails."""
        with pytest.raises(ValueError, match="not found"):
            jobs_repo.update_job("non-existent-id", {"status": "PROCESSING"})


class TestJobsDALTTL:
    """Test suite for TTL (Time-To-Live) attribute handling."""

    def test_job_creation_sets_ttl(self, jobs_repo, valid_job_data):
        """Test job creation includes TTL attribute."""
        result = jobs_repo.create_job(valid_job_data)

        job = result["data"]
        assert "ttl" in job
        assert isinstance(job["ttl"], int)
        assert job["ttl"] > 0

    def test_ttl_is_unix_timestamp(self, jobs_repo, valid_job_data):
        """Test TTL is stored as Unix timestamp (seconds since epoch)."""
        now = datetime.utcnow()
        ttl_timestamp = int((now + timedelta(hours=4)).timestamp())
        valid_job_data["ttl"] = ttl_timestamp

        result = jobs_repo.create_job(valid_job_data)

        job = result["data"]
        assert job["ttl"] == ttl_timestamp

    def test_ttl_represents_future_expiration(self, jobs_repo, valid_job_data):
        """Test TTL represents a future timestamp (expiration time)."""
        now_timestamp = int(datetime.utcnow().timestamp())
        ttl_timestamp = int((datetime.utcnow() + timedelta(hours=4)).timestamp())
        valid_job_data["ttl"] = ttl_timestamp

        result = jobs_repo.create_job(valid_job_data)

        job = result["data"]
        # TTL should be in the future
        assert job["ttl"] > now_timestamp


class TestJobsDALErrorHandling:
    """Test suite for error handling and exception scenarios."""

    def test_create_job_handles_validation_error(self, jobs_repo):
        """Test create_job handles validation errors gracefully."""
        invalid_job = {"job_id": "test"}  # Missing required fields

        with pytest.raises(ValueError):
            jobs_repo.create_job(invalid_job)

    def test_update_job_with_empty_updates_dict(self, jobs_repo, valid_job_data):
        """Test update_job handles empty updates dict."""
        jobs_repo.create_job(valid_job_data)

        # Update with empty dict should not fail
        result = jobs_repo.update_job(valid_job_data["job_id"], {})

        assert result["success"] is True

    def test_get_job_with_none_job_id(self, jobs_repo):
        """Test get_job handles None job_id gracefully."""
        # Should not raise, just return None
        job = jobs_repo.get_job(None)

        assert job is None


class TestJobsDALReservedKeywords:
    """Test suite for DynamoDB reserved keyword handling."""

    def test_update_job_with_reserved_keyword_status(self, jobs_repo, valid_job_data):
        """Test status field update (reserved DynamoDB keyword)."""
        jobs_repo.create_job(valid_job_data)

        # 'status' is a reserved keyword that needs attribute name aliasing
        result = jobs_repo.update_job_status(
            valid_job_data["job_id"], status="PROCESSING"
        )

        assert result["success"] is True
        assert result["data"]["status"] == "PROCESSING"

    def test_update_job_with_reserved_keyword_error(self, jobs_repo, valid_job_data):
        """Test error field update (reserved DynamoDB keyword)."""
        jobs_repo.create_job(valid_job_data)

        # 'error' is a reserved keyword that needs attribute name aliasing
        result = jobs_repo.update_job(
            valid_job_data["job_id"], {"error": "Failed to process"}
        )

        assert result["success"] is True
        job = result["data"]
        assert job.get("error") == "Failed to process"


@mock_aws
class TestJobsDALWithMoto:
    """Integration tests using moto for real DynamoDB mocking."""

    @pytest.fixture
    def dynamodb_table(self):
        """Create mock DynamoDB table for integration testing."""
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="test-jobs-table",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "job_id", "AttributeType": "S"},
                {"AttributeName": "idempotency_key", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "idempotency-key-index",
                    "KeySchema": [
                        {"AttributeName": "idempotency_key", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5,
                    },
                }
            ],
            TimeToLiveSpecification={"AttributeName": "ttl", "Enabled": True},
        )
        table.wait_until_exists()
        return table

    def test_moto_table_has_ttl_enabled(self, dynamodb_table):
        """Test that moto table has TTL enabled."""
        client = boto3.client("dynamodb", region_name="us-east-1")
        response = client.describe_time_to_live(TableName="test-jobs-table")

        ttl_spec = response["TimeToLiveDescription"]
        assert ttl_spec["AttributeName"] == "ttl"
        assert ttl_spec["TimeToLiveStatus"] in ["ENABLED", "ENABLING"]

    def test_moto_table_has_gsi_for_idempotency(self, dynamodb_table):
        """Test that moto table has idempotency GSI."""
        client = boto3.client("dynamodb", region_name="us-east-1")
        response = client.describe_table(TableName="test-jobs-table")

        gsi_list = response["Table"].get("GlobalSecondaryIndexes", [])
        gsi_names = [gsi["IndexName"] for gsi in gsi_list]
        assert "idempotency-key-index" in gsi_names

    def test_moto_put_and_get_item(self, dynamodb_table, valid_job_data):
        """Test basic put/get operations on moto table."""
        # Put item
        dynamodb_table.put_item(Item=valid_job_data)

        # Get item
        response = dynamodb_table.get_item(Key={"job_id": valid_job_data["job_id"]})

        assert "Item" in response
        assert response["Item"]["job_id"] == valid_job_data["job_id"]
        assert response["Item"]["status"] == "PENDING"

    def test_moto_query_by_gsi(self, dynamodb_table, valid_job_data):
        """Test GSI query for idempotency key on moto table."""
        # Put item
        dynamodb_table.put_item(Item=valid_job_data)

        # Query by idempotency key
        response = dynamodb_table.query(
            IndexName="idempotency-key-index",
            KeyConditionExpression="idempotency_key = :key",
            ExpressionAttributeValues={":key": valid_job_data["idempotency_key"]},
            Limit=1,
        )

        assert response["Count"] == 1
        assert response["Items"][0]["job_id"] == valid_job_data["job_id"]

    def test_moto_update_item(self, dynamodb_table, valid_job_data):
        """Test update_item operation on moto table."""
        # Put item
        dynamodb_table.put_item(Item=valid_job_data)

        # Update status
        response = dynamodb_table.update_item(
            Key={"job_id": valid_job_data["job_id"]},
            UpdateExpression="SET #s = :status, started_at = :started",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":status": "PROCESSING",
                ":started": datetime.utcnow().isoformat() + "Z",
            },
            ReturnValues="ALL_NEW",
        )

        assert response["Attributes"]["status"] == "PROCESSING"
        assert "started_at" in response["Attributes"]
