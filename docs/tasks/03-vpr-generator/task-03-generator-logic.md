# Task 03: VPR Generator Logic

**Status:** Pending
**Spec Reference:** [[docs/specs/03-vpr-generator.md]]
**Depends On:** Task 01 (Models), Task 02 (DAL), Task 04 (Prompt)

## Overview

Implement the core VPR generation logic using Sonnet 4.5 via the LLM Router. This module orchestrates: prompt building, LLM invocation, response parsing, and FVS validation.

## Todo

### Core Logic Implementation

- [ ] Create `src/backend/careervp/logic/vpr_generator.py`.
- [ ] Implement `generate_vpr(request: VPRRequest, user_cv: UserCV) -> Result[VPRResponse]`.
- [ ] Implement `_build_prompt(user_cv: UserCV, request: VPRRequest) -> str` (uses Prompt Library).
- [ ] Implement `_parse_llm_response(response: str) -> VPR` (structured output parsing).
- [ ] Implement `_calculate_word_count(vpr: VPR) -> int`.

### FVS Integration

- [ ] Import and use `FVSValidator` from `careervp/logic/fvs_validator.py`.
- [ ] Validate IMMUTABLE fields (dates, titles, companies) against input CV.
- [ ] Return `Result` with `FVS_HALLUCINATION_DETECTED` if validation fails.

### LLM Router Integration

- [ ] Use `LLMClient` with `TaskMode.STRATEGIC` (Sonnet 4.5).
- [ ] Track token usage and calculate cost.
- [ ] Handle LLM errors gracefully with Result pattern.

### Validation

- [ ] Run `uv run ruff format src/backend/careervp/logic/vpr_generator.py`.
- [ ] Run `uv run ruff check --fix src/backend/careervp/logic/vpr_generator.py`.
- [ ] Run `uv run mypy src/backend/careervp/logic/vpr_generator.py --strict`.

### Commit

- [ ] Commit with message: `feat(vpr): implement VPR generator logic with Sonnet 4.5`.

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/logic/vpr_generator.py` | Core VPR generation logic |
| `src/backend/careervp/logic/utils/llm_client.py` | LLM Router (existing) |
| `src/backend/careervp/logic/fvs_validator.py` | FVS validation (existing) |
| `src/backend/tests/unit/test_vpr_generator.py` | Unit tests with mocked LLM |

### Key Implementation Details

```python
"""
VPR Generator - Core logic for Value Proposition Report generation.
Per docs/specs/03-vpr-generator.md and docs/features/CareerVP Prompt Library.md.

Uses Sonnet 4.5 via LLM Router (TaskMode.STRATEGIC).
"""

import time
from typing import TYPE_CHECKING

from careervp.logic.fvs_validator import FVSValidator
from careervp.logic.utils.llm_client import LLMClient, TaskMode
from careervp.models.cv import UserCV
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import (
    EvidenceItem,
    GapStrategy,
    TokenUsage,
    VPR,
    VPRRequest,
    VPRResponse,
)

if TYPE_CHECKING:
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler


def generate_vpr(
    request: VPRRequest,
    user_cv: UserCV,
    dal: 'DynamoDalHandler',
) -> Result[VPRResponse]:
    """
    Generate a Value Proposition Report for a job application.

    Args:
        request: VPR generation request with job posting and optional gap responses.
        user_cv: Parsed CV facts (from CV Parser).
        dal: Data access layer for persistence.

    Returns:
        Result[VPRResponse] with generated VPR or error details.

    FVS Rules Applied:
        - IMMUTABLE: Dates, company names, job titles from CV cannot be fabricated.
        - VERIFIABLE: Skills/achievements must exist in CV or gap_responses.
        - FLEXIBLE: Executive summary, strategic framing allowed creative liberty.
    """
    start_time = time.perf_counter()

    # 1. Build prompt from Prompt Library template
    prompt = _build_prompt(user_cv, request)

    # 2. Invoke LLM via Router (Sonnet 4.5 for strategic tasks)
    llm_client = LLMClient()
    llm_result = llm_client.invoke(
        prompt=prompt,
        task_mode=TaskMode.STRATEGIC,
        max_tokens=4000,
        temperature=0.7,
    )

    if not llm_result.success:
        return Result(
            success=False,
            error=llm_result.error,
            code=ResultCode.LLM_API_ERROR,
        )

    # 3. Parse structured response
    try:
        vpr = _parse_llm_response(
            response=llm_result.data.content,
            application_id=request.application_id,
            user_id=request.user_id,
            language=request.job_posting.language,
        )
    except ValueError as e:
        return Result(
            success=False,
            error=f'Failed to parse LLM response: {e}',
            code=ResultCode.INVALID_INPUT,
        )

    # 4. FVS Validation - verify IMMUTABLE facts against CV
    # FVS_COMMENT: Validating dates, companies, titles from user_cv.experiences
    fvs = FVSValidator()
    fvs_result = fvs.validate_vpr_against_cv(vpr, user_cv)

    if not fvs_result.success:
        return Result(
            success=False,
            error=fvs_result.error,
            code=ResultCode.FVS_HALLUCINATION_DETECTED,
        )

    # 5. Calculate metrics
    vpr.word_count = _calculate_word_count(vpr)
    generation_time_ms = int((time.perf_counter() - start_time) * 1000)

    # 6. Build token usage
    token_usage = TokenUsage(
        input_tokens=llm_result.data.input_tokens,
        output_tokens=llm_result.data.output_tokens,
        cost_usd=llm_result.data.cost_usd,
        model=llm_result.data.model,
    )

    # 7. Persist VPR
    dal.save_vpr(vpr)

    # 8. Return success response
    return Result(
        success=True,
        data=VPRResponse(
            success=True,
            vpr=vpr,
            token_usage=token_usage,
            generation_time_ms=generation_time_ms,
        ),
        code=ResultCode.VPR_GENERATED,
    )
```

### Result Pattern Enforcement

All functions return `Result[T]` - no naked exceptions escape to caller:

```python
# Good - Result pattern
if not llm_result.success:
    return Result(success=False, error=llm_result.error, code=ResultCode.LLM_API_ERROR)

# Bad - naked exception (DO NOT DO THIS)
raise Exception("LLM failed")
```

### Pytest Commands

```bash
# Run VPR generator tests
cd src/backend && uv run pytest tests/unit/test_vpr_generator.py -v

# Run with coverage
cd src/backend && uv run pytest tests/unit/test_vpr_generator.py -v --cov=careervp/logic/vpr_generator

# Run all logic tests
cd src/backend && uv run pytest tests/unit/test_*.py -k "vpr or fvs" -v
```

### Zero-Hallucination Checklist

- [ ] Add `# FVS_COMMENT:` source-code comments marking where IMMUTABLE fields are validated.
- [ ] `_parse_llm_response()` extracts evidence_matrix items that reference CV facts by index/id.
- [ ] All dates in VPR evidence must trace to `user_cv.experiences[].start_date` or `end_date`.
- [ ] All company names must match `user_cv.experiences[].company_name` exactly.
- [ ] All job titles must match `user_cv.experiences[].job_title` exactly.
- [ ] Gap responses can introduce NEW verifiable facts (user-provided evidence).

### FVS Source-Code Comment Requirements

```python
# Required comments in vpr_generator.py:

# FVS_COMMENT: IMMUTABLE - dates from user_cv.experiences cannot be fabricated
# FVS_COMMENT: IMMUTABLE - company_name from user_cv.experiences must match exactly
# FVS_COMMENT: IMMUTABLE - job_title from user_cv.experiences must match exactly
# FVS_COMMENT: VERIFIABLE - skills must exist in user_cv.skills or gap_responses
# FVS_COMMENT: FLEXIBLE - executive_summary allows creative framing
```

### Acceptance Criteria

- [ ] `generate_vpr()` returns `Result[VPRResponse]` in all paths.
- [ ] FVS validation blocks hallucinated dates/titles/companies.
- [ ] Token usage and cost tracked correctly.
- [ ] Word count calculated (target: 1,500-2,000 words).
- [ ] All mypy --strict checks pass.
- [ ] Unit tests mock LLM and verify Result pattern.
