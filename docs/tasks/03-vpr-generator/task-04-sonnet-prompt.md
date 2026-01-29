# Task 04: VPR Prompt Integration

**Status:** Complete
**Spec Reference:** [[docs/specs/03-vpr-generator.md]]
**Depends On:** Task 01 (Models)

## Overview

Integrate the existing `VPR_GENERATION_PROMPT` from the Prompt Library into the VPR generator. The prompt already exists in `docs/features/CareerVP Prompt Library.md` (lines 128-259).

**Note:** Do NOT recreate the prompt. Extract and integrate the existing one.

## Todo

### Prompt Module Creation

- [ ] Create `src/backend/careervp/logic/prompts/__init__.py`.
- [ ] Create `src/backend/careervp/logic/prompts/vpr_prompt.py`.
- [ ] Extract `VPR_GENERATION_PROMPT` constant from Prompt Library.
- [ ] Implement `build_vpr_prompt(user_cv: UserCV, request: VPRRequest) -> str`.

### Prompt Placeholders

- [ ] `{cv_facts_json}` - Serialized UserCV facts.
- [ ] `{job_requirements_json}` - Serialized JobPosting.
- [ ] `{gap_responses_json}` - Serialized GapResponse list.
- [ ] `{company_research_json}` - Serialized CompanyContext (optional).
- [ ] `{previous_insights_json}` - Empty dict for MVP.

### Anti-AI Detection Integration

- [ ] Extract `BANNED_WORDS` list from Prompt Library.
- [ ] Add post-generation check for banned words (warning only for MVP).

### Validation

- [ ] Run `uv run ruff format src/backend/careervp/logic/prompts/`.
- [ ] Run `uv run ruff check --fix src/backend/careervp/logic/prompts/`.
- [ ] Run `uv run mypy src/backend/careervp/logic/prompts/vpr_prompt.py --strict`.

### Commit

- [ ] Commit with message: `feat(vpr): integrate VPR prompt from Prompt Library`.

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/logic/prompts/vpr_prompt.py` | VPR prompt template and builder |
| `docs/features/CareerVP Prompt Library.md` | Source of VPR_GENERATION_PROMPT (lines 128-259) |
| `src/backend/tests/unit/test_vpr_prompt.py` | Unit tests for prompt building |

### Key Implementation Details

```python
"""
VPR Prompt Builder - Integrates VPR_GENERATION_PROMPT from Prompt Library.
Per docs/features/CareerVP Prompt Library.md (lines 128-259).

DO NOT modify the core prompt. Extract as-is and parameterize.
"""

import json
from typing import Any

from careervp.models.cv import UserCV
from careervp.models.vpr import VPRRequest

# Extracted from docs/features/CareerVP Prompt Library.md lines 128-259
VPR_GENERATION_PROMPT = """You are an expert career strategist creating a Value Proposition Report (VPR) for a job application.

CRITICAL REQUIREMENTS:
... (extract full prompt from Prompt Library)
"""

# Anti-AI Detection - Banned words from Prompt Library
BANNED_WORDS: list[str] = [
    'leverage',
    'delve into',
    'landscape',
    'robust',
    'streamline',
    'utilize',
    'paradigm shift',
    'game-changer',
    'synergy',
    'spearheading',
    'cutting-edge',
    'best practices',
]


def build_vpr_prompt(user_cv: UserCV, request: VPRRequest) -> str:
    """
    Build the VPR generation prompt with all required context.

    Args:
        user_cv: Parsed CV facts from CV Parser.
        request: VPR request with job posting and optional gap responses.

    Returns:
        Formatted prompt string ready for LLM invocation.
    """
    # Serialize CV facts (exclude sensitive fields for prompt)
    cv_facts = _serialize_cv_for_prompt(user_cv)

    # Serialize job requirements
    job_requirements = request.job_posting.model_dump(mode='json')

    # Serialize gap responses
    gap_responses = [gr.model_dump(mode='json') for gr in request.gap_responses]

    # Serialize company context (or empty dict)
    company_research = (
        request.company_context.model_dump(mode='json')
        if request.company_context
        else {}
    )

    # MVP: No previous insights yet
    previous_insights: dict[str, Any] = {}

    return VPR_GENERATION_PROMPT.format(
        cv_facts_json=json.dumps(cv_facts, indent=2),
        job_requirements_json=json.dumps(job_requirements, indent=2),
        gap_responses_json=json.dumps(gap_responses, indent=2),
        company_research_json=json.dumps(company_research, indent=2),
        previous_insights_json=json.dumps(previous_insights, indent=2),
    )


def _serialize_cv_for_prompt(user_cv: UserCV) -> dict[str, Any]:
    """
    Serialize UserCV for prompt, excluding raw file content.

    FVS_COMMENT: IMMUTABLE fields (dates, titles, companies) preserved exactly.
    """
    data = user_cv.model_dump(mode='json')
    # Remove large/sensitive fields not needed in prompt
    data.pop('raw_text', None)
    data.pop('file_key', None)
    return data


def check_anti_ai_patterns(content: str) -> list[str]:
    """
    Check generated content for AI detection red flags.

    Returns:
        List of banned words found in content.
    """
    found: list[str] = []
    content_lower = content.lower()

    for word in BANNED_WORDS:
        if word in content_lower:
            found.append(word)

    return found
```

### Result Pattern Enforcement

This module is a pure function (no side effects). It returns strings/lists, not Results. The caller (vpr_generator.py) wraps errors in Result pattern.

### Pytest Commands

```bash
# Run prompt tests
cd src/backend && uv run pytest tests/unit/test_vpr_prompt.py -v

# Verify prompt builds correctly
cd src/backend && uv run python -c "from careervp.logic.prompts.vpr_prompt import build_vpr_prompt; print('OK')"
```

### Zero-Hallucination Checklist

- [ ] `VPR_GENERATION_PROMPT` extracted verbatim from Prompt Library.
- [ ] `_serialize_cv_for_prompt()` preserves IMMUTABLE fields exactly.
- [ ] `BANNED_WORDS` list matches Prompt Library Anti-AI section.
- [ ] No prompt modifications that could introduce hallucination vectors.

### Prompt Extraction Steps

1. Open `docs/features/CareerVP Prompt Library.md`.
2. Locate `VPR_GENERATION_PROMPT` (lines 128-259).
3. Copy the full triple-quoted string.
4. Paste into `vpr_prompt.py` as constant.
5. Verify placeholders match: `{cv_facts_json}`, `{job_requirements_json}`, etc.

### Acceptance Criteria

- [ ] `VPR_GENERATION_PROMPT` constant matches Prompt Library exactly.
- [ ] `build_vpr_prompt()` returns valid prompt string.
- [ ] `BANNED_WORDS` list contains all Anti-AI terms from spec.
- [ ] All mypy --strict checks pass.
- [ ] Unit tests verify prompt placeholder substitution.
