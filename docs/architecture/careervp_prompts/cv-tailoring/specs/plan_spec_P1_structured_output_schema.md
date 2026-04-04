# Implementation Plan: P1 — Structured CV Sections Output Schema

**Spec**: `spec_P1_structured_output_schema.yaml`
**Priority**: P1 (blocks P2–P4)
**Owner**: backend

---

## Problem Summary

Current CV tailoring returns a text blob (`tailored_cv`) instead of structured `cv_sections`. The frontend needs structured sections to enable per-field editing (summary textarea, skills tags, bullet editors).

**Current response:**
```json
{
  "tailored_cv": "<single text blob>",
  "ats_score": 9.0  // float 0-10, wrong scale
}
```

**Expected response:**
```json
{
  "cv_sections": {
    "contact": { "name", "email", "phone", "linkedin", "location" },
    "summary": "<3-4 sentence string>",
    "skills": { "technical": [...], "soft": [...] },
    "experience": [{ "company", "title", "start_date", "end_date", "bullets": [...] }],
    "education": [...],
    "certifications": [...]
  },
  "ats_score": 85,  // integer 0-100
  "fact_verification_passed": true
}
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/backend/careervp/models/cv_tailoring_models.py` | Add CVSections, CVContact, CVSkills, CVExperienceSection dataclasses; update TailoredCVResponse with cv_sections field |
| `src/backend/careervp/logic/cv_tailoring_prompt.py` | Update prompt to request JSON output, add JSON schema contract |
| `src/backend/careervp/logic/cv_tailoring.py` | Update parse_llm_response() to parse JSON into CVSections |
| `src/backend/careervp/handlers/cv_tailoring_handler.py` | Update response serialization |

---

## Implementation Steps

### Step 1: Update Models

Add new dataclasses to `cv_tailoring_models.py`:

```python
# CVSections nested structure
class CVContactSection(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    location: str | None = None

class CVSkillsSection(BaseModel):
    technical: list[str] = []
    soft: list[str] = []

class CVExperienceSection(BaseModel):
    company: str
    title: str
    start_date: str  # MM/YYYY
    end_date: str | None = None
    is_current: bool = False
    bullets: list[str] = []  # CAR format

class CVEducationSection(BaseModel):
    institution: str
    degree: str
    field: str
    graduation_date: str

class CVCertificationSection(BaseModel):
    name: str
    issuer: str
    date: str

class CVSections(BaseModel):
    contact: CVContactSection
    summary: str
    skills: CVSkillsSection
    experience: list[CVExperienceSection]
    education: list[CVEducationSection] = []
    certifications: list[CVCertificationSection] = []
    languages: list[str] | None = None
```

Update `TailoredCVResponse`:
- Add `cv_sections: CVSections | None = None`
- Rename/remove `tailored_cv`
- Add `ats_score: int` (0-100)
- Add `ats_issues: list[str] = []`
- Add `keyword_match_score: int` (1-10)
- Add `keywords_missing: list[str] = []`
- Add `fact_verification_passed: bool = False`
- Add `language: str = "en"`

### Step 2: Update Prompt

In `cv_tailoring_prompt.py`, replace `build_system_prompt()` with spec's stage_2_cv_generation prompt:
- 7 non-negotiable rules
- JSON output contract: "Your response MUST be valid JSON..."
- Format example showing CVSections structure
- Verification chain-of-thought before JSON output

### Step 3: Update Logic Parser

In `cv_tailoring.py`, update `parse_llm_response()`:
- Parse LLM output as JSON (not free-form text)
- Extract into CVSections structure
- Populate experience[].bullets[] from CAR-formatted strings
- Handle missing fields gracefully

### Step 4: Update Response Serialization

In `cv_tailoring_handler.py`:
- Return `cv_sections` key instead of `tailored_cv`
- Ensure ats_score is integer 0-100

---

## Schema Reference

Target: `careervp_cv_tailoring_schemas.json#/definitions/CVSections`

```json
{
  "contact": { "name", "email", "phone", "linkedin", "location" },
  "summary": "50-600 chars",
  "skills": { "technical": [], "soft": [] },
  "experience": [{ "company", "title", "start_date", "end_date", "bullets": [] }],
  "education": [],
  "certifications": []
}
```

---

## Acceptance Criteria

| ID | Description | Verification |
|----|-------------|---------------|
| AC-P1-01 | cv_sections object with 6 sub-fields | `jq '.cv_sections \| keys'` |
| AC-P1-02 | experience[0].bullets[] ≥ 1 | Length check |
| AC-P1-03 | ats_score integer 0-100 | Type + range check |
| AC-P1-04 | fact_verification_passed boolean | Type check |
| AC-P1-05 | tailored_cv key absent | `jq 'has("tailored_cv")'` |

---

## Other Files to Check

- Handler: `src/backend/careervp/handlers/cv_tailoring_handler.py`
- Tests: Existing tests in `src/backend/tests/unit/test_cv_tailoring.py` may fail (ats_score scale change)

---

## Notes

- **DynamoDB**: Existing records have old format — consider read path handles both formats during transition
- **Frontend**: Will need separate update to render cv_sections (out of scope for P1)
- **ATS scoring**: Deterministic rules post-generation gives 0-100 score (not from LLM)