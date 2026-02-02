"""
VPR DynamoDAL tests per docs/specs/03-vpr-generator.md:14 storage contract.
"""

import os
from datetime import datetime, timezone
from typing import Iterator

import boto3
import pytest
from moto import mock_aws

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.models.vpr import VPR, EvidenceItem, GapStrategy

TABLE_NAME = 'test-vpr-table'


@pytest.fixture(scope='function', autouse=True)
def aws_env() -> Iterator[None]:
    """Set AWS defaults so boto3 works under moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    yield
    for key in [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'AWS_SESSION_TOKEN',
        'AWS_DEFAULT_REGION',
    ]:
        os.environ.pop(key, None)


@pytest.fixture(scope='function', autouse=True)
def reset_dal_singleton() -> Iterator[None]:
    """Ensure DynamoDalHandler picks up new table names each test."""
    DynamoDalHandler.reset_instance()
    yield
    DynamoDalHandler.reset_instance()


@pytest.fixture(scope='function')
def dynamodb_table() -> Iterator[None]:
    """Create a DynamoDB table with the PK/SK + user_id GSI design."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
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
        table.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)
        yield


def _build_vpr(version: int = 1, application_id: str = 'app-123', user_id: str = 'user-456') -> VPR:
    """Helper to build a valid VPR instance for persistence tests."""
    return VPR(
        application_id=application_id,
        user_id=user_id,
        executive_summary='Candidate summary with strategic framing.',
        evidence_matrix=[
            EvidenceItem(
                requirement='Leadership',
                evidence='Led cross-functional teams for 3 years at Apex Labs.',
                alignment_score='STRONG',
                impact_potential='Scaled delivery velocity by 25%.',
            )
        ],
        differentiators=['Scaled cross-functional delivery'],
        gap_strategies=[
            GapStrategy(
                gap='AI certifications',
                mitigation_approach='Highlight hands-on pilots with internal AI tooling.',
                transferable_skills=['ML Ops'],
            )
        ],
        cultural_fit='Values-first operator with transparent communication.',
        talking_points=['Discuss recent platform migration'],
        keywords=['Leadership', 'AI strategy'],
        version=version,
        language='en',
        created_at=datetime.now(timezone.utc),
        word_count=1200,
    )


class TestDynamoDalHandlerVPR:
    """End-to-end persistence tests for VPR DAL methods."""

    def test_save_and_get_vpr(self, dynamodb_table: None) -> None:
        handler = DynamoDalHandler(TABLE_NAME)
        vpr = _build_vpr(version=1)

        save_result = handler.save_vpr(vpr)
        assert save_result.success is True

        fetch_result = handler.get_vpr(application_id=vpr.application_id, version=1)
        assert fetch_result.success is True
        assert fetch_result.data is not None
        assert fetch_result.data.version == 1
        assert fetch_result.data.application_id == vpr.application_id

    def test_get_latest_vpr_prefers_highest_version(self, dynamodb_table: None) -> None:
        handler = DynamoDalHandler(TABLE_NAME)
        handler.save_vpr(_build_vpr(version=1))
        handler.save_vpr(_build_vpr(version=2))

        latest_result = handler.get_latest_vpr('app-123')
        assert latest_result.success is True
        assert latest_result.data is not None
        assert latest_result.data.version == 2

    def test_list_vprs_filters_by_user(self, dynamodb_table: None) -> None:
        handler = DynamoDalHandler(TABLE_NAME)
        handler.save_vpr(_build_vpr(version=1, application_id='app-123', user_id='user-456'))
        handler.save_vpr(_build_vpr(version=2, application_id='app-456', user_id='user-456'))
        handler.save_vpr(_build_vpr(version=1, application_id='app-789', user_id='other-user'))

        list_result = handler.list_vprs('user-456')
        assert list_result.success is True
        assert list_result.data is not None
        assert len(list_result.data) == 2
        versions = [v.version for v in list_result.data]
        assert versions == sorted(versions, reverse=True)

    def test_get_vpr_handles_missing_record(self, dynamodb_table: None) -> None:
        handler = DynamoDalHandler(TABLE_NAME)

        missing_result = handler.get_vpr(application_id='missing', version=1)
        assert missing_result.success is True
        assert missing_result.data is None
