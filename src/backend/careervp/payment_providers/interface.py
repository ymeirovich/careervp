"""
Payment Provider Interface — provider-agnostic billing abstraction.

Implement this protocol to swap the payment processor without touching
any business logic.  All concrete providers (Stripe, Paddle, etc.) must
implement every method defined here.

To add a new provider:
1. Create careervp/payment_providers/<provider_name>_provider.py
2. Implement PaymentProviderInterface
3. Swap the concrete class in the Lambda handler factory
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# ─── Data transfer objects ────────────────────────────────────────────────────


@dataclass
class CustomerRecord:
    """Represents a customer created in the payment provider."""

    customer_id: str
    email: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class CheckoutSession:
    """Represents a checkout session URL to redirect the user to."""

    session_id: str
    checkout_url: str
    customer_id: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class PortalSession:
    """Represents a customer portal session URL."""

    session_id: str
    portal_url: str


@dataclass
class WebhookEvent:
    """Normalised inbound webhook event from the payment provider."""

    event_id: str
    event_type: str
    # Provider-specific raw object (subscription, invoice, etc.)
    data: dict[str, Any] = field(default_factory=dict)
    # Unix timestamp of when the event was created upstream
    created: int = 0


class PaymentProviderError(Exception):
    """Raised by any PaymentProviderInterface implementation on failure."""

    def __init__(self, message: str, code: str = 'PAYMENT_PROVIDER_ERROR') -> None:
        super().__init__(message)
        self.code = code


# ─── Protocol ─────────────────────────────────────────────────────────────────


@runtime_checkable
class PaymentProviderInterface(Protocol):
    """
    Abstract contract for all payment providers.

    Each method corresponds to a billing action; the concrete provider
    translates it into provider-specific API calls.

    Raises:
        PaymentProviderError: on any provider-side failure (network, auth, etc.)
    """

    def create_customer(self, email: str, metadata: dict[str, str]) -> CustomerRecord:
        """Create a new customer record and return their provider-assigned ID."""
        ...

    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        plan: str,
        user_id: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession:
        """
        Create a hosted checkout session for the given price.

        Args:
            customer_id: Provider customer ID (from create_customer)
            price_id:    Provider price/product ID for the selected plan
            plan:        Human-readable plan name stored in metadata ('monthly', 'quarterly')
            user_id:     Application user ID stored in metadata for webhook correlation
            success_url: Redirect URL on successful payment
            cancel_url:  Redirect URL on cancellation

        Returns:
            CheckoutSession with a URL to redirect the user to
        """
        ...

    def create_portal_session(self, customer_id: str, return_url: str) -> PortalSession:
        """
        Create a self-service billing portal session.

        The portal lets subscribers manage payment methods, cancel, or upgrade.
        """
        ...

    def construct_webhook_event(self, payload: bytes, signature: str, secret: str) -> WebhookEvent:
        """
        Validate and parse an inbound webhook payload.

        Args:
            payload:   Raw request body bytes (must not be decoded before this call)
            signature: Provider-supplied signature header value
            secret:    Webhook endpoint secret (from provider dashboard / SSM)

        Returns:
            WebhookEvent with verified event_id, event_type, and data

        Raises:
            PaymentProviderError: if signature verification fails
        """
        ...

    def get_price_map(self) -> dict[str, str]:
        """
        Return a mapping of plan name → provider price ID.

        Example: {'monthly': 'price_xxx', 'quarterly': 'price_yyy'}

        This is called once at cold-start and cached by the billing service.
        """
        ...
