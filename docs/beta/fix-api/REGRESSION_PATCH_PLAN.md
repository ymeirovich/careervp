# Regression Patch Plan (Low-Risk Ordered)

## Goal
Stabilize the failing backend unit suite by first aligning stale tests to current contracts, then reconciling route/spec artifacts, and only then applying minimal behavioral code changes for true runtime/config drift.

## Scope
- Repo: `careervp`
- Primary failure set: 17 failing tests from `uv run pytest src/backend/tests/unit -q`
- Ordering rule: tests-only changes first, then route/spec reconciliation, then behavioral code changes.

---

## Phase 1: Tests-Only Updates (Lowest Risk)

### 1.1 Gap handler tests: align fixtures and patch targets
Files:
- `src/backend/tests/unit/test_gap_analysis_handler.py`
- `src/backend/tests/unit/test_gap_handler_config_validation.py`
- `src/backend/tests/unit/test_l1_artifact_persistence.py`
- `src/backend/tests/unit/test_l3_trial_credit_charging.py`
- `src/backend/tests/unit/test_l0_gap_analysis_generation.py`

Changes:
- Add/normalize test env fixture values where success paths require them:
  - `GAP_RESPONSES_TABLE_NAME`
  - `DYNAMODB_TABLE_NAME`
- Replace stale `patch('careervp.handlers.gap_handler._get_dal')` with concrete helpers used by code:
  - `_get_questions_dal`
  - `_get_responses_dal`
- In config-validation tests, use full lambda context object (or helper) compatible with Powertools decorators:
  - `function_name`
  - `memory_limit_in_mb`
  - `invoked_function_arn`
  - `aws_request_id`

Acceptance criteria:
- `test_gap_analysis_handler.py` passes without changing production code behavior.
- Config-validation tests fail/succeed for intended reasons (config logic), not missing context attributes.
- No references remain to nonexistent `_get_dal` helper in unit tests.

---

### 1.2 Interview-prep and application-schema expectation refresh
Files:
- `src/backend/tests/unit/test_l0_interview_prep_generation.py`
- `src/backend/tests/unit/test_l3_application_schema.py`

Changes:
- Update interview-prep status-code assertions to current handler contract for negative/failure paths.
- Update application-schema assertions to current repository write schema (or helper adapter output), not legacy `pk`-only assumptions.

Acceptance criteria:
- Assertions reflect actual public behavior and persisted shape currently used by repo code.

---

### 1.3 Payload-count hardcoded tests
Files:
- `src/backend/tests/unit/test_refactor3_artifact_bootstrap.py`
- `src/backend/tests/unit/test_route_smoke_script.py`

Changes:
- Replace hardcoded payload-count assertion (`27`) with either:
  1) Updated canonical count (`28`), or
  2) Dynamic count derived from canonical manifest/source-of-truth file.

Recommended:
- Prefer dynamic expected count sourced from canonical payload registry to reduce future brittleness.

Acceptance criteria:
- Payload-count tests track source-of-truth count and no longer fail on additive payload updates.

---

## Phase 2: Route/Spec Reconciliation (Medium Risk, Non-Behavioral)

### 2.1 Canonical route surface sync
Files:
- `src/backend/tests/unit/test_l6_route_dedup.py`
- `docs/beta/canonical_routes.md`
- `docs/beta/evidence/I7_routes/frozen_spec.json`
- Any generated route diff artifact consumed by tests

Observed drift to reconcile:
- Extra operations currently detected vs frozen spec:
  - `POST /gap-analysis/questions`
  - `POST /users/me/trial/reset`

Decision policy:
- If routes are intentional and deployed: update canonical route docs/spec and route-count expectations.
- If not intentional: remove routes in infra/route map, then regenerate frozen spec artifacts.

Recommended path (lowest operational risk):
- Treat as intentional active surface and update frozen spec + route assertions.

Acceptance criteria:
- `test_l6_route_dedup.py` passes with zero extras/missing routes.
- Canonical docs and frozen spec are consistent with deployed route map.

---

## Phase 3: Behavioral Code Changes (Highest Risk, Minimal and Targeted)

### 3.1 Trial table resolution consistency
Files:
- `src/backend/careervp/handlers/job_handler.py`
- `src/backend/careervp/handlers/user_handler.py`
- `src/backend/careervp/handlers/gap_handler.py` (only if trial path involved)

Issue:
- Trial service may read from table not provisioned in some test/runtime configs.

Change:
- Standardize table env precedence for trial-service construction across handlers.
- Ensure same fallback order everywhere (e.g. `USERS_TABLE_NAME` -> `DYNAMODB_TABLE_NAME` -> `TABLE_NAME`).

Acceptance criteria:
- `test_job_handler.py::test_create_job_returns_201` no longer fails with `ResourceNotFoundException` from trial lookup.
- Trial-related behavior remains unchanged functionally except table-resolution robustness.

---

### 3.2 Gap responses table strictness (only if product decision requires behavior change)
Files:
- `src/backend/careervp/handlers/gap_handler.py`
- Related tests in Phase 1

Current behavior:
- `GAP_RESPONSES_TABLE_NAME` required for responses DAL.

Behavior options:
- Option A (recommended): keep strict requirement and update tests/fixtures only.
- Option B: add compatibility fallback to `DYNAMODB_TABLE_NAME`/`TABLE_NAME`.

Recommended:
- Option A for cleaner separation and less hidden coupling.

Acceptance criteria:
- Explicit env requirement documented and covered by config-validation tests.

---

## Verification Sequence
Run in this exact order after each phase:

1. Phase 1 subset:
- `uv run pytest src/backend/tests/unit/test_gap_analysis_handler.py -q`
- `uv run pytest src/backend/tests/unit/test_gap_handler_config_validation.py -q`
- `uv run pytest src/backend/tests/unit/test_l1_artifact_persistence.py -q`
- `uv run pytest src/backend/tests/unit/test_l3_trial_credit_charging.py -q`
- `uv run pytest src/backend/tests/unit/test_l0_gap_analysis_generation.py -q`
- `uv run pytest src/backend/tests/unit/test_l0_interview_prep_generation.py -q`
- `uv run pytest src/backend/tests/unit/test_l3_application_schema.py -q`
- `uv run pytest src/backend/tests/unit/test_refactor3_artifact_bootstrap.py -q`
- `uv run pytest src/backend/tests/unit/test_route_smoke_script.py -q`

2. Phase 2 subset:
- `uv run pytest src/backend/tests/unit/test_l6_route_dedup.py -q`

3. Phase 3 subset:
- `uv run pytest src/backend/tests/unit/test_job_handler.py -q`
- Re-run gap config tests if `gap_handler.py` changed.

4. Final regression gate:
- `uv run pytest src/backend/tests/unit -q`

---

## Guardrails
- Do not change production behavior during Phase 1.
- In Phase 2, treat canonical route docs/spec as versioned contract artifacts.
- In Phase 3, keep code changes minimal and limited to configuration/contract alignment.
- Every changed test assertion must map to either:
  - current implementation contract, or
  - an updated canonical spec artifact in same patch set.

---

## Deliverables
- Updated tests with no stale helper patches or stale env/context assumptions.
- Reconciled canonical route artifacts and route dedup test.
- Minimal behavioral config fixes (if needed) with passing unit suite.
- Final evidence: clean run of `uv run pytest src/backend/tests/unit -q`.
