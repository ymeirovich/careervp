"""
VPR DynamoDAL tests per docs/specs/03-vpr-generator.md:14 storage contract.
"""

import os
from datetime import datetime, timezone
from typing import Iterator

import boto3  # type: ignore[import-untyped]
import pytest
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from moto import mock_aws
from pytest_mock import MockerFixture

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.models.result import ResultCode
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


def test_list_cover_letters_returns_full_items(mocker: MockerFixture) -> None:
    handler = DynamoDalHandler(TABLE_NAME)
    mock_table = mocker.Mock()
    mock_table.query.return_value = {
        'Items': [
            {
                'pk': 'user-1',
                'sk': 'ARTIFACT#COVER_LETTER#cv-1#job-1#v1',
                'cv_id': 'cv-1',
                'job_id': 'job-1',
                'cover_letter': {'text': 'hello'},
            }
        ]
    }
    mocker.patch.object(handler, '_get_db_handler', return_value=mock_table)

    result = handler.list_cover_letters('user-1')

    assert result.success is True
    assert isinstance(result.data, list)
    assert result.data[0]['cv_id'] == 'cv-1'
    assert isinstance(result.data[0]['cover_letter'], dict)


def test_list_gap_questions_by_prefix_matches_normalized_job_id(mocker: MockerFixture) -> None:
    handler = DynamoDalHandler(TABLE_NAME)
    mock_table = mocker.Mock()
    mock_table.query.return_value = {
        'Items': [
            {
                'pk': 'user-1',
                'sk': 'ARTIFACT#GAP_ANALYSIS#cv-1# Job-123 ',
                'job_id': ' Job-123 ',
            },
            {
                'pk': 'user-1',
                'sk': 'ARTIFACT#GAP_ANALYSIS#cv-1#JOB-123',
            },
            {
                'pk': 'user-1',
                'sk': 'ARTIFACT#GAP_ANALYSIS#cv-1#job-999',
                'job_id': 'job-999',
            },
        ]
    }
    mocker.patch.object(handler, '_get_db_handler', return_value=mock_table)

    result = handler.list_gap_questions_by_prefix('user-1', job_id='job-123')

    assert result.success is True
    assert isinstance(result.data, list)
    assert len(result.data) == 2
    assert all('job-123' in str(item.get('sk', '')).lower() for item in result.data)


def test_delete_tailored_cv_deletes_prefixed_item(mocker: MockerFixture) -> None:
    handler = DynamoDalHandler(TABLE_NAME)
    mock_table = mocker.Mock()
    mock_table.get_item.side_effect = [
        {},
        {'Item': {'pk': 'user-1', 'sk': 'ARTIFACT#CV_TAILORED#cv-tail-123'}},
    ]
    mock_table.delete_item.return_value = {}
    mocker.patch.object(handler, '_get_db_handler', return_value=mock_table)

    result = handler.delete_tailored_cv('user-1', 'cv-tail-123')

    assert result.success is True
    assert mock_table.delete_item.call_count == 1
    delete_key = mock_table.delete_item.call_args.kwargs['Key']
    assert delete_key['sk'] == 'ARTIFACT#CV_TAILORED#cv-tail-123'


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

    def test_save_gap_questions_returns_schema_mismatch_code_on_validation_exception(self, mocker: MockerFixture) -> None:
        handler = DynamoDalHandler(TABLE_NAME)
        mock_table = mocker.Mock()
        mock_table.put_item.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'ValidationException',
                    'Message': 'The provided key element does not match the schema',
                }
            },
            operation_name='PutItem',
        )
        mocker.patch.object(handler, '_get_db_handler', return_value=mock_table)

        result = handler.save_gap_questions(
            user_id='user-1',
            cv_id='cv-1',
            job_id='job-1',
            questions=[{'question_id': 'q1', 'question': 'Example'}],
        )

        assert result.success is False
        assert result.code == ResultCode.TABLE_SCHEMA_MISMATCH
        assert result.error is not None
        assert 'table_name' in result.error
        assert 'operation=save_gap_questions' in result.error

    def test_save_gap_responses_raw_includes_table_and_operation_on_failure(self, mocker: MockerFixture) -> None:
        handler = DynamoDalHandler(TABLE_NAME)
        mock_table = mocker.Mock()
        mock_table.put_item.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'ProvisionedThroughputExceededException',
                    'Message': 'rate exceeded',
                }
            },
            operation_name='PutItem',
        )
        mocker.patch.object(handler, '_get_db_handler', return_value=mock_table)

        result = handler.save_gap_responses_raw(
            user_id='user-1',
            job_id='job-1',
            responses=[{'question_id': 'q1', 'response': 'A'}],
        )

        assert result.success is False
        assert result.code == ResultCode.DYNAMODB_ERROR
        assert result.error is not None
        assert f'table_name={TABLE_NAME}' in result.error
        assert 'operation=save_gap_responses_raw' in result.error
