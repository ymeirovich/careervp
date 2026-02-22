import os

ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',')


def get_cors_headers(origin: str | None) -> dict[str, str]:
    """Return CORS headers with origin validation."""
    if not origin:
        return {
            'Access-Control-Allow-Origin': ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else '',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        }

    if origin in ALLOWED_ORIGINS:
        return {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        }

    # Reject origin not in allowlist
    return {}
