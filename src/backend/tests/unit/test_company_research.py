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
    _normalize_domain,
    _parse_llm_payload,
    _resolve_domain,
    _structure_raw_content,
    _truncate_text,
    _try_llm_fallback,
    _try_web_search,
    _try_website_scrape,
    _web_api_identity_verified,
    load_confident_company_research,
    research_company,
)
from careervp.logic.prompts.company_research_prompt import build_structure_user_prompt
from careervp.models.company import CompanyResearchRequest, CompanyResearchResult, ResearchSource, SearchResult
from careervp.models.job import CompanyContext
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
        key_products=['Workflow Cloud'],
        company_size='201-500 employees',
        key_executives=['Alex Rivera, CEO'],
        competitive_positioning='Operational workflow software',
        growth_signals=['Hiring'],
        source=source,
        source_urls=['https://www.sysaid.com/about'],
        confidence_score=0.9,
        research_timestamp=datetime.now(timezone.utc),
    )


def test_research_company_tavily_site_scoped_success(sample_request: CompanyResearchRequest) -> None:
    """research_company should use site-scoped Tavily retrieval when a domain is available."""

    async def run() -> None:
        with (
            patch(
                'careervp.logic.company_research._try_web_search',
                new_callable=AsyncMock,
            ) as mock_try_search,
            patch('careervp.logic.company_research._structure_raw_content', new_callable=AsyncMock) as mock_structure,
        ):
            mock_try_search.return_value = Result(success=True, data=' '.join(['Acme Corp mission products'] * 90), code=ResultCode.SUCCESS)
            mock_structure.return_value = Result(
                success=True,
                data=_build_company_result(ResearchSource.WEB_API),
                code=ResultCode.RESEARCH_COMPLETE,
            )

            result = await research_company(sample_request)

        assert result.success is True
        assert result.data is not None
        assert result.data.source == ResearchSource.WEB_API
        mock_try_search.assert_awaited_once()
        assert mock_try_search.await_args_list[0].kwargs['domain'] == 'acme.com'
        assert mock_structure.await_args_list[0].kwargs['source'] == ResearchSource.WEB_API
        assert mock_structure.await_args_list[0].kwargs['job_domain'] == 'acme.com'

    asyncio.run(run())


def test_research_company_tavily_general_fallback(sample_request: CompanyResearchRequest) -> None:
    """When site-scoped Tavily retrieval fails, research_company should fall back to general Tavily search."""

    async def run() -> None:
        with (
            patch(
                'careervp.logic.company_research._try_web_search',
                new_callable=AsyncMock,
            ) as mock_try_search,
            patch('careervp.logic.company_research._structure_raw_content', new_callable=AsyncMock) as mock_structure,
        ):
            mock_try_search.side_effect = [
                Result(success=False, error='domain miss', code=ResultCode.NO_RESULTS),
                Result(success=True, data=' '.join(['Acme Corp culture'] * 90), code=ResultCode.SUCCESS),
            ]
            mock_structure.return_value = Result(
                success=True,
                data=_build_company_result(ResearchSource.WEB_API),
                code=ResultCode.RESEARCH_COMPLETE,
            )

            result = await research_company(sample_request)

        assert result.success is True
        assert result.data is not None
        assert result.data.source == ResearchSource.WEB_API
        assert mock_try_search.await_count == 2
        assert mock_try_search.await_args_list[0].kwargs['domain'] == 'acme.com'
        assert 'domain' not in mock_try_search.await_args_list[1].kwargs
        mock_structure.assert_awaited_once()

    asyncio.run(run())


def test_research_company_no_llm_fabrication_when_sources_fail(sample_request: CompanyResearchRequest) -> None:
    """FE-UI-041: when Tavily retrieval fails, research must NOT fall back to LLM
    synthesis of company facts. It returns ALL_SOURCES_FAILED instead of fabricated content."""

    async def run() -> None:
        with (
            patch(
                'careervp.logic.company_research._try_web_search',
                new_callable=AsyncMock,
            ) as mock_try_search,
            patch('careervp.logic.company_research._structure_raw_content', new_callable=AsyncMock) as mock_structure,
        ):
            mock_try_search.return_value = Result(success=False, error='no results', code=ResultCode.SEARCH_FAILED)

            result = await research_company(sample_request)

        assert result.success is False
        assert result.code == ResultCode.ALL_SOURCES_FAILED
        assert result.data is None
        assert mock_try_search.await_count == 2
        mock_structure.assert_not_awaited()

    asyncio.run(run())


def test_research_company_all_sources_fail(sample_request: CompanyResearchRequest) -> None:
    """research_company should bubble up failure when all sources fail."""

    async def run() -> None:
        with (
            patch(
                'careervp.logic.company_research._try_web_search',
                new_callable=AsyncMock,
            ) as mock_try_search,
            patch('careervp.logic.company_research._structure_raw_content', new_callable=AsyncMock),
        ):
            mock_try_search.return_value = Result(success=False, error='no results', code=ResultCode.SEARCH_FAILED)

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
        'key_products': ['Platform'],
        'company_size': '201-500 employees',
        'key_executives': ['Alex CEO'],
        'competitive_positioning': 'Enterprise workflow platform',
        'growth_signals': ['Hiring globally'],
    }

    class DummyRouter:
        def invoke(self, **kwargs):
            return Result(success=True, data={'text': json.dumps(payload)}, code=ResultCode.SUCCESS)

    async def run() -> None:
        with patch('careervp.logic.company_research.get_llm_router', return_value=DummyRouter()):
            response = await _structure_raw_content(
                company_name='Acme Corp',
                raw_text=' '.join(['insight'] * 320),
                source=ResearchSource.WEB_API,
                source_urls=['https://acme.com/about', 'https://acme.com/about'],
                word_count=320,
                context_hint='web api results',
                job_domain='acme.com',
            )

        assert response.success is True
        assert response.data is not None
        assert response.data.values == payload['values']
        assert response.data.source_urls == ['https://acme.com/about']
        assert response.data.overview == payload['overview']
        assert response.data.key_products == payload['key_products']
        assert response.data.company_size == payload['company_size']
        assert response.data.key_executives == payload['key_executives']
        assert response.data.competitive_positioning == payload['competitive_positioning']
        assert response.data.growth_signals == payload['growth_signals']

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
    """If explicit domain is missing, research_company should use the job posting URL domain."""
    request = sample_request.model_copy()
    request.domain = None
    request.job_posting_url = cast(HttpUrl, 'https://acme.com/jobs/123')

    async def run() -> None:
        with (
            patch(
                'careervp.logic.company_research._try_web_search',
                new_callable=AsyncMock,
            ) as mock_try_search,
            patch('careervp.logic.company_research._structure_raw_content', new_callable=AsyncMock) as mock_structure,
        ):
            mock_try_search.return_value = Result(success=True, data=' '.join(['Acme Corp mission'] * 90), code=ResultCode.SUCCESS)
            mock_structure.return_value = Result(
                success=True,
                data=_build_company_result(ResearchSource.WEB_API),
                code=ResultCode.RESEARCH_COMPLETE,
            )

            response = await research_company(request)

        assert response.success is True
        assert mock_try_search.await_args_list[0].kwargs['domain'] == 'acme.com'

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
    web_api_confidence = _calculate_confidence(
        ResearchSource.WEB_API,
        600,
        {
            'overview': 'Acme overview',
            'mission': 'm',
            'values': ['v'],
            'recent_news': ['n'],
            'strategic_priorities': ['p'],
        },
        company_name='Acme Corp',
        content_text='Acme Corp builds workflow tools.',
        source_urls=['https://example.com/about'],
    )
    assert web_api_confidence >= 0.85
    mismatched_web_api_confidence = _calculate_confidence(
        ResearchSource.WEB_API,
        600,
        {
            'overview': 'Other overview',
            'mission': 'm',
            'values': ['v'],
            'recent_news': ['n'],
            'strategic_priorities': ['p'],
        },
        company_name='Acme Corp',
        content_text='Different company content.',
        source_urls=['https://other.example/about'],
        job_domain='acme.com',
    )
    assert mismatched_web_api_confidence <= 0.7
    fallback_confidence = _calculate_confidence(ResearchSource.LLM_FALLBACK, 450, {})
    assert fallback_confidence <= 0.5


def test_web_api_with_identity_match_passes_gate() -> None:
    confidence = _calculate_confidence(
        ResearchSource.WEB_API,
        600,
        {
            'overview': 'Acme overview',
            'mission': 'm',
            'values': ['v'],
            'recent_news': ['n'],
            'strategic_priorities': ['p'],
        },
        company_name='Acme Corp',
        content_text='Acme Corp builds workflow tools for IT teams.',
        source_urls=['https://example.com/about'],
    )

    assert confidence >= 0.85


def test_web_api_domain_match_satisfies_identity() -> None:
    confidence = _calculate_confidence(
        ResearchSource.WEB_API,
        600,
        {
            'overview': 'Acme overview',
            'mission': 'm',
            'values': ['v'],
            'recent_news': ['n'],
            'strategic_priorities': ['p'],
        },
        company_name='Acme Corp',
        content_text='This page describes a modern service desk platform.',
        source_urls=['https://sysaid.com/about'],
        job_domain='sysaid.com',
    )

    assert _web_api_identity_verified(
        company_name='Acme Corp',
        content_text='This page describes a modern service desk platform.',
        source_urls=['https://sysaid.com/about'],
        job_domain='sysaid.com',
    )
    assert confidence >= 0.85


def test_web_api_no_identity_match_capped_below_gate() -> None:
    confidence = _calculate_confidence(
        ResearchSource.WEB_API,
        600,
        {
            'overview': 'Other overview',
            'mission': 'm',
            'values': ['v'],
            'recent_news': ['n'],
            'strategic_priorities': ['p'],
        },
        company_name='Acme Corp',
        content_text='Different company content.',
        source_urls=['https://other.example/about'],
        job_domain='acme.com',
    )

    assert confidence <= 0.70


def test_missing_core_fields_apply_penalty() -> None:
    confidence = _calculate_confidence(
        ResearchSource.WEB_API,
        600,
        {
            'overview': 'Acme overview',
            'values': ['v'],
            'recent_news': ['n'],
        },
        company_name='Acme Corp',
        content_text='Acme Corp builds workflow tools.',
        source_urls=['https://acme.com/about'],
        job_domain='acme.com',
    )

    assert confidence == pytest.approx(0.68)


def test_total_failure_returns_all_sources_failed(sample_request: CompanyResearchRequest) -> None:
    async def run() -> None:
        with (
            patch('careervp.logic.company_research._try_web_search', new_callable=AsyncMock) as mock_try_search,
            patch('careervp.logic.company_research._structure_raw_content', new_callable=AsyncMock) as mock_structure,
        ):
            mock_try_search.side_effect = [
                Result(success=False, error='site failed', code=ResultCode.SEARCH_FAILED),
                Result(success=False, error='general failed', code=ResultCode.NO_RESULTS),
            ]

            result = await research_company(sample_request)

        assert result.success is False
        assert result.code == ResultCode.ALL_SOURCES_FAILED
        assert result.data is None
        assert mock_try_search.await_count == 2
        mock_structure.assert_not_awaited()

    asyncio.run(run())


def test_truncation_at_2500_words() -> None:
    raw_text = ' '.join(f'word-{index}' for index in range(3000))
    truncated = _truncate_text(raw_text, max_words=2500)

    assert len(truncated.split()) == 2500
    assert 'word-2499' in truncated
    assert 'word-2500' not in truncated


def test_result_model_has_new_fields() -> None:
    result = CompanyResearchResult(
        company_name='Acme Corp',
        overview='Acme overview',
        values=['Innovation'],
        mission='Ship reliable workflows',
        strategic_priorities=['Scale'],
        recent_news=['Raised funding'],
        financial_summary='Private',
        key_products=['Workflow Cloud'],
        company_size='201-500 employees',
        key_executives=['Alex Rivera, CEO'],
        competitive_positioning='Operational workflow software',
        growth_signals=['Hiring'],
        source=ResearchSource.WEB_API,
        source_urls=['https://acme.com/about'],
        confidence_score=0.88,
        research_timestamp=datetime.now(timezone.utc),
    )

    assert result.key_products == ['Workflow Cloud']
    assert result.company_size == '201-500 employees'
    assert result.key_executives == ['Alex Rivera, CEO']
    assert result.competitive_positioning == 'Operational workflow software'
    assert result.growth_signals == ['Hiring']


def test_context_surfaces_overview_and_financial_summary() -> None:
    item = {
        'user_id': 'user-1',
        'company_research_id': 'cr-1',
        'company_name': 'Acme Corp',
        'overview': 'Acme overview',
        'mission': 'Ship reliable workflows',
        'values': ['Innovation'],
        'strategic_priorities': ['Scale'],
        'recent_news': ['Raised funding'],
        'financial_summary': 'Private',
        'key_products': ['Workflow Cloud'],
        'company_size': '201-500 employees',
        'key_executives': ['Alex Rivera, CEO'],
        'competitive_positioning': 'Operational workflow software',
        'growth_signals': ['Hiring'],
        'confidence_score': '0.9',
        'created_at': '2026-06-27T10:00:00+00:00',
    }

    with patch('careervp.logic.company_research.read_cr_artifact', return_value=item):
        context = load_confident_company_research(application_id='app-1', user_id='user-1')

    assert isinstance(context, CompanyContext)
    assert context.overview == 'Acme overview'
    assert context.financial_summary == 'Private'


def test_context_carries_new_fields_for_vpr() -> None:
    context = CompanyContext(
        company_name='Acme Corp',
        overview='Acme overview',
        mission='Ship reliable workflows',
        values=['Innovation'],
        strategic_priorities=['Scale'],
        recent_news=['Raised funding'],
        financial_summary='Private',
        key_products=['Workflow Cloud'],
        company_size='201-500 employees',
        key_executives=['Alex Rivera, CEO'],
        competitive_positioning='Operational workflow software',
        growth_signals=['Hiring'],
        industry='SaaS',
    )

    dumped = context.model_dump()

    assert dumped['overview'] == 'Acme overview'
    assert dumped['financial_summary'] == 'Private'
    assert dumped['key_products'] == ['Workflow Cloud']
    assert dumped['company_size'] == '201-500 employees'
    assert dumped['key_executives'] == ['Alex Rivera, CEO']
    assert dumped['competitive_positioning'] == 'Operational workflow software'
    assert dumped['growth_signals'] == ['Hiring']


def test_structuring_prompt_requests_new_keys() -> None:
    prompt = build_structure_user_prompt('Acme Corp', 'raw content', 'Tavily profile search')

    assert 'key_products' in prompt
    assert 'company_size' in prompt
    assert 'key_executives' in prompt
    assert 'competitive_positioning' in prompt
    assert 'growth_signals' in prompt


def test_domain_normalization_handles_urls_and_bare_domains() -> None:
    assert _normalize_domain('https://www.acme.com/careers') == 'acme.com'
    assert _normalize_domain('acme.com') == 'acme.com'
