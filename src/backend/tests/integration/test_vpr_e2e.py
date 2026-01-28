"""
VPR End-to-End Integration Tests.
Exercises Handler -> Generator -> DAL stack with moto-backed DynamoDB and mocked LLM.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws
from mypy_boto3_dynamodb.service_resource import Table

from careervp.handlers.vpr_handler import lambda_handler
from careervp.models.result import Result, ResultCode


@pytest.fixture(scope='module')
def aws_env() -> Iterator[None]:
    """Set deterministic AWS credentials + Powertools configuration for moto."""
    patcher = pytest.MonkeyPatch()
    patcher.setenv('AWS_ACCESS_KEY_ID', 'testing')
    patcher.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    patcher.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    patcher.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-test')
    patcher.setenv('LOG_LEVEL', 'INFO')
    try:
        yield
    finally:
        patcher.undo()


@pytest.fixture(scope='function')
def dynamodb_table(aws_env: None) -> Iterator[Table]:
    """Provision a moto-backed DynamoDB table matching the DAL schema."""
    table_name = 'test-careervp-artifacts'
    env_patcher = pytest.MonkeyPatch()
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user_id-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'sk', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        env_patcher.setenv('DYNAMODB_TABLE_NAME', table_name)
        try:
            yield table
        finally:
            env_patcher.undo()


def _seed_user_cv(table: Table, user_id: str) -> None:
    """Insert a parsed CV record required for handler lookup."""
    table.put_item(
        Item={
            'pk': user_id,
            'sk': 'CV',
            'user_id': user_id,
            'full_name': 'Test User',
            'language': 'en',
            'contact_info': {'email': 'test@example.com'},
            'experience': [
                {
                    'company': 'Acme Corp',
                    'role': 'Engineer',
                    'dates': '2020 – 2023',
                    'achievements': ['Built scalable systems'],
                }
            ],
            'education': [],
            'certifications': [],
            'skills': ['Python', 'AWS'],
            'top_achievements': [],
            'professional_summary': 'Seasoned engineer.',
            'is_parsed': True,
        }
    )


def _mock_llm_success_payload() -> dict[str, Any]:
    """Valid LLM payload for a successful VPR generation."""
    return {
        'text': json.dumps(
            {
                'executive_summary': 'Strong match for TechCo.',
                'evidence_matrix': [
                    {
                        'requirement': '3+ years experience',
                        'evidence': 'Worked at Acme Corp from 2020 to 2023 leading platform reliability.',
                        'alignment_score': 'STRONG',
                        'impact_potential': 'Immediate contributor.',
                    }
                ],
                'differentiators': ['Elevated reliability SLAs across mission-critical services.'],
                'gap_strategies': [],
                'cultural_fit': 'Values alignment.',
                'talking_points': ['Highlight platform reliability metrics with specific numbers.'],
                'keywords': ['Python', 'AWS'],
                'language': 'en',
                'version': 1,
            }
        ),
        'input_tokens': 4800,
        'output_tokens': 1400,
        'cost': 0.024,
        'model': 'claude-sonnet-4-5',
    }


def _mock_llm_payload_with_hallucination() -> dict[str, Any]:
    """LLM payload referencing a company absent from the CV to trigger FVS rejection."""
    payload = _mock_llm_success_payload()
    hallucinatory_vpr = json.loads(payload['text'])
    hallucinatory_vpr['evidence_matrix'][0]['evidence'] = 'Drove growth at Fictional Startup in 2019 with zero downtime.'
    payload['text'] = json.dumps(hallucinatory_vpr)
    return payload


def _build_event(application_id: str = 'app-456', user_id: str = 'user-123') -> dict[str, Any]:
    """Construct an API Gateway proxy event body matching the handler contract."""
    request = {
        'application_id': application_id,
        'user_id': user_id,
        'job_posting': {
            'company_name': 'TechCo',
            'role_title': 'Senior Engineer',
            'description': 'Build systems.',
            'responsibilities': ['Own services'],
            'requirements': ['3+ years experience'],
            'nice_to_have': [],
            'language': 'en',
        },
    }
    return {'body': json.dumps(request)}


class TestVPREndToEnd:
    """Integration coverage for major VPR Handler scenarios."""

    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_full_success_flow(self, mock_llm_cls: MagicMock, dynamodb_table: Table) -> None:
        _seed_user_cv(dynamodb_table, 'user-123')
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = Result(
            success=True,
            data=_mock_llm_success_payload(),
            code=ResultCode.SUCCESS,
        )
        mock_llm_cls.return_value = mock_llm
        assert os.environ['DYNAMODB_TABLE_NAME'] == dynamodb_table.table_name

        response = lambda_handler(_build_event(), MagicMock())

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['vpr']['application_id'] == 'app-456'

        saved = dynamodb_table.get_item(Key={'pk': 'app-456', 'sk': 'ARTIFACT#VPR#v1'})
        assert 'Item' in saved

    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_fvs_rejection_returns_422(self, mock_llm_cls: MagicMock, dynamodb_table: Table) -> None:
        _seed_user_cv(dynamodb_table, 'user-123')
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = Result(
            success=True,
            data=_mock_llm_payload_with_hallucination(),
            code=ResultCode.SUCCESS,
        )
        mock_llm_cls.return_value = mock_llm
        assert os.environ['DYNAMODB_TABLE_NAME'] == dynamodb_table.table_name

        response = lambda_handler(_build_event(application_id='app-789'), MagicMock())

        assert response['statusCode'] == 422
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error'] == 'VPR references facts not present in source CV'
        persisted = dynamodb_table.get_item(Key={'pk': 'app-789', 'sk': 'ARTIFACT#VPR#v1'})
        assert 'Item' not in persisted

    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_missing_cv_returns_404(self, mock_llm_cls: MagicMock, dynamodb_table: Table) -> None:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = Result(
            success=True,
            data=_mock_llm_success_payload(),
            code=ResultCode.SUCCESS,
        )
        mock_llm_cls.return_value = mock_llm
        assert os.environ['DYNAMODB_TABLE_NAME'] == dynamodb_table.table_name

        response = lambda_handler(_build_event(user_id='user-999'), MagicMock())

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['success'] is False
        mock_llm.invoke.assert_not_called()

    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_llm_failure_returns_502(self, mock_llm_cls: MagicMock, dynamodb_table: Table) -> None:
        _seed_user_cv(dynamodb_table, 'user-123')
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = Result(
            success=False,
            data=None,
            error='Anthropic unavailable',
            code=ResultCode.LLM_API_ERROR,
        )
        mock_llm_cls.return_value = mock_llm
        assert os.environ['DYNAMODB_TABLE_NAME'] == dynamodb_table.table_name

        response = lambda_handler(_build_event(), MagicMock())

        assert response['statusCode'] == 502
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error'] == 'Anthropic unavailable'
