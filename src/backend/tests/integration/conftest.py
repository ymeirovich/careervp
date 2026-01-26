import os

import pytest
from botocore.exceptions import ClientError, NoCredentialsError
from cdk.careervp.constants import (
    CONFIGURATION_NAME,
    ENVIRONMENT,
    IDEMPOTENCY_TABLE_NAME_OUTPUT,
    POWER_TOOLS_LOG_LEVEL,
    POWERTOOLS_SERVICE_NAME,
    SERVICE_NAME,
    TABLE_NAME_OUTPUT,
)

from tests.utils import get_stack_output


def _safe_stack_output(output_name: str, env_key: str, default_value: str) -> str:
    """
    Attempt to load a CloudFormation output, but fall back to an environment override or default.
    Local tests (moto, unit tests) should not require a deployed stack to run.
    """
    preconfigured = os.environ.get(env_key)
    if preconfigured:
        return preconfigured
    try:
        return get_stack_output(output_name)
    except (ClientError, NoCredentialsError):
        return default_value


@pytest.fixture(scope='module', autouse=True)
def init():
    os.environ[POWERTOOLS_SERVICE_NAME] = SERVICE_NAME
    os.environ[POWER_TOOLS_LOG_LEVEL] = 'DEBUG'
    os.environ['REST_API'] = 'https://www.ranthebuilder.cloud/api'
    os.environ['ROLE_ARN'] = 'arn:partition:service:region:account-id:resource-type:resource-id'
    os.environ['CONFIGURATION_APP'] = SERVICE_NAME
    os.environ['CONFIGURATION_ENV'] = ENVIRONMENT
    os.environ['CONFIGURATION_NAME'] = CONFIGURATION_NAME
    os.environ['CONFIGURATION_MAX_AGE_MINUTES'] = '5'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'  # used for appconfig mocked boto calls
    os.environ['TABLE_NAME'] = _safe_stack_output(TABLE_NAME_OUTPUT, 'TABLE_NAME', 'local-careervp-users')
    os.environ['IDEMPOTENCY_TABLE_NAME'] = _safe_stack_output(IDEMPOTENCY_TABLE_NAME_OUTPUT, 'IDEMPOTENCY_TABLE_NAME', 'local-careervp-idempotency')


@pytest.fixture(scope='module', autouse=True)
def table_name():
    return os.environ['TABLE_NAME']
