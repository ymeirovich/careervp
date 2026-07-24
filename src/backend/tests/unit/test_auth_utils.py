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
                'claims': {'sub': 'user-from-claims'},
            }
        }
    }

    assert extract_user_id(event) == 'user-from-jwt'


def test_extract_user_id_supports_rest_authorizer_claims_sub(monkeypatch) -> None:
    monkeypatch.setenv('ENV', 'prod')
    event = {'requestContext': {'authorizer': {'claims': {'sub': 'user-from-claims'}}}}

    assert extract_user_id(event) == 'user-from-claims'


def test_extract_user_id_does_not_use_principal_id_fallback(monkeypatch) -> None:
    monkeypatch.setenv('ENV', 'prod')
    event = {'requestContext': {'authorizer': {'principalId': 'legacy-principal-id'}}}

    assert extract_user_id(event) is None


def test_extract_user_id_does_not_use_x_user_id_header_fallback(monkeypatch) -> None:
    monkeypatch.setenv('ENV', 'local')
    event = {'headers': {'x-user-id': 'local-user'}}

    # P-04: the client-supplied `x-user-id` header fallback was an identity bypass and has been
    # removed. Identity comes only from validated Cognito claims; a header-only event fails closed.
    assert extract_user_id(event) is None


def test_extract_user_id_returns_none_when_claims_missing_sub(monkeypatch) -> None:
    monkeypatch.setenv('ENV', 'dev')
    event = {'requestContext': {'authorizer': {'jwt': {'claims': {}}, 'claims': {}}}}

    assert extract_user_id(event) is None


def test_extract_user_id_returns_none_and_logs_warning_on_failure(monkeypatch) -> None:
    monkeypatch.setenv('ENV', 'prod')
    event = {'requestContext': {'authorizer': {'jwt': {'claims': {}}, 'claims': {}}}}

    with patch.object(logger, 'warning') as warning_mock:
        assert extract_user_id(event) is None
        warning_mock.assert_called_once()
