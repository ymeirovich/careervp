from __future__ import annotations

import json
import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('POWERTOOLS_SERVICE_NAME', 'careervp-stop-chain-test')
os.environ.setdefault('LOG_LEVEL', 'INFO')

RESPONSES_TABLE_NAME = 'test-gap-responses-stop-chain'
APPLICATIONS_TABLE_NAME = 'test-applications-stop-chain'
USER_ID = 'user-stop-chain-001'
JOB_ID = 'job-stop-chain-001'
EXECUTION_ARN = 'arn:aws:states:us-east-1:123456789012:execution:careervp-artifact-chain:chain-job-stop-chain-001'


@pytest.fixture(autouse=True)
def stop_chain_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('GAP_RESPONSES_TABLE_NAME', RESPONSES_TABLE_NAME)
    monkeypatch.setenv('APPLICATIONS_TABLE_NAME', APPLICATIONS_TABLE_NAME)
    monkeypatch.setenv('ARTIFACT_CHAIN_ENABLED', 'true')
    monkeypatch.setenv('STEP_FUNCTIONS_CHAIN_ARN', 'arn:aws:states:us-east-1:123456789012:stateMachine:careervp-artifact-chain')

    import careervp.handlers.gap_handler as gap_handler

    gap_handler._application_repository = None
    gap_handler._trial_service = None
    yield
    gap_handler._application_repository = None
    gap_handler._trial_service = None


@pytest.fixture
def dynamodb_tables() -> Generator[None, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

        responses_table = dynamodb.create_table(
            TableName=RESPONSES_TABLE_NAME,
            KeySchema=[
                {'AttributeName': 'userId', 'KeyType': 'HASH'},
                {'AttributeName': 'questionId', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'questionId', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        responses_table.meta.client.get_waiter('table_exists').wait(TableName=RESPONSES_TABLE_NAME)

        applications_table = dynamodb.create_table(
            TableName=APPLICATIONS_TABLE_NAME,
            KeySchema=[
                {'AttributeName': 'userId', 'KeyType': 'HASH'},
                {'AttributeName': 'applicationId', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'applicationId', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        applications_table.meta.client.get_waiter('table_exists').wait(TableName=APPLICATIONS_TABLE_NAME)

        yield


def _submit_event(user_id: str = USER_ID, job_id: str = JOB_ID) -> dict[str, Any]:
    return {
        'resource': '/gap-analysis/responses',
        'path': '/gap-analysis/responses',
        'httpMethod': 'POST',
        'headers': {'Content-Type': 'application/json'},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
        'body': json.dumps(
            {
                'job_id': job_id,
                'responses': [{'question_id': 'q1', 'response': 'Delivered measurable outcomes.'}],
            }
        ),
        'isBase64Encoded': False,
    }


def _ok_gap_responses_dal() -> MagicMock:
    from careervp.models.result import Result, ResultCode

    dal = MagicMock()
    dal.save_gap_responses_raw.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)
    return dal


@pytest.mark.integration
def test_gap_submit_persists_execution_arn(dynamodb_tables: None) -> None:
    from careervp.handlers import gap_handler

    mock_jobs_repo = MagicMock()
    mock_jobs_repo.get_job.return_value = {
        'company_name': 'Acme Corp',
        'job_posting_url': 'https://example.com/jobs/123',
    }
    mock_sfn = MagicMock()
    mock_sfn.start_execution.return_value = {'executionArn': EXECUTION_ARN}

    with (
        patch.object(gap_handler, '_get_responses_dal', return_value=_ok_gap_responses_dal()),
        patch.object(gap_handler, '_get_jobs_repository', return_value=mock_jobs_repo),
        patch('careervp.handlers.gap_handler.boto3.client', return_value=mock_sfn),
    ):
        response = gap_handler.submit_response(_submit_event())

    assert response['statusCode'] == 200

    application = (
        boto3.resource('dynamodb', region_name='us-east-1')
        .Table(APPLICATIONS_TABLE_NAME)
        .get_item(Key={'userId': USER_ID, 'applicationId': JOB_ID})['Item']
    )

    assert application['chain_execution_arn'] == EXECUTION_ARN
    assert application['chain_execution_status'] == 'RUNNING'
