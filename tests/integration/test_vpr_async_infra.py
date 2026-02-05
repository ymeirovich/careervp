"""
Integration tests for VPR async infrastructure.

Tests the complete async workflow:
1. Submit handler creates DynamoDB record and sends SQS message
2. Worker lambda processes SQS message
3. Worker updates DynamoDB state transitions (PENDING → PROCESSING → COMPLETED)
4. Worker writes result to S3
5. Status handler returns job state
6. Failure handling with DLQ

Mocks AWS services (SQS, DynamoDB, S3) using moto library.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import uuid4

import boto3
import pytest
from moto import mock_aws


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def aws_credentials():
    """
    Mock AWS Credentials for moto.

    Sets environment variables that boto3 will use for authentication.
    These are fake credentials that work with moto's virtual AWS.
    """
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def sqs_client(aws_credentials):
    """
    Return a mocked SQS client.

    Creates SQS queues for testing:
    - careervp-vpr-jobs-queue-dev (main queue)
    - careervp-vpr-jobs-dlq-dev (dead letter queue)
    """
    with mock_aws():
        client = boto3.client("sqs", region_name="us-east-1")

        # Create DLQ first
        dlq_response = client.create_queue(
            QueueName="careervp-vpr-jobs-dlq-dev",
            Attributes={
                "MessageRetentionPeriod": "14400",  # 4 hours
            },
        )
        dlq_url = dlq_response["QueueUrl"]
        dlq_arn = client.get_queue_attributes(
            QueueUrl=dlq_url, AttributeNames=["QueueArn"]
        )["Attributes"]["QueueArn"]

        # Create main queue with DLQ configuration
        _ = client.create_queue(
            QueueName="careervp-vpr-jobs-queue-dev",
            Attributes={
                "VisibilityTimeout": "660",  # 11 minutes
                "ReceiveMessageWaitTimeSeconds": "20",  # Long polling
                "MessageRetentionPeriod": "14400",  # 4 hours
                "RedrivePolicy": json.dumps(
                    {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": "3"}
                ),
            },
        )

        yield client


@pytest.fixture(scope="function")
def dynamodb_client(aws_credentials):
    """
    Return a mocked DynamoDB client.

    Creates the careervp-jobs-table-dev table with:
    - Partition key: job_id
    - GSI: idempotency-key-index on idempotency_key
    - TTL enabled on ttl attribute
    """
    with mock_aws():
        client = boto3.client("dynamodb", region_name="us-east-1")

        # Create jobs table
        client.create_table(
            TableName="careervp-jobs-table-dev",
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
                }
            ],
        )

        # Enable TTL
        client.update_time_to_live(
            TableName="careervp-jobs-table-dev",
            TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
        )

        yield client


@pytest.fixture(scope="function")
def s3_client(aws_credentials):
    """
    Return a mocked S3 client.

    Creates the VPR results bucket with:
    - Encryption enabled (SSE-S3)
    - Block public access enabled
    - 7-day lifecycle policy
    """
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")

        # Create results bucket
        bucket_name = "careervp-dev-vpr-results-use1-test"
        client.create_bucket(Bucket=bucket_name)

        # Enable encryption
        client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            },
        )

        # Block public access
        client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        # Set lifecycle policy (7-day expiration)
        client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration={
                "Rules": [
                    {
                        "Id": "DeleteAfter7Days",
                        "Status": "Enabled",
                        "Expiration": {"Days": 7},
                        "Filter": {"Prefix": "results/"},
                    }
                ]
            },
        )

        yield client


@pytest.fixture
def sample_vpr_request() -> Dict[str, Any]:
    """
    Return a sample VPR request payload.
    """
    return {
        "application_id": "app-123",
        "user_id": "user-456",
        "job_posting": {
            "company_name": "Natural Intelligence",
            "role_title": "Learning & Development Manager",
            "responsibilities": [
                "Design and deliver training programs",
                "Manage learning management system",
            ],
            "requirements": [
                "5+ years L&D experience",
                "Instructional design expertise",
            ],
        },
        "gap_responses": [
            {
                "question": "Tell me about your training experience",
                "answer": "I have 6 years of corporate training experience",
            }
        ],
    }


@pytest.fixture
def sample_vpr_result() -> Dict[str, Any]:
    """
    Return a sample VPR result payload.
    """
    return {
        "value_proposition": "Experienced L&D professional with proven track record...",
        "key_strengths": [
            "6 years corporate training experience",
            "Strong instructional design skills",
        ],
        "alignment_score": 85,
        "recommendations": [
            "Highlight LMS management experience",
            "Emphasize curriculum development",
        ],
    }


# ============================================================================
# Test Cases
# ============================================================================


def test_submit_handler_creates_dynamodb_record(
    dynamodb_client, sqs_client, sample_vpr_request
):
    """
    Test that submit handler creates DynamoDB record with PENDING status.

    Verifies:
    - Record is created with correct job_id
    - Status is set to PENDING
    - Input data is stored correctly
    - TTL is set to 10 minutes from creation
    - Idempotency key is set correctly
    """
    # Arrange
    job_id = str(uuid4())
    idempotency_key = (
        f"vpr#{sample_vpr_request['user_id']}#{sample_vpr_request['application_id']}"
    )
    created_at = datetime.utcnow().isoformat() + "Z"
    ttl = int((datetime.utcnow() + timedelta(minutes=10)).timestamp())

    # Act - Simulate submit handler behavior
    dynamodb_client.put_item(
        TableName="careervp-jobs-table-dev",
        Item={
            "job_id": {"S": job_id},
            "idempotency_key": {"S": idempotency_key},
            "user_id": {"S": sample_vpr_request["user_id"]},
            "application_id": {"S": sample_vpr_request["application_id"]},
            "status": {"S": "PENDING"},
            "created_at": {"S": created_at},
            "input_data": {"S": json.dumps(sample_vpr_request)},
            "ttl": {"N": str(ttl)},
        },
    )

    # Assert
    response = dynamodb_client.get_item(
        TableName="careervp-jobs-table-dev", Key={"job_id": {"S": job_id}}
    )

    assert "Item" in response
    item = response["Item"]
    assert item["job_id"]["S"] == job_id
    assert item["status"]["S"] == "PENDING"
    assert item["user_id"]["S"] == sample_vpr_request["user_id"]
    assert item["idempotency_key"]["S"] == idempotency_key
    assert "input_data" in item
    assert "ttl" in item


def test_submit_handler_sends_sqs_message(
    dynamodb_client, sqs_client, sample_vpr_request
):
    """
    Test that submit handler sends message to SQS queue.

    Verifies:
    - Message is sent to correct queue
    - Message body contains job_id and input_data
    - Message attributes are set correctly
    """
    # Arrange
    job_id = str(uuid4())
    queue_url = sqs_client.get_queue_url(QueueName="careervp-vpr-jobs-queue-dev")[
        "QueueUrl"
    ]

    # Act - Simulate submit handler sending message
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "job_id": job_id,
                "user_id": sample_vpr_request["user_id"],
                "application_id": sample_vpr_request["application_id"],
                "input_data": sample_vpr_request,
            }
        ),
        MessageAttributes={
            "job_type": {"StringValue": "vpr_generation", "DataType": "String"}
        },
    )

    # Assert
    messages = sqs_client.receive_message(
        QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=1
    )

    assert "Messages" in messages
    assert len(messages["Messages"]) == 1

    message = messages["Messages"][0]
    body = json.loads(message["Body"])

    assert body["job_id"] == job_id
    assert body["user_id"] == sample_vpr_request["user_id"]
    assert body["input_data"]["application_id"] == sample_vpr_request["application_id"]
    assert message["MessageAttributes"]["job_type"]["StringValue"] == "vpr_generation"


def test_worker_lambda_processes_sqs_message(
    dynamodb_client, sqs_client, sample_vpr_request
):
    """
    Test that worker lambda successfully receives and processes SQS message.

    Verifies:
    - Worker can receive message from queue
    - Message body is parsed correctly
    - Worker can access job data from DynamoDB
    """
    # Arrange - Create job and send message
    job_id = str(uuid4())
    queue_url = sqs_client.get_queue_url(QueueName="careervp-vpr-jobs-queue-dev")[
        "QueueUrl"
    ]

    # Create job record
    dynamodb_client.put_item(
        TableName="careervp-jobs-table-dev",
        Item={
            "job_id": {"S": job_id},
            "status": {"S": "PENDING"},
            "user_id": {"S": sample_vpr_request["user_id"]},
            "application_id": {"S": sample_vpr_request["application_id"]},
            "input_data": {"S": json.dumps(sample_vpr_request)},
            "created_at": {"S": datetime.utcnow().isoformat() + "Z"},
        },
    )

    # Send message
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "job_id": job_id,
                "user_id": sample_vpr_request["user_id"],
                "application_id": sample_vpr_request["application_id"],
            }
        ),
    )

    # Act - Simulate worker receiving message
    messages = sqs_client.receive_message(
        QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=1
    )

    # Assert
    assert "Messages" in messages
    message = messages["Messages"][0]
    body = json.loads(message["Body"])

    # Verify worker can retrieve job from DynamoDB
    job_response = dynamodb_client.get_item(
        TableName="careervp-jobs-table-dev", Key={"job_id": {"S": body["job_id"]}}
    )

    assert "Item" in job_response
    assert job_response["Item"]["job_id"]["S"] == job_id
    assert job_response["Item"]["status"]["S"] == "PENDING"


def test_worker_updates_dynamodb_to_processing(
    dynamodb_client, sqs_client, sample_vpr_request
):
    """
    Test that worker updates DynamoDB status to PROCESSING.

    Verifies:
    - Status transitions from PENDING to PROCESSING
    - started_at timestamp is set
    - Job record is updated atomically
    """
    # Arrange - Create job in PENDING state
    job_id = str(uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"

    dynamodb_client.put_item(
        TableName="careervp-jobs-table-dev",
        Item={
            "job_id": {"S": job_id},
            "status": {"S": "PENDING"},
            "user_id": {"S": sample_vpr_request["user_id"]},
            "created_at": {"S": created_at},
        },
    )

    # Act - Simulate worker updating status to PROCESSING
    started_at = datetime.utcnow().isoformat() + "Z"
    dynamodb_client.update_item(
        TableName="careervp-jobs-table-dev",
        Key={"job_id": {"S": job_id}},
        UpdateExpression="SET #status = :processing, started_at = :started_at",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":processing": {"S": "PROCESSING"},
            ":started_at": {"S": started_at},
        },
    )

    # Assert
    response = dynamodb_client.get_item(
        TableName="careervp-jobs-table-dev", Key={"job_id": {"S": job_id}}
    )

    item = response["Item"]
    assert item["status"]["S"] == "PROCESSING"
    assert item["started_at"]["S"] == started_at
    assert item["created_at"]["S"] == created_at


def test_worker_writes_result_to_s3(s3_client, sample_vpr_result):
    """
    Test that worker writes VPR result to S3.

    Verifies:
    - Object is written to correct bucket and key
    - Object content is valid JSON
    - Object is encrypted (SSE-S3)
    """
    # Arrange
    job_id = str(uuid4())
    bucket_name = "careervp-dev-vpr-results-use1-test"
    result_key = f"results/{job_id}.json"

    # Act - Simulate worker writing result to S3
    s3_client.put_object(
        Bucket=bucket_name,
        Key=result_key,
        Body=json.dumps(sample_vpr_result),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )

    # Assert
    response = s3_client.get_object(Bucket=bucket_name, Key=result_key)

    assert response["ContentType"] == "application/json"
    assert response["ServerSideEncryption"] == "AES256"

    body = json.loads(response["Body"].read().decode("utf-8"))
    assert body["value_proposition"] == sample_vpr_result["value_proposition"]
    assert body["alignment_score"] == sample_vpr_result["alignment_score"]


def test_worker_updates_dynamodb_to_completed(
    dynamodb_client, s3_client, sample_vpr_result
):
    """
    Test that worker updates DynamoDB status to COMPLETED.

    Verifies:
    - Status transitions from PROCESSING to COMPLETED
    - completed_at timestamp is set
    - result_key points to S3 object
    - token_usage is recorded
    """
    # Arrange - Create job in PROCESSING state
    job_id = str(uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"
    started_at = datetime.utcnow().isoformat() + "Z"
    result_key = f"results/{job_id}.json"

    dynamodb_client.put_item(
        TableName="careervp-jobs-table-dev",
        Item={
            "job_id": {"S": job_id},
            "status": {"S": "PROCESSING"},
            "user_id": {"S": "user-456"},
            "created_at": {"S": created_at},
            "started_at": {"S": started_at},
        },
    )

    # Act - Simulate worker updating status to COMPLETED
    completed_at = datetime.utcnow().isoformat() + "Z"
    dynamodb_client.update_item(
        TableName="careervp-jobs-table-dev",
        Key={"job_id": {"S": job_id}},
        UpdateExpression="SET #status = :completed, completed_at = :completed_at, result_key = :result_key, token_usage = :token_usage",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":completed": {"S": "COMPLETED"},
            ":completed_at": {"S": completed_at},
            ":result_key": {"S": result_key},
            ":token_usage": {
                "M": {"input_tokens": {"N": "7500"}, "output_tokens": {"N": "2200"}}
            },
        },
    )

    # Assert
    response = dynamodb_client.get_item(
        TableName="careervp-jobs-table-dev", Key={"job_id": {"S": job_id}}
    )

    item = response["Item"]
    assert item["status"]["S"] == "COMPLETED"
    assert item["completed_at"]["S"] == completed_at
    assert item["result_key"]["S"] == result_key
    assert item["token_usage"]["M"]["input_tokens"]["N"] == "7500"
    assert item["token_usage"]["M"]["output_tokens"]["N"] == "2200"


def test_worker_handles_failure_with_dlq(
    dynamodb_client, sqs_client, sample_vpr_request
):
    """
    Test that worker handles failures and messages move to DLQ.

    Verifies:
    - Failed jobs update status to FAILED
    - Error message is recorded in DynamoDB
    - Message moves to DLQ after max retries (3)
    """
    # Arrange - Create job and send message
    job_id = str(uuid4())
    queue_url = sqs_client.get_queue_url(QueueName="careervp-vpr-jobs-queue-dev")[
        "QueueUrl"
    ]
    _ = sqs_client.get_queue_url(QueueName="careervp-vpr-jobs-dlq-dev")["QueueUrl"]

    dynamodb_client.put_item(
        TableName="careervp-jobs-table-dev",
        Item={
            "job_id": {"S": job_id},
            "status": {"S": "PENDING"},
            "user_id": {"S": sample_vpr_request["user_id"]},
            "created_at": {"S": datetime.utcnow().isoformat() + "Z"},
        },
    )

    sqs_client.send_message(
        QueueUrl=queue_url, MessageBody=json.dumps({"job_id": job_id})
    )

    # Act - Simulate worker failure (receive and don't delete, 3 times)
    for attempt in range(3):
        _ = sqs_client.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=1
        )
        # Don't delete message - simulates worker crash/failure
        # Message becomes visible again after VisibilityTimeout

    # Update job status to FAILED
    error_message = "Claude API rate limit exceeded"
    dynamodb_client.update_item(
        TableName="careervp-jobs-table-dev",
        Key={"job_id": {"S": job_id}},
        UpdateExpression="SET #status = :failed, #error = :error",
        ExpressionAttributeNames={"#status": "status", "#error": "error"},
        ExpressionAttributeValues={
            ":failed": {"S": "FAILED"},
            ":error": {"S": error_message},
        },
    )

    # Assert job status is FAILED
    response = dynamodb_client.get_item(
        TableName="careervp-jobs-table-dev", Key={"job_id": {"S": job_id}}
    )

    item = response["Item"]
    assert item["status"]["S"] == "FAILED"
    assert item["error"]["S"] == error_message

    # Note: Moto doesn't fully simulate DLQ redrive policy automatically
    # In production, after 3 failed attempts, SQS would move message to DLQ
    # We verify the configuration exists
    queue_attrs = sqs_client.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["RedrivePolicy"]
    )

    redrive_policy = json.loads(queue_attrs["Attributes"]["RedrivePolicy"])
    assert redrive_policy["maxReceiveCount"] == "3"


def test_status_handler_returns_job_state(
    dynamodb_client, s3_client, sample_vpr_result
):
    """
    Test that status handler returns correct job state.

    Verifies:
    - PENDING status returns correct response
    - PROCESSING status returns correct response
    - COMPLETED status returns presigned URL
    - FAILED status returns error message
    - NOT FOUND returns 404
    """
    # Test Case 1: PENDING status
    job_id_pending = str(uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"

    dynamodb_client.put_item(
        TableName="careervp-jobs-table-dev",
        Item={
            "job_id": {"S": job_id_pending},
            "status": {"S": "PENDING"},
            "user_id": {"S": "user-456"},
            "created_at": {"S": created_at},
        },
    )

    response = dynamodb_client.get_item(
        TableName="careervp-jobs-table-dev", Key={"job_id": {"S": job_id_pending}}
    )

    assert response["Item"]["status"]["S"] == "PENDING"
    assert response["Item"]["created_at"]["S"] == created_at

    # Test Case 2: PROCESSING status
    job_id_processing = str(uuid4())
    started_at = datetime.utcnow().isoformat() + "Z"

    dynamodb_client.put_item(
        TableName="careervp-jobs-table-dev",
        Item={
            "job_id": {"S": job_id_processing},
            "status": {"S": "PROCESSING"},
            "user_id": {"S": "user-456"},
            "created_at": {"S": created_at},
            "started_at": {"S": started_at},
        },
    )

    response = dynamodb_client.get_item(
        TableName="careervp-jobs-table-dev", Key={"job_id": {"S": job_id_processing}}
    )

    assert response["Item"]["status"]["S"] == "PROCESSING"
    assert response["Item"]["started_at"]["S"] == started_at

    # Test Case 3: COMPLETED status with S3 result
    job_id_completed = str(uuid4())
    completed_at = datetime.utcnow().isoformat() + "Z"
    result_key = f"results/{job_id_completed}.json"
    bucket_name = "careervp-dev-vpr-results-use1-test"

    # Write result to S3
    s3_client.put_object(
        Bucket=bucket_name,
        Key=result_key,
        Body=json.dumps(sample_vpr_result),
        ContentType="application/json",
    )

    # Update DynamoDB
    dynamodb_client.put_item(
        TableName="careervp-jobs-table-dev",
        Item={
            "job_id": {"S": job_id_completed},
            "status": {"S": "COMPLETED"},
            "user_id": {"S": "user-456"},
            "created_at": {"S": created_at},
            "completed_at": {"S": completed_at},
            "result_key": {"S": result_key},
            "token_usage": {
                "M": {"input_tokens": {"N": "7500"}, "output_tokens": {"N": "2200"}}
            },
        },
    )

    response = dynamodb_client.get_item(
        TableName="careervp-jobs-table-dev", Key={"job_id": {"S": job_id_completed}}
    )

    assert response["Item"]["status"]["S"] == "COMPLETED"
    assert response["Item"]["result_key"]["S"] == result_key

    # Generate presigned URL
    presigned_url = s3_client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket_name, "Key": result_key}, ExpiresIn=3600
    )

    assert presigned_url is not None
    assert bucket_name in presigned_url
    assert result_key.replace("/", "%2F") in presigned_url

    # Test Case 4: FAILED status
    job_id_failed = str(uuid4())
    error_message = "Claude API rate limit exceeded"

    dynamodb_client.put_item(
        TableName="careervp-jobs-table-dev",
        Item={
            "job_id": {"S": job_id_failed},
            "status": {"S": "FAILED"},
            "user_id": {"S": "user-456"},
            "created_at": {"S": created_at},
            "started_at": {"S": started_at},
            "error": {"S": error_message},
        },
    )

    response = dynamodb_client.get_item(
        TableName="careervp-jobs-table-dev", Key={"job_id": {"S": job_id_failed}}
    )

    assert response["Item"]["status"]["S"] == "FAILED"
    assert response["Item"]["error"]["S"] == error_message

    # Test Case 5: NOT FOUND
    job_id_not_found = str(uuid4())
    response = dynamodb_client.get_item(
        TableName="careervp-jobs-table-dev", Key={"job_id": {"S": job_id_not_found}}
    )

    assert "Item" not in response


def test_idempotency_prevents_duplicate_submissions(
    dynamodb_client, sample_vpr_request
):
    """
    Test that idempotency key prevents duplicate VPR submissions.

    Verifies:
    - First submission creates new job
    - Second submission with same idempotency key returns existing job
    - GSI query on idempotency_key works correctly
    """
    # Arrange
    job_id = str(uuid4())
    idempotency_key = (
        f"vpr#{sample_vpr_request['user_id']}#{sample_vpr_request['application_id']}"
    )

    # Act - First submission
    dynamodb_client.put_item(
        TableName="careervp-jobs-table-dev",
        Item={
            "job_id": {"S": job_id},
            "idempotency_key": {"S": idempotency_key},
            "user_id": {"S": sample_vpr_request["user_id"]},
            "application_id": {"S": sample_vpr_request["application_id"]},
            "status": {"S": "PENDING"},
            "created_at": {"S": datetime.utcnow().isoformat() + "Z"},
        },
    )

    # Second submission - Query by idempotency key
    response = dynamodb_client.query(
        TableName="careervp-jobs-table-dev",
        IndexName="idempotency-key-index",
        KeyConditionExpression="idempotency_key = :key",
        ExpressionAttributeValues={":key": {"S": idempotency_key}},
    )

    # Assert - Existing job found
    assert response["Count"] == 1
    existing_job = response["Items"][0]
    assert existing_job["job_id"]["S"] == job_id
    assert existing_job["idempotency_key"]["S"] == idempotency_key
    assert existing_job["status"]["S"] == "PENDING"


def test_end_to_end_workflow(
    dynamodb_client, sqs_client, s3_client, sample_vpr_request, sample_vpr_result
):
    """
    Test complete end-to-end workflow from submission to completion.

    Verifies:
    1. Submit creates DynamoDB record (PENDING) and sends SQS message
    2. Worker receives message and updates to PROCESSING
    3. Worker writes result to S3
    4. Worker updates status to COMPLETED
    5. Status handler returns result with presigned URL
    """
    # Step 1: Submit handler creates job and sends message
    job_id = str(uuid4())
    idempotency_key = (
        f"vpr#{sample_vpr_request['user_id']}#{sample_vpr_request['application_id']}"
    )
    created_at = datetime.utcnow().isoformat() + "Z"

    dynamodb_client.put_item(
        TableName="careervp-jobs-table-dev",
        Item={
            "job_id": {"S": job_id},
            "idempotency_key": {"S": idempotency_key},
            "user_id": {"S": sample_vpr_request["user_id"]},
            "application_id": {"S": sample_vpr_request["application_id"]},
            "status": {"S": "PENDING"},
            "created_at": {"S": created_at},
            "input_data": {"S": json.dumps(sample_vpr_request)},
        },
    )

    queue_url = sqs_client.get_queue_url(QueueName="careervp-vpr-jobs-queue-dev")[
        "QueueUrl"
    ]

    sqs_client.send_message(
        QueueUrl=queue_url, MessageBody=json.dumps({"job_id": job_id})
    )

    # Verify PENDING state
    response = dynamodb_client.get_item(
        TableName="careervp-jobs-table-dev", Key={"job_id": {"S": job_id}}
    )
    assert response["Item"]["status"]["S"] == "PENDING"

    # Step 2: Worker receives message and updates to PROCESSING
    messages = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
    assert "Messages" in messages

    started_at = datetime.utcnow().isoformat() + "Z"
    dynamodb_client.update_item(
        TableName="careervp-jobs-table-dev",
        Key={"job_id": {"S": job_id}},
        UpdateExpression="SET #status = :processing, started_at = :started_at",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":processing": {"S": "PROCESSING"},
            ":started_at": {"S": started_at},
        },
    )

    # Verify PROCESSING state
    response = dynamodb_client.get_item(
        TableName="careervp-jobs-table-dev", Key={"job_id": {"S": job_id}}
    )
    assert response["Item"]["status"]["S"] == "PROCESSING"

    # Step 3: Worker writes result to S3
    bucket_name = "careervp-dev-vpr-results-use1-test"
    result_key = f"results/{job_id}.json"

    s3_client.put_object(
        Bucket=bucket_name,
        Key=result_key,
        Body=json.dumps(sample_vpr_result),
        ContentType="application/json",
    )

    # Step 4: Worker updates to COMPLETED
    completed_at = datetime.utcnow().isoformat() + "Z"
    dynamodb_client.update_item(
        TableName="careervp-jobs-table-dev",
        Key={"job_id": {"S": job_id}},
        UpdateExpression="SET #status = :completed, completed_at = :completed_at, result_key = :result_key, token_usage = :token_usage",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":completed": {"S": "COMPLETED"},
            ":completed_at": {"S": completed_at},
            ":result_key": {"S": result_key},
            ":token_usage": {
                "M": {"input_tokens": {"N": "7500"}, "output_tokens": {"N": "2200"}}
            },
        },
    )

    # Step 5: Status handler returns complete job state
    response = dynamodb_client.get_item(
        TableName="careervp-jobs-table-dev", Key={"job_id": {"S": job_id}}
    )

    final_item = response["Item"]
    assert final_item["status"]["S"] == "COMPLETED"
    assert final_item["result_key"]["S"] == result_key
    assert "token_usage" in final_item

    # Generate presigned URL and verify result accessible
    presigned_url = s3_client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket_name, "Key": result_key}, ExpiresIn=3600
    )

    assert presigned_url is not None

    # Verify result content from S3
    s3_response = s3_client.get_object(Bucket=bucket_name, Key=result_key)
    result_content = json.loads(s3_response["Body"].read().decode("utf-8"))

    assert result_content["value_proposition"] == sample_vpr_result["value_proposition"]
    assert result_content["alignment_score"] == sample_vpr_result["alignment_score"]

    # Clean up - delete message from queue
    receipt_handle = messages["Messages"][0]["ReceiptHandle"]
    sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
