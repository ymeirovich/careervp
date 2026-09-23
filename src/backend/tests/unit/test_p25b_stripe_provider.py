"""
RED tests for AC-P25b-1 — StripeProvider signature verification and paid-launch gate.

Spec: docs/db-redesign/code/code-analysis/project/specs/P-25-payment-provider-spec.md
scope_lock_clause: P-25b

This RED session changes tests and the spec's RED-test brief only. It must not add
StripeProvider or modify any billing implementation.

Rule-13 import technique: each test imports the not-yet-existing stripe_provider
module dynamically inside the test, catches only that module's ModuleNotFoundError
into a None sentinel, and then fails on an explicit AC-P25b-1 guard assertion.
Collection therefore succeeds; neither test is red because of a bare ImportError.

B-2-1 cross-check: Stripe signs the exact raw body with
HMAC-SHA256(secret, f"{timestamp}.{payload}"), uses a caller-side default tolerance
of 300 seconds, and can include multiple v1 signatures while rolling a secret.
The valid header below deliberately puts the matching digest in the second v1 slot.

Secrets (P-06): the fixture generates values at runtime, stores the verification
secret under the PAYMENT_PROVIDER_WEBHOOK_SECRET environment parameter name, and
reads it back by name. No secret value is committed in the test body.
"""

from __future__ import annotations

import hashlib
import hmac
import importlib
import json
import os
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

from careervp.payment_providers.interface import PaymentProviderError, PaymentProviderInterface, WebhookEvent
from careervp.payment_providers.mock_provider import (
    WEBHOOK_SIGNATURE_VERIFICATION_FAILED,
    WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE,
    WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS,
)

_STRIPE_PROVIDER_MODULE = 'careervp.payment_providers.stripe_provider'
_WEBHOOK_SECRET_ENV = 'PAYMENT_PROVIDER_WEBHOOK_SECRET'
_EVENT_ID = 'evt_p25b_001'
_TAMPERED_EVENT_ID = 'evt_p25b_002'
_EVENT_TYPE = 'checkout.session.completed'
_NON_MATCHING_V1 = '0' * 64
_IGNORED_V0 = 'f' * 64


@dataclass(frozen=True, repr=False)
class _WebhookSecrets:
    """Runtime-only fixture values whose repr does not expose generated secrets."""

    correct: str
    wrong: str


@pytest.fixture
def stripe_webhook_secrets(monkeypatch: pytest.MonkeyPatch) -> _WebhookSecrets:
    """Return independently generated correct/wrong secrets; correct comes from env."""
    correct_secret = 'whsec_' + secrets.token_hex(32)
    wrong_secret = 'whsec_' + secrets.token_hex(32)
    monkeypatch.setenv(_WEBHOOK_SECRET_ENV, correct_secret)
    return _WebhookSecrets(correct=os.environ[_WEBHOOK_SECRET_ENV], wrong=wrong_secret)


def _event_payload(timestamp: int) -> bytes:
    """Return the exact deterministic raw JSON body covered by AC-P25b-1."""
    return json.dumps(
        {
            'id': _EVENT_ID,
            'type': _EVENT_TYPE,
            'created': timestamp,
            'data': {'object': {'id': 'sub_p25b_001', 'customer': 'cus_p25b_001'}},
        },
        separators=(',', ':'),
        sort_keys=True,
    ).encode('utf-8')


def _stripe_signature_header(payload: bytes, secret: str, timestamp: int) -> str:
    """Build a Stripe rotation header whose matching digest is the second v1."""
    signed_payload = f'{timestamp}.'.encode('utf-8') + payload
    digest = hmac.new(secret.encode('utf-8'), signed_payload, hashlib.sha256).hexdigest()
    return f't={timestamp},v1={_NON_MATCHING_V1},v1={digest},v0={_IGNORED_V0}'


def _assert_signature_negatives(
    construct_webhook_event: Callable[[bytes, str, str], WebhookEvent],
    payload: bytes,
    valid_header: str,
    correct_secret: str,
    wrong_secret: str,
    now: int,
) -> None:
    """Execute the three exact AC-P25b-1 signature-negative assertions."""
    tampered_payload = payload.replace(_EVENT_ID.encode('utf-8'), _TAMPERED_EVENT_ID.encode('utf-8'))

    # AC-P25b-1: a body mutation under the original valid header has the exact signature-failure code.
    with pytest.raises(PaymentProviderError) as tampered_exc:
        construct_webhook_event(tampered_payload, valid_header, correct_secret)
    # AC-P25b-1: tampered body and replay failures must remain distinguishable.
    assert tampered_exc.value.code == WEBHOOK_SIGNATURE_VERIFICATION_FAILED

    # AC-P25b-1: verification with a distinct wrong secret has the exact signature-failure code.
    with pytest.raises(PaymentProviderError) as wrong_secret_exc:
        construct_webhook_event(payload, valid_header, wrong_secret)
    # AC-P25b-1: a wrong secret is a signature failure, not a replay failure.
    assert wrong_secret_exc.value.code == WEBHOOK_SIGNATURE_VERIFICATION_FAILED

    stale_timestamp = now - WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS - 1
    stale_header = _stripe_signature_header(payload, correct_secret, stale_timestamp)
    # AC-P25b-1: a valid digest signed exactly 301 seconds ago has the exact replay code.
    with pytest.raises(PaymentProviderError) as stale_exc:
        construct_webhook_event(payload, stale_header, correct_secret)
    # AC-P25b-1: the 301-second stale boundary is distinct from signature verification failure.
    assert stale_exc.value.code == WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE


def test_p25b_stripe_provider_verifies_real_signature(stripe_webhook_secrets: _WebhookSecrets) -> None:
    """AC-P25b-1: StripeProvider accepts real Stripe HMAC and rejects three exact negatives."""
    StripeProvider: type[Any] | None
    try:
        stripe_module = importlib.import_module(_STRIPE_PROVIDER_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != _STRIPE_PROVIDER_MODULE:
            raise
        StripeProvider = None
    else:
        provider_class = getattr(stripe_module, 'StripeProvider', None)
        StripeProvider = provider_class if isinstance(provider_class, type) else None
    # AC-P25b-1: RED must fail on its own assertion while StripeProvider is absent.
    assert StripeProvider is not None, 'AC-P25b-1: StripeProvider missing -> real signature verification test fails'

    correct_secret = stripe_webhook_secrets.correct
    wrong_secret = stripe_webhook_secrets.wrong
    now = int(time.time())
    payload = _event_payload(now)
    valid_header = _stripe_signature_header(payload, correct_secret, now)
    provider = StripeProvider()

    event = provider.construct_webhook_event(payload, valid_header, correct_secret)
    # AC-P25b-1: successful local verification returns the normalized port DTO.
    assert isinstance(event, WebhookEvent)
    # AC-P25b-1: the normalized event preserves the exact signed payload id.
    assert event.event_id == _EVENT_ID
    # AC-P25b-1: the normalized event preserves the exact signed payload type.
    assert event.event_type == _EVENT_TYPE

    _assert_signature_negatives(provider.construct_webhook_event, payload, valid_header, correct_secret, wrong_secret, now)


def test_p25b_paid_launch_gate_fails_without_stripe_provider(stripe_webhook_secrets: _WebhookSecrets) -> None:
    """AC-P25b-1: paid launch requires the full port and passing signature negatives."""
    StripeProvider: type[Any] | None
    try:
        stripe_module = importlib.import_module(_STRIPE_PROVIDER_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != _STRIPE_PROVIDER_MODULE:
            raise
        StripeProvider = None
    else:
        provider_class = getattr(stripe_module, 'StripeProvider', None)
        StripeProvider = provider_class if isinstance(provider_class, type) else None
    # AC-P25b-1: guarded in-test import absence fails the launch gate on this assertion.
    assert StripeProvider is not None, 'AC-P25b-1: StripeProvider missing -> paid launch gate fails'

    required_methods = {
        'create_customer',
        'create_checkout_session',
        'create_portal_session',
        'construct_webhook_event',
        'get_price_map',
        'retrieve_subscription',
    }
    missing_methods = {method for method in required_methods if not callable(getattr(StripeProvider, method, None))}
    # AC-P25b-1: the launch gate requires all six exact PaymentProviderInterface methods.
    assert missing_methods == set(), f'AC-P25b-1: StripeProvider missing port methods: {sorted(missing_methods)}'
    # AC-P25b-1: runtime Protocol structure must agree with the explicit method inventory.
    assert issubclass(StripeProvider, PaymentProviderInterface)

    correct_secret = stripe_webhook_secrets.correct
    wrong_secret = stripe_webhook_secrets.wrong
    now = int(time.time())
    payload = _event_payload(now)
    valid_header = _stripe_signature_header(payload, correct_secret, now)
    provider = StripeProvider()

    # AC-P25b-1: the paid-launch gate itself executes all three frozen negative assertions.
    _assert_signature_negatives(provider.construct_webhook_event, payload, valid_header, correct_secret, wrong_secret, now)
