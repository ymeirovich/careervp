"""RED contracts for D-H4/P-01 canonical artifact routing.

Covers AC-DH4-1, AC-P01-1, and AC-DH4-2 only.

Out of scope: ``company_research_store._legacy_table_name`` and the inner
``_legacy_read_cover_letter_by_scan`` query fallback (3.5);
``dynamo_dal_handler`` internal key construction (a later wave); all ``infra``
work and the D-M god-class/GSI split (3.4); request-path Scans (3.3);
auth/trial/user-pool keying (Wave-6 D-H8); and F-04 closure (Wave 4).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from importlib import import_module
from typing import Any, cast
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws
from pydantic import ValidationError

from careervp.dal.application_repository import ApplicationRepository
from careervp.dal.core_repository import CoreRepository
from careervp.logic.artifact_dependency_resolver import DependencyResolution
from careervp.models.api_models import CVTailoringRequest
from careervp.models.cv import UserCV
from careervp.models.result import Result, ResultCode

USER_ID = 'user-a'
APPLICATION_ID = 'job-001'
STALE_VPR_ID = 'vpr-stale-001'
CROSS_TENANT_VPR_ID = 'vpr-user-b-001'
OWNED_VPR_ID = 'vpr-user-a-001'
DENIAL_ENVELOPE = {
    'error': 'VPR is not available for this application',
    'classification': 'access_denied',
    'error_code': 'forbidden',
    'field': 'vpr_id',
}


class _FailSecondUpdateTable:
    """Delegate to a moto table except for the pinned step-2 write failure."""

    def __init__(self, table: Any) -> None:
        self._table = table
        self._update_count = 0

    def update_item(self, **kwargs: Any) -> dict[str, Any]:
        self._update_count += 1
        if self._update_count == 2:
            raise RuntimeError('forced step-2 artifact_id write failure')
        return self._table.update_item(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._table, name)


def _api_event(path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        'httpMethod': 'GET' if body is None else 'POST',
        'path': path,
        'pathParameters': {'application_id': APPLICATION_ID} if body is None else None,
        'requestContext': {
            'authorizer': {
                'claims': {'sub': USER_ID},
                'jwt': {'claims': {'sub': USER_ID}},
            },
            'requestId': 'request-001',
        },
        'headers': {'Content-Type': 'application/json'},
        'body': None if body is None else json.dumps(body),
    }


def _cover_letter_payload(vpr_id: str) -> dict[str, Any]:
    return {
        'cv_id': 'cv-001',
        'job_id': APPLICATION_ID,
        'application_id': APPLICATION_ID,
        'vpr_id': vpr_id,
        'gap_response_ids': ['gap-001'],
        'company_research_id': 'cr-001',
    }


def _interview_prep_payload(
    vpr_id: str,
    *,
    application_id: str | None = APPLICATION_ID,
    job_id: str | None = APPLICATION_ID,
) -> dict[str, Any]:
    return {
        'vpr_id': vpr_id,
        'gap_response_ids': ['gap-001'],
        'focus_areas': ['system design'],
        'question_count': 5,
        'application_id': application_id,
        'job_id': job_id,
    }


def _owned_cv() -> UserCV:
    return UserCV.model_validate(
        {
            'user_id': USER_ID,
            'cv_id': 'cv-001',
            'full_name': 'User A',
            'email': 'user-a@example.com',
            'professional_summary': 'Platform engineer.',
        }
    )


def _require_core_method(method_name: str, acceptance_criterion: str) -> Callable[..., Any]:
    repository = CoreRepository(dal=MagicMock())
    try:
        method = getattr(repository, method_name)
    except AttributeError:
        pytest.fail(f'{acceptance_criterion}: CoreRepository.{method_name} not available at careervp.dal.core_repository')
    if not callable(method):
        pytest.fail(f'{acceptance_criterion}: CoreRepository.{method_name} is not callable at careervp.dal.core_repository')
    return method


def test_dh4_status_endpoint_resolves_hub_artifact_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-DH4-1: the hub round-trips the same opaque canonical artifact_id."""
    from careervp.handlers import application_handler

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        applications_table = dynamodb.create_table(
            TableName='careervp-applications-table-test',
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
        artifacts_table = dynamodb.create_table(
            TableName='careervp-artifacts-table-test',
            KeySchema=[
                {'AttributeName': 'applicationId', 'KeyType': 'HASH'},
                {'AttributeName': 'artifactId', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'applicationId', 'AttributeType': 'S'},
                {'AttributeName': 'artifactId', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        applications_table.put_item(
            Item={
                'userId': USER_ID,
                'applicationId': APPLICATION_ID,
                'application_id': APPLICATION_ID,
                'user_id': USER_ID,
                'job_id': APPLICATION_ID,
                'state': 'artifacts_completed',
                'artifact_statuses': {'cover_letter': 'completed'},
            }
        )
        artifacts_table.put_item(
            Item={
                'applicationId': APPLICATION_ID,
                'artifactId': 'cl-001',
                'artifact_type': 'cover_letter',
                'user_id': USER_ID,
                'status': 'completed',
            }
        )

        failing_table = _FailSecondUpdateTable(applications_table)
        dal = MagicMock()
        dal.table_name = 'careervp-applications-table-test'
        dal._get_db_handler.return_value = failing_table
        repository = ApplicationRepository(dal=dal)
        update_artifact = cast(Callable[..., Any], repository.update_artifact_with_id)
        update_result = update_artifact(
            application_id=APPLICATION_ID,
            user_id=USER_ID,
            artifact_type='cover_letter',
            status='completed',
            artifact_id='cl-001',
        )

        monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'careervp-artifacts-table-test')
        with (
            patch.object(application_handler, '_get_application_repository', return_value=repository),
            patch.object(application_handler, '_get_jobs_repository') as jobs_repository,
        ):
            jobs_repository.return_value.get_job.return_value = None
            response = application_handler.lambda_handler(
                _api_event(f'/applications/{APPLICATION_ID}'),
                MagicMock(),
            )

    body = json.loads(response['body'])
    assert response['statusCode'] == 200
    assert body['artifacts']['cover_letter'] == {
        'status': 'completed',
        'artifact_id': 'cl-001',
    }
    assert isinstance(update_result, Result)
    assert update_result.success is False
    assert update_result.data is None
    assert update_result.code == ResultCode.DYNAMODB_ERROR

    resolver_module = import_module('careervp.logic.artifact_dependency_resolver')
    try:
        resolve_artifact_id = resolver_module.resolve_artifact_id
    except AttributeError:
        pytest.fail('AC-DH4-1: resolve_artifact_id not available at careervp.logic.artifact_dependency_resolver')
    assert resolve_artifact_id({'artifact_id': 'cl-001'}) == 'cl-001'
    for removed_name in ('artifactId', 'vpr_id', 'company_research_id', 'job_id', 'id'):
        assert resolve_artifact_id({removed_name: 'cl-001'}) is None


def test_p01_cover_letter_uses_resolved_vpr_not_client_key() -> None:
    """AC-P01-1: cover-letter VPR resolution never reads arbitrary client keys."""
    from careervp.handlers import cover_letter_handler

    dal = MagicMock()
    dal.table_name = 'careervp-artifacts-table-test'
    dal.get_cv.return_value = _owned_cv()
    dal.get_gap_responses.return_value = Result(success=True, data=[], code=ResultCode.SUCCESS)

    def get_vpr(client_vpr_id: str) -> Result[dict[str, str] | None]:
        if client_vpr_id == CROSS_TENANT_VPR_ID:
            return Result(
                success=True,
                data={'user_id': 'user-b', 'vpr_id': CROSS_TENANT_VPR_ID},
                code=ResultCode.SUCCESS,
            )
        return Result(success=True, data=None, code=ResultCode.SUCCESS)

    dal.get_vpr.side_effect = get_vpr
    jobs_repository = MagicMock()
    jobs_repository.get_job.return_value = {
        'job_id': APPLICATION_ID,
        'user_id': USER_ID,
        'company_name': 'Example Co',
        'title': 'Platform Engineer',
        'description': 'Build reliable distributed systems.',
    }

    responses: list[tuple[int, dict[str, Any]]] = []
    with (
        patch.object(cover_letter_handler, '_get_dal', return_value=dal),
        patch.object(cover_letter_handler, 'JobsRepository', return_value=jobs_repository),
        patch.object(
            cover_letter_handler,
            'resolve_handler_dependencies',
            return_value=DependencyResolution(status='ready'),
        ),
    ):
        for client_vpr_id in (STALE_VPR_ID, CROSS_TENANT_VPR_ID):
            response = cover_letter_handler.lambda_handler(
                _api_event('/cover-letter/generate', _cover_letter_payload(client_vpr_id)),
                MagicMock(),
            )
            responses.append((response['statusCode'], json.loads(response['body'])))

    assert dal.get_vpr.call_args_list == []
    assert responses == [
        (403, DENIAL_ENVELOPE),
        (403, DENIAL_ENVELOPE),
    ]
    _require_core_method('get_vpr_by_artifact_id', 'AC-P01-1')


def test_p01_interview_prep_uses_resolved_vpr_not_client_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-P01-1: interview-prep ownership refusal is terminal and identical."""
    from careervp.handlers import interview_prep_handler, interview_prep_submit_handler

    monkeypatch.setenv('VPR_JOBS_TABLE_NAME', 'careervp-vpr-jobs-table-test')
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'careervp-artifacts-table-test')
    dal = MagicMock()
    dal.table_name = 'careervp-artifacts-table-test'
    dal.get_cv.return_value = None
    dal.get_gap_responses.return_value = Result(success=True, data=[], code=ResultCode.SUCCESS)

    def get_vpr(client_vpr_id: str) -> Result[dict[str, str] | None]:
        if client_vpr_id == CROSS_TENANT_VPR_ID:
            return Result(
                success=True,
                data={'user_id': 'user-b', 'vpr_id': CROSS_TENANT_VPR_ID},
                code=ResultCode.SUCCESS,
            )
        return Result(success=True, data=None, code=ResultCode.SUCCESS)

    dal.get_vpr.side_effect = get_vpr
    jobs_repository = MagicMock()

    def get_job(client_vpr_id: str) -> dict[str, str] | None:
        if client_vpr_id == CROSS_TENANT_VPR_ID:
            return {
                'job_id': CROSS_TENANT_VPR_ID,
                'application_id': APPLICATION_ID,
                'user_id': 'user-b',
            }
        return None

    jobs_repository.get_job.side_effect = get_job

    responses: list[tuple[int, dict[str, Any]]] = []
    with (
        patch.object(interview_prep_handler, '_get_dal', return_value=dal),
        patch.object(interview_prep_handler, 'JobsRepository', return_value=jobs_repository),
    ):
        for client_vpr_id in (STALE_VPR_ID, CROSS_TENANT_VPR_ID):
            response = interview_prep_handler.lambda_handler(
                _api_event(
                    '/interview-prep/generate',
                    _interview_prep_payload(client_vpr_id),
                ),
                MagicMock(),
            )
            responses.append((response['statusCode'], json.loads(response['body'])))

    assert dal.get_vpr.call_args_list == []
    assert responses == [
        (403, DENIAL_ENVELOPE),
        (403, DENIAL_ENVELOPE),
    ]

    dependency_resolution = DependencyResolution(
        status='upstream_required',
        requested_artifact='interview_prep',
        missing=['vpr'],
        http_status=409,
    )
    with (
        patch.object(interview_prep_submit_handler, '_get_artifacts_table_name', return_value='careervp-artifacts-table-test'),
        patch.object(interview_prep_submit_handler, 'DynamoDalHandler', return_value=MagicMock()),
        patch.object(
            interview_prep_submit_handler,
            'resolve_handler_dependencies',
            return_value=dependency_resolution,
        ) as dependency_resolver,
    ):
        interview_prep_submit_handler.lambda_handler(
            _api_event(
                '/interview-prep/generate',
                _interview_prep_payload(
                    OWNED_VPR_ID,
                    application_id=None,
                    job_id=APPLICATION_ID,
                ),
            ),
            MagicMock(),
        )
        assert dependency_resolver.call_args.kwargs['application_id'] == APPLICATION_ID

        dependency_resolver.reset_mock()
        missing_ids_response = interview_prep_submit_handler.lambda_handler(
            _api_event(
                '/interview-prep/generate',
                _interview_prep_payload(
                    OWNED_VPR_ID,
                    application_id=None,
                    job_id=None,
                ),
            ),
            MagicMock(),
        )

    assert missing_ids_response['statusCode'] == 400
    assert json.loads(missing_ids_response['body']) == {
        'error': 'application_id/job_id is required',
        'status_code': 400,
        'code': ResultCode.MISSING_REQUIRED_FIELD,
    }
    dependency_resolver.assert_not_called()
    _require_core_method('get_interview_prep_by_artifact_id', 'AC-P01-1')


def test_dh4_cv_tailoring_preserves_vpr_id_null() -> None:
    """AC-DH4-2 behavior-changing RED: handler omission bypass remains unfixed.

    This is not a regression guard: B-3-6 settled TRUE at the handler boundary
    even though the model layer already distinguishes present-null from omitted.
    The overlap with F-04 remains flagged for human review and does not close it.
    """
    from careervp.handlers import cv_tailoring_handler

    present_null_payload = {
        'cv_id': 'cv-001',
        'job_id': APPLICATION_ID,
        'vpr_id': None,
    }
    omitted_payload = {
        'cv_id': 'cv-001',
        'job_id': APPLICATION_ID,
    }

    validated = CVTailoringRequest.model_validate(present_null_payload)
    assert validated.vpr_id is None
    with pytest.raises(ValidationError) as validation_error:
        CVTailoringRequest.model_validate(omitted_payload)
    errors = validation_error.value.errors()
    assert len(errors) == 1
    assert errors[0]['loc'] == ('vpr_id',)
    assert errors[0]['type'] == 'missing'

    accepted_response = {
        'statusCode': 202,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'status': 'processing'}),
    }
    with patch.object(
        cv_tailoring_handler,
        '_handle_openapi_async_generate',
        return_value=accepted_response,
    ) as downstream:
        present_null_response = cv_tailoring_handler.lambda_handler(
            _api_event('/cv-tailoring', present_null_payload),
            MagicMock(),
        )
        assert present_null_response['statusCode'] == 202
        downstream.assert_called_once()

        downstream.reset_mock()
        omitted_response = cv_tailoring_handler.lambda_handler(
            _api_event('/cv-tailoring', omitted_payload),
            MagicMock(),
        )

    omitted_body = json.loads(omitted_response['body'])
    assert omitted_response['statusCode'] == 400
    assert omitted_body['success'] is False
    assert omitted_body['code'] == ResultCode.VALIDATION_ERROR
    assert 'vpr_id' in omitted_body['message']
    assert 'Field required' in omitted_body['message']
    downstream.assert_not_called()
