"""
Unit tests for careervp.logic.utils.web_scraper.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from careervp.logic.utils.web_scraper import (
    MIN_CONTENT_WORDS,
    count_words,
    extract_text_from_html,
    scrape_company_about_page,
    scrape_url,
)
from careervp.models.result import Result, ResultCode


def test_scrape_url_success() -> None:
    """scrape_url should return HTML when request succeeds."""

    async def run() -> None:
        mock_response = MagicMock()
        mock_response.text = '<html><body><p>Company content here</p></body></html>'
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch('careervp.logic.utils.web_scraper.httpx.AsyncClient', return_value=mock_client):
            result = await scrape_url('https://example.com/about')

        assert result.success is True
        assert '<p>Company content here</p>' in (result.data or '')

    asyncio.run(run())


def test_scrape_url_timeout() -> None:
    """scrape_url should return TIMEOUT result when httpx raises TimeoutException."""

    async def run() -> None:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException('timeout')
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch('careervp.logic.utils.web_scraper.httpx.AsyncClient', return_value=mock_client):
            result = await scrape_url('https://example.com/about')

        assert result.success is False
        assert result.code == ResultCode.TIMEOUT

    asyncio.run(run())


def test_scrape_company_about_page_uses_callback() -> None:
    """Verify scrape_company_about_page extracts text and invokes success callback with URL."""

    async def run() -> None:
        html_content = '<html><body><p>{}</p></body></html>'.format(' '.join(['value'] * MIN_CONTENT_WORDS))

        with patch('careervp.logic.utils.web_scraper.scrape_url', new_callable=AsyncMock) as mock_scrape_url:
            mock_scrape_url.return_value = Result(success=True, data=html_content, code=ResultCode.SUCCESS)
            visited: list[str] = []

            result = await scrape_company_about_page('https://example.com', on_success=visited.append)

        assert result.success is True
        assert visited, 'Expected callback to capture the successful URL'

    asyncio.run(run())


def test_extract_text_from_html_removes_scripts() -> None:
    """extract_text_from_html should drop navigation/script elements."""
    html = """
    <html>
        <head><script>alert('x')</script></head>
        <body>
            <nav>Navigation</nav>
            <main><p>Main content here</p></main>
            <footer>Footer</footer>
        </body>
    </html>
    """
    text = extract_text_from_html(html)

    assert 'Main content here' in text
    assert 'Navigation' not in text
    assert 'alert' not in text


def test_count_words() -> None:
    """count_words should return the number of whitespace-delimited tokens."""
    assert count_words('one two three') == 3
    assert count_words('') == 0
    assert count_words('single') == 1
