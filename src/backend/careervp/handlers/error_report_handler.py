"""Lambda handler for client-side error reports.

The frontend ErrorBoundary posts to the Next.js `/api/errors/` route, which
forwards here (server-to-server). This handler's only job is to land those
reports in backend CloudWatch via the shared Powertools logger, so client
errors sit alongside the rest of the structured backend logs.

Public (no Cognito): error reports fire on pre-auth pages (login, signup) and
the SSR forwarder carries no user token. Abuse is bounded by the API Gateway
stage throttle plus the field-length caps below.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.utilities.typing import LambdaContext

from careervp.handlers.cors_utils import get_cors_headers, set_request_origin
from careervp.handlers.utils.observability import logger, tracer

# Field-length caps: a telemetry sink must never let an oversized stack trace
# flood the log group or balloon a single log line.
_MAX_FIELD_LEN = 4000
_MAX_STACK_LEN = 8000


def _truncate(value: Any, limit: int) -> str:
    text = '' if value is None else str(value)
    if len(text) <= limit:
        return text
    return f'{text[:limit]}…[truncated {len(text) - limit} chars]'


def _parse_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get('body')
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Accept a client error report and log it; always ack so the client never retries."""
    _ = context
    set_request_origin(event)
    method = str(event.get('httpMethod', 'POST')).upper()

    if method == 'OPTIONS':
        return _build_response(HTTPStatus.OK, {'status': 'ok'})

    report = _parse_body(event)

    logger.warning(
        'client_error',
        boundary_key=_truncate(report.get('boundary_key', 'unknown'), 200),
        client_error=_truncate(report.get('error'), _MAX_FIELD_LEN),
        url=_truncate(report.get('url'), _MAX_FIELD_LEN),
        user_agent=_truncate(report.get('user_agent'), _MAX_FIELD_LEN),
        stack=_truncate(report.get('stack'), _MAX_STACK_LEN),
    )

    return _build_response(HTTPStatus.ACCEPTED, {'status': 'received'})


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    headers = get_cors_headers(None)
    headers['Content-Type'] = 'application/json'
    return {
        'statusCode': status_code.value,
        'headers': headers,
        'body': json.dumps(body),
    }
