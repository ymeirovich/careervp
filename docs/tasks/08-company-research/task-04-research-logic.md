# Task 8.4: Company Research Logic

**Status:** Not Started
**Spec Reference:** [[docs/specs/02-company-research.md]]
**Priority:** P0

## Overview

Implement the main company research orchestration logic that coordinates scraping, web search fallback, and LLM fallback paths.

## Todo

### Company Research Logic (`logic/company_research.py`)

- [ ] Create `logic/company_research.py` file
- [ ] Implement `research_company(request: CompanyResearchRequest) -> Result[CompanyResearchResult]`:
    - Orchestrate the three-tier fallback strategy
    - Track which research path was used
    - Return structured CompanyResearchResult
- [ ] Implement `_try_website_scrape(request: CompanyResearchRequest) -> Result[str]`:
    - Attempt to scrape company "About" page
    - Return raw text content if >= 200 words
    - Return failure Result if insufficient content
- [ ] Implement `_try_web_search(company_name: str) -> Result[str]`:
    - Search for company information
    - Aggregate search snippets
    - Return if >= 200 words total
- [ ] Implement `_try_llm_fallback(request: CompanyResearchRequest) -> Result[CompanyResearchResult]`:
    - Use Haiku 4.5 to extract company context from job posting
    - Only called when scrape + search both fail
    - Mark result with LLM_FALLBACK source
- [ ] Implement `_structure_raw_content(raw_text: str, source: ResearchSource, source_urls: list[str]) -> Result[CompanyResearchResult]`:
    - Use Haiku 4.5 to structure raw text into CompanyResearchResult
    - Extract overview, values, mission, etc.
    - Calculate confidence score based on content quality

### Fallback Chain Logic

```
1. Try website scrape
   └─ If >= 200 words → Structure and return (source: WEBSITE_SCRAPE)
   └─ If < 200 words → Continue to step 2

2. Try web search
   └─ If >= 200 words → Structure and return (source: WEB_SEARCH)
   └─ If < 200 words → Continue to step 3

3. Try LLM fallback (extract from job posting text)
   └─ Return with source: LLM_FALLBACK
   └─ Set confidence_score < 0.5
```

### Budget Constraints

- Total research cost: < $0.01 per company
- Web scraping: ~$0.001 (Lambda compute only)
- Web search: ~$0.001 (Lambda compute only)
- LLM structuring (Haiku): ~$0.002-0.003
- LLM fallback (Haiku): ~$0.003-0.005

### Validation

- [ ] Run `uv run ruff format careervp/logic/company_research.py`
- [ ] Run `uv run ruff check careervp/logic/company_research.py --fix`
- [ ] Run `uv run mypy careervp/logic/company_research.py --strict`

### Commit

- [ ] Commit with message: `feat(company-research): add research orchestration logic`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/logic/company_research.py` | Main research orchestration |

### Key Implementation

```python
"""Company research orchestration logic."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from careervp.logic.utils.llm_client import TaskMode, get_llm_router
from careervp.logic.utils.web_scraper import (
    count_words,
    extract_text_from_html,
    scrape_company_about_page,
)
from careervp.logic.utils.web_search import aggregate_search_content, search_company_info
from careervp.models.company import (
    CompanyResearchRequest,
    CompanyResearchResult,
    ResearchSource,
)
from careervp.models.result import Result, ResultCode

if TYPE_CHECKING:
    pass

MIN_CONTENT_WORDS = 200
RESEARCH_TIMEOUT = 60.0  # Total timeout for all research


async def research_company(request: CompanyResearchRequest) -> Result[CompanyResearchResult]:
    """
    Research company using three-tier fallback strategy.

    1. Website scraping (primary)
    2. Web search (fallback 1)
    3. LLM synthesis from job posting (fallback 2)
    """
    source_urls: list[str] = []

    # Step 1: Try website scrape
    if request.domain:
        scrape_result = await _try_website_scrape(request)
        if scrape_result.success and scrape_result.data:
            raw_text = scrape_result.data
            if count_words(raw_text) >= MIN_CONTENT_WORDS:
                source_urls.append(f"https://{request.domain}/about")
                return await _structure_raw_content(
                    raw_text=raw_text,
                    company_name=request.company_name,
                    source=ResearchSource.WEBSITE_SCRAPE,
                    source_urls=source_urls,
                )

    # Step 2: Try web search
    search_result = await _try_web_search(request.company_name)
    if search_result.success and search_result.data:
        raw_text = search_result.data
        if count_words(raw_text) >= MIN_CONTENT_WORDS:
            return await _structure_raw_content(
                raw_text=raw_text,
                company_name=request.company_name,
                source=ResearchSource.WEB_SEARCH,
                source_urls=source_urls,
            )

    # Step 3: LLM fallback
    if request.job_posting_text:
        return await _try_llm_fallback(request)

    # All sources failed
    return Result(
        success=False,
        error="All research sources failed",
        code=ResultCode.ALL_SOURCES_FAILED,
    )
```

### LLM Structuring Prompt

```python
STRUCTURE_PROMPT = """
Extract structured company information from the following text.

Text:
{raw_text}

Return a JSON object with these fields:
- overview: 100-200 word company description
- values: list of 3-5 core values
- mission: company mission statement (if found)
- strategic_priorities: list of current strategic focuses
- recent_news: list of recent achievements/news (if any)
- financial_summary: brief financial info (for public companies only, null otherwise)

Return ONLY valid JSON, no other text.
"""
```

### Confidence Score Calculation

| Source | Base Score | Adjustments |
| ------ | ---------- | ----------- |
| WEBSITE_SCRAPE | 0.9 | -0.1 if < 300 words |
| WEB_SEARCH | 0.7 | -0.1 per missing field |
| LLM_FALLBACK | 0.4 | Max 0.5 regardless of content |

### Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format careervp/logic/company_research.py
uv run ruff check careervp/logic/company_research.py --fix
uv run mypy careervp/logic/company_research.py --strict
```

### Commit Instructions

```bash
cd /Users/yitzchak/Documents/dev/careervp
git add src/backend/careervp/logic/company_research.py
git commit -m "feat(company-research): add research orchestration logic

- Add research_company() with three-tier fallback strategy
- Add _try_website_scrape() for primary research path
- Add _try_web_search() for fallback path 1
- Add _try_llm_fallback() for fallback path 2
- Add _structure_raw_content() with Haiku LLM
- Track research source for transparency
- Calculate confidence score based on source quality

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Acceptance Criteria

- [ ] Returns CompanyResearchResult with source attribution
- [ ] Handles all fallback scenarios correctly
- [ ] Logs which research path was used
- [ ] Respects budget constraint (< $0.01 per company)
- [ ] All code passes ruff and mypy --strict
- [ ] Uses TaskMode.TEMPLATE for Haiku calls
