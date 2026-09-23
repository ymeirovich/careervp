"""F-DEVX-1 — canonical VPR artifact write/read (3.CORR).

A completed VPR was written to the legacy users table under ``pk``/``sk`` while
cover-letter and interview-prep read the canonical artifacts table keyed
``applicationId``/``artifactId``. The resulting ``ValidationException`` was
converted to a false "missing upstream" and surfaced as HTTP 409.

These tests pin the corrected contract:

* the VPR worker writes ONE canonical artifact and no legacy VPR item;
* the canonical write is the completion boundary for both the job and the hub;
* one opaque id is shared by job, hub and canonical artifact;
* the repository returns the real VPR payload, never a jobs-table id stub;
* a key-schema failure propagates as ``TABLE_SCHEMA_MISMATCH`` and never as a
  missing dependency.
"""

from __future__ import annotations

from typing import Any, Generator
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from careervp.dal.core_repository import CoreRepository
from careervp.dal.jobs_repository import JobsRepository
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import VPR, VPRResponse

USERS_TABLE = 'careervp-users-table-test'
ARTIFACTS_TABLE = 'careervp-artifacts-table-test'
APPLICATIONS_TABLE = 'careervp-applications-table-test'
JOBS_TABLE = 'careervp-jobs-table-test'
RESULTS_BUCKET = 'careervp-vpr-results-test'

JOB_ID = 'a1b2c3d4-0000-4000-8000-000000000001'
APP_ID = 'ffffffff-0000-4000-8000-0000000000aa'
USER_ID = 'user-owner-1'
OTHER_USER_ID = 'user-intruder-2'


# ---------------------------------------------------------------------------
# Fixtures — real key schemas, not simplified stand-ins
# ---------------------------------------------------------------------------


@pytest.fixture
def aws_tables(monkeypatch: pytest.MonkeyPatch) -> Generator[dict[str, Any], None, None]:
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', USERS_TABLE)
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', ARTIFACTS_TABLE)
    monkeypatch.setenv('APPLICATIONS_TABLE_NAME', APPLICATIONS_TABLE)
    monkeypatch.setenv('JOBS_TABLE_NAME', JOBS_TABLE)
    monkeypatch.setenv('VPR_JOBS_TABLE_NAME', JOBS_TABLE)
    monkeypatch.setenv('VPR_RESULTS_BUCKET_NAME', RESULTS_BUCKET)

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        users = dynamodb.create_table(
            TableName=USERS_TABLE,
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            AttributeDefinitions=[{'AttributeName': 'pk', 'AttributeType': 'S'}, {'AttributeName': 'sk', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        artifacts = dynamodb.create_table(
            TableName=ARTIFACTS_TABLE,
            KeySchema=[
                {'AttributeName': 'applicationId', 'KeyType': 'HASH'},
                {'AttributeName': 'artifactId', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'applicationId', 'AttributeType': 'S'},
                {'AttributeName': 'artifactId', 'AttributeType': 'S'},
                {'AttributeName': 'artifactType', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'type-index',
                    'KeySchema': [
                        {'AttributeName': 'applicationId', 'KeyType': 'HASH'},
                        {'AttributeName': 'artifactType', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        applications = dynamodb.create_table(
            TableName=APPLICATIONS_TABLE,
            KeySchema=[
                {'AttributeName': 'userId', 'KeyType': 'HASH'},
                {'AttributeName': 'applicationId', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'applicationId', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        jobs = dynamodb.create_table(
            TableName=JOBS_TABLE,
            KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        for table in (users, artifacts, applications, jobs):
            table.wait_until_exists()

        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket=RESULTS_BUCKET)

        yield {'users': users, 'artifacts': artifacts, 'applications': applications, 'jobs': jobs}


@pytest.fixture
def canonical_vpr(minimal_vpr: VPR) -> VPR:
    """The shared valid 10-section VPR, re-owned onto this test's application."""
    return minimal_vpr.model_copy(update={'application_id': APP_ID, 'user_id': USER_ID})


def _completed_job_without_inline_result() -> dict[str, Any]:
    """A live-shaped COMPLETED job: result_key/result_url, NO inline result."""
    return {
        'job_id': JOB_ID,
        'application_id': APP_ID,
        'user_id': USER_ID,
        'status': 'COMPLETED',
        'result_key': f'results/{JOB_ID}.json',
        'result_url': 'https://example-bucket.s3.amazonaws.com/results/x.json?X-Amz-Signature=deadbeef',
        'vpr_version': 1,
        'word_count': 640,
        'created_at': '2026-08-01T09:00:00+00:00',
        'completed_at': '2026-08-01T09:05:00+00:00',
    }


def _seed_canonical_vpr(
    artifacts_table: Any,
    vpr: VPR,
    *,
    user_id: str = USER_ID,
    artifact_id: str = JOB_ID,
    version: int = 1,
    timestamp: str = '2026-08-01T09:05:00+00:00',
) -> None:
    artifacts_table.put_item(
        Item={
            'applicationId': APP_ID,
            'artifactId': artifact_id,
            'artifact_id': artifact_id,
            'artifactType': 'vpr',
            'user_id': user_id,
            'status': 'completed',
            'version': version,
            'created_at': timestamp,
            'updated_at': timestamp,
            'vpr': vpr.model_copy(update={'user_id': user_id, 'version': version}).model_dump(mode='json'),
        }
    )


def _run_worker_job(vpr: VPR, job_overrides: dict[str, Any] | None = None) -> None:
    """Execute the VPR worker against moto with generation stubbed out."""
    from careervp.handlers import vpr_worker_handler

    job = {
        'job_id': JOB_ID,
        'user_id': USER_ID,
        'application_id': APP_ID,
        'status': 'PENDING',
        'input_data': {
            'user_id': USER_ID,
            'application_id': APP_ID,
            'job_id': JOB_ID,
            'job_posting': {
                'company_name': 'Acme Corp',
                'role_title': 'Staff Backend Engineer',
                'responsibilities': ['Own the payments platform'],
                'requirements': ['Python', 'DynamoDB'],
            },
        },
    }
    if job_overrides:
        job.update(job_overrides)

    jobs_repo = JobsRepository(table_name=JOBS_TABLE)
    jobs_repo.create_job(dict(job))

    generated = Result(
        success=True,
        data=VPRResponse(
            success=True,
            vpr=vpr.model_copy(update={'application_id': str(job['application_id'])}),
            generation_time_ms=1200,
        ),
        code=ResultCode.VPR_GENERATED,
    )
    with (
        patch.object(vpr_worker_handler, 'generate_vpr', return_value=generated),
        patch('careervp.dal.dynamo_dal_handler.DynamoDalHandler.get_cv', return_value=MagicMock()),
    ):
        vpr_worker_handler._execute_job(jobs_repo, job, str(job['job_id']), RESULTS_BUCKET, None)


def _run_worker_job_with_real_generator(vpr: VPR) -> None:
    """Execute the worker through the REAL generate_vpr, stubbing only the LLM pipeline.

    Needed for any assertion about persistence performed *inside* generate_vpr.
    """
    from careervp.handlers import vpr_worker_handler
    from careervp.logic import vpr_generator

    job = {
        'job_id': JOB_ID,
        'user_id': USER_ID,
        'application_id': APP_ID,
        'status': 'PENDING',
        'input_data': {
            'user_id': USER_ID,
            'application_id': APP_ID,
            'job_id': JOB_ID,
            'job_posting': {
                'company_name': 'Acme Corp',
                'role_title': 'Staff Backend Engineer',
                'responsibilities': ['Own the payments platform'],
                'requirements': ['Python', 'DynamoDB'],
            },
        },
    }
    jobs_repo = JobsRepository(table_name=JOBS_TABLE)
    jobs_repo.create_job(dict(job))

    pipeline = MagicMock()
    pipeline.run.return_value = Result(success=True, data=MagicMock(vpr=vpr), code=ResultCode.SUCCESS)
    pipeline.token_usage = None

    with (
        patch.object(vpr_generator, 'VPRSixStagePipeline', return_value=pipeline),
        patch('careervp.dal.dynamo_dal_handler.DynamoDalHandler.get_cv', return_value=MagicMock()),
    ):
        vpr_worker_handler._execute_job(jobs_repo, job, JOB_ID, RESULTS_BUCKET, None)


# ---------------------------------------------------------------------------
# 1. The worker writes the canonical artifact and nothing legacy
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_worker_writes_canonical_vpr_artifact_at_pinned_key(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-1: canonical item at applicationId/artifactId with type-index value 'vpr'."""
    _run_worker_job(canonical_vpr)

    item = aws_tables['artifacts'].get_item(Key={'applicationId': APP_ID, 'artifactId': JOB_ID}).get('Item')
    assert item is not None, 'AC-CORR-1: no canonical VPR artifact was written to the artifacts table'
    assert item['artifactType'] == 'vpr', 'AC-CORR-1: type-index value must be exactly "vpr"'
    assert item['artifact_id'] == JOB_ID, 'AC-CORR-1: logical artifact_id attribute must equal the artifactId key'
    assert item['user_id'] == USER_ID, 'AC-CORR-1: owner field must be user_id (live artifacts grammar)'
    assert 'created_at' in item and 'updated_at' in item, 'AC-CORR-1: snake_case timestamps are required'
    assert isinstance(item.get('vpr'), dict), 'AC-CORR-1: the full VPR payload must be stored in DynamoDB'
    assert item['vpr']['executive_summary']['fit_rationale'], 'AC-CORR-1: stored payload must carry real VPR content'


@pytest.mark.unit
def test_worker_writes_no_vpr_item_to_users_table(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-2: the legacy pk/sk VPR write path is gone, not merely shadowed.

    This runs the REAL ``generate_vpr`` (only the LLM pipeline is stubbed), because
    the legacy ``save_vpr`` call lives inside it — stubbing ``generate_vpr`` would
    make this assertion pass vacuously.
    """
    _run_worker_job_with_real_generator(canonical_vpr)

    items = aws_tables['users'].scan().get('Items', [])
    legacy = [item for item in items if str(item.get('sk', '')).startswith('ARTIFACT#VPR#')]
    assert legacy == [], f'AC-CORR-2: worker still wrote {len(legacy)} legacy VPR item(s) to the users table'


@pytest.mark.unit
def test_canonical_write_failure_blocks_job_and_hub_completion(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-3: no completed job or hub status may exist over a missing artifact."""
    from careervp.handlers import vpr_worker_handler

    failure = Result(success=False, data=None, error='forced canonical write failure', code=ResultCode.DYNAMODB_ERROR)
    with (
        patch.object(CoreRepository, 'save_vpr_artifact', return_value=failure),
        pytest.raises(RuntimeError),
    ):
        _run_worker_job(canonical_vpr)

    job = JobsRepository(table_name=JOBS_TABLE).get_job(JOB_ID) or {}
    assert job.get('status') != 'COMPLETED', 'AC-CORR-3: job reported COMPLETED without a canonical artifact'

    hub = aws_tables['applications'].get_item(Key={'userId': USER_ID, 'applicationId': APP_ID}).get('Item') or {}
    statuses = hub.get('artifact_statuses') or {}
    assert statuses.get('vpr') != 'completed', 'AC-CORR-3: hub reported vpr completed without a canonical artifact'
    assert 'vpr_artifact_id' not in statuses, 'AC-CORR-3: hub published an artifact id with no artifact behind it'
    _ = vpr_worker_handler  # imported for module identity in the patch above


@pytest.mark.unit
def test_hub_job_and_canonical_artifact_share_one_id(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-4: one opaque id across jobs, hub and canonical artifact."""
    _run_worker_job(canonical_vpr)

    hub = aws_tables['applications'].get_item(Key={'userId': USER_ID, 'applicationId': APP_ID}).get('Item') or {}
    statuses = hub.get('artifact_statuses') or {}
    item = aws_tables['artifacts'].get_item(Key={'applicationId': APP_ID, 'artifactId': JOB_ID}).get('Item') or {}

    assert statuses.get('vpr_artifact_id') == JOB_ID, 'AC-CORR-4: hub vpr_artifact_id diverged from the job id'
    assert item.get('artifactId') == JOB_ID, 'AC-CORR-4: canonical artifactId diverged from the job id'
    assert statuses.get('vpr') == 'completed', 'AC-CORR-4: hub must report completed once the artifact exists'


@pytest.mark.unit
def test_empty_application_id_fails_before_any_persistence(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-5: no canonical partition key means fail the job, not write junk.

    An unusable job is terminal, not transient, so it takes the worker's existing
    bad-input path (mark FAILED, signal, return) rather than raising for retry.
    """
    _run_worker_job(canonical_vpr, {'application_id': ''})

    assert aws_tables['artifacts'].scan().get('Count', 0) == 0, 'AC-CORR-5: wrote an artifact with no applicationId'
    job = JobsRepository(table_name=JOBS_TABLE).get_job(JOB_ID) or {}
    assert job.get('status') == 'FAILED', f'AC-CORR-5: expected FAILED, got {job.get("status")!r}'


@pytest.mark.unit
def test_canonical_record_never_stores_presigned_result_url(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-6: a presigned URL is not a durable locator and must not be stored."""
    _run_worker_job(canonical_vpr)

    item = aws_tables['artifacts'].get_item(Key={'applicationId': APP_ID, 'artifactId': JOB_ID}).get('Item')
    assert item, 'AC-CORR-6: no canonical artifact was written, so this assertion would pass vacuously'
    flat = str(item)
    assert 'result_url' not in item, 'AC-CORR-6: canonical artifact stored result_url'
    assert 'X-Amz-Signature' not in flat, 'AC-CORR-6: canonical artifact embedded a signed URL'


# ---------------------------------------------------------------------------
# 2. The repository returns real payloads, never a jobs-table stub
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_repository_returns_real_payload_when_job_has_no_inline_result(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-7 (the stub test): jobs metadata must never masquerade as VPR content."""
    aws_tables['jobs'].put_item(Item=_completed_job_without_inline_result())
    _seed_canonical_vpr(aws_tables['artifacts'], canonical_vpr)

    repository = CoreRepository(vpr_jobs_repository=JobsRepository(table_name=JOBS_TABLE))
    result = repository.get_vpr_by_artifact_id(application_id=APP_ID, artifact_id=JOB_ID, user_id=USER_ID)

    assert result.success, f'AC-CORR-7: canonical read failed: {result.error}'
    payload = result.data
    assert isinstance(payload, dict), 'AC-CORR-7: expected a materialized VPR payload'
    assert set(payload) - {'artifact_id', 'application_id', 'user_id'}, 'AC-CORR-7: returned an id-only stub'
    assert payload.get('executive_summary'), 'AC-CORR-7: real VPR sections missing from resolved payload'
    assert payload['executive_summary'].get('fit_rationale'), 'AC-CORR-7: resolved payload carried no VPR narrative'


@pytest.mark.unit
def test_repository_returns_none_when_only_a_job_exists(aws_tables: dict[str, Any]) -> None:
    """AC-CORR-8: with no canonical artifact the answer is a successful None, not a stub."""
    aws_tables['jobs'].put_item(Item=_completed_job_without_inline_result())

    repository = CoreRepository(vpr_jobs_repository=JobsRepository(table_name=JOBS_TABLE))
    result = repository.get_vpr_by_artifact_id(application_id=APP_ID, artifact_id=JOB_ID, user_id=USER_ID)

    assert result.success, 'AC-CORR-8: genuine absence must be a successful result'
    assert result.data is None, f'AC-CORR-8: fabricated a VPR from jobs metadata: {result.data!r}'
    assert result.code == ResultCode.SUCCESS


@pytest.mark.unit
def test_repository_never_falls_back_to_legacy_users_table(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-9: a legacy users-table VPR is not an acceptable answer."""
    aws_tables['users'].put_item(
        Item={
            'pk': APP_ID,
            'sk': 'ARTIFACT#VPR#v1',
            'user_id': USER_ID,
            **canonical_vpr.model_dump(mode='json'),
        }
    )

    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    repository = CoreRepository(dal=DynamoDalHandler(ARTIFACTS_TABLE))
    result = repository.get_vpr_by_artifact_id(application_id=APP_ID, artifact_id=JOB_ID, user_id=USER_ID)

    assert result.success, 'AC-CORR-9: absence of a canonical artifact is not an error'
    assert result.data is None, 'AC-CORR-9: repository served a legacy users-table VPR as canonical'


@pytest.mark.unit
def test_vpr_resolves_when_caller_supplies_no_artifact_id(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-18: the cover-letter SQS worker never supplies a VPR artifact id.

    ``_generate_and_persist_from_sqs`` calls ``_generate_cover_letter_result`` without
    ``vpr_artifact_id``, so ``_resolve_cover_letter_context`` passes the APPLICATION id
    as the artifact id. That only ever resolved because the removed legacy fallback
    looked VPRs up by application_id and ignored the artifact id. The resolution must
    now find the canonical artifact by owner + application instead.
    """
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler
    from careervp.handlers.cover_letter_handler import _resolve_vpr_payload

    _seed_canonical_vpr(aws_tables['artifacts'], canonical_vpr)

    payload = _resolve_vpr_payload(
        dal=DynamoDalHandler(ARTIFACTS_TABLE),
        application_id=APP_ID,
        artifact_id=APP_ID,  # the application id standing in for a missing artifact id
        user_id=USER_ID,
    )

    dumped = payload.model_dump(mode='json')
    assert dumped.get('executive_summary'), 'AC-CORR-18: resolved VPR carried no real content'
    assert dumped.get('artifact_id') == JOB_ID, 'AC-CORR-18: resolution did not find the canonical artifact id'


@pytest.mark.unit
def test_materialized_vpr_payload_is_json_serializable(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-19: DynamoDB returns numbers as Decimal; prompts are built with json.dumps.

    The legacy path returned a validated pydantic model, which coerced Decimal away.
    Reading the canonical item returns raw DynamoDB types, so the repository must
    normalise them or every generator fails with
    "Object of type Decimal is not JSON serializable".
    """
    import json
    from decimal import Decimal

    _seed_canonical_vpr(aws_tables['artifacts'], canonical_vpr)

    repository = CoreRepository(vpr_jobs_repository=JobsRepository(table_name=JOBS_TABLE))
    result = repository.get_vpr_by_artifact_id(application_id=APP_ID, artifact_id=JOB_ID, user_id=USER_ID)
    assert result.success and isinstance(result.data, dict)

    def _find_decimal(node: Any, path: str = 'vpr') -> str | None:
        if isinstance(node, Decimal):
            return path
        if isinstance(node, dict):
            return next((found for k, v in node.items() if (found := _find_decimal(v, f'{path}.{k}'))), None)
        if isinstance(node, list):
            return next((found for i, v in enumerate(node) if (found := _find_decimal(v, f'{path}[{i}]'))), None)
        return None

    leftover = _find_decimal(result.data)
    assert leftover is None, f'AC-CORR-19: Decimal survived materialization at {leftover}'
    json.dumps(result.data)  # the generators do exactly this to build the prompt


@pytest.mark.unit
def test_wrong_owner_receives_forbidden(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-10: cross-tenant reads are denied, not reported as missing."""
    _seed_canonical_vpr(aws_tables['artifacts'], canonical_vpr, user_id=USER_ID)

    repository = CoreRepository(vpr_jobs_repository=JobsRepository(table_name=JOBS_TABLE))
    result = repository.get_vpr_by_artifact_id(application_id=APP_ID, artifact_id=JOB_ID, user_id=OTHER_USER_ID)

    assert not result.success, 'AC-CORR-10: wrong owner must not succeed'
    assert result.code == ResultCode.FORBIDDEN, f'AC-CORR-10: expected FORBIDDEN, got {result.code}'
    assert result.data is None


# ---------------------------------------------------------------------------
# 3. Schema failures are infrastructure failures, never missing dependencies
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_vpr_dal_maps_key_schema_validation_exception(aws_tables: dict[str, Any]) -> None:
    """AC-CORR-11: the live failure must classify as TABLE_SCHEMA_MISMATCH."""
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    schema_error = ClientError(
        {'Error': {'Code': 'ValidationException', 'Message': 'Query condition missed key schema element: applicationId'}},
        'Query',
    )
    handler = DynamoDalHandler(ARTIFACTS_TABLE)
    table = MagicMock()
    table.query.side_effect = schema_error
    with patch.object(DynamoDalHandler, '_get_db_handler', return_value=table):
        result = handler.get_latest_vpr(APP_ID)

    assert not result.success
    assert result.code == ResultCode.TABLE_SCHEMA_MISMATCH, f'AC-CORR-11: got {result.code}, not TABLE_SCHEMA_MISMATCH'


@pytest.mark.unit
def test_dependency_adapter_raises_instead_of_reporting_missing(aws_tables: dict[str, Any]) -> None:
    """AC-CORR-12: the adapter must not convert an infrastructure failure to None."""
    from careervp.handlers.artifact_dependency_utils import DynamoArtifactDependencyRepos
    from careervp.logic.artifact_dependency_resolver import ArtifactUnavailableError

    failure = Result(success=False, data=None, error='schema mismatch', code=ResultCode.TABLE_SCHEMA_MISMATCH)
    repos = DynamoArtifactDependencyRepos(dal=MagicMock(), application_repo=None, user_id=USER_ID)
    with (
        patch.object(CoreRepository, 'get_vpr_by_artifact_id', return_value=failure),
        patch.object(CoreRepository, 'resolve_artifact_id', return_value=Result(success=True, data=JOB_ID, code=ResultCode.SUCCESS)),
    ):
        with pytest.raises(ArtifactUnavailableError) as excinfo:
            repos.get_artifact('vpr', APP_ID)

    assert excinfo.value.code == ResultCode.TABLE_SCHEMA_MISMATCH


@pytest.mark.unit
def test_schema_failure_surfaces_503_not_409(aws_tables: dict[str, Any]) -> None:
    """AC-CORR-13: the submit handler answers 503; 409 upstream_required is forbidden here."""
    import json

    from careervp.handlers import interview_prep_submit_handler
    from careervp.logic.artifact_dependency_resolver import ArtifactUnavailableError

    event = {
        'body': json.dumps(
            {
                'application_id': APP_ID,
                'job_id': APP_ID,
                'vpr_id': JOB_ID,
                'gap_response_ids': ['q1'],
                'question_count': 10,
            }
        ),
        'requestContext': {'authorizer': {'claims': {'sub': USER_ID}}},
    }
    with patch.object(
        interview_prep_submit_handler,
        'resolve_handler_dependencies',
        side_effect=ArtifactUnavailableError('vpr', ResultCode.TABLE_SCHEMA_MISMATCH, 'schema mismatch'),
    ):
        response = interview_prep_submit_handler.lambda_handler(event, MagicMock())

    assert response['statusCode'] == 503, f'AC-CORR-13: expected 503, got {response["statusCode"]}'
    body = json.loads(response['body'])
    assert body.get('status') != 'upstream_required', 'AC-CORR-13: schema failure reported as a missing upstream'
    assert 'vpr' not in (body.get('missing') or []), 'AC-CORR-13: schema failure listed vpr as missing'


# ---------------------------------------------------------------------------
# 4. Downstream resolution over the canonical artifact
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_resolver_accepts_canonical_vpr_as_ready(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-14: an owned canonical VPR resolves ready for interview prep."""
    from careervp.handlers.artifact_dependency_utils import resolve_handler_dependencies

    _seed_canonical_vpr(aws_tables['artifacts'], canonical_vpr)
    aws_tables['applications'].put_item(
        Item={
            'userId': USER_ID,
            'applicationId': APP_ID,
            'artifact_statuses': {'vpr': 'completed', 'vpr_artifact_id': JOB_ID},
            'state': 'vpr_completed',
        }
    )

    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    resolution = resolve_handler_dependencies(
        artifact_type='interview_prep',
        application_id=APP_ID,
        user_id=USER_ID,
        dal=DynamoDalHandler(ARTIFACTS_TABLE),
    )

    assert resolution.status == 'ready', f'AC-CORR-14: expected ready, got {resolution.status} missing={resolution.missing}'
    assert 'vpr' in resolution.resolved_upstream
    assert resolution.resolved_upstream['vpr'].artifact_id == JOB_ID, 'AC-CORR-14: resolver lost the canonical artifact id'


@pytest.mark.unit
def test_resolver_reports_missing_when_no_canonical_vpr(aws_tables: dict[str, Any]) -> None:
    """AC-CORR-15: genuine absence still produces the ordinary upstream_required path."""
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler
    from careervp.handlers.artifact_dependency_utils import resolve_handler_dependencies

    resolution = resolve_handler_dependencies(
        artifact_type='interview_prep',
        application_id=APP_ID,
        user_id=USER_ID,
        dal=DynamoDalHandler(ARTIFACTS_TABLE),
    )

    assert resolution.status == 'upstream_required'
    assert resolution.missing == ['vpr']
    assert resolution.http_status == 409


@pytest.mark.unit
def test_canonical_version_allocation_is_read_from_the_artifacts_table(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-16: version authority moves to the canonical table, not the users table."""
    repository = CoreRepository()
    assert repository.next_vpr_version(APP_ID) == 1, 'AC-CORR-16: first VPR must be version 1'

    _seed_canonical_vpr(aws_tables['artifacts'], canonical_vpr)
    assert repository.next_vpr_version(APP_ID) == 2, 'AC-CORR-16: version must advance past the canonical maximum'


@pytest.mark.unit
def test_latest_canonical_vpr_selected_deterministically(aws_tables: dict[str, Any], canonical_vpr: VPR) -> None:
    """AC-CORR-17: latest is max(version), not GSI response order."""
    _seed_canonical_vpr(aws_tables['artifacts'], canonical_vpr, artifact_id=JOB_ID)
    # Deliberately OLDER timestamps than v1: ordering by updated_at would pick the
    # wrong record, so this only passes if version is what decides.
    _seed_canonical_vpr(
        aws_tables['artifacts'],
        canonical_vpr,
        artifact_id='second-vpr-id',
        version=2,
        timestamp='2026-07-30T09:05:00+00:00',
    )

    repository = CoreRepository()
    resolved = repository.resolve_artifact_id(APP_ID, 'vpr', user_id=USER_ID)
    assert resolved.success
    assert resolved.data == 'second-vpr-id', 'AC-CORR-17: latest canonical VPR must be the highest version'
