"""
L1.3 — Health Check Unit Tests

Validates: health_handler reports anthropic/dynamodb (not bedrock), returns 200 on degraded
Spec: docs/best_practices/yaml/lambda_handler_spec.yaml
Payload: docs/refactor/payloads/beta_l1_persistence_test.json#L1_3_health_check
Invariant: I2
Results: docs/beta/execution_results/L1_3_results.md
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
os.environ.setdefault('ENVIRONMENT', 'test')


def _make_health_event():
    return {
        'httpMethod': 'GET',
        'path': '/health',
        'requestContext': {},
        'headers': {},
        'queryStringParameters': None,
        'body': None,
    }


def _call_health_handler(event=None):
    """Import and call health_handler.lambda_handler."""
    from careervp.handlers import health_handler

    return health_handler.lambda_handler(event or _make_health_event(), None)


def _call_health_check():
    """Import and call health_handler.health_check directly."""
    from careervp.handlers import health_handler

    return health_handler.health_check()


@pytest.mark.unit
class TestHealthReportsBedockRemoved:
    """Health endpoint must not report 'bedrock' — that service was replaced by Anthropic SDK."""

    def test_health_reports_anthropic_not_bedrock(self):
        """Response body does not contain 'bedrock' key in services."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            response = _call_health_handler()
            body = json.loads(response['body'])
            assert 'bedrock' not in body.get('services', {}), f"'bedrock' key still in services: {body.get('services')}"

    def test_health_response_has_anthropic_key(self):
        """Response body contains 'anthropic' key in services."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            result = _call_health_check()
            assert 'anthropic' in result.get('services', {}), f"'anthropic' missing from services: {result.get('services')}"

    def test_health_response_has_dynamodb_key(self):
        """Response body contains 'dynamodb' key in services."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            result = _call_health_check()
            assert 'dynamodb' in result.get('services', {}), f"'dynamodb' missing from services: {result.get('services')}"

    def test_health_response_has_no_lambda_key(self):
        """Response body does not contain 'lambda' key (not a real check)."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            result = _call_health_check()
            assert 'lambda' not in result.get('services', {}), f"'lambda' key should not be in services: {result.get('services')}"


@pytest.mark.unit
class TestHealthAnthropicCheck:
    """Health check tests Anthropic API connectivity."""

    def test_health_reports_anthropic_healthy_on_success(self):
        """Mock Anthropic models.list() success → services.anthropic = 'healthy'."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            result = _call_health_check()
            assert result['services']['anthropic'] == 'healthy', f"Expected 'healthy', got: {result['services'].get('anthropic')}"

    def test_health_reports_anthropic_degraded_on_error(self):
        """Mock Anthropic models.list() raising exception → services.anthropic = 'degraded'."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.side_effect = Exception('API unreachable')
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            result = _call_health_check()
            assert result['services']['anthropic'] == 'degraded', f"Expected 'degraded', got: {result['services'].get('anthropic')}"

    def test_health_reports_anthropic_degraded_on_timeout(self):
        """Mock Anthropic call timing out → services.anthropic = 'degraded'."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.side_effect = TimeoutError('timeout')
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            result = _call_health_check()
            assert result['services']['anthropic'] == 'degraded'

    def test_health_does_not_raise_on_anthropic_error(self):
        """health_check() does not propagate Anthropic exceptions."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.side_effect = RuntimeError('boom')
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            # Must not raise
            result = _call_health_check()
            assert isinstance(result, dict)


@pytest.mark.unit
class TestHealthDynamoDBCheck:
    """Health check tests DynamoDB connectivity."""

    def test_health_reports_dynamodb_healthy(self):
        """Mock describe_table success → services.dynamodb = 'healthy'."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.return_value = {'Table': {'TableStatus': 'ACTIVE'}}
            result = _call_health_check()
            assert result['services']['dynamodb'] == 'healthy', f"Expected 'healthy', got: {result['services'].get('dynamodb')}"

    def test_health_reports_dynamodb_degraded_on_error(self):
        """Mock describe_table raising exception → services.dynamodb = 'degraded'."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.side_effect = Exception('table unavailable')
            result = _call_health_check()
            assert result['services']['dynamodb'] == 'degraded', f"Expected 'degraded', got: {result['services'].get('dynamodb')}"

    def test_health_does_not_raise_on_dynamodb_error(self):
        """health_check() does not propagate DynamoDB exceptions."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.side_effect = RuntimeError('dynamodb down')
            result = _call_health_check()
            assert isinstance(result, dict)


@pytest.mark.unit
class TestHealthResponseShape:
    """Health response always returns 200 with status/services shape."""

    def test_health_returns_200_even_when_degraded(self):
        """Even with all services degraded, HTTP status is 200 (not 500)."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.side_effect = Exception('down')
            mock_boto.return_value.describe_table.side_effect = Exception('down')
            response = _call_health_handler()
            assert response['statusCode'] == 200, f'Expected 200, got {response["statusCode"]}'

    def test_health_response_has_status_field(self):
        """Response contains top-level 'status' field."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            result = _call_health_check()
            assert 'status' in result, "'status' missing from health_check result"
            assert result['status'] in ('healthy', 'degraded')

    def test_health_response_has_services_field(self):
        """Response contains 'services' dict with individual service statuses."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            result = _call_health_check()
            assert 'services' in result
            assert isinstance(result['services'], dict)

    def test_health_status_degraded_when_any_service_degraded(self):
        """Top-level status = 'degraded' if any service is degraded."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.side_effect = Exception('anthropic down')
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            result = _call_health_check()
            assert result['status'] == 'degraded', f"Expected 'degraded' when anthropic fails, got: {result['status']}"

    def test_health_status_healthy_when_all_services_healthy(self):
        """Top-level status = 'healthy' only when all services healthy."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            result = _call_health_check()
            assert result['status'] == 'healthy', f"Expected 'healthy' when all services pass, got: {result['status']}"

    def test_health_response_has_timestamp(self):
        """Response contains 'timestamp' field in ISO format."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            result = _call_health_check()
            assert 'timestamp' in result

    def test_health_response_has_version(self):
        """Response contains 'version' field."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            result = _call_health_check()
            assert 'version' in result


@pytest.mark.unit
class TestHealthRoutePublic:
    """Health check route must be public (no auth required)."""

    def test_health_requires_no_auth(self):
        """Health handler does NOT return 401 when requestContext has no authorizer."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            event = _make_health_event()  # no requestContext/authorizer
            response = _call_health_handler(event)
            assert response['statusCode'] != 401, 'Health check should not require auth'

    def test_health_works_without_request_context(self):
        """Health handler does not fail if requestContext is empty."""
        with patch('anthropic.Anthropic') as mock_cls, patch('boto3.client') as mock_boto:
            mock_cls.return_value.models.list.return_value = MagicMock()
            mock_boto.return_value.describe_table.return_value = {'Table': {}}
            event = _make_health_event()
            event['requestContext'] = {}
            response = _call_health_handler(event)
            assert response['statusCode'] == 200
