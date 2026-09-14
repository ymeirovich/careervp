"""S0a proof: an AUTHENTICATED attacker (real Cognito claims, own identity) exports
another tenant's VPR via GET /jobs/{jobId}/artifacts/vpr/export.

This is the IDOR shape the shipped P-05 probe never tests: that probe uses
forged_header_event (no claims), so every case now 401s at the auth gate and the
ownership logic below is never reached.

Test 2 re-runs all 9 registered P-05 cases with a legitimately authenticated
attacker to measure how many actually enforce ownership.
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


def test_s0a_authenticated_attacker_exports_victim_vpr():
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
            body = json.loads(response.get('body') or '{}')
            print(f'\nS0a status={status}')
            print(f'S0a body keys={list(body)}')

            leaked_via_docx = False
            if 'download_url' in body:
                obj = s3.get_object(
                    Bucket=ARTIFACTS_BUCKET, Key=f'exports/vpr/{job_id}/{job_id}.docx'
                )
                with zipfile.ZipFile(BytesIO(obj['Body'].read())) as z:
                    doc_xml = z.read('word/document.xml').decode('utf-8', 'ignore')
                leaked_via_docx = VPR_SECRET in doc_xml
                print(f'S0a attacker received presigned URL: {body["download_url"][:80]}...')
                print(f'S0a victim secret present in exported DOCX: {leaked_via_docx}')

    assert status == 200 and leaked_via_docx, (
        f'Expected to demonstrate the leak; got status={status}, leaked={leaked_via_docx}'
    )
    print('S0a VERDICT: CONFIRMED — authenticated cross-tenant VPR export succeeded.')


@pytest.mark.parametrize('case', CASES, ids=[c.route_id for c in CASES])
def test_p05_cases_with_real_authenticated_attacker(case):
    """Re-run every registered P-05 case with an authenticated attacker instead of a
    forged header. Records which routes actually enforce ownership."""
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
            )
            if 'export' in case.path:
                event['queryStringParameters'] = {'format': 'docx'}

            response = handler(event, seeding.lambda_context())
            if callable(reset):
                reset()

    status = response.get('statusCode')
    raw_body = response.get('body') or ''
    leaked = [m for m in seeding.VICTIM_MARKERS if m in raw_body]
    denied = status in (401, 403, 404) and not leaked
    print(f'\n[{case.route_id}] authenticated-attacker status={status} leaked={leaked} denied={denied}')
    assert denied, f'[{case.route_id}] served cross-tenant data to an authenticated attacker: status={status}, leaked={leaked}'
