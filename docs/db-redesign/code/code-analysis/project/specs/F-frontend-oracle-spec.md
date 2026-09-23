---
spec_id: F-FRONTEND-ORACLE
title: "Frontend executable-oracle — Zod/ajv contract oracle (F-01) + all-10 §3 assertions (F-06 folded in)"
status: draft
owner: frontend
tier: feature
# Multi-clause spec: list-valued scope_lock_clause + per-clause tooling map.
# SANCTIONED multi-clause form (scope-lock §8.5, codified v1.5.0/A7 + v2.0.0/A7):
# scope-diff.py handles the list (covers every listed clause) and requires a tooling entry per listed clause.
# F-06 is FOLDED INTO F-01 per waves v2.0.0/A11 — NOT deferred: the all-10 §3 assertions ship
# as part of the Wave-0 F-01 oracle (wave_0_guardrails: F-01_with_F-06_assertions).
scope_lock_clause: [F-01, F-06]
tooling:
  F-01: {claude_code: {model: opus, effort: high},  codex: {model: gpt-5-codex, reasoning: high}}    # hard: oracle harness, dual-truth wiring
  F-06: {claude_code: {model: opus, effort: high},  codex: {model: gpt-5-codex, reasoning: high}}    # hard: every §3 item as an executable assertion
format_note: "RED tests are TDD-first, not optional; RED-test descriptions inline (v1.3.0); test files (vitest/ajv harness + nightly Playwright) written at IMPLEMENT in the real careervp repo. Each clause below carries AC-### Given/When/Then blocks (§8.5). No copy-paste prompt: blocks (retired format)."
---

# Spec — Track F: Frontend executable-oracle (F-01 dual-truth oracle + F-06 all-10 §3 assertions)

- **Status:** SPEC ONLY — do **not** implement here. Apply under TDD in Wave 0 (`F-01_with_F-06_assertions` guardrail) — this is a Wave-0 net that MUST exist before additive waves so every later change is contract-checked.
- **Governs clauses:** `F-01` (executable oracle: Zod mirror of `lib/types.ts` + `safeParse` as FE-truth; Pydantic `model_json_schema()` → ajv as BE-truth; MSW in CI + nightly Playwright vs dev) and `F-06` (encode all 10 §3 contract items as executable assertions). **F-06 is FOLDED IN here, not deferred** (waves v2.0.0/A11).
- **Code anchor:** `github.com/ymeirovich/careervp @ 4f7c294` (branch `db-redesign`). All file:line refs are at that commit.
- **Oracle authority (scope-lock §frontend_contract.oracle_rule — IMMUTABLE):** the authoritative contract is `src/frontend/` calls + CDK `route_map` + handlers; **NOT** any OpenAPI/swagger. This spec's FE-truth is `src/frontend/lib/types.ts`; the swagger is explicitly non-authoritative (F-07 marks it so).
- **Env note for the implementer:** frontend is Node + vitest (`src/frontend/`); backend requires Python **≥3.13** + `uv` (`src/backend/pyproject.toml`) to emit `model_json_schema()`. Run FE tests via `npm run test:unit` in `src/frontend/`; regenerate BE JSON Schemas via `uv run` in `src/backend/`. (The analysis env had only Python 3.9 / no uv — set this up first.)
- **TDD contract:** each clause lists the **RED test(s) to write and watch fail FIRST**, then the minimal GREEN change. The oracle harness itself is RED-first: the assertion suite is written to FAIL against the current backend (which has the F-02..F-05 bugs live), proving the oracle actually catches contract drift before any fix ships.
- **Constraints (all clauses):** the oracle must **never weaken** to pass (scope-lock `never_weaken_test`); the §3 frontend contract is IMMUTABLE and must not be versioned/routed around; the oracle is a *check*, not a code change to shipped behavior (the F-02..F-05 fixes are separate clauses — this spec proves they are needed and later proves them fixed).

---

## Problem Statement

"Don't break the UI" is currently an assertion of faith. There is no executable proof that the backend's wire shapes match what `src/frontend/lib/types.ts` consumes. The consequence is a live, shipped contract drift: **four known live violations (`known_live_violations: [F-02, F-03, F-04, F-05]`) reached production undetected** because nothing mechanically compared FE-truth to BE-truth.

The confirmed live drift (each reproduced against `@ 4f7c294`):

- **F-02 — VPR `download_url` missing.** FE `VPRStatusResult` declares `download_url?: string` (`src/frontend/lib/types.ts:214`) and the whole VPR-full-data fetch hangs off it. BE `VPRStatusResult` has **no `download_url` field at all** (`src/backend/careervp/models/api_models.py:174-179`). The FE silently gets `undefined`, the S3 fetch never fires, and VPR-full renders empty.
- **F-03 — status enum gaps.** FE `ArtifactStatus` is `"pending" | "processing" | "completed" | "failed" | "cancelled" | "expired"` (`types.ts:70`). BE `VPRStatusResponse.status` is `Literal['pending', 'processing', 'completed', 'failed']` (`api_models.py:182`) — **missing `cancelled` and `expired`**. §3 item 4 requires the enum be **additive-only**; the backend Literal is a *narrower* set, so a `cancelled`/`expired` value the FE tolerates cannot be emitted by (and would fail validation on) the typed BE model.
- **F-04 — `vpr_id` null→422.** FE `CVTailoringRequest.vpr_id` is `string | null` and the comment is load-bearing: *"must be present (even as null) so backend detects new-API flow"* (`types.ts:517`). BE `CVTailoringRequest.vpr_id` is `str = Field(min_length=1)` (`api_models.py:282`) — **required, non-null, non-empty**. The FE's deliberate `null` (the new-API signal) is rejected with HTTP 422. §3 item 3: *null-vs-absent is load-bearing*.
- **F-05 — nested error envelope → `[object Object]`.** FE expects the **flat** envelope `{error|message, classification, error_code, field}` (§3 item 10; `types.ts` error handling reads these flat keys). BE emits **nested** `ErrorResponse{error: ErrorObject{code, message, details: [ErrorDetail{field, message}]}}` (`api_models.py:520-521`, `508-517`). The FE's flat-key read of a nested object stringifies to `[object Object]` in the UI.

F-06 exists because these four are only the *known* four. The §3 contract has **10 items**; only items 3, 4, and 10 have caught bugs so far. The other seven are unasserted and could drift silently at any deploy. **F-06 encodes all 10 as executable assertions** so the oracle is exhaustive, not anecdotal.

**F-01 builds the oracle that would have caught all four at CI time; F-06 makes that oracle cover every one of the 10 §3 items.**

---

## Evidence (file:line @ 4f7c294)

**Frontend truth (`src/frontend/lib/types.ts`):**
- `types.ts:70` — `ArtifactStatus = "pending" | "processing" | "completed" | "failed" | "cancelled" | "expired"` (the additive, tolerant enum; §3 item 4).
- `types.ts:75` — `HubArtifact.artifact_id: string | null` (round-trip target; §3 items 2, 3).
- `types.ts:179,197,619-627` — `application_id` used as the DB-lookup key; `ApplicationHubData.application.application_id` carries the comment `// same value as job_id` (§3 item 1).
- `types.ts:63-65` — `AsyncTaskResponse.request_id` (primacy) + `job_id?` alias with comment `// alias for request_id` (§3 item 6 — `request_id ?? job_id`).
- `types.ts:208-215` — `VPRStatusResult.download_url?: string` (§3 item 8; F-02 target).
- `types.ts:517` — `CVTailoringRequest.vpr_id: string | null` + `// must be present (even as null)` (§3 item 3; F-04 target).
- `types.ts:263-340` (`VPRFullData`), `374-380` (`CoverLetterStatusResponse.result`), `467-480` (`InterviewPrepStatusResponse.result`), `591-616` (`CVTailoredStatusResponse.result`) — nested `result.*` trees that must round-trip (§3 item 7).
- `types.ts:482-489` — `InterviewPrepPatchResponse` echoes `answer + answer_version + answer_updated_at` (§3 item 5, the PATCH echo half).
- `types.ts:499-511` — `CompanyResearchResult.recent_news?: Array<{...} | string>` with comment `// Accept both` (§3 item 9, shape polymorphism tolerated).
- `types.ts:642-652` — `ExportResponse.download_url + expires_at` (§3 item 8, presigned URL + expiry).

**Backend truth (`src/backend/careervp/models/api_models.py`) — the live bugs:**
- `api_models.py:174-179` — `VPRStatusResult` has fields `uvp, differentiators, strategic_narrative, company_job_fit_score, meta_evaluation` and **no `download_url`** → **F-02**.
- `api_models.py:182` — `VPRStatusResponse.status: Literal['pending', 'processing', 'completed', 'failed']` → **F-03** (no `cancelled`/`expired`).
- `api_models.py:282` — `CVTailoringRequest.vpr_id: str = Field(min_length=1)` → **F-04** (rejects the FE's load-bearing `null`).
- `api_models.py:508-521` — `ErrorDetail{field, message}` → `ErrorObject{code, message, details[]}` → `ErrorResponse{error: ErrorObject}` = **nested**, not the flat §3 item-10 envelope → **F-05**.

**Contract source (scope-lock `frontend_contract`, IMMUTABLE):** `project-scope-lock.yaml:47-60` — the 10 items (verbatim rules) + `known_live_violations: [F-02, F-03, F-04, F-05]`. Reproduced in the §3 assertion table below.

---

## Design — the dual-truth oracle

Two independent truths are compared; neither is allowed to define the other:

| Truth | Source | Mechanism | Proves |
|-------|--------|-----------|--------|
| **FE-truth** | `src/frontend/lib/types.ts` | A **Zod mirror** of each interface/type; validate a payload with `schema.safeParse(payload)` | "the frontend can consume this shape" |
| **BE-truth** | Pydantic models in `src/backend/careervp/models/` | `Model.model_json_schema()` → JSON Schema → **ajv** compiled validator | "the backend can emit / accept this shape" |

**Wiring (three layers, cheapest-first):**
1. **CI unit oracle (MSW):** MSW intercepts the frontend's own fetch calls; the response fixtures are validated against BOTH the Zod mirror (`safeParse` OK) AND the ajv-compiled BE schema. A payload that passes one but fails the other **is** a contract drift — the test fails and names the field. This runs on every PR, no AWS.
2. **Schema-diff oracle:** for each contract-bearing type pair (FE `T` ↔ BE `Model`), assert Zod-mirror ⟺ ajv-from-`model_json_schema()` are mutually satisfiable on a shared fixture corpus; a field required by one and absent/narrower in the other fails. This is where F-02..F-05 get caught mechanically (see the §3 table).
3. **Nightly Playwright vs dev:** the real frontend drives the real dev API; captured live responses are fed through the same Zod + ajv gate. Catches drift the fixtures miss (server-side polymorphism, real error envelopes). Non-blocking on PR; alarms nightly.

**Zod-mirror maintenance:** the mirror lives beside `types.ts` and is asserted to stay in lockstep — a mirror-vs-types drift test fails if a `types.ts` interface gains/loses a field the Zod schema doesn't reflect (so the FE-truth can't silently rot). The mirror is FE-truth's executable form; `types.ts` remains the human-readable source.

**Bug-catch proof (RED-first, load-bearing):** the oracle suite is authored to run against the **current** backend and **FAIL on F-02, F-03, F-04, F-05** before those clauses are fixed. This is the anti-tautology gate: an oracle that passes against a known-broken backend is worthless. After F-02..F-05 land, the same assertions flip GREEN with **zero test weakening** (scope-lock `never_weaken_test`).

---

## F-01 — Executable oracle (Zod safeParse FE-truth + ajv-from-Pydantic BE-truth, MSW in CI + nightly Playwright)

**Deliverable:** the three-layer oracle above, wired into CI, that mechanically compares FE-truth to BE-truth for every contract-bearing type and **fails on drift, naming the field**.

**Fix Plan (GREEN, ordered):**
1. **Zod mirror of `lib/types.ts`.** Author Zod schemas mirroring every contract-bearing interface (`ArtifactStatus`, `HubArtifact`, `AsyncTaskResponse`, `VPRStatusResponse`/`VPRStatusResult`, `CVTailoringRequest`, `ApplicationHubData`, the four `*StatusResponse.result` trees, `InterviewPrepPatchResponse`, `CompanyResearchResult`, `ExportResponse`, the flat error envelope). Add the mirror-vs-`types.ts` lockstep test.
2. **BE JSON Schema emission.** A backend script emits `Model.model_json_schema()` for each corresponding Pydantic model to a committed artifact (`src/backend/scripts/emit_json_schemas.py` → `contract/schemas/*.json`), regenerated in CI so the ajv side always reflects the real backend at HEAD.
3. **ajv compile + cross-validate.** Compile each BE schema with ajv; build a shared fixture corpus per type; assert each fixture passes BOTH `zod.safeParse` and the ajv validator. Divergence = fail with the offending field path.
4. **MSW wiring.** Register MSW handlers that return the fixture corpus for the FE's actual fetch paths (CDK `route_map`, not swagger); the FE call sites' consumed responses pass Zod `safeParse`. Runs in `npm run test:unit`.
5. **Nightly Playwright vs dev.** A scheduled (non-PR-blocking) job drives the real FE against dev, captures live responses, and runs them through the same Zod + ajv gate; failures alarm.
6. **RED-first proof.** Before any F-02..F-05 fix, the suite must FAIL on exactly those four (assert the failure, then invert when the fix clause lands).

**RED tests to write first (watch fail):**
- `oracle_mirror_matches_types` — a `lib/types.ts` interface with a field the Zod mirror lacks (or vice-versa) makes the lockstep test FAIL; guards FE-truth from silently rotting.
- `oracle_be_schema_regenerates` — `model_json_schema()` output for the contract models is committed and CI-regenerated; a hand-edited stale schema (drift from the real Pydantic model at HEAD) FAILS.
- `oracle_fixture_passes_both_truths` — a valid fixture passes BOTH Zod `safeParse` and ajv; a fixture valid under one truth but not the other FAILS and names the field.
- `oracle_catches_F02_download_url_missing` — a VPR-status fixture shaped like the **current** backend (no `download_url`) FAILS the FE-truth (`VPRStatusResult.download_url` consumer) — proving the oracle catches F-02 pre-fix.
- `oracle_catches_F03_status_enum_gap` — a `cancelled`/`expired` status value passes FE-truth but FAILS ajv against the current BE Literal — proving the oracle catches F-03 pre-fix.
- `oracle_catches_F04_vpr_id_null` — `CVTailoringRequest` with `vpr_id: null` passes FE-truth but FAILS ajv against the current BE `min_length=1` — proving the oracle catches F-04 pre-fix.
- `oracle_catches_F05_nested_error` — the current nested `ErrorResponse{error:{...}}` FAILS the flat FE error-envelope Zod schema — proving the oracle catches F-05 pre-fix.
- `oracle_msw_ci_green_on_fixed_shapes` — with the *corrected* shapes (F-02..F-05 fixed), the MSW CI suite is GREEN with zero weakened assertions.

**AC-F01-1** — *Given* the Zod mirror of `lib/types.ts` and ajv validators compiled from `model_json_schema()`, *When* a shared fixture is validated, *Then* it must pass BOTH truths or the oracle fails and names the divergent field. *(F-01 acceptance: FE-truth via safeParse + BE-truth via ajv.)*
**AC-F01-2** — *Given* the MSW-wired CI suite, *When* it runs on a PR, *Then* every FE fetch path (per CDK `route_map`, not swagger) has its consumed response validated against both truths, with no AWS dependency.
**AC-F01-3** — *Given* the **current** backend at `@ 4f7c294`, *When* the oracle suite runs before any F-fix, *Then* it FAILS on exactly F-02, F-03, F-04, F-05 (the `known_live_violations` set) — proving the oracle catches real drift, not a tautology.
**AC-F01-4** — *Given* the nightly Playwright-vs-dev job, *When* it captures live dev responses, *Then* they are validated through the same Zod + ajv gate and any drift alarms (non-blocking on PR).
**AC-F01-5** — *Given* F-02..F-05 are later fixed, *When* the oracle re-runs, *Then* those four assertions flip GREEN with **zero test weakening** (scope-lock `never_weaken_test` upheld).

**Done-when:** AC-F01-1..5 hold; the oracle runs in CI (MSW) and nightly (Playwright); it FAILS on the current backend's F-02..F-05 and would flip GREEN when they are fixed; the Zod mirror is lockstep-tested against `types.ts`; BE schemas are CI-regenerated from `model_json_schema()`; no swagger is used as authority.

---

## F-06 — Encode all 10 §3 contract items as executable assertions (folded into F-01)

**Deliverable:** each of the 10 §3 `frontend_contract.items` (scope-lock `project-scope-lock.yaml:49-59`) has **at least one concrete, executable oracle assertion** in the F-01 harness. No item is "asserted" by prose — every one maps to a check the suite runs and can fail.

**The 10 §3 items → concrete assertions (all covered, none deferred):**

| §3 # | Rule (verbatim from scope-lock) | Executable assertion | Ties to |
|:---:|---|---|---|
| **1** | `application_id == job_id` | For hub/VPR/CV/CL/IP fixtures, assert `application_id === job_id` (and `ApplicationHubData.application.application_id === job.job_id`). A fixture where they diverge FAILS. | AC-F06-1 |
| **2** | `artifact_id round-trips; hub artifact_id resolvable by status endpoint` | Take each `HubArtifact.artifact_id` (incl. `null`), feed it to the matching status-endpoint fixture; assert the status response resolves the **same** `artifact_id` (round-trip identity). | AC-F06-2 |
| **3** | `vpr_id = VPR hub artifact_id; CV-tailoring sends vpr_id:null (never omitted); null-vs-absent load-bearing` | Assert (a) CV-tailoring `vpr_id: null` **passes** both truths (present-but-null accepted); (b) `vpr_id` **omitted** is distinguishable from `null` (absent ≠ null); (c) a non-null `vpr_id` equals the VPR hub `artifact_id`. Catches **F-04**. | AC-F06-3 |
| **4** | `status enum string-compared/unversioned; changes additive only` — values `[pending, processing, completed, failed, cancelled, expired, not_generated, edited]` | Assert every one of the 8 values passes FE-truth (string-compared, tolerant); assert BE emits a **subset** never a **superset** (additive-only: BE may add, never emit a value the FE enum lacks); the current BE Literal missing `cancelled`/`expired` FAILS the round-trip. Catches **F-03**. | AC-F06-4 |
| **5** | `PATCH echoes result.*+version+updated_at; HTTP 409 on stale base_version` | Assert a PATCH response echoes `result.*` + `version` + `updated_at` (e.g. `InterviewPrepPatchResponse.answer_version`/`answer_updated_at`); assert a PATCH with a **stale `base_version`** returns **HTTP 409** (not 200, not a silent overwrite). | AC-F06-5 |
| **6** | `request_id primacy (request_id ?? job_id)` | Assert consumers resolve the poll key as `request_id ?? job_id`: a fixture with only `request_id` and one with only `job_id` both resolve to a usable poll key; `request_id` wins when both present. | AC-F06-6 |
| **7** | `nested result trees preserved (VPR/CV/IP/CL)` | Round-trip the deep `result.*` trees (`VPRFullData`, `CVTailoredStatusResponse.result`, `InterviewPrepStatusResponse.result`, `CoverLetterStatusResponse.result`) through both truths; assert no nested field is flattened/dropped. | AC-F06-7 |
| **8** | `presigned download_url + status:'expired'` | Assert `download_url` (presigned) is present on VPR/export success fixtures **and** consumable by the FE (`VPRStatusResult.download_url`, `ExportResponse.download_url`); assert `status: 'expired'` is a valid, tolerated status. Catches **F-02** (and item-4's `expired`). | AC-F06-8 |
| **9** | `shape polymorphism tolerated, must not worsen` | Assert `CompanyResearchResult.recent_news` accepts BOTH `string[]` and `Array<{title,date}>` (the `// Accept both` union); a change that narrows to one shape FAILS ("must not worsen"). | AC-F06-9 |
| **10** | `error envelope {error\|message, classification, error_code, field}; 401 -> one refresh-retry then sign-out` | Assert the error envelope is **flat** with keys `error\|message`, `classification`, `error_code`, `field` (the current nested `ErrorResponse{error:{code,message,details[]}}` FAILS the flat schema); assert a 401 triggers **exactly one** refresh-retry then sign-out (not a retry loop). Catches **F-05**. | AC-F06-10 |

**RED tests to write first (watch fail):** one per §3 item, named `oracle_s3_item_{n}_*`, each authored to FAIL where the current backend violates it (items 3, 4, 8, 10 fail immediately on F-04/F-03/F-02/F-05; items 1, 2, 5, 6, 7, 9 assert the currently-correct behavior and guard against regression). None may be a prose-only "assertion" — each is a runnable check with a concrete failing case.

**AC-F06-1** — *Given* any hub/artifact fixture, *When* validated, *Then* `application_id === job_id` (item 1) or the oracle fails.
**AC-F06-2** — *Given* a hub `artifact_id` (incl. `null`), *When* fed to its status endpoint, *Then* the same `artifact_id` round-trips (item 2).
**AC-F06-3** — *Given* CV-tailoring `vpr_id: null`, *When* validated, *Then* present-but-null passes both truths, absent ≠ null is preserved, and a non-null `vpr_id` equals the VPR hub `artifact_id` (item 3; catches F-04).
**AC-F06-4** — *Given* the 8-value status enum, *When* validated, *Then* all 8 pass FE-truth and BE is a subset never a superset (additive-only); the current `cancelled`/`expired` gap fails (item 4; catches F-03).
**AC-F06-5** — *Given* a PATCH, *When* it echoes `result.*`+`version`+`updated_at` and a stale `base_version` is sent, *Then* the echo is asserted and the stale write returns HTTP 409 (item 5).
**AC-F06-6** — *Given* an async task fixture, *When* the poll key is resolved, *Then* `request_id ?? job_id` holds and `request_id` wins when both present (item 6).
**AC-F06-7** — *Given* the deep `result.*` trees (VPR/CV/IP/CL), *When* round-tripped, *Then* no nested field is dropped or flattened (item 7).
**AC-F06-8** — *Given* a VPR/export success, *When* validated, *Then* a presigned `download_url` is present and FE-consumable and `status:'expired'` is tolerated (item 8; catches F-02).
**AC-F06-9** — *Given* `CompanyResearchResult.recent_news`, *When* validated, *Then* both `string[]` and `Array<{title,date}>` are accepted and narrowing fails (item 9).
**AC-F06-10** — *Given* an error response, *When* validated, *Then* the flat `{error|message, classification, error_code, field}` envelope holds (nested fails) and a 401 triggers exactly one refresh-retry then sign-out (item 10; catches F-05).

**Done-when:** all 10 §3 items have ≥1 executable oracle assertion (AC-F06-1..10 hold); items 3/4/8/10 FAIL against the current backend (catching F-04/F-03/F-02/F-05) and would flip GREEN when those clauses land; no item is asserted by prose only; the assertions live inside the F-01 harness (folded in, not a separate deferred suite).

---

## Sequencing (Wave 0)

1. **F-01 harness first** (Zod mirror + BE schema emission + ajv + MSW) — it is the Wave-0 net (`wave_0_guardrails: F-01_with_F-06_assertions`) every later change is checked against.
2. **F-06 assertions folded into the same harness** — the 10 §3 items become the oracle's assertion body; do not defer to Wave 4.
3. **Prove RED against the current backend** — the suite FAILS on F-02..F-05; commit that evidence (anti-tautology gate).
4. **Nightly Playwright vs dev** wired after the CI/MSW layer is green on fixtures.
5. When **F-02, F-03, F-04, F-05** land (Wave 4, Track F), the relevant assertions flip GREEN with **zero weakening** — the oracle then continuously guards the contract for all additive waves.

The oracle is a *check*, never a shipped-behavior change; it must never be weakened to pass, and the §3 contract it encodes is IMMUTABLE (any change to a §3 item requires adversarial review, scope-lock `adversarial_review_required_for: frontend_contract_item`).
