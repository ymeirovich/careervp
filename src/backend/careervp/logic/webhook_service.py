"""
WebhookService — routes validated webhook events to subscription operations.

Event routing (S-004.1):
  checkout.session.completed    → upsert_subscription + set_unlimited_usage
  customer.subscription.updated → update_subscription_fields (stale-event guard)
  customer.subscription.deleted → update_subscription_fields (status=canceled)
  invoice.payment_succeeded     → update_subscription_fields (reset fail count)
  invoice.payment_failed        → update_subscription_fields (increment fail count)

Security:
  Dual-secret verification (_verify_webhook) supports zero-downtime secret rotation.
  Tries primary_secret first; on PaymentProviderError, tries previous_secret if set.

Idempotency (commit-after-work):
  1. record_payment_event FIRST (claim slot).
  2. Execute all DynamoDB writes.
  3a. Success → leave record in place (blocks duplicate delivery).
  3b. Any exception → delete_payment_event (releases slot for provider retry) then re-raise.
  This is safe because upsert_subscription uses put_item (idempotent).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from careervp.payment_providers.interface import (
    PaymentProviderError,
    PaymentProviderInterface,
    WebhookEvent,
)


def _ts_to_iso(unix_ts: int) -> str:
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat()


class WebhookService:
    """Routes validated webhook events to the correct subscription operations."""

    PRICE_TO_PLAN: dict[str, str] = {
        'price_monthly_001': 'monthly',
        'price_quarterly_001': 'quarterly',
    }

    def __init__(
        self,
        subscription_repo: Any,
        payment_provider: PaymentProviderInterface,
        primary_secret: str,
        previous_secret: str = 'none',
    ) -> None:
        self._sub_repo = subscription_repo
        self._payment_provider = payment_provider
        self._primary_secret = primary_secret
        self._previous_secret = previous_secret

    def _verify_webhook(self, payload_bytes: bytes, sig_header: str) -> WebhookEvent:
        """Verify webhook signature with dual-secret rotation support.

        Tries primary_secret first. On PaymentProviderError, tries previous_secret
        if it is set and not the sentinel value 'none'. Raises PaymentProviderError
        if all attempts fail.
        """
        try:
            return self._payment_provider.construct_webhook_event(payload_bytes, sig_header, self._primary_secret)
        except PaymentProviderError:
            if self._previous_secret and self._previous_secret != 'none':
                return self._payment_provider.construct_webhook_event(payload_bytes, sig_header, self._previous_secret)
            raise

    def handle_webhook(self, payload_bytes: bytes, sig_header: str) -> dict[str, Any]:
        """Verify, deduplicate, and route an inbound webhook event.

        Returns a dict containing at minimum a 'status_code' key.
        Raises PaymentProviderError when signature verification fails (both secrets).
        Unknown event types return 200 {'status': 'ignored', 'event_type': ...}.
        """
        event = self._verify_webhook(payload_bytes, sig_header)
        provider_name = self._provider_name()

        is_new = self._sub_repo.record_payment_event(
            event.event_id,
            event.event_type,
            provider_name=provider_name,
        )
        if not is_new:
            return self._sub_repo.get_payment_event_result(
                event.event_id,
                event.event_type,
                provider_name,
            ) or {'status_code': 200}

        handlers = {
            'checkout.session.completed': self._handle_checkout_completed,
            'customer.subscription.updated': self._handle_subscription_updated,
            'customer.subscription.deleted': self._handle_subscription_deleted,
            'invoice.payment_succeeded': self._handle_invoice_succeeded,
            'invoice.payment_failed': self._handle_invoice_failed,
        }
        handler = handlers.get(event.event_type)
        if handler is None:
            result = {'status_code': 200, 'status': 'ignored', 'event_type': event.event_type}
            self._sub_repo.complete_payment_event(
                event.event_id,
                event.event_type,
                result,
                provider_name,
            )
            return result

        try:
            handler(event)
        except Exception:
            # Commit-after-work: release idempotency slot so provider can retry
            self._sub_repo.delete_payment_event(
                event.event_id,
                event.event_type,
                provider_name=provider_name,
            )
            raise

        result = {'status_code': 200}
        self._sub_repo.complete_payment_event(
            event.event_id,
            event.event_type,
            result,
            provider_name,
        )
        return result

    def _provider_name(self) -> str:
        """Return the stable provider namespace used in payment-event keys."""
        class_name = type(self._payment_provider).__name__
        return class_name.removesuffix('Provider').lower()

    # ── Event handlers ────────────────────────────────────────────────────────

    def _handle_checkout_completed(self, event: WebhookEvent) -> None:
        data = event.data
        subscription_id = data.get('subscription', '')
        customer_id = data.get('customer', '')
        metadata = data.get('metadata') or {}
        user_id = metadata.get('user_id', '')
        plan = metadata.get('plan', 'monthly')

        if not subscription_id or not user_id:
            return

        stripe_sub = self._payment_provider.retrieve_subscription(subscription_id)
        items = stripe_sub.get('items', {}).get('data', [{}])
        price_id = items[0].get('price', {}).get('id', '') if items else ''

        self._sub_repo.upsert_subscription(
            user_id,
            {
                'subscription_id': subscription_id,
                'customer_id': customer_id,
                'status': 'active',
                'plan': plan,
                'stripe_price_id': price_id,
                'current_period_start': _ts_to_iso(stripe_sub.get('current_period_start', 0)),
                'current_period_end': _ts_to_iso(stripe_sub.get('current_period_end', 0)),
                'trial_end': None,
                'cancel_at_period_end': stripe_sub.get('cancel_at_period_end', False),
                'canceled_at': None,
                'payment_failed_count': 0,
            },
        )
        self._sub_repo.set_unlimited_usage(user_id)

    def _handle_subscription_updated(self, event: WebhookEvent) -> None:
        sub = event.data
        subscription_id = sub.get('id', '')
        customer_id = sub.get('customer', '')
        if not subscription_id or not customer_id:
            return

        result = self._sub_repo.get_subscription_by_customer_id(customer_id)
        existing = result.data if result.success else None
        if not existing:
            return

        user_id = existing.get('user_id', '')
        if not user_id:
            return

        # Stale event guard: only apply if incoming event is newer than stored record
        existing_event_created = existing.get('stripe_event_created', 0)
        if existing_event_created > event.created:
            return

        items = sub.get('items', {}).get('data', [{}])
        price_id = items[0].get('price', {}).get('id', '') if items else ''
        plan = self.PRICE_TO_PLAN.get(price_id, 'monthly')

        self._sub_repo.update_subscription_fields(
            user_id,
            {
                'status': sub.get('status', 'active'),
                'plan': plan,
                'stripe_price_id': price_id,
                'current_period_start': _ts_to_iso(sub.get('current_period_start', 0)),
                'current_period_end': _ts_to_iso(sub.get('current_period_end', 0)),
                'cancel_at_period_end': sub.get('cancel_at_period_end', False),
                'stripe_event_created': event.created,
            },
        )

    def _handle_subscription_deleted(self, event: WebhookEvent) -> None:
        sub = event.data
        subscription_id = sub.get('id', '')
        customer_id = sub.get('customer', '')
        if not subscription_id or not customer_id:
            return

        result = self._sub_repo.get_subscription_by_customer_id(customer_id)
        existing = result.data if result.success else None
        if not existing:
            return

        user_id = existing.get('user_id', '')
        if not user_id:
            return

        self._sub_repo.update_subscription_fields(
            user_id,
            {
                'status': 'canceled',
                'canceled_at': _ts_to_iso(sub.get('canceled_at', 0)) if sub.get('canceled_at') else None,
            },
        )

    def _handle_invoice_succeeded(self, event: WebhookEvent) -> None:
        invoice = event.data
        subscription_id = invoice.get('subscription', '')
        customer_id = invoice.get('customer', '')
        if not subscription_id or not customer_id:
            return

        result = self._sub_repo.get_subscription_by_customer_id(customer_id)
        existing = result.data if result.success else None
        if not existing:
            return

        user_id = existing.get('user_id', '')
        if not user_id:
            return

        self._sub_repo.update_subscription_fields(
            user_id,
            {
                'payment_failed_count': 0,
                'status': 'active',
                'current_period_end': _ts_to_iso(invoice.get('period_end', 0)),
            },
        )

    def _handle_invoice_failed(self, event: WebhookEvent) -> None:
        invoice = event.data
        subscription_id = invoice.get('subscription', '')
        customer_id = invoice.get('customer', '')
        if not subscription_id or not customer_id:
            return

        result = self._sub_repo.get_subscription_by_customer_id(customer_id)
        existing = result.data if result.success else None
        if not existing:
            return

        user_id = existing.get('user_id', '')
        if not user_id:
            return

        current_failed = int(existing.get('payment_failed_count', 0))
        self._sub_repo.update_subscription_fields(
            user_id,
            {
                'payment_failed_count': current_failed + 1,
                'status': 'past_due',
            },
        )


__all__ = ['WebhookService']
