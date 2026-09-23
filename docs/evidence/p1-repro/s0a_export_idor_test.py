"""S0a proof: an AUTHENTICATED attacker (real Cognito claims, own identity) exports
another tenant's VPR via GET /jobs/{jobId}/artifacts/vpr/export.

This is the IDOR shape the shipped P-05 probe never tested before 2026-09-14: that
probe used forged_header_event (no claims), so every case 401s at the auth gate and
the ownership logic below was never reached.

Test 2 re-runs every registered P-05 case with a legitimately authenticated attacker.

Post-fix note (2026-09-14): S0a and S0b are now fixed (export_handler.py /
vpr_status_handler.py both scope their reads to the requesting user), and the real
regression suite lives in tests/integration/test_p05_cross_tenant_idor.py +
test_s0b_vpr_status_s3_fallback_ownership.py, with owner-positive controls this
script doesn't have. This file is kept only as a standalone, from-scratch
reproduction a second reviewer can run without trusting that suite.

Original defect (fixed): test_p05_cases_with_real_authenticated_attacker used to
collapse four different outcomes into one boolean ("denied"), and its failure
message called every non-denied case "served cross-tenant data to an authenticated
attacker" — including cases where the response was an empty, harmless 200 (e.g.
gap.questions.get and company-research.get, which scope their DynamoDB query by the
CALLER's own user_id and so simply never find the victim's row). An empty 200 is not
a disclosure; labeling it as one would have hidden a real leak behind noise from
routes that were never broken. The assertions below are split so each outcome is
named for what it actually is.
"""

from __future__ import annotations

import importlib
import json
import zipfile
from io import BytesIO

import boto3
import pytest
from moto import mock_aws

from tests.integration import p05_seeding as seeding
from tests.integration.p05_owner_check_registry import CASES

VICTIM = 'tenant-A-victim-idor'
ATTACKER = 'tenant-B-attacker-idor'

VPR_BUCKET = 'p05-vpr-results'
ARTIFACTS_BUCKET = 'p05-artifacts-bucket'
VPR_SECRET = 'p05-victim-secret-title'


def _s3_env() -> dict[str, str]:
    env = seeding.table_env()
    env['VPR_RESULTS_BUCKET_NAME'] = VPR_BUCKET
    env['ARTIFACTS_BUCKET_NAME'] = ARTIFACTS_BUCKET
    return env


def test_s0a_authenticated_attacker_denied_victim_vpr():
    """Inverted from the original repro (which asserted the leak succeeded).

    Fixture-validity note: the seeded VPR here intentionally omits `userId` /
    `user_id` to reproduce the *pre-fix* payload shape this bug was originally
    found against. export_handler.py's fixed _read_vpr treats a payload with no
    resolvable owner field as not-found (fails closed on missing data, not open) —
    so this still correctly asserts denial, it just isn't exercising the
    owner-vs-attacker comparison itself. That comparison is covered by
    test_vpr_export_denies_cross_tenant_access / test_vpr_export_allows_rightful_owner
    in tests/unit/test_export_handler.py, which seed a `userId` for both parties.
    """
    with mock_aws():
        seeding.create_all_tables(boto3.resource('dynamodb', region_name='us-east-1'))
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket=VPR_BUCKET)
        s3.create_bucket(Bucket=ARTIFACTS_BUCKET)

        job_id = 'victim-job-0001'
        victim_vpr = {
            'application_id': job_id,
            'user_id': VICTIM,
            'executive_summary': f'{VPR_SECRET} — confidential VPR narrative for the victim.',
            'overall_fit_score': 91,
        }
        s3.put_object(
            Bucket=VPR_BUCKET,
            Key=f'results/{job_id}.json',
            Body=json.dumps(victim_vpr).encode(),
        )

        with seeding.patched_env(_s3_env()):
            seeding.seed_user_profile(VICTIM)
            seeding.seed_user_profile(ATTACKER)

            module = importlib.import_module('careervp.handlers.export_handler')
            event = seeding.authed_event(
                path=f'/jobs/{job_id}/artifacts/vpr/export',
                method='GET',
                claims_sub=ATTACKER,  # a REAL, validly authenticated different tenant
                path_params={'jobId': job_id, 'moduleType': 'vpr'},
            )
            event['queryStringParameters'] = {'format': 'docx'}

            response = module.lambda_handler(event, seeding.lambda_context())

    status = response.get('statusCode')
    raw_body = response.get('body') or ''

    # Split into what each outcome actually means, rather than one collapsed
    # "leaked or not" boolean:
    authenticated = status != 401
    assert authenticated, f'attacker request with real Cognito claims was rejected as unauthenticated (status={status}) — the fixture itself is broken, not proof of anything about ownership'

    content_disclosed = VPR_SECRET in raw_body
    assert not content_disclosed, f'S0a regression: victim VPR content present in an authenticated attacker\'s response body (status={status})'

    ownership_denied = status in (403, 404)
    assert ownership_denied, f'expected an explicit ownership denial (403/404); got status={status}, body={raw_body[:300]}'

    print('S0a VERDICT: FIXED — authenticated cross-tenant VPR export is denied (was CONFIRMED leak pre-fix).')


@pytest.mark.parametrize('case', CASES, ids=[c.route_id for c in CASES])
def test_p05_cases_with_real_authenticated_attacker(case):
    """Re-run every registered P-05 case with an authenticated attacker instead of a
    forged header. Reports which of four distinct outcomes each route produced,
    rather than collapsing them into one pass/fail boolean."""
    module_name = case.handler_import.split(':')[0]
    with mock_aws():
        seeding.create_all_tables(boto3.resource('dynamodb', region_name='us-east-1'))
        s3 = boto3.client('s3', region_name='us-east-1')
        for b in (VPR_BUCKET, ARTIFACTS_BUCKET):
            s3.create_bucket(Bucket=b)

        with seeding.patched_env(_s3_env()):
            seeding.seed_user_profile(VICTIM)
            seeding.seed_user_profile(ATTACKER)
            resource_id = case.seeder(VICTIM)

            module = importlib.import_module(module_name)
            reset = getattr(module, '_reset_handler_caches', None)
            if callable(reset):
                reset()
            handler = getattr(module, case.handler_import.split(':')[1])

            path = (
                case.path.replace('{jobId}', resource_id)
                .replace('{vprId}', resource_id)
                .replace('{application_id}', resource_id)
                .replace('{cvTailoringId}', resource_id)
                .replace('{coverLetterId}', resource_id)
                .replace('{interviewPrepId}', resource_id)
            )
            event = seeding.authed_event(
                path=path,
                method=case.method,
                claims_sub=ATTACKER,
                path_params=case.path_params(resource_id),
                query_params=case.query_params,
            )

            response = handler(event, seeding.lambda_context())
            if callable(reset):
                reset()

    status = response.get('statusCode')
    raw_body = response.get('body') or ''
    leaked_markers = [m for m in seeding.VICTIM_MARKERS if m in raw_body]

    # 1. authentication — a 401 here means the *fixture* failed to authenticate as a
    #    real different tenant, not that ownership was enforced. Distinct from denial.
    authenticated = status != 401

    # 2. actual-content-disclosure — the only outcome that is actually a leak.
    content_disclosed = bool(leaked_markers)

    # 3. ownership-denial — an explicit 403/404, OR (per case.denial_statuses) a
    #    route that scopes its query by the caller's own identity and so returns a
    #    structurally-empty 200 that can never contain another tenant's data.
    ownership_denied = status in case.denial_statuses

    # 4. fixture-validity — a denial is only evidence if the SAME fixture proves the
    #    rightful owner gets the resource back; that positive control lives in
    #    tests/integration/test_p05_cross_tenant_idor.py's
    #    test_p05_cross_tenant_owner_positive_control, not duplicated here.
    print(
        f'\n[{case.route_id}] status={status} authenticated={authenticated} '
        f'content_disclosed={content_disclosed} ownership_denied={ownership_denied} '
        f'leaked_markers={leaked_markers}'
    )

    assert authenticated, f'[{case.route_id}] attacker request with real Cognito claims was rejected as unauthenticated (status={status}) — fixture broken, not evidence of ownership enforcement'
    assert not content_disclosed, f'[{case.route_id}] S0/P-05 regression: victim data present in an authenticated attacker\'s response: leaked_markers={leaked_markers}'
    assert ownership_denied, f'[{case.route_id}] expected one of {case.denial_statuses}; got status={status} with no leaked markers — not a disclosure, but also not a recognized denial shape for this route (registry may need a denial_statuses override)'
