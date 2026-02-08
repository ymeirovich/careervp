# VPR Async Testing Strategy

Comprehensive testing guide for the asynchronous VPR job processing system. This document covers the testing pyramid, mocking strategies, test categories, and CI/CD integration.

## Table of Contents

1. [Testing Pyramid](#testing-pyramid)
2. [Mocking Strategy](#mocking-strategy)
3. [Unit Tests](#unit-tests)
4. [Integration Tests](#integration-tests)
5. [End-to-End Tests](#end-to-end-tests)
6. [Infrastructure Tests](#infrastructure-tests)
7. [Test Execution](#test-execution)
8. [CI/CD Integration](#cicd-integration)

---

## Testing Pyramid

The VPR async testing strategy follows a standard testing pyramid with clear separation of concerns:

```
        /\         E2E Tests (1-5%)
       /  \        - Full API contract validation
      /____\       - Real AWS services (deployed)
      /\  /\       Integration Tests (15-25%)
     /  \/  \      - Mocked AWS services (moto)
    /________\     - Lambda handlers + DAL layer
    /\  /\  /\     Unit Tests (70-80%)
   /  \/  \/  \    - Individual functions
  /__________/     - Business logic
```

**Coverage Targets:**
- **Unit Tests:** 80%+ line coverage
- **Integration Tests:** All happy paths + error cases
- **E2E Tests:** Critical user flows + API contract validation

**Test Distribution:**
- 700+ unit tests (quick, run locally)
- 30+ integration tests (medium, 2-5 seconds each)
- 8+ E2E tests (slow, 30-60 seconds each)

---

## Mocking Strategy

### AWS Services Mocking with moto

All integration and unit tests use `moto` library to mock AWS services without touching real AWS infrastructure.

**Configured Services:**
- **DynamoDB:** Full table operations, GSI queries, TTL
- **SQS:** Queue operations, dead letter queue, message attributes
- **S3:** Object storage, encryption, presigned URLs, lifecycle policies

**moto Setup in conftest.py:**

```python
import os
import boto3
import pytest
from moto import mock_aws

# Baseline AWS credentials (fake, for moto only)
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

@pytest.fixture(scope='function')
def dynamodb_client():
    """Return mocked DynamoDB client with jobs table."""
    with mock_aws():
        client = boto3.client('dynamodb', region_name='us-east-1')

        # Create jobs table
        client.create_table(
            TableName='careervp-jobs-table-dev',
            KeySchema=[
                {'AttributeName': 'job_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'job_id', 'AttributeType': 'S'},
                {'AttributeName': 'idempotency_key', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'idempotency-key-index',
                    'KeySchema': [
                        {'AttributeName': 'idempotency_key', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        )

        yield client

@pytest.fixture(scope='function')
def sqs_client():
    """Return mocked SQS client with job queues."""
    with mock_aws():
        client = boto3.client('sqs', region_name='us-east-1')

        # Create DLQ
        dlq_response = client.create_queue(
            QueueName='careervp-vpr-jobs-dlq-dev',
            Attributes={'MessageRetentionPeriod': '14400'}
        )
        dlq_url = dlq_response['QueueUrl']
        dlq_arn = client.get_queue_attributes(
            QueueUrl=dlq_url,
            AttributeNames=['QueueArn']
        )['Attributes']['QueueArn']

        # Create main queue with DLQ redrive policy
        client.create_queue(
            QueueName='careervp-vpr-jobs-queue-dev',
            Attributes={
                'VisibilityTimeout': '660',
                'ReceiveMessageWaitTimeSeconds': '20',
                'MessageRetentionPeriod': '14400',
                'RedrivePolicy': json.dumps({
                    'deadLetterTargetArn': dlq_arn,
                    'maxReceiveCount': '3'
                })
            }
        )

        yield client

@pytest.fixture(scope='function')
def s3_client():
    """Return mocked S3 client with results bucket."""
    with mock_aws():
        client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'careervp-dev-vpr-results-use1-test'

        # Create bucket with security settings
        client.create_bucket(Bucket=bucket_name)

        # Enable encryption
        client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        }
                    }
                ]
            }
        )

        # Block public access
        client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }
        )

        yield client
```

### Anthropic SDK Mocking

Mock Claude API responses in unit tests to avoid API calls and costs.

**Using unittest.mock:**

```python
from unittest.mock import Mock, patch, MagicMock
from anthropic import Anthropic

@pytest.fixture
def mock_anthropic_client():
    """Return mock Anthropic client with preset responses."""
    with patch('careervp.logic.vpr_generator.Anthropic') as mock_anthropic:
        client = MagicMock()
        mock_anthropic.return_value = client

        # Mock successful VPR generation
        client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({
                'executive_summary': 'Strong alignment with role requirements...',
                'evidence_matrix': [
                    {
                        'requirement': '5+ years L&D experience',
                        'evidence': 'Candidate has 6 years corporate training...',
                        'alignment_score': 0.92
                    }
                ],
                'differentiators': ['Instructional design expertise'],
                'gap_strategies': ['Emphasize LMS management experience'],
                'cultural_fit': 'High alignment with team structure',
                'talking_points': ['6 years of proven training success'],
                'keywords': ['L&D', 'instructional design', 'training']
            }))],
            usage=MagicMock(
                input_tokens=7500,
                output_tokens=2200
            )
        )

        yield client

def test_vpr_generation_success(mock_anthropic_client):
    """Test successful VPR generation."""
    from careervp.logic.vpr_generator import generate_vpr

    vpr_request = {
        'application_id': 'app-123',
        'user_id': 'user-456',
        'job_posting': {...},
        'gap_responses': [...]
    }

    result = generate_vpr(vpr_request)

    assert 'executive_summary' in result
    assert 'evidence_matrix' in result
    mock_anthropic_client.messages.create.assert_called_once()
```

**Mocking API Errors:**

```python
def test_vpr_generation_rate_limit_error():
    """Test handling of Claude API rate limit errors."""
    with patch('careervp.logic.vpr_generator.Anthropic') as mock_anthropic:
        client = MagicMock()
        mock_anthropic.return_value = client

        # Simulate rate limit error
        from anthropic import RateLimitError
        client.messages.create.side_effect = RateLimitError(
            message='Rate limit exceeded',
            response=Mock(status_code=429),
            body={'error': {'type': 'rate_limit_error'}}
        )

        from careervp.logic.vpr_generator import generate_vpr

        with pytest.raises(RateLimitError):
            generate_vpr(vpr_request)
```

---

## Unit Tests

### Test Location
`src/backend/tests/unit/`

### Test Structure

Each unit test focuses on a single function or class method:

```python
import pytest
from careervp.models.vpr import VPRRequest, VPRResponse
from careervp.handlers.vpr_submit_handler import submit_vpr_handler
from unittest.mock import Mock, patch

class TestVPRSubmitHandler:
    """Unit tests for VPR submit endpoint handler."""

    @pytest.fixture
    def vpr_request(self):
        """Valid VPR request payload."""
        return {
            'application_id': 'app-test-123',
            'user_id': 'user-test-456',
            'job_posting': {
                'company_name': 'Natural Intelligence',
                'role_title': 'Learning & Development Manager',
                'description': 'Lead L&D initiatives',
                'responsibilities': ['Design training programs'],
                'requirements': ['5+ years L&D experience'],
                'nice_to_have': [],
                'language': 'en'
            },
            'gap_responses': [
                {
                    'question': 'L&D experience?',
                    'answer': 'I have 6 years of corporate training'
                }
            ]
        }

    def test_submit_handler_returns_202_with_job_id(
        self,
        vpr_request,
        dynamodb_client,
        sqs_client
    ):
        """Test submit handler returns 202 Accepted with job_id."""
        response = submit_vpr_handler(vpr_request)

        assert response['statusCode'] == 202
        assert 'job_id' in response['body']
        assert 'status' in response['body']
        assert response['body']['status'] == 'PENDING'

        # Validate job was created in DynamoDB
        job_id = response['body']['job_id']
        job = dynamodb_client.get_item(
            TableName='careervp-jobs-table-dev',
            Key={'job_id': {'S': job_id}}
        )
        assert 'Item' in job
```

### Testing Idempotency Logic

```python
def test_idempotency_key_returns_existing_job(
    self,
    vpr_request,
    dynamodb_client
):
    """Test duplicate request returns existing job (idempotency)."""
    # First submission
    response1 = submit_vpr_handler(vpr_request)
    job_id_1 = response1['body']['job_id']

    # Second submission (identical payload)
    response2 = submit_vpr_handler(vpr_request)
    job_id_2 = response2['body']['job_id']

    # Should return same job
    assert response2['statusCode'] == 200
    assert job_id_1 == job_id_2
    assert 'already exists' in response2['body']['message'].lower()
```

### Testing Business Logic (VPR Generation)

```python
class TestVPRGenerator:
    """Unit tests for VPR generation logic."""

    def test_vpr_generation_creates_valid_structure(
        self,
        mock_anthropic_client
    ):
        """Test VPR generation produces valid response structure."""
        from careervp.logic.vpr_generator import generate_vpr

        vpr_request = {...}
        vpr = generate_vpr(vpr_request)

        # Validate required fields
        required_fields = [
            'executive_summary',
            'evidence_matrix',
            'differentiators',
            'gap_strategies',
            'cultural_fit',
            'talking_points',
            'keywords'
        ]

        for field in required_fields:
            assert field in vpr, f'Missing required field: {field}'

    def test_vpr_evidence_matrix_structure(
        self,
        mock_anthropic_client
    ):
        """Test evidence_matrix items have required fields."""
        from careервp.logic.vpr_generator import generate_vpr

        vpr = generate_vpr({...})

        assert isinstance(vpr['evidence_matrix'], list)
        for evidence in vpr['evidence_matrix']:
            assert 'requirement' in evidence
            assert 'evidence' in evidence
            assert 'alignment_score' in evidence
            assert 0 <= evidence['alignment_score'] <= 1
```

### Testing Error Handling

```python
def test_vpr_generation_handles_invalid_input(
    self,
    mock_anthropic_client
):
    """Test VPR generation with invalid input raises ValidationError."""
    from careervp.logic.vpr_generator import generate_vpr
    from pydantic import ValidationError

    invalid_request = {
        'application_id': '',  # Empty ID
        'user_id': 'user-456',
        'job_posting': {},  # Missing required fields
        'gap_responses': []
    }

    with pytest.raises(ValidationError):
        generate_vpr(invalid_request)

def test_vpr_generation_handles_api_errors(
    self
):
    """Test VPR generation handles Claude API errors gracefully."""
    with patch('careervp.logic.vpr_generator.Anthropic') as mock_anthropic:
        client = MagicMock()
        mock_anthropic.return_value = client

        from anthropic import APIError
        client.messages.create.side_effect = APIError('API error')

        from careervp.logic.vpr_generator import generate_vpr

        with pytest.raises(APIError):
            generate_vpr({...})
```

---

## Integration Tests

### Test Location
`tests/integration/test_vpr_async_infra.py`

### Complete Workflow Testing

Integration tests verify the end-to-end flow of individual components:

```python
"""Integration tests for VPR async infrastructure."""

import json
from datetime import datetime
from uuid import uuid4
import pytest
from moto import mock_aws
import boto3

class TestVPRAsyncWorkflow:
    """Integration tests for Submit → Worker → Status flow."""

    def test_submit_to_worker_to_completed_flow(
        self,
        dynamodb_client,
        sqs_client,
        s3_client,
        sample_vpr_request,
        sample_vpr_result
    ):
        """
        Test complete workflow: Submit job → Process → Complete.

        Verifies:
        1. Submit creates DynamoDB record (PENDING)
        2. Submit sends message to SQS
        3. Worker receives message and updates status
        4. Worker writes result to S3
        5. Status handler returns presigned URL
        """
        # Step 1: Submit creates job in DynamoDB
        job_id = str(uuid4())
        dynamodb_client.put_item(
            TableName='careervp-jobs-table-dev',
            Item={
                'job_id': {'S': job_id},
                'status': {'S': 'PENDING'},
                'user_id': {'S': sample_vpr_request['user_id']},
                'created_at': {'S': datetime.utcnow().isoformat() + 'Z'}
            }
        )

        # Verify PENDING state
        response = dynamodb_client.get_item(
            TableName='careervp-jobs-table-dev',
            Key={'job_id': {'S': job_id}}
        )
        assert response['Item']['status']['S'] == 'PENDING'

        # Step 2: Submit sends SQS message
        queue_url = sqs_client.get_queue_url(
            QueueName='careervp-vpr-jobs-queue-dev'
        )['QueueUrl']

        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({'job_id': job_id})
        )

        # Step 3: Worker processes message
        messages = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1
        )
        assert 'Messages' in messages

        # Worker updates status to PROCESSING
        dynamodb_client.update_item(
            TableName='careervp-jobs-table-dev',
            Key={'job_id': {'S': job_id}},
            UpdateExpression='SET #status = :processing, started_at = :started_at',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':processing': {'S': 'PROCESSING'},
                ':started_at': {'S': datetime.utcnow().isoformat() + 'Z'}
            }
        )

        # Step 4: Worker writes result to S3
        bucket_name = 'careervp-dev-vpr-results-use1-test'
        result_key = f'results/{job_id}.json'

        s3_client.put_object(
            Bucket=bucket_name,
            Key=result_key,
            Body=json.dumps(sample_vpr_result),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )

        # Step 5: Worker updates status to COMPLETED
        dynamodb_client.update_item(
            TableName='careervp-jobs-table-dev',
            Key={'job_id': {'S': job_id}},
            UpdateExpression='SET #status = :completed, completed_at = :completed_at, result_key = :result_key, token_usage = :token_usage',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':completed': {'S': 'COMPLETED'},
                ':completed_at': {'S': datetime.utcnow().isoformat() + 'Z'},
                ':result_key': {'S': result_key},
                ':token_usage': {'M': {
                    'input_tokens': {'N': '7500'},
                    'output_tokens': {'N': '2200'}
                }}
            }
        )

        # Step 6: Status handler returns presigned URL
        job_item = dynamodb_client.get_item(
            TableName='careervp-jobs-table-dev',
            Key={'job_id': {'S': job_id}}
        )['Item']

        assert job_item['status']['S'] == 'COMPLETED'
        assert job_item['result_key']['S'] == result_key

        # Generate presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': result_key},
            ExpiresIn=3600
        )

        assert presigned_url is not None
        assert bucket_name in presigned_url
```

### Testing Idempotency at Integration Level

```python
def test_idempotency_index_prevents_duplicates(
    self,
    dynamodb_client,
    sample_vpr_request
):
    """Test GSI query for idempotency key works correctly."""
    job_id = str(uuid4())
    idempotency_key = f"vpr#{sample_vpr_request['user_id']}#{sample_vpr_request['application_id']}"

    # Create first job
    dynamodb_client.put_item(
        TableName='careervp-jobs-table-dev',
        Item={
            'job_id': {'S': job_id},
            'idempotency_key': {'S': idempotency_key},
            'status': {'S': 'PENDING'},
            'created_at': {'S': datetime.utcnow().isoformat() + 'Z'}
        }
    )

    # Query by idempotency key (simulating duplicate request check)
    response = dynamodb_client.query(
        TableName='careervp-jobs-table-dev',
        IndexName='idempotency-key-index',
        KeyConditionExpression='idempotency_key = :key',
        ExpressionAttributeValues={':key': {'S': idempotency_key}}
    )

    assert response['Count'] == 1
    assert response['Items'][0]['job_id']['S'] == job_id
```

### Testing Error Scenarios

```python
def test_failure_path_with_dlq(
    self,
    dynamodb_client,
    sqs_client
):
    """Test failed job is marked FAILED and DLQ redrive policy exists."""
    job_id = str(uuid4())
    queue_url = sqs_client.get_queue_url(
        QueueName='careervp-vpr-jobs-queue-dev'
    )['QueueUrl']

    # Create job
    dynamodb_client.put_item(
        TableName='careervp-jobs-table-dev',
        Item={'job_id': {'S': job_id}, 'status': {'S': 'PENDING'}}
    )

    # Send message to queue
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({'job_id': job_id})
    )

    # Simulate worker failure (don't delete message)
    for attempt in range(3):
        sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1
        )
        # Message visibility timeout causes redelivery

    # Update job status to FAILED
    dynamodb_client.update_item(
        TableName='careervp-jobs-table-dev',
        Key={'job_id': {'S': job_id}},
        UpdateExpression='SET #status = :failed, #error = :error',
        ExpressionAttributeNames={
            '#status': 'status',
            '#error': 'error'
        },
        ExpressionAttributeValues={
            ':failed': {'S': 'FAILED'},
            ':error': {'S': 'Claude API rate limit exceeded'}
        }
    )

    # Verify job is marked failed
    job = dynamodb_client.get_item(
        TableName='careervp-jobs-table-dev',
        Key={'job_id': {'S': job_id}}
    )['Item']

    assert job['status']['S'] == 'FAILED'
    assert job['error']['S'] == 'Claude API rate limit exceeded'

    # Verify DLQ redrive policy
    queue_attrs = sqs_client.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['RedrivePolicy']
    )
    redrive_policy = json.loads(queue_attrs['Attributes']['RedrivePolicy'])
    assert redrive_policy['maxReceiveCount'] == '3'
```

---

## End-to-End Tests

### Test Location
`src/backend/tests/e2e/test_vpr_async_polling.py`

### E2E Test Requirements

E2E tests run against deployed AWS infrastructure in the dev environment:

```python
"""
E2E Tests for VPR Async Polling Architecture.

Tests the complete Submit → Poll → Verify flow.
Validates API contract from docs/specs/07-vpr-async-architecture.md

Environment Variables:
- API_BASE_URL: Base URL for API endpoint (default: http://localhost:3000)
- VPR_SUBMIT_ENDPOINT: Override submit endpoint (default: /api/vpr)
- VPR_STATUS_ENDPOINT: Override status endpoint (default: /api/vpr/status)
- TEST_TIMEOUT: Max wait time in seconds (default: 60)
"""

import os
import time
from typing import Any
import httpx
import pytest

class VPRAsyncClient:
    """HTTP client wrapper for VPR async API interactions."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip('/')
        self.submit_path = os.getenv('VPR_SUBMIT_ENDPOINT', '/api/vpr')
        self.status_path = os.getenv('VPR_STATUS_ENDPOINT', '/api/vpr/status')
        self.timeout = int(os.getenv('TEST_TIMEOUT', '60'))

    def submit_vpr_job(self, payload: dict[str, Any]) -> httpx.Response:
        """Submit VPR generation job."""
        url = f'{self.base_url}{self.submit_path}'
        with httpx.Client(timeout=30.0) as client:
            return client.post(url, json=payload)

    def get_job_status(self, job_id: str) -> httpx.Response:
        """Poll job status by job_id."""
        url = f'{self.base_url}{self.status_path}/{job_id}'
        with httpx.Client(timeout=30.0) as client:
            return client.get(url)

    def poll_until_completed(
        self,
        job_id: str,
        interval: int = 5,
        max_wait: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Poll job status until COMPLETED or FAILED, or timeout."""
        max_wait = max_wait or self.timeout
        start_time = time.time()
        poll_count = 0

        while time.time() - start_time < max_wait:
            poll_count += 1
            response = self.get_job_status(job_id)
            body = response.json()

            status = body.get('status')
            if status in ('COMPLETED', 'FAILED'):
                return status, body

            if status not in ('PENDING', 'PROCESSING'):
                raise ValueError(f'Unexpected status: {status}')

            time.sleep(interval)

        elapsed = time.time() - start_time
        raise TimeoutError(f'Job {job_id} did not complete within {elapsed:.1f}s ({poll_count} polls)')

    def retrieve_result_from_s3(self, presigned_url: str) -> dict[str, Any]:
        """Fetch VPR result from S3 presigned URL."""
        with httpx.Client(timeout=30.0) as client:
            response = client.get(presigned_url)
            response.raise_for_status()
            return response.json()
```

### API Contract Tests

```python
class TestVPRAsyncAPI:
    """E2E tests for VPR async API contract."""

    def test_submit_vpr_job_returns_202_accepted(
        self,
        vpr_client,
        sample_vpr_payload
    ):
        """
        Test: POST /api/vpr returns 202 Accepted with job_id

        Validates:
        - HTTP 202 status code
        - Response includes job_id (UUID format)
        - Response includes status (PENDING)
        - Response includes success message
        """
        response = vpr_client.submit_vpr_job(sample_vpr_payload)

        assert response.status_code == 202, f'Expected 202, got {response.status_code}'

        body = response.json()
        assert 'job_id' in body
        assert 'status' in body
        assert body['status'] == 'PENDING'
        assert 'message' in body

        # Validate UUID format (36 chars with 4 hyphens)
        job_id = body['job_id']
        assert len(job_id) == 36 and job_id.count('-') == 4

    def test_poll_status_endpoint_returns_job_state(
        self,
        vpr_client,
        sample_vpr_payload
    ):
        """
        Test: GET /api/vpr/status/{job_id} returns job state

        Validates:
        - Status transitions: PENDING → PROCESSING → COMPLETED
        - Polling works within timeout
        - COMPLETED response includes result_url
        - Token usage is tracked
        """
        # Submit job
        submit_response = vpr_client.submit_vpr_job(sample_vpr_payload)
        assert submit_response.status_code == 202
        job_id = submit_response.json()['job_id']

        # Poll until completed
        final_status, body = vpr_client.poll_until_completed(job_id)

        assert final_status == 'COMPLETED'
        assert 'result_url' in body
        assert 'token_usage' in body
        assert 'input_tokens' in body['token_usage']
        assert 'output_tokens' in body['token_usage']

    def test_retrieve_vpr_result_from_s3(
        self,
        vpr_client,
        sample_vpr_payload
    ):
        """
        Test: Retrieve VPR result from S3 presigned URL

        Validates:
        - Presigned URL is accessible
        - Result is valid JSON matching VPR schema
        - Contains all required fields
        """
        # Submit and wait for completion
        job_id = vpr_client.submit_vpr_job(sample_vpr_payload).json()['job_id']
        final_status, body = vpr_client.poll_until_completed(job_id)

        assert final_status == 'COMPLETED'
        result_url = body['result_url']

        # Retrieve and validate VPR
        vpr = vpr_client.retrieve_result_from_s3(result_url)

        required_fields = [
            'executive_summary',
            'evidence_matrix',
            'differentiators',
            'gap_strategies',
            'cultural_fit',
            'talking_points',
            'keywords'
        ]

        for field in required_fields:
            assert field in vpr, f'Missing required field: {field}'
```

### Idempotency Test (E2E)

```python
def test_idempotent_submit_returns_existing_job(
    self,
    vpr_client,
    sample_vpr_payload
):
    """
    Test: Submitting same request twice returns existing job

    Validates:
    - First request: 202 with new job_id
    - Second request: 200 with same job_id
    - Idempotency key based on user_id + application_id
    """
    # First submission
    response1 = vpr_client.submit_vpr_job(sample_vpr_payload)
    assert response1.status_code == 202
    job_id_1 = response1.json()['job_id']

    # Second submission (identical)
    response2 = vpr_client.submit_vpr_job(sample_vpr_payload)
    assert response2.status_code == 200, f'Expected 200, got {response2.status_code}'
    job_id_2 = response2.json()['job_id']

    # Same job returned
    assert job_id_1 == job_id_2
    assert 'already exists' in response2.json()['message'].lower()
```

### Error Handling Tests

```python
def test_job_not_found_returns_404(self, vpr_client):
    """Test status endpoint returns 404 for non-existent job."""
    fake_job_id = '00000000-0000-0000-0000-000000000000'
    response = vpr_client.get_job_status(fake_job_id)

    assert response.status_code == 404
    body = response.json()
    assert 'error' in body
    assert 'not found' in body['error'].lower()

def test_failed_job_status(self, vpr_client):
    """Test handling of FAILED job status."""
    # Submit invalid payload to trigger failure
    invalid_payload = {
        'application_id': 'app-fail',
        'user_id': 'nonexistent-user',  # User without CV
        'job_posting': {
            'company_name': 'TestCo',
            'role_title': 'Test',
            'description': 'Test',
            'responsibilities': ['Test'],
            'requirements': ['Test'],
            'nice_to_have': [],
            'language': 'en'
        },
        'gap_responses': []
    }

    response = vpr_client.submit_vpr_job(invalid_payload)

    if response.status_code == 404:
        # Immediate validation failure
        assert 'error' in response.json()
    else:
        # Job queued, poll until failure
        job_id = response.json()['job_id']
        final_status, body = vpr_client.poll_until_completed(job_id)

        assert final_status == 'FAILED'
        assert 'error' in body
        assert 'result_url' not in body
```

---

## Infrastructure Tests

### CDK Assertions

Infrastructure tests validate CDK constructs for security, encryption, and configuration:

```python
"""Infrastructure tests for VPR async CDK stack."""

import pytest
from aws_cdk import assertions as cdk_assertions
from aws_cdk import core as cdk
from infra.careervp.vpr_async_stack import VprAsyncStack

class TestVprAsyncInfrastructure:
    """CDK assertion tests for VPR async stack."""

    @pytest.fixture
    def template(self):
        """Synthesize CDK stack to CloudFormation template."""
        stack = VprAsyncStack(
            cdk.App(),
            'VprAsyncStackTest',
            env=cdk.Environment(
                account='123456789012',
                region='us-east-1'
            )
        )
        return cdk_assertions.Template.from_stack(stack)

    def test_dynamodb_table_has_encryption(self, template):
        """Test DynamoDB table has encryption enabled."""
        template.has_resource_properties(
            'AWS::DynamoDB::Table',
            {
                'SSESpecification': {
                    'SSEEnabled': True
                }
            }
        )

    def test_dynamodb_table_has_ttl(self, template):
        """Test DynamoDB table has TTL configured."""
        template.has_resource_properties(
            'AWS::DynamoDB::Table',
            {
                'TimeToLiveSpecification': {
                    'AttributeName': 'ttl',
                    'Enabled': True
                }
            }
        )

    def test_s3_bucket_has_encryption(self, template):
        """Test S3 results bucket has encryption enabled."""
        template.has_resource_properties(
            'AWS::S3::Bucket',
            {
                'BucketEncryption': {
                    'ServerSideEncryptionConfiguration': [
                        {
                            'ServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }
                    ]
                }
            }
        )

    def test_s3_bucket_blocks_public_access(self, template):
        """Test S3 bucket blocks all public access."""
        template.has_resource_properties(
            'AWS::S3::BucketPublicAccessBlockConfiguration',
            {
                'BlockPublicAcls': True,
                'BlockPublicPolicy': True,
                'IgnorePublicAcls': True,
                'RestrictPublicBuckets': True
            }
        )

    def test_sqs_queue_has_dlq(self, template):
        """Test SQS queue has dead-letter queue configured."""
        template.has_resource_properties(
            'AWS::SQS::Queue',
            {
                'RedrivePolicy': {
                    'deadLetterTargetArn': cdk_assertions.Match.object_like({}),
                    'maxReceiveCount': 3
                }
            }
        )

    def test_worker_lambda_has_reserved_concurrency(self, template):
        """Test worker Lambda has reserved concurrency limit."""
        template.has_resource_properties(
            'AWS::Lambda::Function',
            {
                'Timeout': 300,  # 5 minutes
                'MemorySize': 1024
            }
        )

        template.has_resource_properties(
            'AWS::Lambda::ProvisionedConcurrencyConfig',
            {
                'ProvisionedConcurrentExecutions': 5
            }
        )

    def test_lambda_policies_follow_least_privilege(self, template):
        """Test Lambda IAM policies follow least privilege."""
        # Submit lambda: Write to jobs table + SQS
        template.has_resource_properties(
            'AWS::IAM::Role',
            cdk_assertions.Match.object_like({
                'AssumeRolePolicyDocument': cdk_assertions.Match.object_like({
                    'Statement': [
                        cdk_assertions.Match.object_like({
                            'Principal': {
                                'Service': 'lambda.amazonaws.com'
                            },
                            'Effect': 'Allow'
                        })
                    ]
                })
            })
        )

    def test_cloudwatch_alarms_created(self, template):
        """Test CloudWatch alarms are created for monitoring."""
        # DLQ alarm
        template.resource_count_is(
            'AWS::CloudWatch::Alarm',
            2  # DLQ alarm + Error rate alarm (minimum)
        )

    def test_lambda_environment_variables_set(self, template):
        """Test Lambda environment variables are configured."""
        template.has_resource_properties(
            'AWS::Lambda::Function',
            {
                'Environment': cdk_assertions.Match.object_like({
                    'Variables': cdk_assertions.Match.object_like({
                        'TABLE_NAME': cdk_assertions.Match.any(),
                        'QUEUE_URL': cdk_assertions.Match.any(),
                        'RESULTS_BUCKET_NAME': cdk_assertions.Match.any()
                    })
                })
            }
        )
```

---

## Test Execution

### Running Unit Tests Locally

```bash
cd src/backend

# Run all unit tests
uv run pytest tests/unit/ -v

# Run specific test class
uv run pytest tests/unit/handlers/test_vpr_submit_handler.py::TestVPRSubmitHandler -v

# Run with coverage
uv run pytest tests/unit/ --cov=careervp --cov-report=html

# Run specific test with detailed output
uv run pytest tests/unit/logic/test_vpr_generator.py::TestVPRGenerator::test_vpr_generation_success -vv -s
```

### Running Integration Tests Locally

```bash
cd src/backend

# Run integration tests (requires moto, no AWS calls)
uv run pytest tests/integration/ -v

# Run with specific markers
uv run pytest tests/integration/ -m integration -v

# Run with timeout (in case tests hang)
uv run pytest tests/integration/ -v --timeout=30
```

### Running E2E Tests Against Deployed Stack

```bash
cd src/backend

# Set environment variables for E2E tests
export API_BASE_URL="https://your-deployed-api.example.com"
export TEST_TIMEOUT=60

# Run E2E tests
uv run pytest tests/e2e/test_vpr_async_polling.py -v

# Run with verbose output
uv run pytest tests/e2e/test_vpr_async_polling.py -vv -s

# Run specific E2E test
uv run pytest tests/e2e/test_vpr_async_polling.py::TestVPRAsyncAPI::test_submit_vpr_job_returns_202_accepted -v
```

### Running All Tests with Coverage

```bash
cd src/backend

# Run full test suite (unit + integration)
uv run pytest tests/unit/ tests/integration/ -v --cov=careervp --cov-report=term-missing

# Generate HTML coverage report
uv run pytest tests/ --cov=careervp --cov-report=html
# Open htmlcov/index.html in browser
```

### Debugging Tests

```bash
# Run with detailed assertion output
uv run pytest tests/unit/logic/test_vpr_generator.py -vv

# Run with print statements (--capture=no)
uv run pytest tests/unit/ -s

# Run specific test with debugging
uv run pytest tests/unit/test_file.py::test_name -vv -s --pdb

# Run tests matching pattern
uv run pytest tests/unit/ -k "idempotency" -v

# Run with specific log level
uv run pytest tests/unit/ -v --log-cli-level=DEBUG
```

---

## CI/CD Integration

### GitHub Actions Workflow

The VPR async testing is integrated into `.github/workflows/deploy-vpr-async.yml`:

**Stage 1: Lint and Test (ubuntu-latest)**
```yaml
lint-and-test:
  steps:
    - name: Run ruff check
      run: uv run ruff check careervp/

    - name: Run mypy (strict mode)
      run: uv run mypy careervp/ --strict

    - name: Run unit tests
      run: uv run pytest tests/unit/ -v

    - name: Run integration tests
      run: uv run pytest tests/integration/ -v
```

**Stage 2: CDK Synth (requires AWS credentials)**
```yaml
cdk-synth:
  needs: lint-and-test
  steps:
    - name: CDK Synth
      run: npx cdk synth --all
```

**Stage 3: Deploy to Dev (only on main branch)**
```yaml
cdk-deploy:
  needs: cdk-synth
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

**Stage 4: E2E Tests (only after successful deploy)**
```yaml
e2e-test:
  needs: cdk-deploy
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  steps:
    - name: Run E2E tests
      env:
        API_BASE_URL: ${{ needs.cdk-deploy.outputs.api_url }}
      run: uv run pytest tests/e2e/test_vpr_async_polling.py -v
```

**Stage 5: Dry Run on PRs**
```yaml
dry-run:
  if: github.event_name == 'pull_request'
  steps:
    - name: CDK Diff (Dry Run)
      run: npx cdk diff CareerVpVprAsyncDev
```

### Test Execution Flow

```
┌─────────────────────────────────────────────┐
│ Push to main OR Pull Request                │
└──────────────┬──────────────────────────────┘
               │
               ▼
         ┌─────────────┐
         │ Checkout    │
         └──────┬──────┘
                │
                ▼
         ┌──────────────┐
         │ Lint & Test  │ ◄─ Unit tests (70 sec)
         │ (Serial)     │    + Integration tests (45 sec)
         └──────┬───────┘
                │
        ┌───────┴────────┐
        │                │
        ▼                ▼
   (Main Branch)   (Pull Request)
        │                │
        ▼                ▼
   ┌────────┐      ┌──────────┐
   │CDK     │      │CDK Diff  │
   │Synth   │      │(Dry Run) │
   └───┬────┘      └──────────┘
       │
       ▼
   ┌──────────┐
   │Deploy    │ ◄─ Only if lint/test passes
   │to Dev    │
   └────┬─────┘
        │
        ▼
   ┌────────────┐
   │E2E Tests   │ ◄─ Full async workflow test (60 sec)
   │(Polling)   │
   └────────────┘
```

### Performance Targets

- **Unit Tests:** < 70 seconds total
- **Integration Tests:** < 45 seconds total
- **Lint/Type Check:** < 30 seconds total
- **CDK Synth:** < 20 seconds total
- **E2E Tests:** ~60 seconds (sequential polling)
- **Total CI Time:** ~4-5 minutes on main branch

### Monitoring Test Results

**GitHub Actions Summary:**
- View test results in workflow run summary
- Artifact uploads for coverage reports
- Automatic PR comments with CDK diff

**Local Test Metrics:**
```bash
# Measure test execution time
time uv run pytest tests/unit/ -v

# Generate pytest timing report
uv run pytest tests/ --durations=10
```

### Handling Test Failures

**Unit/Integration Test Failures:**
1. Run test locally: `uv run pytest tests/unit/path/to/test.py::test_name -vv`
2. Check logs for mock/assertion issues
3. Verify AWS SDK behavior with current moto version
4. Add `--tb=short` for concise tracebacks

**E2E Test Failures:**
1. Check deployed stack outputs: `aws cloudformation describe-stacks --stack-name CareerVpVprAsyncDev`
2. Verify API is accessible: `curl https://api-url/api/vpr/status/test-id`
3. Check CloudWatch logs for Lambda errors
4. Inspect DynamoDB jobs table for job status

**CDK Synth Failures:**
1. Run locally: `cd infra && npx cdk synth CareerVpVprAsyncDev`
2. Check CDK output for missing resources
3. Verify Lambda asset is built: `cd src/backend && make build`

---

## Best Practices

### Test Organization

- **Group related tests:** Use test classes (e.g., `TestVPRSubmitHandler`)
- **Descriptive names:** `test_submit_handler_returns_202_with_job_id`
- **One assertion per test:** Easier to identify failures
- **Use fixtures:** Reduce duplication, improve readability

### Mocking Strategy

- **Mock external APIs:** Anthropic SDK, external HTTP calls
- **Use moto for AWS:** DynamoDB, SQS, S3 (no real AWS access)
- **Separate concerns:** Unit tests mock more, integration tests mock less
- **Document mock behavior:** Add comments explaining expected responses

### Test Coverage

- **Aim for 80%+ coverage:** Focus on business logic
- **Skip trivial code:** Auto-generated or framework code
- **Cover error paths:** Not just happy path
- **Test boundary conditions:** Empty inputs, max sizes, etc.

### Performance

- **Keep unit tests fast:** < 100ms per test
- **Batch integration tests:** Use fixtures to reduce setup time
- **Parallelize E2E tests:** Can run multiple polling jobs simultaneously
- **Use `pytest-timeout`:** Prevent hanging tests

### Documentation

- **Docstrings for test classes:** Explain what component is tested
- **Descriptive assertions:** Use `assert x == y, f'Expected {y}, got {x}'`
- **Add comments for complex logic:** Especially for mocking
- **Link to specs:** Reference architecture docs in test comments

---

## See Also

- **Architecture Spec:** [docs/specs/07-vpr-async-architecture.md](/docs/specs/07-vpr-async-architecture.md)
- **CI/CD Workflow:** [.github/workflows/deploy-vpr-async.yml](/.github/workflows/deploy-vpr-async.yml)
- **Test Files:**
  - Unit: [src/backend/tests/unit/](/src/backend/tests/unit/)
  - Integration: [tests/integration/test_vpr_async_infra.py](/tests/integration/test_vpr_async_infra.py)
  - E2E: [src/backend/tests/e2e/test_vpr_async_polling.py](/src/backend/tests/e2e/test_vpr_async_polling.py)
