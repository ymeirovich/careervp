# Live Tests - Auth Bootstrap
# Validates Cognito (or configured fallback) token acquisition and authenticated user call.

import json
from typing import Any

import pytest
import requests

from .conftest import API_BASE, get_token_metadata, _decode_jwt_claims


def print_response(test_name: str, endpoint: str, status_code: int, response_data: Any):
    output = {
        "test_name": test_name,
        "endpoint": endpoint,
        "status_code": status_code,
        "response": response_data,
    }
    print(f"\n=== RESPONSE {test_name} ===")
    print(json.dumps(output, indent=2, default=str))


class TestAuthBootstrap:
    @pytest.mark.requires_auth
    def test_cognito_login_returns_jwt(self, auth_token):
        assert isinstance(auth_token, str)
        assert len(auth_token) > 20
        assert auth_token.count(".") >= 2

        metadata = get_token_metadata()
        assert metadata.get("source") in {"cognito", "api"}

    @pytest.mark.requires_auth
    def test_users_me_usage_with_real_token_returns_200(self, auth_headers):
        token = auth_headers.get("Authorization", "").replace("Bearer ", "")
        claims = _decode_jwt_claims(token) if token else {}
        print_response(
            "auth_token_claims",
            "fixture/auth_headers",
            0,
            {"token_use": claims.get("token_use"), "iss": claims.get("iss"), "aud": claims.get("aud"), "client_id": claims.get("client_id")},
        )
        response = requests.get(f"{API_BASE}/users/me/usage", headers=auth_headers, timeout=20)
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_users_me_usage_with_real_token_returns_200",
            "GET /users/me/usage",
            response.status_code,
            data,
        )

        assert response.status_code == 200
