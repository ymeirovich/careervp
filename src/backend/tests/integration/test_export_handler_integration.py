"""Integration tests for export_handler — FE-UI-028.

Uses moto to simulate S3 and DynamoDB. Verifies the full Lambda event
path: event → handler → AWS read → DOCX generation → presigned URL.
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from typing import Any

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('POWERTOOLS_SERVICE_NAME', 'careervp-export-integration-test')
os.environ.setdefault('LOG_LEVEL', 'INFO')

VPR_BUCKET = 'test-vpr-results-int'
ARTIFACTS_BUCKET = 'test-artifacts-int'
ARTIFACTS_TABLE = 'test-artifacts-table-int'
MAIN_TABLE = 'test-main-table-int'
USER_ID = 'user-int-001'
JOB_ID = 'job-int-001'
ALLOWED_ORIGIN = 'https://int-test.example.com'


def _make_event(
    job_id: str = JOB_ID,
    module_type: str = 'vpr',
    fmt: str = 'docx',
    user_id: str = USER_ID,
    origin: str = ALLOWED_ORIGIN,
) -> dict[str, Any]:
    return {
        'httpMethod': 'GET',
        'path': f'/jobs/{job_id}/artifacts/{module_type}/export',
        'pathParameters': {'jobId': job_id, 'moduleType': module_type},
        'queryStringParameters': {'format': fmt},
        'headers': {'origin': origin},
        'body': None,
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
    }


@pytest.fixture(autouse=True)
def export_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('VPR_RESULTS_BUCKET_NAME', VPR_BUCKET)
    monkeypatch.setenv('ARTIFACTS_BUCKET_NAME', ARTIFACTS_BUCKET)
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', ARTIFACTS_TABLE)
    monkeypatch.setenv('TABLE_NAME', MAIN_TABLE)
    monkeypatch.setenv('ALLOWED_ORIGINS', ALLOWED_ORIGIN)
    monkeypatch.setattr('careervp.handlers.cors_utils._ALLOWED_ORIGINS', {ALLOWED_ORIGIN})


@pytest.fixture
def aws_resources() -> Generator[dict[str, Any], None, None]:
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket=VPR_BUCKET)
        s3.create_bucket(Bucket=ARTIFACTS_BUCKET)

        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

        artifacts_table = dynamodb.create_table(
            TableName=ARTIFACTS_TABLE,
            KeySchema=[
                {'AttributeName': 'applicationId', 'KeyType': 'HASH'},
                {'AttributeName': 'artifactId', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'applicationId', 'AttributeType': 'S'},
                {'AttributeName': 'artifactId', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        main_table = dynamodb.create_table(
            TableName=MAIN_TABLE,
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        yield {
            's3': s3,
            'artifacts_table': artifacts_table,
            'main_table': main_table,
        }


# ---------------------------------------------------------------------------
# AC-001 integration: vpr docx — mock S3 get_object + put_object + presign → 200
# ---------------------------------------------------------------------------


def test_vpr_docx_full_event_returns_200(aws_resources: dict[str, Any]) -> None:
    from careervp.handlers.export_handler import lambda_handler

    vpr_data = {
        'summary': 'Excellent candidate with strong background in Python and AWS.',
        'technical_skills': 'Python, AWS Lambda, DynamoDB, S3',
        'leadership': 'Led cross-functional team of 8 engineers.',
    }
    aws_resources['s3'].put_object(
        Bucket=VPR_BUCKET,
        Key=f'results/{JOB_ID}.json',
        Body=json.dumps(vpr_data).encode(),
    )

    response = lambda_handler(_make_event(module_type='vpr'), None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'download_url' in body
    assert 'expires_at' in body


# ---------------------------------------------------------------------------
# AC-002 integration: cover_letter docx — mock DynamoDB artifacts table → 200
# ---------------------------------------------------------------------------


def test_cover_letter_docx_full_event_returns_200(aws_resources: dict[str, Any]) -> None:
    from careervp.handlers.export_handler import lambda_handler

    aws_resources['artifacts_table'].put_item(
        Item={
            'applicationId': USER_ID,
            'artifactId': f'ARTIFACT#COVER_LETTER#{JOB_ID}',
            'cover_letter': {'full_text': 'Dear Hiring Manager, I am thrilled to apply...'},
        }
    )

    response = lambda_handler(_make_event(module_type='cover_letter'), None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'download_url' in body
    assert 'expires_at' in body


# ---------------------------------------------------------------------------
# AC-003 integration: interview_prep docx — mock DynamoDB artifacts table → 200
# ---------------------------------------------------------------------------


def test_interview_prep_docx_full_event_returns_200(aws_resources: dict[str, Any]) -> None:
    from careervp.handlers.export_handler import INTERVIEW_PREP_SORT_KEY_PREFIX, lambda_handler

    aws_resources['artifacts_table'].put_item(
        Item={
            'applicationId': USER_ID,
            'artifactId': f'{INTERVIEW_PREP_SORT_KEY_PREFIX}{JOB_ID}',
            'interview_prep': {
                'questions': [
                    {'question': 'Tell me about yourself', 'answer': 'I am a Python developer.'},
                    {'question': 'Why this role?', 'answer': 'Passion for cloud engineering.'},
                ]
            },
        }
    )

    response = lambda_handler(_make_event(module_type='interview_prep'), None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'download_url' in body


# ---------------------------------------------------------------------------
# AC-004 integration: cv_tailored docx — mock DynamoDB main table → 200
# ---------------------------------------------------------------------------


def test_cv_tailored_docx_full_event_returns_200(aws_resources: dict[str, Any]) -> None:
    from careervp.handlers.export_handler import lambda_handler

    aws_resources['main_table'].put_item(
        Item={
            'pk': USER_ID,
            'sk': f'ARTIFACT#CV_TAILORED#{JOB_ID}',
            'job_id': JOB_ID,
            'cv_sections': {'experience': 'Senior Engineer at Acme Corp.', 'skills': 'Python, Go'},
            'tailored_cv': 'Experienced backend engineer targeting cloud roles.',
        }
    )

    response = lambda_handler(_make_event(module_type='cv_tailored'), None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'download_url' in body


# ---------------------------------------------------------------------------
# AC-015 integration: presigned URL contains artifacts bucket domain
# ---------------------------------------------------------------------------


def test_presigned_url_contains_artifacts_bucket_domain(aws_resources: dict[str, Any]) -> None:
    from careervp.handlers.export_handler import lambda_handler

    aws_resources['s3'].put_object(
        Bucket=VPR_BUCKET,
        Key=f'results/{JOB_ID}.json',
        Body=json.dumps({'summary': 'Test'}).encode(),
    )

    response = lambda_handler(_make_event(module_type='vpr'), None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert ARTIFACTS_BUCKET in body['download_url']


# ---------------------------------------------------------------------------
# CORS headers present on 200 response
# ---------------------------------------------------------------------------


def test_cors_headers_present_on_200_response(aws_resources: dict[str, Any]) -> None:
    from careervp.handlers.export_handler import lambda_handler

    aws_resources['s3'].put_object(
        Bucket=VPR_BUCKET,
        Key=f'results/{JOB_ID}.json',
        Body=json.dumps({'summary': 'Test'}).encode(),
    )

    response = lambda_handler(_make_event(module_type='vpr', origin=ALLOWED_ORIGIN), None)

    assert response['statusCode'] == 200
    assert response['headers'].get('Access-Control-Allow-Origin') == ALLOWED_ORIGIN


# ---------------------------------------------------------------------------
# CORS headers present on error response (501 for pdf)
# ---------------------------------------------------------------------------


def test_cors_headers_present_on_error_response(aws_resources: dict[str, Any]) -> None:
    from careervp.handlers.export_handler import lambda_handler

    response = lambda_handler(_make_event(module_type='vpr', fmt='pdf', origin=ALLOWED_ORIGIN), None)

    assert response['statusCode'] == 501
    assert response['headers'].get('Access-Control-Allow-Origin') == ALLOWED_ORIGIN
