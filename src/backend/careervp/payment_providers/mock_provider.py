"""
MockProvider — launch-rehearsal payment provider (clause P-25).

Unlike PlaceholderPaymentProvider (which skips signature verification and is
inert outside PAYMENT_PROVIDER_PLACEHOLDER mode), MockProvider performs a
*cryptographically real* webhook verification so the negative tests it backs are
meaningful rather than tautological:

  * Signatures use a single compound header string identical in shape to Stripe's
    ``Stripe-Signature``:  ``t=<unix>,v1=<hex-hmac-sha256>``  where
    ``v1 = HMAC-SHA256(secret, f"{t}.{raw_payload}")`` over the exact raw body
    bytes (B-2-1).
  * The signed timestamp is read out of that ONE string — never from the payload
    body — and a delivery whose timestamp is older than
    ``WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS`` is rejected with the distinct replay
    error code, so a valid-digest / stale-timestamp replay cannot slip through.
  * Any mutation of the signed body invalidates the digest, so a tampered payload
    is rejected even though the signature header is unchanged.

The concrete Stripe implementation (P-25b) will verify against this exact scheme;
2.0b cross-checks the format against real Stripe before the money path (2.1).

Secrets (P-06): the caller passes the webhook secret by value (resolved from the
parameter store by name upstream); no literal secret lives in this module.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any

from careervp.payment_providers.interface import (
    CheckoutSession,
    CustomerRecord,
    PaymentProviderError,
    PaymentProviderInterface,
    PortalSession,
    WebhookEvent,
)

# Freshness window for the signed timestamp, in seconds. Matches Stripe's default
# tolerance and the constant the P-25 RED tests sign against (B-2-1).
WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300

# Distinct error code for a cryptographically valid but stale (replayed) signature,
# kept separate from a generic signature-verification failure so callers and tests
# can tell a replay apart from a forged/tampered payload.
WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE = 'WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE'
WEBHOOK_SIGNATURE_VERIFICATION_FAILED = 'WEBHOOK_SIGNATURE_VERIFICATION_FAILED'
WEBHOOK_SIGNATURE_MALFORMED = 'WEBHOOK_SIGNATURE_MALFORMED'
WEBHOOK_PAYLOAD_INVALID = 'WEBHOOK_PAYLOAD_INVALID'


class MockProvider:
    """PaymentProviderInterface implementation with real HMAC webhook verification.

    Returns realistic checkout/portal/customer/subscription objects and preserves
    the frontend checkout/portal URL contract, so billing can be exercised
    end-to-end without a real payment processor.
    """

    # ── Customer / checkout / portal ────────────────────────────────────────────

    def create_customer(self, email: str, metadata: dict[str, str]) -> CustomerRecord:
        return CustomerRecord(
            customer_id=f'cus_mock_{uuid.uuid4().hex[:12]}',
            email=email,
            metadata=dict(metadata),
        )

    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        plan: str,
        user_id: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession:
        session_id = f'cs_mock_{uuid.uuid4().hex[:16]}'
        # A realistic hosted-checkout URL (the shape a real provider redirects to),
        # not the caller's success_url — the frontend consumes `checkout_url` as-is.
        checkout_url = f'https://mock-pay.careervp.test/checkout/{session_id}'
        return CheckoutSession(
            session_id=session_id,
            checkout_url=checkout_url,
            customer_id=customer_id,
            metadata={'user_id': user_id, 'plan': plan, 'price_id': price_id},
        )

    def create_portal_session(self, customer_id: str, return_url: str) -> PortalSession:
        session_id = f'bps_mock_{uuid.uuid4().hex[:16]}'
        portal_url = f'https://mock-pay.careervp.test/portal/{session_id}'
        return PortalSession(session_id=session_id, portal_url=portal_url)

    def get_price_map(self) -> dict[str, str]:
        """Return the plan → price-ID map (env-overridable, realistic defaults)."""
        return {
            'monthly': os.environ.get('PRICE_ID_MONTHLY', 'price_mock_monthly'),
            'quarterly': os.environ.get('PRICE_ID_QUARTERLY', 'price_mock_quarterly'),
        }

    def retrieve_subscription(self, subscription_id: str) -> dict[str, Any]:
        """Return a realistic subscription object for the given ID.

        Shape mirrors the fields the webhook and reconciliation paths read
        (``status``, period bounds, ``items[].price.id``, ``cancel_at_period_end``).
        """
        now = int(time.time())
        return {
            'id': subscription_id,
            'status': 'active',
            'current_period_start': now,
            'current_period_end': now + 30 * 24 * 3600,
            'cancel_at_period_end': False,
            'items': {'data': [{'price': {'id': 'price_mock_monthly'}}]},
        }

    # ── Webhook verification (the whole point of the mock) ──────────────────────

    def construct_webhook_event(self, payload: bytes, signature: str, secret: str) -> WebhookEvent:
        """Verify the compound signature over the raw payload, then parse it.

        Verification order (matches Stripe's, so P-25b can drop in unchanged):
          1. Parse ``t`` and ``v1`` out of the compound signature string.
          2. Recompute ``HMAC-SHA256(secret, f"{t}.{payload}")`` over the RAW body
             bytes and constant-time compare against ``v1``. A tampered body — or a
             wrong secret — fails here.
          3. Only then check that ``t`` is within tolerance of now; a valid digest
             with a stale timestamp is rejected as a replay (distinct error code).

        Raises:
            PaymentProviderError: on a malformed header, a digest mismatch, a stale
                timestamp, or an unparseable body.
        """
        timestamp, provided_digests = self._parse_signature(signature)

        signed_payload = f'{timestamp}.'.encode('utf-8') + payload
        expected_digest = hmac.new(secret.encode('utf-8'), signed_payload, hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(expected_digest, provided_digest) for provided_digest in provided_digests):
            raise PaymentProviderError('Webhook signature verification failed', code=WEBHOOK_SIGNATURE_VERIFICATION_FAILED)

        age = int(time.time()) - timestamp
        if abs(age) > WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS:
            raise PaymentProviderError(
                f'Webhook timestamp {timestamp} outside {WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS}s tolerance',
                code=WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE,
            )

        try:
            body = json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PaymentProviderError(f'Invalid webhook payload: {exc}', code=WEBHOOK_PAYLOAD_INVALID) from exc

        return WebhookEvent(
            event_id=body.get('id', f'evt_mock_{hashlib.sha256(payload).hexdigest()[:12]}'),
            event_type=body.get('type', 'unknown'),
            data=body.get('data', {}).get('object', {}),
            created=body.get('created', 0),
        )

    @staticmethod
    def _parse_signature(signature: str) -> tuple[int, list[str]]:
        """Parse ``t=<unix>,v1=<hex>`` into (timestamp, digests).

        Tolerates extra comma-separated pairs (as Stripe emits) and whitespace.
        Raises PaymentProviderError if ``t`` or any ``v1`` digest is absent or ``t``
        is not an integer.
        """
        timestamp: int | None = None
        digests: list[str] = []
        for part in signature.split(','):
            key, _, value = part.strip().partition('=')
            if key == 't' and value:
                try:
                    timestamp = int(value)
                except ValueError as exc:
                    raise PaymentProviderError(
                        f'Malformed webhook signature timestamp: {value!r}',
                        code=WEBHOOK_SIGNATURE_MALFORMED,
                    ) from exc
            elif key == 'v1' and value:
                digests.append(value)

        if timestamp is None or not digests:
            raise PaymentProviderError(
                'Malformed webhook signature header (expected t=<unix>,v1=<hex>)',
                code=WEBHOOK_SIGNATURE_MALFORMED,
            )
        return timestamp, digests


# Satisfy runtime_checkable Protocol assertion (mirrors PlaceholderPaymentProvider).
assert isinstance(MockProvider(), PaymentProviderInterface)
