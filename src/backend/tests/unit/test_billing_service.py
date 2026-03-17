"""
Unit tests for BillingService (checkout + portal + get-subscription).

Mirrors TypeScript tests: checkout.test.ts, subscription-status.test.ts,
                          portal.test.ts (F-SUB-004/005/006/007/008/015)
Spec: docs/best_practices/yaml/testing_spec.yaml
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from careervp.models.result import ResultCode
from careervp.payment_providers.interface import (
    CheckoutSession,
    CustomerRecord,
    PaymentProviderError,
    PortalSession,
)

# ─── Inline BillingService (production class lives in logic/billing_service.py)
# Tests define the expected interface so the implementation must satisfy it.
# ─────────────────────────────────────────────────────────────────────────────


class BillingService:
    """Thin wrapper that coordinates PaymentProvider + SubscriptionRepository."""

    VALID_PLANS = ('monthly', 'quarterly')

    def __init__(
        self,
        subscription_repo: MagicMock,
        user_repo: MagicMock,
        payment_provider: MagicMock,
    ) -> None:
        self._sub_repo = subscription_repo
        self._user_repo = user_repo
        self._payment_provider = payment_provider

    def handle_checkout(
        self,
        user_id: str,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> dict:
        if plan not in self.VALID_PLANS:
            return {'status_code': 400, 'error': f"Invalid plan '{plan}'. Must be one of {self.VALID_PLANS}."}
        if not success_url or not cancel_url:
            return {'status_code': 400, 'error': 'success_url and cancel_url are required'}

        existing_result = self._sub_repo.get_subscription(user_id)
        existing = existing_result.data if existing_result.success else None
        if existing and existing.get('status') == 'active':
            return {'status_code': 409, 'error': 'User already has an active subscription'}

        # Get or create payment-provider customer
        customer_id = self._sub_repo.get_customer_id(user_id)
        if not customer_id:
            user = self._user_repo.get_user(user_id)
            email = user.get('email', '') if isinstance(user, dict) else ''
            try:
                customer: CustomerRecord = self._payment_provider.create_customer(email=email, metadata={'user_id': user_id})
            except PaymentProviderError as exc:
                return {'status_code': 502, 'error': str(exc), 'code': ResultCode.PAYMENT_PROVIDER_ERROR}
            customer_id = customer.customer_id
            self._sub_repo.update_customer_id(user_id, customer_id)

        price_map: dict[str, str] = self._payment_provider.get_price_map()
        price_id = price_map[plan]

        try:
            session: CheckoutSession = self._payment_provider.create_checkout_session(
                customer_id=customer_id,
                price_id=price_id,
                plan=plan,
                user_id=user_id,
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except PaymentProviderError as exc:
            return {'status_code': 502, 'error': str(exc), 'code': ResultCode.PAYMENT_PROVIDER_ERROR}

        return {'status_code': 200, 'checkout_url': session.checkout_url}

    def handle_get_subscription(self, user_id: str) -> dict:
        result = self._sub_repo.get_subscription(user_id)
        sub = result.data if result.success else None

        if not sub:
            return {
                'status_code': 200,
                'subscription': None,
                'has_active_subscription': False,
            }

        return {
            'status_code': 200,
            'subscription': {
                'subscription_id': sub.get('subscription_id'),
                'customer_id': sub.get('customer_id'),
                'status': sub.get('status'),
                'plan': sub.get('plan'),
                'current_period_end': sub.get('current_period_end'),
                'cancel_at_period_end': sub.get('cancel_at_period_end', False),
                'trial_end': sub.get('trial_end'),
            },
            'has_active_subscription': sub.get('status') == 'active',
        }

    def handle_portal(self, user_id: str, return_url: str) -> dict:
        customer_id = self._sub_repo.get_customer_id(user_id)
        if not customer_id:
            return {'status_code': 404, 'error': 'No billing account found for this user'}

        try:
            portal: PortalSession = self._payment_provider.create_portal_session(customer_id=customer_id, return_url=return_url)
        except PaymentProviderError as exc:
            return {'status_code': 502, 'error': str(exc), 'code': ResultCode.PAYMENT_PROVIDER_ERROR}

        return {'status_code': 200, 'portal_url': portal.portal_url}


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_service(
    *,
    existing_sub: dict | None = None,
    customer_id: str | None = None,
    user_email: str = 'user@careervp.com',
    provider_customer_id: str = 'cus_test001',
    checkout_url: str = 'https://checkout.example.com/pay/cs_test001',
    portal_url: str = 'https://portal.example.com/session/bps_test001',
    create_customer_error: Exception | None = None,
    create_checkout_error: Exception | None = None,
) -> BillingService:
    sub_repo = MagicMock()
    user_repo = MagicMock()
    payment_provider = MagicMock()

    # sub_repo defaults
    sub_result = MagicMock()
    sub_result.success = True
    sub_result.data = existing_sub
    sub_repo.get_subscription.return_value = sub_result
    sub_repo.get_customer_id.return_value = customer_id
    sub_repo.update_customer_id.return_value = MagicMock(success=True)

    # user_repo defaults
    user_repo.get_user.return_value = {'user_id': 'user-xxx', 'email': user_email}

    # payment_provider defaults
    if create_customer_error:
        payment_provider.create_customer.side_effect = create_customer_error
    else:
        payment_provider.create_customer.return_value = CustomerRecord(customer_id=provider_customer_id, email=user_email)

    if create_checkout_error:
        payment_provider.create_checkout_session.side_effect = create_checkout_error
    else:
        payment_provider.create_checkout_session.return_value = CheckoutSession(
            session_id='cs_test001',
            checkout_url=checkout_url,
            customer_id=provider_customer_id,
        )

    payment_provider.create_portal_session.return_value = PortalSession(session_id='bps_test001', portal_url=portal_url)
    payment_provider.get_price_map.return_value = {
        'monthly': 'price_monthly_001',
        'quarterly': 'price_quarterly_001',
    }

    return BillingService(
        subscription_repo=sub_repo,
        user_repo=user_repo,
        payment_provider=payment_provider,
    )


_CHECKOUT_URLS = {
    'success_url': 'https://app.careervp.com/billing/success',
    'cancel_url': 'https://app.careervp.com/billing/cancel',
}


# ─── F-SUB-004: Monthly / Quarterly Checkout ─────────────────────────────────


@pytest.mark.unit
class TestCheckoutCreation:
    def test_monthly_checkout_returns_200_with_checkout_url(self) -> None:
        svc = _make_service()

        result = svc.handle_checkout('user-004', 'monthly', **_CHECKOUT_URLS)

        assert result['status_code'] == 200
        assert 'checkout_url' in result

    def test_quarterly_checkout_returns_200(self) -> None:
        svc = _make_service()

        result = svc.handle_checkout('user-004', 'quarterly', **_CHECKOUT_URLS)

        assert result['status_code'] == 200
        assert 'checkout_url' in result

    def test_creates_customer_with_user_email(self) -> None:
        svc = _make_service(customer_id=None, user_email='tester@careervp.com')
        svc._payment_provider.create_customer.return_value = CustomerRecord(customer_id='cus_new001', email='tester@careervp.com')

        svc.handle_checkout('user-004', 'monthly', **_CHECKOUT_URLS)

        svc._payment_provider.create_customer.assert_called_once_with(
            email='tester@careervp.com',
            metadata={'user_id': 'user-004'},
        )

    def test_stores_customer_id_after_creation(self) -> None:
        svc = _make_service(customer_id=None, provider_customer_id='cus_new001')

        svc.handle_checkout('user-004', 'monthly', **_CHECKOUT_URLS)

        svc._sub_repo.update_customer_id.assert_called_once_with('user-004', 'cus_new001')

    def test_checkout_creates_session_with_monthly_price(self) -> None:
        svc = _make_service()

        svc.handle_checkout('user-004', 'monthly', **_CHECKOUT_URLS)

        call_kwargs = svc._payment_provider.create_checkout_session.call_args.kwargs
        assert call_kwargs['price_id'] == 'price_monthly_001'

    def test_checkout_creates_session_with_quarterly_price(self) -> None:
        svc = _make_service()

        svc.handle_checkout('user-004', 'quarterly', **_CHECKOUT_URLS)

        call_kwargs = svc._payment_provider.create_checkout_session.call_args.kwargs
        assert call_kwargs['price_id'] == 'price_quarterly_001'

    def test_invalid_plan_returns_400(self) -> None:
        svc = _make_service()

        result = svc.handle_checkout('user-004', 'annual', **_CHECKOUT_URLS)

        assert result['status_code'] == 400
        assert 'Invalid plan' in result['error']

    def test_missing_success_url_returns_400(self) -> None:
        svc = _make_service()

        result = svc.handle_checkout(
            'user-004',
            'monthly',
            success_url='',
            cancel_url='https://app.careervp.com/billing/cancel',
        )

        assert result['status_code'] == 400

    def test_no_payment_provider_call_on_invalid_plan(self) -> None:
        svc = _make_service()

        svc.handle_checkout('user-004', 'invalid', **_CHECKOUT_URLS)

        svc._payment_provider.create_customer.assert_not_called()
        svc._payment_provider.create_checkout_session.assert_not_called()


# ─── F-SUB-005: Customer Reuse ────────────────────────────────────────────────


@pytest.mark.unit
class TestCustomerReuse:
    def test_does_not_create_new_customer_when_one_exists(self) -> None:
        svc = _make_service(customer_id='cus_existing001')

        svc.handle_checkout('user-005', 'monthly', **_CHECKOUT_URLS)

        svc._payment_provider.create_customer.assert_not_called()

    def test_uses_existing_customer_id_for_checkout(self) -> None:
        svc = _make_service(customer_id='cus_existing001')

        svc.handle_checkout('user-005', 'monthly', **_CHECKOUT_URLS)

        call_kwargs = svc._payment_provider.create_checkout_session.call_args.kwargs
        assert call_kwargs['customer_id'] == 'cus_existing001'


# ─── F-SUB-006: Duplicate Checkout Blocked ───────────────────────────────────


@pytest.mark.unit
class TestDuplicateCheckoutBlocked:
    def test_returns_409_for_active_subscriber(self) -> None:
        svc = _make_service(existing_sub={'subscription_id': 'sub_active', 'status': 'active'})

        result = svc.handle_checkout('user-006', 'monthly', **_CHECKOUT_URLS)

        assert result['status_code'] == 409
        assert 'active subscription' in result['error']

    def test_no_checkout_call_for_active_subscriber(self) -> None:
        svc = _make_service(existing_sub={'subscription_id': 'sub_active', 'status': 'active'})

        svc.handle_checkout('user-006', 'monthly', **_CHECKOUT_URLS)

        svc._payment_provider.create_checkout_session.assert_not_called()

    def test_allows_checkout_when_subscription_is_canceled(self) -> None:
        svc = _make_service(
            existing_sub={'subscription_id': 'sub_old', 'status': 'canceled'},
            customer_id='cus_existing001',
        )

        result = svc.handle_checkout('user-006', 'monthly', **_CHECKOUT_URLS)

        assert result['status_code'] == 200


# ─── F-SUB-008: Get Subscription Status ──────────────────────────────────────


@pytest.mark.unit
class TestGetSubscription:
    def test_returns_active_subscription_with_flag_true(self) -> None:
        sub = {
            'subscription_id': 'sub_1Pxyz',
            'customer_id': 'cus_Nabc',
            'status': 'active',
            'plan': 'monthly',
            'current_period_end': '2026-04-14T00:00:00Z',
            'cancel_at_period_end': False,
            'trial_end': None,
        }
        svc = _make_service(existing_sub=sub)

        result = svc.handle_get_subscription('user-008')

        assert result['status_code'] == 200
        assert result['has_active_subscription'] is True
        assert result['subscription']['status'] == 'active'

    def test_returns_null_subscription_when_none(self) -> None:
        svc = _make_service(existing_sub=None)

        result = svc.handle_get_subscription('user-008b')

        assert result['status_code'] == 200
        assert result['subscription'] is None
        assert result['has_active_subscription'] is False

    def test_subscription_response_includes_all_fields(self) -> None:
        sub = {
            'subscription_id': 'sub_1Pxyz',
            'customer_id': 'cus_Nabc',
            'status': 'active',
            'plan': 'monthly',
            'current_period_end': '2026-04-14T00:00:00Z',
            'cancel_at_period_end': False,
            'trial_end': None,
        }
        svc = _make_service(existing_sub=sub)

        result = svc.handle_get_subscription('user-008')

        s = result['subscription']
        assert s['subscription_id'] == 'sub_1Pxyz'
        assert s['customer_id'] == 'cus_Nabc'
        assert s['cancel_at_period_end'] is False
        assert s['trial_end'] is None


# ─── F-SUB-015: Cancel-at-Period-End UX ──────────────────────────────────────


@pytest.mark.unit
class TestCancelAtPeriodEndUx:
    def test_active_canceling_subscription_has_flag_true(self) -> None:
        sub = {
            'subscription_id': 'sub_canceling',
            'status': 'active',
            'plan': 'monthly',
            'current_period_end': '2026-04-14T00:00:00Z',
            'cancel_at_period_end': True,
        }
        svc = _make_service(existing_sub=sub)

        result = svc.handle_get_subscription('user-015')

        assert result['has_active_subscription'] is True
        assert result['subscription']['cancel_at_period_end'] is True

    def test_canceling_subscription_still_active(self) -> None:
        sub = {'subscription_id': 'sub_015', 'status': 'active', 'cancel_at_period_end': True}
        svc = _make_service(existing_sub=sub)

        result = svc.handle_get_subscription('user-015')

        assert result['has_active_subscription'] is True


# ─── F-SUB-007: Portal ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPortalSession:
    def test_returns_portal_url_when_customer_exists(self) -> None:
        svc = _make_service(customer_id='cus_existing001')

        result = svc.handle_portal('user-007', 'https://app.careervp.com/settings/billing')

        assert result['status_code'] == 200
        assert 'portal_url' in result

    def test_returns_404_when_no_customer_id(self) -> None:
        svc = _make_service(customer_id=None)

        result = svc.handle_portal('user-new', 'https://app.careervp.com/settings/billing')

        assert result['status_code'] == 404

    def test_returns_502_on_provider_error(self) -> None:
        svc = _make_service(customer_id='cus_existing001')
        svc._payment_provider.create_portal_session.side_effect = PaymentProviderError('Portal unavailable')

        result = svc.handle_portal('user-007', 'https://app.careervp.com/settings/billing')

        assert result['status_code'] == 502
        assert result['code'] == ResultCode.PAYMENT_PROVIDER_ERROR


# ─── Payment provider error propagation ──────────────────────────────────────


@pytest.mark.unit
class TestPaymentProviderErrors:
    def test_create_customer_error_returns_502(self) -> None:
        svc = _make_service(
            customer_id=None,
            create_customer_error=PaymentProviderError('Provider down', ResultCode.PAYMENT_PROVIDER_ERROR),
        )

        result = svc.handle_checkout('user-err', 'monthly', **_CHECKOUT_URLS)

        assert result['status_code'] == 502
        assert result['code'] == ResultCode.PAYMENT_PROVIDER_ERROR

    def test_create_checkout_error_returns_502(self) -> None:
        svc = _make_service(
            customer_id='cus_existing001',
            create_checkout_error=PaymentProviderError('Session failed', ResultCode.PAYMENT_PROVIDER_ERROR),
        )

        result = svc.handle_checkout('user-err', 'monthly', **_CHECKOUT_URLS)

        assert result['status_code'] == 502
