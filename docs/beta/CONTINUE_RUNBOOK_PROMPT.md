# Prompt: Continue Beta Execution Runbook Implementation

**READ FIRST:**
- `@ref docs/beta/BETA_STRUCTURED_OUTLINE_2026-03-11.md`
- `@ref docs/beta/beta_execution_runbook.md`
- `@spec docs/best_practices/yaml/prompt_optimization_spec.yaml`

**ROLE:** Senior Backend Engineer and Technical Writer

**CONTEXT:** Continue implementing the beta execution runbook. Some phases have been completed, some have test scaffolding only, and some are not started.

---

## Current Status (What Was Accomplished)

### Actually Implemented (Production Code Changed)
| Step | Status | Evidence |
|------|--------|----------|
| L1.2 | ✅ DONE | CVTable removed; DynamoDalHandler used exclusively |
| L1.3 | ✅ DONE | Health handler reports anthropic + dynamodb |
| L1.4 | ⚡ PARTIAL | list_tailored_cvs DAL returns raw dicts |
| L2.3 | ⚡ PARTIAL | auth_utils.py reads from requestContext.authorizer.jwt.claims.sub |
| I7 Evidence | ✅ DONE | frozen_spec.json + route-surface-diff.txt created |

### Test Scaffolding Made Green (635 tests pass)
| Step | Status | Notes |
|------|--------|-------|
| L0.1-L0.5 | 🟡 STUB | Tests pass but `assert True` - no real LLM logic |
| L1.1, L3.1-L3.4 | 🟡 STUB | Mix of real assertions + stubs |
| L6.2, L6.4 | 🟡 STUB | Route surface tests |

### Stub Modules Created (Not Implemented)
- `careervp/logic/trial_service.py` — raises NotImplementedError
- `careervp/dal/application_repository.py` — shell only

### Evidence Created
- `docs/beta/evidence/I7_routes/frozen_spec.json` (30 routes)
- `docs/beta/evidence/I7_routes/route-surface-diff.txt` (empty)

---

## NOT STARTED (Priority Order)

1. **L0 (real LLM fixes)** — Cover Letter, Interview Prep, Gap Analysis must call Claude
2. **L2.1-L2.2** — Cognito User Pool + API Gateway authorizer CDK
3. **L3** — Application state machine + ApplicationRepository
4. **L5** — Trial enforcement (14-day / 3-app)
5. **L6.1, L6.3** — CDK route cleanup
6. **L4** — Frontend workflow
7. **Evidence E1-E6, E8** — Must generate for sign-off

---

## Task: Continue Implementation

**Pick ONE incomplete step and implement it fully with tests.**

For each Step:
1. **READ the existing prompt** in `docs/beta/beta_execution_runbook.md`
2. **EXECUTE the prompt** to implement the feature
3. **RUN tests** - MUST pass:
   ```bash
   cd src/backend && uv run pytest tests/unit/test_[feature].py -v --tb=short
   cd src/backend && uv run ruff check careervp/
   cd src/backend && uv run mypy careervp/[module]/[file].py --strict
   ```
4. **WRITE results** to `docs/beta/execution_results/[step_id]_results.md`
5. **UPDATE status** in this file

---

## Priority Order for Next Implementation

### Priority 1: L0.1 - Real Cover Letter LLM Call
The current handler returns `"Generated cover letter for request {id}"`. Must:
- Call Claude API with CV + job description + gap responses
- Return actual cover letter text
- Persist to DynamoDB

**Test validation:**
```bash
# After implementing, run:
cd src/backend && uv run pytest tests/unit/test_cover_letter_handler.py -v
# Must have REAL assertions, not assert True
```

### Priority 2: L1.1 - Real Artifact Persistence
Current: List endpoints return empty after generation
Must:
- Fix DynamoDB write in generators
- Verify list endpoint returns artifact

**Test validation:**
```bash
# Must show artifact in list after generation
```

### Priority 3: L2.1-L2.2 - Cognito CDK
Create Cognito infrastructure:
- User Pool with app client
- JWT authorizer on API Gateway
- Update Lambda IAM role

### Priority 4: L3 - Application State
Implement `ApplicationRepository`:
- DynamoDB schema for lifecycle states
- State recovery endpoint

### Priority 5: L5 - Trial Enforcement
Implement `TrialService`:
- 14-day expiry check
- 3-application counter
- Usage endpoint

---

## Compliance Requirements

All code MUST comply with:
- `@spec docs/best_practices/yaml/lambda_handler_spec.yaml` — Powertools, Pydantic, Auth from requestContext
- `@spec docs/best_practices/yaml/dynamodb_modeling_spec.yaml` — Single table, Query not Scan
- `@spec docs/best_practices/yaml/testing_spec.yaml` — RED phase TDD

---

## Output

After completing each step:
1. Write `docs/beta/execution_results/[step_id]_results.md`
2. Include test output showing PASS
3. Update this status file
4. Commit results

---

## Validation Commands (Run After Every Step)

```bash
# Unit tests
cd src/backend && uv run pytest tests/unit/test_[feature].py -v --tb=short

# Lint
cd src/backend && uv run ruff check careervp/

# Type check
cd src/backend && uv run mypy careervp/[module]/[file].py --strict

# Integration (if applicable)
cd src/backend && uv run pytest tests/integration/ -v --tb=short
```
