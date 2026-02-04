# Phase 11: Gap Analysis Implementation Tasks

## Overview

This directory contains all implementation tasks for Phase 11 - Gap Analysis feature. Tasks must be completed in order as they have dependencies.

**Architecture:** See [GAP_ANALYSIS_DESIGN.md](../../architecture/GAP_ANALYSIS_DESIGN.md)
**Specification:** See [GAP_SPEC.md](../../specs/gap-analysis/GAP_SPEC.md)
**Async Foundation:** See [VPR_ASYNC_DESIGN.md](../../architecture/VPR_ASYNC_DESIGN.md)

---

## Important Note: Synchronous Implementation for Phase 11

**Gap Analysis in Phase 11 will be SYNCHRONOUS (like existing VPR handler), NOT async with SQS.**

The async foundation design (VPR_ASYNC_DESIGN.md) is for future phases. For Phase 11:
- Use direct Lambda invocation (no SQS)
- Return results immediately (no polling)
- Follow existing VPR handler pattern

Future phases can migrate to async pattern when needed.

---

## Task List

| Task | File | Description | Tests | Status |
|------|------|-------------|-------|--------|
| 01 | `task-01-async-foundation.md` | Validation utilities (10MB limit) | `test_validation.py` | Not Started |
| 02 | `task-02-infrastructure.md` | CDK changes (minimal for sync) | `test_gap_analysis_stack.py` | Not Started |
| 03 | `task-03-gap-analysis-logic.md` | Business logic & scoring | `test_gap_analysis_logic.py` | Not Started |
| 04 | `task-04-gap-analysis-prompt.md` | LLM prompts | `test_gap_prompt.py` | Not Started |
| 05 | `task-05-gap-handler.md` | Main handler (POST /gap-analysis) | `test_gap_handler.py` | Not Started |
| 06 | `task-06-dal-extensions.md` | DAL methods for gap storage | `test_gap_dal.py` | Not Started |
| 07 | `task-07-models.md` | Pydantic request/response models | Model validation tests | Not Started |
| 08 | `task-08-integration.md` | Handler integration tests | `test_gap_handler.py` (integration) | Not Started |
| 09 | `task-09-verification.md` | Final verification & deployment | All tests | Not Started |

---

## Execution Order

### Phase 1: Foundation (Tasks 01-02)
1. **Task 01:** Validation utilities
2. **Task 02:** Infrastructure updates (minimal)

### Phase 2: Core Logic (Tasks 03-04)
3. **Task 03:** Gap analysis logic
4. **Task 04:** LLM prompts

### Phase 3: Handler & Storage (Tasks 05-07)
5. **Task 05:** Gap analysis handler
6. **Task 06:** DAL extensions
7. **Task 07:** Pydantic models

### Phase 4: Integration & Verification (Tasks 08-09)
8. **Task 08:** Integration tests
9. **Task 09:** Full verification

---

## Testing Strategy

### Test Directory Structure

```
tests/gap-analysis/
├── conftest.py                          # Shared fixtures
├── unit/
│   ├── test_validation.py              # Task 01
│   ├── test_gap_analysis_logic.py      # Task 03
│   └── test_gap_prompt.py              # Task 04
├── integration/
│   ├── test_gap_handler.py             # Tasks 05, 08
│   └── test_gap_dal.py                 # Task 06
├── infrastructure/
│   └── test_gap_analysis_stack.py      # Task 02
└── e2e/
    └── test_gap_analysis_flow.py       # Task 09
```

### Test Execution

```bash
# Run all gap analysis tests
cd src/backend
uv run pytest tests/gap-analysis/ -v

# Run by category
uv run pytest tests/gap-analysis/unit/ -v
uv run pytest tests/gap-analysis/integration/ -v
uv run pytest tests/gap-analysis/infrastructure/ -v
uv run pytest tests/gap-analysis/e2e/ -v

# Run with coverage
uv run pytest tests/gap-analysis/ -v --cov=careervp --cov-report=html

# Coverage target: 90%+
```

---

## Verification Commands (After All Tasks)

```bash
cd src/backend

# Format code
uv run ruff format .

# Lint code
uv run ruff check --fix .

# Type check
uv run mypy careervp --strict

# Run all tests
uv run pytest tests/gap-analysis/ -v --tb=short

# Check coverage
uv run pytest tests/gap-analysis/ --cov=careervp.logic.gap_analysis --cov=careervp.handlers.gap_handler --cov-report=term-missing

# CDK synth (infrastructure)
cd ../../infra
npx cdk synth
```

---

## Architecture Compliance Checklist

Before marking Phase 11 complete, verify:

- [ ] **Rule 1 & 4 (Layered Monarchy):** Handler → Logic → DAL pattern followed
- [ ] **Rule 2 (Security):** 10MB file size limit enforced
- [ ] **Rule 3 (Sync Pattern):** Direct Lambda invocation (NOT async SQS for Phase 11)
- [ ] **Rule 5 (Result Pattern):** All logic functions return `Result[T]`
- [ ] **Validation:** All user inputs validated with Pydantic models
- [ ] **Observability:** AWS Powertools decorators used (@logger, @tracer, @metrics)
- [ ] **Testing:** 90%+ code coverage achieved
- [ ] **Documentation:** All docstrings complete
- [ ] **Existing Code:** No modifications to working code

---

## Success Criteria

### Functional
- [ ] POST /api/gap-analysis generates 3-5 targeted questions
- [ ] Questions scored by impact × probability
- [ ] Questions sorted by gap_score (descending)
- [ ] Maximum 5 questions returned
- [ ] Hebrew language support
- [ ] LLM timeout handling (600s max)
- [ ] Error responses follow spec

### Technical
- [ ] All 50+ tests pass
- [ ] Code coverage ≥90%
- [ ] ruff format passes
- [ ] ruff check passes
- [ ] mypy --strict passes
- [ ] CDK synth succeeds

### Security
- [ ] File size validation enforced
- [ ] User input sanitized
- [ ] JWT authentication required
- [ ] User isolation enforced

---

## Known Issues & Limitations

1. **Synchronous Processing:** Phase 11 uses synchronous Lambda (30s timeout risk for slow LLMs)
2. **Future Migration:** When VPR async is implemented, Gap Analysis can migrate to async pattern
3. **No Job Tracking:** Phase 11 doesn't use DynamoDB jobs table (returns results immediately)

---

## References

- **Design:** [GAP_ANALYSIS_DESIGN.md](../../architecture/GAP_ANALYSIS_DESIGN.md)
- **Spec:** [GAP_SPEC.md](../../specs/gap-analysis/GAP_SPEC.md)
- **Async Foundation (Future):** [VPR_ASYNC_DESIGN.md](../../architecture/VPR_ASYNC_DESIGN.md)
- **Existing Patterns:** [vpr_handler.py](../../../src/backend/careervp/handlers/vpr_handler.py)
- **Test Suite:** [tests/gap-analysis/](../../../tests/gap-analysis/)

---

## Getting Help

If stuck on any task:
1. Review the architecture and spec documents
2. Look at existing VPR handler patterns
3. Check the test files for expected behavior
4. Review the Class Topology Analysis in plan.md
5. Ask the Lead Architect (reference this documentation)
