"""
Web search fallback utilities for company research.
Leverages DuckDuckGo HTML endpoint per docs/specs/02-company-research.md.
"""

from __future__ import annotations

from typing import Final, cast
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import HttpUrl

from careervp.models.company import SearchResult
from careervp.models.result import Result, ResultCode

DUCKDUCKGO_URL: Final[str] = 'https://html.duckduckgo.com/html/'
SEARCH_TIMEOUT: Final[float] = 15.0
MAX_RESULTS: Final[int] = 5
USER_AGENT: Final[str] = 'Mozilla/5.0 (compatible; CareerVP/1.0; +https://careervp.ai)'


async def search_company_info(company_name: str) -> Result[list[SearchResult]]:
    """
    Perform a DuckDuckGo HTML search for the given company and return parsed results.
    """
    query = f'{company_name} about culture values mission'

    response = await _make_search_request(query)
    if isinstance(response, Result):
        return response  # type: ignore[return-value]

    results = _parse_duckduckgo_results(response.text)
    if not results:
        return Result(success=False, error='No search results found', code=ResultCode.NO_RESULTS)

    return Result(success=True, data=results[:MAX_RESULTS], code=ResultCode.SUCCESS)


async def _make_search_request(query: str) -> Result[httpx.Response] | httpx.Response:
    """Make HTTP request with error handling, returning Result on failure."""
    try:
        async with httpx.AsyncClient(timeout=SEARCH_TIMEOUT) as client:
            return await client.post(
                DUCKDUCKGO_URL,
                data={'q': query},
                headers={'User-Agent': USER_AGENT},
            )
    except httpx.TimeoutException:
        return Result(success=False, error='Search timeout', code=ResultCode.TIMEOUT)
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response else 'unknown'
        return Result(success=False, error=f'Search HTTP {status_code}', code=ResultCode.SEARCH_FAILED)
    except httpx.RequestError as exc:
        return Result(success=False, error=f'Search request error: {exc}', code=ResultCode.SEARCH_FAILED)
    except Exception as exc:  # pragma: no cover - safety net
        return Result(success=False, error=str(exc), code=ResultCode.SEARCH_FAILED)


def _parse_duckduckgo_results(html: str) -> list[SearchResult]:
    """
    Parse DuckDuckGo HTML results into SearchResult structures.
    """
    soup = BeautifulSoup(html, 'html.parser')
    parsed_results: list[SearchResult] = []

    for result_block in soup.select('.result'):
        link = result_block.select_one('.result__a')
        if not link:
            continue

        title = link.get_text(strip=True)
        if not title:
            continue

        href = link.get('href', '')
        raw_url = _extract_redirect_target(str(href) if href else '')
        if not raw_url:
            continue

        snippet = result_block.select_one('.result__snippet')
        snippet_text = snippet.get_text(strip=True) if snippet else ''

        parsed_results.append(
            SearchResult(
                title=title,
                url=cast(HttpUrl, raw_url),
                snippet=snippet_text,
            )
        )

        if len(parsed_results) >= MAX_RESULTS:
            break

    return parsed_results


def aggregate_search_content(results: list[SearchResult]) -> str:
    """
    Combine snippets from SearchResult items into a single text blob for structuring.
    """
    return ' '.join(result.snippet.strip() or result.title.strip() for result in results if result.snippet.strip() or result.title.strip())


def _extract_redirect_target(raw_url: str) -> str:
    """DuckDuckGo HTML uses redirect links; extract the actual target if possible."""
    if not raw_url:
        return ''

    parsed = urlparse(raw_url)
    if all([parsed.scheme, parsed.netloc, parsed.netloc != 'duckduckgo.com']):
        return raw_url

    uddg = parse_qs(parsed.query).get('uddg')
    return unquote(uddg[0]) if uddg else raw_url


__all__ = [
    'DUCKDUCKGO_URL',
    'MAX_RESULTS',
    'SEARCH_TIMEOUT',
    '_parse_duckduckgo_results',
    '_extract_redirect_target',
    'aggregate_search_content',
    'search_company_info',
]
