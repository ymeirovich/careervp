# /goal FE-UI-053 Backend — verify, R6, tests
# Model: sonnet | Effort: medium
# Spec: docs/upgrade/specs/FE-UI-053-cr-enqueue-and-status.yaml
# Tests: docs/upgrade/specs/TEST-FE-053-test-prompts.yaml

GOAL: Verify 3 inherited backend edits, implement R6 (worker failed-row), author
and run all TEST-FE-053 categories. Emit the backend gate fact at the end.
No frontend, no deploy, no commit without user approval.

## INLINED CONTRACTS (do not re-read specs unless resolving ambiguity)

Artifacts-table key schema (cr_artifact_key):
  pk=applicationId, sk=ARTIFACT#COMPANY_RESEARCH#{applicationId}
  artifactType='company_research', user_id=str

Status values GET reads from this table:
  processing  → {status:'processing', company_research:null}
  failed      → {status:'failed', company_research:null}
  completed   → confidence-gated: has research_data + no status=='failed'
  (none/null) → {status:'not_generated', company_research:null}

SQS message body (CRWorkerInput):
  {user_id, job_id, application_id?, company_name?, job_posting_url?, domain?, task_token?}

Queue env var: COMPANY_RESEARCH_QUEUE_URL
Artifacts table env var: ARTIFACTS_TABLE_NAME

## INHERITED STATE (unverified — this session proves or fixes)

company_research_store.py:
  ADDED: write_cr_processing(application_id, user_id) — puts {key, artifactType,
    user_id, status:'processing', created_at}; skips if terminal row exists.
  ADDED: _has_terminal_cr_row() — returns True for status in {completed,failed} or
    row has research_data/confidence_score.
  ADDED: _TERMINAL_CR_STATUSES = {'completed','failed'}
  ADDED: write_cr_processing to __all__

company_research_handler.py:
  _fetch_company_research: now enqueues SQS (COMPANY_RESEARCH_QUEUE_URL) with
    CRWorkerInput JSON + calls write_cr_processing + returns 202. asyncio.run /
    research_company / write_cr_artifact / CompanyResearchResult REMOVED.
  get_company_research: returns {status:'processing'} when row.status=='processing'.
  Imports removed: asyncio, research_company, write_cr_artifact, CompanyResearchResult.

api_construct.py:
  ADDED near CR-worker chain wiring:
    company_research_queue.grant_send_messages(company_research_func)
    company_research_func.add_environment("COMPANY_RESEARCH_QUEUE_URL", queue.queue_url)

## STEP 0 — Verify + mechanical fixes (do first; stop if mypy fails)

Fix landmine #3 while verifying:
- _map_result_code_to_status has zero callers → DELETE it.
- job_posting_url is HttpUrl|None; _coerce_str returns None for it. In the SQS
  message body build: use raw_payload.get('url') primarily, fall back to
  str(request.job_posting_url) if not None.
- Confirm write_cr_processing and read_cr_artifact both use ARTIFACTS_TABLE_NAME
  with the same key schema (cr_artifact_key). Verify user_id ownership match.

Run:
  cd src/backend && uv run ruff format . && uv run ruff check --fix .
  cd src/backend && uv run mypy careervp/handlers/company_research_handler.py \
    careervp/logic/company_research_store.py \
    careervp/handlers/company_research_worker_handler.py --strict
Gate: both clean before proceeding.

## STEP 1 — Implement R6: worker writes failed row (FE-UI-053 R6, SC5, SC8)

CONFIRMED gap: _hard_fail in company_research_worker_handler.py writes only the
APPLICATION record (update_artifact_status + set_company_research_error). The
ARTIFACTS table (what GET reads) never gets a terminal row on failure, so a
hard-failed job's processing placeholder is never cleared → GET returns 'processing'
forever.

Fix (minimal, mirrors write_cr_processing):
1. Add write_cr_failed(application_id: str, user_id: str) → None to
   company_research_store.py. Put {key, artifactType, user_id, status:'failed',
   created_at}. No terminal guard — failed always overwrites (including processing).
   Add to __all__.
2. In company_research_worker_handler._hard_fail, call write_cr_failed(
   application_id=input_data.job_id, user_id=input_data.user_id) alongside
   the existing app-record updates (inside the try block).

Run mypy again on both changed files after implementing.

## STEP 2 — Author backend tests then make them pass

### TEST CATEGORY A: post_enqueue → SC1, SC2, SC3
File: src/backend/tests/unit/test_company_research_handler.py
Patch: careervp.handlers.company_research_handler.boto3 (for SQS mock)
       careervp.handlers.company_research_handler.write_cr_processing

test_post_sends_one_sqs_message
  - Build minimal POST event (valid CompanyResearchRequest fields).
  - Assert sqs_client.send_message called once.
  - Assert MessageBody deserializes as valid CRWorkerInput (all required fields present). → SC1

test_post_returns_202_no_research_call
  - Assert response statusCode == 202.
  - Assert research_company NOT called (it's not even imported; confirm ImportError
    would fire if accidentally re-added). → SC2

test_post_writes_processing_row
  - Assert write_cr_processing called once with correct application_id + user_id. → SC3

Run: cd src/backend && uv run pytest tests/unit/test_company_research_handler.py -q -k post
Pass: all 3 green.

### TEST CATEGORY B: get_status → SC4
File: src/backend/tests/unit/test_company_research_handler.py
Patch: careervp.handlers.company_research_handler.read_cr_artifact (4 return values)

test_get_processing   → item with status='processing' → response body status='processing', company_research=null. → SC4
test_get_completed    → item with research_data + high confidence → status='completed', data present.
test_get_failed       → item with status='failed' → status='failed', company_research=null.
test_get_not_generated → read_cr_artifact returns None → status='not_generated'.

Run: cd src/backend && uv run pytest tests/unit/test_company_research_handler.py -q -k get
Pass: all 4 green.

### TEST CATEGORY C: store_idempotency → SC5
File: src/backend/tests/unit/test_company_research_store.py
Patch: careervp.logic.company_research_store.boto3 (DynamoDB Table mock)

test_write_processing_on_empty        → no existing item → put_item called. → SC5
test_write_processing_on_not_generated → existing {status:'not_generated'} → put_item called.
test_no_overwrite_completed           → existing item with research_data → put_item NOT called.
test_no_overwrite_failed              → existing {status:'failed'} → put_item NOT called.

Run: cd src/backend && uv run pytest tests/unit/test_company_research_store.py -q -k processing
Pass: all 4 green.

### TEST CATEGORY C2: worker_failed_row → SC5, SC8
Files: src/backend/tests/unit/test_company_research_store.py
       src/backend/tests/unit/test_company_research_worker_handler.py

test_write_cr_failed_puts_failed_row
  - write_cr_failed('app-1','user-1') → put_item called; item has status='failed',
    artifactType='company_research', user_id='user-1'. → SC8

test_write_cr_failed_overwrites_processing
  - Existing item with status='processing'; write_cr_failed → put_item called (no guard). → SC8

test_hard_fail_calls_write_cr_failed
  - Patch write_cr_failed; call _hard_fail(input_data, 'cause').
  - Assert write_cr_failed called with application_id=input_data.job_id,
    user_id=input_data.user_id. → SC5, SC8

test_get_failed_after_hard_fail
  - Integration-style (no HTTP): write_cr_processing → write_cr_failed → read_cr_artifact
    → item.status=='failed'. Confirms GET would return failed not processing. → SC8

Run: cd src/backend && uv run pytest tests/unit/test_company_research_store.py \
  tests/unit/test_company_research_worker_handler.py -q -k fail
Pass: all 4 green.

### TEST CATEGORY D: infra_synth → SC6, SC7
File: infra/tests/test_cr_enqueue_infra.py (new)
Use: aws_cdk.assertions.Template.from_stack

test_cr_handler_has_queue_url_env
  - Template: CR handler Lambda Environment contains COMPANY_RESEARCH_QUEUE_URL. → SC6

test_sqs_send_scoped_to_cr_queue
  - Template: IAM policy has sqs:SendMessage on CR queue ARN (not '*'). → SC6

test_no_wildcard_sqs
  - Template: no statement with sqs:SendMessage on Resource='*'. → SC6

test_synth_no_cycle
  - Template.from_stack succeeds with no exception. → SC7

Run: cd infra && uv run pytest tests/test_cr_enqueue_infra.py -q && npx cdk synth
Pass: all 4 tests + synth exit 0.

## STEP 3 — Full suite confirmation
cd src/backend && uv run pytest tests/unit/ -q
All unit tests green (no regressions).

## BACKEND GATE — emit this fact before closing session
"FE-UI-053 backend complete. Artifacts table contract:
 processing row: {applicationId, artifactId, artifactType='company_research',
   user_id, status='processing', created_at}
 failed row: same shape, status='failed'
 completed: write_cr_artifact puts full research data; no explicit status field;
   identified by presence of research_data + confidence_score >= 0.85
 GET reads ARTIFACTS_TABLE_NAME via read_cr_artifact (canonical path).
 All SC1–SC8 proven. Tests green. mypy+ruff clean."

## DEFINITION OF DONE
- [ ] STEP 0: ruff + mypy clean; landmine #3 resolved.
- [ ] STEP 1: write_cr_failed in store + called from _hard_fail.
- [ ] SC1–SC8 all proven by passing tests.
- [ ] cdk synth clean.
- [ ] Backend gate fact emitted.
- [ ] No commit, no deploy without explicit user approval.
