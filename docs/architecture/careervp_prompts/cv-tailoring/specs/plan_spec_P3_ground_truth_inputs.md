# Implementation Plan: P3 — Ground Truth Inputs

**Spec**: `spec_P3_ground_truth_inputs.yaml`
**Priority**: P3 (depends on P1, P2, blocks future specs)
**Owner**: backend

---

## Problem Summary

CVTailoringLogic.tailor_cv() does NOT fetch:
1. `parsed_facts` — cv-parser ground truth from DynamoDB
2. `gap_analysis_responses` — user answers to gap questions
3. `company_research` — cached company context

This causes Stage 1 to receive empty inputs and Stage 3 to verify against UserCV (wrong schema).

---

## Architecture

```
CVTailoringLogic.tailor_cv()
  ├── Fetch cv_record.parsed_facts → ParsedFacts (or construct from UserCV)
  ├── Fetch GAP_ANALYSIS_RESPONSES artifact → GapAnalysisResponses (or empty)
  ├── Fetch company_research cache → CompanyContext (or empty)
  └── run_cv_tailoring_pipeline(parsed_facts, gap_responses, company_context)
        ├── Stage1: keyword mapping (uses parsed_facts + gap_responses)
        ├── Stage2: CV generation (uses company_context)
        └── Stage3: fact verification (validates against parsed_facts, not UserCV)
```

---

## Implementation Steps

### Step 1: Verify existing models

`ParsedFacts`, `GapAnalysisResponses`, `CompanyContext` already exist in `cv_tailoring_models.py` from P2:
- `ParsedFacts` — ✅ exists
- `GapAnalysisResponses` — ✅ exists
- `CompanyContext` — ✅ exists

### Step 2: Update CVTailoringLogic to fetch ground truth

**File**: `src/backend/careervp/logic/cv_tailoring_logic.py`

Changes:
- Add `artifact_dal` and `company_research_dal` as constructor dependencies (or inject via method)
- Add `_fetch_parsed_facts(user_id, cv_id)` method that:
  - Gets cv_record from DAL
  - If `parsed_facts` exists → deserialize to ParsedFacts model
  - If `parsed_facts` is None → construct from UserCV fields (priority_2 strategy)
- Add `_fetch_gap_responses(user_id, cv_id)` method that:
  - Tries to fetch GAP_ANALYSIS_RESPONSES artifact
  - On failure (KeyError/missing) → return `GapAnalysisResponses(responses=[])`
- Add `_fetch_company_context(company_name: str)` method that:
  - Tries to fetch company research from cache
  - On miss → return `CompanyContext(company_name=company_name, ...)`

- Update `tailor_cv()` to call these three methods and pass results to pipeline

### Step 3: Update pipeline to accept new parameters

**File**: `src/backend/careervp/logic/cv_tailoring_pipeline.py`

- `run_cv_tailoring_pipeline()` signature already accepts `parsed_facts`, `gap_responses`, `company_context` — verify they are used
- `run_stage1_keyword_mapping()` already accepts `parsed_facts` — verify gap_responses used
- `run_stage2_cv_generation()` already accepts `company_context` — verify it's passed to prompt

### Step 4: Create test file

**File**: `src/backend/tests/unit/cv_tailoring/test_ground_truth_inputs.py`

Tests for:
- AC-P3-01: parsed_facts passed to pipeline
- AC-P3-02: gap_responses graceful degradation
- AC-P3-03: company_research graceful degradation
- AC-P3-04: Stage3 validates against parsed_facts (not UserCV)
- AC-P3-05: ParsedFacts model validation
- AC-P3-06: GapAnalysisResponses model validation

---

## Acceptance Criteria

| ID | Description | Verification |
|----|-------------|--------------|
| AC-P3-01 | tailor_cv() fetches cv_record.parsed_facts | Mock DAL returns parsed_facts → assert pipeline receives ParsedFacts |
| AC-P3-02 | gap_responses fetch failure returns empty GapAnalysisResponses | Mock artifact_dal raises KeyError → pipeline completes |
| AC-P3-03 | company_research cache miss returns empty CompanyContext | Mock returns None → pipeline completes |
| AC-P3-04 | Stage3 validates against parsed_facts.work_experience | Company in UserCV but not parsed_facts → rejected |
| AC-P3-05 | ParsedFacts model validates required fields | name/email missing → ValidationError |
| AC-P3-06 | GapAnalysisResponses accepts empty list | GapAnalysisResponses(responses=[]) succeeds |

---

## Files to Modify

| File | Changes |
|------|---------|
| `cv_tailoring_logic.py` | Add DAL dependencies, fetch methods, pass to pipeline |
| `cv_tailoring_pipeline.py` | Verify parsed_facts/gap_responses/company_context used in prompts |
| `test_ground_truth_inputs.py` | Create with 10 tests from YAML |

## Files to Create

| File | Purpose |
|------|---------|
| `test_ground_truth_inputs.py` | Unit tests for P3 |

---

## Notes

- **Graceful degradation**: Pipeline must work even when all three inputs are missing/empty
- **ParsedFacts fallback**: When cv-parser hasn't run (current test state), construct from UserCV fields
- **Async**: `tailor_cv()` and all DAL fetches are async