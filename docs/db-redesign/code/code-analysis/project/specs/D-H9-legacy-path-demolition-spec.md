---
spec_id: D-H9-LEGACY-PATH-DEMOLITION
title: "Legacy-path demolition, gated by a retirement register"
status: draft
owner: backend
tier: T1
scope_lock_clause: [D-H9]
tooling:
  D-H9: {claude_code: {model: fable, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - D-H9: Legacy-Path Demolition

> **ADOPTED 2026-07-27 — spec of record for D-H9** at scope-lock **v2.7.0**, superseding
> `specs/D-H9-company-research-migration-spec.md` (deleted in the same commit). D-H9's clause was
> repointed from "complete the FE-UI-044 CR migration" to legacy-path demolition; the retirement
> half of the original clause is kept verbatim, the migration half is dropped. See
> `specs/amendments/D-H2-harness-removal-amendment.md`.

> **Authored 2026-07-27 under the forward-thinking directive.** All stored data is test data,
> dropped before production. Nothing here migrates anything. Every item on the demolition list is
> deleted outright — **once, and only once, the evidence says nothing still depends on it.**

## Problem Statement

Retirement is currently scattered as a trailing clause across half a dozen specs — D-M2 ends with
"stop dual-key CV writes", D-H2's fix plan ends with replacing scattered key construction, D-H7
carves an exemption for a migration script. Each of those steps' actual job is the *new* thing; the
removal is the last line, and last lines are what get skipped. The residue is then found in Wave 5
by something that inexplicably still reads it.

The opposite failure is worse. A fixture that *looks* like dead legacy code can be the only thing
keeping live reads working — this codebase already contains that exact trap: the `pk`/`sk` write
paths read as legacy residue, and they are where VPR, tailored-CV, and gap-question records
currently live (`api_db_construct.py:114` aliases `self.db = self.users_table`, whose keys are
`pk`/`sk` at `:127-130`). Deleting on a static "no callers" reading would have destroyed the live
read path.

D-H9 therefore owns **both halves**: one step that removes everything, and a gate that will not let
it remove anything unproven.

## Evidence

Demolition list, read live from the working tree on 2026-07-27. **Must be re-confirmed live before
any deletion** — a stale list is the failure this project keeps recording.

| # | Item | Location | Runtime-conditional? |
|---|---|---|---|
| 1 | `ValidationException` → legacy-key retry → empty success | `dynamo_dal_handler.py:629-637`, `:678-684` | **Yes — error path only** |
| 2 | `_legacy_read_cover_letter_by_scan` | `dynamo_dal_handler.py:655-698` | Yes |
| 3 | `COVER_LETTER_LEGACY_READ_ENABLED` (defaults `'true'`) | `dynamo_dal_handler.py:621`, `:768` | Yes |
| 4 | `_query_cover_letter_items(..., use_canonical_keys=False)` legacy branch | `dynamo_dal_handler.py:709-733` | Yes |
| 5 | Dual-shape writes — both key conventions and both type spellings on one item | `dynamo_dal_handler.py:535-552` | No |
| 6 | Legacy aliases for mixed environments | `dynamo_dal_handler.py:101` | No |
| 7 | `DYNAMODB_TABLE_NAME` — 9 handler files, 26 infra injection points | see `D-M6-D-Q-canonical-storage-shape-spec.md` | No |
| 8 | `self.db = self.users_table` alias | `api_db_construct.py:114` | No |
| 9 | `cr_migration_backfill.py` + its quarantine report | `src/backend/scripts/cr_migration_backfill.py`, `src/backend/reports/cr-migration-quarantine-20260617T201543Z.json` | No |

Items 1–4 are **runtime-conditional**: whether they execute depends on an environment variable or on
a DynamoDB error occurring, not on whether a caller exists in source. A static scan cannot retire
them. Item 1 is the sharpest case — it executes *only* when the database rejects a read.

## Fix Plan

1. Publish a **retirement register** at
   `docs/db-redesign/code/code-analysis/project/runbooks/retirement-register.md`: one row per item
   above, naming its owning spec, the evidence type it requires, the evidence itself, and the date.
2. **Instrument before deleting.** Add one `logger.warning` at each doomed site naming the item id.
   Run the unit suite, the P-30 smoke harness, and a devx exercise window. Record hit counts.
3. **Fault-inject the error paths.** For items 1–4, a zero hit count proves only that the error did
   not occur. The proof for these is a forced-condition test showing the replacement handles what
   the old path caught.
4. Delete each item **only** when its register row carries both proofs. An item without evidence
   blocks its own removal, not the step.
5. Re-run the standing checks after deletion: unit suite, `cdk synth`, `scope-diff.py`, the F-01
   oracle, and the P-30 4-wire smoke.

## The Retirement Gate

**Two proofs per item. Neither substitutes for the other.**

- **Positive — the replacement handles the case.** Owned by whichever spec built the replacement,
  not by D-H9. D-H9 cites it; it does not re-prove it.
- **Negative — nothing still depends on the old thing.** Owned by D-H9. The evidence type depends on
  whether the item is runtime-conditional:

| Item type | Negative proof | Why not the other kind |
|---|---|---|
| Static (5–9) | Zero-occurrence source scan **plus** a test exercising every read path against records written in the new shape only | A scan proves no *caller*; it does not prove no *reader* of the old data shape |
| Runtime-conditional, flag-gated (2–4) | Instrumented hit counter, zero hits across unit suite + smoke + a named devx window | Source references exist by construction; only execution counts |
| Runtime-conditional, error-path (1) | **Fault injection** — force the `ValidationException` and show the replacement surfaces it correctly | A zero hit counter proves the error did not occur, **not** that the path is unused. This is the distinction the gate exists for. |

**Evidence per item, and who owns it:**

| # | Positive proof | Owning spec | Negative proof |
|---|---|---|---|
| 1 | `test_dh3_validation_exception_not_returned_as_not_found` | D-H2/D-H3 | Fault injection (same test) |
| 2–4 | `test_dh2_core_repository_reads_canonical_only_items` | D-H2/D-H3 | Instrumented counter, zero hits |
| 5 | `test_ds_no_duplicate_field_representation`, `test_ds_item_key_names_match_target_table_declaration` | D-M6/D-Q | `test_dh2_core_repository_reads_canonical_only_items` — reads succeed against canonical-only records |
| 6, 8 | `TableRegistry` resolves every table by one name | D-H2 | Zero-occurrence scan |
| 7 | `test_ds_every_lambda_receives_the_table_env_its_handler_requires` (synth) | D-M6/D-Q | The function→table resolution map, with every `CHANGED` row human-approved |
| 9 | — (nothing replaces it; it becomes unnecessary) | — | No scheduled invoker — confirm no EventBridge rule or CI job calls it |

**Item 7 carries the sharpest risk and is not deletable on a scan.** `DYNAMODB_TABLE_NAME` resolves
to the **users** table for the VPR generator (`api_construct.py:1374`) and to the **artifacts** table
for four other functions (`:2069,2913,2952,2991`). Deleting the variable without the function→table
map repoints handlers at a different table silently. The map is the negative proof.

## RED Tests to Write First

**Rule-14 note.** Every assertion below names an exact value. Counts marked *(re-confirm live)* are
the 2026-07-27 baseline and must be re-read before the test is written — they may shrink, and a
shrink is a finding, not a pass.

---

- `test_dh9_retirement_register_covers_every_demolition_item`: parse
  `runbooks/retirement-register.md` and assert it contains **exactly one row per item id 1–9**, that
  every row names a non-empty `positive_proof`, `negative_proof`, `evidence`, and `date`, and that
  no row carries the literal strings `TBD`, `pending`, or an empty cell. A missing or unfilled row
  fails. Cite AC-DH9-1.

- `test_dh9_no_item_deleted_without_evidence`: for each item id, assert the biconditional — the
  item's symbol is absent from the tree **if and only if** its register row is complete. A deleted
  item with an incomplete row fails (deleted unproven); a complete row whose symbol is still present
  fails only as a warning at RED time and as an error at the D-H9 GATE (proven but not yet removed).
  This is the assertion that makes the gate mechanical rather than procedural. Cite AC-DH9-1.

- `test_dh9_error_path_items_carry_fault_injection_not_a_counter`: assert that the register rows for
  item **1** name a fault-injection test by its pytest node id and **not** an instrumentation hit
  count. A row for item 1 whose `negative_proof` is a counter fails, with the message *"a zero
  counter proves the error did not occur, not that the path is unused."* Cite AC-DH9-2.

- `test_dh9_legacy_read_symbols_absent`: static scan over `src/backend/careervp/` asserting **zero**
  occurrences of each of `_legacy_read_cover_letter_by_scan`, `COVER_LETTER_LEGACY_READ_ENABLED`,
  and `use_canonical_keys`. Baseline to shrink from, read live 2026-07-27 *(re-confirm live)*:
  `_legacy_read_cover_letter_by_scan` 1 definition + 1 call site (`:624`, `:655`);
  `COVER_LETTER_LEGACY_READ_ENABLED` 4 occurrences (`:606`, `:621`, `:767`, `:768`);
  `use_canonical_keys` in `_query_cover_letter_items`. Cite AC-DH9-3.

- `test_dh9_no_dual_shape_write_remains`: exercise every artifact write path against moto and assert
  each written item's attribute set contains the canonical key names its target table declares and
  **none** of `pk`, `sk`, `artifact_type`. The named live violation is `dynamo_dal_handler.py:535-552`.
  Cite AC-DH9-3.

- `test_dh9_dynamodb_table_name_absent_everywhere`: static scan over
  `src/backend/careervp/handlers/`, `src/backend/careervp/logic/`, and `infra/careervp/` asserting
  **zero** occurrences of the string `DYNAMODB_TABLE_NAME`. Baseline *(re-confirm live)*: 9 handler
  files in the backend and 26 injection points in `api_construct.py`. Assert **zero**, not a ratchet
  — by the time D-H9 runs, D-M6/D-Q has converted the call sites and the infra injection, so a
  remaining occurrence is a missed site, not accepted debt. Cite AC-DH9-3.

- `test_dh9_users_table_alias_absent`: assert `infra/careervp/api_db_construct.py` contains zero
  occurrences of `self.db = self.users_table` and that no CDK construct reads `self.api_db.db`.
  Cite AC-DH9-3.

- `test_dh9_migration_script_has_no_scheduled_invoker`: parse the synthesized CloudFormation
  template and assert no `AWS::Events::Rule` target, Lambda handler string, or CI workflow step
  references `cr_migration_backfill`. Only when that holds may the script be deleted — an offline
  script with a live scheduler is not offline. Cite AC-DH9-2.

## Acceptance Criteria

**AC-DH9-1** - Given the demolition list, when any item is removed, then its retirement-register row
carries both a positive and a negative proof, dated, and no item is removed without one.

**AC-DH9-2** - Given a runtime-conditional item, when its negative proof is assessed, then an
error-path item is proven by fault injection and a flag-gated item by an observed zero hit count —
never by a source scan alone.

**AC-DH9-3** - Given the completed demolition, when the tree is scanned, then zero legacy read
symbols, dual-shape writes, overloaded table-name variables, or migration scripts remain.

## Done-when

All RED tests pass; the retirement register is complete and committed; every item on the demolition
list is removed; unit suite, `cdk synth`, `scope-diff.py`, the F-01 oracle, and the P-30 4-wire
smoke are all green after removal; no frontend contract drift.

## Sequencing / Dependencies

**Runs last in Wave 3.** Hard dependencies, because each supplies a positive proof this spec cites
and does not re-prove: D-H2/D-H3 (`CoreRepository`, `TableRegistry`, the ValidationException
surfacing and the canonical-only read test), D-M6/D-Q (canonical storage shape, the function→table
resolution map, the synth env-var assertion), D-M2 (single canonical CV key), D-H7 (request-path
scans eliminated — its migration-script exemption disappears with item 9, making its rule
unconditional).

**Do not run this step early to "get ahead".** Every deletion here is irreversible in the same
session that removes the only thing proving it was safe.
