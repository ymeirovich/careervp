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
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv(POWERTOOLS_SERVICE_NAME, SERVICE_NAME)
        mp.setenv(POWER_TOOLS_LOG_LEVEL, 'DEBUG')
        mp.setenv('REST_API', 'https://www.ranthebuilder.cloud/api')
        mp.setenv('ROLE_ARN', 'arn:partition:service:region:account-id:resource-type:resource-id')
        mp.setenv('CONFIGURATION_APP', SERVICE_NAME)
        mp.setenv('CONFIGURATION_ENV', ENVIRONMENT)
        mp.setenv('CONFIGURATION_NAME', CONFIGURATION_NAME)
        mp.setenv('CONFIGURATION_MAX_AGE_MINUTES', '5')
        mp.setenv('AWS_DEFAULT_REGION', 'us-east-1')  # used for appconfig mocked boto calls
        mp.setenv('TABLE_NAME', _safe_stack_output(TABLE_NAME_OUTPUT, 'TABLE_NAME', 'local-careervp-users'))
        mp.setenv(
            'IDEMPOTENCY_TABLE_NAME',
            _safe_stack_output(IDEMPOTENCY_TABLE_NAME_OUTPUT, 'IDEMPOTENCY_TABLE_NAME', 'local-careervp-idempotency'),
        )
        yield


@pytest.fixture(scope='module', autouse=True)
def table_name():
    return os.environ['TABLE_NAME']
