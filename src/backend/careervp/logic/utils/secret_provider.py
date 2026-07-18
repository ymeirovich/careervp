"""Cached runtime fetcher for secret material stored in SSM SecureString.

P-06: Lambda env vars carry only SSM parameter names, never the secret value
itself. Callers resolve the value here, once per execution environment
(cached for the lifetime of the Lambda's warm state), never logging it.
"""

from __future__ import annotations

from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from careervp.handlers.utils.observability import logger


class SecretFetchError(Exception):
    """Raised when a secret parameter cannot be fetched from SSM."""


@lru_cache(maxsize=None)
def get_ssm_secret(parameter_name: str) -> str:
    """Fetch and decrypt an SSM SecureString value, cached per parameter name.

    The cache lives for the lifetime of the Lambda execution environment
    (module-level, reset on cold start), so repeated invocations in the same
    warm container do not re-fetch the secret.
    """
    ssm_client = boto3.client('ssm')
    try:
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
    except (ClientError, BotoCoreError) as exc:
        logger.error('Failed to fetch secret from SSM', parameter=parameter_name, error=str(exc))
        raise SecretFetchError(f'Unable to fetch secret parameter {parameter_name}') from exc
    value: str = response['Parameter']['Value']
    return value
