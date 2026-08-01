from __future__ import annotations

try:
    from .integration_helpers import IntegrationApiClient, create_authenticated_user, require_field, unwrap_payload
except ImportError:  # pragma: no cover
    from integration_helpers import IntegrationApiClient, create_authenticated_user, require_field, unwrap_payload  # type: ignore


def test_auth_flow_integration() -> None:
    client = IntegrationApiClient.from_env()
    # This test is about the registration flow itself, so it never reuses an account.
    user = create_authenticated_user(client, require_fresh_registration=True)
    login_token = user['login_token']
    register_token = user['register_token']

    assert login_token != register_token

    me_response = client.request('GET', '/users/me', token=login_token, expected_status=200)
    me_payload = unwrap_payload(me_response.data)
    assert me_payload.get('email') == user['email']
    assert me_payload.get('name') == user['name']

    client.request('GET', '/users/me', expected_status=401)

    # /auth/refresh sits outside the product authorizer and consumes the refresh token,
    # and it returns a fresh ID token that the authorizer will accept.
    refresh_response = client.request('POST', '/auth/refresh', token=user['refresh_token'], expected_status=200)
    refreshed_token = require_field(refresh_response.data, 'id_token')
    assert refreshed_token != login_token

    refreshed_me_response = client.request('GET', '/users/me', token=refreshed_token, expected_status=200)
    refreshed_me_payload = unwrap_payload(refreshed_me_response.data)
    assert refreshed_me_payload.get('email') == user['email']
    assert refreshed_me_payload.get('name') == user['name']
