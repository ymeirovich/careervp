"""Configured payment-provider selection."""

from __future__ import annotations

import os

from careervp.payment_providers.interface import PaymentProviderError, PaymentProviderInterface
from careervp.payment_providers.mock_provider import MockProvider
from careervp.payment_providers.stripe_provider import StripeProvider

_CONFIGURATION_ERROR = 'PAYMENT_PROVIDER_CONFIGURATION_ERROR'


def get_payment_provider() -> PaymentProviderInterface:
    """Return the payment provider selected by fail-closed runtime configuration."""
    provider_name = os.environ.get('PAYMENT_PROVIDER')
    if provider_name == 'mock':
        return MockProvider()
    if provider_name == 'stripe':
        from careervp.logic.utils.secret_provider import get_ssm_secret

        parameter_name = os.environ.get('PAYMENT_PROVIDER_API_KEY_SSM_PARAM')
        if parameter_name is None or not parameter_name.strip():
            raise PaymentProviderError(
                'PAYMENT_PROVIDER_API_KEY_SSM_PARAM is required for Stripe',
                code=_CONFIGURATION_ERROR,
            )
        return StripeProvider(api_key=get_ssm_secret(parameter_name))
    raise PaymentProviderError(
        'PAYMENT_PROVIDER must select a supported provider',
        code=_CONFIGURATION_ERROR,
    )
