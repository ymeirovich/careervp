# Task 8.1: CompanyResearch Models Implementation

**Status:** Not Started
**Spec Reference:** [[docs/specs/02-company-research.md]]
**Priority:** P0

## Overview

Create Pydantic models for company research: request model, result model, and supporting enums/types.

## Todo

### CompanyResearch Models (`models/company.py`)

- [ ] Create `models/company.py` file
- [ ] Add `ResearchSource` enum:
    - `WEBSITE_SCRAPE = 'website_scrape'`
    - `WEB_SEARCH = 'web_search'`
    - `LLM_FALLBACK = 'llm_fallback'`
- [ ] Add `CompanyResearchRequest` model with fields:
    - `company_name: str` (required)
    - `domain: str | None` (optional, extracted from job posting URL)
    - `job_posting_url: HttpUrl | None` (optional)
    - `job_posting_text: str | None` (for LLM fallback)
- [ ] Add `CompanyResearchResult` model with fields:
    - `company_name: str`
    - `overview: str` (100-200 words)
    - `values: list[str]` (3-5 core values)
    - `mission: str | None`
    - `strategic_priorities: list[str]`
    - `recent_news: list[str]` (last 6 months)
    - `financial_summary: str | None` (public companies only)
    - `source: ResearchSource`
    - `source_urls: list[str]` (attribution)
    - `confidence_score: float` (0.0-1.0)
    - `research_timestamp: datetime`
- [ ] Add `SearchResult` model for web search results:
    - `title: str`
    - `url: HttpUrl`
    - `snippet: str`

### Validation

- [ ] Run `uv run ruff format careervp/models/company.py`
- [ ] Run `uv run ruff check careervp/models/company.py --fix`
- [ ] Run `uv run mypy careervp/models/company.py --strict`

### Commit

- [ ] Commit with message: `feat(company-research): add CompanyResearch Pydantic models`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/models/company.py` | CompanyResearchRequest, CompanyResearchResult, ResearchSource, SearchResult |

### Model Patterns

Follow existing patterns from `models/cv.py` and `models/vpr.py`:
- Use `Annotated` with `Field` for descriptions
- Include proper `model_config` for JSON serialization
- Use `datetime` from standard library (not pydantic)

### Example Implementation

```python
from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl


class ResearchSource(str, Enum):
    """Source of company research data."""
    WEBSITE_SCRAPE = 'website_scrape'
    WEB_SEARCH = 'web_search'
    LLM_FALLBACK = 'llm_fallback'


class CompanyResearchRequest(BaseModel):
    """Request to research a company."""
    company_name: Annotated[str, Field(description="Name of the company to research")]
    domain: Annotated[str | None, Field(default=None, description="Company domain (e.g., example.com)")]
    job_posting_url: Annotated[HttpUrl | None, Field(default=None, description="URL of the job posting")]
    job_posting_text: Annotated[str | None, Field(default=None, description="Job posting text for LLM fallback")]
```

### Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format careervp/models/company.py
uv run ruff check careervp/models/company.py --fix
uv run mypy careervp/models/company.py --strict
```

### Commit Instructions

```bash
cd /Users/yitzchak/Documents/dev/careervp
git add src/backend/careervp/models/company.py
git commit -m "feat(company-research): add CompanyResearch Pydantic models

- Add ResearchSource enum (website_scrape, web_search, llm_fallback)
- Add CompanyResearchRequest model with company_name, domain, job_posting_url
- Add CompanyResearchResult model with overview, values, mission, source
- Add SearchResult model for web search results

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Acceptance Criteria

- [ ] All models pass ruff and mypy --strict checks
- [ ] Models follow existing patterns in models/cv.py
- [ ] ResearchSource enum covers all fallback scenarios
- [ ] Type annotations are complete with Annotated and Field descriptions
- [ ] CompanyResearchResult includes confidence_score for transparency
