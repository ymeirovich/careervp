# CareerVP — Coverage Matrix & Frontend Can't-Break Contract

**Purpose:** Define ALL functionality (the definitive test surface) and the exact
frontend response contract the DB redesign must not break. Built from four
ground-truth passes: backend API contract, async/scheduled surface, frontend
touchpoints, and test coverage. Reconciled to `main @ 4f7c294` (2026-06-29).

> **Oracle warning:** the OpenAPI spec (`careervp-api-v1.yaml`) is **drifted** and one
> `docs/swagger/openapi.json` is an unrelated "orders" stub. The **deployed truth** is
> CDK `route_map` + four `{proxy+}` proxies + in-Lambda routers. The **authoritative
> "must-not-break" contract is what `src/frontend/` actually calls** (below), NOT any
> doc. Do not generate the test surface from the spec — it would silently drop ~20
> real endpoints.

---

## 1. Functionality surface (the coverage matrix)

Legend: **Tested** = has a real, non-stubbed test · **FE** = frontend depends on it ·
⚠️ = coverage compromised by the autouse resolver stub.

### 1a. HTTP endpoints
Auth: `/auth/*` proxy is `authorized=False` → all auth sub-routes public at the
gateway (Lambda enforces). Public allowlist: `/health`, `/auth/*`, `/billing/webhook`,
`/errors`, `/swagger*`.

| Endpoint | Handler | Tested | FE | Notes |
|---|---|---|---|---|
| POST /auth/register·login·refresh·logout | auth_handler | ✅ | ✅ | logout not in spec |
| GET /health | health_handler | ✅ | — | |
| GET·PUT /users/me | user_handler | ⚠️ | ✅ | |
| GET /users/me/usage | user_handler | ⚠️ | ✅ | trial + app counters |
| GET /users/me/subscription | billing_handler | ⚠️ | ✅ | BillingInfoCard |
| POST /users/me/cv · GET /users/me/cv[/{id}] · DELETE /users/me/cv/{id} | cv_upload/user_handler | ⚠️ | ✅ | DELETE hidden behind `/users` proxy, not in spec |
| POST /users/me/trial/reset | user_handler | ⚠️ | — | not in spec |
| POST /jobs · GET /jobs · GET /jobs/{id} | job_handler | ⚠️ | ✅ | `/jobs/{id}` renames `role_title`→title, `company`→company_name |
| POST·GET /jobs/{id}/gap-questions · POST /jobs/{id}/gap-responses | gap_handler | ⚠️ | ✅ | also reachable via `/gap-analysis/*` proxy |
| GET /applications/{application_id} | application_handler | ⚠️ | ✅✅ | **THE hub read — linchpin.** Not in spec |
| POST /vpr/generate · GET /vpr/{id}/status · POST /vpr/{id}/cancel · GET /vprs | vpr_submit/vpr_status | ✅ | ✅ | spec says `/vpr/{id}` (drift) |
| POST /cv-tailoring/generate · GET /{id}/status · PATCH · DELETE · POST /{id}/cancel · GET /cv-tailorings | cv_tailoring_handler | ⚠️ | ✅ | |
| POST /cover-letter/generate · GET /{id}/status · PATCH · POST /{id}/cancel · GET /cover-letters | cover_letter_(submit_)handler | ⚠️ | ✅ | |
| POST /interview-prep/generate · GET /{id}/status · PATCH · POST /{id}/cancel · GET /interview-preps | interview_prep_(submit_)handler | ⚠️ | ✅ | |
| POST /company-research/fetch · GET /company-research/{jobId} · POST /{jobId}/cancel | company_research_handler | ✅ | ✅ | status-envelope |
| GET /knowledge-base | company_research_func | ❌ | — | `knowledge_base_handler` is dead/unwired |
| POST /ai/assist | ai_assist_handler | ⚠️ | ✅ | not in spec/route_map |
| GET /jobs/{id}/artifacts/{type}/export | export_handler | ⚠️ | ✅ | presigned download_url; PDF=501 |
| POST /billing/checkout · /billing/portal | billing_handler | ✅(svc) | ✅ | **hidden behind `/billing` proxy — not in spec/route_map** |
| POST /billing/webhook | billing_handler | ✅(svc) | — | public; self-verifies signature |
| POST /errors · GET /swagger* | error_report/swagger | ⚠️/❌ | ✅ | telemetry / docs |

**Dead/orphaned:** `vpr_handler.py` (sync generator removed), `knowledge_base_handler.py`.

### 1b. Async behaviors (35 total — see async report for full list)
Queues → workers: cv-upload (S3-triggered), vpr-jobs, company-research,
cover-letter-jobs, interview-prep-jobs; `artifacts_table` stream → cv-tailor worker.
SFN chain: CompanyResearch → VPR → (choice) → CVTailoring → {CoverLetter ∥ InterviewPrep},
task-token + heartbeats + per-state catch → failure handlers.

- ⚠️ **Only VPR DLQ has a reaper.** 8 other DLQs silently expire after 14d.
- 🐛 **Billing reconcile entrypoint mismatch** — infra `billing_reconcile_handler.handler`
  vs source `lambda_handler` → nightly reconcile fails at invoke.
- Un-tested reliability: `batchItemFailures` only on CR worker (F4); zero `@idempotent` (F3).
- Dead: `vpr-worker` Lambda (no event source), `gap-analysis-queue` + `jobs_table` stream (no consumer).

### 1c. Scheduled (EventBridge)
- Hourly `artifact_cleanup` — **destructive** (deletes S3 results; CANCELLED/STOPPED-chain jobs).
- Nightly 02:00 `billing_reconcile` — calls payment provider (currently broken, see 🐛).

### 1d. Coverage reality
- **78.45% line coverage, branch-rate = 0** — error/`ValidationException` branches invisible.
- **~30 handler tests neutralized** by autouse `mock_artifact_dependency_resolver` +
  `mock_company_research_load` → the gate/routing path (where the dossier bug lives) is
  not really tested. High % is inflated.
- Weakest: `logic.utils` (32% — web/scraper/circuit-breaker), `handlers.utils`/`handlers.models`.

---

## 2. Frontend can't-break contract (the guardrail)

Active app: `src/frontend/` (Axios → `NEXT_PUBLIC_API_URL`, Bearer). Repo-root
`frontend/` is a dead legacy tree. **These are hard constraints on the DB redesign.**

1. **`application_id == job_id` — ONE identifier, two names.** The hub is
   `GET /applications/{jobId}`; `application.application_id` must equal the path
   `job_id`. `useGenerateModule` sends `application_id=jobId` (VPR/CL/IP) and
   `job_id=jobId` (CV-tailoring/CR). **If the redesign splits these, every generate/hub
   call breaks.** → the external handle must stay unified (core may subsume both internally).
2. **`artifact_id` is the round-tripped opaque key.** UI reads
   `artifacts.{module}.artifact_id` from the hub and feeds that exact string into
   `/{module}/{id}/status`, `PATCH`, cancel. **A hub `artifact_id` MUST be directly
   resolvable by the status endpoint.** (This is exactly dossier requirement #2 — give
   artifacts a real stored key.)
3. **`vpr_id` = the VPR's hub `artifact_id`**, passed into CL/IP/CV generate. The
   dossier's identifier defect, confirmed from the UI. The redesign must keep VPR's
   external id stable and hub-surfaced. **CV-tailoring sends `vpr_id: null` (never
   omitted)** — the null-vs-absent distinction is load-bearing (backend detects new-API flow).
4. **Status enum is hard-coded, string-compared, unversioned:**
   `pending|processing|completed|failed|cancelled|expired` (+ `not_generated`, `edited`).
   Unknown → `notStarted`. **Changes must be additive/versioned.** 3s polling loop
   branches solely on `status`, stops on completed|failed|cancelled.
5. **PATCH optimistic concurrency:** must echo `result.*` + `version` + `updated_at`,
   and return **HTTP 409** on stale `base_version`. Autosave/ConflictModal keys on 409.
6. **`request_id` primacy** for async generate (`request_id ?? job_id`). Dropping it
   breaks polling for every module.
7. **Nested `result` shapes** each view destructures directly (VPR `download_url`→S3
   `VPRFullData` tree; CV `result.cv_sections` deep tree + `ats_grade` green/yellow/red;
   IP `result.questions[].id` stable key; CL `result.cover_letter`). Must be preserved.
8. **Presigned `download_url` side channel** + `status:'expired'` signal for aged VPRs;
   FE distinguishes S3 403/401 as "session expired."
9. **Shape polymorphism already tolerated** (must not worsen): CR status-envelope;
   `recent_news` string|object; list endpoints bare-array|wrapped; `cvs[0]` = default CV.
10. **Error envelope:** `error|message`, `classification`, `error_code`, `field`; 401 →
    one silent refresh-retry then sign-out.

**Net:** the redesign is a **data-layer + internal-identifier change that must keep the
API response shapes stable** (or version the route). The internal PK (`USER#{sub}`) is
free to change — the UI only constrains `application_id`/`artifact_id`/status/`version`.

---

## 3. Migration already in progress (do not restart)

`FE-UI-044` implemented a **CR canonical-store migration** — dual-write + backfill of
239 legacy company-research items `users-table → artifacts-table` — with tests in flight
(`test_cr_migration_backfill`, `test_cr_dual_read_legacy`, `test_cr_canonical_store_roundtrip`,
`test_dal_migration_integration`). The expand→dual-write→backfill→dual-read pattern is
**already proven on one entity.** Current state = partial migration; finish and extend
the pattern to remaining entities rather than starting over. `docs/upgrade/specs/`
also holds `TEST-DEBT-001` and `TEST-CHAIN-001` (existing test-debt backlog + prompts).

---

## 4. Test-surface gaps to close (feeds test-strategy)

- Make the autouse resolver/CR mocks **opt-in**; drive real `resolve_dependencies`
  against **moto tables with the actual key schemas** (`pk/sk`, `applicationId/artifactId`, `job_id`).
- **Turn on branch coverage.**
- **Whole-chain-to-persisted-result** tests (gap→CR→VPR→{CV,CL,IP}); assert ONE stored key, not three.
- **Replay-same-event** idempotency gate (webhook + every worker).
- **`batchItemFailures`** gate on VPR/CL/IP workers (copy CR worker's pattern).
- **Cross-tenant isolation** negative test (the `x-user-id` fallback in `auth_utils.py` has none).
- Characterize the shipped-but-untested chain (TEST-DEBT-001), esp. the routing/gate path.
