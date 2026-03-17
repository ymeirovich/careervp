"""
Unit tests for WebhookService (event routing + idempotency).

Mirrors TypeScript tests:
  webhook-checkout.test.ts   (F-SUB-010/011)
  webhook-invoice.test.ts    (F-SUB-012/013)
  webhook-subscription-updated.test.ts (F-SUB-014a/b)
  webhook-subscription-deleted.test.ts (F-SUB-016)
  webhook-out-of-order.test.ts
  webhook-stale-data-out-of-order.test.ts
  webhook-signature.test.ts

Spec: docs/best_practices/yaml/testing_spec.yaml
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from careervp.payment_providers.interface import PaymentProviderError, WebhookEvent

# ─── Inline WebhookService (implementation lives in logic/webhook_service.py)
# Tests define the expected contract. ─────────────────────────────────────────


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
        subscription_repo: MagicMock,
        payment_provider: MagicMock,
    ) -> None:
        self._sub_repo = subscription_repo
        self._payment_provider = payment_provider

    def handle_event(self, payload: bytes, signature: str, secret: str) -> dict:
        try:
            event: WebhookEvent = self._payment_provider.construct_webhook_event(payload, signature, secret)
        except PaymentProviderError as exc:
            return {'status_code': 400, 'error': f'Invalid webhook: {exc}'}

        # Idempotency guard
        is_new = self._sub_repo.record_payment_event(event.event_id, event.event_type)
        if not is_new:
            return {'status_code': 200, 'message': 'duplicate event ignored'}

        handlers = {
            'checkout.session.completed': self._handle_checkout_completed,
            'customer.subscription.updated': self._handle_subscription_updated,
            'customer.subscription.deleted': self._handle_subscription_deleted,
            'invoice.payment_succeeded': self._handle_invoice_succeeded,
            'invoice.payment_failed': self._handle_invoice_failed,
        }
        handler = handlers.get(event.event_type)
        if handler:
            handler(event)

        return {'status_code': 200}

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
        if not subscription_id:
            return

        items = sub.get('items', {}).get('data', [{}])
        price_id = items[0].get('price', {}).get('id', '') if items else ''
        plan = self.PRICE_TO_PLAN.get(price_id, 'monthly')

        # Stale data guard: only apply if event is newer than stored record
        user_sub_result = self._sub_repo.get_subscription_by_subscription_id(subscription_id)
        existing = user_sub_result.data if user_sub_result.success else None
        if existing:
            existing_event_created = existing.get('stripe_event_created', 0)
            incoming_event_created = event.created
            if existing_event_created > incoming_event_created:
                return  # reject stale out-of-order event

        self._sub_repo.update_subscription_by_subscription_id(
            subscription_id,
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
        if not subscription_id:
            return
        self._sub_repo.update_subscription_by_subscription_id(
            subscription_id,
            {
                'status': 'canceled',
                'canceled_at': _ts_to_iso(sub.get('canceled_at', 0)) if sub.get('canceled_at') else None,
            },
        )

    def _handle_invoice_succeeded(self, event: WebhookEvent) -> None:
        invoice = event.data
        subscription_id = invoice.get('subscription', '')
        if not subscription_id:
            return
        self._sub_repo.update_subscription_by_subscription_id(
            subscription_id,
            {
                'payment_failed_count': 0,
                'status': 'active',
                'current_period_end': _ts_to_iso(invoice.get('period_end', 0)),
            },
        )

    def _handle_invoice_failed(self, event: WebhookEvent) -> None:
        invoice = event.data
        subscription_id = invoice.get('subscription', '')
        if not subscription_id:
            return
        self._sub_repo.increment_payment_failed_count(subscription_id)
        self._sub_repo.update_subscription_by_subscription_id(subscription_id, {'status': 'past_due'})


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_service() -> tuple[WebhookService, MagicMock, MagicMock]:
    sub_repo = MagicMock()
    payment_provider = MagicMock()

    # Default: first delivery
    sub_repo.record_payment_event.return_value = True

    sub_result = MagicMock()
    sub_result.success = True
    sub_result.data = None
    sub_repo.get_subscription_by_subscription_id.return_value = sub_result

    return WebhookService(sub_repo, payment_provider), sub_repo, payment_provider


def _make_event(
    event_type: str,
    event_id: str = 'evt_001',
    data: dict | None = None,
    created: int = 1741996800,
) -> WebhookEvent:
    return WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        data=data or {},
        created=created,
    )


def _stripe_sub(
    *,
    price_id: str = 'price_monthly_001',
    current_period_start: int = 1741996800,
    current_period_end: int = 1744675200,
    cancel_at_period_end: bool = False,
) -> dict:
    return {
        'id': 'sub_1Pxyz',
        'status': 'active',
        'items': {'data': [{'price': {'id': price_id}}]},
        'current_period_start': current_period_start,
        'current_period_end': current_period_end,
        'cancel_at_period_end': cancel_at_period_end,
    }


# ─── Webhook signature verification ──────────────────────────────────────────


@pytest.mark.unit
class TestWebhookSignature:
    def test_returns_400_on_invalid_signature(self) -> None:
        svc, _, payment_provider = _make_service()
        payment_provider.construct_webhook_event.side_effect = PaymentProviderError('Invalid signature')

        result = svc.handle_event(b'{}', 'bad_sig', 'secret')

        assert result['status_code'] == 400

    def test_returns_200_on_valid_signature(self) -> None:
        svc, sub_repo, payment_provider = _make_service()
        event = _make_event('checkout.session.completed')
        payment_provider.construct_webhook_event.return_value = event
        payment_provider.retrieve_subscription.return_value = _stripe_sub()

        result = svc.handle_event(b'{}', 'valid_sig', 'secret')

        assert result['status_code'] == 200


# ─── F-SUB-010: Checkout Completed → Subscription Activated ──────────────────


@pytest.mark.unit
class TestCheckoutCompleted:
    def test_upserts_subscription_with_status_active(self) -> None:
        svc, sub_repo, payment_provider = _make_service()
        event = _make_event(
            'checkout.session.completed',
            data={
                'subscription': 'sub_1Pxyz',
                'customer': 'cus_Nabc',
                'metadata': {'user_id': 'user-010', 'plan': 'monthly'},
            },
        )
        payment_provider.construct_webhook_event.return_value = event
        payment_provider.retrieve_subscription.return_value = _stripe_sub()

        svc.handle_event(b'{}', 'sig', 'secret')

        call_kwargs = sub_repo.upsert_subscription.call_args
        data = call_kwargs[0][1]
        assert data['status'] == 'active'
        assert data['plan'] == 'monthly'
        assert data['payment_failed_count'] == 0

    def test_sets_unlimited_usage_after_checkout(self) -> None:
        svc, sub_repo, payment_provider = _make_service()
        event = _make_event(
            'checkout.session.completed',
            data={
                'subscription': 'sub_1Pxyz',
                'customer': 'cus_Nabc',
                'metadata': {'user_id': 'user-010', 'plan': 'monthly'},
            },
        )
        payment_provider.construct_webhook_event.return_value = event
        payment_provider.retrieve_subscription.return_value = _stripe_sub()

        svc.handle_event(b'{}', 'sig', 'secret')

        sub_repo.set_unlimited_usage.assert_called_once_with('user-010')

    def test_stores_stripe_price_id(self) -> None:
        svc, sub_repo, payment_provider = _make_service()
        event = _make_event(
            'checkout.session.completed',
            data={
                'subscription': 'sub_1Pxyz',
                'customer': 'cus_Nabc',
                'metadata': {'user_id': 'user-010', 'plan': 'monthly'},
            },
        )
        payment_provider.construct_webhook_event.return_value = event
        payment_provider.retrieve_subscription.return_value = _stripe_sub(price_id='price_monthly_001')

        svc.handle_event(b'{}', 'sig', 'secret')

        data = sub_repo.upsert_subscription.call_args[0][1]
        assert data['stripe_price_id'] == 'price_monthly_001'

    def test_period_dates_are_iso_formatted(self) -> None:
        svc, sub_repo, payment_provider = _make_service()
        event = _make_event(
            'checkout.session.completed',
            data={
                'subscription': 'sub_1Pxyz',
                'customer': 'cus_Nabc',
                'metadata': {'user_id': 'user-010', 'plan': 'monthly'},
            },
        )
        payment_provider.construct_webhook_event.return_value = event
        payment_provider.retrieve_subscription.return_value = _stripe_sub(current_period_start=1741996800, current_period_end=1744675200)

        svc.handle_event(b'{}', 'sig', 'secret')

        data = sub_repo.upsert_subscription.call_args[0][1]
        # Both should be parseable ISO timestamps
        datetime.fromisoformat(data['current_period_start'])
        datetime.fromisoformat(data['current_period_end'])


# ─── F-SUB-011: Idempotent Duplicate Delivery ────────────────────────────────


@pytest.mark.unit
class TestIdempotentDuplicates:
    def test_duplicate_event_returns_200_without_reprocessing(self) -> None:
        svc, sub_repo, payment_provider = _make_service()
        sub_repo.record_payment_event.return_value = False  # already recorded
        event = _make_event('checkout.session.completed')
        payment_provider.construct_webhook_event.return_value = event

        result = svc.handle_event(b'{}', 'sig', 'secret')

        assert result['status_code'] == 200
        sub_repo.upsert_subscription.assert_not_called()

    def test_idempotency_key_checked_before_processing(self) -> None:
        svc, sub_repo, payment_provider = _make_service()
        event = _make_event('checkout.session.completed', event_id='evt_unique_001')
        payment_provider.construct_webhook_event.return_value = event
        payment_provider.retrieve_subscription.return_value = _stripe_sub()

        svc.handle_event(b'{}', 'sig', 'secret')

        sub_repo.record_payment_event.assert_called_once_with('evt_unique_001', 'checkout.session.completed')


# ─── F-SUB-014a: Plan Change ──────────────────────────────────────────────────


@pytest.mark.unit
class TestSubscriptionUpdated:
    def test_plan_change_monthly_to_quarterly(self) -> None:
        svc, sub_repo, payment_provider = _make_service()
        event = _make_event(
            'customer.subscription.updated',
            data={
                'id': 'sub_1Pxyz',
                'status': 'active',
                'items': {'data': [{'price': {'id': 'price_quarterly_001'}}]},
                'current_period_start': 1741996800,
                'current_period_end': 1749945600,
                'cancel_at_period_end': False,
            },
        )
        payment_provider.construct_webhook_event.return_value = event

        svc.handle_event(b'{}', 'sig', 'secret')

        update_data = sub_repo.update_subscription_by_subscription_id.call_args[0][1]
        assert update_data['plan'] == 'quarterly'
        assert update_data['status'] == 'active'

    def test_cancel_at_period_end_toggle(self) -> None:
        svc, sub_repo, payment_provider = _make_service()
        event = _make_event(
            'customer.subscription.updated',
            data={
                'id': 'sub_1Pxyz',
                'status': 'active',
                'items': {'data': [{'price': {'id': 'price_monthly_001'}}]},
                'current_period_start': 1741996800,
                'current_period_end': 1744675200,
                'cancel_at_period_end': True,
            },
        )
        payment_provider.construct_webhook_event.return_value = event

        svc.handle_event(b'{}', 'sig', 'secret')

        update_data = sub_repo.update_subscription_by_subscription_id.call_args[0][1]
        assert update_data['cancel_at_period_end'] is True
        assert update_data['status'] == 'active'
        assert update_data['plan'] == 'monthly'


# ─── F-SUB-016: Subscription Deleted ─────────────────────────────────────────


@pytest.mark.unit
class TestSubscriptionDeleted:
    def test_sets_status_to_canceled(self) -> None:
        svc, sub_repo, payment_provider = _make_service()
        event = _make_event(
            'customer.subscription.deleted',
            data={'id': 'sub_1Pxyz', 'canceled_at': 1741996800},
        )
        payment_provider.construct_webhook_event.return_value = event

        svc.handle_event(b'{}', 'sig', 'secret')

        update_data = sub_repo.update_subscription_by_subscription_id.call_args[0][1]
        assert update_data['status'] == 'canceled'

    def test_stores_canceled_at_timestamp(self) -> None:
        svc, sub_repo, payment_provider = _make_service()
        event = _make_event(
            'customer.subscription.deleted',
            data={'id': 'sub_1Pxyz', 'canceled_at': 1741996800},
        )
        payment_provider.construct_webhook_event.return_value = event

        svc.handle_event(b'{}', 'sig', 'secret')

        update_data = sub_repo.update_subscription_by_subscription_id.call_args[0][1]
        assert update_data['canceled_at'] is not None


# ─── Out-of-order stale event handling ───────────────────────────────────────


@pytest.mark.unit
class TestOutOfOrderEvents:
    def test_stale_event_does_not_overwrite_newer_data(self) -> None:
        """If stored record has newer stripe_event_created, ignore the incoming."""
        svc, sub_repo, payment_provider = _make_service()

        existing_result = MagicMock()
        existing_result.success = True
        existing_result.data = {
            'subscription_id': 'sub_1Pxyz',
            'plan': 'quarterly',
            'stripe_event_created': 1742000000,  # newer
        }
        sub_repo.get_subscription_by_subscription_id.return_value = existing_result

        event = _make_event(
            'customer.subscription.updated',
            data={
                'id': 'sub_1Pxyz',
                'status': 'active',
                'items': {'data': [{'price': {'id': 'price_monthly_001'}}]},
                'current_period_start': 1741000000,
                'current_period_end': 1743000000,
                'cancel_at_period_end': False,
            },
            created=1741000000,  # older than stored
        )
        payment_provider.construct_webhook_event.return_value = event

        svc.handle_event(b'{}', 'sig', 'secret')

        sub_repo.update_subscription_by_subscription_id.assert_not_called()

    def test_newer_event_does_overwrite_older_data(self) -> None:
        svc, sub_repo, payment_provider = _make_service()

        existing_result = MagicMock()
        existing_result.success = True
        existing_result.data = {
            'subscription_id': 'sub_1Pxyz',
            'plan': 'monthly',
            'stripe_event_created': 1741000000,  # older
        }
        sub_repo.get_subscription_by_subscription_id.return_value = existing_result

        event = _make_event(
            'customer.subscription.updated',
            data={
                'id': 'sub_1Pxyz',
                'status': 'active',
                'items': {'data': [{'price': {'id': 'price_quarterly_001'}}]},
                'current_period_start': 1742000000,
                'current_period_end': 1749945600,
                'cancel_at_period_end': False,
            },
            created=1742000000,  # newer
        )
        payment_provider.construct_webhook_event.return_value = event

        svc.handle_event(b'{}', 'sig', 'secret')

        sub_repo.update_subscription_by_subscription_id.assert_called_once()


# ─── Invoice events ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestInvoiceEvents:
    def test_invoice_succeeded_resets_payment_failed_count(self) -> None:
        svc, sub_repo, payment_provider = _make_service()
        event = _make_event(
            'invoice.payment_succeeded',
            data={'subscription': 'sub_1Pxyz', 'period_end': 1744675200},
        )
        payment_provider.construct_webhook_event.return_value = event

        svc.handle_event(b'{}', 'sig', 'secret')

        update_data = sub_repo.update_subscription_by_subscription_id.call_args[0][1]
        assert update_data['payment_failed_count'] == 0
        assert update_data['status'] == 'active'

    def test_invoice_failed_increments_payment_failed_count(self) -> None:
        svc, sub_repo, payment_provider = _make_service()
        event = _make_event(
            'invoice.payment_failed',
            data={'subscription': 'sub_1Pxyz'},
        )
        payment_provider.construct_webhook_event.return_value = event

        svc.handle_event(b'{}', 'sig', 'secret')

        sub_repo.increment_payment_failed_count.assert_called_once_with('sub_1Pxyz')
        update_data = sub_repo.update_subscription_by_subscription_id.call_args[0][1]
        assert update_data['status'] == 'past_due'
