"""
PlaceholderPaymentProvider — stub implementation for local dev & tests.

# ┌─────────────────────────────────────────────────────────────────────────┐
# │  PLACEHOLDER — NOT A REAL PAYMENT PROVIDER                              │
# │                                                                         │
# │  Replace this class with a concrete provider when you integrate a       │
# │  payment processor.  See careervp/payment_providers/interface.py for    │
# │  the full contract.                                                     │
# │                                                                         │
# │  Example concrete implementations to add:                               │
# │    careervp/payment_providers/stripe_provider.py  (Stripe)              │
# │    careervp/payment_providers/paddle_provider.py  (Paddle)              │
# └─────────────────────────────────────────────────────────────────────────┘

All methods raise NotImplementedError in production so mis-wiring is caught
immediately.  In tests, inject a MagicMock or a custom subclass instead.
"""

from __future__ import annotations

import os
import uuid

from careervp.payment_providers.interface import (
    CheckoutSession,
    CustomerRecord,
    PaymentProviderError,
    PaymentProviderInterface,
    PortalSession,
    WebhookEvent,
)

_PLACEHOLDER_MODE = os.environ.get('PAYMENT_PROVIDER_PLACEHOLDER', '').lower() == 'true'


class PlaceholderPaymentProvider:
    """Stub that satisfies PaymentProviderInterface without calling any API.

    In PAYMENT_PROVIDER_PLACEHOLDER=true mode (e.g. local dev / unit tests)
    all methods return lightweight fake objects so handlers can be exercised
    end-to-end without network calls.

    Outside placeholder mode every method raises NotImplementedError to ensure
    a real provider is wired before going live.
    """

    def create_customer(self, email: str, metadata: dict[str, str]) -> CustomerRecord:
        self._guard()
        return CustomerRecord(
            customer_id=f'cus_placeholder_{uuid.uuid4().hex[:8]}',
            email=email,
            metadata=metadata,
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
        self._guard()
        session_id = f'cs_placeholder_{uuid.uuid4().hex[:12]}'
        # TODO: replace with provider checkout URL when implementing real provider
        checkout_url = f'{success_url}?session_id={session_id}&placeholder=true'
        return CheckoutSession(
            session_id=session_id,
            checkout_url=checkout_url,
            customer_id=customer_id,
            metadata={'user_id': user_id, 'plan': plan},
        )

    def create_portal_session(self, customer_id: str, return_url: str) -> PortalSession:
        self._guard()
        session_id = f'bps_placeholder_{uuid.uuid4().hex[:12]}'
        # TODO: replace with real portal URL when implementing real provider
        portal_url = f'{return_url}?portal_session={session_id}&placeholder=true'
        return PortalSession(session_id=session_id, portal_url=portal_url)

    def construct_webhook_event(self, payload: bytes, signature: str, secret: str) -> WebhookEvent:
        """In placeholder mode, parse payload as JSON without signature check.

        IMPORTANT: Do NOT deploy placeholder mode to production — there is no
        signature verification here.  This is only for local development and tests.
        """
        self._guard()
        import json

        try:
            body = json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PaymentProviderError(f'Invalid webhook payload: {exc}') from exc

        return WebhookEvent(
            event_id=body.get('id', f'evt_placeholder_{uuid.uuid4().hex[:12]}'),
            event_type=body.get('type', 'unknown'),
            data=body.get('data', {}).get('object', {}),
            created=body.get('created', 0),
        )

    def get_price_map(self) -> dict[str, str]:
        """Return configurable price map from env vars or static placeholder IDs.

        When deploying a real provider, set:
          PRICE_ID_MONTHLY=price_xxx
          PRICE_ID_QUARTERLY=price_yyy
        """
        self._guard()
        return {
            'monthly': os.environ.get('PRICE_ID_MONTHLY', 'price_placeholder_monthly'),
            'quarterly': os.environ.get('PRICE_ID_QUARTERLY', 'price_placeholder_quarterly'),
        }

    @staticmethod
    def _guard() -> None:
        if not _PLACEHOLDER_MODE:
            raise NotImplementedError(
                'PlaceholderPaymentProvider is not configured for production use. '
                'Set PAYMENT_PROVIDER_PLACEHOLDER=true for local development, '
                'or implement a concrete PaymentProviderInterface subclass.'
            )


# Satisfy runtime_checkable Protocol assertion
assert isinstance(PlaceholderPaymentProvider(), PaymentProviderInterface)
