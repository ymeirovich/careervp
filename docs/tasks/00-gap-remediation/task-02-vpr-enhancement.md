# Task: VPR Generator Enhancement for Gap Responses

**Status:** Not Started
**Spec Reference:** [[docs/specs/99-gap-remediation.md#GAP-01]]
**Priority:** P0 - Implement when Phase 11 starts

## Overview

Update the VPR Generator to accept Gap Analysis responses as input, enabling richer value proposition reports with user-provided evidence.

## Prerequisites

- Phase 11 models (GapResponse) must be created first
- This task should be completed alongside Phase 11 Task 11.1

## Todo

### VPR Generator Updates (`logic/vpr_generator.py`)

- [ ] Add import for `GapResponse` model (when created)
- [ ] Update `generate_vpr()` signature:
    ```python
    def generate_vpr(
        request: VPRRequest,
        user_cv: UserCV,
        dal: DynamoDalHandler,
        gap_responses: list[GapResponse] | None = None,
        previous_responses: list[GapResponse] | None = None,
    ) -> Result[VPRResponse]:
    ```
- [ ] Update `build_vpr_prompt()` call to include gap responses
- [ ] Maintain backward compatibility (None defaults)

### VPR Prompt Updates (`logic/prompts/vpr_prompt.py`)

- [ ] Add `_format_gap_responses(responses: list[GapResponse] | None) -> str` helper
- [ ] Update `build_vpr_prompt()` to accept gap responses parameter
- [ ] Add gap evidence section to prompt template

### Prompt Enhancement

```python
def _format_gap_responses(responses: list[GapResponse] | None) -> str:
    """Format gap analysis responses for inclusion in VPR prompt."""
    if not responses:
        return ""

    lines = [
        "",
        "## Gap Analysis Evidence",
        "The candidate provided the following additional context:",
        "",
    ]
    for response in responses:
        lines.append(f"**Q:** {response.question}")
        lines.append(f"**A:** {response.answer}")
        lines.append("")

    lines.append("Use this evidence to strengthen the Value Proposition Report.")
    return "\n".join(lines)
```

### Test Updates (`tests/unit/test_vpr_generator.py`)

- [ ] Add `test_generate_vpr_with_gap_responses` - Verify gap responses included in prompt
- [ ] Add `test_generate_vpr_without_gap_responses` - Backward compatibility
- [ ] Add `test_generate_vpr_with_previous_responses` - Historical data enrichment

### Validation

- [ ] Run `uv run ruff format careervp/logic/vpr_generator.py careervp/logic/prompts/vpr_prompt.py`
- [ ] Run `uv run ruff check careervp/logic/vpr_generator.py careervp/logic/prompts/vpr_prompt.py --fix`
- [ ] Run `uv run mypy careervp/logic/vpr_generator.py careervp/logic/prompts/vpr_prompt.py --strict`
- [ ] Run `uv run pytest tests/unit/test_vpr_generator.py -v`

### Commit

- [ ] Commit with message: `feat(vpr): add gap_responses parameter to generate_vpr`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/logic/vpr_generator.py` | Update function signature |
| `src/backend/careervp/logic/prompts/vpr_prompt.py` | Add gap response formatting |
| `src/backend/tests/unit/test_vpr_generator.py` | Add new tests |

### Current Function Signature

```python
def generate_vpr(request: VPRRequest, user_cv: UserCV, dal: DynamoDalHandler) -> Result[VPRResponse]:
```

### Target Function Signature

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from careervp.models.gap_analysis import GapResponse

def generate_vpr(
    request: VPRRequest,
    user_cv: UserCV,
    dal: DynamoDalHandler,
    gap_responses: list[GapResponse] | None = None,
    previous_responses: list[GapResponse] | None = None,
) -> Result[VPRResponse]:
    """
    Generate a Value Proposition Report (spec lines 91-104).

    Args:
        request: VPR generation request
        user_cv: Parsed user CV
        dal: Database access layer
        gap_responses: Gap analysis responses for current application
        previous_responses: Gap/interview responses from previous applications
    """
```

### Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format careervp/logic/vpr_generator.py careervp/logic/prompts/vpr_prompt.py
uv run ruff check careervp/logic/vpr_generator.py careervp/logic/prompts/vpr_prompt.py --fix
uv run mypy careervp/logic/vpr_generator.py careervp/logic/prompts/vpr_prompt.py --strict
uv run pytest tests/unit/test_vpr_generator.py -v
```

### Commit Instructions

```bash
cd /Users/yitzchak/Documents/dev/careervp
git add src/backend/careervp/logic/vpr_generator.py src/backend/careervp/logic/prompts/vpr_prompt.py tests/unit/test_vpr_generator.py
git commit -m "feat(vpr): add gap_responses parameter to generate_vpr

- Add gap_responses and previous_responses parameters
- Add _format_gap_responses() helper for prompt building
- Maintain backward compatibility with None defaults
- Add tests for gap response integration

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Acceptance Criteria

- [ ] Function signature updated with new parameters
- [ ] Prompt includes gap analysis evidence section when provided
- [ ] Backward compatible (works without gap responses)
- [ ] All existing tests continue to pass
- [ ] New tests cover gap response scenarios
