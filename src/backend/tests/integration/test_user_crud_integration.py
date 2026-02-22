from __future__ import annotations

try:
    from .integration_helpers import IntegrationApiClient, create_authenticated_user, unwrap_payload
except ImportError:  # pragma: no cover
    from integration_helpers import IntegrationApiClient, create_authenticated_user, unwrap_payload


def test_user_crud_integration() -> None:
    client = IntegrationApiClient.from_env()
    user = create_authenticated_user(client)
    token = user['login_token']

    me_response = client.request('GET', '/users/me', token=token, expected_status=200)
    me_payload = unwrap_payload(me_response.data)
    assert me_payload.get('email') == user['email']
    assert me_payload.get('name') == user['name']

    update_payload = {'name': 'Updated Name', 'timezone': 'US/Eastern'}
    update_response = client.request(
        'PUT',
        '/users/me',
        token=token,
        json_body=update_payload,
        expected_status=200,
    )
    updated_profile = unwrap_payload(update_response.data)
    assert updated_profile.get('name') == 'Updated Name'
    assert updated_profile.get('timezone') == 'US/Eastern'

    persisted_response = client.request('GET', '/users/me', token=token, expected_status=200)
    persisted_profile = unwrap_payload(persisted_response.data)
    assert persisted_profile.get('name') == 'Updated Name'
    assert persisted_profile.get('timezone') == 'US/Eastern'

    client.request(
        'PUT',
        '/users/me',
        token=token,
        json_body={'name': ''},
        expected_status=400,
    )
