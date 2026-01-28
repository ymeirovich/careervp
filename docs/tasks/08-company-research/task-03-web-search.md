# Task 8.3: Web Search Fallback

**Status:** Not Started
**Spec Reference:** [[docs/specs/02-company-research.md]]
**Priority:** P0

## Overview

Implement web search fallback for when website scraping returns insufficient content (<200 words). Uses DuckDuckGo HTML API as the primary search method.

## Todo

### Web Search Implementation (`logic/utils/web_search.py`)

- [ ] Create `logic/utils/web_search.py` file
- [ ] Implement `search_company_info(company_name: str) -> Result[list[SearchResult]]`:
    - Build search query: `"[Company Name] about culture values mission"`
    - Use DuckDuckGo HTML search endpoint
    - Parse search result snippets
    - Return top 3-5 results
- [ ] Implement `_parse_duckduckgo_results(html: str) -> list[SearchResult]`:
    - Extract title, URL, and snippet from each result
    - Handle malformed HTML gracefully
- [ ] Implement `aggregate_search_content(results: list[SearchResult]) -> str`:
    - Combine snippets into coherent text
    - Return aggregated content for structuring
- [ ] Add error handling for:
    - Search service unavailable
    - Rate limiting
    - No results found

### SearchResult Model (if not in task-01)

Ensure `SearchResult` model exists in `models/company.py`:
```python
class SearchResult(BaseModel):
    title: str
    url: HttpUrl
    snippet: str
```

### Validation

- [ ] Run `uv run ruff format careervp/logic/utils/web_search.py`
- [ ] Run `uv run ruff check careervp/logic/utils/web_search.py --fix`
- [ ] Run `uv run mypy careervp/logic/utils/web_search.py --strict`

### Commit

- [ ] Commit with message: `feat(company-research): add web search fallback`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/logic/utils/web_search.py` | Web search fallback utility |

### DuckDuckGo Search Implementation

```python
"""Web search fallback for company research."""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING

import httpx
from bs4 import BeautifulSoup

from careervp.models.company import SearchResult
from careervp.models.result import Result, ResultCode

if TYPE_CHECKING:
    pass

SEARCH_TIMEOUT = 15.0  # seconds
MAX_RESULTS = 5

# DuckDuckGo HTML search endpoint
DUCKDUCKGO_URL = "https://html.duckduckgo.com/html/"


async def search_company_info(company_name: str) -> Result[list[SearchResult]]:
    """Search for company information using DuckDuckGo."""
    query = f"{company_name} about culture values mission"

    try:
        async with httpx.AsyncClient(timeout=SEARCH_TIMEOUT) as client:
            response = await client.post(
                DUCKDUCKGO_URL,
                data={"q": query},
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; CareerVP/1.0)",
                },
            )
            response.raise_for_status()

            results = _parse_duckduckgo_results(response.text)
            if not results:
                return Result(
                    success=False,
                    error="No search results found",
                    code=ResultCode.NO_RESULTS,
                )

            return Result(success=True, data=results[:MAX_RESULTS], code=ResultCode.SUCCESS)

    except httpx.TimeoutException:
        return Result(success=False, error="Search timeout", code=ResultCode.TIMEOUT)
    except Exception as e:
        return Result(success=False, error=str(e), code=ResultCode.SEARCH_FAILED)


def _parse_duckduckgo_results(html: str) -> list[SearchResult]:
    """Parse DuckDuckGo HTML search results."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResult] = []

    for result in soup.select(".result"):
        title_elem = result.select_one(".result__title")
        link_elem = result.select_one(".result__url")
        snippet_elem = result.select_one(".result__snippet")

        if title_elem and link_elem:
            title = title_elem.get_text(strip=True)
            # DuckDuckGo uses redirect URLs, extract actual URL
            url = link_elem.get("href", "")
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            if url and title:
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                ))

    return results


def aggregate_search_content(results: list[SearchResult]) -> str:
    """Combine search result snippets into aggregated content."""
    snippets = [r.snippet for r in results if r.snippet]
    return " ".join(snippets)
```

### Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format careervp/logic/utils/web_search.py
uv run ruff check careervp/logic/utils/web_search.py --fix
uv run mypy careervp/logic/utils/web_search.py --strict
```

### Commit Instructions

```bash
cd /Users/yitzchak/Documents/dev/careervp
git add src/backend/careervp/logic/utils/web_search.py
git commit -m "feat(company-research): add web search fallback

- Add search_company_info() using DuckDuckGo HTML API
- Add _parse_duckduckgo_results() for HTML parsing
- Add aggregate_search_content() for combining snippets
- Handle timeouts and search failures gracefully
- Return top 5 results

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Acceptance Criteria

- [ ] Returns Result[list[SearchResult]] with up to 5 results
- [ ] SearchResult contains title, url, snippet
- [ ] Handles search failures gracefully
- [ ] Max 5 results returned
- [ ] All code passes ruff and mypy --strict
- [ ] No real API calls in unit tests
