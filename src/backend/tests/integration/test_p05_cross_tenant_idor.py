"""[AC-P05-1] Cross-tenant IDOR denial — the correctness-critical P-05 RED test.

Spec: docs/db-redesign/code/code-analysis/project/specs/P-04-P-05-auth-idor-spec.md
Runbook prompt: PROMPT 1.1-RED (wave-1-prompts.md)

Both tenants are REALLY seeded (a victim record owned by tenant A, and tenant B exists as a distinct
identity). Three things are asserted per route, not one:

1. ``test_p04_forged_header_denied`` — a P-04 regression only. The attack is a request with NO
   Cognito authorizer claims and a forged ``x-user-id`` header naming the victim — the shape
   ``auth_utils.extract_user_id`` used to trust. Since that fallback was removed, every covered route
   now stops at the 401 front door before reaching any per-route ownership code at all. A green run
   here proves P-04, and *only* P-04 — it is evidence about the shared identity resolver, not about
   any individual handler's ownership check, and must never be read as the latter.

2. ``test_p05_cross_tenant_attacker_denied`` — the actual P-05 probe. The attacker is a genuinely
   different, authenticated tenant (real Cognito claims via ``seeding.authed_event``), requesting the
   victim's resource. This is the only one of the three that can reach a handler's real per-route
   ownership check, because request 1 never gets past the authorizer boundary to begin with.

3. ``test_p05_cross_tenant_owner_positive_control`` — for every case above, the *rightful* owner must still get
   the resource back. Pass B of the 2026-09-13 audit found that some of these fixtures returned 404
   (or empty results) for the victim too — meaning "the attacker got nothing" was never evidence of
   an ownership check working, since *nobody* got anything. A denial test without this control proves
   nothing.

This test uses moto (in-process, no live API) so it runs deterministically in the integration leg
rather than skipping on a missing ``API_BASE`` — a skipped test is not RED (RUNBOOK-RULES.md rule 7).
"""

from __future__ import annotations

import importlib
from typing import Any

import boto3
import pytest
from moto import mock_aws

from tests.integration import p05_seeding as seeding
from tests.integration.p05_owner_check_registry import CASES, OwnerCheckCase

VICTIM = 'tenant-A-victim-idor'
ATTACKER = 'tenant-B-attacker-idor'


def _resolve_handler(handler_import: str) -> Any:
    module_name, callable_name = handler_import.split(':')
    module = importlib.import_module(module_name)
    return getattr(module, callable_name)


def _reset_caches(module_name: str) -> None:
    module = importlib.import_module(module_name)
    reset = getattr(module, '_reset_handler_caches', None)
    if callable(reset):
        reset()


def _resolve_path(case: OwnerCheckCase, resource_id: str) -> str:
    return (
        case.path.replace('{jobId}', resource_id)
        .replace('{vprId}', resource_id)
        .replace('{application_id}', resource_id)
        .replace('{cvTailoringId}', resource_id)
        .replace('{coverLetterId}', resource_id)
        .replace('{interviewPrepId}', resource_id)
    )


def _run_case(case: OwnerCheckCase, event: dict[str, Any]) -> dict[str, Any]:
    module_name = case.handler_import.split(':')[0]
    _reset_caches(module_name)
    handler = _resolve_handler(case.handler_import)
    response: dict[str, Any] = handler(event, seeding.lambda_context())
    _reset_caches(module_name)
    return response


def _seed_two_tenants(case: OwnerCheckCase) -> str:
    """Seed both tenants and the victim's resource; returns the seeded resource id."""
    seeding.create_all_tables(boto3.resource('dynamodb', region_name='us-east-1'))
    seeding.seed_user_profile(VICTIM)
    seeding.seed_user_profile(ATTACKER)
    return case.seeder(VICTIM)


@pytest.mark.parametrize('case', CASES, ids=[c.route_id for c in CASES])
def test_p04_forged_header_denied(case: OwnerCheckCase) -> None:
    """P-04 only: an unauthenticated forged x-user-id header must not resolve to an identity.

    This cannot reach any handler's ownership check — every case here fails at the shared
    identity resolver before ownership is ever evaluated. See module docstring point 1.
    """
    with mock_aws():
        with seeding.patched_env(seeding.table_env()):
            resource_id = _seed_two_tenants(case)
            event = seeding.forged_header_event(
                path=_resolve_path(case, resource_id),
                method=case.method,
                victim_user_id=VICTIM,
                path_params=case.path_params(resource_id),
                query_params=case.query_params,
            )
            response = _run_case(case, event)

    status = response.get('statusCode')
    raw_body = response.get('body') or ''
    leaked_markers = [m for m in seeding.VICTIM_MARKERS if m in raw_body]

    assert status == 401 and not leaked_markers, (
        f'[{case.route_id}] P-04 regression: a forged x-user-id header (no Cognito claims) naming '
        f'the victim reached {case.handler_attr} and was honoured. Expected fail-closed 401 with no '
        f'victim data; got status={status}, leaked_markers={leaked_markers}, body={raw_body[:300]}'
    )


@pytest.mark.parametrize('case', CASES, ids=[c.route_id for c in CASES])
def test_p05_cross_tenant_attacker_denied(case: OwnerCheckCase) -> None:
    """P-05: a genuinely authenticated, different tenant must be denied the victim's resource.

    Unlike the forged-header attack, this reaches each handler's real per-route ownership
    check (real Cognito claims via seeding.authed_event) — this is the actual P-05 contract.
    """
    with mock_aws():
        with seeding.patched_env(seeding.table_env()):
            resource_id = _seed_two_tenants(case)
            event = seeding.authed_event(
                path=_resolve_path(case, resource_id),
                method=case.method,
                claims_sub=ATTACKER,
                path_params=case.path_params(resource_id),
                query_params=case.query_params,
            )
            response = _run_case(case, event)

    status = response.get('statusCode')
    raw_body = response.get('body') or ''
    leaked_markers = [m for m in seeding.VICTIM_MARKERS if m in raw_body]

    assert status in case.denial_statuses and not leaked_markers, (
        f'[{case.route_id}] cross-tenant IDOR not denied. An authenticated, different tenant '
        f"(real Cognito claims, not the victim) requested the victim's resource via "
        f'{case.handler_attr} and it was not refused. Expected one of {case.denial_statuses} with no '
        f'victim data; got status={status}, leaked_markers={leaked_markers}, body={raw_body[:300]}'
    )


@pytest.mark.parametrize('case', CASES, ids=[c.route_id for c in CASES])
def test_p05_cross_tenant_owner_positive_control(case: OwnerCheckCase) -> None:
    """The rightful owner must still be able to fetch their own resource.

    Load-bearing control: without this, a denial test proves nothing — Pass B of the
    2026-09-13 audit found fixtures that returned 404/empty for the victim too, which made
    "the attacker got nothing" meaningless (nobody got anything).
    """
    with mock_aws():
        with seeding.patched_env(seeding.table_env()):
            resource_id = _seed_two_tenants(case)
            event = seeding.authed_event(
                path=_resolve_path(case, resource_id),
                method=case.method,
                claims_sub=VICTIM,
                path_params=case.path_params(resource_id),
                query_params=case.query_params,
            )
            response = _run_case(case, event)

    status = response.get('statusCode')
    raw_body = response.get('body') or ''

    assert status == 200, (
        f'[{case.route_id}] owner-positive control failed: the rightful owner (real Cognito claims) '
        f'requesting their own resource via {case.handler_attr} did not get it back. Got '
        f'status={status}, body={raw_body[:300]}. Without this passing, a denial test for this '
        f'route is not evidence of an ownership check.'
    )
