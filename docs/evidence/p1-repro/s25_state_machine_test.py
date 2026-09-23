"""S25 verification: update_state(..., user_id='') against the real
applications-table key schema. Does it ever succeed? What exception fires?"""

import boto3
import pytest
from moto import mock_aws

from careervp.dal.application_repository import ApplicationRepository
from careervp.dal.dynamo_dal_handler import DynamoDalHandler

TABLE = 'test-applications-table'


@pytest.fixture()
def apps_table():
    with mock_aws():
        ddb = boto3.resource('dynamodb', region_name='us-east-1')
        ddb.create_table(
            TableName=TABLE,
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
        yield ddb.Table(TABLE)


def test_update_state_with_real_user_succeeds(apps_table):
    repo = ApplicationRepository(dal=DynamoDalHandler(table_name=TABLE))
    app_id = repo.create(user_id='user-1', job_id='job-1')
    repo.update_state(application_id=app_id, user_id='user-1', new_state='cv_selected', expected_state='created')
    repo.update_state(application_id=app_id, user_id='user-1', new_state='gap_questions_pending', expected_state='cv_selected')
    item = apps_table.get_item(Key={'userId': 'user-1', 'applicationId': app_id})['Item']
    print(f"CONTROL: state advanced to {item['state']}")
    assert item['state'] == 'gap_questions_pending'


def test_update_state_with_empty_user_id(apps_table):
    repo = ApplicationRepository(dal=DynamoDalHandler(table_name=TABLE))
    app_id = repo.create(user_id='user-1', job_id='job-1')
    repo.update_state(application_id=app_id, user_id='user-1', new_state='cv_selected', expected_state='created')
    try:
        repo.update_state(application_id=app_id, user_id='', new_state='gap_questions_pending', expected_state='cv_selected')
        print('EMPTY-USER: update_state SUCCEEDED — claim REFUTED')
    except Exception as exc:  # noqa: BLE001
        print(f'EMPTY-USER: raised {type(exc).__name__}: {exc}')
    item = apps_table.get_item(Key={'userId': 'user-1', 'applicationId': app_id})['Item']
    print(f"EMPTY-USER: real item state after call = {item['state']}")
    assert item['state'] == 'cv_selected'  # never advanced
