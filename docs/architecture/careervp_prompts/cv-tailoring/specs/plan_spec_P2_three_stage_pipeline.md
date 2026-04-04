# Implementation Plan: P2 — Three-Stage CV Tailoring Pipeline

**Spec**: `spec_P2_three_stage_pipeline.yaml`
**Priority**: P2 (depends on P1, blocks P3)
**Owner**: backend

---

## Problem Summary

Current CV tailoring uses a single LLM call. The spec requires a 3-stage pipeline:
1. **Stage 1**: Keyword mapping (Python, no LLM) — extract from VPR + job description + parsed_facts
2. **Stage 2**: CV generation (LLM Haiku) — produce CVSections with verification block
3. **Stage 3**: Fact verification (Python) — cross-check against parsed_facts, strip hallucinations

---

## Architecture

```
run_cv_tailoring_pipeline()
  ├── run_stage1_keyword_mapping()     → Stage1Output (Python, NO LLM)
  │   ├── Extract uvp_statement from VPR
  │   ├── Extract key_differentiators from VPR
  │   ├── analyze_and_map_keywords() (existing)
  │   └── Build evidence map from parsed_facts
  │
  ├── run_stage2_cv_generation()         → Stage2Output (LLM Haiku call)
  │   ├── Build system prompt with verif rules
  │   ├── Build user prompt with stage1 + parsed_facts
  │   ├── Call LLM (Haiku, max 2500 tokens)
  │   └── Parse JSON response
  │
  └── run_stage3_fact_verification()   → Stage3Result (Python, NO LLM)
      ├── Check contact.name against parsed_facts
      ├── Check contact.email against parsed_facts
      ├── Check every experience[].company in parsed_facts
      ├── Strip hallucination_flags
      └── Return Stage3Result with fact_verification_passed
```

---

## Files to Create

| File | Exports |
|------|---------|
| `src/backend/careervp/logic/cv_tailoring_pipeline.py` | Stage1Output, Stage2Output, Stage3Result, run_stage1_keyword_mapping, run_stage2_cv_generation, run_stage3_fact_verification, run_cv_tailoring_pipeline |

---

## Files to Modify

| File | Changes |
|------|---------|
| `cv_tailoring_prompt.py` | Add build_stage1_system_prompt(), build_stage2_system_prompt(), build_stage1_user_prompt(), build_stage2_user_prompt() |
| `cv_tailoring.py` | Update run_cv_tailoring_pipeline() to call new pipeline module |
| `cv_tailoring_logic.py` | Update CVTailoringLogic.tailor_cv() to call new pipeline |

---

## Implementation Steps

### Step 1: Add Pydantic Models to cv_tailoring_models.py

```python
class PrimaryKeyword(BaseModel):
    """A keyword with evidence mapping."""
    keyword: str
    category: str  # "required", "preferred", "nice_to_have"
    priority: int
    supporting_evidence: str | None = None

class ExperienceItemInPlan(BaseModel):
    """Experience item selected for CV."""
    company: str
    title: str
    include_reason: str

class Stage1Output(BaseModel):
    """Stage 1: Keyword mapping output."""
    uvp_statement: str
    key_differentiators: list[str]
    primary_keywords: list[PrimaryKeyword]
    keywords_to_emphasize: list[str]
    keywords_missing_from_cv: list[str]
    experience_items_to_include: list[ExperienceItemInPlan]
    experience_items_to_exclude: list[str]
    summary_focus: str
    skills_to_feature: list[str]

class Stage2Verification(BaseModel):
    """Stage 2 self-verification block."""
    ats_keyword_score: int
    keywords_added_in_review: list[str]
    summary_rewritten: bool
    fact_verification_passed: bool
    hallucination_flags: list[str]

class Stage2Output(BaseModel):
    """Stage 2: CV generation output."""
    verification: Stage2Verification
    cv_sections: CVSections

class Stage3Result(BaseModel):
    """Stage 3: Fact verification result."""
    cv_sections: CVSections
    fact_verification_passed: bool
    items_corrected: list[str]
    items_removed: list[str]
```

### Step 2: Create cv_tailoring_pipeline.py

Functions to implement:
- `run_stage1_keyword_mapping(vpr, job_description, parsed_facts, gap_responses) -> Stage1Output`
- `run_stage2_cv_generation(stage1, parsed_facts, job_description, company_context, user_feedback, llm_client) -> Stage2Output`
- `run_stage3_fact_verification(stage2, parsed_facts) -> Stage3Result`
- `run_cv_tailoring_pipeline(cv, job, vpr, gap_responses, company_context, llm_client) -> Stage3Result`

### Step 3: Update Prompt Builder

Add to cv_tailoring_prompt.py:
- `build_stage1_system_prompt()` → spec verbatim
- `build_stage2_system_prompt()` → spec verbatim
- `build_stage1_user_prompt(vpr, job_description, parsed_facts, gap_responses) -> str`
- `build_stage2_user_prompt(stage1, parsed_facts, job_description, company_context, user_feedback) -> str`

### Step 4: Add Feature Flag

Environment variable `PIPELINE_V2_ENABLED` (default: true):
- If false, fall back to existing _tailor_cv_legacy()

---

## Acceptance Criteria

| ID | Description | Verification |
|----|-------------|---------------|
| AC-P2-01 | Stage1Output has >= 12 primary_keywords | len(stage1.primary_keywords) >= 12 |
| AC-P2-02 | Each keyword has keyword, category, priority, evidence | Schema check |
| AC-P2-03 | Stage2Verification.ats_keyword_score >= 6 | Score check |
| AC-P2-04 | Experience bullets are CAR format | Regex check |
| AC-P2-05 | Stage3 strips hallucination_flags | items_removed >= 1 |
| AC-P2-06 | Stage3 rejects hallucinated company | fact_verification_passed == False |
| AC-P2-07 | Pipeline completes in <= 60s | Lambda duration |
| AC-P2-08 | Feature flag fallback | ENV var test |
| AC-P2-09 | Prompts match spec verbatim | String comparison |
| AC-P2-10 | MyPy strict passes | mypy --strict |

---

## Notes

- **Stage 1 is Python only** (no LLM call) — per spec line 87-107
- **Stage 3 is Python only** (no LLM call) — deterministic verification
- Uses existing `analyze_and_map_keywords()` for keyword extraction
- VPR data provides uvp_statement and key_differentiators already structured