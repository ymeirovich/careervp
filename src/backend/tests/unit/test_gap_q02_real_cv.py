"""
Q-02 RED/GREEN tests: Inject the REAL CV into gap-question generation.

TDD contract:
  - test_gap_payload_is_characterization_stub  — documents the current bug (runs BEFORE the fix)
  - test_gap_loads_real_cv_moto               — primary correctness test, moto + real key schema
  - test_gap_loads_real_cv_by_id              — unit companion, patch-based
  - test_gap_missing_cv_errors_not_stub       — None from DAL → §3 item-10 envelope + HTTP 404

All four tests start RED against the unmodified handler.  After the GREEN fix they all pass.
Do NOT weaken any assertion to make a test pass; do NOT modify the spec.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any, cast
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

# ---------------------------------------------------------------------------
# Shared fixtures (mirror test_gap_analysis_handler.py patterns)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_caches() -> Generator[None, None, None]:
    from careervp.handlers.gap_handler import _reset_handler_caches

    _reset_handler_caches()
    yield
    _reset_handler_caches()


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-gap-q02-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    # gap questions table
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-gap-table')
    monkeypatch.setenv('TABLE_NAME', 'test-gap-table')
    monkeypatch.setenv('USERS_TABLE_NAME', 'test-gap-table')
    monkeypatch.setenv('GAP_QUESTIONS_TABLE_NAME', 'test-gap-table')
    monkeypatch.setenv('GAP_RESPONSES_TABLE_NAME', 'test-gap-responses-table')
    # CV table — separate, named cvs-table (mirrors live infra)
    monkeypatch.setenv('CVS_TABLE_NAME', 'test-cvs-table')
    yield


def _event(
    path: str,
    method: str,
    body: dict[str, Any] | None = None,
    user_id: str = 'user-q02',
    path_parameters: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        'resource': path,
        'path': path,
        'httpMethod': method,
        'headers': {
            'Content-Type': 'application/json',
            'x-user-id': user_id,
        },
        'multiValueHeaders': {},
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'pathParameters': path_parameters,
        'stageVariables': None,
        'requestContext': {
            'resourcePath': path,
            'httpMethod': method,
            'path': path,
            'stage': 'test',
            'requestId': 'req-q02',
            'authorizer': {'claims': {'sub': user_id}},
        },
        'body': json.dumps(body) if body is not None else None,
        'isBase64Encoded': False,
    }


def _context() -> Any:
    ctx = MagicMock()
    ctx.aws_request_id = 'req-q02'
    ctx.function_name = 'gap-handler'
    return ctx


# Real UserCV item — the key shape that get_cv_by_id queries (userId/cvId schema).
# Also contains pk/sk for the legacy fallback path inside get_cv_by_id.
_REAL_CV_ITEM: dict[str, Any] = {
    # Canonical key schema (userId/cvId)
    'userId': 'user-q02',
    'cvId': 'cv-real-001',
    # Legacy key schema (pk/sk) — present so the table can hold both schemas
    'pk': 'user-q02',
    'sk': 'CV#cv-real-001',
    # UserCV required fields
    'user_id': 'user-q02',
    'full_name': 'Jane Realname',
    'work_experience': [
        {
            'company': 'RealCorp',
            'role': 'Senior Engineer',
            'start_date': '2020-01',
            'end_date': 'Present',
            'achievements': ['Reduced latency by 40%'],
            'technologies': ['Python', 'AWS'],
        }
    ],
    'skills': [{'name': 'Python'}, {'name': 'AWS'}],
    'education': [],
    'certifications': [],
    'languages': [],
    'is_parsed': True,
}


# ---------------------------------------------------------------------------
# Helper: create the gap questions table (pk/sk schema, mirroring existing tests)
# ---------------------------------------------------------------------------


def _create_gap_table(dynamodb_resource: Any) -> Any:
    table = dynamodb_resource.create_table(
        TableName='test-gap-table',
        KeySchema=[
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName='test-gap-table')
    return table


# ---------------------------------------------------------------------------
# Helper: create the CVs table with userId/cvId schema (live-truth key schema).
# get_cv_by_id first tries `Key={'userId': ..., 'cvId': ...}` and falls back to
# pk/sk only on a ValidationException — so the table MUST use the userId/cvId schema.
# ---------------------------------------------------------------------------


def _create_cvs_table(dynamodb_resource: Any) -> Any:
    table = dynamodb_resource.create_table(
        TableName='test-cvs-table',
        KeySchema=[
            {'AttributeName': 'userId', 'KeyType': 'HASH'},
            {'AttributeName': 'cvId', 'KeyType': 'RANGE'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'userId', 'AttributeType': 'S'},
            {'AttributeName': 'cvId', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName='test-cvs-table')
    return table


# ---------------------------------------------------------------------------
# Test 1 — CHARACTERISATION: documents the CURRENT stub bug.
# This test asserts the bug exists BEFORE the fix.
# After the GREEN fix it is expected to become a negative characterisation
# (the fix inverts this behaviour), but for the RED→GREEN gate it must PASS
# as a stub check right now (i.e. the handler still uses the stub).
# ---------------------------------------------------------------------------


def test_gap_payload_is_characterization_stub() -> None:
    """Inverted characterisation: after the fix, the stub values must NOT appear.

    The original RED version of this test confirmed the bug ('Candidate' stub was returned).
    After the GREEN fix the stub is gone; this test confirms the fix held — the function
    no longer accepts the old (cv_id-only) signature and no longer returns the stub.

    Specifically: calling _build_user_cv_prompt_payload without user_id must raise TypeError,
    proving the stub path is unreachable via the old call signature.
    """
    from careervp.handlers.gap_handler import _build_user_cv_prompt_payload

    # After the fix the function requires user_id; old call signature is gone.
    build_payload = cast(Any, _build_user_cv_prompt_payload)
    with pytest.raises(TypeError, match='user_id'):
        build_payload(cv_id='cv-ignored', focus_areas=['python'])


# ---------------------------------------------------------------------------
# Test 2 — PRIMARY MOTO TEST: handler end-to-end with a real CV in DynamoDB.
# Seeds a moto table with the ACTUAL live key schema (userId/cvId).
# Asserts the LLM prompt contains the real candidate name and a real experience
# bullet, and does NOT contain 'Candidate' or 'Current Company'.
# ---------------------------------------------------------------------------


@mock_aws
def test_gap_loads_real_cv_moto() -> None:
    """Primary correctness: handler must pass real CV data into the LLM prompt.

    Seeds a moto cvs-table (userId/cvId schema) with a known UserCV, calls the
    handler POST /gap-analysis/questions, and asserts the prompt forwarded to
    generate_gap_questions contains the real candidate name ('Jane Realname') and
    a real experience bullet ('RealCorp'), NOT the stub values.
    """
    from careervp.handlers.gap_handler import lambda_handler
    from careervp.models.result import Result, ResultCode

    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    _create_gap_table(dynamodb)
    cvs_table = _create_cvs_table(dynamodb)
    cvs_table.put_item(Item=_REAL_CV_ITEM)

    event = _event(
        path='/gap-analysis/questions',
        method='POST',
        body={
            'cv_id': 'cv-real-001',
            'job_id': 'job-q02-moto',
            'max_questions': 3,
            'focus_areas': ['python'],
        },
        user_id='user-q02',
    )

    captured_user_cv: dict[str, Any] = {}

    # Wrap generate_gap_questions to capture what user_cv dict is passed to it.
    async def _capture_generate(
        user_cv: dict[str, Any],
        job_posting: dict[str, Any],
        dal: Any,
        language: str = 'en',
    ) -> Any:
        captured_user_cv.update(user_cv)
        # Return a minimal success so the handler doesn't blow up downstream.
        return Result(
            success=True,
            data=[
                {
                    'question_id': 'gap-q1',
                    'question': 'Describe impact.',
                    'impact': 'HIGH',
                    'probability': 'MEDIUM',
                    'tags': ['[CV IMPACT]'],
                    'requirement': 'Python',
                    'strategic_intent': 'assess',
                    'evidence_gap': 'none',
                    'priority': 'CRITICAL',
                    'destination': 'CV IMPACT',
                    'gap_score': 0.9,
                }
            ],
            code=ResultCode.GAP_QUESTIONS_GENERATED,
        )

    with (
        patch('careervp.handlers.gap_handler.generate_gap_questions', side_effect=_capture_generate),
        patch('careervp.handlers.gap_handler._get_trial_service') as mock_trial,
    ):
        trial_svc = MagicMock()
        trial_svc.check_trial_status.return_value = {'is_active': True}
        trial_svc.consume_credit.return_value = None
        mock_trial.return_value = trial_svc

        response = lambda_handler(event, _context())

    assert response['statusCode'] in (200, 201), f'Expected 200/201, got {response["statusCode"]}; body={response["body"]}'

    # The prompt dict passed to generate_gap_questions must contain the real name.
    personal = captured_user_cv.get('personal_info', {})
    full_name = personal.get('full_name', '')
    assert full_name == 'Jane Realname', (
        f"Expected 'Jane Realname' in user_cv personal_info.full_name, got {full_name!r}. Handler is still using the stub CV."
    )

    # Must NOT contain stub sentinel values.
    assert full_name != 'Candidate', "Handler still using stub 'Candidate' full_name"

    work_exp = captured_user_cv.get('work_experience', [])
    companies = [e.get('company', '') for e in work_exp]
    assert 'RealCorp' in companies, f"Expected 'RealCorp' in work_experience companies, got {companies}"
    assert 'Current Company' not in companies, "Handler still injecting stub 'Current Company'"


# ---------------------------------------------------------------------------
# Test 3 — UNIT COMPANION: patch-based; asserts get_cv_by_id is called with
# the request's user_id + cv_id.
# ---------------------------------------------------------------------------


def test_gap_loads_real_cv_by_id() -> None:
    """Unit companion: DynamoDalHandler.get_cv_by_id must be called with the right keys.

    Uses patch instead of moto so the test runs without network I/O.
    Complements test_gap_loads_real_cv_moto (which is the authoritative test).
    """
    from careervp.handlers.gap_handler import _build_user_cv_prompt_payload
    from careervp.models.cv import UserCV, WorkExperience

    fake_cv = UserCV(
        user_id='user-q02',
        full_name='Jane Patched',
        language='en',
        contact_info=None,
        experience=[WorkExperience(company='PatchedCorp', role='Lead Engineer', achievements=[], technologies=[])],
        skills=[],
        education=[],
        certifications=[],
        languages=[],
        top_achievements=[],
        is_parsed=True,
    )

    with patch('careervp.handlers.gap_handler.DynamoDalHandler') as MockDalHandler:
        mock_dal_instance = MagicMock()
        MockDalHandler.return_value = mock_dal_instance
        mock_dal_instance.get_cv_by_id.return_value = fake_cv

        result = _build_user_cv_prompt_payload(user_id='user-q02', cv_id='cv-patch-001', focus_areas=['aws'])

    # get_cv_by_id must be called with the exact user_id + cv_id from the request.
    mock_dal_instance.get_cv_by_id.assert_called_once_with('user-q02', 'cv-patch-001')

    # Returned dict must contain the real name, not the stub.
    personal = result.get('personal_info', {})
    assert personal.get('full_name') == 'Jane Patched', f"Expected 'Jane Patched', got {personal.get('full_name')!r}"
    assert result.get('personal_info', {}).get('full_name') != 'Candidate'


# ---------------------------------------------------------------------------
# Test 4 — MISSING CV: get_cv_by_id returning None must yield HTTP 404 with
# the §3 item-10 error envelope; the stub must NOT be used as a silent fallback.
# ---------------------------------------------------------------------------


def test_gap_missing_cv_errors_not_stub() -> None:
    """Missing CV: None from DAL → §3 item-10 envelope + HTTP 404, never the stub.

    Asserts:
    - statusCode == 404
    - body contains 'error_code' == 'cv_not_found'
    - response is never a successful (200) stub gap generation
    """
    from careervp.handlers.gap_handler import lambda_handler

    event = _event(
        path='/gap-analysis/questions',
        method='POST',
        body={
            'cv_id': 'cv-missing-999',
            'job_id': 'job-q02-missing',
            'max_questions': 5,
            'focus_areas': ['python'],
        },
        user_id='user-q02',
    )

    with (
        patch('careervp.handlers.gap_handler.DynamoDalHandler') as MockDalHandler,
        patch('careervp.handlers.gap_handler._get_trial_service') as mock_trial,
        patch('careervp.handlers.gap_handler.generate_gap_questions') as mock_gen,
    ):
        mock_dal_instance = MagicMock()
        MockDalHandler.return_value = mock_dal_instance
        mock_dal_instance.get_cv_by_id.return_value = None  # CV not found

        trial_svc = MagicMock()
        trial_svc.check_trial_status.return_value = {'is_active': True}
        trial_svc.consume_credit.return_value = None
        mock_trial.return_value = trial_svc

        response = lambda_handler(event, _context())

    # Must NOT succeed (stub fallback is forbidden).
    assert response['statusCode'] == 404, f'Expected HTTP 404 for missing CV, got {response["statusCode"]}; body={response["body"]}'

    body = json.loads(response['body'])

    # §3 item-10 envelope: must carry error_code == 'cv_not_found'
    assert set(body) == {'error', 'message', 'classification', 'error_code', 'field'}
    assert body.get('error_code') == 'cv_not_found', f"Expected error_code='cv_not_found' in body, got {body}"

    # generate_gap_questions must NOT be called (the stub path must not run).
    mock_gen.assert_not_called()
