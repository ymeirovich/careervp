# Wave 3 — Status Ledger

**Read this file FIRST before starting any Wave-3 prompt.** `wave-3-prompts.md` describes what
*should* happen; this file describes what *actually* happened, and is what every prompt checks
before starting its own work (see `RUNBOOK-RULES.md`, rules 2–3). Update your own row when you
finish a step or stop on a problem — do not leave this file stale for the next session to trip
over.

Rows are listed in dependency order. Before starting a step, read the row above it (or the rows
it depends on per `wave-3-prompts.md` §2) — if any of them show an open problem, resolve that
first.

---

## ✅ AUTHORIZED — Wave 2 GATE passed

**This ledger and `wave-3-prompts.md` were authored on 2026-07-26 *ahead of* the Wave-2 GATE, by an
explicit human decision to prepare Wave 3 in parallel (authoring is gate-safe: no code, no test, no
deploy crosses the barrier).** The barrier is now clear: the `GATE` row in
[`/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md`](./wave-2-status.md)
reads **PASSED** from evidence `docs/evidence/wave2-gate-20260726T205022Z-d8707a.json`
(9 PASS, 0 FAIL, 0 HUMAN_REQUIRED, 2 RECORDED), and the required smoke harness evidence
`docs/evidence/smoke-20260726T205022Z-fdac58.json` is 4/4 green. Wave 3 may now execute, starting
with 3.1-RED.

---

**Deploy target: `CareerVpCrudDevx`** (project-wide since 2026-07-25 — `CareerVpCrudDev` is being
retired). Anything pointed at `api.dev.careervp.com` is talking to the OLD stack; use the raw invoke
URL `https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/` until the human-only base-path
flip happens. **No Wave-3 work merges to `main`** — the push-to-`main` CI path still targets the old
stack (Wave-2 bet `B-2-4`, item 1, still open).

| Step | Clause(s) | Status (plain English) | Open problem for the next step | Commit | Date |
|---|---|---|---|---|---|
| 3.1-RED | D-H2, D-H3 | **RED LANDED in the working tree after the human D-H2 contract correction.** Added exactly four tests in `src/backend/tests/unit/test_dh2_dh3_key_authority.py`; all four collect and fail on their intended AC assertions. The artifact-key scan reports **56** live artifacts/core key-building sites while explicitly excluding auth/trial/user-pool keying; its B-3-5 `USER#` ratchet re-confirms **9 sites / 5 files**. The D-H3 and canonical-only tests catch the absent module import inside the test and fail via explicit `AC-DH3-1` / `AC-DH2-1` messages naming `careervp.dal.core_repository`, not collection errors or skips. The env-precedence scan reports the spec's full enumerated **22 locations / 9 files** and records that the heading says 23 although the list sums to 22; the test retains 23 as the maximum and freezes all 22 source signatures so a new site fails. B-3-2 is confirmed TRUE/default-on in `ISSUES.md` (`dynamo_dal_handler.py:628-637`, flag default `'true'` at `:621`; scan twin at `:677-683`); B-3-5's count delta is recorded there. Verification: repository-wide Ruff format/check clean; strict mypy clean on the new file; focused existing regressions `18 passed`; pre-existing unit suite with only this intentional RED file excluded `1374 passed, 15 skipped, 4 xfailed, 1 xpassed`; `check_scope_lock_integrity.py --base HEAD` reports `OK`. Zero files under `src/backend/careervp/` were modified. Prompt and corrected D-H2/D-H3 YAML clauses match; no harness test or AC-DH2-2 was added. | **3.1-GREEN must run in a fresh session and may not edit this RED file.** Create importable `careervp.dal.core_repository.CoreRepository` and `careervp.dal.table_registry.TableRegistry`; re-home the 56 reported artifacts/core key constructions; remove the 22 reported handler precedence sites without widening either ratchet; preserve D-H3's three outcomes (retry-hit succeeds with item, retry-miss becomes `TABLE_SCHEMA_MISMATCH`, retry-raises unchanged); make every canonical cover-letter read return the canonical-only moto item. **Human commit ceremony remains:** the correction note says to add the v2.7.1 §12 row to the MD twin and use a `Scope-Lock-Approved-By:` trailer. The current integrity command returns `OK`, so it does not enforce that missing row in the working tree; do not mistake that tooling result for the human approval trailer a commit still needs. | pending — proposed commit message: `test: add RED key-authority and schema-mismatch contracts` | 2026-07-27 |
| 3.1-GREEN | D-H2, D-H3 | **GREEN — all four RED tests pass with implementation-only changes; zero test files and zero spec RED-briefs modified** (the only test change is a NEW 9-test characterization file, `src/backend/tests/unit/test_table_registry_characterization.py`, pinning key grammar and env-resolution semantics before re-homing). Created `careervp/dal/table_registry.py` (sole artifacts/core key-grammar + table-name-resolution authority) and `careervp/dal/core_repository.py` (repository entry point; canonical cover-letter read `CoreRepository.get_cover_letter_by_artifact_id`). All **56** reported artifacts/core key sites re-homed out of `handlers/`+`logic/` and all **22** enumerated env-precedence sites removed from the 9 handler files — both scans now assert zero live sites; neither ratchet baseline was widened, and the full baseline cleared in one session (no B-3-5 residue enumeration needed). The env chains survive **only inside the registry**, deliberately as three distinct named roles (full artifacts chain, legacy two-key tail, company-research chain) because `ai_assist_nested_stack.py` points `ARTIFACTS_TABLE_NAME` and `COMPANY_RESEARCH_TABLE_NAME` at **different physical tables** — collapsing them would silently retarget reads. `dynamo_dal_handler.py`'s `save_cv` legacy-alias keys and key-prefix constants now come from the registry. D-H3: both named swallow sites (`read_cover_letter_by_artifact_id` get_item retry and the `_legacy_read_cover_letter_by_scan` twin) return `Result(success=False, code=TABLE_SCHEMA_MISMATCH)` with an error log on a ValidationException retry-miss; retry-hit and retry-raise outcomes unchanged, per the spec's three-outcome GREEN boundary. Verification, all fresh: 4 RED tests pass; full suite `1553 passed, 30 skipped, 4 xfailed, 1 xpassed`, zero regressions; Ruff format+check clean; `mypy careervp --strict` clean (136 files); `make coverage-tests` exit 0 — overall 73.13/54.50, core 73.36/**55.52** (Wave-2 measured 55.49 — core-branch ratchet held and improved), supporting 73.67/52.26; oracle tests (`test_frontend_oracle_schema_emission.py` + `test_route_parity_openapi.py`) 5 passed — no §3 identifier/response-shape drift; `check_scope_lock_integrity.py --base HEAD` OK. Also verified: the RED commit `fb41d22` landed **with** the human `Scope-Lock-Approved-By` trailer, so the ceremony flagged in the 3.1-RED row is complete. | **Parity-harness import path: none — the harness was retired at scope-lock v2.7.0; nothing for 3.2/3.4/3.5 to import.** They extend `careervp.dal.core_repository.CoreRepository` / `careervp.dal.table_registry` instead (contention hotspot — serialize per §2). Residues recorded, not hidden: (a) `logic/company_research_store.py::_legacy_table_name` still resolves `TABLE_NAME → DYNAMODB_TABLE_NAME` (reversed legacy order) — it is outside the handler-scoped baseline and dies with the CR legacy path in 3.5 (D-H9 demolition); (b) `dal/dynamo_dal_handler.py` still builds keys internally — `dal/` is outside the scan boundary and its grammar constants now come from the registry, but collapsing its key building into `CoreRepository` is later-wave work; (c) the inner query-level fallback in `_legacy_read_cover_letter_by_scan` (canonical-query ValidationException → legacy query → miss at the `allow_sk_match=False` match) still returns success-None — the spec's GREEN boundary named only the two outer sites; flag for 3.5 when the whole legacy scan path is demolished. | `f438355` | 2026-07-27 |
| 3.2 | D-H4, P-01 | not started (skeleton — fill in after 3.1-GREEN lands) | — | — | — |
| 3.3 | D-H7 | not started (skeleton — fill in after 3.1-GREEN lands) | — | — | — |
| 3.4 | D-M1, D-M2, D-M3, D-M5, D-M6, D-Q | not started (skeleton — fill in after 3.1-GREEN lands) | — | — | — |
| 3.5 | D-H9 | not started (skeleton — fill in after 3.1-GREEN lands) | — | — | — |
| GATE | — | not started | — | — | — |

---

## Wave-3 bets (rule 9 — ✅ PROMOTED to `ISSUES.md` 2026-07-27, before any prompt ran)

Rule 9 requires every belief a wave rests on to be written down *before* its prompts run, with the
cheapest check that would disprove it and the fallback decided now. **All five live in
`/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/ISSUES.md`
under "Wave-3 bets"** — that is the authoritative text (belief, why it is a bet, cheapest-tier check,
fallback decided now, settled-status). The table below is the index; read the full entries there, and
re-read every one at the GATE.

`B-3-5` is new — added during the 2026-07-27 pre-flight when the two D-H2 static scans turned out to
have no scope boundary at all. It is the bet whose absence blocked Wave-2 step 2.2.

| Bet | Belief (stated so it could be false) | Cheapest check (rule 9 ladder) | Fallback if false |
|---|---|---|---|
| B-3-1 | The migration-parity harness (built in 3.1) can assert *exact* public-projection equality between a legacy read and the canonical read for every migrated slice, with no benign diffs. **SETTLED FALSE 2026-07-27 — fallback taken.** | Tier 3 — one minimal moto test: seed one legacy + one canonical record for a single artifact type, run the harness, inspect the diff. **Not needed: settled by Tier 1 instead.** A live read of the DAL write paths found benign diffs are guaranteed, not hypothetical — the cover-letter write at `dynamo_dal_handler.py:535-552` puts *both* key conventions and *both* spellings of the type field on one item, and the artifacts/gap-responses/knowledge tables declare `time_to_live_attribute="expiration"` while the DAL writes `ttl`. Exact raw equality was never achievable. | **Fallback taken, in force.** The harness normalizes against a documented internal-field allowlist, now **enumerated with its derivation rule** in `D-H2-D-H3-key-authority-spec.md` (10 attributes, each with live evidence). Grows only by a dated ledger entry. **RETIRED at scope-lock v2.7.0** — the harness no longer exists; nothing in Wave 3 depends on this bet. Full entry kept in `ISSUES.md` for the GATE re-read. |
| B-3-2 | The swallowed `ValidationException`s D-H3 targets are actually reachable on the request path, not dead defensive `except` blocks. | Tier 1 — grep the DAL/handler `except` sites that convert `ValidationException`→`None`/404; Tier 3 — a moto test forcing a malformed key. | If unreachable, D-H3 ships as a guard-rail + regression test (surface-and-log), not a behavior change; record that it changed nothing live and why. |
| B-3-3 | The "239 legacy CR items" figure D-H9 (3.5) backfills is still accurate at Wave-3 time. **RETIRED at scope-lock v2.7.0 — there is no backfill.** | Tier 1 — live count in **devx** before 3.5. **Not needed:** D-H9 was repointed to demolition; legacy CR items are deleted, not migrated. | None required. The demolition gate asks a different question — not "how many items are there" but "does anything still read them". |
| B-3-4 | Wave-3's GSI changes (3.4 minimized GSI, retire `userEmail` PK) stay under the CFN resource ceiling and cause zero stateful replacement. Carries `B-2-3` forward. | Tier 4 — **isolated synth-template diff** per infra-touching step (HEAD vs change-stashed, no live stack — the 2.3-root-cause technique); assert zero replacement markers on stateful resources. | Sequence the GSI add/remove as separate gated deploys (add new → dual-read → drop old), never a single replacing change. |
| B-3-5 | D-H2's two static scans can be scoped to the **artifacts/core** table without leaving a hole — user/application/jobs keying stays for Wave-6 D-H8. | Tier 1 — enumerate every candidate site live and classify it, **before** the test is written. Done 2026-07-27. | Ship the scan as a **frozen-baseline ratchet** (enumerated sites, may shrink never grow) rather than an absolute zero-occurrences assertion the wave is not scoped to satisfy. |

---

## ✅ SCOPE-LOCK AMENDMENT LANDED — v2.7.0, 2026-07-27

**Decision:** all stored data in every environment is disposable test data, dropped before
production. Wave 3+ is **forward-thinking only** — no migration, no dual-read, no backfill, no
cutover. A record in a legacy shape is deleted and rewritten, never migrated.

**Landed in `project-scope-lock.{md,yaml}` at v2.7.0** (proposal:
`../specs/amendments/D-H2-harness-removal-amendment.md`):

- **Harness retired** from D-H2; `migration-parity` dropped from D-H4 / D-M2 / D-M5 / D-H9
  verification. A14 homed it to prove a live-data cutover; there is no cutover.
- **D-H9 repointed** from "complete the FE-UI-044 CR migration" to **legacy-path demolition gated
  by a retirement register**. The retirement half of the clause is kept verbatim; the migration
  half is dropped. `../specs/D-H9-legacy-path-demolition-spec.md` is the spec of record and
  supersedes `D-H9-company-research-migration-spec.md`, which is deleted.
- **O-3 resolved** (cutover/downtime tolerance + retention window). It was OPEN and formally
  `blocks: [wave_3, wave_6]` — a question that gated this entire wave.
- **Bets `B-3-1` and `B-3-3` retired** in `ISSUES.md`, kept rather than deleted so rule 9's
  re-read at the GATE does not mistake a vanished bet for an unsettled one.

**Also landed alongside, not part of the contract change:** `RUNBOOK-RULES.md` **rule 18** (Fable
routed to long-horizon implementation only — never RED, recon, GATE, or security work), a fourth
bucket in the execution plan's model convention, and the D-M6/D-Q clause-mapping fix (the seams
bundle dropped both clauses; `D-M6-D-Q-canonical-storage-shape-spec.md` now owns them outright, so
`scope-diff.py`'s clause→spec mapping is deterministic again).

**Caveat recorded, not hidden:** §0.3 says the contract twins are write-protected from agent
sessions and land only via a human-executed commit. This amendment was **applied by an agent
session at explicit human direction**, with the approval trailer naming the human approver. If the
governance intent is that a human literally authors the twin diff, amend the commit.

---

## Standing notes carried into every step (do not lose these)

- **The two IMMUTABLE laws apply to every row that touches `infra/`:** never move the live API
  (`RestApi`), never move the Cognito user pool. Internal PK/SK/table changes are fine; the API
  Gateway logical id and the Cognito pool logical id stay byte-stable.
- **Frontend §3 identifiers and response shapes may not drift.** D-H2/D-H4/D-M all change *internal*
  keying; none of that is an API change. The executable oracle (Wave-0 step 0.3,
  `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/F-frontend-oracle-spec.md`)
  is the contract check — a Wave-3 change that alters a §3 identifier is a rule-5 stop.
- **Migration-parity discipline (v2.0.0/A14) is RETIRED — superseded by v2.7.0 / `O-3`** (see the
  amendment section above). Wave 3 is forward-thinking only: no migration, no dual-read window, no
  backfill, no cutover, and **no parity harness** — 3.1 does not build one and 3.2/3.4/3.5 do not
  consume one. A record in a legacy shape is deleted and rewritten. D-H2's `verification` is `unit`.
- **`CoreRepository` / `TableRegistry` (created by 3.1) is the Wave-3 contention hotspot** — the
  analogue of `api_construct.py` in Wave 2. Every later step extends it. Never run two steps that
  edit it at the same time; see `wave-3-prompts.md` §2 for the serialization order.
- **Deploy target is `CareerVpCrudDevx`; deploys are manual-dispatch only; nothing merges to
  `main`** (Wave-2 `B-2-4` item 1 open). Anything at `api.dev.careervp.com` is the OLD stack.
- Carried in from earlier waves, still open, none of which gate Wave 3: **P-07b** (browser admin
  scope + implicit grant — gates STAGING, has a written stopping condition); **I-05** (AI-assist
  token-metering red test — belongs to the metering clause, do not silence it inside a Wave-3 step);
  **I-06** (login client admin scope). Do not fix these as a side effect of a Wave-3 step.
