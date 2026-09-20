"""
CV Upload Handler Tests.
Uses moto to mock S3 and DynamoDB, and pytest-mock to mock LLM calls.

Per docs/specs/01-cv-parser.md and CLAUDE.md patterns.
"""

import base64
import json
from typing import Any
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from careervp.models.result import Result, ResultCode

_VALID_CV_TEXT = (
    'John Smith Senior Software Engineer with 8 years experience in Python, AWS, '
    'distributed systems, mentoring teams, API optimization, CI/CD delivery, and '
    'microservices architecture across high-scale production platforms.'
)


@pytest.fixture(scope='function', autouse=True)
def aws_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up environment variables for moto and Lambda Powertools.

    Uses monkeypatch so every key is restored to its prior value on teardown.
    A plain ``os.environ.pop()`` cleanup here deleted the baseline AWS
    credentials that tests/conftest.py sets at import time, leaving them unset
    for the remainder of the session — which made 23 later tests in tests/unit
    reach real AWS and fail with NoCredentialsError on any machine without
    ambient credentials. See docs/handoff/2026-09-20-HANDOFF-04-*.md.
    """
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-test')
    monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
    monkeypatch.setenv('POWERTOOLS_TRACE_DISABLED', 'true')
    monkeypatch.setenv('TABLE_NAME', 'test-users-table')
    monkeypatch.setenv('CV_BUCKET_NAME', 'test-cv-bucket')
    monkeypatch.setenv('IDEMPOTENCY_TABLE_NAME', 'test-idempotency-table')


@pytest.fixture
def dynamodb_table():
    """Create a mocked DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-users-table',
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
        table.meta.client.get_waiter('table_exists').wait(TableName='test-users-table')
        yield table


@pytest.fixture
def s3_bucket():
    """Create a mocked S3 bucket."""
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-cv-bucket')
        yield s3


@pytest.fixture
def mock_llm_success():
    """Mock successful LLM response for CV parsing."""
    parsed_cv_json = {
        'full_name': 'John Doe',
        'contact_info': {
            'phone': '+1-555-1234',
            'email': 'john.doe@example.com',
            'location': 'New York, USA',
            'linkedin': 'linkedin.com/in/johndoe',
        },
        'experience': [
            {
                'company': 'Tech Corp',
                'role': 'Senior Engineer',
                'dates': '2020 – Present',
                'achievements': ['Led team of 5', 'Increased revenue by 20%'],
            }
        ],
        'education': [
            {
                'institution': 'MIT',
                'degree': 'B.S. Computer Science',
                'field_of_study': 'Computer Science',
                'graduation_date': '2019',
            }
        ],
        'certifications': [],
        'skills': ['Python', 'AWS', 'JavaScript'],
        'top_achievements': ['Led team of 5', 'Increased revenue by 20%'],
        'professional_summary': 'Experienced software engineer.',
    }

    mock_result = Result(
        success=True,
        data={
            'text': json.dumps(parsed_cv_json),
            'input_tokens': 100,
            'output_tokens': 200,
            'cost': 0.001,
        },
        code=ResultCode.SUCCESS,
    )
    return mock_result


def generate_api_gw_event(body: dict, path: str = '/users/me/cv', method: str = 'POST') -> dict:
    """Generate an API Gateway event for testing."""
    return {
        'version': '1.0',
        'resource': path,
        'path': path,
        'httpMethod': method,
        'headers': {'Content-Type': 'application/json'},
        'multiValueHeaders': {},
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'requestContext': {
            'accountId': '123456789012',
            'apiId': 'testapi',
            'domainName': 'testapi.execute-api.us-east-1.amazonaws.com',
            'domainPrefix': 'testapi',
            'httpMethod': method,
            'path': path,
            'protocol': 'HTTP/1.1',
            'requestId': 'test-request-id',
            'requestTime': '01/Jan/2025:00:00:00 +0000',
            'requestTimeEpoch': 1735689600000,
            'stage': 'test',
            'authorizer': {'claims': {'sub': 'test-user-123'}},
        },
        'pathParameters': None,
        'stageVariables': None,
        'body': json.dumps(body) if body else None,
        'isBase64Encoded': False,
    }


def _create_cvs_table() -> Any:
    """Create the dedicated CVs table.

    Since the Stage-1 repoint every CV reader resolves from CVS_TABLE_NAME, and a
    failed write there is fatal, so any test that expects a 201 must provide it.
    ``tests/conftest.py`` sets CVS_TABLE_NAME for the whole session.
    """
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    return dynamodb.create_table(
        TableName='test-cvs-table',
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


def generate_lambda_context() -> Any:
    """Generate a mock Lambda context."""
    context = MagicMock()
    context.aws_request_id = 'test-request-id'
    context.function_name = 'cv-upload-handler'
    context.memory_limit_in_mb = 1024
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:cv-upload'
    return context


class TestCVUploadValidation:
    """Test request validation."""

    @mock_aws
    def test_missing_content_returns_bad_request(self):
        """Request without file_content or text_content should fail."""
        # Create mock resources
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket='test-cv-bucket')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test-users-table',
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

        from careervp.handlers.cv_upload_handler import lambda_handler

        event = generate_api_gw_event({'user_id': 'test-user-123'})
        context = generate_lambda_context()

        response = lambda_handler(event, context)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'file_content or text_content' in body['error']

    @mock_aws
    def test_file_content_without_file_type_fails(self):
        """Request with file_content but no file_type should fail."""
        # Create mock resources
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket='test-cv-bucket')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test-users-table',
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

        from careervp.handlers.cv_upload_handler import lambda_handler

        event = generate_api_gw_event(
            {
                'user_id': 'test-user-123',
                'file_content': base64.b64encode(b'test content').decode(),
            }
        )
        context = generate_lambda_context()

        response = lambda_handler(event, context)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'file_type is required' in body['error']

    @mock_aws
    def test_invalid_base64_fails(self):
        """Request with invalid base64 content should fail."""
        # Create mock resources
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket='test-cv-bucket')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test-users-table',
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

        from careervp.handlers.cv_upload_handler import lambda_handler

        event = generate_api_gw_event(
            {
                'user_id': 'test-user-123',
                'file_content': 'not-valid-base64!!!',
                'file_type': 'txt',
            }
        )
        context = generate_lambda_context()

        response = lambda_handler(event, context)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'base64' in body['error'].lower()


class TestCVUploadWithTextContent:
    """Test CV upload with plain text content."""

    @mock_aws
    def test_text_content_success(self, mock_llm_success):
        """Successful CV parsing with text content."""
        _create_cvs_table()
        # Create mock resources
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket='test-cv-bucket')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test-users-table',
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

        with patch('careervp.logic.cv_parser.get_llm_router') as mock_router:
            mock_router.return_value.invoke.return_value = mock_llm_success

            from careervp.handlers.cv_upload_handler import lambda_handler

            cv_text = """
            JOHN DOE
            Senior Software Engineer
            Phone: +1-555-1234
            Email: john.doe@example.com

            EXPERIENCE
            Tech Corp | Senior Engineer | 2020 – Present
            - Led team of 5 engineers
            - Increased revenue by 20%

            EDUCATION
            MIT | B.S. Computer Science | 2019

            SKILLS
            Python, AWS, JavaScript
            """

            event = generate_api_gw_event(
                {
                    'user_id': 'test-user-123',
                    'text_content': cv_text,
                }
            )
            context = generate_lambda_context()

            response = lambda_handler(event, context)

            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert body['success'] is True
            assert body['user_cv'] is not None
            assert body['user_cv']['full_name'] == 'John Doe'
            assert body['language_detected'] == 'en'
            assert body['cv_id']
            assert body['status'] == 'parsed'
            assert isinstance(body['parsed_data'], dict)

    @mock_aws
    def test_text_content_too_short_fails(self):
        """CV text that is too short should fail."""
        # Create mock resources
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket='test-cv-bucket')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test-users-table',
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

        from careervp.handlers.cv_upload_handler import lambda_handler

        event = generate_api_gw_event(
            {
                'user_id': 'test-user-123',
                'text_content': 'Too short',
            }
        )
        context = generate_lambda_context()

        response = lambda_handler(event, context)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'too short' in body['error'].lower()


class TestCVUploadWithFileContent:
    """Test CV upload with file content (base64 encoded)."""

    @mock_aws
    def test_txt_file_upload_success(self, mock_llm_success):
        """Successful CV parsing with TXT file upload."""
        _create_cvs_table()
        # Create mock resources
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-cv-bucket')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test-users-table',
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

        with patch('careervp.logic.cv_parser.get_llm_router') as mock_router:
            mock_router.return_value.invoke.return_value = mock_llm_success

            from careervp.handlers.cv_upload_handler import lambda_handler

            cv_text = """
            JOHN DOE
            Senior Software Engineer
            Phone: +1-555-1234
            Email: john.doe@example.com

            EXPERIENCE
            Tech Corp | Senior Engineer | 2020 – Present
            - Led team of 5 engineers
            - Increased revenue by 20%

            EDUCATION
            MIT | B.S. Computer Science | 2019

            SKILLS
            Python, AWS, JavaScript
            """
            file_content = base64.b64encode(cv_text.encode()).decode()

            event = generate_api_gw_event(
                {
                    'user_id': 'test-user-123',
                    'file_content': file_content,
                    'file_type': 'txt',
                }
            )
            context = generate_lambda_context()

            response = lambda_handler(event, context)

            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert body['success'] is True
            assert body['user_cv'] is not None
            assert body['user_cv']['source_file_key'] is not None
            assert body['user_cv']['source_file_key'].startswith('test-user-123/')

            # Verify file was uploaded to S3
            objects = s3.list_objects_v2(Bucket='test-cv-bucket')
            assert objects['KeyCount'] == 1
            assert objects['Contents'][0]['Key'].startswith('test-user-123/')


class TestCVUploadDynamoDBPersistence:
    """Test that parsed CVs are persisted to DynamoDB."""

    @mock_aws
    def test_cv_saved_to_dynamodb(self, mock_llm_success):
        """Parsed CV should be saved to DynamoDB."""
        _create_cvs_table()
        # Create mock resources
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket='test-cv-bucket')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-users-table',
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
        table.meta.client.get_waiter('table_exists').wait(TableName='test-users-table')

        with patch('careervp.logic.cv_parser.get_llm_router') as mock_router:
            mock_router.return_value.invoke.return_value = mock_llm_success

            from careervp.handlers.cv_upload_handler import lambda_handler

            cv_text = """
            JOHN DOE
            Senior Software Engineer
            Phone: +1-555-1234
            Email: john.doe@example.com

            EXPERIENCE
            Tech Corp | Senior Engineer | 2020 – Present
            - Led team of 5 engineers

            EDUCATION
            MIT | B.S. Computer Science | 2019

            SKILLS
            Python, AWS, JavaScript
            """

            event = generate_api_gw_event(
                {
                    'user_id': 'test-user-123',
                    'text_content': cv_text,
                }
            )
            context = generate_lambda_context()

            response = lambda_handler(event, context)

            assert response['statusCode'] == 201

            # Verify CV was saved to DynamoDB
            # Query for items with pk='test-user-123' and sk starts with 'CV#'
            client = boto3.client('dynamodb', region_name='us-east-1')
            response = client.query(
                TableName='test-users-table',
                KeyConditionExpression='pk = :pk AND begins_with(sk, :sk)',
                ExpressionAttributeValues={':pk': {'S': 'test-user-123'}, ':sk': {'S': 'CV#'}},
            )
            items = response.get('Items', [])
            assert len(items) == 1, f'Expected 1 CV item, got {len(items)}'
            # Convert DynamoDB format to plain dict
            saved_item = {k: list(v.values())[0] for k, v in items[0].items()}
            assert saved_item['full_name'] == 'John Doe'
            assert saved_item['is_parsed'] is True

    @mock_aws
    def test_openapi_payload_uses_bearer_token_for_user_id(self, mock_llm_success):
        """OpenAPI payload should resolve authenticated user_id from bearer token claims."""
        _create_cvs_table()
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket='test-cv-bucket')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test-users-table',
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

        with patch('careervp.logic.cv_parser.get_llm_router') as mock_router:
            mock_router.return_value.invoke.return_value = mock_llm_success
            from careervp.handlers.cv_upload_handler import lambda_handler

            event = generate_api_gw_event(
                {
                    'cv_content': (
                        'John Smith Senior Software Engineer with 8 years experience in Python, AWS, '
                        'distributed systems, mentoring teams, API optimization, CI/CD delivery, and '
                        'microservices architecture across high-scale production platforms.'
                    ),
                    'file_name': 'john_smith_cv.txt',
                }
            )
            event['headers'] = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer test-access-token',
            }
            event['requestContext']['authorizer'] = {'claims': {'sub': 'token-user-123'}}
            context = generate_lambda_context()

            response = lambda_handler(event, context)

            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert body['success'] is True
            assert body['status'] == 'parsed'
            assert body['cv_id']

    @mock_aws
    def test_legacy_payload_ignores_client_user_id_and_stores_authorizer_owner(self, mock_llm_success):
        """A legacy payload may not choose the owner of a stored CV."""
        _create_cvs_table()
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-users-table',
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
        table.meta.client.get_waiter('table_exists').wait(TableName='test-users-table')

        with patch('careervp.logic.cv_parser.get_llm_router') as mock_router:
            mock_router.return_value.invoke.return_value = mock_llm_success
            from careervp.handlers.cv_upload_handler import lambda_handler

            authenticated_user_id = 'authorizer-user-123'
            foreign_user_id = 'foreign-user-456'
            event = generate_api_gw_event(
                {
                    'user_id': foreign_user_id,
                    'text_content': (
                        'John Smith Senior Software Engineer with 8 years experience in Python, AWS, '
                        'distributed systems, mentoring teams, API optimization, CI/CD delivery, and '
                        'microservices architecture across high-scale production platforms.'
                    ),
                }
            )
            event['requestContext']['authorizer'] = {'claims': {'sub': authenticated_user_id}}

            response = lambda_handler(event, generate_lambda_context())

        assert response['statusCode'] == 201
        cv_id = json.loads(response['body'])['cv_id']
        stored = table.get_item(Key={'pk': authenticated_user_id, 'sk': f'CV#{cv_id}'}).get('Item')
        assert stored is not None
        assert stored['user_id'] == authenticated_user_id
        foreign_stored = table.get_item(Key={'pk': foreign_user_id, 'sk': f'CV#{cv_id}'}).get('Item')
        assert foreign_stored is None

    @mock_aws
    def test_cv_written_to_both_tables_when_cvs_table_configured(self, mock_llm_success, monkeypatch):
        """The dual write lands in cvs-table, which is where every reader now looks."""
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        for name in ('test-users-table', 'test-cvs-table'):
            dynamodb.create_table(
                TableName=name,
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
        monkeypatch.setenv('CVS_TABLE_NAME', 'test-cvs-table')

        with patch('careervp.logic.cv_parser.get_llm_router') as mock_router:
            mock_router.return_value.invoke.return_value = mock_llm_success
            from careervp.handlers.cv_upload_handler import lambda_handler

            event = generate_api_gw_event({'text_content': _VALID_CV_TEXT})
            event['requestContext']['authorizer'] = {'claims': {'sub': 'dual-write-user'}}
            response = lambda_handler(event, generate_lambda_context())

        assert response['statusCode'] == 201
        cv_id = json.loads(response['body'])['cv_id']
        key = {'pk': 'dual-write-user', 'sk': f'CV#{cv_id}'}
        assert dynamodb.Table('test-users-table').get_item(Key=key).get('Item') is not None
        assert dynamodb.Table('test-cvs-table').get_item(Key=key).get('Item') is not None

    @mock_aws
    def test_cvs_table_write_failure_is_fatal_not_a_201(self, mock_llm_success, monkeypatch):
        """Stage-1 closeout 4a.

        Every CV reader resolves from cvs-table since the repoint. A cvs-table write
        that fails while the request still returns 201 produces a CV that exists to
        nobody. The request must fail instead.
        """
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test-users-table',
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
        # Configured, distinct from TABLE_NAME, and deliberately never created:
        # the save_cv call raises ResourceNotFoundException.
        monkeypatch.setenv('CVS_TABLE_NAME', 'test-cvs-table-does-not-exist')

        with patch('careervp.logic.cv_parser.get_llm_router') as mock_router:
            mock_router.return_value.invoke.return_value = mock_llm_success
            from careervp.handlers.cv_upload_handler import lambda_handler

            event = generate_api_gw_event({'text_content': _VALID_CV_TEXT})
            event['requestContext']['authorizer'] = {'claims': {'sub': 'fatal-write-user'}}
            response = lambda_handler(event, generate_lambda_context())

        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'cv_id' not in body


class TestCVUploadErrorHandling:
    """Test error handling scenarios."""

    @mock_aws
    def test_llm_failure_returns_error(self):
        """LLM parsing failure should return appropriate error."""
        # Create mock resources
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket='test-cv-bucket')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test-users-table',
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

        llm_error_result: Result[dict[str, Any] | None] = Result(
            success=False,
            error='LLM API rate limited',
            code=ResultCode.LLM_RATE_LIMITED,
        )

        with patch('careervp.logic.cv_parser.get_llm_router') as mock_router:
            mock_router.return_value.invoke.return_value = llm_error_result

            from careervp.handlers.cv_upload_handler import lambda_handler

            cv_text = """
            JOHN DOE
            Senior Software Engineer
            Phone: +1-555-1234
            Email: john.doe@example.com

            EXPERIENCE
            Tech Corp | Senior Engineer | 2020 – Present
            - Led team of 5 engineers

            EDUCATION
            MIT | B.S. Computer Science | 2019

            SKILLS
            Python, AWS, JavaScript
            """

            event = generate_api_gw_event(
                {
                    'user_id': 'test-user-123',
                    'text_content': cv_text,
                }
            )
            context = generate_lambda_context()

            response = lambda_handler(event, context)

            assert response['statusCode'] == 429  # Rate limited
            body = json.loads(response['body'])
            assert body['success'] is False

    @mock_aws
    def test_s3_upload_failure(self):
        """S3 upload failure should return error."""
        # Don't create the S3 bucket to simulate failure
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test-users-table',
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

        from careervp.handlers.cv_upload_handler import lambda_handler

        cv_text = """
        JOHN DOE
        Senior Software Engineer
        This is a longer CV text to pass the minimum length requirement.
        """
        file_content = base64.b64encode(cv_text.encode()).decode()

        event = generate_api_gw_event(
            {
                'user_id': 'test-user-123',
                'file_content': file_content,
                'file_type': 'txt',
            }
        )
        context = generate_lambda_context()

        response = lambda_handler(event, context)

        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'store CV file' in body['error']


class TestCVUploadMalformedRequest:
    """Test handling of malformed requests."""

    @mock_aws
    def test_invalid_json_body(self):
        """Invalid JSON body should return error."""
        # Create mock resources
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket='test-cv-bucket')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test-users-table',
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

        from careervp.handlers.cv_upload_handler import lambda_handler

        event = generate_api_gw_event({})
        event['body'] = 'not valid json {'
        context = generate_lambda_context()

        response = lambda_handler(event, context)

        assert response['statusCode'] == 400

    @mock_aws
    def test_missing_user_id(self):
        """Request without user_id should fail."""
        # Create mock resources
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket='test-cv-bucket')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test-users-table',
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

        from careervp.handlers.cv_upload_handler import lambda_handler

        event = generate_api_gw_event({'text_content': 'some content'})
        context = generate_lambda_context()

        response = lambda_handler(event, context)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
