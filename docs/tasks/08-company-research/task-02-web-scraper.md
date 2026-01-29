# Task 8.2: Web Scraper Utility

**Status:** Not Started
**Spec Reference:** [[docs/specs/02-company-research.md]]
**Priority:** P0

## Overview

Implement web scraping utilities for extracting company information from websites. This is the primary research path before fallbacks.

## Todo

### Dependencies

- [ ] Add `beautifulsoup4>=4.12.0` to pyproject.toml
- [ ] Add `httpx>=0.27.0` to pyproject.toml
- [ ] Run `uv sync` to install dependencies

### Web Scraper Implementation (`logic/utils/web_scraper.py`)

- [ ] Create `logic/utils/web_scraper.py` file
- [ ] Implement `scrape_url(url: str, timeout: float = 10.0) -> Result[str]`:
    - Use `httpx.AsyncClient` for HTTP requests
    - Set realistic User-Agent header
    - Handle timeouts (10s max per request)
    - Return raw HTML content
- [ ] Implement `extract_text_from_html(html: str) -> str`:
    - Use BeautifulSoup4 to parse HTML
    - Remove `<script>`, `<style>`, `<nav>`, `<header>`, `<footer>` tags
    - Extract meaningful text content
    - Preserve paragraph structure
- [ ] Implement `scrape_company_about_page(url: str) -> Result[str]`:
    - Attempt to find and scrape "/about", "/about-us", "/company" pages
    - Return extracted text content
    - Handle 404/403 errors gracefully
- [ ] Implement `count_words(text: str) -> int`:
    - Count words in extracted text
    - Used to determine if fallback is needed (<200 words)
- [ ] Add error handling for:
    - Connection timeouts
    - SSL errors
    - HTTP 4xx/5xx errors
    - Blocked/rate-limited requests

### Validation

- [ ] Run `uv run ruff format careervp/logic/utils/web_scraper.py`
- [ ] Run `uv run ruff check careervp/logic/utils/web_scraper.py --fix`
- [ ] Run `uv run mypy careervp/logic/utils/web_scraper.py --strict`

### Commit

- [ ] Commit with message: `feat(company-research): add web scraper utility`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/logic/utils/web_scraper.py` | Web scraping utilities |
| `src/backend/pyproject.toml` | Add beautifulsoup4, httpx dependencies |

### Key Implementation Details

```python
"""Web scraping utilities for company research."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx
from bs4 import BeautifulSoup

from careervp.models.result import Result, ResultCode

if TYPE_CHECKING:
    pass

# Realistic browser User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

SCRAPE_TIMEOUT = 10.0  # seconds
MIN_CONTENT_WORDS = 200


async def scrape_url(url: str, timeout: float = SCRAPE_TIMEOUT) -> Result[str]:
    """Fetch HTML content from URL with timeout and error handling."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            return Result(success=True, data=response.text, code=ResultCode.SUCCESS)
    except httpx.TimeoutException:
        return Result(success=False, error=f"Timeout fetching {url}", code=ResultCode.TIMEOUT)
    except httpx.HTTPStatusError as e:
        return Result(success=False, error=f"HTTP {e.response.status_code} from {url}", code=ResultCode.SCRAPE_FAILED)
    except Exception as e:
        return Result(success=False, error=str(e), code=ResultCode.SCRAPE_FAILED)


def extract_text_from_html(html: str) -> str:
    """Extract meaningful text content from HTML, removing navigation/scripts."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted elements
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        tag.decompose()

    # Get text with proper spacing
    text = soup.get_text(separator=" ", strip=True)

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return " ".join(chunk for chunk in chunks if chunk)


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())
```

### About Page Discovery

Try these common paths in order:
1. `/about`
2. `/about-us`
3. `/company`
4. `/company/about`
5. `/who-we-are`

### Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format careervp/logic/utils/web_scraper.py
uv run ruff check careervp/logic/utils/web_scraper.py --fix
uv run mypy careervp/logic/utils/web_scraper.py --strict
```

### Commit Instructions

```bash
cd /Users/yitzchak/Documents/dev/careervp
git add src/backend/careervp/logic/utils/web_scraper.py src/backend/pyproject.toml
git commit -m "feat(company-research): add web scraper utility

- Add scrape_url() with httpx and timeout handling
- Add extract_text_from_html() with BeautifulSoup
- Add scrape_company_about_page() with common path discovery
- Add count_words() for content threshold checking
- Handle timeouts, HTTP errors, and blocked sites gracefully

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Acceptance Criteria

- [ ] Handles timeout gracefully (returns Result with error)
- [ ] Extracts text content from HTML
- [ ] Removes scripts/styles/navigation elements
- [ ] Uses realistic User-Agent to avoid blocks
- [ ] All code passes ruff and mypy --strict
- [ ] No real HTTP calls in unit tests (mock httpx)
