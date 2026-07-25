"""Lambda handler for billing routes.

Routes:
  POST /billing/checkout       → BillingService.handle_checkout
  GET  /users/me/subscription  → BillingService.handle_get_subscription
  POST /billing/portal         → BillingService.handle_portal
"""

from __future__ import annotations

import base64
import json
import os
from http import HTTPStatus
from typing import Any, cast

from careervp.dal.subscription_repository import SubscriptionRepository
from careervp.dal.user_repository import UserRepository
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers, set_request_origin
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.billing_service import BillingService
from careervp.logic.utils.secret_provider import get_ssm_secret
from careervp.logic.webhook_service import WebhookService
from careervp.payment_providers.factory import get_payment_provider
from careervp.payment_providers.interface import PaymentProviderError

# ─── Cold-start singletons ────────────────────────────────────────────────────

_billing_service: BillingService | None = None
_webhook_service: WebhookService | None = None


def _get_webhook_service() -> WebhookService:
    global _webhook_service
    if _webhook_service is None:
        primary_secret_param = os.environ['PAYMENT_PROVIDER_WEBHOOK_SECRET_SSM_PARAM']
        previous_secret_param = os.environ.get('PAYMENT_PROVIDER_WEBHOOK_SECRET_PREVIOUS_SSM_PARAM')
        primary_secret = get_ssm_secret(primary_secret_param)
        previous_secret = get_ssm_secret(previous_secret_param) if previous_secret_param else 'none'
        _webhook_service = WebhookService(
            subscription_repo=SubscriptionRepository(),
            payment_provider=get_payment_provider(),
            primary_secret=primary_secret,
            previous_secret=previous_secret,
        )
    return _webhook_service


def _get_billing_service() -> BillingService:
    global _billing_service
    if _billing_service is None:
        _billing_service = BillingService(
            subscription_repo=SubscriptionRepository(),
            user_repo=UserRepository(),
            payment_provider=get_payment_provider(),
        )
    return _billing_service


# ─── Handler ──────────────────────────────────────────────────────────────────


@logger.inject_lambda_context(log_event=False)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(raise_on_empty_metrics=False)
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ARG001
    """Route billing API requests to BillingService methods."""
    set_request_origin(event)
    headers = _cors_headers()
    method = str(event.get('httpMethod', '')).upper()
    path = str(event.get('path', '')).rstrip('/')

    logger.info('billing request', http_method=method, path=path)

    if method == 'OPTIONS':
        return _response(HTTPStatus.OK, {'success': True}, headers)

    # ── POST /billing/webhook (no auth, no CORS) ──────────────────────────────
    if method == 'POST' and path == '/billing/webhook':
        payload_bytes = _extract_raw_body(event)
        sig_header = (event.get('headers') or {}).get('Payment-Provider-Signature', '')
        wh_svc = _get_webhook_service()
        try:
            result = wh_svc.handle_webhook(payload_bytes, sig_header)
        except PaymentProviderError:
            return _response(HTTPStatus.BAD_REQUEST, {'error': 'invalid_signature'}, {})
        status_code = result.get('status_code', 200)
        body = {k: v for k, v in result.items() if k != 'status_code'}
        return _response(status_code, body, {})

    user_id = extract_user_id(event)
    if not user_id:
        return _response(
            HTTPStatus.UNAUTHORIZED,
            {'error': 'Missing or invalid authentication token'},
            headers,
        )

    svc = _get_billing_service()

    # ── GET /users/me/subscription ────────────────────────────────────────────
    if method == 'GET' and path == '/users/me/subscription':
        result = svc.handle_get_subscription(user_id)
        return _billing_response(result, headers)

    # ── POST /billing/checkout ────────────────────────────────────────────────
    if method == 'POST' and path == '/billing/checkout':
        checkout_body = _parse_body(event)
        if checkout_body is None:
            return _response(HTTPStatus.BAD_REQUEST, {'error': 'Invalid JSON body'}, headers)
        result = svc.handle_checkout(
            user_id=user_id,
            plan=str(checkout_body.get('plan') or ''),
            success_url=str(checkout_body.get('success_url') or ''),
            cancel_url=str(checkout_body.get('cancel_url') or ''),
        )
        return _billing_response(result, headers)

    # ── POST /billing/portal ──────────────────────────────────────────────────
    if method == 'POST' and path == '/billing/portal':
        portal_body = _parse_body(event)
        if portal_body is None:
            return _response(HTTPStatus.BAD_REQUEST, {'error': 'Invalid JSON body'}, headers)
        result = svc.handle_portal(
            user_id=user_id,
            return_url=str(portal_body.get('return_url') or ''),
        )
        return _billing_response(result, headers)

    return _response(HTTPStatus.NOT_FOUND, {'error': 'Endpoint not found'}, headers)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Standard Lambda entrypoint alias."""
    return cast(dict[str, Any], handler(event, context))


# ─── Utilities ────────────────────────────────────────────────────────────────


def _extract_raw_body(event: dict[str, Any]) -> bytes:
    """Return the raw request body bytes (handles base64-encoded API Gateway payloads)."""
    if event.get('isBase64Encoded'):
        return base64.b64decode(event['body'])
    return (event.get('body') or '').encode('utf-8')


def _parse_body(event: dict[str, Any]) -> dict[str, Any] | None:
    """Parse JSON body from the event; returns None on decode error or non-object JSON."""
    try:
        result = json.loads(event.get('body') or '{}')
        return result if isinstance(result, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _billing_response(service_result: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Convert a BillingService result dict into a Lambda HTTP response."""
    status_code = service_result.get('status_code', 200)
    body = {k: v for k, v in service_result.items() if k != 'status_code'}
    return _response(status_code, body, headers)


def _cors_headers() -> dict[str, str]:
    headers = get_cors_headers(None)
    headers.setdefault('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    headers.setdefault('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return headers


def _response(
    status: int | HTTPStatus,
    body: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    status_code = int(status.value) if isinstance(status, HTTPStatus) else int(status)
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body),
    }
