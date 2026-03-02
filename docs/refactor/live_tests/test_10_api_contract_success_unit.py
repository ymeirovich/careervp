"""Unit checks for strict contract auth-header behavior."""

from __future__ import annotations

from .test_10_api_contract_success import _build_headers, _update_state


def test_build_headers_prefers_id_token_for_protected_routes() -> None:
    state = {
        "id_token": "id.jwt.token",
        "access_token": "access.jwt.token",
    }

    headers = _build_headers("user_get.json", state)
    assert headers["Authorization"] == "Bearer id.jwt.token"


def test_build_headers_uses_refresh_token_for_refresh_payload() -> None:
    state = {
        "refresh_token": "refresh.jwt.token",
        "id_token": "id.jwt.token",
        "access_token": "access.jwt.token",
    }

    headers = _build_headers("auth_refresh.json", state)
    assert headers["Authorization"] == "Bearer refresh.jwt.token"


def test_update_state_persists_id_token_from_auth_login() -> None:
    state: dict[str, str] = {}
    _update_state(
        "auth_login.json",
        {},
        {
            "access_token": "access.jwt.token",
            "id_token": "id.jwt.token",
            "refresh_token": "refresh.jwt.token",
        },
        state,
    )

    assert state["id_token"] == "id.jwt.token"
