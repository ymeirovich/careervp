"""Regression guard for F-DEVX-2: the integration credential must be a Cognito ID token.

The deployed API Gateway authorizer is a COGNITO_USER_POOLS authorizer, which validates
ID tokens only. Sending the access token yields 401 on every authenticated route, which
is what silently disabled these suites. The frontend already uses the ID token
(src/frontend/lib/auth.ts getCurrentToken -> session.getIdToken()).

No token value is ever logged, asserted on, or written to evidence — only the decoded
`token_use` claim.
"""

from __future__ import annotations

try:
    from .integration_helpers import IntegrationApiClient, create_authenticated_user, decode_token_claims
except ImportError:  # pragma: no cover
    from integration_helpers import IntegrationApiClient, create_authenticated_user, decode_token_claims  # type: ignore


def test_integration_api_credential_is_an_id_token() -> None:
    client = IntegrationApiClient.from_env()
    user = create_authenticated_user(client)

    claims = decode_token_claims(user['login_token'])
    assert claims.get('token_use') == 'id', f"Integration API credential has token_use={claims.get('token_use')!r}; the authorizer accepts 'id' only."

    # Empty when an operator-supplied account was reused and no registration happened.
    if user['register_token']:
        register_claims = decode_token_claims(user['register_token'])
        assert register_claims.get('token_use') == 'id'

    # The access token is kept only for Cognito/OAuth wires that bypass the product
    # authorizer. Pin that it is a different token type, so the two cannot be swapped
    # back without this test failing.
    cognito_claims = decode_token_claims(user['cognito_access_token'])
    assert cognito_claims.get('token_use') == 'access'


def test_integration_id_token_is_accepted_and_access_token_is_not() -> None:
    client = IntegrationApiClient.from_env()
    user = create_authenticated_user(client)

    client.request('GET', '/users/me', token=user['login_token'], expected_status=200)
    client.request('GET', '/users/me', token=user['cognito_access_token'], expected_status=401)
