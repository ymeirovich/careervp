"""
BillingService — business logic for checkout, subscription status, and portal.

Coordinates SubscriptionRepository, UserRepository, and PaymentProviderInterface.
Uses an atomic checkout-lock (create_checkout_intent / release_checkout_intent) to
prevent duplicate customer creation under concurrent Lambda invocations.
"""

from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from careervp.models.result import ResultCode
from careervp.payment_providers.interface import (
    CheckoutSession,
    CustomerRecord,
    PaymentProviderError,
    PortalSession,
)


class BillingService:
    """Coordinates PaymentProvider + SubscriptionRepository for billing operations."""

    VALID_PLANS = ('monthly', 'quarterly')

    def __init__(
        self,
        subscription_repo: Any,
        user_repo: Any,
        payment_provider: Any,
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
    ) -> dict[str, Any]:
        """Process a checkout request.

        Acquires a checkout lock ONLY when no customer_id exists yet, to prevent
        duplicate customer creation under concurrent requests.  The lock is released
        in a finally block on both success and failure paths.

        Returns a dict with a 'status_code' key and the response payload.
        """
        if plan not in self.VALID_PLANS:
            return {
                'status_code': 400,
                'error': f"Invalid plan '{plan}'. Must be one of {self.VALID_PLANS}.",
            }
        if not success_url or not cancel_url:
            return {'status_code': 400, 'error': 'success_url and cancel_url are required'}

        # MUST check for active subscription BEFORE acquiring the checkout lock
        existing_result = self._sub_repo.get_subscription(user_id)
        existing = existing_result.data if existing_result.success else None
        if existing and existing.get('status') == 'active':
            return {'status_code': 409, 'error': 'User already has an active subscription'}

        customer_id, error = self._get_or_create_customer_id(user_id)
        if error is not None:
            return error

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
            return {
                'status_code': 502,
                'error': str(exc),
                'code': ResultCode.PAYMENT_PROVIDER_ERROR,
            }

        return {'status_code': 200, 'checkout_url': session.checkout_url}

    def _get_or_create_customer_id(
        self,
        user_id: str,
    ) -> tuple[str, None] | tuple[None, dict[str, Any]]:
        """Return (customer_id, None) or (None, error_dict).

        If a customer_id already exists, returns it immediately.
        Otherwise acquires a checkout lock, creates the customer, stores the id,
        and always releases the lock in a finally block.
        """
        customer_id: str | None = self._sub_repo.get_customer_id(user_id)
        if customer_id:
            return customer_id, None

        # Acquire atomic lock — raises ClientError(ConditionalCheckFailedException)
        # if another checkout is already in progress for this user
        try:
            self._sub_repo.create_checkout_intent(user_id)
        except ClientError as exc:
            error_code = exc.response.get('Error', {}).get('Code', '')
            if error_code == 'ConditionalCheckFailedException':
                return None, {
                    'status_code': 409,
                    'error': 'checkout_in_progress',
                    'code': ResultCode.CHECKOUT_IN_PROGRESS,
                }
            raise

        try:
            user = self._user_repo.get_user(user_id)
            if isinstance(user, dict):
                email: str = user.get('email', '') or ''
            elif user is not None:
                email = getattr(user, 'email', '') or ''
            else:
                email = ''

            try:
                customer: CustomerRecord = self._payment_provider.create_customer(
                    email=email,
                    metadata={'user_id': user_id},
                )
            except PaymentProviderError as exc:
                return None, {
                    'status_code': 502,
                    'error': str(exc),
                    'code': ResultCode.PAYMENT_PROVIDER_ERROR,
                }

            new_id: str = customer.customer_id
            self._sub_repo.update_customer_id(user_id, new_id)
            return new_id, None
        finally:
            # Always release the lock — TTL is last-resort cleanup only
            self._sub_repo.release_checkout_intent(user_id)

    def handle_get_subscription(self, user_id: str) -> dict[str, Any]:
        """Return the current subscription state for a user.

        Returns {'subscription': None, 'has_active_subscription': False} when no
        subscription record exists.
        """
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

    def handle_portal(self, user_id: str, return_url: str) -> dict[str, Any]:
        """Create a billing portal session for an existing customer.

        Returns 404 when no customer_id is found (user has never subscribed).
        """
        customer_id = self._sub_repo.get_customer_id(user_id)
        if not customer_id:
            return {'status_code': 404, 'error': 'No billing account found for this user'}

        try:
            portal: PortalSession = self._payment_provider.create_portal_session(
                customer_id=customer_id,
                return_url=return_url,
            )
        except PaymentProviderError as exc:
            return {
                'status_code': 502,
                'error': str(exc),
                'code': ResultCode.PAYMENT_PROVIDER_ERROR,
            }

        return {'status_code': 200, 'portal_url': portal.portal_url}


__all__ = ['BillingService']
