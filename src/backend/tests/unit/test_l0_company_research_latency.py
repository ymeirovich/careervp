"""L0.5 real unit tests for company research latency controls."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from careervp.logic.company_research import _structure_raw_content
from careervp.logic.llm_cache import DEFAULT_CACHE_TTL_SECONDS
from careervp.logic.utils.web_scraper import SCRAPE_TIMEOUT, scrape_company_about_page, scrape_url
from careervp.models.company import ResearchSource
from careervp.models.result import Result, ResultCode


def test_web_scraper_has_timeout() -> None:
    """scrape_url configures the HTTP client with an explicit timeout."""

    async def run() -> None:
        mock_response = MagicMock()
        mock_response.text = '<html><body>ok</body></html>'
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with (
            patch('careervp.logic.utils.web_scraper._is_safe_url', return_value=True),
            patch('careervp.logic.utils.web_scraper.httpx.AsyncClient', return_value=mock_client) as async_client_cls,
        ):
            result = await scrape_url('https://example.com/about')

        assert result.success is True
        assert async_client_cls.call_args.kwargs['timeout'] == SCRAPE_TIMEOUT

    asyncio.run(run())


def test_web_scraper_limits_to_3_urls() -> None:
    """scrape_company_about_page attempts at most 3 candidate URLs."""

    async def run() -> None:
        candidate_urls = [f'https://example.com/path-{idx}' for idx in range(10)]
        with (
            patch('careervp.logic.utils.web_scraper._build_candidate_urls', return_value=candidate_urls),
            patch('careervp.logic.utils.web_scraper.scrape_url', new_callable=AsyncMock) as mock_scrape,
        ):
            mock_scrape.return_value = Result(success=False, error='not found', code=ResultCode.SCRAPE_FAILED)
            await scrape_company_about_page('https://example.com')

        assert mock_scrape.await_count == 3

    asyncio.run(run())


def test_cache_hit_skips_llm_call() -> None:
    """Cache hit returns immediately without invoking the LLM router."""

    async def run() -> None:
        cached_payload = {
            'company_name': 'Acme Corp',
            'overview': 'Cached overview',
            'values': ['Ownership'],
            'mission': 'Serve customers',
            'strategic_priorities': ['Scale'],
            'recent_news': ['Cached news'],
            'financial_summary': None,
            'source': 'website_scrape',
            'source_urls': ['https://acme.com/about'],
            'confidence_score': 0.88,
            'research_timestamp': datetime.now(timezone.utc).isoformat(),
        }
        cache = MagicMock()
        cache.get.return_value = json.dumps(cached_payload)

        router = MagicMock()
        router.invoke.return_value = Result(success=True, data={'text': '{}'}, code=ResultCode.SUCCESS)

        with (
            patch('careervp.logic.company_research.LLMResponseCache', return_value=cache),
            patch('careervp.logic.company_research.get_llm_router', return_value=router),
        ):
            result = await _structure_raw_content(
                company_name='Acme Corp',
                raw_text=' '.join(['content'] * 250),
                source=ResearchSource.WEB_SEARCH,
                source_urls=['https://acme.com/about'],
                word_count=250,
                context_hint='test',
            )

        assert result.success is True
        router.invoke.assert_not_called()

    asyncio.run(run())


def test_cache_miss_calls_llm_and_stores_result() -> None:
    """Cache miss invokes LLM and stores response with 7-day TTL."""

    async def run() -> None:
        cache = MagicMock()
        cache.get.return_value = None
        cache.set.return_value = True

        router = MagicMock()
        router.invoke.return_value = Result(
            success=True,
            data={
                'text': json.dumps(
                    {
                        'overview': 'Acme overview',
                        'values': ['Innovation'],
                        'mission': 'Grow responsibly',
                        'strategic_priorities': ['Scale'],
                        'recent_news': ['Expanded to EU'],
                        'financial_summary': 'Private',
                    }
                )
            },
            code=ResultCode.SUCCESS,
        )

        with (
            patch('careervp.logic.company_research.LLMResponseCache', return_value=cache),
            patch('careervp.logic.company_research.get_llm_router', return_value=router),
        ):
            result = await _structure_raw_content(
                company_name='Acme Corp',
                raw_text=' '.join(['content'] * 280),
                source=ResearchSource.WEBSITE_SCRAPE,
                source_urls=['https://acme.com/about'],
                word_count=280,
                context_hint='test',
            )

        assert result.success is True
        router.invoke.assert_called_once()
        cache.set.assert_called_once()
        assert cache.set.call_args.kwargs['ttl_seconds'] == DEFAULT_CACHE_TTL_SECONDS

    asyncio.run(run())
