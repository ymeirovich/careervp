"""Shared pytest configuration for CareerVP backend tests."""

import os

import pytest

from careervp.dal.dynamo_dal_handler import DynamoDalHandler

# Ensure aws-lambda-env-modeler re-reads environment variables between tests.
os.environ['LAMBDA_ENV_MODELER_DISABLE_CACHE'] = 'true'

# Baseline AWS/moto configuration so tests never reach real AWS.
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['AWS_REGION'] = 'us-east-1'

# Default application env vars used across handlers.
os.environ['POWERTOOLS_SERVICE_NAME'] = 'careervp-test'
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
os.environ['TABLE_NAME'] = 'test-users-table'
os.environ['CV_BUCKET_NAME'] = 'test-cv-bucket'
os.environ['IDEMPOTENCY_TABLE_NAME'] = 'test-idempotency-table'


@pytest.fixture(autouse=True)
def reset_dynamo_dal_singleton():
    """Ensure each test gets a fresh DAL instance with its requested table."""
    DynamoDalHandler.reset_instance()
    yield
    DynamoDalHandler.reset_instance()


@pytest.fixture(scope='session', autouse=True)
def ensure_lambda_build_dir():
    """Create placeholder lambda asset directory expected by CDK tests."""
    from pathlib import Path

    backend_root = Path(__file__).resolve().parent.parent
    lambdas_dir = backend_root / '.build' / 'lambdas'
    lambdas_dir.mkdir(parents=True, exist_ok=True)
    (lambdas_dir / '.placeholder').touch()
