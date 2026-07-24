"""[AC-P05-1] Cross-tenant IDOR denial — the correctness-critical P-05 RED test.

Spec: docs/db-redesign/code/code-analysis/project/specs/P-04-P-05-auth-idor-spec.md
Runbook prompt: PROMPT 1.1-RED (wave-1-prompts.md)

Both tenants are REALLY seeded (a victim record owned by tenant A, and tenant B exists as a distinct
identity). The attack models the actual live vulnerability: a request reaches a handler with NO
Cognito authorizer claims but a forged ``x-user-id`` header naming the victim — exactly the shape
``careervp.handlers.auth_utils.extract_user_id`` still trusts today (handlers/auth_utils.py:44). The
handler therefore resolves the caller AS the victim and serves the victim's resource.

Contract asserted per route:
- the handler MUST fail closed (HTTP 401) — identity may not be derived from a client header — and
- NONE of the victim's seeded field values may appear in the response body.

RED today: the forged header resolves to the victim, so the handler returns the victim's data
(status != 401 and/or victim markers present). GREEN once P-04 removes the header fallback:
``extract_user_id`` returns ``None`` -> every covered handler returns 401.

This test uses moto (in-process, no live API) so it runs deterministically in the integration leg
rather than skipping on a missing ``API_BASE`` — a skipped test is not RED (RUNBOOK-RULES.md rule 7).
"""

from __future__ import annotations

import importlib
import json
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


@pytest.mark.parametrize('case', CASES, ids=[c.route_id for c in CASES])
def test_p05_cross_tenant_authenticated_routes_deny(case: OwnerCheckCase) -> None:
    module_name = case.handler_import.split(':')[0]
    with mock_aws():
        seeding.create_all_tables(boto3.resource('dynamodb', region_name='us-east-1'))
        with seeding.patched_env(seeding.table_env()):
            # Seed BOTH tenants: victim owns the resource; attacker exists as a real, distinct user.
            seeding.seed_user_profile(VICTIM)
            seeding.seed_user_profile(ATTACKER)
            resource_id = case.seeder(VICTIM)

            _reset_caches(module_name)
            handler = _resolve_handler(case.handler_import)
            event = seeding.forged_header_event(
                path=case.path.replace('{jobId}', resource_id)
                .replace('{vprId}', resource_id)
                .replace('{application_id}', resource_id)
                .replace('{cvTailoringId}', resource_id)
                .replace('{coverLetterId}', resource_id)
                .replace('{interviewPrepId}', resource_id),
                method=case.method,
                victim_user_id=VICTIM,
                path_params=case.path_params(resource_id),
            )
            response = handler(event, seeding.lambda_context())
            _reset_caches(module_name)

    status = response.get('statusCode')
    raw_body = response.get('body') or ''
    try:
        body = json.loads(raw_body)
    except (ValueError, TypeError):
        body = {}

    leaked_markers = [m for m in seeding.VICTIM_MARKERS if m in raw_body]

    assert status == 401 and not leaked_markers, (
        f'[{case.route_id}] cross-tenant IDOR not denied. A forged x-user-id header (no Cognito '
        f'claims) naming the victim reached {case.handler_attr} and was honoured. '
        f'Expected fail-closed 401 with no victim data; got status={status}, '
        f'leaked_markers={leaked_markers}, body={body}'
    )
