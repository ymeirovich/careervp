---
spec_id: D-H7-SCANS
title: "Eliminate request-path DynamoDB Scans"
status: draft
owner: backend
tier: T1
scope_lock_clause: D-H7
claude_code: {model: opus, effort: high}
codex: {model: gpt-5-codex, reasoning: high}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - D-H7: Request-Path Scan Elimination

## Problem Statement

Request-path DynamoDB `Scan` calls do not scale and can leak tenant boundaries. D-H7 eliminates scans from runtime handlers/repositories, retaining scans only in offline migration/admin scripts.

## Evidence

**PINNED 2026-07-29 by step 3.3-SPEC.** Every citation below was re-read live at that date. The
Wave-0 Evidence was stale in a way that pointed the wrong direction; the corrections are recorded
here rather than silently replaced, because bet `B-3-8` in `ISSUES.md` turns on exactly these numbers.

### E-1. Tier-1 `.scan(` inventory — the complete live source surface

`grep -rn "\.scan(" careervp/ scripts/` from `src/backend` returns **exactly three** hits
repository-wide. **All three are owned by a decision that already exists.** None is 3.3's own.

| # | Site | Classification | The existing decision that owns it |
|---|---|---|---|
| 1 | `careervp/dal/subscription_repository.py:415` (`scan_active_subscriptions`, paginated `FilterExpression sk=SUBSCRIPTION#CURRENT AND status=active`) | Reconcile path — **not** a request path | **Deliberately KEPT.** Wave-2 `2.1-GREEN` row: "preserve `scan_active_subscriptions` and `BillingReconcileLambda` Scan access; money path and reconcile are separate Lambdas." Its only caller is `logic/reconciliation_service.py:50`, whose module docstring (`:14`) states "NEVER call `scan_active_subscriptions` from any HTTP handler — reconcile only." |
| 2 | `careervp/dal/dynamo_dal_handler.py:800` (`_legacy_read_cover_letter_by_scan`, `ValidationException` → `scan(FilterExpression=Attr('pk').eq(pk) & Attr('sk').eq(sk), Limit=1)`) | Request path, but **legacy** | **3.5** (D-H9 legacy-path demolition) — the same legacy cover-letter family `3.1-GREEN` recorded as residue (c). **3.3 does not annex it.** |
| 3 | `scripts/cr_migration_backfill.py:261` (`_scan_legacy_cr_items`, paginated) | Offline migration script | Out of the guard's scanned scope **by directory** (see F-1 below), and deleted outright at 3.5 under scope-lock v2.7.0. |

**Consequence: `B-3-8` is settled FALSE** and its pre-decided fallback is in force — D-H7/3.3 is a
**guard-rail + regression-test step with no behavior change**. See `ISSUES.md` → `B-3-8`.

### E-2. Corrections to the Wave-0 Evidence (deltas, not silent replacements)

- **`subscription_repository.py:127-129` is stale twice over.** The Wave-0 line claimed it "still
  falls back to a money-path scan." Live: (a) the money-path scan is **gone** —
  `get_subscription_by_customer_id` is at `:102-125` and *queries* `customer-id-index`
  (`IndexName=CUSTOMER_ID_INDEX_NAME`, `KeyConditionExpression=Key('customer_id').eq(customer_id)`,
  `FilterExpression=Attr('sk').eq(SUBSCRIPTION_SK)`) with no scan; Wave-2 `2.1-GREEN` removed both
  that scan and `BillingLambda`'s `dynamodb:Scan` grant. (b) Lines `127-129` today are the
  `# ─── Public write methods ───` section divider and the `upsert_subscription` decorator — the
  citation now points at **nothing at all**. The only scan in that file is the retained reconcile
  scan at `:415`.
- **`test_l1_list_endpoints.py:222-272` is approximately right but covers something else.** Live, the
  class `TestListEndpointsQueryNotScan` spans `:221-276+` and asserts query-not-scan for the **list
  DAL methods only** (`list_cover_letters`, `list_tailored_cvs`, `list_vprs`). It says nothing about
  subscription lookup.
- **The real pre-existing duplicate is elsewhere, and Wave-0 never cited it.**
  `tests/unit/test_p14_p15_billing_idempotency.py:198-220`
  (`test_p15_billing_lookup_uses_query_not_scan`, AC-P15-1) **already** asserts exactly the
  subscription-lookup invariant: `users_table.query.assert_called_once()`,
  `IndexName == 'customer-id-index'`, partition key `customer_id`, equality on the customer id, and
  `users_table.scan.assert_not_called()`. This is why RED test 2 below is pinned as a labelled guard.

### E-3. Two IAM findings the Wave-0 spec never mentions (they are what give 3.3 content)

- **F-1 (in scope, resolved toward closure — see DP-2 in the Fix Plan).**
  `infra/careervp/api_construct.py:932-950` defines inline policy **`"artifacts_table"`** on the
  shared Lambda role (`iam.Role` at `:812`, logical-id constant `constants.SERVICE_ROLE_ARN ==
  "ServiceRoleArn"`, `role_name = naming.role_name("lambda", API_FEATURE)`), granting actions
  `PutItem, GetItem, UpdateItem, DeleteItem, Query, Scan` — the literal `"dynamodb:Scan"` is at
  **`api_construct.py:941`** — on `artifacts_table.table_arn` **and**
  `{artifacts_table.table_arn}/index/type-index`. Confirmed live from the synthesized template, not
  read off the source: the statement's `Action` list is exactly
  `['dynamodb:PutItem', 'dynamodb:GetItem', 'dynamodb:UpdateItem', 'dynamodb:DeleteItem',
  'dynamodb:Query', 'dynamodb:Scan']`. **No source path calls Scan on the artifacts table**
  (E-1 has zero artifacts-table scans), so this grant is demonstrably wider than any caller needs.
  Wave-2 `2.1-GREEN` removed the Scan action from `BillingLambda` **only**; this grant survived and
  **no test covers it**.
- **F-2 (OUT of scope — enumerated residue owned by 3.4).** CDK's `grant_read_data` /
  `grant_read_write_data` include `dynamodb:Scan` implicitly. Live count in `api_construct.py`:
  **exactly 22** occurrences (`grep -c "grant_read_data\|grant_read_write_data"` → `22`). The
  pre-flight estimated "~20"; **22 is the pinned number.** Under a full-IAM reading every runtime
  Lambda can still scan even with zero scans in source. Narrowing these 22 calls is **3.4's**, per
  DP-2's rule-10 stopping condition — 3.4 is already reshaping `api_construct.py` and two steps
  reshaping it concurrently is the Wave-2 `api_construct.py` incident replayed.

### E-4. Which synthesized template holds what (a vacuous-pass trap, pinned)

Both confirmed by building the stack live on 2026-07-29:

- The `artifacts_table` policy is on a role that P-26 Job-1 **re-homed into
  `CrudFeaturesNestedStack`**. It is found via the **`features_template`** fixture
  (`infra/tests/infrastructure/conftest.py:114`), on role logical id
  `CareerVpCrudDevCrudServiceRoleArn305AAC1B`. It is **absent from the parent
  `synthesized_template`** — an IAM assertion written against the parent template finds no matching
  policy and **passes vacuously**.
- Tables are `dynamodb.TableV2`, which synthesizes to **`AWS::DynamoDB::GlobalTable`** (11 resources
  in the parent template), **not** `AWS::DynamoDB::Table` — whose live count is **0**. A GSI
  assertion written against `AWS::DynamoDB::Table` finds no resources and **passes vacuously**.
  Precedent for the correct type: `infra/tests/infrastructure/test_p12_p13_retain_stateful.py:19-21`
  and `test_apigw_proxy_collapse.py:65` ("tables are GlobalTables — none of the legacy type").

### E-5. AC-DH7-2 is ALREADY SATISFIED — confirmed live, so its test is a guard

The one suspiciously-named index is a red herring. `infra/careervp/api_db_construct.py:384-393`
defines `status-index` on the **applications** table with `partition_key=userId` and
`sort_key=status` — user-scoped, high-cardinality, `status` only in the **sort** position. Confirmed
from the synthesized template: `KeySchema == [('userId', 'HASH'), ('status', 'RANGE')]`.

**Exactly 8 GSIs exist repository-wide** (`grep -c "index_name=" api_db_construct.py` → `8`), each
confirmed against the synthesized template:

| GSI | Table (source line) | Partition key (HASH) | Sort key (RANGE) | AC-DH7-2 shape |
|---|---|---|---|---|
| `email-index` | users (`:144`) | `email` | — | high-cardinality |
| `user_id-index` | users (`:151`) | `user_id` | `sk` | user-scoped |
| `customer-id-index` | users (`:161`) | `customer_id` | — | high-cardinality |
| `idempotency-key-index` | jobs (`:316`) | `idempotency_key` | — | high-cardinality |
| `user_id-index` | jobs (`:323`) | `user_id` | — | user-scoped |
| `status-index` | applications (`:385`) | **`userId`** | `status` | user-scoped — **the red herring** |
| `entity-index` | knowledge (`:451`) | `knowledgeType` | `entityId` | **pre-existing exception — see below** |
| `type-index` | artifacts (`:492`) | `applicationId` | `artifactType` | high-cardinality |

**`entity-index` is the one PK that is neither user-scoped nor obviously high-cardinality**
(`knowledgeType` is a type enum). It is **not 3.3's**, on three independent grounds: (a) AC-DH7-2 is
scoped to *"Given **new** indexes for replacements"* and this index is pre-existing, not introduced
as a scan replacement; (b) it has **zero live callers** — `grep -rn "entity-index\|knowledgeType"
careervp/` returns **no matches**, so no request path reads it; (c) the knowledge table's key shape
is already owned by **D-M5** ("retire `userEmail` PII partition key", 3.4) and **Q-07** ("recreate
knowledge-table on `user_id`/sub key", Wave 4). It is recorded in RED test 3's frozen baseline as a
named exception with those owners — enumerated residue, never silence.

### E-6. A fourth scan-shaped site the tier-1 regex cannot see — DELTA from the pre-flight

The pre-flight inventoried four hits (3 source + 1 IAM). Live re-check confirms all four exactly.
A wider sweep (`grep -rni "scan"` over `careervp/` + `scripts/`) surfaced **one site the `.scan(`
pattern structurally cannot match**, and it must be recorded before RED so the guard's limits are
honest:

- **`careervp/handlers/artifact_cleanup_handler.py:188`** calls
  `deps.jobs_repo.scan_by_status('CANCELLED', has_result_key=True)`.
  **`scan_by_status` does not exist.** `grep -rn "scan_by_status"` finds only this caller and its
  `.build/` copy — no definition anywhere — and `dir(JobsRepository)` is
  `['create_job', 'get_job', 'get_job_by_idempotency_key', 'get_jobs_by_user',
  'get_vpr_jobs_by_user', 'list_jobs', 'update_job', 'update_job_status']`. `deps` is typed `Any`,
  so `mypy --strict` cannot catch it, and the call is wrapped in
  `except Exception: logger.warning('Cleanup: scan failed'); return []` (`:190-192`).

**Classification: NOT a fourth Scan, and `B-3-8` stays FALSE.** Three independent reasons:
(a) **no DynamoDB Scan is ever issued** — the attribute lookup raises `AttributeError` before any
API call; (b) it is **not a request path** — `artifact_cleanup_handler` is the EventBridge-scheduled
orphan-cleanup reaper, the same category as the retained reconcile scan; (c) removing a Scan that
does not exist is not work D-H7 can do.

**It is, however, a latent bug that is NOT 3.3's to fix** (rule 5): the reaper's CANCELLED-orphan
sweep silently reaps nothing on every scheduled run. **Flagged for human review** as a new-issue
candidate; no owner is asserted here, because assigning one would be this step inventing scope.
Its consequence *for 3.3* is bounded and real: it is a **known limit** of RED test 1's guard, pinned
there by name.

### E-7. A naming red herring the guard must not false-positive on

`careervp/handlers/cover_letter_handler.py:1155-1171` documents and logs a "list-scan fallback"
(`'Canonical cover letter read missed; using list-scan fallback (Phase A)'`) and metric
`CoverLetterCanonicalReadFallback`. It calls `dal.list_cover_letters_canonical(user_id)` — a
**Query** — then filters in Python. **No Scan.** Likewise `ScanIndexForward=False` appears at
`dynamo_dal_handler.py:123,134,181,191` and `jobs_repository.py:159` — a Query keyword argument, not
a Scan. A word-level grep for "scan" false-positives on all of these; RED test 1 is pinned to AST
call matching for exactly this reason.

### E-8. Scope-lock facts carried in

- Scope-lock D-H7 (`project-scope-lock.yaml:115`) is `tier: T1`, `status: TARGET`,
  `verification: integration`. **A unit/synth suite does not discharge `integration`** — the same
  gap 3.2-GREEN recorded as undeployed debt against `CareerVpCrudDevx`. 3.3-GREEN inherits this and
  must record it rather than claim closure.
- Scope-lock D-H7 and P-15 both require Scan removal on request paths.
- The scanned source scope contains **105 files**: `careervp/handlers` (43), `careervp/dal` (17),
  `careervp/logic` (45).

## Fix Plan

1. **DONE at 3.3-SPEC (2026-07-29), not deferred to GREEN.** Inventory `scan(` call sites and
   classify each as request-path, test, or offline migration. Result: three sites, all owned
   elsewhere — Evidence E-1. Plus one scan-shaped-but-dead site (E-6) and one naming red herring
   (E-7).
2. **NO-OP — nothing for 3.3 to replace.** `B-3-8` settled **FALSE**: there is no request-path Scan
   that is 3.3's own. Site 1 is deliberately retained by Wave-2 `2.1-GREEN`; site 2 is **3.5's**
   (D-H9 demolition); site 3 is an offline script outside the guard's scanned scope. **3.3 removes no
   Scan and changes no read path.** Do not go hunting for a scan to justify the step, and do not
   annex `dynamo_dal_handler.py:800` from 3.5 — either is a rule-5 stop.
3. **This plus item 4 IS the step.** Add the static guard rejecting `.scan(` in
   `careervp/{handlers,dal,logic}`, as a **frozen-baseline ratchet** over the two enumerated
   allow-listed sites (RED test 1). Offline scripts need **no allow-list entry**: `scripts/` is
   excluded **by directory**, not by exception.
4. Ensure no low-cardinality `STATUS#{status}` GSI partition key is introduced. **Already satisfied**
   (Evidence E-5) — shipped as a frozen 8-GSI regression guard (RED test 3).

### DP-1 — RESOLVED: **Option A (no touch)**

3.3 touches **neither `CoreRepository` nor `TableRegistry`**.

- **Evidence:** DP-1 follows directly from `B-3-8` settling FALSE (E-1). There is no replacement
  query to build, so there is no keyed-query helper to add (Option B) and no existing 3.2-era helper
  to consume (Option C). Independently: the only two live scans sit on the **users** table
  (`subscription_repository`, `USER#{id}` / `SUBSCRIPTION#CURRENT`) and the **legacy cover-letter**
  path — neither is `TableRegistry`'s artifacts/core surface, and `B-3-5` parks user/application
  keying for Wave-6 D-H8. §3.3's own note is explicit: "A scan found there is Option A regardless."
- **Consequence for later steps, stated so nothing has to ask:** 3.3 does **not** take the §2
  `CoreRepository`/`TableRegistry` serialization lock. **3.3 runs fully parallel to 3.4 and 3.5** with
  respect to the repository modules. 3.4 and 3.5 may be scheduled without waiting on 3.3.
- **Rule-10 stopping condition: not triggered.** All three known sites — and the fourth candidate in
  E-6 — were classified as *kept*, *another step's*, or *not-a-Scan* using decisions that already
  exist (Wave-2 `2.1-GREEN`; `3.1-GREEN` residue (c); this spec's own Fix Plan item 3). No site was
  resolved by assigning it to 3.3.

### DP-2 — RESOLVED: **Option "Source + the one explicit grant"**

AC-DH7-1 is read as **source *and* the single explicit `dynamodb:Scan` grant** — not source-only, and
not full IAM closure.

- **What 3.3 does:** the static source guard over `careervp/{handlers,dal,logic}` (RED test 1),
  **plus** removing the literal `"dynamodb:Scan"` at **`infra/careervp/api_construct.py:941`** from
  the `"artifacts_table"` inline policy, proven by a synth assertion.
- **Evidence for taking it (E-3 F-1):** one line of `infra/`; it closes the one grant that is
  **demonstrably** wider than any caller needs (zero artifacts-table scans exist in source, per E-1);
  no test covers it today; and it is provable by a synth assertion rather than argument.
- **Why not full IAM closure (E-3 F-2):** that means narrowing **22** implicit
  `grant_read_data`/`grant_read_write_data` calls in the file 3.4 is already reshaping. §3.3's
  **rule-10 stopping condition fires only for that option, and it is NOT taken** — so no STOP is
  required here. Those 22 calls are **enumerated residue owned by 3.4**, with the count pinned at 22
  (the pre-flight's "~20" was an estimate).
- **Consequence for later steps:** **3.3 now holds the `infra/` lock for this one edit.**
  `api_construct.py` may not be edited by 3.4 concurrently with 3.3-GREEN. **`B-3-4` applies:** the
  edit is proven with the isolated-template-diff technique (HEAD vs change-stashed, no live stack —
  the Wave-2 2.3 root-cause method), asserting **zero replacement markers on stateful resources**. An
  IAM inline-policy action removal is not a stateful change, so the expected diff is the single
  `Action` element and nothing else — which is exactly what the isolated diff must show.
- **Both IMMUTABLE laws are untouched:** no `RestApi` move, no Cognito user-pool move. The role's
  logical id is unchanged; only one action string leaves one inline policy.

## RED Tests to Write First

**Exactly three tests — the same three the Wave-0 spec named, with the same names. No test is added,
removed, or renamed.** Because `B-3-8` is FALSE, **every day-one-green assertion is LABELLED A GUARD**
in its own docstring, with the reason (`B-3-6`'s handling). A guard is not a failure of this step — an
*unlabelled* guard is. No test may be deleted, renumbered, or bent into failing to make 3.3 look
substantial.

**Note on where DP-2's IAM assertion lives.** DP-2 resolved AC-DH7-1 to mean source **and** the one
explicit grant. Both halves therefore belong to **AC-DH7-1**, and the IAM assertion is pinned as
**Part B of test 1** rather than as a new test — a fourth RED test is out of bounds for this step.

---

### 1. `test_dh7_no_scan_in_runtime_handlers_or_dal` — covers **AC-DH7-1** (both halves, per DP-2)

Two parts, one test. **Part A is a day-one guard; Part B is the single assertion in all of 3.3 that
is red before the fix and green after.**

#### Part A — the static source guard

**LABEL: frozen-baseline ratchet guard. Passes on day one by construction.**

**Scanned scope — exactly these three directories, recursively, `*.py` only** (105 files live):
`src/backend/careervp/handlers`, `src/backend/careervp/dal`, `src/backend/careervp/logic`.
**Not scanned, and each exclusion is by decision, not convenience:**
`careervp/models`, `careervp/validation`, `careervp/payment_providers`, `careervp/infrastructure`
(no DynamoDB call sites; outside the AC's "handlers/repositories" wording); `src/backend/scripts`
(offline — Fix Plan item 3 allow-lists offline scripts, and excluding the whole directory is what
that means in practice); `src/backend/tests` (test doubles legitimately call `.scan()`, e.g.
`test_p14_p15_billing_idempotency.py:191`); `.build/` (generated Lambda bundles — a stale copy of
every source file, which would double every count).

**Assertion form — a frozen-baseline RATCHET, not absolute zero.** The test asserts
`found_sites ⊆ BASELINE` (may shrink, never grow), and additionally that every element of `BASELINE`
is still resolvable to a real file so the baseline cannot rot into a no-op.

**Why a ratchet and not `assert len(found) == 0` — this is the load-bearing choice.** An absolute
zero-occurrences assertion over `dal/` is **unsatisfiable by anything 3.3 is scoped to do**: it would
require either removing `subscription_repository.py:415`, which Wave-2 `2.1-GREEN` **deliberately
retained** for `BillingReconcileLambda`, or removing `dynamo_dal_handler.py:800`, which is **3.5's**
work. The only ways to make an absolute assertion pass are annexing 3.5's site or dropping `dal/`
from scope and leaving a hole — a rule-5 stop and a false green respectively. `B-3-5`'s pattern from
3.1 is therefore reused verbatim: enumerate every allow-listed site with the decision that
allow-lists it, allow shrink, forbid growth. **Shrink must not fail:** when 3.5 deletes
`dynamo_dal_handler.py:800`, this test must still pass without being edited.

**The allow-list — ENUMERATED SITE BY SITE with its owning decision. Exactly two entries.**
(A directory wildcard is explicitly forbidden here: a wildcard over `dal/` would silently absorb any
future scan added to any of its 17 files.)

| Allow-listed site | Owning decision (verbatim source of authority) |
|---|---|
| `careervp/dal/subscription_repository.py` :: `scan_active_subscriptions` (line 415 at pinning time) | Wave-2 `2.1-GREEN` ledger row — "preserve `scan_active_subscriptions` and `BillingReconcileLambda` Scan access; money path and reconcile are separate Lambdas." Reconcile-only; enforced by the `reconciliation_service.py:14` docstring prohibition. |
| `careervp/dal/dynamo_dal_handler.py` :: `_legacy_read_cover_letter_by_scan` (line 800 at pinning time) | **3.5** (D-H9 legacy-path demolition) — the legacy cover-letter family recorded as `3.1-GREEN` residue (c). Allow-listed **only until 3.5 deletes it**; not 3.3's to remove. |

**Baseline entries are keyed by `(relative_path, enclosing_function_name)`, never by line number** —
otherwise any unrelated edit above line 415 breaks the build and the next session "fixes" the test.

**How the scan is performed: AST, not regex.** Parse each file with `ast.parse` and walk it. Flag a
site when **any** of the following holds:

1. `ast.Call` whose `func` is an `ast.Attribute` with `attr == 'scan'` — any receiver
   (`table.scan(...)`, `self._table.scan(...)`, `dynamodb.Table(n).scan(...)`).
2. `ast.Attribute` with `attr == 'scan'` appearing **outside** a `Call` position — catches
   `fn = table.scan` followed by a later `fn(...)`, which form 1 alone misses.
3. `ast.Call` to `getattr` whose second argument is the string constant `'scan'` — catches
   `getattr(table, 'scan')(...)`.
4. `ast.Call` whose `func` is an `ast.Attribute` with `attr == 'get_paginator'` and whose first
   argument is the string constant `'scan'` — the boto3 low-level paginator route.

**Enclosing function name** is resolved by tracking the nearest enclosing
`FunctionDef`/`AsyncFunctionDef` during the walk, so baseline keys are stable.

**Why AST and not a `".scan("` regex — the false-negative and false-positive cases, both live.**
A regex misses forms 2–4 entirely. It also **false-positives** on live code: `ScanIndexForward=False`
at `dynamo_dal_handler.py:123,134,181,191` and `jobs_repository.py:159` (a Query kwarg), and the
`'…using list-scan fallback (Phase A)'` log string plus its docstring at
`cover_letter_handler.py:1155-1171`, which is a **Query** followed by in-Python filtering (Evidence
E-7). AST matches call structure, so comments, docstrings, log strings, and keyword arguments cannot
match — a property the test asserts positively by requiring
`cover_letter_handler.py` and `jobs_repository.py` to contribute **zero** sites.

**KNOWN LIMITS — stated, not papered over.** Each is a deliberate accepted gap, recorded so a future
reader does not mistake this guard for a proof:

- **Dynamic dispatch with a computed name** (`getattr(table, method_name)` where `method_name` is a
  variable, or `eval`/`exec`) is undetectable by static analysis. **Live-verified zero at pinning:**
  `grep -rn "getattr(.*scan\|['\"]scan['\"]" careervp/` returns **no matches**, and the only
  `get_paginator` calls in the repo are `scripts/verify_oidc_cdk_diff.py:45` (`list_roles`) and
  `scripts/dlq_delivery_drill.py:117` (`list_rules`) — both outside the scanned scope and neither a
  scan.
- **Differently-named wrappers are out of reach by design.** `artifact_cleanup_handler.py:188` calls
  `deps.jobs_repo.scan_by_status(...)`; `attr == 'scan_by_status' != 'scan'`, so this guard does
  **not** flag it — correctly, since **no Scan is issued at all** (the method does not exist;
  Evidence E-6). Matching on the `scan_*` prefix instead was **rejected**: it would fail on day one
  against a site that issues no Scan, is on a scheduled reaper rather than a request path, and whose
  underlying bug is not 3.3's to fix. If a future session implements `scan_by_status` on
  `JobsRepository` using `table.scan(...)`, that lands in `dal/` and **this guard catches it there**.
- **Cross-module aliasing** (`from x import scan as s`) is not modelled; there are no such imports
  live.
- The guard proves nothing about **runtime** behaviour — that is AC-DH7-1's IAM half below and the
  clause's `verification: integration`, which a unit suite does not discharge (Evidence E-8).

**Failure message must name `AC-DH7-1`**, the offending `path::function`, and the sentence "add it to
the D-H7 baseline only with a dated decision that owns it" — so a future failure is actionable rather
than merely red.

#### Part B — the one explicit IAM grant (DP-2)

**LABEL: NOT a guard. This is the one assertion in 3.3 that is RED before the fix and GREEN after —
the single behaviour-adjacent change in the step.** `dynamodb:Scan` is present at pinning time
(Evidence E-3 F-1) and 3.3-GREEN removes it. It sits under AC-DH7-1 because DP-2 resolved that AC to
mean source **and** this one grant.

**Exactly which policy statement:** inline policy **`PolicyName == "artifacts_table"`** on the shared
Lambda role, source `infra/careervp/api_construct.py:932-950`, literal to remove at **`:941`**.

**The exact synth assertion:**

- Use the **`features_template`** fixture (`infra/tests/infrastructure/conftest.py:114`), **not**
  `synthesized_template` — the role was re-homed into `CrudFeaturesNestedStack` by P-26 Job 1 and is
  **absent from the parent template**, where this assertion would pass vacuously (Evidence E-4).
- `features_template.find_resources("AWS::IAM::Role")`; for each role, iterate
  `props["Properties"].get("Policies", [])` and select entries with
  `policy["PolicyName"] == "artifacts_table"`.
- **Assert the policy was found first** — `assert matched, 'AC-DH7-1: artifacts_table inline policy
  not found; assertion would pass vacuously'`. Without this the test is a no-op the moment the policy
  is renamed.
- For each matched statement in `policy["PolicyDocument"]["Statement"]`:
  - `assert "dynamodb:Scan" not in stmt["Action"]`
  - and pin the **whole surviving list exactly**:
    `stmt["Action"] == ['dynamodb:PutItem', 'dynamodb:GetItem', 'dynamodb:UpdateItem',
    'dynamodb:DeleteItem', 'dynamodb:Query']` — order included, so neither a re-added Scan nor a
    silently-widened action list passes.
- **Match the role by policy name, not by logical id.** The live logical id is
  `CareerVpCrudDevCrudServiceRoleArn305AAC1B`, but the `CareerVpCrudDev` prefix is environment-derived
  and the `305AAC1B` suffix is a CDK hash; hard-coding it makes the test fail under the `devx` target
  for the wrong reason.
- **Resources are asserted unchanged**, so the fix narrows actions without quietly narrowing scope:
  the statement still covers `artifacts_table.table_arn` **and** `.../index/type-index`.
- **`B-3-4` proof accompanies this edit** (DP-2): isolated template diff, HEAD vs change-stashed, zero
  replacement markers on stateful resources; the only expected difference is the removal of the single
  `Action` element.

> **⛔ SCOPE THE ASSERTION TO THE INLINE STATEMENT ONLY. Do NOT union it with the role's attached
> default policy — that assertion is UNSATISFIABLE by 3.3 and would deadlock GREEN.**
>
> The obvious thing to copy is the repo's existing "no Scan grant" test,
> `src/backend/tests/infrastructure/test_p15_billing_iam.py` (AC-P15-1, Wave-2 2.1). Its
> `_role_policy_actions` helper deliberately **unions** a role's inline `Policies` with every
> standalone `AWS::IAM::Policy` whose `Roles` list references that role — and for the shared role
> here, that union includes `dynamodb:Scan` from a **second, independent source**. Verified live on
> 2026-07-29 against the synthesized template:
>
> ```
> shared role     : CareerVpCrudDevCrudServiceRoleArn305AAC1B
> attached policy : ServiceRoleArnDefaultPolicy2B096FD3   | Scan present: True
> INLINE has Scan : True     ATTACHED(default policy) has Scan : True     UNION has Scan : True
> ```
>
> The attached `...DefaultPolicy...` Scan comes from the **22 implicit `grant_read_data` /
> `grant_read_write_data` calls** (Evidence E-3 F-2), which are **3.4's**. A union-style assertion
> therefore stays red after 3.3 removes `api_construct.py:941`, and 3.3-GREEN may not edit the test —
> so the step would dead-end in a §0.3 amendment. Per DP-2 that outcome is explicitly out of scope:
> the P-15 precedent is the right *pattern* for finding a role across parent and nested templates, and
> the wrong *breadth* for this assertion.
>
> **Pin, therefore:** select the role by the presence of inline `PolicyName == "artifacts_table"`, and
> assert **only** on that statement's `Action` list. Assert **nothing** about
> `ServiceRoleArnDefaultPolicy2B096FD3` or any other attached policy. A companion assertion is
> permitted and encouraged: that `dynamodb:Scan` **is still present** in the attached default policy,
> labelled as **3.4's residue**, so the 22-grant surface is proven-and-owned rather than silently
> assumed — and so a future reader cannot mistake this test for full IAM closure.

**Out of scope, enumerated as residue owned by 3.4:** the **22** implicit
`grant_read_data`/`grant_read_write_data` calls in `api_construct.py` (Evidence E-3 F-2). Part B
asserts **nothing** about them — an assertion here would fail on day one against work 3.3 is
explicitly forbidden to do.

---

### 2. `test_dh7_subscription_lookup_uses_query` — covers **AC-DH7-1**

**LABEL: regression guard, DUPLICATE BY DESIGN. Passes on day one.**

**Be honest about what it adds, because the coverage already exists.**
`tests/unit/test_p14_p15_billing_idempotency.py:198-220`
(`test_p15_billing_lookup_uses_query_not_scan`) already asserts every substantive fact about this
path under **AC-P15-1** (Evidence E-2). What this test adds is **not new coverage** — it is
**AC ownership**: AC-DH7-1 must be independently verifiable from D-H7's own test module, so that
re-scoping or relocating the P-15 billing test cannot silently remove D-H7's evidence. The docstring
must say exactly that, so no future reader deletes it as a redundant copy or mistakes it for a fix.

**Pinned assertions** (mirroring the P-15 test's stimulus so the two cannot drift apart):

- Construct `SubscriptionRepository(table_name=<users table>,
  idempotency_table_name=<idempotency table>, dynamodb_resource=<MagicMock>)` with
  `dynamodb.Table.side_effect` routing the idempotency name to a separate mock, and
  `users_table.query.return_value = {'Items': []}`.
- Call **`get_subscription_by_customer_id('cus_dh7_001')`** — exactly one call, and **only** this
  method.
- `users_table.query.assert_called_once()`
- `query.kwargs['IndexName'] == 'customer-id-index'`
- `KeyConditionExpression` resolves to partition key name `customer_id` with the equality value
  `'cus_dh7_001'`
- **`users_table.scan.assert_not_called()`** — scoped to this single lookup call.

**MUST NOT assert anything about `scan_active_subscriptions`** — neither its behaviour nor its
existence nor its call count. That scan is **deliberately retained** by Wave-2 `2.1-GREEN` for
`BillingReconcileLambda`; an over-broad assertion here (e.g. "the repository never scans", or a
repository-level `scan.assert_not_called()`) would break the reconcile path Wave 2 explicitly chose
to keep. The retention fact lives in Evidence E-1 and in RED test 1's allow-list, which is the
correct home for it. The `assert_not_called()` above is bounded to the single
`get_subscription_by_customer_id` invocation for exactly this reason.

---

### 3. `test_dh7_no_status_only_gsi_partition_key` — covers **AC-DH7-2**

**LABEL: frozen-enumeration regression guard. ALREADY SATISFIED — passes on day one** (Evidence E-5).
`status-index` is a red herring: its partition key is `userId` and `status` sits in the **sort**
position. Nothing is fixed here; the point is that a future GSI cannot slip past.

**Resource type — the vacuous-pass trap, pinned:** enumerate
`synthesized_template.find_resources("AWS::DynamoDB::GlobalTable")`. Tables are `dynamodb.TableV2`,
so `AWS::DynamoDB::Table` has a live count of **0** and an assertion against it passes vacuously
(Evidence E-4). **Assert the resource set is non-empty** (`== 11` GlobalTables live) before asserting
anything about its contents.

**Two assertions, in this order:**

**(a) The AC-DH7-2 / Fix-Plan-item-4 prohibition — the behavioural rule, applied to every GSI.**
For every GSI on every table, the `HASH` key's `AttributeName`, lower-cased, is **not** `status` and
does not start with `status#`. This is the exact thing the clause forbids ("no low-cardinality
`STATUS#{status}` GSI partition key is introduced") and it holds for all 8 GSIs live.

**(b) A frozen enumeration by exact index name and key schema, so a NEW GSI fails rather than
slipping past.** Assert the set of `(IndexName, tuple(KeySchema))` across all GlobalTables equals
exactly this 8-entry baseline — **set equality, not containment**, so an added GSI fails and a
removed GSI also fails (a removal is a deliberate schema decision that must be re-recorded, not
absorbed):

| # | `IndexName` | `KeySchema` (exact, as synthesized) |
|---|---|---|
| 1 | `email-index` | `[('email', 'HASH')]` |
| 2 | `user_id-index` | `[('user_id', 'HASH'), ('sk', 'RANGE')]` |
| 3 | `customer-id-index` | `[('customer_id', 'HASH')]` |
| 4 | `idempotency-key-index` | `[('idempotency_key', 'HASH')]` |
| 5 | `user_id-index` | `[('user_id', 'HASH')]` |
| 6 | `status-index` | `[('userId', 'HASH'), ('status', 'RANGE')]` |
| 7 | `entity-index` | `[('knowledgeType', 'HASH'), ('entityId', 'RANGE')]` |
| 8 | `type-index` | `[('applicationId', 'HASH'), ('artifactType', 'RANGE')]` |

Entries 2 and 5 share the name `user_id-index` on **different tables** (users and jobs) with
**different key schemas**, so the baseline must be a set of `(name, keyschema)` pairs — a
name-keyed dict would silently collapse them and lose one.

**`entity-index` is a NAMED, OWNED EXCEPTION to assertion (a)'s spirit, and it is enumerated, not
hidden.** Its partition key `knowledgeType` is neither user-scoped nor obviously high-cardinality.
It is **not 3.3's** and assertion (a) does not fail on it, because (a) is pinned to the
`status`-partition prohibition the clause actually states. Grounds, per Evidence E-5: AC-DH7-2 is
scoped to *"new indexes for replacements"* and this one is pre-existing; it has **zero live callers**
in `careervp/`; and the knowledge table's key shape is already owned by **D-M5** (3.4) and **Q-07**
(Wave 4). The test's docstring must name it, name those owners, and state that a broader
"every PK is user-scoped or high-cardinality" assertion was **deliberately rejected** here — it would
fail on day one and drag the knowledge-table reshape into 3.3, which is scope drift, not rigour.

**Failure message must name `AC-DH7-2`** and, for a baseline mismatch, print the added/removed
`(IndexName, KeySchema)` pairs plus "a new GSI needs a recorded partition-key shape decision before
this baseline is updated."

## Acceptance Criteria

**AC-DH7-1** - Given runtime request paths, when handlers/repositories execute, then DynamoDB Scan is never called.

**AC-DH7-2** - Given new indexes for replacements, when synthesized, then GSI partition keys are user-scoped, high-cardinality, or sparse.

## Done-when

All RED tests pass; P-15 money-path scan test also passes; no frontend contract drift.

## Sequencing / Dependencies

Depends on D-H2 for repository routing. Can share implementation with P-15 where billing paths overlap.

