# Amendment Proposal — retire the migration-parity harness; Wave 3+ is forward-thinking only

> Emitted per scope-lock §0.3. This is a proposal awaiting human validation. It
> does not edit either `project-scope-lock` twin, change infrastructure, or
> authorize a deployment. Per §0.3/A3 the contract twins are write-protected
> from agent sessions and must be human-committed.

| Field | Value |
|---|---|
| **clause_id** | `D-H2` (primary — harness homing), `D-H4` / `D-M2` / `D-M5` / `D-H9` (verification mode), `O-3` (open question resolved) |
| **tag** | All five clauses are `status: TARGET`. No IMMUTABLE invariant, no locked decision (`L-1`–`L-7`), no frontend-contract item is changed. |
| **semver level** | **MINOR** — "refine a TARGET; resolve an OPEN". Rationale below. |
| **affected contract twins** | `project-scope-lock.md`, `project-scope-lock.yaml` (updated together, with a §12 / `change_log` row) |
| **affected specs** | `D-H2-D-H3-key-authority-spec.md`, `D-H4-P-01-canonical-artifact-spec.md`, `D-M-seams-bundle-spec.md`, `D-H9-company-research-migration-spec.md` (superseded), `D-H9-legacy-path-demolition-spec.md` (new, adopted by this amendment) |
| **affected tests** | None exist yet — Wave 3 has written no test. This is why the amendment is cheap **now** and expensive after 3.1-GREEN. |
| **affected runbooks** | `runbooks/wave-3-prompts.md` (3.1-RED / 3.1-GREEN / 3.2), `runbooks/wave-3-status.md`, `redesign-execution-plan.md:301,342`, `test-strategy.md:98`, `ISSUES.md` (`B-3-1`, `B-3-3`) |
| **requires adversarial review?** | **No** per `amendment_protocol.adversarial_review_required_for` — the harness is neither an immutable invariant, a locked decision, nor a frontend-contract item. Human sign-off is still mandatory. |

## Proposed decision

**All stored data in every environment is test data and is dropped before production.** Wave 3 and
onward are therefore **forward-thinking only**: there is no migration, no dual-read window, no
backfill, and no cutover. Records in a legacy shape are deleted and rewritten, never migrated.

Three consequences:

1. **The migration-parity harness is retired.** Its sole purpose is to prove that a record read the
   old way and the same record read the new way are identical — i.e. that migrating lost nothing.
   With nothing migrated, it has no job. It is removed from `D-H2` and the `migration-parity`
   verification mode is dropped from `D-H4`, `D-M2`, `D-M5`, and `D-H9`.
2. **`D-H9` is repointed, not deleted.** Its clause survives with its content generalized from
   *"complete the in-flight FE-UI-044 CR migration (verify the 239-item backfill, confirm dual-read
   parity, retire the legacy read path)"* to *"retire every legacy read path, dual-shape write, and
   overloaded table-name variable, each gated on evidence that nothing still depends on it."* The
   retirement half of the original clause is kept verbatim; only the migration half is dropped.
   `D-H9-legacy-path-demolition-spec.md` is its new spec and supersedes
   `D-H9-company-research-migration-spec.md`.
3. **`O-3` is resolved.** It currently reads *"cutover/downtime tolerance + retention window"* with
   `blocks: [wave_3, wave_6]` and **no `status: RESOLVED`** — so a question that formally blocks
   Wave 3 is open right now. The forward-thinking decision answers it: there is no cutover to
   tolerate and no retention window to honour, because nothing is being carried across.

## Why the amendment is needed

`project-scope-lock.md:165` names D-H2 as "**also home of the reusable dual-read migration-parity
harness**", and `project-scope-lock.yaml:114` carries `verification: contract+integration+migration-parity`
on D-H4 (likewise D-M2 `:117`, D-M5 `:119`, D-H9 `:123`). Those lines were added by **v2.0.0
amendment A14**, which homed the harness in D-H2 on the reasoning that *"a pre-launch live-data
cutover is proven `legacy read == core read` per item"*. **The premise "live-data cutover" is what
changed.** A14's reasoning was correct given a live-data assumption; the assumption no longer holds.

Without this amendment, 3.1 builds an instrument whose only consumer set (`3.2`, `3.4`, `3.5`) will
never call it, and four downstream specs keep parity preconditions that gate work on proving
something about data that will be deleted.

**The amendment is also load-bearing for correctness, not only cost.** Bet `B-3-1` was settled FALSE
on 2026-07-27: exact raw-item parity was never achievable on this data, because the cover-letter
write at `src/backend/careervp/dal/dynamo_dal_handler.py:535-552` puts **both** key conventions and
**both** spellings of the type field on one item. The harness only works at all behind a
10-attribute exclusion allowlist. Keeping it means maintaining that allowlist for an assertion
nobody needs.

## Evidence cited

All read live from the working tree on 2026-07-27 and re-confirmable by command:

| Claim | Evidence |
|---|---|
| Artifact records are written with three different key conventions | `dynamo_dal_handler.py:303-308` (`pk`/`sk`), `:535-552` (both), `:980-990` (`userId`/`questionId`) |
| Artifact records currently land in the **users** table, not the artifacts table | `api_db_construct.py:114` (`self.db = self.users_table`) + `:127-130` (users-table keys are `pk`/`sk`) + `api_construct.py:1374` (`DYNAMODB_TABLE_NAME = db.table_name`) |
| One env var resolves to three different tables | `api_construct.py:1374` (users), `:2069`, `:2913`, `:2952`, `:2991` (artifacts) |
| Exact parity was never achievable | `dynamo_dal_handler.py:535-552` — duplicate key conventions and duplicate type spellings on a single item |
| Nothing has been built against the harness yet | Wave 3 has written zero tests; `wave-3-status.md` 3.1-RED row |
| `O-3` is open and blocks Wave 3 | `project-scope-lock.yaml:257` — no `status: RESOLVED` |

## Semver rationale

**MINOR.** Per `amendment_protocol.semver`, MINOR covers *"refine a TARGET; resolve an OPEN"* — this
does both: five `TARGET` clauses are refined and `O-3` is resolved. MAJOR covers *"change an
IMMUTABLE invariant/locked-decision; drop a feature; break a frontend-contract item"*, and none
applies: the harness is an internal test instrument, not a product feature, and no frontend-contract
item moves.

**The MAJOR reading, stated so you can overrule me:** if you read "drop a feature" as covering any
scoped deliverable rather than only a product feature, this is MAJOR. It reverses part of a v2.0.0
eval-council condition (A14), which is the strongest argument for the heavier tag. I propose MINOR
because the council's condition was *"the harness has no owner before Wave-3 data migrations"* — a
conditional whose antecedent this amendment removes — but the call is yours, and taking MAJOR costs
nothing but a version digit.

## The full change set — apply as ONE commit, not piecemeal

| # | Artifact | Change |
|---|---|---|
| 1 | `project-scope-lock.md:165` | Drop "**Also home of the reusable dual-read migration-parity harness**" and its parenthetical from D-H2 |
| 2 | `project-scope-lock.md:173` | Rewrite D-H9: migration/backfill/parity → legacy-path retirement gated on evidence |
| 3 | `project-scope-lock.yaml:114` | D-H4 `verification: contract+integration+migration-parity` → `contract+integration`; delete the A14 `note` |
| 4 | `project-scope-lock.yaml:117` | D-M2 `verification: integration+migration-parity` → `integration` |
| 5 | `project-scope-lock.yaml:119` | D-M5 `verification: migration-parity+security` → `security` |
| 6 | `project-scope-lock.yaml:123` | D-H9 title + `verification: migration-parity` → `integration`; drop `current_state: partial_migration_dual_read_fallback_live` and the A10 note |
| 7 | `project-scope-lock.yaml:257` | `O-3` → `status: RESOLVED, resolved: "2026-07-27", decision: "no cutover tolerance and no retention window — all stored data is disposable test data, dropped before production; Wave 3+ is forward-thinking only"` |
| 8 | Both twins | §12 / `change_log` row + version bump + `Scope-Lock-Approved-By:` trailer |

Then, in the same commit or an immediate follow-up (these are **not** contract files, so an agent
session may make them once the twins land):

| # | Artifact | Change |
|---|---|---|
| 9 | `D-H2-D-H3-key-authority-spec.md` | Delete `test_dh2_migration_parity_harness_reports_identical_projection`, the allowlist block, `AC-DH2-2`, Fix-Plan item 3, and the Done-when harness clause. Keep `test_dh2_core_repository_reads_canonical_only_items` — it is a retirement proof, not a parity proof. |
| 10 | `D-H4-P-01-canonical-artifact-spec.md:34,42` | Drop the parity precondition and `test_dh4_legacy_artifact_id_parity_before_cutover` |
| 11 | `D-M-seams-bundle-spec.md:35,45` | D-M2 becomes "one canonical key, full stop"; delete `test_dm2_cv_migration_parity_before_dual_key_retire`; keep `test_dm2_cv_write_has_single_canonical_key` |
| 12 | `D-H9-company-research-migration-spec.md` | Superseded by `D-H9-legacy-path-demolition-spec.md`; delete or archive |
| 13 | `ISSUES.md` `B-3-1`, `B-3-3` | Retire both with a dated note — rule 9 re-reads every bet at the GATE, so a live bet pointing at deleted work trips it |
| 14 | `wave-3-prompts.md` | Remove harness deliverables and `AC-DH2-2` citations from 3.1-RED / 3.1-GREEN / 3.2 |
| 15 | `redesign-execution-plan.md:301,342` · `test-strategy.md:98` | Remove the A14 harness homing |
| 16 | `wave-3-status.md` | Delete the pending-amendment block; record the amendment as landed |

## Cost of NOT approving

3.1-GREEN builds the harness and the 10-attribute allowlist; 3.2, 3.4, and 3.5 each carry a parity
precondition that gates real work on proving a property of data that is about to be deleted. The
amendment stays available afterwards, but by then it also has to delete working code and passing
tests — today it deletes only prose.

## How to approve

Per `amendment_protocol.deviation_loop` and `contract_self_protection`:

1. **Read this proposal and decide the semver level** (MINOR proposed; MAJOR defensible).
2. **Edit both twins yourself** — `project-scope-lock.md` and `project-scope-lock.yaml`, items 1–8
   above. An agent session may not make these edits.
3. **Commit them yourself**, in one commit containing all four of what the CI guard requires
   (`scripts/ci/check_scope_lock_integrity.py`, `.github/workflows/scope-lock-guard.yml`):
   - a §12 / `change_log` row describing the change,
   - a **Version** bump on both files,
   - **twin-sync** (both files in the same commit),
   - a **`Scope-Lock-Approved-By:`** trailer in the commit message.
   Missing any one of the four and the guard rejects the diff.
4. **Tell me it landed.** Items 9–16 are ordinary files, so I make those and re-run
   `scope-diff.py` to confirm no clause is left uncovered and no spec orphaned.

There is no approval command and no flag — the human-executed commit *is* the approval, and the
trailer is the signature.
