"""
CV Upload Handler Tests.
Uses moto to mock S3 and DynamoDB, and pytest-mock to mock LLM calls.

Per docs/specs/01-cv-parser.md and CLAUDE.md patterns.
"""

import base64
import json
import os
from typing import Any, Dict, cast
from unittest.mock import MagicMock, patch

import boto3
import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_aws

from careervp.models.result import Result, ResultCode


@pytest.fixture(scope='function', autouse=True)
def aws_env_vars():
    """Set up environment variables for moto and Lambda Powertools."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'careervp-test'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    os.environ['TABLE_NAME'] = 'test-users-table'
    os.environ['CV_BUCKET_NAME'] = 'test-cv-bucket'
    os.environ['IDEMPOTENCY_TABLE_NAME'] = 'test-idempotency-table'
    yield
    # Cleanup
    for key in [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'AWS_SECURITY_TOKEN',
        'AWS_SESSION_TOKEN',
        'TABLE_NAME',
        'CV_BUCKET_NAME',
        'IDEMPOTENCY_TABLE_NAME',
    ]:
        os.environ.pop(key, None)


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


def generate_api_gw_event(body: Dict[str, Any], path: str = '/api/cv', method: str = 'POST') -> Dict[str, Any]:
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
        },
        'pathParameters': None,
        'stageVariables': None,
        'body': json.dumps(body) if body else None,
        'isBase64Encoded': False,
    }


def generate_lambda_context() -> LambdaContext:
    """Generate a mock Lambda context."""
    context = MagicMock()
    context.aws_request_id = 'test-request-id'
    context.function_name = 'cv-upload-handler'
    context.memory_limit_in_mb = 1024
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:cv-upload'
    return cast(LambdaContext, context)


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

            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert body['user_cv'] is not None
            assert body['user_cv']['full_name'] == 'John Doe'
            assert body['language_detected'] == 'en'

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

            assert response['statusCode'] == 200
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

            assert response['statusCode'] == 200

            # Verify CV was saved to DynamoDB
            saved_item = table.get_item(Key={'pk': 'test-user-123', 'sk': 'CV'})
            assert 'Item' in saved_item
            assert saved_item['Item']['full_name'] == 'John Doe'
            assert saved_item['Item']['is_parsed'] is True


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

        llm_error_result: Result[Dict[str, Any]] = Result(
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
