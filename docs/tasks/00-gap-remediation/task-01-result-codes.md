# Task: ResultCode Enum Additions

**Status:** Not Started
**Spec Reference:** [[docs/specs/99-gap-remediation.md#GAP-02]]
**Priority:** P0 - Blocks Phase 8

## Overview

Add missing result codes to `ResultCode` class for company research, gap analysis, and interview prep features.

## Todo

### ResultCode Additions (`models/result.py`)

- [ ] Add company research result codes:
    - `SCRAPE_FAILED = 'SCRAPE_FAILED'`
    - `SEARCH_FAILED = 'SEARCH_FAILED'`
    - `ALL_SOURCES_FAILED = 'ALL_SOURCES_FAILED'`
    - `NO_RESULTS = 'NO_RESULTS'`
    - `TIMEOUT = 'TIMEOUT'`
    - `RESEARCH_COMPLETE = 'RESEARCH_COMPLETE'`
- [ ] Add gap analysis result codes:
    - `GAP_QUESTIONS_GENERATED = 'GAP_QUESTIONS_GENERATED'`
    - `GAP_RESPONSES_SAVED = 'GAP_RESPONSES_SAVED'`
- [ ] Add interview prep result codes:
    - `INTERVIEW_QUESTIONS_GENERATED = 'INTERVIEW_QUESTIONS_GENERATED'`
    - `INTERVIEW_REPORT_GENERATED = 'INTERVIEW_REPORT_GENERATED'`

### Validation

- [ ] Run `uv run ruff format careervp/models/result.py`
- [ ] Run `uv run ruff check careervp/models/result.py --fix`
- [ ] Run `uv run mypy careervp/models/result.py --strict`

### Commit

- [ ] Commit with message: `feat(models): add result codes for Phase 8-12 features`

---

## Codex Implementation Guide

### File Path

`src/backend/careervp/models/result.py`

### Code Changes

Add the following codes to the `ResultCode` class after the existing codes:

```python
class ResultCode:
    """Standard result codes used across the application."""

    # ... existing codes ...

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

### Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format careervp/models/result.py
uv run ruff check careervp/models/result.py --fix
uv run mypy careervp/models/result.py --strict
```

### Commit Instructions

```bash
cd /Users/yitzchak/Documents/dev/careervp
git add src/backend/careervp/models/result.py
git commit -m "feat(models): add result codes for Phase 8-12 features

- Add company research codes (SCRAPE_FAILED, SEARCH_FAILED, etc.)
- Add gap analysis codes (GAP_QUESTIONS_GENERATED, GAP_RESPONSES_SAVED)
- Add interview prep codes (INTERVIEW_QUESTIONS_GENERATED, etc.)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Acceptance Criteria

- [ ] All new result codes added
- [ ] ResultCode class passes mypy --strict
- [ ] Existing tests still pass
