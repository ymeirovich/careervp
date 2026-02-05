# Phase 10: Cover Letter Generation - Task Breakdown

**Date:** 2026-02-05
**Phase:** 10 - Cover Letter Generation
**Status:** Task Documentation Complete - Ready for Implementation

---

## Overview

This document provides a comprehensive breakdown of all implementation tasks for Phase 10: Cover Letter Generation. Each task is atomic (completable in 1-2 hours) with clear success criteria and test coverage.

---

## Task List

| Task | Description | Complexity | Duration | Test File(s) |
|------|-------------|------------|----------|--------------|
| **01** | Validation Utilities | Low | 1 hour | test_validation.py (15-20 tests) |
| **02** | Infrastructure (CDK) | Medium | 2 hours | test_cover_letter_stack.py (10-15 tests) |
| **03** | Cover Letter Logic | High | 3 hours | test_cover_letter_logic.py (25-30 tests) |
| **04** | Cover Letter Prompt | Medium | 2 hours | test_cover_letter_prompt.py (15-20 tests) |
| **05** | FVS Integration | Medium | 2 hours | test_fvs_integration.py (20-25 tests) |
| **06** | Cover Letter Handler | Medium | 2 hours | test_cover_letter_handler_unit.py (15-20 tests) |
| **07** | DAL Extensions | Low | 1 hour | test_cover_letter_dal_unit.py (10-15 tests) |
| **08** | Pydantic Models | Low | 1 hour | test_cover_letter_models.py (20-25 tests) |
| **09** | Integration Tests | Medium | 2 hours | test_cover_letter_handler_integration.py (25-30 tests) |
| **10** | E2E Verification | Medium | 2 hours | test_cover_letter_flow.py (10-15 tests) |
| **11** | Deployment | Low | 1 hour | N/A (manual verification) |

**Total Estimated Duration:** 19 hours

---

## Dependency Graph

```
┌─────────────┐
│   Task 01   │  Validation Utilities
│  (Blocking) │  Must complete FIRST
└──────┬──────┘
       │
       ├───────────────────────────────────┐
       │                                   │
       ▼                                   ▼
┌─────────────┐                    ┌─────────────┐
│   Task 08   │  Models            │   Task 02   │  Infrastructure
│  (Blocking) │                    │  (Blocking) │
└──────┬──────┘                    └──────┬──────┘
       │                                   │
       ├───────────────────────────────────┤
       │                                   │
       ▼                                   ▼
┌─────────────┐                    ┌─────────────┐
│   Task 04   │  Prompt            │   Task 07   │  DAL (Optional)
│             │                    │             │
└──────┬──────┘                    └──────┬──────┘
       │                                   │
       ├───────────────────────────────────┤
       │                                   │
       ▼                                   ▼
┌─────────────┐                    ┌─────────────┐
│   Task 03   │  Logic             │   Task 05   │  FVS Integration
│  (Blocking) │                    │             │
└──────┬──────┘                    └──────┬──────┘
       │                                   │
       └───────────────┬───────────────────┘
                       │
                       ▼
                ┌─────────────┐
                │   Task 06   │  Handler
                │  (Blocking) │
                └──────┬──────┘
                       │
                       ▼
                ┌─────────────┐
                │   Task 09   │  Integration Tests
                │             │
                └──────┬──────┘
                       │
                       ▼
                ┌─────────────┐
                │   Task 10   │  E2E Tests
                │             │
                └──────┬──────┘
                       │
                       ▼
                ┌─────────────┐
                │   Task 11   │  Deployment
                └─────────────┘
```

### Critical Path

1. **Task 01** → **Task 08** → **Task 03** → **Task 06** → **Task 09** → **Task 10** → **Task 11**

**Tasks that can be done in parallel:**
- Task 02 (Infrastructure) can be done alongside Task 03-06
- Task 04 (Prompt) can be done alongside Task 02-07
- Task 05 (FVS) can be done alongside Task 03-04
- Task 07 (DAL) is OPTIONAL and can be done anytime after Task 01

---

## Implementation Order

### Recommended Sequence

**Phase 1: Foundation (Tasks 01, 08)**
```
1. Task 01: Validation Utilities (BLOCKING - do first)
2. Task 08: Pydantic Models (BLOCKING - do second)
```

**Phase 2: Infrastructure & Support (Tasks 02, 04, 07)**
```
3. Task 02: Infrastructure (CDK) - can parallelize with Phase 3
4. Task 04: Cover Letter Prompt - can parallelize with Phase 3
5. Task 07: DAL Extensions (OPTIONAL) - can parallelize with Phase 3
```

**Phase 3: Core Logic (Tasks 03, 05)**
```
6. Task 03: Cover Letter Logic (BLOCKING for Task 06)
7. Task 05: FVS Integration (BLOCKING for Task 06)
```

**Phase 4: Handler (Task 06)**
```
8. Task 06: Cover Letter Handler (BLOCKING for Task 09)
```

**Phase 5: Testing (Tasks 09, 10)**
```
9. Task 09: Integration Tests
10. Task 10: E2E Tests
```

**Phase 6: Deployment (Task 11)**
```
11. Task 11: Deployment & Verification
```

---

## Test-to-Task Mapping

| Task | Test File | Test Count | Coverage Target |
|------|-----------|------------|-----------------|
| 01 | `tests/cover-letter/unit/test_validation.py` | 15-20 | 100% |
| 02 | `tests/cover-letter/infrastructure/test_cover_letter_stack.py` | 10-15 | 90% |
| 03 | `tests/cover-letter/unit/test_cover_letter_logic.py` | 25-30 | 95% |
| 04 | `tests/cover-letter/unit/test_cover_letter_prompt.py` | 15-20 | 90% |
| 05 | `tests/cover-letter/unit/test_fvs_integration.py` | 20-25 | 95% |
| 06 | `tests/cover-letter/unit/test_cover_letter_handler_unit.py` | 15-20 | 90% |
| 07 | `tests/cover-letter/unit/test_cover_letter_dal_unit.py` | 10-15 | 90% |
| 08 | `tests/cover-letter/unit/test_cover_letter_models.py` | 20-25 | 100% |
| 09 | `tests/cover-letter/integration/test_cover_letter_handler_integration.py` | 25-30 | 85% |
| 10 | `tests/cover-letter/e2e/test_cover_letter_flow.py` | 10-15 | 80% |

**Total Test Count:** 165-205 tests
**Overall Coverage Target:** 90%+

---

## Success Criteria

### Per-Task Criteria

Each task is considered COMPLETE when:

1. ✅ **Implementation**: Code written following architectural patterns
2. ✅ **Tests Pass**: All tests for this task pass (GREEN)
3. ✅ **Format**: `ruff format` passes with no changes
4. ✅ **Lint**: `ruff check --fix` passes with no errors
5. ✅ **Type Check**: `mypy --strict` passes with no errors
6. ✅ **Coverage**: Code coverage meets target (90%+)

### Phase-Wide Criteria

Phase 10 is considered COMPLETE when:

1. ✅ All 11 tasks complete
2. ✅ All 165-205 tests pass
3. ✅ Code coverage ≥ 90%
4. ✅ All code quality checks pass (ruff, mypy)
5. ✅ Infrastructure deployed successfully
6. ✅ E2E tests pass against deployed environment
7. ✅ Architect verification complete

---

## Files to Create/Modify

### New Files (9 files)

**Logic:**
1. `src/backend/careervp/logic/cover_letter_generator.py` - Core cover letter logic
2. `src/backend/careervp/logic/prompts/cover_letter_prompt.py` - LLM prompt

**Handlers:**
3. `src/backend/careervp/handlers/cover_letter_handler.py` - Lambda handler
4. `src/backend/careervp/handlers/utils/validation.py` - Validation utilities

**Models:**
5. `src/backend/careervp/models/cover_letter.py` - Pydantic models

**DAL (Optional):**
6. `src/backend/careervp/dal/dynamo_dal_handler.py` - Add DAL methods (modify existing)

**Infrastructure:**
7. `infra/careervp/api_construct.py` - Add Lambda + route (modify existing)
8. `infra/careervp/constants.py` - Add COVER_LETTER constant (modify existing)

**Environment:**
9. `src/backend/careervp/handlers/models/env_vars.py` - Add CoverLetterEnvVars (modify existing)

### Test Files (15 files)

**Fixtures:**
1. `tests/cover-letter/conftest.py` - Pytest fixtures

**Unit Tests (8 files):**
2. `tests/cover-letter/unit/test_validation.py`
3. `tests/cover-letter/unit/test_cover_letter_logic.py`
4. `tests/cover-letter/unit/test_cover_letter_prompt.py`
5. `tests/cover-letter/unit/test_fvs_integration.py`
6. `tests/cover-letter/unit/test_cover_letter_handler_unit.py`
7. `tests/cover-letter/unit/test_cover_letter_dal_unit.py`
8. `tests/cover-letter/unit/test_cover_letter_models.py`
9. `tests/cover-letter/unit/__init__.py`

**Integration Tests (2 files):**
10. `tests/cover-letter/integration/test_cover_letter_handler_integration.py`
11. `tests/cover-letter/integration/__init__.py`

**Infrastructure Tests (2 files):**
12. `tests/cover-letter/infrastructure/test_cover_letter_stack.py`
13. `tests/cover-letter/infrastructure/__init__.py`

**E2E Tests (2 files):**
14. `tests/cover-letter/e2e/test_cover_letter_flow.py`
15. `tests/cover-letter/e2e/__init__.py`

---

## Verification Commands

### Per-Task Verification

After completing each task, run:

```bash
cd src/backend

# Format
uv run ruff format careervp/path/to/file.py

# Lint
uv run ruff check --fix careervp/path/to/file.py

# Type check
uv run mypy careervp/path/to/file.py --strict

# Run tests for THIS task
uv run pytest tests/cover-letter/unit/test_file.py -v

# Expected: All tests for this task PASS
```

### Phase-Wide Verification

After completing all tasks, run:

```bash
cd src/backend

# Format all
uv run ruff format .

# Lint all
uv run ruff check --fix .

# Type check all
uv run mypy careervp --strict

# Run all cover letter tests
uv run pytest tests/cover-letter/ -v --cov=careervp --cov-report=html

# Expected: 165-205 tests PASS, coverage ≥90%
```

### Infrastructure Verification

```bash
cd infra

# Synthesize CloudFormation
npx cdk synth

# Run infrastructure tests
cd ..
uv run pytest tests/cover-letter/infrastructure/ -v

# Expected: All CDK assertions PASS
```

### E2E Verification

```bash
cd src/backend

# Run E2E tests
uv run pytest tests/cover-letter/e2e/ -v

# Expected: All E2E tests PASS
```

---

## Risk Assessment

### High-Risk Tasks (Require Extra Care)

1. **Task 03: Cover Letter Logic** (HIGH RISK)
   - Most complex logic with quality scoring algorithm
   - Multiple scoring dimensions (personalization, relevance, tone)
   - Highest test count (25-30 tests)
   - **Mitigation:** Follow TDD strictly, test each scoring component independently

2. **Task 05: FVS Integration** (MEDIUM-HIGH RISK)
   - Critical for data accuracy and anti-hallucination verification
   - Must detect ALL company name and job title violations
   - **Mitigation:** Use existing fvs_validator.py patterns, comprehensive test coverage

3. **Task 06: Cover Letter Handler** (MEDIUM RISK)
   - Integrates all components (logic, FVS, storage, response formatting)
   - Complex error handling with multiple error codes
   - **Mitigation:** Follow existing handler patterns (cv_upload_handler.py)

### Low-Risk Tasks (Straightforward)

1. **Task 01: Validation Utilities** - Simple validation functions
2. **Task 08: Pydantic Models** - Data model definitions
3. **Task 07: DAL Extensions** - OPTIONAL, follows existing patterns

---

## Common Pitfalls

### Pitfall 1: Skipping Tests
**Problem:** Implementing code without running tests after each task
**Solution:** Run `pytest tests/cover-letter/unit/test_file.py -v` after EVERY task

### Pitfall 2: Modifying Architecture
**Problem:** Changing API contracts or architectural patterns
**Solution:** Follow specs exactly, do NOT deviate from COVER_LETTER_SPEC.md

### Pitfall 3: FVS Bypass
**Problem:** Not validating generated cover letter against FVS baseline
**Solution:** Always call `validate_cover_letter()` before returning result

### Pitfall 4: Incomplete Error Handling
**Problem:** Missing error codes or HTTP status mappings
**Solution:** Follow error handling strategy in COVER_LETTER_SPEC.md

### Pitfall 5: Missing Type Hints
**Problem:** Functions without type annotations
**Solution:** Run `mypy --strict` after every function

### Pitfall 6: Quality Scoring Errors
**Problem:** Quality score calculation doesn't match algorithm
**Solution:** Test each component (personalization, relevance, tone) separately

### Pitfall 7: LLM Response Parsing
**Problem:** Not handling malformed JSON or missing fields from LLM
**Solution:** Add comprehensive error handling and fallback strategies

### Pitfall 8: Timeout Handling
**Problem:** Not properly catching asyncio.TimeoutError
**Solution:** Use asyncio.wait_for() with proper exception handling

---

## Reference Documents

### Architecture & Design
- [COVER_LETTER_DESIGN.md](../../architecture/COVER_LETTER_DESIGN.md) - Complete architecture
- [COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md) - API specification

### Existing Patterns
- [cv_upload_handler.py](../../../src/backend/careervp/handlers/cv_upload_handler.py) - Handler pattern
- [fvs_validator.py](../../../src/backend/careervp/logic/fvs_validator.py) - FVS validation pattern
- [dynamo_dal_handler.py](../../../src/backend/careervp/dal/dynamo_dal_handler.py) - DAL pattern
- [vpr_generator.py](../../../src/backend/careervp/logic/vpr_generator.py) - Logic pattern

### Test Patterns
- [conftest.py](../../../tests/conftest.py) - Existing pytest fixtures
- [test_cv_tailoring_logic.py](../09-cv-tailoring/task-03-tailoring-logic.md) - Logic testing pattern

---

## Task Detail Files

1. [task-01-validation.md](./task-01-validation.md) - Validation Utilities
2. [task-02-infrastructure.md](./task-02-infrastructure.md) - CDK Infrastructure
3. [task-03-cover-letter-logic.md](./task-03-cover-letter-logic.md) - Core Cover Letter Logic
4. [task-04-cover-letter-prompt.md](./task-04-cover-letter-prompt.md) - LLM Prompt Engineering
5. [task-05-fvs-integration.md](./task-05-fvs-integration.md) - FVS Validation
6. [task-06-cover-letter-handler.md](./task-06-cover-letter-handler.md) - Lambda Handler
7. [task-07-dal-extensions.md](./task-07-dal-extensions.md) - DynamoDB DAL (OPTIONAL)
8. [task-08-models.md](./task-08-models.md) - Pydantic Models
9. [task-09-integration-tests.md](./task-09-integration-tests.md) - Integration Tests
10. [task-10-e2e-verification.md](./task-10-e2e-verification.md) - E2E Tests
11. [task-11-deployment.md](./task-11-deployment.md) - Deployment & Verification

---

**Document Version:** 1.0
**Last Updated:** 2026-02-05
**Next Review:** After each task completion
