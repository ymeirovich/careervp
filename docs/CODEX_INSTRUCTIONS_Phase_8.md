# Codex Implementation Instructions

## Overview

You are implementing Phase 8 (Company Research) and Gap Remediation tasks for the CareerVP project. Follow these instructions precisely.

---

## Rules (MUST Follow)

### Code Quality Rules

1. **ALWAYS run verification commands after EVERY file change:**
   ```bash
   cd /Users/yitzchak/Documents/dev/careervp/src/backend
   uv run ruff format <file>
   uv run ruff check <file> --fix
   uv run mypy <file> --strict
   ```

2. **Zero errors required** - Do not proceed to the next task until all ruff/mypy errors are resolved.

3. **Follow existing patterns** - Before writing new code, read similar existing files:
   - Models: Read `models/cv.py` and `models/vpr.py` for patterns
   - Handlers: Read `handlers/cv_upload_handler.py` for Lambda patterns
   - Logic: Read `logic/vpr_generator.py` for business logic patterns
   - Tests: Read `tests/unit/test_vpr_generator.py` for test patterns

4. **Use TYPE_CHECKING imports** for circular dependency prevention:
   ```python
   from __future__ import annotations
   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from careervp.models.some_model import SomeModel
   ```

5. **Use Result pattern** for all logic functions:
   ```python
   from careervp.models.result import Result, ResultCode

   def my_function() -> Result[MyType]:
       # Success
       return Result(success=True, data=result, code=ResultCode.SUCCESS)
       # Error
       return Result(success=False, error="message", code=ResultCode.SOME_ERROR)
   ```

6. **NEVER make real HTTP/API calls in tests** - Always mock external dependencies.

### Git Rules

1. **Do NOT commit unless explicitly asked**
2. **Use conventional commit format** when committing:
   ```
   feat(scope): short description

   - Bullet point details
   - More details

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```
3. **Stage specific files** - Never use `git add -A` or `git add .`

### Testing Rules

1. **Run relevant tests after each implementation:**
   ```bash
   uv run pytest tests/unit/test_<module>.py -v
   ```

2. **Target 90%+ coverage** for all new code

3. **Mock all external dependencies:**
   - `httpx.AsyncClient` for HTTP requests
   - `LLMClient` / `get_llm_router()` for AI calls
   - `boto3` / DynamoDB for database calls

---

## Implementation Order

Execute tasks in this exact order:

### Step 1: Gap Remediation - ResultCode (BLOCKING)

**Task:** `docs/tasks/00-gap-remediation/task-01-result-codes.md`

**File:** `src/backend/careervp/models/result.py`

**Action:** Add these codes to the `ResultCode` class:

```python
# Company Research codes (Phase 8)
SCRAPE_FAILED = 'SCRAPE_FAILED'
SEARCH_FAILED = 'SEARCH_FAILED'
ALL_SOURCES_FAILED = 'ALL_SOURCES_FAILED'
NO_RESULTS = 'NO_RESULTS'
TIMEOUT = 'TIMEOUT'
RESEARCH_COMPLETE = 'RESEARCH_COMPLETE'

# Gap Analysis codes (Phase 11)
GAP_QUESTIONS_GENERATED = 'GAP_QUESTIONS_GENERATED'
GAP_RESPONSES_SAVED = 'GAP_RESPONSES_SAVED'

# Interview Prep codes (Phase 12)
INTERVIEW_QUESTIONS_GENERATED = 'INTERVIEW_QUESTIONS_GENERATED'
INTERVIEW_REPORT_GENERATED = 'INTERVIEW_REPORT_GENERATED'
```

**Verify:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format careervp/models/result.py
uv run ruff check careervp/models/result.py --fix
uv run mypy careervp/models/result.py --strict
```

---

### Step 2: Dependencies

**File:** `src/backend/pyproject.toml`

**Action:** Add to `[project.dependencies]`:
```toml
"beautifulsoup4>=4.12.0",
"httpx>=0.27.0",
```

**Verify:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv sync
```

---

### Step 3: Task 8.1 - Company Research Models

**Task:** `docs/tasks/08-company-research/task-01-models.md`

**File:** `src/backend/careervp/models/company.py`

**Create models:**
- `ResearchSource` enum
- `CompanyResearchRequest` model
- `CompanyResearchResult` model
- `SearchResult` model

**Pattern to follow:** `models/vpr.py`

**Verify:**
```bash
uv run ruff format careervp/models/company.py
uv run ruff check careervp/models/company.py --fix
uv run mypy careervp/models/company.py --strict
```

---

### Step 4: Task 8.2 - Web Scraper Utility

**Task:** `docs/tasks/08-company-research/task-02-web-scraper.md`

**File:** `src/backend/careervp/logic/utils/web_scraper.py`

**Implement:**
- `scrape_url(url: str, timeout: float = 10.0) -> Result[str]`
- `extract_text_from_html(html: str) -> str`
- `scrape_company_about_page(domain: str) -> Result[str]`
- `count_words(text: str) -> int`

**Key requirements:**
- Use `httpx.AsyncClient` with async/await
- Set User-Agent header to avoid blocks
- Handle timeouts (10s max)
- Remove `<script>`, `<style>`, `<nav>`, `<header>`, `<footer>` tags

**Verify:**
```bash
uv run ruff format careervp/logic/utils/web_scraper.py
uv run ruff check careervp/logic/utils/web_scraper.py --fix
uv run mypy careervp/logic/utils/web_scraper.py --strict
```

---

### Step 5: Task 8.3 - Web Search Fallback

**Task:** `docs/tasks/08-company-research/task-03-web-search.md`

**File:** `src/backend/careervp/logic/utils/web_search.py`

**Implement:**
- `search_company_info(company_name: str) -> Result[list[SearchResult]]`
- `_parse_duckduckgo_results(html: str) -> list[SearchResult]`
- `aggregate_search_content(results: list[SearchResult]) -> str`

**Key requirements:**
- Use DuckDuckGo HTML endpoint: `https://html.duckduckgo.com/html/`
- POST request with `q` parameter
- Parse results with BeautifulSoup
- Return max 5 results

**Verify:**
```bash
uv run ruff format careervp/logic/utils/web_search.py
uv run ruff check careervp/logic/utils/web_search.py --fix
uv run mypy careervp/logic/utils/web_search.py --strict
```

---

### Step 6: Task 8.4 - Company Research Logic

**Task:** `docs/tasks/08-company-research/task-04-research-logic.md`

**File:** `src/backend/careervp/logic/company_research.py`

**Implement:**
- `research_company(request: CompanyResearchRequest) -> Result[CompanyResearchResult]`
- `_try_website_scrape(request: CompanyResearchRequest) -> Result[str]`
- `_try_web_search(company_name: str) -> Result[str]`
- `_try_llm_fallback(request: CompanyResearchRequest) -> Result[CompanyResearchResult]`
- `_structure_raw_content(...) -> Result[CompanyResearchResult]`

**Fallback chain:**
```
1. Website scrape (if >= 200 words) → Return with WEBSITE_SCRAPE source
2. Web search (if >= 200 words) → Return with WEB_SEARCH source
3. LLM fallback → Return with LLM_FALLBACK source
```

**Key requirements:**
- Use `TaskMode.TEMPLATE` for Haiku LLM calls
- Track source for transparency
- Calculate confidence_score based on source

**Verify:**
```bash
uv run ruff format careervp/logic/company_research.py
uv run ruff check careervp/logic/company_research.py --fix
uv run mypy careervp/logic/company_research.py --strict
```

---

### Step 7: Task 8.5 - Company Research Handler

**Task:** `docs/tasks/08-company-research/task-05-handler.md`

**File:** `src/backend/careervp/handlers/company_research_handler.py`

**Implement:**
- `lambda_handler(event: dict, context: LambdaContext) -> dict`
- `_map_result_code_to_status(code: ResultCode) -> HTTPStatus`
- `_build_response(status_code: HTTPStatus, body: dict) -> dict`

**Pattern to follow:** `handlers/cv_upload_handler.py`

**Powertools decorators required:**
```python
@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
```

**HTTP status mapping:**
| ResultCode | HTTP Status |
|------------|-------------|
| SUCCESS | 200 |
| INVALID_INPUT | 400 |
| SCRAPE_FAILED | 206 |
| ALL_SOURCES_FAILED | 503 |
| TIMEOUT | 504 |

**Verify:**
```bash
uv run ruff format careervp/handlers/company_research_handler.py
uv run ruff check careervp/handlers/company_research_handler.py --fix
uv run mypy careervp/handlers/company_research_handler.py --strict
```

---

### Step 8: Task 8.6 - Unit Tests

**Task:** `docs/tasks/08-company-research/task-06-tests.md`

**Files:**
- `tests/unit/test_web_scraper.py`
- `tests/unit/test_web_search.py`
- `tests/unit/test_company_research.py`
- `tests/unit/test_company_research_handler.py`

**Test scenarios required:**

**Web Scraper Tests:**
- `test_scrape_url_success` - Mock successful HTTP
- `test_scrape_url_timeout` - Mock timeout
- `test_scrape_url_http_error` - Mock 404/403
- `test_extract_text_from_html` - Test parsing
- `test_count_words` - Test word counting

**Web Search Tests:**
- `test_search_company_info_success`
- `test_search_company_info_timeout`
- `test_search_company_info_no_results`

**Research Logic Tests:**
- `test_research_company_scrape_success`
- `test_research_company_scrape_insufficient_fallback_to_search`
- `test_research_company_llm_fallback`
- `test_research_company_all_fail`

**Handler Tests:**
- `test_handler_success`
- `test_handler_invalid_request`
- `test_handler_service_unavailable`

**Mocking pattern:**
```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_scrape_url_success() -> None:
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = MagicMock(text="<html>content</html>")
        mock_instance.__aenter__.return_value = mock_instance
        mock_client.return_value = mock_instance

        result = await scrape_url("https://example.com")
        assert result.success is True
```

**Verify:**
```bash
uv run pytest tests/unit/test_web_scraper.py tests/unit/test_web_search.py tests/unit/test_company_research.py tests/unit/test_company_research_handler.py -v
```

---

### Step 9: Task 8.7 - CDK Integration

**Task:** `docs/tasks/08-company-research/task-07-cdk-integration.md`

**Files:**
- `infra/careervp/constants.py`
- `infra/careervp/api_construct.py`

**Add to constants.py:**
```python
COMPANY_RESEARCH_LAMBDA = "CompanyResearch"
GW_RESOURCE_COMPANY_RESEARCH = "company-research"
```

**Add to api_construct.py:**
1. Create API resource: `api_resource.add_resource(constants.GW_RESOURCE_COMPANY_RESEARCH)`
2. Add `_add_company_research_lambda_integration()` method
3. Add Lambda to monitoring list

**Lambda config:**
- Memory: 512 MB
- Timeout: 60 seconds
- Handler: `careervp.handlers.company_research_handler.lambda_handler`

**Verify:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/infra
cdk synth
```

---

## Final Verification

After all tasks complete, run full test suite:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# All unit tests
uv run pytest tests/unit/ -v --tb=short

# With coverage
uv run pytest tests/unit/ --cov=careervp --cov-report=term-missing

# Type checking
uv run mypy careervp --strict

# Linting
uv run ruff check careervp/
uv run ruff format --check careervp/
```

---

## File Reference

| Task | File Path |
|------|-----------|
| ResultCode | `src/backend/careervp/models/result.py` |
| Models | `src/backend/careervp/models/company.py` |
| Web Scraper | `src/backend/careervp/logic/utils/web_scraper.py` |
| Web Search | `src/backend/careervp/logic/utils/web_search.py` |
| Research Logic | `src/backend/careervp/logic/company_research.py` |
| Handler | `src/backend/careervp/handlers/company_research_handler.py` |
| Tests | `src/backend/tests/unit/test_*.py` |
| CDK Constants | `infra/careervp/constants.py` |
| CDK API | `infra/careervp/api_construct.py` |

---

## Error Recovery

If you encounter errors:

1. **Import errors** - Check if the module is in `__init__.py`
2. **Type errors** - Use `from __future__ import annotations` and TYPE_CHECKING
3. **Test failures** - Ensure all external calls are mocked
4. **CDK synth errors** - Check BUILD_FOLDER path exists

---

## Do NOT

- Do NOT skip verification commands
- Do NOT commit without being asked
- Do NOT make real HTTP calls in tests
- Do NOT modify files outside the specified paths
- Do NOT add features not specified in tasks
- Do NOT add comments to code you didn't write
