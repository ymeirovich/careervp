"""Managed web search utilities for company research."""

from __future__ import annotations

from typing import Final

from careervp.logic.utils.tavily_client import TavilyClient
from careervp.models.company import SearchResult
from careervp.models.result import Result, ResultCode

MAX_RESULTS: Final[int] = 5
PROFILE_RESULTS: Final[int] = 3
NEWS_RESULTS: Final[int] = 3


async def search_company_info(company_name: str, *, domain: str | None = None) -> Result[list[SearchResult]]:
    """Run Tavily profile and news queries for a company."""
    clean_company_name = company_name.strip()
    if not clean_company_name:
        return Result(success=False, error='Company name is required for search', code=ResultCode.INVALID_INPUT)

    clean_domain = _normalize_domain(domain)
    tavily = TavilyClient()
    profile_result = await _search_profile(tavily, clean_company_name, clean_domain)
    news_result = await _search_news(tavily, clean_company_name, domain=clean_domain)

    results = _merge_results(profile_result.data or [], news_result.data or [])
    if results:
        return Result(success=True, data=results[:MAX_RESULTS], code=ResultCode.SUCCESS)

    error = profile_result.error or news_result.error or 'No Tavily search results found'
    code = _select_failure_code(profile_result, news_result)
    return Result(success=False, error=error, code=code)


async def search_company_news(company_name: str, *, domain: str | None = None) -> Result[list[SearchResult]]:
    """Run only the volatile company news query."""
    clean_company_name = company_name.strip()
    if not clean_company_name:
        return Result(success=False, error='Company name is required for search', code=ResultCode.INVALID_INPUT)

    clean_domain = _normalize_domain(domain)
    result = await _search_news(TavilyClient(), clean_company_name, domain=clean_domain)
    if result.data:
        return Result(success=True, data=result.data[:NEWS_RESULTS], code=ResultCode.SUCCESS)
    return Result(success=False, error=result.error or 'No Tavily news results found', code=result.code or ResultCode.NO_RESULTS)


def aggregate_search_content(results: list[SearchResult]) -> str:
    """Combine SearchResult content into a single text blob for structuring."""
    return '\n\n'.join(_result_content(result) for result in results if _result_content(result))


async def _search_profile(tavily: TavilyClient, company_name: str, domain: str | None) -> Result[list[SearchResult]]:
    search_name = _domain_to_search_name(domain) if domain else company_name
    if domain:
        return await tavily.search(
            f'{search_name} mission products business model',
            max_results=PROFILE_RESULTS,
            include_domains=[domain],
        )
    return await tavily.search(
        f'{search_name} mission products business model',
        max_results=PROFILE_RESULTS,
    )


async def _search_news(tavily: TavilyClient, company_name: str, *, domain: str | None = None) -> Result[list[SearchResult]]:
    search_name = _domain_to_search_name(domain) if domain else company_name
    if domain:
        return await tavily.search(
            f'{search_name} news funding leadership',
            max_results=NEWS_RESULTS,
            include_domains=[domain],
        )
    return await tavily.search(
        f'{search_name} news funding leadership',
        max_results=NEWS_RESULTS,
    )


def _merge_results(*result_groups: list[SearchResult]) -> list[SearchResult]:
    seen_urls: set[str] = set()
    merged: list[SearchResult] = []
    for group in result_groups:
        for result in group:
            url = str(result.url)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            merged.append(result)
    return merged


def _result_content(result: SearchResult) -> str:
    title = result.title.strip()
    snippet = result.snippet.strip()
    if title and snippet:
        return f'{title}\n{snippet}'
    return snippet or title


def _normalize_domain(domain: str | None) -> str | None:
    if not domain:
        return None
    clean_domain = domain.strip().removeprefix('https://').removeprefix('http://').split('/', 1)[0].lower()
    return clean_domain.removeprefix('www.') or None


def _domain_to_search_name(domain: str) -> str:
    """Extract a search-friendly name from a domain (e.g. 'sysaid.com' → 'sysaid').

    Used as the query term when domain is available so searches aren't anchored
    to a potentially mistyped user-entered company name.
    """
    base = domain.split('.')[0]
    return base if base else domain


def _select_failure_code(first: Result[list[SearchResult]], second: Result[list[SearchResult]]) -> str:
    if first.code == ResultCode.MISSING_ENV or second.code == ResultCode.MISSING_ENV:
        return ResultCode.MISSING_ENV
    if first.code == ResultCode.TIMEOUT or second.code == ResultCode.TIMEOUT:
        return ResultCode.TIMEOUT
    if first.code == ResultCode.NO_RESULTS and second.code == ResultCode.NO_RESULTS:
        return ResultCode.NO_RESULTS
    return ResultCode.SEARCH_FAILED


__all__ = [
    'MAX_RESULTS',
    'aggregate_search_content',
    'search_company_info',
    'search_company_news',
]
