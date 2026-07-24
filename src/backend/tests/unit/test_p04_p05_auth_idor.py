"""RED tests for P-04 (auth-fallback cleanup) and P-05 (owner-enforced routes).

Spec: docs/db-redesign/code/code-analysis/project/specs/P-04-P-05-auth-idor-spec.md
Runbook prompt: PROMPT 1.1-RED (wave-1-prompts.md)

These are the *contract*. A separate GREEN session (which has not read this reasoning and MUST NOT
edit this file) makes them pass. Four of the five P-04/P-05 tests are here; the fifth — the
cross-tenant behavioral probe with real two-tenant seeding — lives in
``tests/integration/test_p05_cross_tenant_idor.py`` so it is picked up by the runbook's integration
VERIFY selector (``-k cross_tenant``).

Why each fails today (verified against the working tree on 2026-07-24):
- ``test_p04_no_x_user_id_fallbacks_remain``       -> fails at handlers/auth_utils.py:44
- ``test_p04_no_authorizer_disabled_runtime_switch``-> fails at infra/careervp/api_construct.py:2130
- ``test_p05_route_matrix_has_owner_assertion_for_every_authenticated_route``
                                                    -> fails because the shared identity resolver
                                                       every route depends on still trusts x-user-id
- ``test_p05_error_envelope_is_flat``              -> fails: the IDOR denial returns a bare
                                                       ``{'error': ...}`` missing classification/
                                                       error_code/field.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.security import p04_p05_route_matrix as route_matrix

_REPO_ROOT = Path(__file__).resolve().parents[4]
_HANDLERS_DIR = _REPO_ROOT / 'src' / 'backend' / 'careervp' / 'handlers'
_RUNTIME_SCAN_DIRS = (
    _REPO_ROOT / 'src' / 'backend' / 'careervp',
    _REPO_ROOT / 'infra' / 'careervp',
)
# Build output is not source; a hit there is a stale-artifact false positive (per spec Evidence note).
_EXCLUDED_PARTS = {'cdk.out', '.build', '__pycache__', 'tests'}


def _iter_python_files(root: Path):
    for path in root.rglob('*.py'):
        if _EXCLUDED_PARTS.intersection(path.parts):
            continue
        yield path


def _grep(root: Path, pattern: re.Pattern[str]) -> list[str]:
    hits: list[str] = []
    for path in _iter_python_files(root):
        for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
            if pattern.search(line):
                hits.append(f'{path.relative_to(_REPO_ROOT)}:{lineno}: {line.strip()}')
    return hits


# --------------------------------------------------------------------------------------------------
# P-04
# --------------------------------------------------------------------------------------------------


def test_p04_no_x_user_id_fallbacks_remain() -> None:
    """[AC-P04-1] No handler may derive identity from a client-supplied ``x-user-id`` header.

    RED today: careervp/handlers/auth_utils.py:44 falls back to the ``x-user-id`` / ``X-User-Id``
    request header when Cognito claims are absent, which lets a caller assert any identity.
    """
    pattern = re.compile(r'x-user-id', re.IGNORECASE)
    hits = _grep(_HANDLERS_DIR, pattern)
    assert hits == [], (
        'Client-supplied x-user-id identity fallback still present in handler code '
        '(P-04 requires identity to come only from validated JWT claims / P-24 resolver):\n' + '\n'.join(hits)
    )


def test_p04_no_authorizer_disabled_runtime_switch() -> None:
    """[AC-P04-1] The dead ``AUTHORIZER_DISABLED`` bypass switch must not exist in runtime/infra code.

    RED today: infra/careervp/api_construct.py:2130 still injects ``AUTHORIZER_DISABLED`` into the
    CV-tailoring Lambda environment. It has zero code readers, but it is a re-armable auth bypass and
    P-04 requires it deleted.
    """
    pattern = re.compile(r'AUTHORIZER_DISABLED')
    hits: list[str] = []
    for root in _RUNTIME_SCAN_DIRS:
        hits.extend(_grep(root, pattern))
    assert hits == [], (
        'AUTHORIZER_DISABLED bypass switch still present in runtime/infra code '
        '(P-04 requires it deleted, and never rebuilt as a lever):\n' + '\n'.join(hits)
    )


# --------------------------------------------------------------------------------------------------
# P-05
# --------------------------------------------------------------------------------------------------


def test_p05_route_matrix_has_owner_assertion_for_every_authenticated_route() -> None:
    """[AC-P05-1] Coverage ratchet built from the LIVE CDK route_map.

    Two things are asserted, read fresh from ``infra/careervp/api_construct.py`` at test time so this
    can never silently rot against a frozen snapshot:

    (a) COVERAGE RATCHET (structural): every authenticated route that carries a foreign resource id
        in its path (an IDOR surface) is served by a handler that has a real cross-tenant owner-check
        probe in ``tests/integration/test_p05_cross_tenant_idor.py``. Adding a new such route without
        a probe breaks this test — that is the whole point.

    (b) The owner assertions those probes exercise are only as strong as the ONE identity resolver
        every authenticated handler calls, ``careervp.handlers.auth_utils.extract_user_id``. This
        test fails RED today because that resolver still honours a forged ``x-user-id`` header, so
        every per-route owner check is currently bypassable at a single shared point.
    """
    # (a) structural ratchet — handlers covered by the cross-tenant integration probe.
    from tests.integration import p05_owner_check_registry as registry

    covered_handlers = set(registry.COVERED_HANDLERS)
    resource_routes = route_matrix.resource_by_id_routes()
    assert resource_routes, 'Parsed zero resource-by-id routes — the route_map parser has drifted.'

    uncovered = sorted(f'{r.method} {r.path} (handler={r.handler_attr})' for r in resource_routes if r.handler_attr not in covered_handlers)
    assert uncovered == [], (
        'These authenticated routes carry a foreign resource id but their handler has no '
        'cross-tenant owner-check probe (add one to tests/integration/test_p05_cross_tenant_idor.py '
        'and register the handler):\n' + '\n'.join(uncovered)
    )

    # (b) the shared resolver every authenticated route trusts must not accept a client header.
    from careervp.handlers.auth_utils import extract_user_id

    forged_event = {
        'requestContext': {'httpMethod': 'GET', 'path': '/jobs/victim-owned'},  # no authorizer claims
        'headers': {'x-user-id': 'victim-tenant-id'},
    }
    resolved = extract_user_id(forged_event)
    assert resolved is None, (
        'extract_user_id() resolved identity from the client-supplied x-user-id header '
        f'(returned {resolved!r}); every per-route owner check in the matrix is bypassable through '
        'this single shared resolver until the P-04 fallback is removed.'
    )


def test_p05_error_envelope_is_flat() -> None:
    """[AC-P05-2] An IDOR denial must use the §3 item-10 FLAT error envelope.

    RED today: a cross-tenant GET on another user's job returns 403 with a bare ``{'error': ...}``
    body that is missing the ``classification`` / ``error_code`` / ``field`` keys the flat envelope
    requires. The response must never nest an ``error.code`` object (that shape breaks the frontend
    401 -> refresh -> sign-out oracle).

    This drives the real handler with a legitimately authenticated *other* tenant (Cognito claims for
    user B) requesting user A's job — i.e. the ownership check that already exists, whose denial
    envelope P-05 must standardise.
    """
    import json

    import boto3
    from moto import mock_aws

    from tests.integration import p05_seeding

    with mock_aws():
        p05_seeding.create_all_tables(boto3.resource('dynamodb', region_name='us-east-1'))
        env = p05_seeding.table_env()
        with p05_seeding.patched_env(env):
            victim = 'tenant-A-victim'
            attacker = 'tenant-B-attacker'
            job_id = p05_seeding.seed_job(owner_user_id=victim)

            from careervp.handlers.job_handler import _reset_handler_caches, lambda_handler

            _reset_handler_caches()
            event = p05_seeding.authed_event(
                path=f'/jobs/{job_id}',
                method='GET',
                claims_sub=attacker,
                path_params={'jobId': job_id},
            )
            response = lambda_handler(event, p05_seeding.lambda_context())
            _reset_handler_caches()

    assert response['statusCode'] in (403, 404), f'Expected an ownership denial (403/404) for cross-tenant job read, got {response["statusCode"]}.'
    body = json.loads(response['body'])

    # No nested error.code object (frontend contract).
    assert not (isinstance(body.get('error'), dict) and 'code' in body['error']), f'IDOR denial must not nest an error.code object; got body={body}'
    # Flat envelope required keys.
    assert ('error' in body) or ('message' in body), f'Denial envelope missing error/message: {body}'
    missing = [k for k in ('classification', 'error_code', 'field') if k not in body]
    assert missing == [], f'IDOR denial envelope is not the flat §3 item-10 shape; missing keys {missing}. body={body}'
