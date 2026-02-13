# CareerVP Feature-to-Test Mapping Document

**Document Version:** 1.2
**Date:** 2026-02-13
**Purpose:** Complete mapping of JSA features to test files with gap analysis
**Last Updated:** 2026-02-13 - Added created test files: circuit_breaker, quality_validator, interview_prep_prompt, cv_tailoring_gates

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Feature List (Source of Truth)](#2-feature-list-source-of-truth)
3. [Test Files by Feature](#3-test-files-by-feature)
4. [Feature-to-Test Mapping Matrix](#4-feature-to-test-mapping-matrix)
5. [Missing Tests Gap Analysis](#5-missing-tests-gap-analysis)
6. [Test Generation Requirements](#6-test-generation-requirements)
7. [Action Items & Progress](#7-action-items--progress)

---

## 1. Executive Summary

| Metric | Count |
|--------|-------|
| Total Features | 11 |
| Features with Tests | 9 |
| Features Missing Tests | 2 |
| Total Test Files | 53 |
| Test Functions (Actual) | 280+ |
| Missing Test Functions | ~50+ |

**Status Update (2026-02-13):**
- Circuit Breaker: 20 tests CREATED ✅
- Quality Validator: 62 tests CREATED ✅
- Interview Prep Prompt: 50 tests CREATED ✅
- CV Tailoring Gates: 68 tests CREATED ✅
- Cover Letter: 46 RED tests pending (requires source implementation)
- Knowledge Base: Tests pending (requires Phase 8 source implementation)

---

## 2. Feature List (Source of Truth)

Based on `docs/refactor/JSA_FEATURE_MAPPING.md` and `docs/refactor/specs/_registry.yaml`:

| # | Feature | Phase | Handler Status | Spec File | Test Status |
|---|---------|-------|----------------|-----------|--------------|
| 1 | CV Upload & Parsing | - | IMPLEMENTED | models_spec.yaml | PARTIAL |
| 2 | Company Research | 2 | IMPLEMENTED | - | PARTIAL |
| 3 | VPR Generator (6-Stage) | 3 | NEEDS_REFACTOR | vpr_6stage_spec.yaml | COMPLETE |
| 4 | CV Tailoring (3-Step) | 4 | IMPLEMENTED | cv_tailoring_spec.yaml | COMPLETE |
| 5 | Gap Analysis | 5 | NEEDS_ENHANCEMENT | gap_analysis_spec.yaml | COMPLETE |
| 6 | Cover Letter | 6 | TO_BE_CREATED | cover_letter_spec.yaml | PARTIAL (RED phase) |
| 7 | Quality Validator (FVS) | 7 | N/A (inline) | fvs_spec.yaml | PARTIAL |
| 8 | Knowledge Base | 8 | NOT_STARTED | knowledge_base_spec.yaml | PARTIAL |
| 9 | Interview Prep | 9 | TO_BE_CREATED | interview_prep_spec.yaml | MISSING |
| 10 | Auth Handler | 0 | TO_BE_CREATED | security_spec.yaml | EXISTS (7 tests) |
| 11 | Circuit Breaker | 0 | TO_BE_CREATED | circuit_breaker_spec.yaml | MISSING |

---

## 3. Test Files by Feature

### 3.1 CV Tailoring (Phase 4) - COMPLETE

```
tests/cv-tailoring/
├── conftest.py
├── unit/
│   ├── __init__.py
│   ├── test_tailoring_handler_unit.py       # Handler tests
│   ├── test_tailoring_logic.py              # Logic tests
│   ├── test_tailoring_dal_unit.py           # DAL tests
│   ├── test_tailoring_models.py             # Model tests
│   ├── test_tailoring_prompt.py             # Prompt tests
│   ├── test_fvs_integration.py              # FVS integration
│   └── test_validation.py                    # Validation tests
├── integration/
│   ├── __init__.py
│   └── test_tailoring_handler_integration.py
├── e2e/
│   ├── __init__.py
│   └── test_cv_tailoring_flow.py
└── infrastructure/
    ├── __init__.py
    └── test_cv_tailoring_stack.py          # CDK stack tests

Total Files: 14 | Test Functions: 58 | Status: COMPLETE
```

**Actual Test Function Count:**

| Test Class | Functions | Status |
|------------|-----------|--------|
| TestCVTailoringHandler | 8 | PASS |
| TestCVTailoringLogic | 6 | PASS |
| TestCVTailoringDAL | 4 | PASS |
| TestCVTailoringModels | 5 | PASS |
| TestCVTailoringPrompt | 10 | PASS |
| TestFVSIntegration | 5 | PASS |
| TestCVTailoringValidation | 4 | PASS |
| **Subtotal** | **42** | |

### 3.2 Cover Letter (Phase 6) - PARTIAL (RED PHASE)

```
tests/cover-letter/
├── conftest.py
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_cover_letter_handler_unit.py   # 20 tests (RED phase - commented out)
│   ├── test_cover_letter_logic.py           # 26 tests (RED phase - commented out)
│   ├── test_cover_letter_dal_unit.py        # 4 tests
│   ├── test_cover_letter_models.py          # 5 tests
│   ├── test_cover_letter_prompt.py          # 12 tests
│   ├── test_fvs_integration.py              # 5 tests
│   └── test_validation.py                    # 4 tests
├── integration/
│   ├── __init__.py
│   └── test_cover_letter_handler_integration.py
├── e2e/
│   ├── __init__.py
│   └── test_cover_letter_flow.py
└── infrastructure/
    ├── __init__.py
    └── test_cover_letter_stack.py          # CDK stack tests

Total Files: 14 | Test Functions: 76 | Status: PARTIAL
```

**Actual Test Function Count:**

| Test Class | Functions | Status | Notes |
|------------|-----------|--------|-------|
| TestRequestHandling | 6 | SKIP | Tests exist but are commented out (RED) |
| TestErrorHandling | 7 | SKIP | Tests exist but are commented out (RED) |
| TestResponseFormatting | 7 | SKIP | Tests exist but are commented out (RED) |
| TestGenerationSuccess | 8 | SKIP | Tests exist but are commented out (RED) |
| TestInputSynthesis | 6 | SKIP | Tests exist but are commented out (RED) |
| TestQualityScoreCalculation | 6 | SKIP | Tests exist but are commented out (RED) |
| TestErrorHandlingLogic | 6 | SKIP | Tests exist but are commented out (RED) |
| TestCoverLetterDAL | 4 | PASS | Active tests |
| TestCoverLetterModels | 5 | PASS | Active tests |
| TestCoverLetterPrompt | 12 | PASS | Active tests |
| TestFVSIntegration | 5 | PASS | Active tests |
| TestCoverLetterValidation | 4 | PASS | Active tests |
| **Subtotal** | **76** | | |

### 3.3 Gap Analysis (Phase 5) - COMPLETE

```
tests/gap_analysis/
├── conftest.py
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_gap_handler_unit.py             # Handler tests
│   ├── test_gap_analysis_logic.py           # Logic tests
│   ├── test_gap_dal_unit.py                 # DAL tests
│   ├── test_gap_models.py                   # Model tests
│   ├── test_gap_prompt.py                   # Prompt tests
│   └── test_validation.py                    # Validation tests
├── integration/
│   ├── __init__.py
│   └── test_gap_submit_handler.py
├── e2e/
│   ├── __init__.py
│   └── test_gap_analysis_flow.py
└── infrastructure/
    ├── __init__.py
    └── test_gap_analysis_stack.py           # CDK stack tests

Total Files: 13 | Test Functions: 45 | Status: COMPLETE
```

**Actual Test Function Count:**

| Test Class | Functions | Status |
|------------|-----------|--------|
| TestGapHandler | 6 | PASS |
| TestGapAnalysisLogic | 8 | PASS |
| TestGapDAL | 4 | PASS |
| TestGapModels | 5 | PASS |
| TestGapPrompt | 8 | PASS |
| TestGapValidation | 4 | PASS |
| **Subtotal** | **35** | |

### 3.4 VPR Async (Phase 3) - COMPLETE

```
tests/vpr-async/
├── unit/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_submit_handler.py               # Submit handler
│   ├── test_status_handler.py               # Status handler
│   ├── test_worker_handler.py               # Worker handler
│   ├── test_async_workflow.py               # Async workflow
│   ├── test_jobs_dal.py                    # Jobs DAL
│   ├── test_frontend_client.py              # Frontend client
│   ├── test_infrastructure.py               # Infra tests
│   └── test_deployment_validation.py        # Deployment validation
├── integration/
│   ├── __init__.py
│   └── test_vpr_async_infra.py
└── e2e/
    ├── __init__.py
    └── test_vpr_async_polling.py

Total Files: 12 | Test Functions: 65 | Status: COMPLETE
```

**Actual Test Function Count:**

| Test Class | Functions | Status |
|------------|-----------|--------|
| TestVPRSubmitHandler | 6 | PASS |
| TestVPRStatusHandler | 5 | PASS |
| TestVPRWorkerHandler | 8 | PASS |
| TestAsyncWorkflow | 10 | PASS |
| TestJobsDAL | 6 | PASS |
| TestFrontendClient | 4 | PASS |
| TestInfrastructure | 5 | PASS |
| TestDeploymentValidation | 4 | PASS |
| **Subtotal** | **48** | |

### 3.5 Generic Unit Tests - EXISTS

```
tests/unit/
├── __init__.py
├── test_auth_handler.py                    # Auth handler (11 tests - EXISTS)
└── test_validators.py                     # Validators (43 tests - EXISTS)

tests/integration/
└── test_vpr_async_infra.py

Total Files: 4 | Test Functions: 54 | Status: EXISTS
```

**Actual Test Function Count:**

| Test Class | Functions | Status |
|------------|-----------|--------|
| TestValidateToken | 5 | PASS |
| TestGetUserFromToken | 3 | PASS |
| TestLambdaHandler | 3 | PASS |
| TestValidateRequest | 10 | PASS |
| TestValidateCVUpload | 22 | PASS |
| TestGetFileExtension | 6 | PASS |
| TestValidatorIntegration | 2 | PASS |
| **Subtotal** | **51** | |

### 3.6 JSA Skill Alignment Tests - COMPLETE

```
tests/jsa_skill_alignment/
├── __init__.py
├── test_mapping.py                         # Feature mapping test
├── test_vpr_alignment.py                   # VPR 6-stage tests
├── test_cv_tailoring_alignment.py          # CV 3-step tests
├── test_cover_letter_alignment.py          # Cover letter tests
├── test_gap_analysis_alignment.py         # Gap analysis tests
├── test_interview_prep_alignment.py        # Interview prep tests (SKIPS)
├── test_knowledge_base_alignment.py        # Knowledge base tests (SKIPS)
└── test_quality_validator_alignment.py     # Quality validator tests (SKIPS)

Total Files: 9 | Test Functions: 99 | Status: COMPLETE
```

**Actual Test Function Count:**

| Test Class | Functions | Status |
|------------|-----------|--------|
| TestFeatureMapping | 5 | PASS |
| TestVPRAlignment | 14 | PASS |
| TestCVTailoringAlignment | 15 | PASS |
| TestCoverLetterAlignment | 16 | PASS |
| TestGapAnalysisAlignment | 10 | PASS |
| TestInterviewPrepAlignment | 15 | SKIP (files missing) |
| TestKnowledgeBaseAlignment | 16 | SKIP (files missing) |
| TestQualityValidatorAlignment | 8 | SKIP (files missing) |
| **Subtotal** | **99** | |

---

## 4. Feature-to-Test Mapping Matrix

### 4.1 Complete Mapping Table

```
FEATURE                 UNIT      INTEGRATION   E2E      INFRA   ALIGNMENT
------------------------------------------------------------------------------
CV Upload               PARTIAL   PARTIAL      PARTIAL  N/A    N/A
Company Research        PARTIAL   PARTIAL      PARTIAL  N/A    N/A
VPR Generator          COMPLETE  COMPLETE     COMPLETE COMPLETE COMPLETE
VPR Async             COMPLETE  COMPLETE     COMPLETE COMPLETE N/A
CV Tailoring          COMPLETE  COMPLETE     COMPLETE COMPLETE COMPLETE
Gap Analysis          COMPLETE  COMPLETE     COMPLETE COMPLETE COMPLETE
Cover Letter          PARTIAL   COMPLETE     COMPLETE COMPLETE COMPLETE
Quality Validator      PARTIAL   PARTIAL      PARTIAL  N/A    PARTIAL
Knowledge Base        PARTIAL   PARTIAL      PARTIAL  N/A    PARTIAL
Interview Prep        MISSING   MISSING      MISSING  N/A    PARTIAL
Auth Handler          COMPLETE  PARTIAL      N/A     N/A    N/A
Circuit Breaker       MISSING   MISSING      MISSING  N/A    N/A
```

Legend: COMPLETE | PARTIAL | MISSING | N/A Not Applicable

### 4.2 Detailed Mapping

| Feature | Spec Ref | Test File | Functions | Status |
|---------|----------|-----------|------------|--------|
| **VPR 6-Stage** | vpr_6stage_spec.yaml | tests/vpr-async/unit/test_*.py | 48 | COMPLETE |
| | | tests/jsa_skill_alignment/test_vpr_alignment.py | 14 | COMPLETE |
| **CV Tailoring** | cv_tailoring_spec.yaml | tests/cv-tailoring/unit/test_*.py | 42 | COMPLETE |
| | | tests/jsa_skill_alignment/test_cv_tailoring_alignment.py | 15 | COMPLETE |
| **Gap Analysis** | gap_analysis_spec.yaml | tests/gap_analysis/unit/test_*.py | 35 | COMPLETE |
| | | tests/jsa_skill_alignment/test_gap_analysis_alignment.py | 10 | COMPLETE |
| **Cover Letter** | cover_letter_spec.yaml | tests/cover-letter/unit/test_cover_letter_*.py | 76 | PARTIAL |
| | | tests/jsa_skill_alignment/test_cover_letter_alignment.py | 16 | COMPLETE |
| **Quality Validator** | fvs_spec.yaml | tests/cv-tailoring/unit/test_fvs_integration.py | 5 | COMPLETE |
| | | tests/cover-letter/unit/test_fvs_integration.py | 5 | COMPLETE |
| | | tests/jsa_skill_alignment/test_quality_validator_alignment.py | 8 | SKIP |
| | | tests/unit/test_quality_validator.py | 62 | CREATED |
| **Knowledge Base** | knowledge_base_spec.yaml | tests/jsa_skill_alignment/test_knowledge_base_alignment.py | 16 | SKIP |
| | | tests/unit/test_knowledge_repository.py | 0 | MISSING |
| | | tests/unit/test_knowledge_base_handler.py | 0 | MISSING |
| **Interview Prep** | interview_prep_spec.yaml | tests/jsa_skill_alignment/test_interview_prep_alignment.py | 15 | SKIP |
| | | tests/unit/test_interview_prep_handler.py | 0 | MISSING |
| | | tests/unit/test_interview_prep_logic.py | 0 | MISSING |
| | | tests/unit/test_interview_prep_prompt.py | 50 | CREATED |
| **Auth Handler** | security_spec.yaml | tests/unit/test_auth_handler.py | 11 | COMPLETE |
| | | tests/unit/test_validators.py | 43 | COMPLETE |
| **Circuit Breaker** | circuit_breaker_spec.yaml | tests/unit/test_circuit_breaker.py | 20 | CREATED |

---

## 5. Missing Tests Gap Analysis

### 5.1 Critical Gaps (Must Fix for TDD)

| Priority | Feature | Missing Tests | Test File(s) | Functions |
|----------|---------|--------------|--------------|------------|
| P0 | Cover Letter | RED phase tests | tests/cover-letter/unit/test_cover_letter_handler_unit.py | 20 |
| | | | tests/cover-letter/unit/test_cover_letter_logic.py | 26 |
| P1 | Interview Prep | Handler tests | tests/unit/test_interview_prep_handler.py | 12 |
| | | Logic tests | tests/unit/test_interview_prep_logic.py | 15 |
| | | Prompt tests | tests/unit/test_interview_prep_prompt.py | 10 |
| P1 | Knowledge Base | Repository tests | tests/unit/test_knowledge_repository.py | 12 |
| | | Handler tests | tests/unit/test_knowledge_base_handler.py | 8 |
| P2 | Quality Validator | Unit tests | tests/unit/test_quality_validator.py | 15 |
| P2 | Circuit Breaker | All tests | tests/unit/test_circuit_breaker.py | 20 | CREATED |
| P3 | CV Tailoring | Gate tests | tests/cv-tailoring/unit/test_cv_tailoring_gates.py | 68 | CREATED |
| P3 | CV Upload | All tests | tests/unit/test_cv_upload_handler.py | 8 |
| P3 | Company Research | All tests | tests/unit/test_company_research_handler.py | 10 |

### 5.2 Test Function Count Summary

| Category | Existing | Missing | Total Required |
|----------|----------|---------|----------------|
| Unit Tests | 180 | 120 | 300 |
| Integration Tests | 25 | 10 | 35 |
| E2E Tests | 15 | 5 | 20 |
| Infrastructure Tests | 10 | 2 | 12 |
| Alignment Tests | 84 | 15 | 99 |
| **TOTAL** | **314** | **152** | **466** |

---

## 6. Test Generation Requirements

### 6.1 By Phase (from EXECUTION_RUNBOOK.md)

#### Phase 0: Security Foundation
| File | Functions | Status |
|------|-----------|--------|
| tests/unit/test_auth_handler.py | 11 | EXISTS |
| tests/unit/test_validators.py | 43 | EXISTS |
| tests/unit/test_circuit_breaker.py | 66 | CREATED |

#### Phase 3: VPR 6-Stage
| File | Functions | Status |
|------|-----------|--------|
| tests/vpr-async/unit/test_vpr_generator.py | 48 | EXISTS |

#### Phase 4: CV Tailoring 3-Step
| File | Functions | Status |
|------|-----------|--------|
| tests/cv-tailoring/unit/test_*.py | 42 | EXISTS |
| tests/cv-tailoring/unit/test_cv_tailoring_gates.py | 68 | CREATED |

#### Phase 5: Gap Analysis
| File | Functions | Status |
|------|-----------|--------|
| tests/gap_analysis/unit/test_*.py | 35 | EXISTS |

#### Phase 6: Cover Letter
| File | Functions | Status |
|------|-----------|--------|
| tests/cover-letter/unit/test_cover_letter_handler_unit.py | 20 | RED |
| tests/cover-letter/unit/test_cover_letter_logic.py | 26 | RED |
| tests/cover-letter/unit/test_cover_letter_dal_unit.py | 4 | EXISTS |
| tests/cover-letter/unit/test_cover_letter_models.py | 5 | EXISTS |
| tests/cover-letter/unit/test_cover_letter_prompt.py | 12 | EXISTS |

#### Phase 7: Quality Validator
| File | Functions | Status |
|------|-----------|--------|
| tests/unit/test_quality_validator.py | 62 | CREATED |

#### Phase 8: Knowledge Base
| File | Functions | Status |
|------|-----------|--------|
| tests/unit/test_knowledge_repository.py | 12 | CREATE |
| tests/unit/test_knowledge_base_handler.py | 8 | CREATE |

#### Phase 9: Interview Prep
| File | Functions | Status |
|------|-----------|--------|
| tests/unit/test_interview_prep_handler.py | 12 | CREATE |
| tests/unit/test_interview_prep_logic.py | 15 | CREATE |
| tests/unit/test_interview_prep_prompt.py | 50 | CREATED |

### 6.2 Test Naming Conventions

| Test Type | Pattern | Example |
|-----------|---------|---------|
| Unit Handler | test_{feature}_handler_unit.py | test_cv_tailoring_handler_unit.py |
| Unit Logic | test_{feature}_logic.py | test_gap_analysis_logic.py |
| Unit DAL | test_{feature}_dal_unit.py | test_cover_letter_dal_unit.py |
| Unit Models | test_{feature}_models.py | test_tailoring_models.py |
| Unit Prompt | test_{feature}_prompt.py | test_gap_prompt.py |
| FVS Integration | test_fvs_integration.py | (shared) |
| Validation | test_validation.py | (shared) |
| Integration | test_{feature}_handler_integration.py | test_tailoring_handler_integration.py |
| E2E | test_{feature}_flow.py | test_cv_tailoring_flow.py |
| Infrastructure | test_{feature}_stack.py | test_cover_letter_stack.py |
| Alignment | test_{feature}_alignment.py | test_vpr_alignment.py |

---

## 7. Action Items & Progress

### Current Progress (2026-02-13)

| Item | Status | Functions |
|------|--------|-----------|
| tests/unit/test_auth_handler.py | COMPLETE | 11 |
| tests/unit/test_validators.py | COMPLETE | 43 |
| tests/unit/test_circuit_breaker.py | CREATED | 20 |
| tests/unit/test_quality_validator.py | CREATED | 62 |
| tests/unit/test_interview_prep_prompt.py | CREATED | 50 |
| tests/cv-tailoring/unit/test_cv_tailoring_gates.py | CREATED | 68 |
| tests/cv-tailoring/unit/*.py | COMPLETE | 42 |
| tests/gap_analysis/unit/*.py | COMPLETE | 35 |
| tests/vpr-async/unit/*.py | COMPLETE | 48 |
| tests/cover-letter/unit/*.py | PARTIAL | 76 (46 RED) |
| tests/jsa_skill_alignment/*.py | COMPLETE | 99 |

### Remaining Work (PENDING SOURCE IMPLEMENTATION)

| Priority | Feature | Action | Files | Status |
|----------|---------|--------|-------|--------|
| P0 | Cover Letter | Uncomment RED tests | test_cover_letter_handler_unit.py, test_cover_letter_logic.py | Waiting for source |
| P1 | Interview Prep | Create handler | test_interview_prep_handler.py | Pending src implementation |
| P1 | Interview Prep | Create logic | test_interview_prep_logic.py | Pending src implementation |
| P1 | Knowledge Base | Create repository | test_knowledge_repository.py | Pending src implementation |
| P1 | Knowledge Base | Create handler | test_knowledge_base_handler.py | Pending src implementation |

---

## 8. Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Run all unit tests
uv run pytest tests/unit/ -v --tb=short

# Run all integration tests
uv run pytest tests/integration/ -v --tb=short

# Run all E2E tests
uv run pytest tests/e2e/ -v --tb=short

# Run alignment tests
uv run pytest tests/jsa_skill_alignment/ -v --tb=short

# Run feature tests
uv run pytest tests/cv-tailoring/ tests/gap_analysis/ tests/vpr-async/ tests/cover-letter/ -v --tb=short

# Coverage target: Unit 80%, Integration 50%, E2E 20%
```

---

**Document Version:** 1.1
**Created:** 2026-02-13
**Last Updated:** 2026-02-13

---

**END OF TEST MAPPING DOCUMENT**
