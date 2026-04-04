# Implementation Plan: P4 — ATS Scoring 100pt Scale

**Spec**: `spec_P4_ats_scoring_100pt.yaml`
**Priority**: P4 (depends on P2, P3)
**Owner**: backend

---

## Problem Summary

Current ATS scoring uses a 0-10 float scale with constants:
- `TARGET_ATS_SCORE = 8.0` (80% target)
- `ANTI_AI_MIN_SCORE = 9.0` (90% anti-AI detection)

The spec mandates changing to a cleaner 0-100 integer scale for better UX (percentage intuition).

---

## Implementation Steps

### Step 1: Update backend constants

**File**: `src/backend/careervp/logic/cv_tailoring.py`

Change:
```python
TARGET_ATS_SCORE = 80  # Was 8.0
ANTI_AI_MIN_SCORE = 90  # Was 9.0
```

### Step 2: Update ATS scoring formula

**File**: `src/backend/careervp/logic/cv_tailoring.py`

Rewrite `calculate_ats_score()` to output 0-100 integer:
- Keyword density: 0-40 points
- Formatting: 0-20 points
- Length compliance: 0-20 points
- Impact metrics: 0-20 points

### Step 3: Update response model

**File**: `src/backend/careervp/models/cv_tailoring_models.py`

Update `ATSVerification`:
```python
class ATSVerification(BaseModel):
    ats_score: int = Field(default=0, ge=0, le=100)  # Was float with ge=0, le=10
    keyword_score: int = Field(default=0, ge=0, le=40)
    formatting_score: int = Field(default=0, ge=0, le=20)
    length_score: int = Field(default=0, ge=0, le=20)
    impact_score: int = Field(default=0, ge=0, le=20)
```

### Step 4: Update CV Tailoring Logic

**File**: `src/backend/careervp/logic/cv_tailoring_logic.py`

Update `TailoredCVResponse`:
```python
class TailoredCVResponse(BaseModel):
    # ... existing fields ...
    ats_score: int = Field(default=0, ge=0, le=100)  # Was float
```

### Step 5: Run tests

Run tests in `test_P4_ats_scoring_100pt.yaml` to verify changes.

---

## Acceptance Criteria

| ID | Description | Verification |
|----|-------------|--------------|
| AC-P4-01 | ats_score is 0-100 integer | Type check |
| AC-P4-02 | TARGET_ATS_SCORE = 80 | Constant check |
| AC-P4-03 | All scores sum to 100 | Formula verification |
| AC-P4-04 | Tests pass | pytest |

---

## Files to Modify

| File | Changes |
|------|---------|
| `cv_tailoring.py` | Update constants, rewrite formula |
| `cv_tailoring_models.py` | Update ATSVerification |
| `cv_tailoring_logic.py` | Update TailoredCVResponse |
| `test_ats_scoring.py` | Create/update tests |

---

## Notes

- Frontend changes deferred (UI task)
- Keep backward-compatible API response format
- 0-100 more intuitive for users (percentage)