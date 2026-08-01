"""Regression guard for F-DEVX-2: the E2E credential must be a Cognito ID token.

The deployed API Gateway authorizer is a COGNITO_USER_POOLS authorizer, which validates
ID tokens only. Sending the access token yields 401 on every authenticated route, which
is what silently disabled these suites. The frontend already uses the ID token
(src/frontend/lib/auth.ts getCurrentToken -> session.getIdToken()).

No token value is ever logged, asserted on, or written to evidence — only the decoded
`token_use` claim.
"""

from __future__ import annotations

try:
    from .e2e_helpers import E2EClient, decode_token_claims, register_and_login
except ImportError:  # pragma: no cover
    from e2e_helpers import E2EClient, decode_token_claims, register_and_login  # type: ignore


def test_e2e_api_credential_is_an_id_token() -> None:
    client = E2EClient.from_env()
    user = register_and_login(client)

    claims = decode_token_claims(user['token'])
    assert claims.get('token_use') == 'id', f"E2E API credential has token_use={claims.get('token_use')!r}; the authorizer accepts 'id' only."

    # The access token is kept only for Cognito/OAuth wires that bypass the product
    # authorizer. Pin that it is a different token type, so the two cannot be swapped
    # back without this test failing.
    cognito_claims = decode_token_claims(user['cognito_access_token'])
    assert cognito_claims.get('token_use') == 'access'


def test_e2e_id_token_is_accepted_and_access_token_is_not() -> None:
    client = E2EClient.from_env()
    user = register_and_login(client)

    client.request('GET', '/users/me', token=user['token'], expected_status=200)
    client.request('GET', '/users/me', token=user['cognito_access_token'], expected_status=401)
