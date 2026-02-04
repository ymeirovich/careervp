"""
Web scraping utilities for company research.
Primary path per docs/specs/02-company-research.md and Task 8.2 instructions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final, Iterable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from careervp.models.result import Result, ResultCode

USER_AGENT: Final[str] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
SCRAPE_TIMEOUT: Final[float] = 10.0
MIN_CONTENT_WORDS: Final[int] = 200
ABOUT_PATHS: Final[tuple[str, ...]] = ('', 'about', 'about-us', 'company', 'company/about', 'who-we-are')


async def scrape_url(url: str, timeout: float = SCRAPE_TIMEOUT) -> Result[str]:
    """
    Fetch HTML content from a URL using httpx with defensive error handling.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers={'User-Agent': USER_AGENT})
            response.raise_for_status()
            return Result(success=True, data=response.text, code=ResultCode.SUCCESS)
    except httpx.TimeoutException:
        return Result(success=False, error=f'Timeout fetching {url}', code=ResultCode.TIMEOUT)
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response else 'unknown'
        return Result(success=False, error=f'HTTP {status_code} from {url}', code=ResultCode.SCRAPE_FAILED)
    except httpx.RequestError as exc:
        return Result(success=False, error=f'HTTP request error for {url}: {exc}', code=ResultCode.SCRAPE_FAILED)
    except Exception as exc:  # pragma: no cover - safety net
        return Result(success=False, error=str(exc), code=ResultCode.SCRAPE_FAILED)


def extract_text_from_html(html: str) -> str:
    """
    Extract meaningful text content from HTML by removing navigation, scripts, and styles.
    """
    soup = BeautifulSoup(html, 'html.parser')

    for element in soup(['script', 'style', 'nav', 'header', 'footer', 'noscript', 'aside', 'form']):
        element.decompose()

    text = soup.get_text(separator='\n')
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return '\n'.join(lines)


def count_words(text: str) -> int:
    """Count words in a text blob."""
    if not text:
        return 0
    return len(text.split())


async def scrape_company_about_page(base_url: str, on_success: Callable[[str], None] | None = None) -> Result[str]:
    """
    Attempt to scrape the most relevant "About" style page for a company.
    Tries a set of known path variants and returns the first successful extraction.
    """
    candidate_urls = list(_build_candidate_urls(base_url))
    if not candidate_urls:
        return Result(success=False, error='Invalid base URL for scraping', code=ResultCode.INVALID_INPUT)

    last_error: str | None = None
    for candidate in candidate_urls:
        result = await scrape_url(candidate)
        if not result.success or not result.data:
            last_error = result.error or 'Scrape failed'
            continue

        extracted_text = extract_text_from_html(result.data)
        if extracted_text:
            if on_success:
                on_success(candidate)
            return Result(success=True, data=extracted_text, code=ResultCode.SUCCESS)
        last_error = 'No textual content extracted'

    return Result(
        success=False,
        error=last_error or 'Unable to locate company about page',
        code=ResultCode.SCRAPE_FAILED,
    )


def _build_candidate_urls(base_url: str) -> Iterable[str]:
    """Yield normalized URLs to attempt scraping."""
    normalized_bases = _normalize_base_urls(base_url)
    for base in normalized_bases:
        for path in ABOUT_PATHS:
            yield _join_url(base, path)


def _normalize_base_urls(raw_url: str) -> list[str]:
    """Normalize the incoming URL/domain into concrete base URLs."""
    trimmed = raw_url.strip()
    if not trimmed:
        return []

    parsed = urlparse(trimmed if '://' in trimmed else f'https://{trimmed}')
    if not parsed.netloc:
        return []

    base_https = f'https://{parsed.netloc}'
    base_http = f'http://{parsed.netloc}'

    bases = [base_https]
    if base_http not in bases:
        bases.append(base_http)
    if parsed.scheme in {'http', 'https'}:
        explicit = f'{parsed.scheme}://{parsed.netloc}'
        if explicit not in bases:
            bases.insert(0, explicit)

    seen: set[str] = set()
    unique_bases: list[str] = []
    for candidate in bases:
        if candidate not in seen:
            seen.add(candidate)
            unique_bases.append(candidate.rstrip('/'))
    return unique_bases


def _join_url(base: str, path: str) -> str:
    """Join base URL with path, ensuring a single slash separator."""
    if not path:
        return base
    return urljoin(f'{base.rstrip("/")}/', path.lstrip('/'))


__all__ = [
    'ABOUT_PATHS',
    'MIN_CONTENT_WORDS',
    'SCRAPE_TIMEOUT',
    'scrape_url',
    'scrape_company_about_page',
    'extract_text_from_html',
    'count_words',
]
