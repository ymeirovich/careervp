"""S0b regression: the VPR status endpoint's S3 fallback must not serve
another tenant's VPR when the DynamoDB job row is absent (TTL expiry, or any
get_job() failure that returns None — jobs_repository.py swallows ClientError
to None).

Promoted from docs/evidence/p1-repro/s0b_status_fallback_test.py (P1
adversarial validation, 2026-09-12), which is written inverted — it PASSED
when the defect was present. Inverted here, plus an owner-positive control:
Pass B of that same audit found that a denial test proves nothing on its own
if the rightful owner would also have been denied.
"""

from __future__ import annotations

import importlib
import json

import boto3
from moto import mock_aws

from tests.integration import p05_seeding as seeding

VICTIM = 'tenant-A-victim-idor'
ATTACKER = 'tenant-B-attacker-idor'
VPR_BUCKET = 'p05-vpr-results'
VPR_SECRET = 'victim-secret-title-confidential'
VPR_ID = 'victim-vpr-0002'


def _env() -> dict[str, str]:
    env = seeding.table_env()
    env['VPR_RESULTS_BUCKET_NAME'] = VPR_BUCKET
    env['S3_BUCKET_NAME'] = VPR_BUCKET
    return env


def _run(*, seed_job_row: bool, requesting_user: str) -> tuple[int, str]:
    with mock_aws():
        ddb = boto3.resource('dynamodb', region_name='us-east-1')
        seeding.create_all_tables(ddb)
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket=VPR_BUCKET)
        s3.put_object(
            Bucket=VPR_BUCKET,
            Key=f'results/{VPR_ID}.json',
            Body=json.dumps(
                {
                    'application_id': VPR_ID,
                    'userId': VICTIM,  # real stored shape: VPR.user_id via camelCase alias
                    'executive_summary': f'{VPR_SECRET} — confidential victim VPR.',
                    'overall_fit_score': 91,
                }
            ).encode(),
        )

        with seeding.patched_env(_env()):
            seeding.seed_user_profile(VICTIM)
            seeding.seed_user_profile(ATTACKER)

            if seed_job_row:
                ddb.Table(seeding.JOBS_TABLE).put_item(
                    Item={
                        'job_id': VPR_ID,
                        'user_id': VICTIM,
                        'status': 'COMPLETED',
                        'created_at': '2026-09-01T00:00:00Z',
                    }
                )

            module = importlib.import_module('careervp.handlers.vpr_status_handler')
            reset = getattr(module, '_reset_handler_caches', None)
            if callable(reset):
                reset()

            event = seeding.authed_event(
                path=f'/vpr/{VPR_ID}/status',
                method='GET',
                claims_sub=requesting_user,
                path_params={'vprId': VPR_ID},
            )
            response = module.lambda_handler(event, seeding.lambda_context())
            if callable(reset):
                reset()

    return response.get('statusCode'), (response.get('body') or '')


def test_control_job_row_present_denies_attacker():
    """Load-bearing control: with the job row present, a different user is denied.

    Confirms the ordinary ownership check still works — otherwise a broken
    fallback fix could hide behind a broken primary check too.
    """
    status, _ = _run(seed_job_row=True, requesting_user=ATTACKER)
    assert status == 403


def test_job_row_absent_denies_attacker_via_s3_fallback():
    """The fix: job row absent (TTL/transient-error), S3 result present,
    requested by someone other than its owner — must not leak."""
    status, body = _run(seed_job_row=False, requesting_user=ATTACKER)
    assert status == 404
    assert VPR_SECRET not in body
    assert 'download_url' not in body


def test_job_row_absent_allows_rightful_owner_via_s3_fallback():
    """Owner-positive control: the fallback must still serve the real owner —
    a denial test alone doesn't prove the fix didn't just break the fallback
    for everyone (P1 Pass B: the original export/gap fixtures returned 404/
    empty for the rightful owner too, so "the attacker got nothing" proved
    nothing)."""
    status, body = _run(seed_job_row=False, requesting_user=VICTIM)
    assert status == 200
    assert VPR_SECRET in body
    assert 'download_url' in body
