"""Gap analysis handler helpers (CORS + error responses)."""

from __future__ import annotations

import json
from typing import Any


def _cors_headers() -> dict[str, str]:
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Content-Type': 'application/json',
    }


def _error_response(status_code: int, message: str, code: str) -> dict[str, Any]:
    return {
        'statusCode': int(status_code),
        'headers': _cors_headers(),
        'body': json.dumps({'error': message, 'code': code}),
    }
