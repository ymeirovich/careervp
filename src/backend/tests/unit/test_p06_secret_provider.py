"""P-06 runtime secret provider unit tests.

scope_lock_clause: P-06
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from careervp.logic.utils.secret_provider import get_ssm_secret


def setup_function() -> None:
    # lru_cache persists across tests unless cleared explicitly.
    get_ssm_secret.cache_clear()


def test_p06_runtime_secret_provider_fetches_with_decryption() -> None:
    """AC-P06-2: SSM fetch uses WithDecryption=True."""
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {'Parameter': {'Value': 'top-secret-value'}}

    with patch('careervp.logic.utils.secret_provider.boto3.client', return_value=mock_client) as mock_boto_client:
        value = get_ssm_secret('/careervp/dev/jwt-private-key')

    assert value == 'top-secret-value'
    mock_boto_client.assert_called_once_with('ssm')
    mock_client.get_parameter.assert_called_once_with(Name='/careervp/dev/jwt-private-key', WithDecryption=True)


def test_p06_runtime_secret_provider_caches_per_parameter_name() -> None:
    """AC-P06-2: repeated calls for the same parameter do not re-fetch."""
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {'Parameter': {'Value': 'cached-value'}}

    with patch('careervp.logic.utils.secret_provider.boto3.client', return_value=mock_client):
        first = get_ssm_secret('/careervp/dev/jwt-public-key')
        second = get_ssm_secret('/careervp/dev/jwt-public-key')

    assert first == second == 'cached-value'
    mock_client.get_parameter.assert_called_once()


def test_p06_runtime_secret_provider_never_logs_secret_value() -> None:
    """AC-P06-2: the secret value itself must never be passed to the logger."""
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {'Parameter': {'Value': 'do-not-log-me'}}

    with (
        patch('careervp.logic.utils.secret_provider.boto3.client', return_value=mock_client),
        patch('careervp.logic.utils.secret_provider.logger') as mock_logger,
    ):
        get_ssm_secret('/careervp/dev/payment-provider-webhook-secret')

    for call in mock_logger.mock_calls:
        rendered_call = str(call)
        assert 'do-not-log-me' not in rendered_call
