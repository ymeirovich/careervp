# SEQUENCING GUIDE — FE-UI-053 + FE-UI-054 (DO NOT run as /goal)
# Run the three sub-handoffs below in order. Each is a separate /goal session.
#
# Gate:  run FE-UI-053-backend first → confirm artifacts-table contract → then
#        run FE-UI-054-frontend and FE-UI-053-054-deploy in parallel or series.
#
# Sub-handoffs:
#   docs/upgrade/handoff/FE-UI-053-backend-handoff.md   (Sonnet)
#   docs/upgrade/handoff/FE-UI-054-frontend-handoff.md  (Sonnet, after backend gate)
#   docs/upgrade/handoff/FE-UI-053-054-deploy-handoff.md (Opus, after both green)
#
# Original monolithic plan preserved below for reference.
# ==============================================================================

# [ARCHIVED] /goal Handoff — IMPLEMENT FE-UI-053 + FE-UI-054 (CR async enqueue + polling)

GOAL: Finish and verify the Company Research async wiring + session-independent
polling. A prior session landed PARTIAL, UNVERIFIED backend+infra edits. Do NOT
trust them — verify first, then complete frontend + all tests + deploy.

Specs (authoritative): docs/upgrade/specs/FE-UI-053-cr-enqueue-and-status.yaml,
FE-UI-054-cr-polling-session-independent.yaml, TEST-FE-053-test-prompts.yaml,
TEST-FE-054-test-prompts.yaml. Working dir: /Users/yitzchak/Documents/dev/careervp.

## STATE AS OF HANDOFF (uncommitted, branch ui-upgrade, NOT verified, NOT deployed)
DONE (code only, no lint/mypy/test run):
- company_research_store.py: added write_cr_processing(), _has_terminal_cr_row(),
  _utc_now_iso(), _TERMINAL_CR_STATUSES, __all__ entry. (FE-UI-053 R2)
- company_research_handler.py: _fetch_company_research now enqueues SQS
  (COMPANY_RESEARCH_QUEUE_URL) + write_cr_processing + 202; removed asyncio.run /
  research_company / write_cr_artifact / CompanyResearchResult imports + dead
  _persist_company_research_item; GET returns {status:processing} for processing
  rows. (FE-UI-053 R1, R3)
- api_construct.py: company_research_queue.grant_send_messages(company_research_func)
  + COMPANY_RESEARCH_QUEUE_URL env, near the CR-worker chain wiring. (FE-UI-053 R4)
NOT DONE (must do this session): FE-UI-053 R6 (write_cr_failed + worker hard-fail
call — see STEP 1), landmine #3 cleanup (STEP 0), all 4 test files, frontend
FE-UI-054, every verification command, deploy + smoke.

## START HERE (ordered — do not skip)

### STEP 0 — Verify the inherited edits (trust nothing)
- Re-read the 3 modified files; confirm they match FE-UI-053 R1–R4.
- Run: `cd src/backend && uv run ruff format . && uv run ruff check --fix .`
- Run: `cd src/backend && uv run mypy careervp/handlers/company_research_handler.py
  careervp/logic/company_research_store.py --strict`
- Resolve landmine #3 (mechanical): (a) job_posting_url is HttpUrl|None — build the
  SQS url from raw_payload['url'] primarily, fall back to str(request.job_posting_url)
  guarded against None (worker also re-hydrates from jobs table). (b) DELETE the now-
  unused _map_result_code_to_status (zero callers; keeps module clean for SC7).
- Confirm: write_cr_processing writes ARTIFACTS_TABLE_NAME; GET's read_cr_artifact
  reads the SAME table (artifactType=='company_research' + user_id match required).

### STEP 1 — Worker-failed-row reconciliation (DEFINED TASK — FE-UI-053 R6)
CONFIRMED gap (already investigated): the worker records failure ONLY on the
application record (_hard_fail → update_artifact_status='failed'), never on the
ARTIFACTS table that GET reads. With the new processing placeholder, a hard-failed
job is left as 'processing' forever. Implement Option A (single source of truth =
artifacts table) per FE-UI-053 R6 + SC8:
- Add write_cr_failed(application_id, user_id) to company_research_store.py — puts
  {key, artifactType, user_id, status:'failed', created_at}.
- Call it from company_research_worker_handler._hard_fail (alongside the existing
  app-record updates).
- GET needs NO change (_is_confident_cr already maps status=='failed' → failed).
Prove via TEST-FE-053 § worker_failed_row (SC5, SC8).

### STEP 2 — Author backend tests (TEST-FE-053; author then make pass)
Per TEST-FE-053 sections: post_enqueue (SC1,SC2,SC3), get_status (SC4),
store_idempotency (SC5), infra_synth (SC6,SC7). Files:
src/backend/tests/unit/test_company_research_handler.py,
test_company_research_store.py, infra/tests/test_cr_enqueue_infra.py (new).
Patch careervp.handlers.company_research_handler.boto3 for SQS asserts.
Run: `cd src/backend && uv run pytest tests/unit/test_company_research_handler.py
tests/unit/test_company_research_store.py -q` ; `cd infra && uv run pytest
tests/test_cr_enqueue_infra.py -q && npx cdk synth`.

### STEP 3 — Implement frontend FE-UI-054
File: src/frontend/app/applications/[id]/company-research/page.tsx. Per spec R1–R4:
- R1/R2 move poll loop OUT of handleTrigger into a status-keyed useEffect; on mount
  call api.getCompanyResearchStatus(jobId) (status-aware) — NOT getCompanyResearch(),
  which collapses non-completed to null. If `processing` auto-resume polling (survives
  reload + navigation; server row is source of truth). getCompanyResearchStatus
  already returns status verbatim (methods.ts ~L113) — verify, no change expected.
- R3 terminal map: completed→card, failed→error, processing→keep polling,
  not_generated→idle "Run research" CTA (NOT error). Note current page treats
  not_generated as error (~L61) — fix.
- R4 10s cadence, 5min cap, then "still running — refresh later" (no cancel).

### STEP 4 — Author frontend tests (TEST-FE-054)
File: src/frontend/tests/ui/unit/CompanyResearchPage.test.tsx. Sections:
mount_polling (SC1,SC5), remount_resume (SC1,SC2), not_generated_cta (SC3),
terminal_states (SC4). vitest fake timers + mocked GET.
Run: `cd src/frontend && npm run typecheck && npm run test:unit &&
npm run test:integration && npm run test:e2e`.

### STEP 5 — Live re-verification BEFORE deploy (state may have drifted)
- `aws lambda list-event-source-mappings --function-name
  careervp-company-research-worker-lambda-dev --region us-east-1` → mapping ENABLED.
- `aws sqs get-queue-url --queue-name careervp-company-research-queue-dev` → exists.
- Confirm CR API handler timeout still ≤ API GW 29s integration limit is NOT the
  blocker anymore (enqueue path returns fast; the 60s Lambda timeout is fine since
  it no longer runs research synchronously).
- `cd infra && npx cdk diff` → review ONLY the CR queue grant + env var delta.

### STEP 6 — Deploy + smoke (only after all green + user OK to deploy)
- Deploy per repo convention. Then end-to-end: POST /company-research/fetch →
  confirm a message lands on the queue, worker Lambda fires (CloudWatch), a
  processing row appears, GET flips processing→completed/failed, frontend renders.

## DEFINITION OF DONE
- [ ] STEP 0 lint+mypy clean on the 3 inherited files + landmine #3 resolved.
- [ ] STEP 1 R6 implemented: write_cr_failed added + called from worker _hard_fail.
- [ ] FE-UI-053 SC1–SC8 all proven by TEST-FE-053 (backend pytest + cdk synth green).
- [ ] FE-UI-054 SC1–SC6 all proven by TEST-FE-054 (typecheck+unit+integration+e2e green).
- [ ] Reload AND navigate-away-return both resume polling to terminal (SC1/SC2).
- [ ] STEP 5 live checks pass; cdk diff scoped to CR grant+env only.
- [ ] Deploy + smoke green (gated on explicit user approval to deploy).
- [ ] Commit per repo rules (safe_commit.sh); no deploy/commit without user OK.

## CONSTRAINTS
- Verify-first: inherited edits are unproven; let tests/types/synth be the judge.
- No commit, no deploy without explicit user approval.
- Backend mandatory checks (CLAUDE.md): ruff + mypy --strict on changed modules;
  pytest unit. Frontend: typecheck + unit + integration + e2e.
