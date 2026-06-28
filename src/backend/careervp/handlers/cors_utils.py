import os
from typing import Any

_ALLOWED_ORIGINS: set[str] = {o.strip() for o in os.getenv('ALLOWED_ORIGINS', '').split(',') if o.strip()}

_current_request_origin: str | None = None


def set_request_origin(event: dict[str, Any]) -> None:
    """Call at the top of each Lambda handler to capture the request Origin header."""
    global _current_request_origin
    raw_headers: dict[str, str] = event.get('headers') or {}
    _current_request_origin = raw_headers.get('origin') or raw_headers.get('Origin')


def get_cors_headers(origin: str | None) -> dict[str, str]:
    """Return CORS headers with origin validation."""
    resolved = origin if origin is not None else _current_request_origin
    if not resolved:
        return {}

    if resolved in _ALLOWED_ORIGINS:
        return {
            'Access-Control-Allow-Origin': resolved,
            'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        }

    # Reject origin not in allowlist
    return {}
