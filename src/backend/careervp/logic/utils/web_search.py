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

    try:
        async with httpx.AsyncClient(timeout=SEARCH_TIMEOUT) as client:
            response = await client.post(
                DUCKDUCKGO_URL,
                data={'q': query},
                headers={'User-Agent': USER_AGENT},
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        return Result(success=False, error='Search timeout', code=ResultCode.TIMEOUT)
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response else 'unknown'
        return Result(success=False, error=f'Search HTTP {status_code}', code=ResultCode.SEARCH_FAILED)
    except httpx.RequestError as exc:
        return Result(success=False, error=f'Search request error: {exc}', code=ResultCode.SEARCH_FAILED)
    except Exception as exc:  # pragma: no cover - safety net
        return Result(success=False, error=str(exc), code=ResultCode.SEARCH_FAILED)

    results = _parse_duckduckgo_results(response.text)
    if not results:
        return Result(success=False, error='No search results found', code=ResultCode.NO_RESULTS)

    return Result(success=True, data=results[:MAX_RESULTS], code=ResultCode.SUCCESS)


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
        raw_href = link.get('href')
        raw_url = raw_href if isinstance(raw_href, str) else ''
        resolved_url = _extract_redirect_target(raw_url)
        snippet_el = result_block.select_one('.result__snippet')
        snippet = snippet_el.get_text(strip=True) if snippet_el else ''

        if not title or not resolved_url:
            continue

        resolved_http_url = cast(HttpUrl, resolved_url)

        parsed_results.append(
            SearchResult(
                title=title,
                url=resolved_http_url,
                snippet=snippet,
            )
        )

        if len(parsed_results) >= MAX_RESULTS:
            break

    return parsed_results


def aggregate_search_content(results: list[SearchResult]) -> str:
    """
    Combine snippets from SearchResult items into a single text blob for structuring.
    """
    snippets = [result.snippet.strip() for result in results if result.snippet.strip()]
    if snippets:
        return ' '.join(snippets)
    titles = [result.title.strip() for result in results if result.title.strip()]
    return ' '.join(titles)


def _extract_redirect_target(raw_url: str) -> str:
    """DuckDuckGo HTML uses redirect links; extract the actual target if possible."""
    if not raw_url:
        return ''

    parsed = urlparse(raw_url)
    if parsed.scheme and parsed.netloc and parsed.netloc != 'duckduckgo.com':
        return raw_url

    params = parse_qs(parsed.query)
    uddg = params.get('uddg')
    if uddg and uddg[0]:
        return unquote(uddg[0])

    return raw_url


__all__ = [
    'DUCKDUCKGO_URL',
    'MAX_RESULTS',
    'SEARCH_TIMEOUT',
    '_parse_duckduckgo_results',
    '_extract_redirect_target',
    'aggregate_search_content',
    'search_company_info',
]
