"""
RED tests for clause P-25 — payment-provider port + MockProvider (Wave-2 step 2.0).

Spec: docs/db-redesign/code/code-analysis/project/specs/P-25-payment-provider-spec.md
Acceptance criteria under test:
  * AC-P25-1 — billing logic uses the provider *port*, not concrete provider classes,
               and preserves the frontend checkout/portal URL contract.
  * AC-P25-2 — MockProvider webhook verification rejects a tampered body / signature /
               timestamp.

Authored by the RED session (RUNBOOK-RULES rule 7): TEST FILES ONLY. No file under
src/backend/careervp/ was modified to make these run.

RED technique (rule 13) — the MockProvider does not exist yet, so a top-level
`import ... MockProvider` would raise at COLLECTION time and error out the whole file
(a collection error is "broken", not RED). Instead:

  * `test_p25_billing_service_depends_on_provider_interface_only` needs no MockProvider;
    it statically inspects the *existing* billing logic against the *existing* port and
    fails NOW on its own assertion (billing calls `retrieve_subscription`, which the port
    does not declare).
  * The three MockProvider tests import it lazily via `_load_mock_provider()`, which
    returns a `None` sentinel when the module is absent. Collection therefore succeeds and
    each test fails on its OWN guard assertion (`assert MockProvider is not None`), never on
    ImportError. The substantive assertions below each guard are the frozen contract GREEN
    must satisfy — a merely-existing but broken mock still fails them (a tampering mock that
    ignores the body, a mock that skips the timestamp check, or one that rejects everything
    all fail the body below the guard).

Bets settled while writing this file (ISSUES.md "Wave-2 bets"):
  * B-2-1 — the canonical webhook-signature format is a single compound string
    `t=<unix>,v1=<hex-hmac-sha256>` over `f"{t}.{payload}"`, tolerance 300s (Stripe's
    scheme). The mock MUST read the timestamp out of that one string; the replay test
    below puts a *fresh* timestamp in the payload body and a *stale* one in the signature,
    so a mock that reads the body instead of the signature fails.
  * B-2-2 — the "fresh id per delivery attempt" footgun lives in event *generation*, which
    2.0's mock does not expose; the id-stability + suppression test is assigned to 2.1.
    See the note at the bottom of this file and the ISSUES.md B-2-2 row.

Secrets (P-06): the webhook secret is referenced by its parameter NAME and its value is
fetched from the environment at runtime — never a literal real secret in source.
"""

from __future__ import annotations

import ast
import hashlib
import hmac
import inspect
import json
import os
import secrets
import textwrap
import time
from types import ModuleType
from typing import Any

import pytest

from careervp.logic import billing_service, reconciliation_service, webhook_service
from careervp.logic.billing_service import BillingService
from careervp.payment_providers import interface as interface_module
from careervp.payment_providers.interface import PaymentProviderError

# ─── Canonical webhook-signature scheme (B-2-1) ───────────────────────────────
# A single compound header string, identical in shape to Stripe's `Stripe-Signature`.
# 2.0b checks Stripe against THIS: v1 = HMAC-SHA256(secret, f"{t}.{payload}"), header
# `t=<unix>,v1=<hex>`, freshness window WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS.
WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300

# Exact error code the mock must raise when the signed timestamp is outside tolerance
# (the spec's "exact replay error"; distinct from a generic signature failure).
EXPECTED_REPLAY_ERROR_CODE = 'WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE'

# P-06: parameter NAME in the environment; value fetched at runtime, never a literal secret.
_WEBHOOK_SECRET_ENV = 'PAYMENT_PROVIDER_WEBHOOK_SECRET'


def _sign(payload: bytes, secret: str, timestamp: int) -> str:
    """Produce the canonical compound signature header for `payload` at `timestamp`."""
    signed_payload = str(timestamp).encode('utf-8') + b'.' + payload
    digest = hmac.new(secret.encode('utf-8'), signed_payload, hashlib.sha256).hexdigest()
    return f't={timestamp},v1={digest}'


def _event_payload(event_id: str, event_type: str, created: int) -> bytes:
    """Deterministic JSON webhook body (sorted keys, compact) so signing is stable."""
    body = {
        'id': event_id,
        'type': event_type,
        'created': created,
        'data': {'object': {'id': 'sub_test_001', 'customer': 'cus_test_001'}},
    }
    return json.dumps(body, separators=(',', ':'), sort_keys=True).encode('utf-8')


@pytest.fixture
def webhook_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """A generated per-test HMAC key exposed via the P-06 parameter-name env var.

    No real secret is committed: a random value is generated and written into the
    environment under `_WEBHOOK_SECRET_ENV`, then fetched back by name at runtime.
    """
    value = 'whsec_' + secrets.token_hex(16)
    monkeypatch.setenv(_WEBHOOK_SECRET_ENV, value)
    return os.environ[_WEBHOOK_SECRET_ENV]


def _load_mock_provider() -> Any | None:
    """Import MockProvider lazily; return None when the module is not yet implemented.

    Keeping this out of module scope means collection never trips on the missing module,
    so each test fails on its own guard assertion rather than on a collection error.
    """
    try:
        from careervp.payment_providers.mock_provider import MockProvider
    except ImportError:
        return None
    return MockProvider


# ─── AC-P25-1: billing depends on the port only ───────────────────────────────


def _declared_port_methods() -> set[str]:
    """The public method names the PaymentProviderInterface Protocol declares."""
    src = textwrap.dedent(inspect.getsource(interface_module.PaymentProviderInterface))
    classdef = ast.parse(src).body[0]
    assert isinstance(classdef, ast.ClassDef)
    return {node.name for node in classdef.body if isinstance(node, ast.FunctionDef) and not node.name.startswith('_')}


def _provider_methods_called_in(module: ModuleType) -> set[str]:
    """Every method name invoked on `self._payment_provider` inside `module`."""
    tree = ast.parse(inspect.getsource(module))
    called: set[str] = set()
    for node in ast.walk(tree):
        # Match  self._payment_provider.<name>
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == '_payment_provider'
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == 'self'
        ):
            called.add(node.attr)
    return called


_CONCRETE_PROVIDER_TOKENS = ('PlaceholderPaymentProvider', 'StripeProvider', 'MockProvider')


def test_p25_billing_service_depends_on_provider_interface_only() -> None:
    """AC-P25-1: billing logic may call only methods the provider port declares, and may
    name no concrete provider class.

    RED now: WebhookService and ReconciliationService both call
    `retrieve_subscription`, which PaymentProviderInterface does not declare — so billing
    depends on a concrete provider's API, not on the port. Goes green when GREEN either
    declares that method on the port or removes the dependency.
    """
    port_methods = _declared_port_methods()
    billing_modules = (billing_service, webhook_service, reconciliation_service)

    called: set[str] = set()
    for module in billing_modules:
        called |= _provider_methods_called_in(module)
    undeclared = called - port_methods

    concrete_refs: set[str] = set()
    for module in billing_modules:
        source = inspect.getsource(module)
        concrete_refs |= {token for token in _CONCRETE_PROVIDER_TOKENS if token in source}

    violations: list[str] = []
    if undeclared:
        violations.append(f'billing calls provider methods not on the port: {sorted(undeclared)} (port declares {sorted(port_methods)})')
    if concrete_refs:
        violations.append(f'billing names concrete provider class(es): {sorted(concrete_refs)}')

    assert violations == [], 'AC-P25-1 violations — ' + '; '.join(violations)


# ─── AC-P25-2: MockProvider webhook verification ──────────────────────────────


def test_p25_mock_webhook_rejects_tampered_signature(webhook_secret: str) -> None:
    """AC-P25-2: a valid signature is accepted, but mutating the signed body afterwards
    makes verification reject the event with PaymentProviderError.

    Teeth: a mock whose signature check ignores the body would accept the tampered payload
    and fail this test; a mock that rejects everything would fail the valid-accept step.
    """
    MockProvider = _load_mock_provider()
    assert MockProvider is not None, (
        'AC-P25-2: careervp/payment_providers/mock_provider.py:MockProvider is not '
        'implemented yet — construct_webhook_event must reject a body-tampered payload '
        'with PaymentProviderError.'
    )
    provider = MockProvider()

    payload = _event_payload('evt_tamper_001', 'checkout.session.completed', int(time.time()))
    signature = _sign(payload, webhook_secret, int(time.time()))

    # Valid signature is accepted (proves the mock is not simply rejecting everything).
    event = provider.construct_webhook_event(payload, signature, webhook_secret)
    assert event.event_id == 'evt_tamper_001'

    # Same signature, mutated body → rejected.
    tampered = payload.replace(b'evt_tamper_001', b'evt_tamper_XXX')
    assert tampered != payload
    with pytest.raises(PaymentProviderError):
        provider.construct_webhook_event(tampered, signature, webhook_secret)


def test_p25_mock_webhook_rejects_replay_timestamp(webhook_secret: str) -> None:
    """AC-P25-2: a cryptographically valid signature whose timestamp is older than
    WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS is rejected with the exact replay error code.

    The timestamp is carried ONLY in the compound signature string; the payload body's
    `created` field is fresh. A mock that reads the timestamp from the body (or skips the
    timestamp check) would accept the stale signature and fail this test — this is the
    B-2-1 forcing function.
    """
    MockProvider = _load_mock_provider()
    assert MockProvider is not None, (
        'AC-P25-2: careervp/payment_providers/mock_provider.py:MockProvider is not '
        'implemented yet — construct_webhook_event must reject a stale-timestamp '
        f'signature with PaymentProviderError code {EXPECTED_REPLAY_ERROR_CODE!r}.'
    )
    provider = MockProvider()

    now = int(time.time())
    payload = _event_payload('evt_replay_001', 'checkout.session.completed', created=now)

    # Fresh signature is accepted (proves the mock is not simply rejecting everything).
    fresh_signature = _sign(payload, webhook_secret, now)
    accepted = provider.construct_webhook_event(payload, fresh_signature, webhook_secret)
    assert accepted.event_id == 'evt_replay_001'

    # Valid digest, but the signed timestamp is outside tolerance → distinct replay error.
    stale_ts = now - WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS - 1
    stale_signature = _sign(payload, webhook_secret, stale_ts)
    with pytest.raises(PaymentProviderError) as excinfo:
        provider.construct_webhook_event(payload, stale_signature, webhook_secret)
    assert excinfo.value.code == EXPECTED_REPLAY_ERROR_CODE


def test_p25_checkout_portal_contract_shape_preserved(webhook_secret: str) -> None:
    """AC-P25-1: checkout and portal responses expose the exact URL fields the frontend
    consumes — `checkout_url` and `portal_url`.

    Field names derived from src/frontend (NOT swagger, which is non-authoritative):
      * checkout_url — components/billing/PlansSection.tsx:59,81
      * portal_url   — components/billing/BillingInfoCard.tsx:79, api/methods.ts:70

    Routed through the MockProvider (P-25's launch-rehearsal provider) so the assertion
    proves the mock preserves the frontend contract end-to-end through BillingService.
    """
    MockProvider = _load_mock_provider()
    assert MockProvider is not None, (
        'AC-P25-1: careervp/payment_providers/mock_provider.py:MockProvider is not '
        'implemented yet — checkout/portal responses must carry the frontend fields '
        "'checkout_url' and 'portal_url'."
    )
    provider = MockProvider()

    sub_repo: Any = _make_billing_sub_repo()
    user_repo: Any = _make_user_repo()
    billing = BillingService(sub_repo, user_repo, provider)

    checkout = billing.handle_checkout(
        user_id='user_test_1',
        plan='monthly',
        success_url='https://app.example.test/billing/success',
        cancel_url='https://app.example.test/billing/cancel',
    )
    assert checkout['status_code'] == 200, checkout
    assert 'checkout_url' in checkout
    assert isinstance(checkout['checkout_url'], str) and checkout['checkout_url']

    portal = billing.handle_portal(
        user_id='user_test_1',
        return_url='https://app.example.test/billing',
    )
    assert portal['status_code'] == 200, portal
    assert 'portal_url' in portal
    assert isinstance(portal['portal_url'], str) and portal['portal_url']


def _make_billing_sub_repo() -> Any:
    """A subscription repo stub that lets handle_checkout/handle_portal reach the provider."""
    from unittest.mock import MagicMock

    from careervp.models.result import Result

    repo = MagicMock()
    # No existing subscription → checkout proceeds to the provider.
    repo.get_subscription.return_value = Result(success=False, data=None, code='NOT_FOUND')
    repo.get_customer_id.return_value = 'cus_test_existing_1'  # skip customer creation
    return repo


def _make_user_repo() -> Any:
    from unittest.mock import MagicMock

    repo = MagicMock()
    repo.get_user.return_value = {'email': 'user@example.test'}
    return repo


# ─── B-2-2 note: test_p25_mock_event_id_is_stable_across_retries is intentionally omitted ──
#
# The prompt lists this NEW test with an explicit escape hatch ("If you conclude this
# belongs to 2.1 rather than here, say so and leave it out rather than writing a weak
# version"). The footgun B-2-2 names — "the mock issues a FRESH id per delivery attempt
# where Stripe reuses ONE id across retries" — lives in the mock's event *generation /
# emission* surface. Clause P-25 (project-scope-lock.yaml) scopes the mock to "signs test
# webhooks + returns realistic subscription/customer objects"; it does not include a
# retry/emission API, and inventing one here to test it would over-reach the clause
# (rule 5). A 2.0-only test restricted to construct_webhook_event parsing can assert only
# "same payload → same event_id", which is trivially green for any id-from-payload mock and
# does not exercise the fresh-id-per-attempt footgun — precisely the weak version the prompt
# forbids. The test is therefore assigned to step 2.1 (the money path, which B-2-2 is
# load-bearing for and where the emission/idempotency wiring lives). The B-2-2 *decision*
# is recorded now in ISSUES.md: event_id must be stable across provider retries; if the
# provider cannot guarantee that, idempotency keys on a digest of the verified raw payload.
