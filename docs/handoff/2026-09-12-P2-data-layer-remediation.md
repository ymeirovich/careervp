# P2 — Data layer remediation design

**Model: Opus 5, xhigh effort. Run AFTER P1 returns its verdicts.**
**Prerequisite: read `docs/handoff/2026-09-12-P0-COMMON.md` first — it is binding.**

This session produces a **design and an ordered plan**, not a rewrite. Do not
start editing handlers.

**Validation obligation (P0 §1):** the framing below — that four root causes are
one problem — came from unvalidated automated analysis. Verify the load-bearing
claims yourself before designing around them, starting with
`api_db_construct.py:114`. If P1 refuted the framing, follow P1, not this file,
and say so.

---

You are designing the remediation for the data-access layer of a pre-launch
serverless app (AWS Lambda + DynamoDB + CDK Python). There is **no production
environment and no real customer data** — every stored row is disposable. That
freedom is the single most important input to your design: you may choose
correctness over compatibility everywhere, and you should.

## Read first

- `docs/handoff/2026-09-12-RECON-FINDINGS.md` — the defect inventory
- `docs/handoff/2026-09-12-P1-VERDICTS.md` if present — P1's validation results.
  **Anything P1 marked REFUTED is out of scope. Do not design around a
  non-existent bug.**
- `docs/HARNESS.md` — the five proof commands this project measures itself with
- `src/backend/careervp/dal/table_registry.py` — the partial attempt at a key
  authority that already exists

## The problem, stated at the root

Four of the six root causes in the inventory are one problem wearing four masks:

**R1** — `infra/careervp/api_db_construct.py:114` does `self.db = self.users_table`,
so the generic `DYNAMODB_TABLE_NAME` env var resolves to the **users** table on
every Lambda that inherits it, while handlers read it as jobs, artifacts, or VPR.

**R2** — Two key schemes coexist: canonical `applicationId/artifactId` and legacy
`pk/sk`. `table_registry.py` maintains *both* (`legacy_key_condition` /
`canonical_key_condition`, `legacy_item_key` / `canonical_item_key`), and callers
pick either. Some writes splat both schemes into one item; some readers can
therefore never match.

**R4** — `Limit=N` + `FilterExpression` misused in 8 places. DynamoDB applies
`Limit` before the filter, so these read N arbitrary items, filter them out, and
return empty. Masked today only because the tables are nearly empty.

**Plus** — 9 DAL modules (`application_repository`, `cv_dal`, `jobs_repository`,
`idempotency_repository`, `cv_tailoring_dal`, `user_repository`,
`knowledge_repository`, `identity_map_repository`, `subscription_repository`)
each instantiate their own `boto3.resource`, independent of `table_registry` and
of each other.

Symptom, to make the stakes concrete: the same tailored CV is written to the
**cvs** table by the worker Lambda, to the **users** table by the API Lambda, and
read back from a third location by `export_handler` — because all three resolve
"the artifacts table" through a different chain.

## What to produce

Per `P0-COMMON.md` §4, your report **must end with the traceability table** and
the ADDITIONS / REDUCTIONS / UNKNOWNS lists. For this session the `Backend` and
`Infra` columns carry the payload, and REDUCTIONS should be long — see §3.

### 1. The target design

One table authority. Specify it concretely enough to implement:

- Which physical table holds which logical entity, and the single mechanism by
  which any Lambda resolves it. State explicitly what replaces the generic
  `DYNAMODB_TABLE_NAME` and how a handler becomes *unable* to resolve the wrong
  table — a naming convention is not enough; make the wrong thing fail loudly at
  import or cold start.
- One key scheme per table. Pick canonical or legacy per table and say why. The
  legacy scheme must end up with **zero** live callers, not fewer callers.
- Where `table_registry.py` fits: extend it, replace it, or absorb it into
  `core_repository`. Justify against what's already there.
- What happens to the 9 independent `boto3.resource` sites. Note
  `dal/dynamo_dal_handler.py:83-87` builds a fresh `boto3.session.Session()` on
  *every* call — client lifecycle is part of this design, not a separate
  cleanup.

### 2. The ordered plan

A sequence of changes, each of which:
- is independently committable and independently revertible,
- names the RED test that must fail before it and pass after,
- names which inventory findings it closes (by S-number),
- states what `make journey` should report before and after. If a step
  shouldn't move the journey number, say so — a step that changes the number
  unexpectedly is a signal, not a success.

Order by **risk reduction per step**, not by module. The first step should be the
one that makes the next five safe.

### 3. The demolition list

Every symbol, env var, table, and code path that must be **deleted**, not
deprecated, once the migration lands. Include at minimum (verify each first —
some may have been refuted by P1): `legacy_key_condition`, `legacy_item_key`,
`legacy_query_candidates`, `COVER_LETTER_LEGACY_READ_ENABLED`,
`legacy_read_cover_letter`, the `'cv-tailoring'` and `'vpr_table'` literals,
`cv_dal.py:76-79`'s bare `cv_id` key, and the hardcoded cross-environment table
list at `cover_letter_handler.py:199-227`.

Pre-launch with disposable data, deletion is cheap and dual-path maintenance is
what produced this. Bias hard toward deletion.

### 4. The regression net

These bugs were invisible because the tests didn't model them. Specify the tests
that make this class *structurally* impossible to reintroduce. Consider at least:

- A test asserting every table env var injected by CDK resolves to the physical
  table the consuming handler expects — i.e. the R1 bug cannot recur silently.
- A test asserting no live code path calls a `legacy_*` helper.
- A test asserting `Limit` is never combined with `FilterExpression` (this is a
  greppable invariant; make it an enforced one).
- Round-trip tests per entity: **write via the real write path, read via the real
  read path, assert equality.** Most of these bugs would have died instantly to
  such a test. There is currently no such test for any entity.

State for each whether it's a unit test, an infra/CDK synth assertion, or a lint
rule — the cheapest mechanism that actually catches it.

### 5. The knowledge table — schema decision only

The `knowledge` table (`infra/careervp/api_db_construct.py:428-465`, pk
`userEmail` / sk `knowledgeType`) is **dead**: zero live readers, zero live
writers (verify this). A separate session (P5) designs the cumulative-memory
feature that will eventually use it.

Your scope here is narrow and only this: the table is part of the data layer you
are rationalizing, so (a) confirm it is dead, (b) note that `userEmail` as a
partition key is inconsistent with every other table's `userId` (Cognito `sub`)
and puts PII in a key, and (c) state whether your table-authority design should
cover it now or leave it out until P5 lands. **Do not design the feature.** Flag
the schema conflict and move on.

### 6. Stack decision — record your read

The human asked whether to continue on the existing CloudFormation stack or start
fresh. Current state: `CareerVpCrudDevx` is `UPDATE_COMPLETE`, 553 resources
across 6 templates, all tables CFN-owned with PITR enabled and
`DeployedGitSha` wired (`service_stack.py:177-182`). The older `CareerVpCrudDev`
still exists and is slated for retirement. No `prod` exists — go-live is a first
deploy onto a fresh stack regardless.

State your position with reasons: does any part of your remediation *require* a
new stack, or is it entirely application-layer? Note specifically whether any
table needs a key-schema change — a DynamoDB partition/sort key cannot be altered
in place, so that would mean new tables (cheap here: the data is disposable) and
it is the one thing that could change the answer.

## Constraints

- **Design only. Produce no source edits in this session.** The human explicitly
  wants the plan reviewable before code moves.
- Every claim about current behavior must cite file:line, and you must have
  opened the file. Do not inherit a citation from the inventory without checking
  it.
- Label OBSERVATION / INFERENCE / OPINION.
- Where you face a judgment call (e.g. canonical vs legacy for a given table),
  present the options with costs and let the human choose. Do not decide silently.
- If you conclude the inventory's framing is wrong — that these are not four
  masks of one problem — say so and argue it. That would be a valuable result,
  not a failure.
