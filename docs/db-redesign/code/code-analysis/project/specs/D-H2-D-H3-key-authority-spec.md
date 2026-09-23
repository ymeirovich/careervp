---
spec_id: D-H2-D-H3-KEY-AUTHORITY
title: "Single key-authority repository and ValidationException surfacing"
status: draft
owner: backend
tier: T1
scope_lock_clause: [D-H2, D-H3]
tooling:
  D-H2: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  D-H3: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - D-H2/D-H3: Key Authority and ValidationException Surfacing

## Problem Statement

Key construction is scattered across handlers/DAL code and some `ValidationException`s are swallowed as false "not found." D-H2 creates the single key-authority repository. D-H3 ensures malformed key/schema access is surfaced, not hidden.

## Evidence

- `src/backend/careervp/dal/dynamo_dal_handler.py:101` keeps legacy aliases for mixed environments, showing multi-schema compatibility is still present.
- `src/backend/careervp/handlers/cv_tailoring_handler.py:345,577,732,803,858,946,1001-1002,1038` repeatedly constructs DAL handlers from table-name precedence, proving no single key authority governs access.
- `src/backend/careervp/handlers/cover_letter_handler.py:56-63,649,1369,1446` uses `ARTIFACTS_TABLE_NAME -> DYNAMODB_TABLE_NAME -> TABLE_NAME` precedence, contradicting the no-env-var-table-precedence invariant.
- `infra/careervp/api_construct.py:484-494` builds an LLM cache table separately, demonstrating separate tables are acceptable when contract says they stay outside core.
- Scope-lock D-H2 requires `TableRegistry`/`CoreRepository` as the sole key builder; D-H3 requires surfacing swallowed `ValidationException`. *(v2.7.0: the dual-read migration-parity harness was removed from this clause — see O-3.)*

**Evidence addendum (2026-07-27) — the cited file list is a sample, not the population.** The three
files named above are illustrative; a live enumeration found **9 handler files carrying the
artifacts/core env-precedence chain**, not 3, and `cv_tailoring_handler.py` — cited above — does not
use `ARTIFACTS_TABLE_NAME` at all (it uses the two-key `DYNAMODB_TABLE_NAME -> TABLE_NAME` tail).
The authoritative, dated, enumerated baseline is in the "RED Tests to Write First" section below and
must be re-confirmed live before RED. This addendum appends to the original evidence rather than
replacing it, so the sampling error stays visible: a spec's Evidence section proves a defect exists,
it does not size the work, and the runbook step that read it as a work list inherited a file list
that was ~⅓ of the real one.

## Fix Plan

1. Add a `TableRegistry`/`CoreRepository` as the sole artifact key builder and repository entry point.
2. Replace scattered PK/SK string construction behind repository methods, beginning with characterization tests.
3. On DynamoDB `ValidationException`, return a typed error/result and log schema/key mismatch, never convert it to a false 404.
4. Preserve frontend §3 identifiers and response shapes; internal PK/SK changes are not API changes.

## RED Tests to Write First

> **Precision edit 2026-07-27 (rule 14).** The four descriptions below originally named their
> subject but not their assertion values — no approved module list, "exact projection equality"
> undefined, "schema error/result" naming no type, and a scan whose boundary was never drawn. Rule
> 14 requires exact assertion values *before* a test is written, so the RED session is not
> improvising the contract it is supposed to be pinning. This edit pins values only; it adds no
> requirement and widens no clause. Same action, same reason as the P-31 precision edit that
> preceded Wave-2 step 2.7 (commit `ac9841c`). Every enumerated baseline below was read live from
> the working tree on 2026-07-27 and **must be re-confirmed live by the RED session** — a stale
> baseline is the exact failure this project keeps recording.

> **Precision edit 2026-07-27 (rule 14) — second pass, unblocking 3.1-RED.** The 3.1-RED session
> stopped before writing any test because two rule-14 defects survived the first pass: B-3-1's
> internal-field allowlist was still an undefined "enumerated once 3.1-RED settles" placeholder, and
> `test_dh3_validation_exception_not_returned_as_not_found` still carried an "or"-shaped assertion.
> Both are now settled from live evidence read on 2026-07-27: the allowlist is enumerated with a
> stated derivation rule, and the D-H3 brief pins its own stimulus so exactly one result code is
> correct. This pass also **corrects a factual error** in the prior D-H3 brief about where the defect
> lives — see the corrected-mechanism note under that test; that correction narrows what GREEN may
> change and is called out rather than folded in silently. One RED test is **added**
> (`test_dh2_core_repository_reads_canonical_only_items`) because the retirement of the dual-shape
> writes needs a negative proof that no read depends on the legacy key convention, and no spec in
> Wave 3 provided one. This edit pins values, corrects a stated fact, and adds a proof obligation
> **within** the existing D-H2 clause; it removes no clause and widens no scope-lock item.
>
> **Third pass 2026-07-27 — scope-lock v2.7.0 landed.** The migration-parity harness has been
> **removed** from this spec: its RED test, `AC-DH2-2`, the 10-attribute internal-field allowlist,
> Fix-Plan item 3, and the Done-when harness clause are all gone, and bet `B-3-1` is retired. The
> reason is recorded in the contract, not here: all stored data is disposable test data, so there
> is no migration to prove parity for (`project-scope-lock` O-3, resolved 2026-07-27). Four RED
> tests remain. `test_dh2_core_repository_reads_canonical_only_items` **stays** — it was never a
> parity proof; it is the negative proof D-H9's demolition gate cites before the dual-shape writes
> at `dynamo_dal_handler.py:535-552` may be deleted.

**Approved key-authority modules** (the only paths any scan below may allow):

- `src/backend/careervp/dal/table_registry.py`
- `src/backend/careervp/dal/core_repository.py`

---

- `test_dh2_all_artifact_keys_built_by_core_repository`: static scan over
  `src/backend/careervp/handlers/` and `src/backend/careervp/logic/` asserting that **artifacts/core**
  `pk`/`sk`/`USER#`/artifact-SK strings are constructed only in the two approved modules above.
  **Scope boundary (B-3-5):** artifacts/core keying only. User-pool, trial, and application-table
  keying is **out of scope for D-H2** and belongs to the Wave-6 D-H8 single-table collapse — the
  scan must not fail on it. Live baseline read 2026-07-27: 9 `USER#` construction sites outside
  `dal/` across 5 files — `handlers/company_research_handler.py`, `handlers/auth_handler.py`,
  `logic/company_research_store.py`, `logic/auth_service.py`, `logic/trial_service.py`. Of these,
  the **company-research pair is in scope** (CR is an artifact type; D-H9/step 3.5 retires its legacy path);
  `auth_handler`, `auth_service`, and `trial_service` are **out of scope** and the scan states that
  exclusion by name and reason, not by silent omission. Cite AC-DH2-1.

- `test_dh3_validation_exception_not_returned_as_not_found`: moto/stub DynamoDB raises a
  `ClientError` on the read path with `Error.Code == 'ValidationException'` and the **verbatim**
  message `'The provided key element does not match the schema'`. Assert the repository returns
  **exactly `Result(success=False, code=ResultCode.TABLE_SCHEMA_MISMATCH)`** — one code, no
  alternative. It asserts specifically that the return is **NOT**
  `Result(success=True, data=None, code=ResultCode.SUCCESS)`.

  **Why one code and not two.** The test authors its own stimulus, so it can stage a failure with
  exactly one correct answer instead of widening the assertion. `_map_dal_error_code`
  (`dynamo_dal_handler.py:46-55`) branches on message content: `schema` or `key element` →
  `TABLE_SCHEMA_MISMATCH`, anything else → `DYNAMODB_VALIDATION_EXCEPTION`. Pinning the message
  pins the branch. The message above is the verbatim string already used by the existing passing
  test at `src/backend/tests/unit/test_dynamo_dal_handler.py:395-417`, so this test reuses a proven
  stimulus rather than inventing one. `DYNAMODB_VALIDATION_EXCEPTION` is deliberately **not**
  asserted anywhere: a live enumeration on 2026-07-27 found it appears exactly twice in the whole
  codebase — its definition at `models/result.py:121` and the one line that can emit it at
  `dynamo_dal_handler.py:54` — with zero tests asserting it and zero callers branching on it.

  **No new exception class is introduced**: `ResultCode.TABLE_SCHEMA_MISMATCH` already exists at
  `src/backend/careervp/models/result.py:122`.

  **Corrected mechanism (precision edit 2026-07-27).** An earlier revision of this brief stated that
  `_map_dal_error_code` already computes the correct code and "the defect is that callers on the
  cover-letter read path discard it." **That is not what the code does, and the difference changes
  what GREEN is allowed to touch.** Read live 2026-07-27:
  `src/backend/careervp/dal/dynamo_dal_handler.py:629-637` catches the `ValidationException` and
  never reaches `_dal_failure_result` at all — it retries the read under the legacy `{'pk','sk'}`
  key schema and, on a miss, returns `Result(success=True, data=None, code=ResultCode.SUCCESS)`
  directly. The code is never computed on that path, let alone discarded. `:678-684` is the same
  shape on the scan path.

  **GREEN boundary — three outcomes, not one.** The legacy retry is a live compatibility path
  (`COVER_LETTER_LEGACY_READ_ENABLED` defaults `true`), so GREEN must split the outcomes rather than
  failing the whole branch:

  1. ValidationException → legacy retry **finds the item** → unchanged: `success=True` with the item.
  2. ValidationException → legacy retry **misses** → `Result(success=False, code=ResultCode.TABLE_SCHEMA_MISMATCH)`.
  3. The legacy retry itself raises → unchanged (`_dal_failure_result`, already correct).

  Without this boundary, a GREEN session can satisfy the assertion by failing the whole branch and
  silently break every mixed-schema read. **This also pre-settles B-3-2 toward "reachable":** the
  swallow sits on a live, default-on compatibility path, not in a dead defensive `except`. Cite
  AC-DH3-1.

- `test_dh2_core_repository_reads_canonical_only_items`: seed the artifacts table in moto with items
  carrying **only** the canonical key attributes (`applicationId`/`artifactId`, no `pk`/`sk`), then
  exercise every `CoreRepository` read method for that artifact type and assert each returns the
  seeded item. This is the **negative proof** that the dual-shape write at
  `dynamo_dal_handler.py:535-552` can later be reduced to one key convention without a read going
  dark — a static "no callers" scan cannot establish that, because the legacy key path is selected
  at runtime. No retirement of the dual-shape write may proceed on this artifact type until this
  test is green. Cite AC-DH2-1.

- `test_dh2_no_env_table_precedence_in_handlers`: static scan asserting that **multi-key environment
  fallback resolution of the artifacts/core table** is absent from `src/backend/careervp/handlers/`.
  **Scope boundary (B-3-5):** the artifacts/core chain and its two-key tail — i.e.
  `ARTIFACTS_TABLE_NAME -> DYNAMODB_TABLE_NAME -> TABLE_NAME` and
  `DYNAMODB_TABLE_NAME -> TABLE_NAME`. Fallbacks resolving a *different* table
  (`APPLICATIONS_TABLE_NAME`, `USERS_TABLE_NAME`, `GAP_QUESTIONS_TABLE_NAME`,
  `KNOWLEDGE_TABLE_NAME`) are **out of scope** for D-H2 and the scan states that by name. A single
  unconditional read such as `os.environ['ARTIFACTS_TABLE_NAME']` is **not** a precedence chain and
  is out of scope. **Enumerated violation baseline, read live 2026-07-27 — 9 handler files, 23
  sites:** `ai_assist_handler.py:69,498`; `company_research_handler.py:404`;
  `cover_letter_handler.py:57,59,60,659,1381,1458`; `cover_letter_submit_handler.py:72`;
  `cv_tailoring_handler.py:346,734,805,860,948,1003,1004,1040`; `export_handler.py:161`;
  `interview_prep_handler.py:49`; `interview_prep_submit_handler.py:72`;
  `vpr_submit_handler.py:354`. The scan asserts against this enumerated baseline as a **ratchet** —
  it may shrink, never grow — so a *new* precedence site fails the test even before the baseline
  reaches zero (B-3-5 fallback). Cite AC-DH2-1.

## Acceptance Criteria

**AC-DH2-1** - Given any artifact repository operation, when a key is built, then it is built by the single key-authority module.


**AC-DH3-1** - Given a DynamoDB schema/key validation failure, when the repository catches it, then the error is surfaced and observable, not reported as not found.

## Done-when

All RED tests pass; `TableRegistry`/`CoreRepository` are the sole key authority; no frontend contract drift.

## Sequencing / Dependencies

Wave 3 foundation. Must precede D-H4, D-H7, D-M*, D-H9, and P-01.

