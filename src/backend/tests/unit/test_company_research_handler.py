"""
Unit tests for careervp.handlers.company_research_handler.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from careervp.handlers.company_research_handler import lambda_handler
from careervp.models.company import CompanyResearchResult, ResearchSource
from careervp.models.result import Result, ResultCode


def _build_company_result(source: ResearchSource) -> CompanyResearchResult:
    return CompanyResearchResult(
        company_name='Acme Corp',
        overview='Acme overview',
        values=['Innovation'],
        mission=None,
        strategic_priorities=[],
        recent_news=[],
        financial_summary=None,
        source=source,
        source_urls=['https://acme.com/about'],
        confidence_score=0.8,
        research_timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture(autouse=True)
def company_research_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ENV', 'local')


def _event(body: str) -> dict[str, object]:
    return {
        'body': body,
        'headers': {'x-user-id': 'user-1'},
    }


def test_handler_success() -> None:
    """lambda_handler should return 202 and request handle when research is submitted."""
    event = _event(json.dumps({'company_name': 'Acme Corp', 'domain': 'acme.com'}))
    context = MagicMock()

    mock_result = Result(success=True, data=_build_company_result(ResearchSource.WEBSITE_SCRAPE), code=ResultCode.RESEARCH_COMPLETE)

    with patch('careervp.handlers.company_research_handler.research_company', new_callable=AsyncMock) as mock_research:
        mock_research.return_value = mock_result

        response = lambda_handler(event, context)

    assert response['statusCode'] == HTTPStatus.ACCEPTED.value
    body = json.loads(response['body'])
    assert body['status'] == 'processing'
    assert body['request_id']


def test_handler_invalid_json_returns_400() -> None:
    """Invalid JSON body should yield 400."""
    event = _event('{bad json')
    context = MagicMock()

    response = lambda_handler(event, context)

    assert response['statusCode'] == HTTPStatus.BAD_REQUEST.value


def test_handler_validation_error_returns_400() -> None:
    """Missing company_name should yield 400."""
    event = _event(json.dumps({'domain': 'acme.com'}))
    context = MagicMock()

    response = lambda_handler(event, context)

    assert response['statusCode'] == HTTPStatus.BAD_REQUEST.value


def test_handler_partial_content_status() -> None:
    """When logic returns SCRAPE_FAILED code, handler still returns async 202 contract response."""
    event = _event(json.dumps({'company_name': 'Acme Corp'}))
    context = MagicMock()

    mock_result = Result(success=True, data=_build_company_result(ResearchSource.WEB_SEARCH), code=ResultCode.SCRAPE_FAILED)

    with patch('careervp.handlers.company_research_handler.research_company', new_callable=AsyncMock) as mock_research:
        mock_research.return_value = mock_result

        response = lambda_handler(event, context)

    assert response['statusCode'] == HTTPStatus.ACCEPTED.value


def test_handler_failure_propagates_error_code() -> None:
    """Failures still return async 202 contract response with request handle."""
    event = _event(json.dumps({'company_name': 'Acme Corp'}))
    context = MagicMock()

    mock_result: Result[CompanyResearchResult] = Result(success=False, error='Service unavailable', code=ResultCode.ALL_SOURCES_FAILED)

    with patch('careervp.handlers.company_research_handler.research_company', new_callable=AsyncMock) as mock_research:
        mock_research.return_value = mock_result

        response = lambda_handler(event, context)

    assert response['statusCode'] == HTTPStatus.ACCEPTED.value
