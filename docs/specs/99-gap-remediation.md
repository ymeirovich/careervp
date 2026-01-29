# Spec: Gap Remediation for Phases 1-7

## Overview

This spec documents gaps identified in completed Phases 1-7 that require remediation before or during Phase 8+ implementation.

## Gap Analysis Summary

| Gap ID | Component | Priority | Status |
| ------ | --------- | -------- | ------ |
| GAP-01 | VPR Generator Enhancement | P0 | Not Started |
| GAP-02 | ResultCode Enum Additions | P0 | Not Started |
| GAP-03 | CICD Pipeline | P0 | Not Started |
| GAP-04 | Integration Test Coverage | P1 | Partial |
| GAP-05 | CV Parser Test Coverage | P2 | Partial |

---

## GAP-01: VPR Generator Enhancement

**Priority:** P0 (Blocks Phase 11 - Gap Analysis)
**File:** `src/backend/careervp/logic/vpr_generator.py`
**Spec Reference:** plan.md lines 110-147

### Description

The existing VPR Generator does not accept Gap Analysis responses as input. Per the application workflow, VPR generation should incorporate user responses from Gap Analysis to strengthen the value proposition with evidence.

### Current State

```python
def generate_vpr(request: VPRRequest, user_cv: UserCV, dal: DynamoDalHandler) -> Result[VPRResponse]:
```

### Required Changes

```python
from careervp.models.gap_analysis import GapResponse  # To be created in Phase 11

def generate_vpr(
    request: VPRRequest,
    user_cv: UserCV,
    dal: DynamoDalHandler,
    gap_responses: list[GapResponse] | None = None,         # Current application
    previous_responses: list[GapResponse] | None = None,    # All previous applications
) -> Result[VPRResponse]:
```

### Prompt Enhancement

Add to `vpr_prompt.py`:
```python
def _format_gap_responses(gap_responses: list[GapResponse] | None) -> str:
    if not gap_responses:
        return ""

    lines = ["## Gap Analysis Evidence", "The candidate provided the following additional context:"]
    for response in gap_responses:
        lines.append(f"Q: {response.question}")
        lines.append(f"A: {response.answer}")
    return "\n".join(lines)
```

### Tasks

- [ ] Update `generate_vpr()` signature to accept `gap_responses: list[GapResponse] | None`
- [ ] Update `generate_vpr()` signature to accept `previous_responses: list[GapResponse] | None`
- [ ] Add `_format_gap_responses()` helper in vpr_prompt.py
- [ ] Update VPR prompt to incorporate gap analysis evidence
- [ ] Update unit tests to verify gap response integration
- [ ] Maintain backward compatibility (parameters default to None)

### Verification Commands

```bash
cd src/backend
uv run ruff check careervp/logic/vpr_generator.py --fix
uv run mypy careervp/logic/vpr_generator.py --strict
uv run pytest tests/unit/test_vpr_generator.py -v
```

---

## GAP-02: ResultCode Enum Additions

**Priority:** P0 (Required for Phase 8)
**File:** `src/backend/careervp/models/result.py`

### Description

The current `ResultCode` class is missing codes required for company research and web scraping functionality.

### Current State

ResultCode has basic codes but lacks web-specific error codes.

### Required Additions

```python
class ResultCode:
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

### Tasks

- [ ] Add Phase 8 result codes (SCRAPE_FAILED, SEARCH_FAILED, etc.)
- [ ] Add Phase 11 result codes
- [ ] Add Phase 12 result codes
- [ ] Run ruff/mypy validation

### Verification Commands

```bash
cd src/backend
uv run ruff check careervp/models/result.py --fix
uv run mypy careervp/models/result.py --strict
```

---

## GAP-03: CICD Pipeline

**Priority:** P0 (Required before deployment)
**File:** `.github/workflows/deploy.yml`

### Description

No CICD pipeline exists. GitHub Actions workflow needed for:
- PR validation (lint, typecheck, test, cdk synth)
- Deployment to dev/staging/prod environments

### Required Files

| File | Purpose |
| ---- | ------- |
| `.github/workflows/pr-validation.yml` | PR checks |
| `.github/workflows/deploy.yml` | Deployment workflow |
| `.github/workflows/cdk-diff.yml` | CDK diff on PR |

### PR Validation Workflow

```yaml
name: PR Validation

on:
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: cd src/backend && uv sync
      - run: cd src/backend && uv run ruff check .
      - run: cd src/backend && uv run ruff format --check .

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: cd src/backend && uv sync
      - run: cd src/backend && uv run mypy careervp --strict

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: cd src/backend && uv sync
      - run: cd src/backend && uv run pytest tests/unit/ -v --tb=short

  cdk-synth:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - uses: astral-sh/setup-uv@v4
      - run: npm install -g aws-cdk
      - run: cd infra && uv sync
      - run: cd infra && cdk synth
```

### Deployment Workflow

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-dev:
    runs-on: ubuntu-latest
    environment: dev
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - uses: astral-sh/setup-uv@v4
      - run: cd src/backend && uv sync && uv build
      - run: cd infra && uv sync && cdk deploy --require-approval never
```

### Tasks

- [ ] Create `.github/workflows/pr-validation.yml`
- [ ] Create `.github/workflows/deploy.yml`
- [ ] Add pytest unit test hook to `.pre-commit-config.yaml`
- [ ] Create environment configs (dev, staging, prod)
- [ ] Document required GitHub secrets

---

## GAP-04: Integration Test Coverage

**Priority:** P1
**Directory:** `tests/integration/`

### Description

Limited integration test coverage. Only `test_vpr_e2e.py` exists.

### Required Tests

| Test File | Purpose |
| --------- | ------- |
| `test_cv_upload_e2e.py` | CV upload → parse → store flow |
| `test_full_application_e2e.py` | Complete application workflow |
| `test_company_research_e2e.py` | Company research with real HTTP mocks |

### Tasks

- [ ] Create `test_cv_upload_e2e.py`
- [ ] Expand `test_vpr_e2e.py` coverage
- [ ] Create `test_company_research_e2e.py` after Phase 8

---

## GAP-05: CV Parser Test Coverage

**Priority:** P2
**File:** `tests/unit/test_cv_parser.py`

### Description

CV parser tests exist but coverage is limited to helper functions. Main `parse_cv()` function not fully tested.

### Current Tests

- `test_clean_text_normalizes_whitespace`
- `test_detect_language_returns_hebrew`
- `test_detect_language_defaults_to_english_on_error`
- `test_parse_llm_response_handles_json_code_block`
- `test_parse_llm_response_invalid_json`

### Additional Tests Needed

- [ ] `test_parse_cv_success` - Full parse flow with mocked LLM
- [ ] `test_parse_cv_invalid_file` - Unsupported file format
- [ ] `test_parse_cv_llm_timeout` - LLM timeout handling
- [ ] `test_parse_cv_fvs_validation` - FVS validation on parsed CV
- [ ] `test_parse_cv_hebrew_cv` - Hebrew language support

---

## Implementation Order

1. **GAP-02: ResultCode Additions** - Quick fix, unblocks Phase 8
2. **GAP-01: VPR Generator Enhancement** - Defer until Phase 11 starts
3. **GAP-03: CICD Pipeline** - Implement before first deployment
4. **GAP-04/05: Test Coverage** - Ongoing improvement

## Codex Instructions

When implementing any gap remediation task:

1. Read the existing code first
2. Follow existing patterns in the codebase
3. Run verification commands after every change
4. Mark tasks complete only after all checks pass
5. Commit with conventional commit format

```bash
git commit -m "fix(vpr): add gap_responses parameter to generate_vpr

- Add gap_responses and previous_responses parameters
- Maintain backward compatibility with None defaults
- Update prompt to incorporate gap evidence

Co-Authored-By: Claude <noreply@anthropic.com>"
```
