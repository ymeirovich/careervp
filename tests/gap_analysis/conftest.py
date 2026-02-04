"""
Pytest fixtures for gap analysis tests.
Shared test data and mocks for unit, integration, and e2e tests.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest


@pytest.fixture(autouse=True)
def set_test_env_vars():
    """Set required environment variables for all tests."""
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["JOBS_TABLE_NAME"] = "careervp-jobs-table-test"
    os.environ["QUEUE_URL"] = (
        "https://sqs.us-east-1.amazonaws.com/123456789012/careervp-gap-analysis-queue-test"
    )
    os.environ["RESULTS_BUCKET_NAME"] = "careervp-results-test"
    os.environ["POWERTOOLS_SERVICE_NAME"] = "careervp-gap-analysis"
    os.environ["LOG_LEVEL"] = "INFO"
    yield
    # Cleanup after tests
    for key in [
        "AWS_DEFAULT_REGION",
        "AWS_REGION",
        "JOBS_TABLE_NAME",
        "QUEUE_URL",
        "RESULTS_BUCKET_NAME",
    ]:
        os.environ.pop(key, None)


@pytest.fixture
def mock_user_id() -> str:
    """Mock user ID for testing."""
    return "user_test_123"


@pytest.fixture
def mock_cv_id() -> str:
    """Mock CV ID for testing."""
    return "cv_test_789"


@pytest.fixture
def mock_job_id() -> str:
    """Mock job ID for testing."""
    return str(uuid4())


@pytest.fixture
def mock_user_cv() -> dict[str, Any]:
    """Mock UserCV data structure."""
    return {
        "personal_info": {
            "full_name": "Jane Developer",
            "email": "jane@example.com",
            "phone": "+1-555-0123",
            "location": "San Francisco, CA",
        },
        "work_experience": [
            {
                "company": "Tech Corp",
                "role": "Cloud Engineer",
                "start_date": "2021-01",
                "end_date": "2024-01",
                "responsibilities": [
                    "Designed and implemented cloud infrastructure on AWS",
                    "Managed CI/CD pipelines using Jenkins",
                    "Led migration to microservices architecture",
                ],
            },
            {
                "company": "Startup Inc",
                "role": "Software Engineer",
                "start_date": "2019-06",
                "end_date": "2021-01",
                "responsibilities": [
                    "Developed backend APIs using Python and Flask",
                    "Worked with PostgreSQL databases",
                    "Participated in agile development processes",
                ],
            },
        ],
        "skills": [
            "Python",
            "JavaScript",
            "AWS",
            "Docker",
            "PostgreSQL",
            "Jenkins",
            "Git",
        ],
        "education": [
            {
                "institution": "State University",
                "degree": "Bachelor of Science",
                "field": "Computer Science",
                "graduation_year": "2019",
            }
        ],
        "certifications": [],
        "projects": [],
        "language": "en",
    }


@pytest.fixture
def mock_job_posting() -> dict[str, Any]:
    """Mock JobPosting data structure."""
    return {
        "company_name": "TechCorp",
        "role_title": "Senior Software Engineer",
        "description": "We are seeking a Senior Software Engineer to join our platform team.",
        "requirements": [
            "5+ years of software development experience",
            "Strong proficiency in Python and AWS",
            "Experience with microservices architecture",
            "Knowledge of Kubernetes and container orchestration",
            "Experience with CI/CD pipelines",
        ],
        "responsibilities": [
            "Design and implement scalable backend systems",
            "Lead technical design discussions",
            "Mentor junior engineers",
            "Participate in on-call rotation",
        ],
        "nice_to_have": [
            "Experience with Terraform",
            "Previous leadership experience",
            "Open source contributions",
        ],
        "language": "en",
        "source_url": "https://example.com/jobs/123",
    }


@pytest.fixture
def mock_gap_questions() -> list[dict[str, Any]]:
    """Mock generated gap questions."""
    return [
        {
            "question_id": f"q1-{uuid4()}",
            "question": "You worked as a Cloud Engineer at Tech Corp. Can you describe your hands-on experience with AWS services, particularly EC2, S3, and Lambda?",
            "impact": "HIGH",
            "probability": "HIGH",
            "gap_score": 1.0,
        },
        {
            "question_id": f"q2-{uuid4()}",
            "question": "The role requires experience with microservices architecture. In your current position, have you designed or maintained microservices-based systems?",
            "impact": "HIGH",
            "probability": "MEDIUM",
            "gap_score": 0.88,
        },
        {
            "question_id": f"q3-{uuid4()}",
            "question": "Do you have experience with Kubernetes for container orchestration? If so, please describe how you've used it in production.",
            "impact": "MEDIUM",
            "probability": "HIGH",
            "gap_score": 0.78,
        },
        {
            "question_id": f"q4-{uuid4()}",
            "question": "You've worked in engineering roles for 4 years. Have you had any opportunities to lead technical initiatives or mentor junior developers?",
            "impact": "MEDIUM",
            "probability": "MEDIUM",
            "gap_score": 0.6,
        },
        {
            "question_id": f"q5-{uuid4()}",
            "question": "Since your last role, have you gained any experience with Python or developed relevant backend systems?",
            "impact": "MEDIUM",
            "probability": "LOW",
            "gap_score": 0.51,
        },
    ]


@pytest.fixture
def mock_llm_response(mock_gap_questions: list[dict[str, Any]]) -> str:
    """Mock LLM API response (JSON string)."""
    return json.dumps(mock_gap_questions)


@pytest.fixture
def mock_gap_analysis_request(
    mock_user_id: str, mock_cv_id: str, mock_job_posting: dict[str, Any]
) -> dict[str, Any]:
    """Mock GapAnalysisRequest."""
    return {
        "user_id": mock_user_id,
        "cv_id": mock_cv_id,
        "job_posting": mock_job_posting,
        "language": "en",
    }


@pytest.fixture
def mock_gap_analysis_result(
    mock_job_id: str,
    mock_user_id: str,
    mock_job_posting: dict[str, Any],
    mock_gap_questions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Mock GapAnalysisResult."""
    return {
        "job_id": mock_job_id,
        "user_id": mock_user_id,
        "job_posting": mock_job_posting,
        "questions": mock_gap_questions,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "questions_generated": len(mock_gap_questions),
            "processing_time_seconds": 45,
            "language": "en",
        },
    }


@pytest.fixture
def mock_dynamodb_job_record(mock_job_id: str, mock_user_id: str) -> dict[str, Any]:
    """Mock DynamoDB job record."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "pk": f"JOB#{mock_job_id}",
        "sk": "METADATA",
        "gsi1pk": f"USER#{mock_user_id}",
        "gsi1sk": f"JOB#gap_analysis#{now}",
        "job_id": mock_job_id,
        "user_id": mock_user_id,
        "feature": "gap_analysis",
        "status": "PENDING",
        "request_data": {},
        "result_s3_key": None,
        "error": None,
        "code": None,
        "created_at": now,
        "started_at": None,
        "completed_at": None,
        "failed_at": None,
        "ttl": int((datetime.now(timezone.utc).timestamp() + 604800)),  # 7 days
    }


@pytest.fixture
def mock_sqs_event(mock_job_id: str) -> dict[str, Any]:
    """Mock SQS event for worker Lambda."""
    return {
        "Records": [
            {
                "messageId": str(uuid4()),
                "receiptHandle": "mock-receipt-handle",
                "body": json.dumps(
                    {
                        "job_id": mock_job_id,
                        "user_id": "user_test_123",
                        "cv_id": "cv_test_789",
                    }
                ),
                "attributes": {
                    "ApproximateReceiveCount": "1",
                    "SentTimestamp": "1638360000000",
                },
                "messageAttributes": {},
                "md5OfBody": "mock-md5",
                "eventSource": "aws:sqs",
                "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:careervp-gap-analysis-queue-test",
                "awsRegion": "us-east-1",
            }
        ]
    }


@pytest.fixture
def mock_api_gateway_event(mock_gap_analysis_request: dict[str, Any]) -> dict[str, Any]:
    """Mock API Gateway event for submit handler."""
    return {
        "resource": "/api/gap-analysis/submit",
        "path": "/api/gap-analysis/submit",
        "httpMethod": "POST",
        "headers": {
            "Authorization": "Bearer mock-jwt-token",
            "Content-Type": "application/json",
        },
        "body": json.dumps(mock_gap_analysis_request),
        "isBase64Encoded": False,
        "requestContext": {
            "authorizer": {
                "claims": {"sub": "user_test_123", "email": "test@example.com"}
            }
        },
    }


@pytest.fixture
def mock_api_gateway_status_event(mock_job_id: str) -> dict[str, Any]:
    """Mock API Gateway event for status handler."""
    return {
        "resource": "/api/gap-analysis/status/{job_id}",
        "path": f"/api/gap-analysis/status/{mock_job_id}",
        "httpMethod": "GET",
        "headers": {"Authorization": "Bearer mock-jwt-token"},
        "pathParameters": {"job_id": mock_job_id},
        "isBase64Encoded": False,
        "requestContext": {
            "authorizer": {
                "claims": {"sub": "user_test_123", "email": "test@example.com"}
            }
        },
    }


@pytest.fixture
def mock_lambda_context():
    """Mock AWS Lambda context."""

    class MockLambdaContext:
        function_name = "gap-analysis-test"
        memory_limit_in_mb = 1024
        invoked_function_arn = (
            "arn:aws:lambda:us-east-1:123456789012:function:gap-analysis-test"
        )
        aws_request_id = str(uuid4())

        @staticmethod
        def get_remaining_time_in_millis():
            return 300000  # 5 minutes

    return MockLambdaContext()


@pytest.fixture
def mock_s3_presigned_url(mock_job_id: str) -> str:
    """Mock S3 presigned URL."""
    return f"https://careervp-results-test.s3.amazonaws.com/jobs/gap-analysis/{mock_job_id}.json?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=MOCK&X-Amz-Date=20250204T120000Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=mock-signature"
