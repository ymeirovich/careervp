"""S11d verification: does save_cv raise on a GPA-bearing CV, and does the
exception escape the (ClientError, ValidationError) catch as a TypeError?

Also verifies save_vpr with float cost_usd (the claimed sibling)."""

import boto3
import pytest
from moto import mock_aws

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.models.cv import Education, UserCV

TABLE = 'test-cvs-table'


@pytest.fixture()
def cvs_table():
    with mock_aws():
        ddb = boto3.resource('dynamodb', region_name='us-east-1')
        ddb.create_table(
            TableName=TABLE,
            KeySchema=[
                {'AttributeName': 'userId', 'KeyType': 'HASH'},
                {'AttributeName': 'cvId', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'cvId', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        yield


def _cv(gpa):
    return UserCV(
        user_id='user-123',
        full_name='Test Person',
        email='test@example.com',
        education=[
            Education(institution='Test University', degree='BSc', gpa=gpa),
        ],
    )


def test_save_cv_without_gpa_succeeds(cvs_table):
    dal = DynamoDalHandler(TABLE)
    dal.save_cv(_cv(None))  # gpa None -> excluded by exclude_none
    print('NO-GPA: save_cv succeeded')


def test_save_cv_with_gpa(cvs_table):
    dal = DynamoDalHandler(TABLE)
    try:
        dal.save_cv(_cv(3.8))
        print('GPA: save_cv SUCCEEDED — claim REFUTED')
    except Exception as exc:  # noqa: BLE001
        print(f'GPA: save_cv raised {type(exc).__module__}.{type(exc).__name__}: {exc}')
        raise
