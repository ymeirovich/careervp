"""
Unit tests for careervp.handlers.company_research_handler.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

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


def test_handler_success() -> None:
    """lambda_handler should return 200 when research succeeds."""
    event = {'body': json.dumps({'company_name': 'Acme Corp', 'domain': 'acme.com'})}
    context = MagicMock()

    mock_result = Result(success=True, data=_build_company_result(ResearchSource.WEBSITE_SCRAPE), code=ResultCode.RESEARCH_COMPLETE)

    with patch('careervp.handlers.company_research_handler.research_company', new_callable=AsyncMock) as mock_research:
        mock_research.return_value = mock_result

        response = lambda_handler(event, context)

    assert response['statusCode'] == HTTPStatus.OK.value
    body = json.loads(response['body'])
    assert body['company_name'] == 'Acme Corp'


def test_handler_invalid_json_returns_400() -> None:
    """Invalid JSON body should yield 400."""
    event = {'body': '{bad json'}
    context = MagicMock()

    response = lambda_handler(event, context)

    assert response['statusCode'] == HTTPStatus.BAD_REQUEST.value


def test_handler_validation_error_returns_400() -> None:
    """Missing company_name should yield 400."""
    event = {'body': json.dumps({'domain': 'acme.com'})}
    context = MagicMock()

    response = lambda_handler(event, context)

    assert response['statusCode'] == HTTPStatus.BAD_REQUEST.value


def test_handler_partial_content_status() -> None:
    """When logic returns SCRAPE_FAILED code, handler should return HTTP 206."""
    event = {'body': json.dumps({'company_name': 'Acme Corp'})}
    context = MagicMock()

    mock_result = Result(success=True, data=_build_company_result(ResearchSource.WEB_SEARCH), code=ResultCode.SCRAPE_FAILED)

    with patch('careervp.handlers.company_research_handler.research_company', new_callable=AsyncMock) as mock_research:
        mock_research.return_value = mock_result

        response = lambda_handler(event, context)

    assert response['statusCode'] == HTTPStatus.PARTIAL_CONTENT.value


def test_handler_failure_propagates_error_code() -> None:
    """Failures from logic should respect mapped HTTP status."""
    event = {'body': json.dumps({'company_name': 'Acme Corp'})}
    context = MagicMock()

    mock_result: Result[CompanyResearchResult] = Result(success=False, error='Service unavailable', code=ResultCode.ALL_SOURCES_FAILED)

    with patch('careervp.handlers.company_research_handler.research_company', new_callable=AsyncMock) as mock_research:
        mock_research.return_value = mock_result

        response = lambda_handler(event, context)

    assert response['statusCode'] == HTTPStatus.SERVICE_UNAVAILABLE.value
