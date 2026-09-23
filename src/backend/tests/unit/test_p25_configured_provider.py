"""P-25 configured payment-provider selection contract."""

from __future__ import annotations

import importlib
import os
import secrets
from collections.abc import Callable
from types import ModuleType
from typing import Any, cast

import pytest

from careervp.logic.utils import secret_provider
from careervp.payment_providers.interface import PaymentProviderError, PaymentProviderInterface
from careervp.payment_providers.mock_provider import MockProvider
from careervp.payment_providers.stripe_provider import StripeProvider

_FACTORY_MODULE = 'careervp.payment_providers.factory'
_API_KEY_PARAMETER = '/careervp/test/payment-provider-api-key'

ProviderFactory = Callable[[], PaymentProviderInterface]


def _import_provider_factory_module() -> ModuleType:
    try:
        return importlib.import_module(_FACTORY_MODULE)
    except ImportError as exc:
        pytest.fail(f'AC-P25-1 configured-provider factory module {_FACTORY_MODULE!r} is missing or unimportable: {exc}', pytrace=False)


@pytest.mark.parametrize('unsupported_provider', ['placeholder', 'bogus'])
def test_p25_configured_provider_factory_selects_mock_and_stripe(
    monkeypatch: pytest.MonkeyPatch,
    unsupported_provider: str,
) -> None:
    """Configuration selects exact concrete providers and fails closed."""
    fixture_secret = f'p25-{secrets.token_urlsafe(32)}'
    resolver_calls: list[str] = []

    def resolve_fixture_secret(parameter_name: str) -> str:
        resolver_calls.append(parameter_name)
        return fixture_secret

    monkeypatch.setattr(secret_provider, 'get_ssm_secret', resolve_fixture_secret)
    factory_module = _import_provider_factory_module()
    factory_candidate: Any = getattr(factory_module, 'get_payment_provider', None)
    assert callable(factory_candidate), f'AC-P25-1 {_FACTORY_MODULE}.get_payment_provider must be callable'
    factory = cast(ProviderFactory, factory_candidate)
    if hasattr(factory_module, 'get_ssm_secret'):
        monkeypatch.setattr(factory_module, 'get_ssm_secret', resolve_fixture_secret)

    monkeypatch.delenv('PAYMENT_PROVIDER_API_KEY_SSM_PARAM', raising=False)
    monkeypatch.delenv('STRIPE_SECRET_KEY', raising=False)
    monkeypatch.setenv('PAYMENT_PROVIDER', 'mock')
    mock_result = factory()
    assert type(mock_result) is MockProvider

    monkeypatch.setenv('PAYMENT_PROVIDER', 'stripe')
    monkeypatch.setenv('PAYMENT_PROVIDER_API_KEY_SSM_PARAM', _API_KEY_PARAMETER)
    stripe_result = factory()
    assert resolver_calls == [_API_KEY_PARAMETER]
    assert fixture_secret not in os.environ.values()
    assert type(stripe_result) is StripeProvider
    assert vars(stripe_result).get('_api_key') == fixture_secret

    monkeypatch.setenv('PAYMENT_PROVIDER', unsupported_provider)
    with pytest.raises(PaymentProviderError) as error:
        factory()
    assert error.value.code == 'PAYMENT_PROVIDER_CONFIGURATION_ERROR'
