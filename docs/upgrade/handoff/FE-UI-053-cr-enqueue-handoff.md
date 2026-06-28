# /goal Handoff — CR Async Enqueue + Session-Independent Polling

GOAL: Connect the deployed-but-orphaned Company Research async pipeline and make
status polling survive reload/navigation. This run AUTHORS 4 files only (2 specs
+ 2 test-prompts). No code edits, no deploy.

ID MAP (renumbered, relationship explicit):
- FE-UI-053  backend  spec   → TEST-FE-053 (its tests)
- FE-UI-054  frontend spec   → TEST-FE-054 (its tests)
FE-UI-054 depends_on FE-UI-053. Both depend_on FE-UI-030 (worker), FE-UI-029 (chain/DAL).

## OUTPUT OPTIMIZATION MANDATE (apply to every file you write)
- Match the TERSE house format of TEST-FE-052-test-prompts.yaml, NOT the verbose
  prose of FE-UI-030.yaml. Bullet requirements, no narrative paragraphs.
- Each file SELF-CONTAINED: a /goal run must execute it without reading the
  codebase first. Inline the contract + file refs it needs.
- Reference SYMBOLS (function/class names) as primary anchors; line numbers are
  secondary hints only — add "verify symbol, lines may have drifted".
- Cross-link by ID (R1, SC1, T1) instead of restating text.
- Target sizes: each spec ≤120 lines, each test-prompt ≤90 lines.
- recommended_model: sonnet on all 4 (pattern-following, no novel architecture).

## CONTEXT (ground truth — do not re-discover)
- Async infra is LIVE: queue `careervp-company-research-queue-dev`, DLQ, worker
  `careervp-company-research-worker-lambda-dev` with ENABLED SQS event source.
  Worker code complete. Only the ENQUEUE link is missing.
- BUG: handler `_fetch_company_research` runs `asyncio.run(research_company())`
  inline, returns fake `202 processing`, persists nothing when confidence <0.85 →
  GET returns `not_generated`; queue stays empty; worker never fires.
- Frontend treats `not_generated` AND `failed` as terminal → errors instantly.
  Poll loop lives in the `handleTrigger` closure → lost on reload/navigation.

## KEY REFS (verify symbol; lines may have drifted)
- src/backend/careervp/handlers/company_research_handler.py
  `_fetch_company_research` (~L154), `get_company_research` (~L229)
- src/backend/careervp/logic/company_research_store.py
  read_cr_artifact / write_cr_artifact (add processing-row writer)
- Worker input `CRWorkerInput` (company_research_worker_handler.py ~L34):
  {user_id, job_id, application_id?, company_name?, job_posting_url?, domain?, task_token?}
- infra/careervp/api_construct.py (handler lambda def);
  infra/careervp/api_db_construct.py `self.company_research_queue`
- src/frontend/app/applications/[id]/company-research/page.tsx
  init useEffect (~L20), handleTrigger poll loop (~L40), terminal branch (~L61)
- Handler lambda today: NO queue url env, NO sqs:SendMessage grant (must add).

## FILE 1 — docs/upgrade/specs/FE-UI-053-cr-enqueue-and-status.yaml (owner: backend)
Follow spec YAML shape: spec_id, title, priority, status:draft, owner, tier,
recommended_model:sonnet, depends_on, problem_statement{current_behavior,
required_behavior}, requirements, success_criteria.
Requirements:
- R1 POST /company-research/fetch: validate → sqs.send_message to
  COMPANY_RESEARCH_QUEUE_URL with full CRWorkerInput → write processing row →
  return 202 {request_id,status:"processing"}. DELETE inline asyncio.run + persist.
- R2 Store: idempotent write_cr_processing() upserting status=processing; never
  overwrite a terminal COMPLETED/FAILED row.
- R3 GET: return {status:"processing",company_research:null} for processing rows;
  keep completed/failed/not_generated.
- R4 Infra: queue.grant_send_messages(handler) + add_environment
  COMPANY_RESEARCH_QUEUE_URL=queue.queue_url.
- R5 Worker terminal always wins over processing (idempotent re-POST safe).
success_criteria:
- SC1 POST sends exactly one SQS msg; body validates as CRWorkerInput.
- SC2 POST returns 202 <2s; NO research_company() call on request path.
- SC3 processing row present immediately post-POST.
- SC4 GET=processing until worker terminal, then completed/failed.
- SC5 sub-0.85 → worker writes failed (not silent not_generated).
- SC6 handler IAM sqs:SendMessage on CR queue ONLY; env var present.
- SC7 cdk synth clean; mypy --strict + ruff clean on changed modules.

## FILE 2 — docs/upgrade/specs/FE-UI-054-cr-polling-session-independent.yaml (owner: frontend)
depends_on: FE-UI-053.
Requirements:
- R1 On mount: GET status; if processing, AUTO-RESUME polling (reload /
  navigate-away-return reconnects to in-flight job). State of truth = server row.
- R2 Move poll loop OUT of handleTrigger into a status-keyed effect; runs on both
  trigger and mount.
- R3 Terminal map: completed→render; failed→error; processing→keep polling;
  not_generated→idle "Run research" CTA (NOT error).
- R4 Cadence 10s, cap 5min; at cap show "still running, refresh later" (job
  continues server-side, not cancelled).
success_criteria:
- SC1 trigger → reload mid-run → resumes → completed renders.
- SC2 navigate away mid-run → return → polling resumes from server status.
- SC3 not_generated shows CTA, never error toast.
- SC4 failed→error; completed→card.
- SC5 no poll state held only in closure/unmount-sensitive scope.
- SC6 typecheck + unit + integration + e2e green.

## FILE 3 — docs/upgrade/specs/TEST-FE-053-test-prompts.yaml (backend tests)
Match TEST-FE-052 format: named sections, each `prompt: |` with Context/Files/
numbered tests w/ Assert/Run/pass-line. Map every test to FE-UI-053 SCs.
- T1 POST enqueues one SQS msg w/ correct body (mock boto3 sqs; assert args) → SC1
- T2 POST 202 + processing row; assert NO research_company() call → SC2,SC3
- T3 GET processing/completed/failed/not_generated (4 cases) → SC4
- T4 write_cr_processing idempotent; no terminal overwrite → SC5
- T5 infra synth: queue url env + SendMessage grant on handler → SC6
Run lines: `cd src/backend && uv run pytest tests/unit/ -q`; `cd infra && npx cdk synth`.

## FILE 4 — docs/upgrade/specs/TEST-FE-054-test-prompts.yaml (frontend tests)
Same format. Map to FE-UI-054 SCs.
- T1 mount status=processing → auto-polls (mock api, fake timers) → SC1,SC5
- T2 remount mid-run resumes to completed → SC1
- T3 not_generated → CTA, no error → SC3
- T4 failed→error; completed→card → SC4
Run line: `cd src/frontend && npm run test:unit && npm run test:integration && npm run test:e2e`.

## CONSTRAINTS
- No code edits, no deploy. Output = the 4 files only.
- Specs use existing YAML shape; test-prompts use TEST-FE-052 shape.

## DEFINITION OF DONE
- [x] 4 files at the exact paths above; IDs 053/054 + TEST-FE-053/054.
- [x] Every spec has numbered success_criteria; every test maps test→SC.
- [x] Session-independence (reload + navigation) explicit in FE-UI-054 SC1/SC2.
- [x] Backend SC2 keeps the "202 fast, no sync research" guard.
- [x] All 4 files obey the OUTPUT OPTIMIZATION MANDATE (terse, self-contained, ≤size).

## COMPLETED

Session 2026-06-28: All 4 output files authored.
- docs/upgrade/specs/FE-UI-053-cr-enqueue-and-status.yaml (103 lines)
- docs/upgrade/specs/FE-UI-054-cr-polling-session-independent.yaml (94 lines)
- docs/upgrade/specs/TEST-FE-053-test-prompts.yaml (79 lines)
- docs/upgrade/specs/TEST-FE-054-test-prompts.yaml (78 lines)
