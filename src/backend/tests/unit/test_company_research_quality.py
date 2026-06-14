"""
Unit tests for FE-UI-041 — CR quality gate / no fabrication.

TEST-CHAIN-002 categories covered:
  unit-cr-serve      — missing CR => not_generated, never fabricated
  unit-cr-quality    — no-source => ALL_SOURCES_FAILED
  unit-cr-confidence — sub-threshold not served as completed
  regression-no-company-for — 'Company for' literal removed everywhere
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from careervp.models.company import CompanyResearchRequest
from careervp.models.result import Result, ResultCode

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _aws_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-cr-quality-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('ENV', 'local')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-cr-quality-table')


@pytest.fixture
def cr_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-cr-quality-table',
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
        table.meta.client.get_waiter('table_exists').wait(TableName='test-cr-quality-table')
        yield table


def _get_event(job_id: str, user_id: str = 'user-1') -> dict[str, Any]:
    return {
        'resource': f'/company-research/{job_id}',
        'path': f'/company-research/{job_id}',
        'httpMethod': 'GET',
        'headers': {'Content-Type': 'application/json', 'x-user-id': user_id},
        'pathParameters': {'jobId': job_id},
        'queryStringParameters': None,
        'requestContext': {
            'httpMethod': 'GET',
            'authorizer': {'claims': {'sub': user_id}},
        },
        'body': None,
        'isBase64Encoded': False,
    }


def _lambda_context() -> Any:
    ctx = MagicMock()
    ctx.aws_request_id = 'test-req-1'
    ctx.function_name = 'company-research-handler'
    return ctx


# ---------------------------------------------------------------------------
# 1. unit-cr-serve: missing CR => {status:'not_generated', company_research:null}
# ---------------------------------------------------------------------------


def test_get_missing_cr_returns_not_generated(cr_table: Any) -> None:
    """
    GET /company-research/{jobId} with no CR item must return
    {status:'not_generated', company_research:null} — never a fabricated company payload.

    RED: current code returns _build_fallback_company_research_payload with
         company_name='Company for <uuid>' on missing item.
    """
    from careervp.handlers.company_research_handler import lambda_handler

    event = _get_event('job-missing-999')
    response = lambda_handler(event, _lambda_context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])

    # Required: explicit not_generated status
    assert body.get('status') == 'not_generated', f"Expected status='not_generated', got: {body.get('status')!r}"
    assert body.get('company_research') is None, f'Expected company_research=null, got: {body.get("company_research")!r}'

    # Must not contain fabricated company content
    body_str = json.dumps(body)
    assert 'Company for ' not in body_str, "Response must not contain fabricated 'Company for ...' content"
    assert 'mission' not in body or body.get('mission') is None, 'Missing CR must not surface a fabricated mission field'


# ---------------------------------------------------------------------------
# 2. regression: _build_fallback_company_research_payload must be removed
# ---------------------------------------------------------------------------


def test_fallback_payload_function_removed() -> None:
    """
    _build_fallback_company_research_payload must no longer exist anywhere in the codebase.

    RED: the function is currently defined in company_research_handler.py:449-461.
    """
    result = subprocess.run(
        ['grep', '-r', '--include=*.py', '_build_fallback_company_research_payload', 'careervp/'],
        capture_output=True,
        text=True,
        cwd='/Users/yitzchak/Documents/dev/careervp/src/backend',
    )
    matches = result.stdout.strip()
    assert matches == '', f'_build_fallback_company_research_payload still present in codebase:\n{matches}'


# ---------------------------------------------------------------------------
# 3. regression: 'Company for ' literal must be gone from backend source
# ---------------------------------------------------------------------------


def test_no_company_for_literal_anywhere() -> None:
    """
    No 'Company for ' string literal must remain in careervp/ source.

    RED: company_research_handler.py:167,453 and gap_handler.py:537,545
         all contain 'Company for '.
    """
    result = subprocess.run(
        ['grep', '-r', '--include=*.py', 'Company for ', 'careervp/'],
        capture_output=True,
        text=True,
        cwd='/Users/yitzchak/Documents/dev/careervp/src/backend',
    )
    matches = result.stdout.strip()
    assert matches == '', f"'Company for ' literal still present in careervp/ source:\n{matches}"


# ---------------------------------------------------------------------------
# 4. unit-cr-confidence: sub-threshold CR not served as 'completed'
# ---------------------------------------------------------------------------


def test_subthreshold_cr_not_served_as_completed(cr_table: Any) -> None:
    """
    A CR stored with confidence_score < CR_CONFIDENCE_THRESHOLD (0.85) or
    status='failed' must NOT be returned as a completed research payload.
    GET must return {status:'failed', company_research:null}.

    RED: current _build_company_research_response ignores confidence/status
         and returns the full item content regardless.
    """
    from careervp.handlers.company_research_handler import lambda_handler

    cr_table.put_item(
        Item={
            'pk': 'user-1',
            'sk': 'ARTIFACT#COMPANY_RESEARCH#job-low-conf',
            'user_id': 'user-1',
            'job_id': 'job-low-conf',
            'company_research_id': 'cr-low-1',
            'company_name': 'LowConf Corp',
            'mission': 'Some generic mission.',
            'values': ['Innovation'],
            'recent_news': [],
            'culture': 'Generic culture text.',
            'products': ['Generic product'],
            'funding_status': 'Unknown',
            'size_range': 'Unknown',
            'industry': 'Technology',
            'confidence_score': '0.6',  # below 0.85 threshold
            'artifact_status': 'failed',
        }
    )

    event = _get_event('job-low-conf')
    response = lambda_handler(event, _lambda_context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])

    # Must not be served as completed
    status = body.get('status')
    assert status in ('failed', 'not_generated'), f'Sub-threshold CR must not be served as completed; got status={status!r}'
    assert body.get('company_research') is None, 'Sub-threshold CR must have company_research=null in response'


# ---------------------------------------------------------------------------
# 5. unit-cr-quality: no source content => ALL_SOURCES_FAILED
# ---------------------------------------------------------------------------


def test_no_source_returns_all_sources_failed() -> None:
    """
    When scrape AND search both fail, research_company must return
    Result(success=False, code=ALL_SOURCES_FAILED) — not a successful result
    synthesised from job posting text alone (LLM fabrication).

    RED: current code falls through to _try_llm_fallback which succeeds when
         job_posting_text is provided, returning a low-confidence but 'success=True' result.
    """
    from careervp.logic.company_research import research_company

    request = CompanyResearchRequest(
        company_name='Acme Corp',
        domain='acme.com',
        job_posting_text='Acme Corp is hiring a senior engineer to build reliable systems.',
    )

    with (
        patch(
            'careervp.logic.company_research.scrape_company_about_page',
            new_callable=AsyncMock,
            return_value=Result(success=False, error='Connection refused', code=ResultCode.SCRAPE_FAILED),
        ),
        patch(
            'careervp.logic.company_research.search_company_info',
            new_callable=AsyncMock,
            return_value=Result(success=False, error='Search quota exceeded', code=ResultCode.SEARCH_FAILED),
        ),
    ):
        import asyncio

        result = asyncio.run(research_company(request))

    assert not result.success, 'research_company must fail when scrape and search both return empty'
    assert result.code == ResultCode.ALL_SOURCES_FAILED, f'Expected ALL_SOURCES_FAILED, got code={result.code!r}'
    # Result data must not contain any synthesised company content
    assert result.data is None, 'Result.data must be None when all sources failed — no LLM fabrication allowed'


# ---------------------------------------------------------------------------
# 6. gap_handler must never seed 'Company for {job_id}'
# ---------------------------------------------------------------------------


def test_gap_handler_uses_real_company_name() -> None:
    """
    _build_job_prompt_payload must seed the real company_name when present,
    and must NEVER fall back to 'Company for {job_id}' — even on exception.

    RED: the exception path (and explicit fallback) currently returns
         {'company_name': f'Company for {job_id}', ...}.
    """
    from careervp.handlers.gap_handler import _build_job_prompt_payload  # type: ignore[attr-defined]

    job_id = 'job-acme-123'

    # Case A: real company name available
    mock_job = {
        'title': 'Senior Engineer',
        'company_name': 'Acme Corp',
        'description': 'Build reliable systems.',
        'requirements': ['Python', 'AWS'],
    }
    mock_repo = MagicMock()
    mock_repo.get_job.return_value = mock_job

    with patch('careervp.handlers.gap_handler._get_jobs_repository', return_value=mock_repo):
        payload_a = _build_job_prompt_payload(job_id, [])

    assert payload_a['company_name'] == 'Acme Corp', f"Expected 'Acme Corp', got {payload_a['company_name']!r}"
    assert 'Company for ' not in payload_a['company_name'], "company_name must not be a 'Company for ...' placeholder"

    # Case B: job record unavailable (exception path) — must NOT seed 'Company for'
    with patch('careervp.handlers.gap_handler._get_jobs_repository', side_effect=Exception('DB error')):
        payload_b = _build_job_prompt_payload(job_id, [])

    assert payload_b.get('company_name') != f'Company for {job_id}', (
        "On job fetch failure, company_name must be null/empty — never 'Company for {job_id}'"
    )
    assert 'Company for ' not in (payload_b.get('company_name') or ''), "Exception path must not produce 'Company for ...' placeholder"
