## Regression Recovery + YAML2 100% Completion Plan

### Summary
Goal: restore behavior to at least `live-test-results27.log` quality, then fully satisfy every acceptance criterion in `/docs/beta/fix-api/yaml2/*` without introducing new regressions.

Execution model: **Hybrid Revert+Fix** (selected default because it is the safest path to recover quickly and still reach full spec compliance).

Confidence model: no promotion unless all gates pass:
1. Spec traceability gates (AC-by-AC evidence).
2. Regression gates (non-2xx + empty-array checks).
3. Live e2e gates (targeted + full suite, repeated).

---

### Public API / Interface Changes (Explicit)
1. `GET /jobs/{jobId}/gap-questions`:
- Keep success shape for persisted data.
- Return explicit non-2xx on DAL/storage failure (instead of silent empty `200`).

2. `GET /cover-letter/{id}/status` and `GET /cover-letters`:
- Canonical read path must use artifacts-table keys (`applicationId`, `artifactId`), with optional legacy fallback read only if needed.
- Unknown ID remains `404` with domain code.

3. `GET /vprs`:
- Preserve response schema.
- Ensure generated VPR appears in list deterministically (pagination + filtering fix).

4. Interview prep status flow:
- Keep existing response schema.
- Live test logic must only quality-assert completed payloads (processing status should continue polling).

5. Infra/runtime interface addition:
- Add dedicated `GAP_QUESTIONS_TABLE_NAME` env var to remove ambiguous table resolution.

---

### Regression-to-Change Mapping

| Spec | Regression to reverse | Code changes | Validation gate |
|---|---|---|---|
| `GAP_GET_002` ([spec](/Users/yitzchak/Documents/dev/careervp/docs/beta/fix-api/yaml2/gap_questions_read_after_write.yaml)) | `28`: POST gap questions `500 DYNAMODB_ERROR`; `27`: GET returned empty array | Fix table resolution in [gap_handler.py](/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/gap_handler.py) (remove/last-priority `ARTIFACTS_TABLE_NAME` for gap question reads/writes), add `GAP_QUESTIONS_TABLE_NAME` in [api_construct.py](/Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py), keep strict POST persistence gate, make GET DAL failures non-2xx | Unit: `test_gap_handler_persistence_required.py`, `test_gap_dal_job_id_filter.py`; Integration: `test_gap_read_after_write_roundtrip.py`; Live: `test_05_gap_analysis.py` + strict contract payload |
| `COVER_LETTER_002` ([spec](/Users/yitzchak/Documents/dev/careervp/docs/beta/fix-api/yaml2/cover_letter_list_roundtrip.yaml)) | `28`: status 404 for generated ID + list empty | **Phase A (this step)**: unify writes to canonical `applicationId/artifactId` schema; retain legacy `pk/sk` read fallback (`COVER_LETTER_LEGACY_READ_ENABLED=true`) in [cover_letter_handler.py](/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/cover_letter_handler.py) and [dynamo_dal_handler.py](/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/dal/dynamo_dal_handler.py); remove “success despite persistence failure” behavior; keep unknown-id 404. **Phase B** (follow-on): remove legacy fallback after `check_cover_letter_key_schema.py` audit confirms zero legacy records remain | Unit: `test_cover_letter_status_storage_keys.py`, `test_cover_letter_list_includes_generated_artifact.py`; Integration: `test_cover_letter_roundtrip_persistence.py`; Live: `test_07_cover_letter.py`; Pre-Phase-B: `AC-CL-MIGRATE-001` key-schema audit |
| `VPR_LIST_METADATA_001` ([spec](/Users/yitzchak/Documents/dev/careervp/docs/beta/fix-api/yaml2/vpr_list_metadata_backfill.yaml)) | `28`: generated VPR ID missing after 60s | Fix `get_vpr_jobs_by_user` pagination/filter behavior in [jobs_repository.py](/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/dal/jobs_repository.py) so filtered results are collected across pages; keep metadata fallback in [vpr_status_handler.py](/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/vpr_status_handler.py) | Unit: `test_vpr_status_handler.py`; Live: `test_04_vpr.py::test_list_vprs` |
| `CV_TAILORING_002` ([spec](/Users/yitzchak/Documents/dev/careervp/docs/beta/fix-api/yaml2/cv_tailoring_delete_route_completion.yaml)) | `28`: DELETE returns `403 DEFAULT_4XX`; **root cause unconfirmed** (H1: integration missing, H2: auth mismatch — both `requires_diagnosis`) | **Run `check_deployed_parity.py --filter-route "DELETE /cv-tailoring/{cvTailoringId}"` before any code change** to confirm H1 vs H2; apply only the confirmed conditional fix to [api_construct.py](/Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py); verify handler delete branch in [cv_tailoring_handler.py](/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/cv_tailoring_handler.py) | Unit: `AC-CVT-300` (diagnosis artifact); route surface test; Live: `test_delete_tailored_cv_roundtrip` |
| `TRIAL_002` ([spec](/Users/yitzchak/Documents/dev/careervp/docs/beta/fix-api/yaml2/trial_and_contract_route_alignment.yaml)) | historical route mismatch/false trial diagnosis; **route alias risk**: `/gap-analysis/questions` may appear in legacy contract payload files — canonical route is `/jobs/{jobId}/gap-questions` | Audit `docs/refactor2/api_contract_payloads` for legacy alias (AC-TR-300); keep canonical contract path assertion in [test_10_api_contract_success.py](/Users/yitzchak/Documents/dev/careervp/docs/refactor/live_tests/test_10_api_contract_success.py); add no-alias assertion in `test_contract_route_parity.py`; keep endpoint-level attribution logs/metrics in [gap_handler.py](/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/gap_handler.py) | Unit: `test_trial_credit_attribution.py`; Integration: `test_contract_route_parity.py::test_no_legacy_route_alias_in_payloads`; Live strict contract suite must be fully green |
| `INTERVIEW_PREP_002` ([spec](/Users/yitzchak/Documents/dev/careervp/docs/beta/fix-api/yaml2/interview_prep_status_schema_alignment.yaml)) | `26` had 404 not found; `28` now 200 processing but quality fails | Keep artifacts-schema status behavior in [interview_prep_handler.py](/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/interview_prep_handler.py); ensure completed responses include full `result`; adjust live test polling condition to quality-assert only when completed | Unit/integration existing interview-prep suites + live `test_08_interview_prep.py` |
| `INTERVIEW_PREP_003` ([spec](/Users/yitzchak/Documents/dev/careervp/docs/beta/fix-api/yaml2/interview_prep_agentic_architecture_alignment.yaml)) | `28` async path can end `failed` with empty questions | Stabilize context resolution and worker completion path in [interview_prep_handler.py](/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/interview_prep_handler.py), [logic/interview_prep.py](/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/logic/interview_prep.py), [interview_prep_prompt.py](/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/logic/prompts/interview_prep_prompt.py) | Unit: prompt/context/l0 tests; Integration: roundtrip/context-source; Live: `test_08_interview_prep.py` |

---

### Step-by-Step Execution Plan

### Phase 1: Recovery Scaffold (No feature work yet)
1. Create branch: `hotfix/yaml2-regression-recovery`.
2. Freeze baseline evidence:
- Keep `live-test-results26.log`, `27.log`, `28.log` as immutable comparison set.
3. Add a regression parser script (new CI gate):
- Compute per endpoint: non-2xx count, empty-array count, generated-ID-missing cases.
- Output machine-readable artifact (`json`) for PR checks.
4. Create AC tracker for all yaml2 specs:
- Extract all AC IDs + required tests/evidence into one checklist file.
- CI fails if any AC has no mapped evidence.

### Phase 2: Restore to “>=27 parity” (stabilization)

**Targeted smoke gate (mandatory for every step deploy in Phases 2 and 3):**
After each step is deployed, before the two-pass full suite, run:

```sh
uv run python scripts/smoke/run_targeted_smoke.py --step RECOVERY_00X \
  --out docs/evidence/targeted-smoke-RECOVERY_00X-<timestamp>.json
```

This validates 5 critical endpoints in under 3 minutes (gap POST, cover-letter status, VPR list,
CV tailoring DELETE not-403, interview-prep status). Smoke failure immediately triggers the
step's rollback_trigger_matrix. Do not proceed to the two-pass suite if smoke fails.

**Per-step regression delta check (after each smoke passes):**

```sh
uv run python scripts/spec_quality/check_regression_delta.py \
  --baseline careervp/live-test-results27.log \
  --current docs/evidence/targeted-smoke-RECOVERY_00X-<timestamp>.json \
  --out docs/evidence/per-step-regression-delta-RECOVERY_00X-<timestamp>.json
```

Block promotion of the step if delta shows any new non-2xx or empty-array regression.
This is a per-step check, not deferred to Phase 4.

**Step execution order and parallelization:**

- RECOVERY_001 completes first (all others depend on it).
- RECOVERY_002 (GAP) completes before RECOVERY_007 (Trial) due to shared attribution changes.
- RECOVERY_003, 004, 005, 006 each depend only on RECOVERY_001 and may run in parallel.
- Recommended grouping: RECOVERY_001 → {002} → {003, 004, 005, 006 in parallel} → {007} → {008}.
- **RECOVERY_005 prerequisite**: run diagnosis_gate (H1/H2 check) before writing any infra code.
- **RECOVERY_003 prerequisite**: COVER_LETTER_LEGACY_READ_ENABLED=true must be set (Phase A deploy).

1. Apply GAP fixes first (highest blast radius). Run smoke + delta after deploy.
2. In parallel: cover-letter dual-read fix, VPR pagination fix, CV tailoring DELETE (post-diagnosis), interview-prep quality fix. Run smoke + delta independently after each deploy.
3. Re-run targeted live tests for each step domain after smoke passes:

   - `test_05_gap_analysis`
   - `test_04_vpr`
   - `test_07_cover_letter`
   - `test_06_cv_tailoring`

4. Gate: parity pass criteria (enforced per step, not deferred to Phase 4)

   - No new non-2xx beyond baseline allowlist.
   - No new empty arrays on generated-resource list/read paths.
   - Must meet or exceed `27` outcomes for VPR inclusion and interview-prep status resolvability.

### Phase 3: Complete remaining yaml2 acceptance criteria
1. Implement residual edge-case logic per spec ACs.
2. Update/add missing tests listed in each yaml2 validation plan.
3. Ensure spec traceability entries have real evidence links/output.
4. Set each yaml2 spec status to `implemented` only after all gates pass.

### Phase 4: Full validation and anti-regression hardening
1. Run local/unit/integration suites for all touched domains.
2. Run strict contract suite.
3. Run full live suite end-to-end **twice** (two consecutive greens required).
4. Run regression parser against new live output and compare to `26/27/28`.
5. Promotion gate:
- 7/7 yaml2 specs pass AC checklist.
- Contract suite green.
- Live full suite green twice.
- Regression parser shows improvement from `28` and no degradation from `27`.

### Phase 5: Controlled rollout + rollback protocol

1. Deploy to dev-live only.
2. Execute targeted smoke immediately after deploy (`scripts/smoke/run_targeted_smoke.py`).
   The 5 assertions checked: gap POST persistence, cover-letter status resolvable,
   VPR list includes generated ID, CV tailoring DELETE not-403, interview-prep status resolvable.
3. If targeted smoke fails on any assertion:
   - Identify the failing endpoint from the JSON output.
   - Revert only the offending step's change-set commit(s), not the full branch.
   - Re-run targeted smoke on the reverted state to confirm clean.
   - Re-run targeted domain live tests before redeploy.
4. If targeted smoke passes, run per-step regression delta check before two-pass full suite.
5. Promote only after all Phase 4 gates hold and targeted smoke + delta checks are clean.

**New scripts required before Phase 2 begins (built in RECOVERY_001):**

- `scripts/smoke/run_targeted_smoke.py` — targeted smoke runner
- `scripts/spec_quality/check_regression_delta.py` — per-step and final delta checker
- `scripts/spec_quality/check_deployed_parity.py` — route/auth/env parity checker
- `scripts/spec_quality/check_evidence_integrity.py` — evidence artifact validator
- `scripts/spec_quality/check_yaml2_closure.py` — final yaml2 AC closure verifier
- `scripts/spec_quality/check_cover_letter_key_schema.py` — cover letter schema audit (for Phase B gate)

---

### Test Cases and Scenarios (Must Pass)
1. Gap read-after-write:
- POST questions success implies GET returns persisted questions (>=3).
- DAL failure yields non-2xx with explicit code.

2. Cover letter roundtrip:
- POST returns request ID.
- Status resolves same ID.
- List contains generated ID within polling window.
- Unknown ID returns domain 404.

3. VPR list:
- Generated VPR appears in `/vprs` within polling window.
- Metadata fields non-empty when resolvable.
- No cross-user leakage.

4. CV tailoring delete:
- Create -> delete -> verify absence from list/status behavior.
- Unknown delete returns 404.

5. Trial/contract:
- Canonical route parity holds.
- No `DEFAULT_4XX` for contract-covered routes.
- Trial credit attribution logs include endpoint + before/after usage.

6. Interview prep:
- Generated ID resolves via status.
- Quality assertions run only on completed payload.
- Completed payload has >=3 usable questions.
- Failure path includes deterministic reason (not silent empty-only payload).

---

### How We Guarantee “100% Followed”

1. Machine-enforced AC checklist derived from yaml2 specs (CI required).
2. Every AC must map to:
   - Code location,
   - Unit/integration/live test,
   - Evidence artifact path.
3. Status cannot be flipped to `implemented` without all mappings green.
4. Two-run live stability requirement prevents one-off false greens.
5. Per-step regression delta checker prevents hidden regressions from being deferred to Phase 4.
6. Targeted smoke (<3 min) provides fast rollback signal before the two-pass suite runs.
7. CV tailoring root cause confirmed via diagnosis_gate before any infra code is written.
8. Cover letter uses Phase A dual-read (legacy fallback enabled) with Phase B gated on key-schema audit.
9. Contract payload files audited for legacy route aliases (`/gap-analysis/questions`) before RECOVERY_007 closes.
10. All gate scripts (`check_regression_delta.py`, `check_deployed_parity.py`, `check_evidence_integrity.py`,
    `check_yaml2_closure.py`, `run_targeted_smoke.py`, `check_cover_letter_key_schema.py`) must be
    built and verified as part of RECOVERY_001 before any other step proceeds.

---

### Assumptions and Defaults
1. Default strategy: **Hybrid Revert+Fix**.
2. Deployment target for validation is current dev-live API.
3. Required credentials for live tests and AWS route inventory are available.
4. Untracked `.tmp/` content is treated as non-release artifact and ignored unless it affects test/deploy tooling.
