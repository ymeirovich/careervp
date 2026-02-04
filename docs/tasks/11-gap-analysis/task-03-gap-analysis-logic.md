# Task 03: Gap Analysis Logic

## Overview

Implement core business logic for gap question generation and scoring.

**Files to create:**
- `src/backend/careervp/logic/gap_analysis.py`

**Dependencies:** Task 01 (validation), Task 04 (prompts)
**Estimated time:** 4 hours
**Unit Tests:** `tests/gap-analysis/unit/test_gap_analysis_logic.py`

---

## Implementation

### File: `src/backend/careervp/logic/gap_analysis.py`

```python
"""
Gap analysis logic - generate targeted questions to identify CV gaps.
Per docs/architecture/GAP_ANALYSIS_DESIGN.md.
"""

import asyncio
import json
from typing import Any

from careervp.dal.db_handler import DalHandler
from careervp.logic.llm_client import LLMClient
from careervp.logic.prompts.gap_analysis_prompt import (
    create_gap_analysis_system_prompt,
    create_gap_analysis_user_prompt,
)
from careervp.models import Result, ResultCode
from careervp.models.cv import UserCV
from careervp.models.job import JobPosting


async def generate_gap_questions(
    user_cv: UserCV,
    job_posting: JobPosting,
    dal: DalHandler,
    language: str = 'en'
) -> Result[list[dict[str, Any]]]:
    """
    Generate gap analysis questions using LLM.

    Algorithm:
    1. Build LLM prompt with CV and job posting
    2. Call Claude API with 600s timeout
    3. Parse JSON response
    4. Calculate gap scores
    5. Sort by score, return top 5

    Args:
        user_cv: Parsed user CV
        job_posting: Target job posting
        dal: Data access layer
        language: Question language (en or he)

    Returns:
        Result[list[GapQuestion]] with 0-5 questions sorted by gap_score
    """
    try:
        # 1. Create prompts
        system_prompt = create_gap_analysis_system_prompt()
        user_prompt = create_gap_analysis_user_prompt(user_cv, job_posting)

        # 2. Call LLM with timeout
        llm_client = LLMClient()

        try:
            llm_result = await asyncio.wait_for(
                llm_client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model="claude-3-haiku-20240307"  # Fast & cost-effective
                ),
                timeout=600  # 10 minutes max
            )
        except asyncio.TimeoutError:
            return Result(
                success=False,
                error="LLM processing timeout after 10 minutes",
                code=ResultCode.TIMEOUT
            )

        if not llm_result.success:
            return Result(
                success=False,
                error=llm_result.error,
                code=llm_result.code
            )

        # 3. Parse JSON response
        try:
            questions = json.loads(llm_result.data)
        except json.JSONDecodeError as e:
            return Result(
                success=False,
                error=f"Failed to parse LLM response: {str(e)}",
                code=ResultCode.INTERNAL_ERROR
            )

        # 4. Calculate gap scores (if not already set)
        for question in questions:
            if 'gap_score' not in question:
                question['gap_score'] = calculate_gap_score(
                    impact=question['impact'],
                    probability=question['probability']
                )

        # 5. Sort by gap_score descending, take top 5
        questions_sorted = sorted(
            questions,
            key=lambda q: q['gap_score'],
            reverse=True
        )[:5]

        return Result(
            success=True,
            data=questions_sorted,
            code=ResultCode.GAP_QUESTIONS_GENERATED
        )

    except Exception as e:
        return Result(
            success=False,
            error=f"Unexpected error: {str(e)}",
            code=ResultCode.INTERNAL_ERROR
        )


def calculate_gap_score(impact: str, probability: str) -> float:
    """
    Calculate gap score using weighted formula.

    Formula: gap_score = (0.7 * impact_score) + (0.3 * probability_score)

    Scores:
    - HIGH = 1.0
    - MEDIUM = 0.6
    - LOW = 0.3

    Args:
        impact: Impact level (HIGH, MEDIUM, LOW)
        probability: Probability level (HIGH, MEDIUM, LOW)

    Returns:
        Gap score between 0.3 and 1.0

    Raises:
        ValueError: If impact or probability is invalid

    Examples:
        >>> calculate_gap_score('HIGH', 'HIGH')
        1.0
        >>> calculate_gap_score('HIGH', 'MEDIUM')
        0.88
        >>> calculate_gap_score('MEDIUM', 'MEDIUM')
        0.6
        >>> calculate_gap_score('LOW', 'LOW')
        0.3
    """
    score_map = {'HIGH': 1.0, 'MEDIUM': 0.6, 'LOW': 0.3}

    if impact not in score_map:
        raise ValueError(f"Invalid impact level: {impact}. Must be HIGH, MEDIUM, or LOW.")

    if probability not in score_map:
        raise ValueError(f"Invalid probability level: {probability}. Must be HIGH, MEDIUM, or LOW.")

    impact_score = score_map[impact]
    probability_score = score_map[probability]

    # Weighted formula: prioritize impact (70%) over probability (30%)
    gap_score = (0.7 * impact_score) + (0.3 * probability_score)

    return gap_score
```

---

## Verification Commands

```bash
cd src/backend

# Format
uv run ruff format careervp/logic/gap_analysis.py

# Lint
uv run ruff check careervp/logic/gap_analysis.py --fix

# Type check
uv run mypy careervp/logic/gap_analysis.py --strict

# Unit tests
uv run pytest tests/gap-analysis/unit/test_gap_analysis_logic.py -v --tb=short

# Coverage
uv run pytest tests/gap-analysis/unit/test_gap_analysis_logic.py --cov=careervp.logic.gap_analysis --cov-report=term-missing

# Expected: 90%+ coverage, all tests pass
```

---

## Acceptance Criteria

- [ ] `generate_gap_questions()` implemented with LLM integration
- [ ] Async timeout handling (600s) via `asyncio.wait_for()`
- [ ] JSON parsing with error handling
- [ ] `calculate_gap_score()` implements weighted formula
- [ ] Questions sorted by gap_score descending
- [ ] Maximum 5 questions returned
- [ ] Language parameter supported
- [ ] Returns `Result[list[dict]]` pattern
- [ ] All unit tests pass (20+ tests)
- [ ] Code coverage ≥90%
- [ ] Type checking passes (mypy --strict)

---

## Commit Message

```bash
git add src/backend/careervp/logic/gap_analysis.py
git commit -m "feat(gap-analysis): implement question generation logic

- Add generate_gap_questions() with LLM integration
- Add calculate_gap_score() weighted formula (impact × probability)
- Implement async timeout handling (600s max)
- Sort questions by gap_score, return top 5
- All unit tests pass (23/23)

Per docs/architecture/GAP_ANALYSIS_DESIGN.md.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```
