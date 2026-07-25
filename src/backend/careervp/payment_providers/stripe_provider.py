"""
Stripe payment-provider implementation (clause P-25b).

Webhook verification implements Stripe's documented v1 signature scheme
directly because the official ``stripe`` SDK is not a project dependency:

* parse the timestamp and every ``v1`` digest from ``Stripe-Signature``;
* compute HMAC-SHA256 over ``b"{timestamp}." + raw_payload``;
* accept when any v1 digest matches in constant time (signing-secret rotation);
* reject a valid but stale signature with a distinct replay error code.

The remaining methods call Stripe's HTTPS API through the project's existing
``httpx`` dependency. Secrets are supplied by value: the webhook secret is a
method argument, while the API key may be passed to the constructor or resolved
upstream into ``STRIPE_SECRET_KEY``. No secret literal lives in this module.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any, cast
from urllib.parse import quote

import httpx

from careervp.payment_providers.interface import (
    CheckoutSession,
    CustomerRecord,
    PaymentProviderError,
    PaymentProviderInterface,
    PortalSession,
    WebhookEvent,
)

STRIPE_API_BASE_URL = 'https://api.stripe.com/v1'
STRIPE_API_KEY_ENV = 'STRIPE_SECRET_KEY'
WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300

WEBHOOK_SIGNATURE_VERIFICATION_FAILED = 'WEBHOOK_SIGNATURE_VERIFICATION_FAILED'
WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE = 'WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE'
WEBHOOK_PAYLOAD_INVALID = 'WEBHOOK_PAYLOAD_INVALID'

PAYMENT_PROVIDER_CONFIGURATION_ERROR = 'PAYMENT_PROVIDER_CONFIGURATION_ERROR'
PAYMENT_PROVIDER_TIMEOUT = 'PAYMENT_PROVIDER_TIMEOUT'
PAYMENT_PROVIDER_NETWORK_ERROR = 'PAYMENT_PROVIDER_NETWORK_ERROR'
PAYMENT_PROVIDER_AUTHENTICATION_FAILED = 'PAYMENT_PROVIDER_AUTHENTICATION_FAILED'
PAYMENT_PROVIDER_RATE_LIMITED = 'PAYMENT_PROVIDER_RATE_LIMITED'
PAYMENT_PROVIDER_API_ERROR = 'PAYMENT_PROVIDER_API_ERROR'
PAYMENT_PROVIDER_RESPONSE_INVALID = 'PAYMENT_PROVIDER_RESPONSE_INVALID'


class StripeProvider:
    """PaymentProviderInterface implementation backed by Stripe."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        api_base_url: str = STRIPE_API_BASE_URL,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._api_base_url = api_base_url.rstrip('/')
        self._timeout_seconds = timeout_seconds

    def create_customer(self, email: str, metadata: dict[str, str]) -> CustomerRecord:
        """Create a Stripe customer."""
        form = {'email': email}
        form.update({f'metadata[{key}]': value for key, value in metadata.items()})
        response = self._request('POST', '/customers', form=form)
        return CustomerRecord(
            customer_id=self._required_string(response, 'id', resource='customer'),
            email=self._optional_string(response, 'email', default=email),
            metadata=self._string_mapping(response.get('metadata')),
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
        """Create a hosted Stripe Checkout subscription session."""
        form = {
            'mode': 'subscription',
            'customer': customer_id,
            'line_items[0][price]': price_id,
            'line_items[0][quantity]': '1',
            'success_url': success_url,
            'cancel_url': cancel_url,
            'metadata[user_id]': user_id,
            'metadata[plan]': plan,
            'subscription_data[metadata][user_id]': user_id,
            'subscription_data[metadata][plan]': plan,
        }
        response = self._request('POST', '/checkout/sessions', form=form)
        return CheckoutSession(
            session_id=self._required_string(response, 'id', resource='checkout session'),
            checkout_url=self._required_string(response, 'url', resource='checkout session'),
            customer_id=self._optional_string(response, 'customer', default=customer_id),
            metadata=self._string_mapping(response.get('metadata')) or {'user_id': user_id, 'plan': plan},
        )

    def create_portal_session(self, customer_id: str, return_url: str) -> PortalSession:
        """Create a Stripe Billing Portal session."""
        response = self._request(
            'POST',
            '/billing_portal/sessions',
            form={'customer': customer_id, 'return_url': return_url},
        )
        return PortalSession(
            session_id=self._required_string(response, 'id', resource='portal session'),
            portal_url=self._required_string(response, 'url', resource='portal session'),
        )

    def construct_webhook_event(self, payload: bytes, signature: str, secret: str) -> WebhookEvent:
        """Verify a Stripe v1 webhook signature and normalize the signed event."""
        timestamp, provided_digests = self._parse_signature_header(signature)
        signed_payload = f'{timestamp}.'.encode('utf-8') + payload
        expected_digest = hmac.new(secret.encode('utf-8'), signed_payload, hashlib.sha256).hexdigest()

        if not any(hmac.compare_digest(expected_digest, provided_digest) for provided_digest in provided_digests):
            raise PaymentProviderError(
                'Webhook signature verification failed',
                code=WEBHOOK_SIGNATURE_VERIFICATION_FAILED,
            )

        if timestamp < int(time.time()) - WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS:
            raise PaymentProviderError(
                f'Webhook timestamp {timestamp} is older than the {WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS}s tolerance',
                code=WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE,
            )

        body = self._parse_webhook_payload(payload)
        event_id = self._required_string(body, 'id', resource='webhook event')
        event_type = self._required_string(body, 'type', resource='webhook event')
        data = self._webhook_object(body)
        created_value = body.get('created', 0)
        created = created_value if isinstance(created_value, int) and not isinstance(created_value, bool) else 0
        return WebhookEvent(event_id=event_id, event_type=event_type, data=data, created=created)

    def get_price_map(self) -> dict[str, str]:
        """Return Stripe price IDs resolved into the process environment upstream."""
        try:
            return {
                'monthly': os.environ['PRICE_ID_MONTHLY'],
                'quarterly': os.environ['PRICE_ID_QUARTERLY'],
            }
        except KeyError as exc:
            raise PaymentProviderError(
                f'Missing Stripe price configuration: {exc.args[0]}',
                code=PAYMENT_PROVIDER_CONFIGURATION_ERROR,
            ) from exc

    def retrieve_subscription(self, subscription_id: str) -> dict[str, Any]:
        """Fetch an authoritative Stripe subscription object."""
        encoded_subscription_id = quote(subscription_id, safe='')
        return self._request('GET', f'/subscriptions/{encoded_subscription_id}')

    @staticmethod
    def _parse_signature_header(signature: str) -> tuple[int, tuple[str, ...]]:
        timestamp: int | None = None
        digests: list[str] = []

        for part in signature.split(','):
            key, separator, value = part.strip().partition('=')
            if not separator or not value:
                continue
            if key == 't' and timestamp is None:
                try:
                    timestamp = int(value)
                except ValueError as exc:
                    raise PaymentProviderError(
                        'Webhook signature verification failed',
                        code=WEBHOOK_SIGNATURE_VERIFICATION_FAILED,
                    ) from exc
            elif key == 'v1':
                digests.append(value)

        if timestamp is None or not digests:
            raise PaymentProviderError(
                'Webhook signature verification failed',
                code=WEBHOOK_SIGNATURE_VERIFICATION_FAILED,
            )
        return timestamp, tuple(digests)

    @staticmethod
    def _parse_webhook_payload(payload: bytes) -> dict[str, Any]:
        try:
            parsed: object = json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PaymentProviderError(
                'Invalid webhook payload',
                code=WEBHOOK_PAYLOAD_INVALID,
            ) from exc

        if not isinstance(parsed, dict):
            raise PaymentProviderError(
                'Invalid webhook payload',
                code=WEBHOOK_PAYLOAD_INVALID,
            )
        return cast(dict[str, Any], parsed)

    @classmethod
    def _webhook_object(cls, body: dict[str, Any]) -> dict[str, Any]:
        data_value = body.get('data')
        if not isinstance(data_value, dict):
            return {}
        data = cast(dict[str, Any], data_value)
        object_value = data.get('object')
        if not isinstance(object_value, dict):
            return {}
        return cast(dict[str, Any], object_value)

    def _request(self, method: str, path: str, *, form: dict[str, str] | None = None) -> dict[str, Any]:
        api_key = self._api_key or os.environ.get(STRIPE_API_KEY_ENV)
        if not api_key:
            raise PaymentProviderError(
                f'Stripe API key was not supplied ({STRIPE_API_KEY_ENV})',
                code=PAYMENT_PROVIDER_CONFIGURATION_ERROR,
            )

        try:
            with httpx.Client(
                base_url=self._api_base_url,
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=self._timeout_seconds,
            ) as client:
                response = client.request(method, path, data=form)
        except httpx.TimeoutException as exc:
            raise PaymentProviderError('Stripe API request timed out', code=PAYMENT_PROVIDER_TIMEOUT) from exc
        except httpx.RequestError as exc:
            raise PaymentProviderError('Stripe API request failed', code=PAYMENT_PROVIDER_NETWORK_ERROR) from exc

        if response.is_error:
            raise self._api_error(response)

        try:
            parsed: object = response.json()
        except json.JSONDecodeError as exc:
            raise PaymentProviderError(
                'Stripe API returned an invalid JSON response',
                code=PAYMENT_PROVIDER_RESPONSE_INVALID,
            ) from exc
        if not isinstance(parsed, dict):
            raise PaymentProviderError(
                'Stripe API returned an unexpected response shape',
                code=PAYMENT_PROVIDER_RESPONSE_INVALID,
            )
        return cast(dict[str, Any], parsed)

    @staticmethod
    def _api_error(response: httpx.Response) -> PaymentProviderError:
        if response.status_code in {401, 403}:
            code = PAYMENT_PROVIDER_AUTHENTICATION_FAILED
        elif response.status_code == 429:
            code = PAYMENT_PROVIDER_RATE_LIMITED
        else:
            code = PAYMENT_PROVIDER_API_ERROR

        message = f'Stripe API request failed with HTTP {response.status_code}'
        try:
            parsed: object = response.json()
        except json.JSONDecodeError:
            return PaymentProviderError(message, code=code)
        if isinstance(parsed, dict):
            error_value = cast(dict[str, object], parsed).get('error')
            if isinstance(error_value, dict):
                stripe_message = cast(dict[str, object], error_value).get('message')
                if isinstance(stripe_message, str):
                    message = stripe_message
        return PaymentProviderError(message, code=code)

    @staticmethod
    def _required_string(data: dict[str, Any], key: str, *, resource: str) -> str:
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
        raise PaymentProviderError(
            f'Stripe {resource} response is missing {key!r}',
            code=PAYMENT_PROVIDER_RESPONSE_INVALID,
        )

    @staticmethod
    def _optional_string(data: dict[str, Any], key: str, *, default: str) -> str:
        value = data.get(key)
        return value if isinstance(value, str) and value else default

    @staticmethod
    def _string_mapping(value: object) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        mapping = cast(dict[object, object], value)
        return {key: item for key, item in mapping.items() if isinstance(key, str) and isinstance(item, str)}


assert isinstance(StripeProvider(), PaymentProviderInterface)
