---
spec_id: D-M6-D-Q-CANONICAL-STORAGE-SHAPE
title: "Canonical storage shape: one table per entity, declared key names, one casing, enforced TTL"
status: draft
owner: backend
tier: T1
scope_lock_clause: [D-M6, D-Q]
tooling:
  D-M6: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  D-Q: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - D-M6/D-Q: Canonical Storage Shape

> **Authored 2026-07-27 under the forward-thinking directive.** All stored data is test data and is
> dropped before production. This spec describes the **target** shape only. It contains no
> migration, dual-read, backfill, or parity clause, and none may be added to it — a record in the
> wrong shape is deleted and rewritten, never migrated. Every line of Evidence below was read live
> from the working tree on 2026-07-27 and **must be re-confirmed live before RED**.

## Problem Statement

No document states what a stored record should look like. The result is not drift from a standard —
there is no standard to drift from. One DAL file writes three different key conventions, sends
artifact records to two different tables, writes the same logical field under two spellings on one
item, and writes an expiry field that no table reads. Every Wave-3+ spec that says "canonical"
assumes a target shape that no artifact defines. D-M6 owns the schema contract; D-Q owns
schema-enforced TTL. This spec is that contract.

## Evidence

**Three key conventions in one file** (`src/backend/careervp/dal/dynamo_dal_handler.py`):

- `pk`/`sk` — VPR `:303-308`, tailored CV `:440-451`, gap questions `:902-912`
- `applicationId`/`artifactId` — cover letter `:535-552`
- `userId`/`questionId` — gap responses `:980-990` and `:1014-1025`

**Artifact records are stored in the users table.** `infra/careervp/api_db_construct.py:114` aliases
`self.db = self.users_table`, and the users table declares `pk`/`sk` as its keys
(`api_db_construct.py:127-130`). `api_construct.py:1374` injects `DYNAMODB_TABLE_NAME =
db.table_name` into the VPR generator, so every `pk`/`sk` artifact write above lands in the **users
table**, not the purpose-built artifacts table that sits beside it with `applicationId`/`artifactId`
keys (`api_db_construct.py:472-479`). This is the mechanical root of the P-01 three-schema drift.

**One environment variable, three tables.** `DYNAMODB_TABLE_NAME` resolves to the users table for
the VPR generator (`api_construct.py:1374`) and to the artifacts table for cover-letter-worker
`:2069`, cover-letter-api `:2913`, interview-prep-api `:2952`, and cover-letter-status `:2991`.
A handler falling through to it cannot know which table it received.

**Duplicate representation of one fact.** The cover-letter write at `:535-552` puts both key
conventions on a single item (`applicationId`/`artifactId` *and* `pk`/`sk`) and both spellings of
the type field (`artifactType` *and* `artifact_type`).

**Mixed casing across one record.** Key attributes are camelCase (`applicationId`, `artifactId`,
`artifactType`), payload attributes are snake_case (`user_id`, `cv_id`, `created_at`), and the API
returns snake_case (`artifact_id`, `src/backend/careervp/handlers/cover_letter_handler.py:869`). The
users table contradicts the pattern again with snake_case GSI keys (`user_id`, `customer_id`,
`api_db_construct.py:151-165`).

**TTL is written to a field no table reads.** The DAL writes `ttl` at `:451,550,912,989,1024`. The
artifacts, gap-responses, and knowledge tables all declare `time_to_live_attribute="expiration"`
(`api_db_construct.py:483,415,442`). The users table declares no TTL attribute at all
(`:123-168`). **Nothing written by these paths ever expires.**

**Two artifact types carry no lifecycle metadata.** The VPR write at `:303-308` sets neither
`artifact_type` nor any expiry field.

## Fix Plan

1. Publish the **entity→table map** below as the single authority for which table holds which
   record. One entity, one table, no alternates.
2. An item's key attribute names are **exactly** the names its target table declares. No aliasing,
   no second key convention on the same item.
3. Each logical field appears **once** per item, in one spelling. Key attributes take the casing
   their table declares; every non-key payload attribute is `snake_case`.
4. The expiry attribute an item writes is **the name its target table declares** as
   `time_to_live_attribute`. A table with no declared TTL attribute receives no expiry field.
5. Table name resolution goes through `TableRegistry` (D-H2). Each Lambda receives exactly one
   environment variable per table it uses, named for that table. `DYNAMODB_TABLE_NAME` is retired.
6. Publish the **function→table resolution map** as a synth-time assertion, so a Lambda missing the
   variable its handler requires fails at synth rather than at runtime.

## Entity to Table Map

| Entity | Table | Key attributes | Expiry attribute |
|---|---|---|---|
| VPR | artifacts | `applicationId` / `artifactId` | `expiration` |
| Tailored CV | artifacts | `applicationId` / `artifactId` | `expiration` |
| Cover letter | artifacts | `applicationId` / `artifactId` | `expiration` |
| Interview prep | artifacts | `applicationId` / `artifactId` | `expiration` |
| Company research | artifacts | `applicationId` / `artifactId` | `expiration` |
| Gap questions | artifacts | `applicationId` / `artifactId` | `expiration` |
| Gap responses | gap-responses | `userId` / `questionId` | `expiration` |
| User profile / session | users | `pk` / `sk` | none declared |
| Knowledge | knowledge | `userEmail` / `knowledgeType` | `expiration` |

Two rows are judgment calls and are flagged for human confirmation before RED, not silently
settled: **gap questions** are routed to the artifacts table because they are generated output,
while **gap responses** stay in their own declared table because they are user-submitted input.
**Knowledge** retains its `userEmail` partition key here only because retiring it is D-M5's clause,
not this one; this spec does not pre-empt that decision.

## RED Tests to Write First

**Approved storage-shape authority modules** (the only paths that may name a table or build a key):

- `src/backend/careervp/dal/table_registry.py`
- `src/backend/careervp/dal/core_repository.py`

---

- `test_ds_item_key_names_match_target_table_declaration`: for each write path in the entity→table
  map, seed moto with the table as declared in `api_db_construct.py` and assert the written item's
  attribute set contains **exactly** the two key names that table declares and **no** key name from
  any other convention. Exact assertion per artifact write: `'applicationId' in item`,
  `'artifactId' in item`, `'pk' not in item`, `'sk' not in item`, `'userId' not in item`,
  `'questionId' not in item`. Cite AC-DM6-2.

- `test_ds_no_duplicate_field_representation`: assert no written item carries two spellings of one
  logical field. Exact: for every item produced by any write path,
  `not ('artifactType' in item and 'artifact_type' in item)`, and the set of item keys contains no
  pair `(x, y)` where `y == to_snake_case(x)` and `x != y`. The cover-letter write at
  `dynamo_dal_handler.py:535-552` is the named live violation and must fail this test before
  implementation. Cite AC-DM6-2.

- `test_ds_expiry_attribute_matches_table_ttl_declaration`: assert the expiry attribute written
  equals the target table's declared `time_to_live_attribute`. Exact: artifacts, gap-responses, and
  knowledge writes produce `'expiration' in item` and `'ttl' not in item`; users-table writes
  produce neither `'expiration'` nor `'ttl'`. The five `'ttl'` writes at
  `dynamo_dal_handler.py:451,550,912,989,1024` are the named live violations. Cite AC-DQ-1.

- `test_ds_every_artifact_write_carries_type_and_expiry`: assert every write path routed to the
  artifacts table produces an item containing `artifact_type` and `expiration`. The VPR write at
  `dynamo_dal_handler.py:303-308` is the named live violation — it sets neither. Cite AC-DM6-2.

- `test_ds_no_dynamodb_table_name_env_var_anywhere`: static scan over
  `src/backend/careervp/handlers/`, `src/backend/careervp/logic/`, and `infra/careervp/` asserting
  zero occurrences of the string `DYNAMODB_TABLE_NAME`. **Enumerated baseline, read live
  2026-07-27:** 9 handler files in the backend (`ai_assist_handler.py:69,498`;
  `company_research_handler.py:113,404`; `cover_letter_handler.py:57,59-64,659,744,1381,1458`;
  `cover_letter_submit_handler.py:72`;
  `cv_tailoring_handler.py:346,579,734,805,860,948,1003,1004,1040`; `export_handler.py:161`;
  `interview_prep_handler.py:49,441`; `interview_prep_submit_handler.py:72`;
  `vpr_submit_handler.py:354`) and 26 injection points in `infra/careervp/api_construct.py`. The
  assertion is **zero**, not a ratchet. Cite AC-DM6-3.

- `test_ds_every_lambda_receives_the_table_env_its_handler_requires`: synthesize the CDK template
  and, for each `AWS::Lambda::Function`, resolve its `Handler` property to the handler module, look
  up that module's required table variables in the function→table resolution map, and assert every
  one is present in that function's `Environment.Variables`. Asserts against the **synthesized
  template**, not source, and requires no deploy. Cite AC-DM6-3.

- `test_ds_function_table_resolution_map_is_complete`: assert the committed function→table
  resolution map names every `AWS::Lambda::Function` in the synthesized template, and that each row
  records the table the handler's current environment-variable chain resolves to **today** plus the
  table the map assigns it **going forward**, with rows where those differ marked `CHANGED`. A
  function absent from the map fails the test. This is the instrument that makes a silent table
  switch impossible; see "Conversion Safety" below. Cite AC-DM6-3.

## Conversion Safety

Data is disposable; **configuration is not**. The environment-variable chains being deleted are live
wiring, and collapsing them can silently repoint a handler at a different table — the VPR generator
resolves `DYNAMODB_TABLE_NAME` to the **users** table today while four cover-letter and
interview-prep functions resolve the identical variable to the **artifacts** table.

The function→table resolution map is the guard. It records, per Lambda, what the chain resolves to
today and what the registry will resolve to after conversion. Rows that match are mechanical. Rows
marked `CHANGED` are deliberate repointings that a human approves before the conversion lands. The
danger is never that a table assignment changes — several must. The danger is a table assignment
changing without anyone noticing, and the map converts that into a visible decision.

## Acceptance Criteria

**AC-DM6-2** - Given any stored record, when it is written, then its key names are exactly those its
target table declares, each logical field appears once in one spelling, and its type and expiry
metadata are present.

**AC-DM6-3** - Given any Lambda function, when the template is synthesized, then it receives exactly
one environment variable per table its handler uses, named for that table, and the function→table
resolution map accounts for every function with `CHANGED` rows human-approved.

**AC-DQ-1** - Given any table with a declared TTL attribute, when a record is written to it, then
the expiry value is written to that declared attribute name and records actually expire.

## Done-when

All RED tests pass; the entity→table map and the function→table resolution map are committed; zero
occurrences of `DYNAMODB_TABLE_NAME` remain in backend or infra; no frontend contract drift.

## Sequencing / Dependencies

Depends on `TableRegistry`/`CoreRepository` from D-H2 (step 3.1). Hard prerequisite for D-H4/P-01
(canonical artifact ids), D-M2 (single canonical CV key), and D-H8 (Wave-6 single-table collapse) —
each of those asserts a target shape that this spec is the authority for.

**Coverage resolved 2026-07-27.** `D-M-seams-bundle-spec.md` previously also claimed `D-M6` and
`D-Q`, which made `scope-diff.py`'s clause→spec mapping non-deterministic (it resolved to whichever
file it scanned last). The bundle has dropped both clauses and now points here; its `AC-DM6-1` was
removed, so the AC ids here starting at `AC-DM6-2` are intentional and leave the original numbering
traceable rather than silently reusing it.
