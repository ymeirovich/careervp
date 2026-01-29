# Task 8.6: Company Research Tests

**Status:** Not Started
**Spec Reference:** [[docs/specs/02-company-research.md]]
**Priority:** P0

## Overview

Create comprehensive unit tests for all company research components: web scraper, web search, research logic, and handler. All tests must mock external dependencies.

## Todo

### Test Files to Create

- [ ] `tests/unit/test_web_scraper.py`
- [ ] `tests/unit/test_web_search.py`
- [ ] `tests/unit/test_company_research.py`
- [ ] `tests/unit/test_company_research_handler.py`

### Web Scraper Tests (`test_web_scraper.py`)

- [ ] `test_scrape_url_success` - Mock successful HTTP response
- [ ] `test_scrape_url_timeout` - Mock timeout exception
- [ ] `test_scrape_url_http_error` - Mock 404/403 responses
- [ ] `test_extract_text_from_html` - Test HTML parsing
- [ ] `test_extract_text_removes_scripts` - Verify script/style removal
- [ ] `test_count_words` - Test word counting

### Web Search Tests (`test_web_search.py`)

- [ ] `test_search_company_info_success` - Mock successful search
- [ ] `test_search_company_info_timeout` - Mock timeout
- [ ] `test_search_company_info_no_results` - Mock empty results
- [ ] `test_parse_duckduckgo_results` - Test HTML parsing
- [ ] `test_aggregate_search_content` - Test snippet aggregation

### Company Research Logic Tests (`test_company_research.py`)

- [ ] `test_research_company_scrape_success` - Full scrape path
- [ ] `test_research_company_scrape_insufficient_fallback_to_search` - <200 words triggers search
- [ ] `test_research_company_search_fallback_success` - Search path works
- [ ] `test_research_company_llm_fallback` - Both fail, use LLM
- [ ] `test_research_company_all_fail` - All sources fail gracefully
- [ ] `test_research_source_attribution` - Verify source is set correctly
- [ ] `test_confidence_score_calculation` - Verify scores per source

### Handler Tests (`test_company_research_handler.py`)

- [ ] `test_handler_success` - Valid request returns 200
- [ ] `test_handler_invalid_request` - Missing company_name returns 400
- [ ] `test_handler_partial_content` - Fallback used returns 206
- [ ] `test_handler_service_unavailable` - All fail returns 503
- [ ] `test_handler_metrics_logged` - Verify metrics are emitted

### Mocking Requirements

- **NEVER** make real HTTP requests
- Mock `httpx.AsyncClient` for web requests
- Mock `LLMClient` / `get_llm_router()` for LLM calls
- Use `pytest-asyncio` for async tests

### Validation

- [ ] Run `uv run pytest tests/unit/test_web_scraper.py -v`
- [ ] Run `uv run pytest tests/unit/test_web_search.py -v`
- [ ] Run `uv run pytest tests/unit/test_company_research.py -v`
- [ ] Run `uv run pytest tests/unit/test_company_research_handler.py -v`
- [ ] Run `uv run pytest tests/unit/test_company_research*.py tests/unit/test_web_*.py -v --cov=careervp/logic/company_research --cov=careervp/logic/utils/web_scraper --cov=careervp/logic/utils/web_search`

### Commit

- [ ] Commit with message: `test(company-research): add comprehensive unit tests`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `tests/unit/test_web_scraper.py` | Web scraper unit tests |
| `tests/unit/test_web_search.py` | Web search unit tests |
| `tests/unit/test_company_research.py` | Research logic tests |
| `tests/unit/test_company_research_handler.py` | Handler tests |

### Test Patterns

```python
"""Unit tests for web scraper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from careervp.logic.utils.web_scraper import (
    count_words,
    extract_text_from_html,
    scrape_url,
)
from careervp.models.result import ResultCode


@pytest.mark.asyncio
async def test_scrape_url_success() -> None:
    """Test successful URL scraping."""
    mock_response = MagicMock()
    mock_response.text = "<html><body><p>Company content here</p></body></html>"
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        result = await scrape_url("https://example.com/about")

        assert result.success is True
        assert result.data is not None
        assert "Company content" in result.data


@pytest.mark.asyncio
async def test_scrape_url_timeout() -> None:
    """Test timeout handling."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.side_effect = httpx.TimeoutException("Timeout")
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        result = await scrape_url("https://example.com/about")

        assert result.success is False
        assert result.code == ResultCode.TIMEOUT


def test_extract_text_from_html() -> None:
    """Test HTML text extraction."""
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

    assert "Main content here" in text
    assert "alert" not in text  # Script removed
    assert "Navigation" not in text  # Nav removed


def test_count_words() -> None:
    """Test word counting."""
    assert count_words("one two three") == 3
    assert count_words("") == 0
    assert count_words("word") == 1
```

### Research Logic Test Pattern

```python
"""Unit tests for company research logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from careervp.logic.company_research import research_company
from careervp.models.company import CompanyResearchRequest, ResearchSource
from careervp.models.result import Result, ResultCode


@pytest.fixture
def sample_request() -> CompanyResearchRequest:
    return CompanyResearchRequest(
        company_name="Acme Corp",
        domain="acme.com",
        job_posting_text="We are looking for a software engineer...",
    )


@pytest.mark.asyncio
async def test_research_company_scrape_success(sample_request: CompanyResearchRequest) -> None:
    """Test successful scrape path returns WEBSITE_SCRAPE source."""
    rich_content = " ".join(["word"] * 250)  # 250 words

    with patch(
        "careervp.logic.company_research._try_website_scrape",
        new_callable=AsyncMock,
    ) as mock_scrape:
        mock_scrape.return_value = Result(success=True, data=rich_content)

        with patch(
            "careervp.logic.company_research._structure_raw_content",
            new_callable=AsyncMock,
        ) as mock_structure:
            # ... setup mock_structure

            result = await research_company(sample_request)

            assert result.success is True
            mock_scrape.assert_called_once()
```

### Handler Test Pattern

```python
"""Unit tests for company research handler."""

from __future__ import annotations

import json
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from careervp.handlers.company_research_handler import lambda_handler
from careervp.models.company import CompanyResearchResult, ResearchSource
from careervp.models.result import Result


def test_handler_success() -> None:
    """Test successful research request."""
    event = {
        "body": json.dumps({"company_name": "Acme Corp"}),
    }
    context = MagicMock()

    mock_result = CompanyResearchResult(
        company_name="Acme Corp",
        overview="A great company",
        values=["Innovation"],
        source=ResearchSource.WEBSITE_SCRAPE,
        # ... other fields
    )

    with patch(
        "careervp.handlers.company_research_handler.research_company",
        new_callable=AsyncMock,
    ) as mock_research:
        mock_research.return_value = Result(success=True, data=mock_result)

        response = lambda_handler(event, context)

        assert response["statusCode"] == HTTPStatus.OK.value
        body = json.loads(response["body"])
        assert body["company_name"] == "Acme Corp"


def test_handler_invalid_request() -> None:
    """Test missing company_name returns 400."""
    event = {"body": json.dumps({})}
    context = MagicMock()

    response = lambda_handler(event, context)

    assert response["statusCode"] == HTTPStatus.BAD_REQUEST.value
```

### Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Run all company research tests
uv run pytest tests/unit/test_web_scraper.py tests/unit/test_web_search.py tests/unit/test_company_research.py tests/unit/test_company_research_handler.py -v

# With coverage
uv run pytest tests/unit/test_company_research*.py tests/unit/test_web_*.py -v \
    --cov=careervp/logic/company_research \
    --cov=careervp/logic/utils/web_scraper \
    --cov=careervp/logic/utils/web_search \
    --cov=careervp/handlers/company_research_handler \
    --cov-report=term-missing
```

### Commit Instructions

```bash
cd /Users/yitzchak/Documents/dev/careervp
git add tests/unit/test_web_scraper.py tests/unit/test_web_search.py tests/unit/test_company_research.py tests/unit/test_company_research_handler.py
git commit -m "test(company-research): add comprehensive unit tests

- Add test_web_scraper.py with HTTP mocking
- Add test_web_search.py with DuckDuckGo mocking
- Add test_company_research.py with all fallback paths
- Add test_company_research_handler.py with Lambda event mocking
- 90%+ coverage for company research module
- No real HTTP/API calls in any test

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Acceptance Criteria

- [ ] 90%+ coverage for company_research.py
- [ ] All fallback paths tested (scrape → search → LLM)
- [ ] No real API/HTTP calls in any test
- [ ] All tests pass with `pytest -v`
- [ ] Tests follow existing patterns in test_vpr_generator.py
