# Spec: Company Research (Option D - Hybrid)

## Overview

Company research provides contextual information about the target company to enhance VPR generation, CV tailoring, and cover letter personalization. This is a **V1 required feature**.

## Architecture

```
CompanyResearchRequest → Scrape Company Website → Web Search Fallback → LLM Fallback → CompanyResearchResult
```

## Logic

### Primary Path: Website Scraping

1. Extract company domain from job posting URL or user-provided domain.
2. Scrape the company "About" page using `httpx` + `BeautifulSoup4`.
3. Extract text content, removing navigation, scripts, and styles.
4. If extracted text >= 200 words, proceed to structuring.

### Fallback Path 1: Web Search

**Trigger:** Primary scraping returns < 200 words of usable content.

1. Use MCP tool (`google-search` or `brave-search`) if available.
2. If no MCP tool, fall back to DuckDuckGo HTML API scraping.
3. Search query: `"[Company Name] about culture values mission recent news"`.
4. Aggregate top 3-5 search result snippets.
5. If aggregated content >= 200 words, proceed to structuring.

### Fallback Path 2: LLM Synthesis

**Trigger:** Both scraping and web search return insufficient content (< 200 words combined).

1. Use Claude Haiku 4.5 to extract company context from job posting text.
2. Prompt focuses on inferring company values, culture, and priorities from job description language.
3. Mark result with `source: LLM_FALLBACK` for transparency.

### Structuring

Use Claude Haiku 4.5 (or regex extraction for simple cases) to structure raw text into:

- **Company Overview** (100-200 words)
- **Core Values/Mission** (list of 3-5 values)
- **Current Strategic Priorities** (if detectable)
- **Recent News/Achievements** (last 6 months, if available)
- **Financial Performance** (if public company and data available)

## Output Schema

```python
class ResearchSource(str, Enum):
    WEBSITE_SCRAPE = 'website_scrape'
    WEB_SEARCH = 'web_search'
    LLM_FALLBACK = 'llm_fallback'

class CompanyResearchResult(BaseModel):
    company_name: str
    overview: str  # 100-200 words
    values: list[str]  # 3-5 core values
    mission: str | None
    strategic_priorities: list[str]
    recent_news: list[str]  # Last 6 months
    financial_summary: str | None  # Public companies only
    source: ResearchSource
    source_urls: list[str]  # Attribution
    confidence_score: float  # 0.0-1.0
    research_timestamp: datetime
```

## Constraints

### Budget

- **Target:** < $0.01 per company research
- **Scraping:** ~$0.001 (Lambda compute only)
- **Web Search:** ~$0.001 (Lambda compute only)
- **LLM Fallback:** ~$0.005 (Haiku for basic extraction)

### Performance

- **Timeout:** 60 seconds total
- **Scraping timeout:** 10 seconds per URL
- **Web search timeout:** 15 seconds

### Error Handling

| Scenario | Action |
| -------- | ------ |
| Website blocked/unavailable | Trigger web search fallback |
| Web search returns no results | Trigger LLM fallback |
| All sources fail | Return partial result with low confidence |
| Rate limited | Exponential backoff, max 3 retries |

## Integration Points

### VPR Generator

Company research is called **before** VPR generation:

```python
# In vpr_generator.py
company_context = await research_company(CompanyResearchRequest(
    company_name=job_posting.company_name,
    domain=extract_domain(job_posting.source_url),
    job_posting_url=job_posting.source_url,
))

vpr = await generate_vpr(
    request=vpr_request,
    user_cv=user_cv,
    company_context=company_context,  # Injected into prompt
)
```

### Cover Letter Generator

Company research enables personalized opening paragraphs:

```python
# In cover_letter_prompt.py
if company_context.source != ResearchSource.LLM_FALLBACK:
    prompt += f"""
    Company Context (use for personalization):
    - Mission: {company_context.mission}
    - Values: {', '.join(company_context.values)}
    - Recent News: {company_context.recent_news[0] if company_context.recent_news else 'N/A'}
    """
```

## API Endpoint

```yaml
POST /company-research
Request:
  company_name: string (required)
  domain: string (optional)
  job_posting_url: string (optional)
Response:
  200: CompanyResearchResult
  206: Partial content (low confidence result)
  400: Invalid input
  503: All research sources failed
```

## Testing Requirements

### Unit Tests

1. **Successful scrape path** - Mock HTTP response with rich content
2. **Web search fallback** - Mock scrape failure, successful search
3. **LLM fallback** - Mock both scrape and search failure
4. **Timeout handling** - Mock slow responses
5. **Content threshold** - Verify 200-word minimum triggers fallback

### Mocking

- `httpx.AsyncClient` for web requests
- MCP tool calls for search
- `LLMClient` for Haiku extraction
- **NEVER** make real HTTP requests in tests

## Codex Implementation Guidelines

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/models/company.py` | Data models |
| `src/backend/careervp/logic/utils/web_scraper.py` | Website scraping |
| `src/backend/careervp/logic/utils/web_search.py` | Search fallback |
| `src/backend/careervp/logic/company_research.py` | Orchestration |
| `src/backend/careervp/handlers/company_research_handler.py` | Lambda handler |
| `tests/unit/test_company_research.py` | Unit tests |
| `tests/unit/test_web_scraper.py` | Scraper tests |

### Dependencies to Add

```toml
# pyproject.toml
dependencies = [
    # ... existing
    "beautifulsoup4>=4.12.0",
    "httpx>=0.27.0",
]
```

### Verification Commands

```bash
cd src/backend
uv run ruff format careervp/logic/company_research.py careervp/logic/utils/web_scraper.py
uv run ruff check careervp/logic/company_research.py careervp/logic/utils/web_scraper.py --fix
uv run mypy careervp/logic/company_research.py careervp/logic/utils/web_scraper.py --strict
uv run pytest tests/unit/test_company_research.py tests/unit/test_web_scraper.py -v
```

## Acceptance Criteria

- [ ] Website scraping extracts meaningful content from company "About" pages
- [ ] Web search fallback triggers when scraping returns < 200 words
- [ ] LLM fallback triggers when both scraping and search fail
- [ ] Result includes `source` field for transparency
- [ ] Budget constraint (< $0.01) is respected
- [ ] All tests pass with mocked dependencies
- [ ] Zero ruff/mypy errors
