"""Shared two-tenant seeding + event helpers for the P-05 cross-tenant IDOR tests.

Not a test file. Creates every DynamoDB table the covered handlers read from (with the exact key
schemas the handlers use), seeds a *real* victim record per resource family, and builds API-Gateway
proxy events. Used by both ``tests/integration/test_p05_cross_tenant_idor.py`` and the flat-envelope
test in ``tests/unit/test_p04_p05_auth_idor.py``.

Schemas verified against the working tree 2026-07-24:
- main table (TABLE_NAME / DYNAMODB_TABLE_NAME): pk / sk
- artifacts table (ARTIFACTS_TABLE_NAME): applicationId / artifactId
- applications table (APPLICATIONS_TABLE_NAME): userId / applicationId
- jobs table (JOBS_TABLE_NAME / VPR_JOBS_TABLE_NAME): job_id (+ GSIs user_id-index, entity_type-index)
"""

from __future__ import annotations

import contextlib
import os
import uuid
from typing import Any, Generator
from unittest.mock import MagicMock

import boto3

MAIN_TABLE = 'p05-main-table'
ARTIFACTS_TABLE = 'p05-artifacts-table'
APPLICATIONS_TABLE = 'p05-applications-table'
JOBS_TABLE = 'p05-jobs-table'

# Fields we plant on the victim record and then assert never leak to the attacker.
VICTIM_MARKERS = ('p05-victim-secret-title', 'victim-secret@example.invalid', 'Victim Secret Name')


def table_env() -> dict[str, str]:
    return {
        'TABLE_NAME': MAIN_TABLE,
        'DYNAMODB_TABLE_NAME': MAIN_TABLE,
        'USERS_TABLE_NAME': MAIN_TABLE,
        'KNOWLEDGE_TABLE_NAME': MAIN_TABLE,
        'GAP_QUESTIONS_TABLE_NAME': MAIN_TABLE,
        'GAP_RESPONSES_TABLE_NAME': MAIN_TABLE,
        'ARTIFACTS_TABLE_NAME': ARTIFACTS_TABLE,
        'APPLICATIONS_TABLE_NAME': APPLICATIONS_TABLE,
        'JOBS_TABLE_NAME': JOBS_TABLE,
        'VPR_JOBS_TABLE_NAME': JOBS_TABLE,
        'CVS_TABLE_NAME': MAIN_TABLE,
        'ENVIRONMENT': 'test',
        'POWERTOOLS_SERVICE_NAME': 'p05-idor-test',
        'POWERTOOLS_TRACE_DISABLED': 'true',
        'LOG_LEVEL': 'INFO',
        'AWS_DEFAULT_REGION': 'us-east-1',
        'AWS_ACCESS_KEY_ID': 'testing',
        'AWS_SECRET_ACCESS_KEY': 'testing',
        'AWS_SECURITY_TOKEN': 'testing',
        'AWS_SESSION_TOKEN': 'testing',
    }


@contextlib.contextmanager
def patched_env(env: dict[str, str]) -> Generator[None, None, None]:
    previous = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        yield
    finally:
        for key, old in previous.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def _pk_sk_table(ddb: Any, name: str, pk: str, sk: str) -> Any:
    return ddb.create_table(
        TableName=name,
        KeySchema=[{'AttributeName': pk, 'KeyType': 'HASH'}, {'AttributeName': sk, 'KeyType': 'RANGE'}],
        AttributeDefinitions=[
            {'AttributeName': pk, 'AttributeType': 'S'},
            {'AttributeName': sk, 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )


def create_all_tables(ddb: Any) -> None:
    _pk_sk_table(ddb, MAIN_TABLE, 'pk', 'sk')
    _pk_sk_table(ddb, ARTIFACTS_TABLE, 'applicationId', 'artifactId')
    _pk_sk_table(ddb, APPLICATIONS_TABLE, 'userId', 'applicationId')
    ddb.create_table(
        TableName=JOBS_TABLE,
        KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'job_id', 'AttributeType': 'S'},
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
            {'AttributeName': 'entity_type', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'user_id-index',
                'KeySchema': [{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
            {
                'IndexName': 'entity_type-index',
                'KeySchema': [{'AttributeName': 'entity_type', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    for name in (MAIN_TABLE, ARTIFACTS_TABLE, APPLICATIONS_TABLE, JOBS_TABLE):
        ddb.meta.client.get_waiter('table_exists').wait(TableName=name)


def _t(name: str) -> Any:
    return boto3.resource('dynamodb', region_name='us-east-1').Table(name)


# --------------------------------------------------------------------------------------------------
# Per-family seeders. Each seeds ONE victim-owned record and returns the id an attacker would target.
# --------------------------------------------------------------------------------------------------


def seed_user_profile(owner_user_id: str) -> str:
    _t(MAIN_TABLE).put_item(
        Item={
            'pk': f'USER#{owner_user_id}',
            'sk': 'PROFILE',
            'user_id': owner_user_id,
            'email': VICTIM_MARKERS[1],
            'name': VICTIM_MARKERS[2],
            'preferences': {},
        }
    )
    return owner_user_id


def seed_job(owner_user_id: str) -> str:
    job_id = f'job-{uuid.uuid4().hex[:10]}'
    _t(JOBS_TABLE).put_item(
        Item={
            'job_id': job_id,
            'user_id': owner_user_id,
            'entity_type': 'JOB',
            'title': VICTIM_MARKERS[0],
            'company_name': 'Victim Co',
            'status': 'PENDING',
            'created_at': '2026-07-24T00:00:00+00:00',
        }
    )
    return job_id


def seed_vpr_job(owner_user_id: str) -> str:
    # vpr_status_handler resolves the VPR by JobsRepository.get_job(vpr_id) then owner-checks.
    vpr_id = f'vpr-{uuid.uuid4().hex[:10]}'
    _t(JOBS_TABLE).put_item(
        Item={
            'job_id': vpr_id,
            'user_id': owner_user_id,
            'entity_type': 'VPR',
            'application_id': f'app-{vpr_id}',
            'status': 'COMPLETED',
            'title': VICTIM_MARKERS[0],
            'created_at': '2026-07-24T00:00:00+00:00',
        }
    )
    return vpr_id


def seed_application(owner_user_id: str) -> str:
    application_id = f'app-{uuid.uuid4().hex[:10]}'
    _t(APPLICATIONS_TABLE).put_item(
        Item={
            'userId': owner_user_id,
            'applicationId': application_id,
            'application_id': application_id,
            'user_id': owner_user_id,
            'status': 'ACTIVE',
            'title': VICTIM_MARKERS[0],
        }
    )
    return application_id


def _seed_artifact(owner_user_id: str, artifact_id: str) -> None:
    _t(ARTIFACTS_TABLE).put_item(
        Item={
            'applicationId': owner_user_id,
            'artifactId': artifact_id,
            'user_id': owner_user_id,
            'status': 'completed',
            'title': VICTIM_MARKERS[0],
            'email': VICTIM_MARKERS[1],
        }
    )


def seed_cv_tailoring(owner_user_id: str) -> str:
    # cv_tailoring_handler._get_tailored_cv_item reads the MAIN table with pk=user_id,
    # sk=ARTIFACT#CV_TAILORED#{request_id} (NOT the artifacts table).
    request_id = f'cvt-{uuid.uuid4().hex[:10]}'
    _t(MAIN_TABLE).put_item(
        Item={
            'pk': owner_user_id,
            'sk': f'ARTIFACT#CV_TAILORED#{request_id}',
            'request_id': request_id,
            'user_id': owner_user_id,
            'status': 'completed',
            'title': VICTIM_MARKERS[0],
        }
    )
    return request_id


def seed_cover_letter(owner_user_id: str) -> str:
    cover_letter_id = f'cl-{uuid.uuid4().hex[:10]}'
    _seed_artifact(owner_user_id, f'ARTIFACT#COVER_LETTER#{cover_letter_id}')
    return cover_letter_id


def seed_interview_prep(owner_user_id: str) -> str:
    interview_prep_id = f'ip-{uuid.uuid4().hex[:10]}'
    _seed_artifact(owner_user_id, f'ARTIFACT#INTERVIEW_PREP#{interview_prep_id}')
    return interview_prep_id


def seed_company_research(owner_user_id: str) -> str:
    job_id = f'job-{uuid.uuid4().hex[:10]}'
    # company_research_handler reads pk=user_id, sk=ARTIFACT#COMPANY_RESEARCH#{job_id} (+ KB variants).
    _t(MAIN_TABLE).put_item(
        Item={
            'pk': owner_user_id,
            'sk': f'ARTIFACT#COMPANY_RESEARCH#{job_id}',
            'user_id': owner_user_id,
            'status': 'completed',
            'company_name': VICTIM_MARKERS[0],
        }
    )
    return job_id


def seed_export_artifact(owner_user_id: str) -> str:
    # export_handler reads the tailored-CV artifact by pk=user_id via begins_with(ARTIFACT#CV_TAILORED#).
    job_id = f'job-{uuid.uuid4().hex[:10]}'
    _seed_artifact(owner_user_id, f'ARTIFACT#CV_TAILORED#{job_id}')
    return job_id


def seed_gap_questions(owner_user_id: str) -> str:
    job_id = f'job-{uuid.uuid4().hex[:10]}'
    _t(MAIN_TABLE).put_item(
        Item={
            'pk': owner_user_id,
            'sk': f'ARTIFACT#GAP_ANALYSIS#{job_id}#q1',
            'user_id': owner_user_id,
            'job_id': job_id,
            'question': VICTIM_MARKERS[0],
        }
    )
    return job_id


# --------------------------------------------------------------------------------------------------
# Event / context helpers
# --------------------------------------------------------------------------------------------------


def _base_event(path: str, method: str, path_params: dict[str, str] | None) -> dict[str, Any]:
    return {
        'version': '1.0',
        'resource': path,
        'path': path,
        'httpMethod': method,
        'headers': {'Content-Type': 'application/json'},
        'multiValueHeaders': {},
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'pathParameters': path_params,
        'stageVariables': None,
        'body': None,
        'isBase64Encoded': False,
        'requestContext': {'httpMethod': method, 'path': path, 'stage': 'test', 'requestId': 'p05'},
    }


def forged_header_event(path: str, method: str, victim_user_id: str, path_params: dict[str, str] | None = None) -> dict[str, Any]:
    """The attack: NO Cognito authorizer claims, only a forged ``x-user-id`` header = the victim.

    This is exactly the shape auth_utils.extract_user_id trusts today via its header fallback.
    """
    event = _base_event(path, method, path_params)
    event['headers']['x-user-id'] = victim_user_id
    return event


def authed_event(path: str, method: str, claims_sub: str, path_params: dict[str, str] | None = None) -> dict[str, Any]:
    """A legitimately authenticated caller (Cognito claims), used to exercise the existing denial."""
    event = _base_event(path, method, path_params)
    event['requestContext']['authorizer'] = {'claims': {'sub': claims_sub}}
    return event


def lambda_context() -> Any:
    context = MagicMock()
    context.aws_request_id = 'p05-request-id'
    context.function_name = 'p05-handler'
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:p05-handler'
    return context
