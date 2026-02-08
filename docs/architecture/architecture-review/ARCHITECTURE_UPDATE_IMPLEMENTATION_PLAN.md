# Architecture Update Implementation Plan (Junior-Engineer Ready)

**Date:** 2026-02-08
**Based on:** ARCHITECTURE_UPDATE_PLAN.md
**Status:** Draft - Ready for Execution
**Audience:** Junior Engineer implementing the plan
**Owner:** Engineering

---

## Purpose

This plan is written so a junior engineer can execute it without omitting any requirement. It includes detailed task guidance, explicit acceptance criteria, and verification steps to ensure all architecture update criteria are met.

---

## How To Use This Plan

1. Read the Key References section before coding.
2. Follow phases in order. Do not skip exit criteria.
3. Use the Checklists in each phase to confirm nothing is missed.
4. Record evidence for each requirement in the Verification Matrix.

---

## Key References (Read First)

- `docs/architecture/architecture-review/ARCHITECTURE_UPDATE_PLAN.md`
- `docs/architecture/architecture-review/DEEP_ANALYSIS_RESULTS.md`
- `docs/architecture/architecture-review/NEXT_STEPS_POST_REVIEW.md`
- `docs/architecture/CV_TAILORING_DESIGN.md`
- `docs/architecture/COVER_LETTER_DESIGN.md`
- `docs/architecture/GAP_ANALYSIS_DESIGN.md`

---

## Non-Negotiable Rules

- Handlers must not access DAL directly. All DAL access goes through logic classes.
- `DynamoDalHandler` is the single DAL entrypoint.
- Canonical models live in `models/cv.py` and `models/fvs.py` only.
- Preserve VPR behavior and data contracts.

---

## Phase 0: Preflight and Setup (0.5 day)

**Goal:** Ensure you have the right context, tools, and tracking before changes.

**Tasks**
- Read all Key References and confirm the architectural decisions are already resolved.
- Create tracking tickets for each task ID in this plan.
- Create a working branch for the refactor.
- Collect baseline info for later comparison.

**Baseline info to capture**
- Locations of `cv_models.py` and `fvs_models.py` usage.
- Locations where handlers access DAL directly.
- Existing DAL methods in `DynamoDalHandler`.

**Exit criteria**
- Tracking tickets exist for every task ID.
- A working branch is created.
- Baseline locations documented in the ticket notes.

---

## Phase 1: Model Consolidation (MDL-1 to MDL-9) (Week 1)

**Goal:** Unify `UserCV` and FVS models to prevent drift and confusion.

**Detailed tasks**

| ID | Task | Files | Instructions | Output |
|---|---|---|---|---|
| MDL-1 | Compare `UserCV` models and identify differences | `models/cv.py`, `models/cv_models.py` | Create a field-by-field diff. Note missing fields and type mismatches. | Diff summary in ticket |
| MDL-2 | Merge unique fields into `models/cv.py` | `models/cv.py` | Add fields from `cv_models.py` that are required for CV Tailoring. Keep names consistent with existing API usage. | Updated canonical model |
| MDL-3 | Update CV Tailoring imports to `models.cv` | Multiple | Replace all `cv_models` imports and update references. | Code compiles with single `UserCV` |
| MDL-4 | Delete `models/cv_models.py` | - | Only after MDL-3 is complete and no imports remain. | File removed |
| MDL-5 | Compare FVS model sets | `models/fvs.py`, `models/fvs_models.py` | Create a field-by-field diff. | Diff summary in ticket |
| MDL-6 | Merge unique fields into `models/fvs.py` | `models/fvs.py` | Add fields required by CV Tailoring or other features. | Updated canonical model |
| MDL-7 | Update all FVS imports | Multiple | Replace all `fvs_models` imports and update references. | No imports from `fvs_models.py` |
| MDL-8 | Delete `models/fvs_models.py` | - | Only after MDL-7 is complete and no imports remain. | File removed |
| MDL-9 | Run tests for model changes | - | Run impacted unit and integration tests. | Green tests |

**Checklist**
- `rg "cv_models"` returns zero results.
- `rg "fvs_models"` returns zero results.
- Only `models/cv.py` and `models/fvs.py` contain canonical models.

**Exit criteria**
- All model imports point to `models/cv.py` or `models/fvs.py`.
- Tests passing for model-related changes.

---

## Phase 2: DAL Enhancement (DAL-1 to DAL-7) (Week 1)

**Goal:** Expand `DynamoDalHandler` to cover CV Tailoring, Cover Letter, and Gap Analysis artifacts.

**DAL schema rules to follow**
- All artifacts follow `PK = user_id`.
- SK patterns must match ARCHITECTURE_UPDATE_PLAN.md.
- TTL must be 90 days for stored artifacts.

**Detailed tasks**

| ID | Task | Files | Instructions | Output |
|---|---|---|---|---|
| DAL-1 | Add CV Tailoring methods | `dal/dynamo_dal_handler.py` | Implement `save_tailored_cv`, `get_tailored_cv`, `list_tailored_cvs`. | CRUD methods present |
| DAL-2 | Add Cover Letter methods | `dal/dynamo_dal_handler.py` | Implement `save_cover_letter`, `get_cover_letter`, `list_cover_letters`. | CRUD methods present |
| DAL-3 | Add Gap Analysis methods | `dal/dynamo_dal_handler.py` | Implement `save_gap_questions`, `get_gap_questions`. | CRUD methods present |
| DAL-4 | Add Gap Response methods | `dal/dynamo_dal_handler.py` | Implement `save_gap_responses`, `get_gap_responses`. | CRUD methods present |
| DAL-5 | Create DAL unit tests | `tests/dal/test_dynamo_dal_handler.py` | Add coverage for all new methods and SK patterns. | Tests added |
| DAL-6 | Deprecate and remove `CVTable` | `dal/cv_dal.py` | Remove after replacements are in place. | File removed or unused |
| DAL-7 | Deprecate and remove `cv_tailoring_dal.py` | `dal/cv_tailoring_dal.py` | Remove after replacements are in place. | File removed or unused |

**Checklist**
- SK patterns and TTL values match ARCHITECTURE_UPDATE_PLAN.md.
- No direct references to `CVTable` or `cv_tailoring_dal.py` remain.
- DAL tests cover create, read, and list flows for each artifact type.

**Exit criteria**
- `DynamoDalHandler` fully supports all required artifact types.
- DAL tests pass.

---

## Phase 3: CV Tailoring Refactor (CVT-1 to CVT-10) (Week 2)

**Goal:** Enforce strict Handler → Logic → DAL layering and align CV Tailoring with new models and DAL.

**Handler responsibilities**
- Parse API Gateway event and validate request.
- Extract `user_id` from JWT claims.
- Initialize dependencies (DAL, LLM, FVS).
- Call `CVTailoringLogic` and format the HTTP response.
- No DAL calls and no business logic.

**Logic responsibilities**
- Fetch data from DAL.
- Build prompts, call LLM, validate FVS, and store artifacts.

**Detailed tasks**

| ID | Task | Files | Instructions | Output |
|---|---|---|---|---|
| CVT-1 | Create `CVTailoringLogic` with DI constructor | `logic/cv_tailoring_logic.py` | Constructor takes `dal`, `llm_client`, `fvs`. All business logic lives here. | Logic layer implemented |
| CVT-2 | Move CV fetch and DAL ops into logic | `handlers/cv_tailoring_handler.py`, `logic/cv_tailoring_logic.py` | Remove DAL calls from handler. Add DAL usage in logic. | Handler has no DAL access |
| CVT-3 | Replace `CVTable` with `DynamoDalHandler` | `logic/cv_tailoring_logic.py` | Use new DAL methods from Phase 2. | Unified DAL usage |
| CVT-4 | Add CV Tailoring methods to DAL | `dal/dynamo_dal_handler.py` | Ensure methods are finalized and used by logic. | DAL methods finalized |
| CVT-5 | Use unified `UserCV` | Multiple | Import from `models/cv.py`. Update any conversion logic. | Consistent model usage |
| CVT-6 | Add idempotency key support | `handlers/cv_tailoring_handler.py`, `logic/cv_tailoring_logic.py` | Follow existing idempotency pattern from other handlers. | Idempotent request handling |
| CVT-7 | Add Powertools decorators | `handlers/cv_tailoring_handler.py` | Mirror observability patterns from other handlers. | Observability added |
| CVT-8 | Add retry logic for LLM calls | `logic/cv_tailoring_logic.py` | Use existing retry utilities if present, otherwise add minimal retry wrapper. | Resilient LLM calls |
| CVT-9 | Update unit tests | `tests/cv_tailoring/` | Update tests to match new layering and models. | Updated unit tests |
| CVT-10 | Update integration tests | `tests/cv_tailoring/` | Update integration tests to match new handler behavior. | Updated integration tests |

**Checklist**
- `cv_tailoring_handler.py` contains no DAL calls.
- Logic class is fully testable without API Gateway context.
- Idempotency key format matches existing conventions.
- Powertools logger/tracer/metrics usage matches other handlers.

**Exit criteria**
- Handler delegates all business logic to `CVTailoringLogic`.
- No direct DAL access in handler.
- Unit and integration tests pass for CV Tailoring.

---

## Phase 4: Documentation Updates (CLD-1..5, GAD-1..5) (Week 3)

**Goal:** Update specs, prompts, tasks, and test scaffolding for Cover Letter and Gap Analysis.

**Cover Letter docs**

| ID | Task | Files | Instructions | Output |
|---|---|---|---|---|
| CLD-1 | Create `cover_letter_prompt.py` | `logic/prompts/cover_letter_prompt.py` | Implement prompt builders using `COVER_LETTER_DESIGN.md` references. | Prompt module |
| CLD-2 | Update spec | `docs/specs/cover-letter/COVER_LETTER_SPEC.md` | Add Handler → Logic → DAL flow, DAL signatures, FVS rules, error codes, idempotency key. | Updated spec |
| CLD-3 | Create tasks doc | `docs/tasks/cover-letter/COVER_LETTER_TASKS.md` | Use task list from ARCHITECTURE_UPDATE_PLAN.md. | Tasks doc |
| CLD-4 | Create test scaffold | `tests/cover_letter/` | Create directory structure and placeholder tests. | Test scaffold |
| CLD-5 | Create fixtures | `tests/cover_letter/conftest.py` | Add base fixtures matching other test suites. | Fixtures file |

**Gap Analysis docs**

| ID | Task | Files | Instructions | Output |
|---|---|---|---|---|
| GAD-1 | Create `gap_analysis_prompt.py` | `logic/prompts/gap_analysis_prompt.py` | Implement prompt builders using `GAP_ANALYSIS_DESIGN.md` references. | Prompt module |
| GAD-2 | Update spec | `docs/specs/gap-analysis/GAP_SPEC.md` | Add Handler → Logic → DAL flow, DAL signatures, FVS rules, error codes, scoring details. | Updated spec |
| GAD-3 | Create tasks doc | `docs/tasks/gap-analysis/GAP_ANALYSIS_TASKS.md` | Use task list from ARCHITECTURE_UPDATE_PLAN.md. | Tasks doc |
| GAD-4 | Create test scaffold | `tests/gap_analysis/` | Create directory structure and placeholder tests. | Test scaffold |
| GAD-5 | Create fixtures | `tests/gap_analysis/conftest.py` | Add base fixtures matching other test suites. | Fixtures file |

**Checklist**
- Specs include layering details, DAL signatures, and error mappings.
- Prompt modules exist with function stubs documented.
- Task docs mirror the IDs from ARCHITECTURE_UPDATE_PLAN.md.

**Exit criteria**
- Docs updated and test scaffolds created.

---

## Phase 5: Verification and Sign-off (Week 3)

**Goal:** Ensure all architecture criteria are met and nothing is omitted.

**Validation steps**
- Run affected unit and integration tests.
- Verify no handler directly accesses DAL.
- Verify only canonical models remain and old files are deleted.
- Verify `DynamoDalHandler` includes all required methods.
- Verify documentation updates match design docs.

**Exit criteria**
- All tests pass for impacted components.
- Verification matrix is complete.
- Architect and Tech Lead sign-off recorded.

---

## Verification Matrix (Do Not Skip)

| Requirement | Evidence | Location |
|---|---|---|
| Handlers do not access DAL | Code inspection + `rg` search | `handlers/` |
| Logic layer owns DAL access | Code inspection | `logic/` |
| `UserCV` consolidated | `cv_models.py` removed, imports updated | `models/cv.py` |
| FVS models consolidated | `fvs_models.py` removed, imports updated | `models/fvs.py` |
| DAL supports all artifacts | DAL tests + method list | `dal/dynamo_dal_handler.py` |
| CV Tailoring updated | Unit + integration tests | `tests/cv_tailoring/` |
| Cover Letter docs updated | File existence and content check | `docs/specs/cover-letter/` |
| Gap Analysis docs updated | File existence and content check | `docs/specs/gap-analysis/` |

---

## Definition of Done

- All phases complete with exit criteria met.
- No references to `cv_models.py`, `fvs_models.py`, `CVTable`, or `cv_tailoring_dal.py` remain.
- `DynamoDalHandler` provides all required methods and tests cover them.
- CV Tailoring follows strict Handler → Logic → DAL layering.
- Cover Letter and Gap Analysis docs and scaffolding are created and updated.
- Verification matrix is completed and sign-off recorded.

---

## Status Tracking

| Phase | Status | Owner | Notes |
|---|---|---|---|
| Phase 0 | PENDING | - | - |
| Phase 1 | PENDING | - | - |
| Phase 2 | PENDING | - | - |
| Phase 3 | PENDING | - | - |
| Phase 4 | PENDING | - | - |
| Phase 5 | PENDING | - | - |

---

## Sign-Off

| Reviewer | Status | Date |
|---|---|---|
| Architect | PENDING | - |
| Tech Lead | PENDING | - |

