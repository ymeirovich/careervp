from __future__ import annotations

try:
    from .integration_helpers import IntegrationApiClient, create_authenticated_user, require_field, unwrap_payload
except ImportError:  # pragma: no cover
    from integration_helpers import IntegrationApiClient, create_authenticated_user, require_field, unwrap_payload


def test_auth_flow_integration() -> None:
    client = IntegrationApiClient.from_env()
    user = create_authenticated_user(client)
    login_token = user['login_token']
    register_token = user['register_token']

    assert login_token != register_token

    me_response = client.request('GET', '/users/me', token=login_token, expected_status=200)
    me_payload = unwrap_payload(me_response.data)
    assert me_payload.get('email') == user['email']
    assert me_payload.get('name') == user['name']

    client.request('GET', '/users/me', expected_status=401)

    refresh_response = client.request('POST', '/auth/refresh', token=login_token, expected_status=200)
    refreshed_token = require_field(refresh_response.data, 'access_token')
    assert refreshed_token != login_token

    refreshed_me_response = client.request('GET', '/users/me', token=refreshed_token, expected_status=200)
    refreshed_me_payload = unwrap_payload(refreshed_me_response.data)
    assert refreshed_me_payload.get('email') == user['email']
    assert refreshed_me_payload.get('name') == user['name']
