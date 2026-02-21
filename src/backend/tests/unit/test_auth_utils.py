"""Unit tests for centralized auth extraction helpers."""

from __future__ import annotations

from unittest.mock import patch

from careervp.handlers.auth_utils import extract_user_id, logger


def test_extract_user_id_prefers_http_api_v2_jwt_sub(monkeypatch) -> None:
    monkeypatch.setenv('ENV', 'prod')
    event = {
        'requestContext': {
            'authorizer': {
                'jwt': {'claims': {'sub': 'user-from-jwt'}},
                'principalId': 'user-from-principal',
            }
        }
    }

    assert extract_user_id(event) == 'user-from-jwt'


def test_extract_user_id_falls_back_to_lambda_authorizer_principal_id(monkeypatch) -> None:
    monkeypatch.setenv('ENV', 'prod')
    event = {'requestContext': {'authorizer': {'principalId': 'user-from-principal'}}}

    assert extract_user_id(event) == 'user-from-principal'


def test_extract_user_id_uses_header_fallback_in_local_env_with_lowercase_key(monkeypatch) -> None:
    monkeypatch.setenv('ENV', 'local')
    event = {'headers': {'x-user-id': 'local-user-lower'}}

    assert extract_user_id(event) == 'local-user-lower'


def test_extract_user_id_uses_header_fallback_in_local_env_with_mixed_case_key(monkeypatch) -> None:
    monkeypatch.setenv('ENV', 'local')
    event = {'headers': {'X-User-Id': 'local-user-mixed'}}

    assert extract_user_id(event) == 'local-user-mixed'


def test_extract_user_id_does_not_use_header_fallback_outside_local(monkeypatch) -> None:
    monkeypatch.setenv('ENV', 'dev')
    event = {'headers': {'x-user-id': 'should-not-be-used'}}

    assert extract_user_id(event) is None


def test_extract_user_id_returns_none_and_logs_warning_on_failure(monkeypatch) -> None:
    monkeypatch.setenv('ENV', 'prod')
    event = {'requestContext': {'authorizer': {'jwt': {'claims': {}}, 'principalId': '   '}}}

    with patch.object(logger, 'warning') as warning_mock:
        assert extract_user_id(event) is None
        warning_mock.assert_called_once()
