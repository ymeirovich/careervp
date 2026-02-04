"""
Unit tests for careervp.logic.company_research.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Callable, cast
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import HttpUrl

from careervp.logic.company_research import (
    _calculate_confidence,
    _deduplicate_urls,
    _ensure_list,
    _ensure_optional_text,
    _ensure_text,
    _parse_llm_payload,
    _resolve_domain,
    _structure_raw_content,
    _try_llm_fallback,
    _try_web_search,
    _try_website_scrape,
    research_company,
)
from careervp.models.company import CompanyResearchRequest, CompanyResearchResult, ResearchSource, SearchResult
from careervp.models.result import Result, ResultCode


@pytest.fixture
def sample_request() -> CompanyResearchRequest:
    return CompanyResearchRequest(
        company_name='Acme Corp',
        domain='acme.com',
        job_posting_text='We are hiring to scale values-driven products.',
    )


def _build_company_result(source: ResearchSource) -> CompanyResearchResult:
    return CompanyResearchResult(
        company_name='Acme Corp',
        overview='Acme overview',
        values=['Innovation'],
        mission='Innovate responsibly',
        strategic_priorities=['Scale'],
        recent_news=['Won award'],
        financial_summary=None,
        source=source,
        source_urls=['https://acme.com/about'],
        confidence_score=0.9,
        research_timestamp=datetime.now(timezone.utc),
    )


def test_research_company_scrape_success(sample_request: CompanyResearchRequest) -> None:
    """research_company should return website source when scrape succeeds."""

    async def run() -> None:
        rich_content = ' '.join(['mission'] * 250)

        with (
            patch(
                'careervp.logic.company_research.scrape_company_about_page',
                new_callable=AsyncMock,
            ) as mock_scrape_page,
            patch(
                'careervp.logic.company_research._structure_raw_content',
                new_callable=AsyncMock,
            ) as mock_structure,
        ):
            mock_scrape_page.return_value = Result(success=True, data=rich_content, code=ResultCode.SUCCESS)
            mock_structure.return_value = Result(
                success=True,
                data=_build_company_result(ResearchSource.WEBSITE_SCRAPE),
                code=ResultCode.RESEARCH_COMPLETE,
            )

            result = await research_company(sample_request)

        assert result.success is True
        assert result.data is not None
        assert result.data.source == ResearchSource.WEBSITE_SCRAPE
        mock_structure.assert_awaited_once()

    asyncio.run(run())


def test_research_company_web_search_fallback(sample_request: CompanyResearchRequest) -> None:
    """When scrape fails, research_company should fall back to web search."""

    async def run() -> None:
        search_results = [
            SearchResult(
                title='Acme values',
                url=cast(HttpUrl, 'https://acme.com/about'),
                snippet=' '.join(['culture'] * 220),
            )
        ]

        with (
            patch(
                'careervp.logic.company_research.scrape_company_about_page',
                new_callable=AsyncMock,
            ) as mock_scrape_page,
            patch(
                'careervp.logic.company_research.search_company_info',
                new_callable=AsyncMock,
            ) as mock_search_info,
            patch(
                'careervp.logic.company_research._structure_raw_content',
                new_callable=AsyncMock,
            ) as mock_structure,
        ):
            mock_scrape_page.return_value = Result(success=False, error='insufficient', code=ResultCode.SCRAPE_FAILED)
            mock_search_info.return_value = Result(success=True, data=search_results, code=ResultCode.SUCCESS)
            mock_structure.return_value = Result(
                success=True,
                data=_build_company_result(ResearchSource.WEB_SEARCH),
                code=ResultCode.RESEARCH_COMPLETE,
            )

            result = await research_company(sample_request)

        assert result.success is True
        assert result.data is not None
        assert result.data.source == ResearchSource.WEB_SEARCH
        mock_structure.assert_awaited_once()

    asyncio.run(run())


def test_research_company_llm_fallback(sample_request: CompanyResearchRequest) -> None:
    """LLM fallback should run when both scrape and search fail."""

    async def run() -> None:
        with (
            patch(
                'careervp.logic.company_research.scrape_company_about_page',
                new_callable=AsyncMock,
            ) as mock_scrape_page,
            patch(
                'careervp.logic.company_research.search_company_info',
                new_callable=AsyncMock,
            ) as mock_search_info,
            patch(
                'careervp.logic.company_research._structure_raw_content',
                new_callable=AsyncMock,
            ) as mock_structure,
        ):
            mock_scrape_page.return_value = Result(success=False, error='error', code=ResultCode.SCRAPE_FAILED)
            mock_search_info.return_value = Result(success=False, error='no results', code=ResultCode.SEARCH_FAILED)
            mock_structure.return_value = Result(
                success=True,
                data=_build_company_result(ResearchSource.LLM_FALLBACK),
                code=ResultCode.RESEARCH_COMPLETE,
            )

            result = await research_company(sample_request)

        assert result.success is True
        assert result.data is not None
        assert result.data.source == ResearchSource.LLM_FALLBACK
        mock_structure.assert_awaited()

    asyncio.run(run())


def test_research_company_all_sources_fail(sample_request: CompanyResearchRequest) -> None:
    """research_company should bubble up failure when all sources fail."""

    async def run() -> None:
        with (
            patch(
                'careervp.logic.company_research.scrape_company_about_page',
                new_callable=AsyncMock,
            ) as mock_scrape_page,
            patch(
                'careervp.logic.company_research.search_company_info',
                new_callable=AsyncMock,
            ) as mock_search_info,
            patch(
                'careervp.logic.company_research._structure_raw_content',
                new_callable=AsyncMock,
            ) as mock_structure,
        ):
            mock_scrape_page.return_value = Result(success=False, error='error', code=ResultCode.SCRAPE_FAILED)
            mock_search_info.return_value = Result(success=False, error='no results', code=ResultCode.SEARCH_FAILED)
            mock_structure.return_value = Result(success=False, error='llm error', code=ResultCode.ALL_SOURCES_FAILED)

            result = await research_company(sample_request)

        assert result.success is False
        assert result.code == ResultCode.ALL_SOURCES_FAILED

    asyncio.run(run())


def test_try_website_scrape_records_source_url(sample_request: CompanyResearchRequest) -> None:
    """_try_website_scrape should append the resolved URL when successful."""

    async def run() -> None:
        async def fake_scrape(base_url: str, on_success: Callable[[str], None]) -> Result[str]:
            on_success(f'{base_url}/about')
            return Result(
                success=True,
                data=' '.join(['about'] * 210),
                code=ResultCode.SUCCESS,
            )

        with patch(
            'careervp.logic.company_research.scrape_company_about_page',
            new_callable=AsyncMock,
        ) as mock_scrape_page:
            mock_scrape_page.side_effect = fake_scrape
            urls: list[str] = []
            response = await _try_website_scrape(sample_request, domain='acme.com', source_urls=urls)

        assert response.success is True
        assert urls and urls[0].startswith('acme.com')

    asyncio.run(run())


def test_try_web_search_requires_sufficient_words() -> None:
    """_try_web_search should fail when aggregated snippets are too short."""

    async def run() -> None:
        short_results = [SearchResult(title='Snippet', url=cast(HttpUrl, 'https://acme.com'), snippet='Too short content')]
        with patch(
            'careervp.logic.company_research.search_company_info',
            new_callable=AsyncMock,
        ) as mock_search_info:
            mock_search_info.return_value = Result(success=True, data=short_results, code=ResultCode.SUCCESS)

            response = await _try_web_search('Acme Corp', source_urls=[])

        assert response.success is False
        assert response.code == ResultCode.SEARCH_FAILED

    asyncio.run(run())


def test_try_website_scrape_insufficient_content(sample_request: CompanyResearchRequest) -> None:
    """_try_website_scrape should return SCRAPE_FAILED when word count is low."""

    async def run() -> None:
        with patch(
            'careervp.logic.company_research.scrape_company_about_page',
            new_callable=AsyncMock,
        ) as mock_scrape_page:
            mock_scrape_page.return_value = Result(success=True, data='too short', code=ResultCode.SUCCESS)
            response = await _try_website_scrape(sample_request, domain='acme.com', source_urls=[])

        assert response.success is False
        assert response.code == ResultCode.SCRAPE_FAILED

    asyncio.run(run())


def test_try_llm_fallback_requires_job_text(sample_request: CompanyResearchRequest) -> None:
    """_try_llm_fallback should return error when job_posting_text is missing."""
    request = sample_request.model_copy()
    request.job_posting_text = None

    async def run() -> None:
        response = await _try_llm_fallback(request)
        assert response.success is False
        assert response.code == ResultCode.ALL_SOURCES_FAILED

    asyncio.run(run())


def test_structure_raw_content_parses_llm_output() -> None:
    """_structure_raw_content should build CompanyResearchResult from LLM JSON."""
    payload = {
        'overview': 'Company overview text',
        'values': ['Innovation', 'Ownership'],
        'mission': 'Empower clients',
        'strategic_priorities': ['Scale'],
        'recent_news': ['Raised Series B'],
        'financial_summary': 'Private',
    }

    class DummyRouter:
        def invoke(self, **kwargs):
            return Result(success=True, data={'text': json.dumps(payload)}, code=ResultCode.SUCCESS)

    async def run() -> None:
        with patch('careervp.logic.company_research.get_llm_router', return_value=DummyRouter()):
            response = await _structure_raw_content(
                company_name='Acme Corp',
                raw_text=' '.join(['insight'] * 320),
                source=ResearchSource.WEB_SEARCH,
                source_urls=['https://source.one', 'https://source.one'],
                word_count=320,
                context_hint='web search snippets',
            )

        assert response.success is True
        assert response.data is not None
        assert response.data.values == payload['values']
        assert response.data.source_urls == ['https://source.one']
        assert response.data.overview == payload['overview']

    asyncio.run(run())


def test_structure_raw_content_handles_llm_failure() -> None:
    """LLM failures should return error Result."""

    class FailingRouter:
        def invoke(self, **kwargs):
            return Result(success=False, error='llm error', code=ResultCode.LLM_API_ERROR)

    async def run() -> None:
        with patch('careervp.logic.company_research.get_llm_router', return_value=FailingRouter()):
            response = await _structure_raw_content(
                company_name='Acme Corp',
                raw_text='content',
                source=ResearchSource.WEBSITE_SCRAPE,
                source_urls=[],
                word_count=50,
                context_hint='test',
            )

        assert response.success is False
        assert response.code == ResultCode.LLM_API_ERROR

    asyncio.run(run())


def test_structure_raw_content_handles_invalid_json() -> None:
    """Invalid JSON should trigger parse failure branch."""

    class InvalidRouter:
        def invoke(self, **kwargs):
            return Result(success=True, data={'text': 'not-json'}, code=ResultCode.SUCCESS)

    async def run() -> None:
        with patch('careervp.logic.company_research.get_llm_router', return_value=InvalidRouter()):
            response = await _structure_raw_content(
                company_name='Acme Corp',
                raw_text='content',
                source=ResearchSource.WEB_SEARCH,
                source_urls=[],
                word_count=250,
                context_hint='test',
            )

        assert response.success is False
        assert response.error == 'Unable to parse LLM response'

    asyncio.run(run())


def test_research_company_without_domain(sample_request: CompanyResearchRequest) -> None:
    """If domain is missing, research_company should still proceed via job posting URL."""
    request = sample_request.model_copy()
    request.domain = None
    request.job_posting_url = cast(HttpUrl, 'https://acme.com/jobs/123')

    async def run() -> None:
        with (
            patch(
                'careervp.logic.company_research.scrape_company_about_page',
                new_callable=AsyncMock,
            ) as mock_scrape_page,
            patch(
                'careervp.logic.company_research.search_company_info',
                new_callable=AsyncMock,
            ) as mock_search_info,
            patch(
                'careervp.logic.company_research._structure_raw_content',
                new_callable=AsyncMock,
            ) as mock_structure,
        ):
            mock_scrape_page.return_value = Result(success=False, error='no domain', code=ResultCode.SCRAPE_FAILED)
            mock_search_info.return_value = Result(
                success=True,
                data=[
                    SearchResult(
                        title='About',
                        url=cast(HttpUrl, 'https://acme.com/about'),
                        snippet=' '.join(['mission'] * 220),
                    )
                ],
                code=ResultCode.SUCCESS,
            )
            mock_structure.return_value = Result(
                success=True,
                data=_build_company_result(ResearchSource.WEB_SEARCH),
                code=ResultCode.RESEARCH_COMPLETE,
            )

            response = await research_company(request)

        assert response.success is True

    asyncio.run(run())


def test_research_company_handles_timeout(sample_request: CompanyResearchRequest) -> None:
    """research_company should convert asyncio.TimeoutError into TIMEOUT Result."""

    def fake_wait_for(coro, timeout):
        coro.close()
        raise asyncio.TimeoutError()

    with patch('careervp.logic.company_research.asyncio.wait_for', side_effect=fake_wait_for):
        result = asyncio.run(research_company(sample_request))

    assert result.success is False
    assert result.code == ResultCode.TIMEOUT


def test_parse_llm_payload_edge_cases() -> None:
    """_parse_llm_payload should return None for invalid inputs."""
    assert _parse_llm_payload('') is None
    assert _parse_llm_payload('not-json') is None
    assert _parse_llm_payload('["value"]') is None


def test_helper_functions_cover_edge_cases() -> None:
    """Directly exercise helper utilities."""
    assert (
        _resolve_domain(
            CompanyResearchRequest(
                company_name='Acme',
                domain=None,
                job_posting_url=cast(HttpUrl, 'https://acme.com/jobs/1'),
            )
        )
        == 'acme.com'
    )
    assert _ensure_list(['Value', '']) == ['Value']
    assert _ensure_list('Single') == ['Single']
    assert _ensure_text(' text ') == 'text'
    assert _ensure_text(123) == ''
    assert _ensure_optional_text(' optional ') == 'optional'
    assert _ensure_optional_text('  ') is None
    assert _deduplicate_urls(['https://one', 'https://one', 'https://two']) == ['https://one', 'https://two']
    scrape_confidence = _calculate_confidence(ResearchSource.WEBSITE_SCRAPE, 250, {})
    assert scrape_confidence < 0.9
    search_confidence = _calculate_confidence(
        ResearchSource.WEB_SEARCH, 400, {'mission': 'm', 'values': ['v'], 'recent_news': [], 'strategic_priorities': []}
    )
    assert search_confidence < 0.7
    fallback_confidence = _calculate_confidence(ResearchSource.LLM_FALLBACK, 450, {})
    assert fallback_confidence <= 0.5
