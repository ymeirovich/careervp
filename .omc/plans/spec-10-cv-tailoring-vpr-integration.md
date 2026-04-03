# Spec 10 Implementation Plan: CV Tailoring VPR Integration

## Overview
Thread optional VPR parameter through CV tailoring call stack. When user provides vpr_id in request, fetch VPR and inject it as strategic guide in tailoring prompt.

## Files to Modify

### 1. cv_tailoring_models.py
**Change:** Add vpr_id field to TailorCVRequest
```python
# After idempotency_key field
vpr_id: str | None = None
```

### 2. cv_tailoring_logic.py
**Change:** Fetch VPR and pass to tailor_cv()
- After line 50 (master_cv fetch): Add VPR fetch block
- Add vpr=vpr to tailor_cv() call (line 76)
- Import VPR (use TYPE_CHECKING guard)

### 3. cv_tailoring.py
**Changes:**
- Add vpr: VPR | None = None to both @overload stubs (lines 189, 201) and implementation (line 212)
- Add vpr to _tailor_cv_legacy() call
- Add vpr to _tailor_cv_legacy() signature
- Add vpr: VPR | None = None parameter
- Pass vpr to build_tailoring_prompt() call

### 4. cv_tailoring_prompt.py
**Changes:**
- Add vpr: VPR | None = None to build_user_prompt() signature
- Add VPR injection block:
```python
if vpr is not None:
    import json
    sections.append('# VPR Strategic Guide')
    sections.append(
        'Use this VPR to prioritize CV content. '
        'Expand bullet points for roles/skills that map to unique_strengths. '
        'Align professional_summary with differentiators.positioning_statement.\n\n'
        + json.dumps(vpr.model_dump(mode='json'), indent=2)
    )
```

## VPR Fetch Pattern (in cv_tailoring_logic.py)
```python
# Fetch VPR for strategic guidance (optional — graceful degradation)
vpr: VPR | None = None
if request.vpr_id:
    vpr_result = self.dal.get_vpr(request.vpr_id)
    if vpr_result.success and vpr_result.data is not None:
        vpr = vpr_result.data
    else:
        logger.warning(
            'CV tailoring: VPR not found or fetch failed — proceeding without strategic guide',
            vpr_id=request.vpr_id,
            error=vpr_result.error,
        )
```

## Dependencies
- dal.get_vpr() already exists (spec verified)
- VPR model exists in careervp.models.vpr

## Risks to Mitigate
1. **Circular imports:** Use TYPE_CHECKING guard for VPR import
2. **mypy overloads:** Must add vpr to all three signatures

## Test Strategy
- Existing CV tailoring tests should pass (no regression)
- Can add unit test for VPR injection in prompt

## Order of Implementation
1. cv_tailoring_models.py - Add field
2. cv_tailoring_prompt.py - Add VPR injection (no cascading changes)
3. cv_tailoring.py - Thread parameter through functions
4. cv_tailoring_logic.py - Add VPR fetch and pass to tailor_cv()
5. Verify with ruff, mypy, pytest

## Blockers
None identified. Spec depends on spec 08 (already implemented).