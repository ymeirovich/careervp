# Wave 0 — Remaining Prompts (copy-paste runbook)

- **Generated:** 2026-07-12, against `redesign-execution-plan.md` v2.0.0.
- **Purpose:** Wave 0 has 20 rows (0.0 → 0.75). A fresh validation pass (code + git evidence, not
  the table's own Status column, which is known to lag) found the table **wrong for four rows**
  and found **two rows with a spec but zero implementation** that the table's `verified`-adjacent
  neighbors made easy to miss. This file contains: (1) one prep prompt to fix the drift itself, then
  (2) one prompt per genuinely unfinished step, in dependency order. Steps already verified by real
  evidence are listed for completeness but have no prompt — there is nothing left to run.

## Validation summary (source of truth for this file)

> **Re-validated 2026-07-16.** Two rows below were wrong in the 2026-07-12 pass — corrected inline.

| Step | Real status | Note |
|---|---|---|
| 0.0, 0.1, 0.1.5, 0.2, 0.35, 0.4, 0.5, 0.55 | done | table accurate |
| 0.61, 0.62, 0.63, 0.75 | done | commits `926a061`, `e3839c4`/`e3d3051`; `redesign-execution-plan.md`'s Status column already reads `implemented` for these — no board drift remains |
| 0.1.6 (P-03), 0.3 (F-01/F-06) | **0.3 (F-01/F-06) DONE, not a gap.** | 2026-07-15 verification: `npx jest -t oracle` = 21/21 passing (all 10 F-06 §3 items + F-01 legs incl. `vpr_id` null-vs-absent and 409-on-stale-`base_version`). 0.1.6 (P-03) still genuinely spec_written only — see Prompt 1. |
| 0.56 (P-32 budgets slice) | not_started | no code, no evidence artifact |
| 0.6 (P-12/P-13 RETAIN) | **CODE LANDED (commit `567320d`), tests missing.** | `api_db_construct.py` already applies `self.removal_policy` (RETAIN unless scratch) + `self.deletion_protection` + PITR at ~11 stateful sites — the "DESTROY everywhere / zero deletion_protection" premise below (Prompt 4, original) was wrong. Remaining gap: no test asserts it, so scope-diff shows P-12/P-13 as spec_written [NO TEST]; and deploy #1 (`ExecuteChangeSet`) status on dev is unconfirmed. See corrected Prompt 4. |
| 0.64 (fire drill) | verified | `redesign-execution-plan.md` records commit `28411d4`, from-scratch recreate = 328s |
| 0.64b (domain slice) | in_progress | CDK/DNS/cert done; Deploy Frontend workflow fix never proven green in actual CI |
| 0.65 (P-26 decomposition) | not_started | Job-1 amendment (resource-import/`cdk refactor` mechanism) **ACCEPTED 2026-07-15** — the §0.3 STOP is lifted, but the migration itself has not been authored or run. Original Prompt 7 described the pre-amendment mechanism (create-in-nested/delete-from-parent) and is superseded — see corrected Prompt 7. |
| 0.7 (P-24 identity surrogate) | **IMPLEMENTED (commit `09bd6f3`), DORMANT by design — not `not_started`.** | Resolver + map-table landed under TDD (13 tests). The custom Lambda authorizer that would activate it (`_add_api_authorizer_lambda`) has no call site — live authorizer is Cognito. Landed ahead of its own dep (0.65) per the plan's numeric-dep rule; this is safe (inert code) but means 0.65's resource-import must now also re-home this authorizer construct. See corrected Prompt 8 (verify-only, not IMPLEMENT). |

**Critical path to Wave 1:** `{0.6 (deploy-confirm), 0.64b}` → `0.65` → `0.7 verify` → Wave 1 step 1.0.
0.64 is verified. 0.7's code already exists dormant, so the critical path is "confirm 0.6 is deployed" +
"finish 0.65" + "re-verify 0.7," not "build 0.7 from scratch."

**Touches-serialization note:** 0.6 and 0.65/0.7 all touch `app.py` and CDK constructs — do not run
their prompts concurrently. 0.1.6, 0.3, and 0.56 touch no shared CDK file and are safe to run in
parallel with each other and with the serialized chain.

---

## Prompt 0 — Status-board + tooling-gap sync (run first, SETUP)

**Model/effort:** Claude Code `sonnet / medium` · Codex `gpt-5-codex / medium` — mechanical.

```
Fix two pieces of drift in the db-redesign execution plan, no application code changes:

1. In docs/db-redesign/code/code-analysis/project/redesign-execution-plan.md, update the Status
   column for rows 0.61 (P-29), 0.62 (P-30), 0.63 (P-21), and 0.75 (Q-10) from `not_started` to
   `implemented`. Evidence: 0.61/0.62/0.63 landed in commit 926a061 (evidence_pack.py,
   smoke_harness.py, monitoring.py SNS EmailSubscription wiring, all with passing RED-origin
   tests). 0.75 landed in commits e3839c4/e3d3051 (llm_metering.py, PRICE_PER_APP, CostPerApplication
   alarm in monitoring.py, mypy-strict/ruff-clean). Add one line to each row's status-notes block
   (near line 147-153) recording the commit hash as evidence, matching the existing style of the
   0.5/0.55 status notes.

2. scope-diff.py (docs/db-redesign/code/code-analysis/project/scope-diff.py) under-reports Q-10 as
   `spec_written [NO TEST]` because the tests added for it in src/backend/tests/unit/test_llm_client.py
   lack the `scope_lock_clause: Q-10` marker comment the tool's regex scans for. Add that marker
   comment to the relevant Q-10 test(s) so `python3 scope-diff.py` reports Q-10 as test_written/
   implemented correctly. Do not change test logic.

Do NOT touch project-scope-lock.yaml or project-scope-lock.md — this is a status-board and tooling
fix only, not a contract amendment.

VERIFY: `python3 docs/db-redesign/code/code-analysis/project/scope-diff.py` now shows Q-10 with a
test reference; `git diff --stat` touches only the execution-plan.md and the one test file's marker
comment.

OUTPUT REQUIRED:
1. A git commit message.
2. Since this step has no scope-lock or coverage surface, skip those check-ins and go straight to
   confirming: "Ready — proceed to Prompt 1 (0.1.6 P-03) and Prompt 2 (0.3 F-01/F-06), which can run
   in parallel with each other and with Prompt 4 (0.6)."
```

---

## Prompt 1 — Step 0.1.6 (P-03: `/api/*` surface map + assertion) — IMPLEMENT

**Model/effort:** Claude Code `sonnet / medium` · Codex `gpt-5-codex / medium`.
**Deps:** 0.1 (done). **Touches:** none — safe to run in parallel with everything else in this wave.

```
Implement clause P-03 per docs/db-redesign/code/code-analysis/project/specs/P-03-api-surface-spec.md
in the real careervp repo (src/backend, infra). The spec is SPEC ONLY today — write the RED test(s)
it describes first (watch them fail), then the minimal GREEN code:
- Enumerate the /api/* surface from the CDK route_map + the staging export.
- Grep src/frontend for any /api/* reference — assert zero.
- Assert /api/* is absent from both dev and prod `cdk synth` output.

Note: a pre-existing test (src/backend/tests/unit/test_l6_route_surface.py:169-172, predates
db-redesign) already asserts a `/api/` prefix absence incidentally. Do not just point scope-diff.py
at that test — it isn't P-03-tagged and wasn't written against this spec's AC-### criteria. Either
extend it with the missing assertions + a `scope_lock_clause: P-03` marker, or write a new test file;
whichever leaves the AC-### criteria in the spec fully covered.

VERIFY:
cd src/backend && uv run pytest tests/unit -k p03 -v
cd src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict
cd infra && uv sync && cdk synth   # confirm no /api/* paths in synth output

SCOPE-LOCK CHECK-IN: python3 docs/db-redesign/code/code-analysis/project/scope-diff.py — confirm P-03
now shows test_written/implemented, not spec_written [NO TEST].

COVERAGE REPORT: report actual line/branch % for any touched files vs
src/backend/scripts/check_coverage_gates.py's enforced_baseline (core 71/53, supporting 70/48) — report
only, do not edit the gate script or project-scope-lock.yaml.

OUTPUT REQUIRED:
1. A git commit message.
2. IF clean: "Ready — 0.1.6 implemented and verified."
3. IF issues remain (test still red, scope-diff mismatch, coverage regression): a remediation prompt
   describing exactly what's unresolved, fix-forward by default (only suggest reverting if the
   analysis shows the whole approach here was wrong).
```

---

## Prompt 2 — Step 0.3 (F-01/F-06: executable frontend oracle) — IMPLEMENT

**Model/effort:** Claude Code `opus / high` · Codex `gpt-5-codex / high`.
**Deps:** 0.1.5 (done). **Touches:** none — safe to run in parallel with Prompt 1/3/4.

```
Implement clauses F-01+F-06 per
docs/db-redesign/code/code-analysis/project/specs/F-frontend-oracle-spec.md (multi-clause spec,
SPEC ONLY today — no oracle code exists anywhere in src/frontend or src/backend; confirmed via
`grep -rn model_json_schema` and no `*zod*` files found). Build the executable oracle:
- A Zod mirror of `lib/types.ts` on the frontend side.
- Pydantic `model_json_schema()` on the backend side, validated against the Zod mirror via ajv.
- MSW-based contract tests.
- ALL 10 contract items from the spec as executable assertions — F-06 is folded into F-01, not
  deferred (v2.0.0/A11) — including the `vpr_id: null`-vs-absent behavioral leg and the
  409-on-stale-`base_version` leg.
Write the RED tests described in the spec first, watch them fail, then the minimal GREEN code.

VERIFY:
cd src/frontend && npm run typecheck && npm run test:unit && npm run test:integration
cd src/backend && uv run pytest tests/unit -k "oracle or f01 or f06" -v

SCOPE-LOCK CHECK-IN: python3 docs/db-redesign/code/code-analysis/project/scope-diff.py — confirm F-01
and F-06 both show test_written/implemented.

COVERAGE REPORT: report actual vs enforced_baseline for touched backend files (report-only).

OUTPUT REQUIRED:
1. A git commit message.
2. IF clean: "Ready — 0.3 implemented and verified. Wave-0's frontend-contract net is now live for
   any later wave's contract-touching change."
3. IF issues remain: fix-forward remediation prompt with the specific failing assertion(s) named.
```

---

## Prompt 3 — Step 0.56 (P-32 budgets slice: AWS Budgets + Cost Anomaly Detection) — human console + thin AUTHOR

**Model/effort:** Claude Code `sonnet / medium` · Codex `gpt-5-codex / medium`.
**Deps:** 0.1 (done). **Touches:** none.

**⚠️ Naming note:** the execution-plan row cites `specs/P-32-budgets-slice-spec.md`, which does not
exist. The actual spec is `specs/P-32-cost-obs-edge-spec.md` ("Budgets slice, cost anomaly, tags,
correlation IDs, log retention, alarms, validators") — it bundles the Wave-0 budgets slice with
Wave-5 remainder items in one file. Confirm the budgets/cost-anomaly section is self-sufficient for
this step alone before running it; if it isn't scoped tightly enough to implement just the Wave-0
slice in isolation, treat that as a scope-lock deviation per §0.3 (STOP → Amendment Proposal) rather
than guessing the split.

```
This step is primarily a human console task (AWS Budgets + Cost Anomaly Detection), same category as
0.55's human-run items — no evidence artifact for it exists anywhere in the repo yet
(grep -rn "Budgets\|Cost Anomaly" only hits the spec file and vendored botocore data).

1. Read specs/P-32-cost-obs-edge-spec.md's budgets/cost-anomaly slice. If it's cleanly separable from
   the Wave-5 remainder, proceed; if not, stop and emit an Amendment Proposal (per §0.3) recommending
   the file be split, and wait for human confirmation before continuing.
2. Author any CDK needed for AWS Budgets / Cost Anomaly Detection thresholds (if the spec calls for
   IaC rather than a pure console click-through) under TDD — RED test asserting the budget/anomaly
   resource exists in synth, then GREEN.
3. Produce a human-run runbook (matching the style of runbooks/p28-human-gated-deploy-runbook.md) for
   whatever part is console-only and cannot be expressed in CDK.
4. Record an evidence artifact (script or doc) confirming the budget/anomaly detector actually exists
   in the target AWS account — do not mark this done on code existing alone; P-27/P-28 already
   established that pattern for human-run steps.

VERIFY: cd infra && cdk synth (if CDK touched); confirm the evidence artifact exists and is dated.

SCOPE-LOCK CHECK-IN: python3 docs/db-redesign/code/code-analysis/project/scope-diff.py — confirm P-32
shows test_written or better for the budgets sub-slice.

OUTPUT REQUIRED:
1. A git commit message.
2. IF clean: "Ready — 0.56 done, evidence artifact at <path>."
3. IF blocked on the human console action itself (can't be done by an agent): a remediation prompt
   that is actually a checklist for the human to execute, with the exact console steps and what
   evidence to paste back.
```

---

## Prompt 4 — Step 0.6 (P-12/P-13: RETAIN + deletion_protection) — TEST GAP CLOSURE, not IMPLEMENT

**Model/effort:** Claude Code `sonnet / medium` · Codex `gpt-5-codex / medium`.
**Deps:** 0.55, 0.61, 0.62 (all done). **Touches:** `api_db_construct.py` (test file only, unless a
gap is found), `app.py` — **serialize**; do not run concurrently with 0.65/0.7 prompts.

**⚠️ Corrected 2026-07-16 — the original premise below was wrong.** P-12/P-13 code is ALREADY LANDED
(commit `567320d`): `api_db_construct.py` applies `self.removal_policy` (RETAIN unless
`scratch_teardown_safe`) + `self.deletion_protection` + PITR at ~11 stateful sites. Do NOT
re-implement. The real gap is that scope-diff.py shows P-12/P-13 as `spec_written [NO TEST]` —
no test asserts this exists — so the step can't reach `verified`.

```
Step 0.6 (P-12/P-13) code is ALREADY LANDED (commit 567320d): infra/careervp/api_db_construct.py
defines self.removal_policy (RETAIN unless scratch_teardown_safe) + self.deletion_protection, applied
with PITR at ~11 stateful DynamoDB/S3 sites. Do NOT re-implement. Per
specs/P-12-P-13-retain-stateful-spec.md, the gap is test coverage:

1. Write the missing infra tests (characterization, since code exists): synth CareerVpCrudDev and
   assert RemovalPolicy.RETAIN + DeletionProtectionEnabled + PITR on EVERY stateful table/bucket, and
   assert P-13 (no dead RETAIN-flagged stack is instantiated). Tag them scope_lock_clause: P-12 / P-13
   so scope-diff.py picks them up. If any stateful site is found missing RETAIN, that IS a real GREEN
   fix — flag it explicitly, don't silently patch it into the test.
2. cd infra && cdk diff — confirm the DESTROY->RETAIN policy flip on already-deployed resources shows
   ZERO stateful replacement (this should already be true since the code has been live in the repo
   since commit 567320d — this is a confirmation, not a new risk).
3. Do NOT run cdk deploy / ExecuteChangeSet. Instead, answer this for the human: has deploy #1
   (RETAIN) actually been executed against the live dev stack? Check cdk diff against the deployed
   stack (not just synth) to determine drift. If cdk diff shows the policy already matches live state,
   deploy #1 already happened silently as part of a later deploy; if it shows a pending change, deploy
   #1 is still the human's next action.

VERIFY:
cd src/backend && uv run pytest tests/infrastructure -k "retain or p12 or p13" -v   # now selects >0 tests, all green
cd infra && uv sync && cdk synth && cdk diff
SCOPE-LOCK CHECK-IN: python3 docs/db-redesign/code/code-analysis/project/scope-diff.py — P-12/P-13 now test_written+.
OUTPUT REQUIRED:
1. A git commit message (tests only, unless a missed RETAIN site needed fixing).
2. A one-line human question: "Is deploy #1 (RETAIN) live on dev? [confirmed via cdk diff / needs
   ExecuteChangeSet]".
3. IF clean: "Ready — 0.6 test gap closed; deploy #1 status = <confirmed live / pending human action>."
```

---

## Prompt 5 — Step 0.64b finish (P-26 domain slice: prove O-9 closed) — IMPLEMENT/verify

**Model/effort:** Claude Code `opus / high` · Codex `gpt-5-codex / high`.
**Deps:** 0.62 (done); practically also wants 0.6's deploy #1 landed first for a clean baseline.
**Touches:** none for the remaining work (the CDK domain/cert/DNS piece is already done — this is
CI + frontend env only).

```
0.64b's CDK/DNS/cert slice is already implemented and evidenced: infra/careervp/api_construct.py:
262-286 has the ACM cert reference, REGIONAL DomainName for api.dev.careervp.com, and
BasePathMapping; dig confirms api.dev.careervp.com resolves; Amplify NEXT_PUBLIC_API_URL is set and
redeployed green. What remains, per O-9 in project-scope-lock.yaml (still status: OPEN):

1. The "Deploy Frontend" GitHub workflow was rewritten for Amplify SSR in commit 3d28d7d, but its
   last actual CI run was 2026-05-03 and FAILED — the fix has never executed in CI on this branch.
   Get it to run and go green for real (push/trigger it, don't just read the YAML and assume it's
   fine).
2. Once the workflow is proven green, run the P-30 4-wire smoke harness
   (src/backend/scripts/smoke_harness.py, from step 0.62) against the CUSTOM DOMAIN
   (api.dev.careervp.com), not the raw execute-api URL, and confirm all 4 wires pass.
3. Only after both (1) and (2) are green, mark O-9 status: RESOLVED in project-scope-lock.yaml — this
   IS a scope-lock edit, so it requires the §12 twin-sync protocol: update both project-scope-lock.md
   and .yaml in the same commit, add a §12 change-log row, bump the version, and the commit needs a
   `Scope-Lock-Approved-By: Yitzchak Meirovich <date>` trailer. Do not silently edit the open_questions
   block without that — the Scope-Lock Guard CI job will reject it anyway.

VERIFY: `gh run list --workflow=deploy-frontend.yml` shows a green run after your trigger; smoke
harness output against the custom domain, all 4 wires green.

SCOPE-LOCK CHECK-IN: python3 docs/db-redesign/code/code-analysis/project/scope-diff.py (no clause
change expected here besides the O-9 status flip, which lives in open_questions not the clause table).

OUTPUT REQUIRED:
1. A git commit message — note this will actually be a PAIR of commits if the O-9 flip needs to be
   separate from the workflow-trigger validation, so the twin-sync commit is isolated and reviewable.
2. IF clean: "Ready — 0.64b fully closed, O-9 resolved. Proceed to Prompt 6 (0.64 fire drill) if not
   already done, then Prompt 7 (0.65)."
3. IF the workflow still fails in CI: a fix-forward remediation prompt diagnosing the actual failure
   (don't just re-trigger blind).
```

---

## Prompt 6 — Step 0.64 (rollback fire-drill: from-scratch recreate RTO) — runbook, human-observed

**Model/effort:** none listed in the execution plan (runbook step, like 0.1 and 0.64's own text) —
run this one as a lightweight `sonnet / medium` orchestration since it mostly drives AWS operations
and records numbers, no code authorship.

**Deps:** 0.6, 0.61, 0.62 (0.6 must be landed — deploy #1 — before this is meaningful).

```
The incremental-redeploy RTO is already measured (~7 min: CFN update ~67-83s + CI overhead,
2026-07-11 recon, recorded in project-scope-lock.md:119). What's missing is the from-scratch
RECREATE case — the P-26 blue/green scenario, which couldn't be measured from expired CloudWatch
events. Using the P-29 evidence pack (0.61) as the "before" snapshot and the P-30 smoke harness
(0.62) as the pass/fail check:

1. In a scratch/dev-isolated context (never against the live stack without the P-27 stack policy
   correctly scoped), measure how long a from-scratch stack recreation actually takes — this may mean
   timing a `cdk deploy` of an isolated duplicate stack, or another safe proxy the human approves
   first. Do NOT experiment against the real dev stack's live resources without explicit human sign-
   off given P-27's RETAIN/deletion-protection is now live.
2. Record both numbers (incremental ~7min, from-scratch recreate) in project-scope-lock.md's
   evidence/current_state section — this is documentation, not a locked-decision edit, so it doesn't
   need full §12 amendment machinery, but flag it clearly as a factual update with a citation.

VERIFY: the recorded number has a timestamp and a reproducible method description, not just a bare
figure.

OUTPUT REQUIRED:
1. A git commit message.
2. IF clean: "Ready — 0.64 done, both RTO numbers on record. Proceed to Prompt 7 (0.65) once 0.64b is
   also fully closed."
3. IF you cannot safely measure from-scratch RTO without touching live resources: STOP and report
   back with exactly what human action/environment is needed instead of guessing.
```

---

## Prompt 7 — Step 0.65 (P-26 Job 1: resource-import migration) — IMPLEMENT, hard

**Model/effort:** Claude Code `opus / xhigh` · Codex `gpt-5-codex / high (max)` — hardest clause in
the wave; live-user blast radius.
**Deps:** 0.64b (fully closed, O-9 resolved), 0.6 (deploy #1 confirmed live), 0.61, 0.62, 0.63, 0.64
(verified) — **all must be `verified` before starting this prompt.** **Touches:** `api_construct.py`,
`app.py` — serial, and do not start until 0.6's deploy #1 has landed (this step must never move the
RestApi or the Cognito pool; the RETAIN policy from 0.6 is the safety net if anything goes wrong).

**⚠️ Corrected 2026-07-16 — the original Job-1 mechanism below is SUPERSEDED.** The Job-1 amendment
(`specs/amendments/P-26-job1-resource-import-amendment.md`, Option A) was **ACCEPTED 2026-07-15**:
the movable Lambdas/log-groups/queues carry explicit physical names and are already deployed, so a
plain nested-stack move fails with a CloudFormation "resource already exists" error. Job 1 is now a
**human-gated CFN resource-import / `cdk refactor` migration** (physical-id preserved), not an
automation-executed additive change. **Job 2 (new RestApi) is NOT triggered** — per-template resource
counts are all under 500 (dev 410, prod 421 — the amendment's own measurement).

```
Implement clause P-26 Job 1 per specs/P-26-blue-green-api-spec.md AS AMENDED by
specs/amendments/P-26-job1-resource-import-amendment.md (Option A ACCEPTED 2026-07-15). Read BOTH,
plus the spec's "Why this clause is uniquely dangerous" section, before writing anything.

MECHANISM (amended — this SUPERSEDES the spec's original Job-1 "create-in-nested/delete-from-parent"):
Job 1 is a HUMAN-GATED CloudFormation resource-import / `cdk refactor` migration (physical-id
preserved — no delete/create, no "resource already exists"). The movable feature Lambdas/log-groups/
queues carry explicit physical names and are already deployed, so import is the ONLY safe relocation.
The artifact-chain export locks (api_construct.py:2156-2193) must be broken/re-imported in the SAME
transaction. NOTE: the P-24 custom authorizer Lambda (_add_api_authorizer_lambda, api_construct.py:2034,
currently dormant/no call site, landed commit 09bd6f3) is another explicitly-named movable resource
that postdates this spec — account for it in the import mapping.

JOB 2 IS NOT TRIGGERED: every template is <500 (dev 410, prod 421, per the amendment). Do NOT stand up
a new RestApi. Prepare NO base-path flip / retire change set. If synth reveals a template >=500,
STOP per §0.3 (that contradicts the amendment's counts) — do not guess.

NON-NEGOTIABLE (unchanged, IMMUTABLE): never move the RestApi
(logical id CareerVpCrudDevCrudservicerestapi5E02FD49) in place or across stacks; never move/replace
the Cognito UserPool.

Write the RED tests first (they already exist as the fail-closed net —
src/backend/tests/infrastructure/test_p26_blue_green_api.py: RestApi logical-id/URL unchanged, Cognito
pool singular/untouched, no template >=500, P-28 replacement auto-fail). At IMPLEMENT time, update the
Job-1 Verify wording in the spec to "cdk diff shows import/refactor (physical-id preserved), not
create-in-nested/delete-from-parent" (authored now per the amendment DECISION section).

VERIFY:
cd infra && uv sync && cdk synth      # RestApi id/URL byte-stable; parent count reduced by the imported subtrees
cd infra && cdk refactor --dry-run    # (or the equivalent) shows IMPORT/refactor mappings, physical-ids preserved
cd src/backend && uv run pytest tests/infrastructure -k p26 -v

Do NOT run cdk deploy / cdk refactor execute / ExecuteChangeSet — hand the prepared refactor mapping +
templates + the P-28 DescribeChangeSet Replacement report to the human (P-28).

SCOPE-LOCK CHECK-IN: python3 docs/db-redesign/code/code-analysis/project/scope-diff.py — confirm P-26
shows test_written/implemented.

COVERAGE REPORT: report actual vs enforced_baseline for touched infra files (report-only).

OUTPUT REQUIRED:
1. A git commit message.
2. The exact list of resources being re-homed + which export locks are broken/re-imported, and the
   prepared refactor artifact path awaiting human execution.
3. IF clean: "Ready — 0.65 Job 1 refactor prepared (Job 2 not triggered). After human executes and
   P-30 smoke stays green on the RestApi's URL, proceed to Prompt 8 (0.7 re-verification) — the last
   Wave-0 blocker before Wave 1."
4. IF a live-truth contradiction surfaces: STOP per §0.3, emit an Amendment Proposal, do not guess.
```

---

## Prompt 8 — Step 0.7 (P-24: identity surrogate `user_id`) — RE-VERIFY, not IMPLEMENT

**Model/effort:** Claude Code `sonnet / medium` · Codex `gpt-5-codex / medium` (verification only —
authorizer *instantiation* is a separate, later Wave-1 P-04/P-07 action, out of scope here).
**Deps:** 0.65 (verified — resource-import must have re-homed the authorizer construct cleanly),
0.62 (done), O-4 (already RESOLVED). **Touches:** none expected (verification pass).

**⚠️ Corrected 2026-07-16 — this is NOT an IMPLEMENT step.** P-24 is ALREADY IMPLEMENTED (commit
`09bd6f3`, TDD, 13 tests): `identity_resolver.py`, `identity_map_repository.py`, authorizer wiring,
additive identity-map table. It landed DORMANT by design — `_add_api_authorizer_lambda`
(`api_construct.py:2034`) has no call site; the live authorizer is Cognito. It also landed AHEAD of
its own dependency (0.65) — safe (inert code) but means this prompt must re-confirm nothing broke
during 0.65's resource-import.

```
Step 0.7 (P-24) is IMPLEMENTED (commit 09bd6f3): identity_resolver.py, identity_map_repository.py,
authorizer wiring, additive identity-map table. It landed DORMANT — _add_api_authorizer_lambda
(api_construct.py:2034) has no call site; the live authorizer is Cognito. Do NOT re-implement, and do
NOT instantiate the custom authorizer here (that is a Wave-1 P-04/P-07 auth flip with its own P-23
canary + resolver-failure alarm — explicitly out of scope for 0.7/Wave 0).

Verify to the `verified` bar, AFTER 0.65's resource-import has landed (confirm the authorizer
construct/Lambda survived the re-home cleanly — that's the one thing 0.65 could break here):
1. cd src/backend && uv run pytest -k "p24 or identity_surrogate" -v   # expect the 13+ existing tests green
2. cd src/backend && uv run ruff format . && uv run ruff check . && uv run mypy careervp --strict
3. cd infra && uv sync && cdk synth   # Cognito UserPool + RestApi logical ids byte-stable (no replace);
   confirm the identity-map table and authorizer Lambda still synth correctly post-0.65 refactor
4. scope-diff.py — P-24 shows test_written/implemented.
5. Confirm in writing that the resolver is still dormant-by-design (authorizer not wired) and that
   flipping it on is a Wave-1 deliverable — so 0.7 = code+tests+synth verified, NOT live-behavior
   verified.

OUTPUT REQUIRED:
1. A git commit message (status/docs only, unless 0.65 broke something needing a fix).
2. IF clean: "0.7 re-verified post-0.65 (still dormant-by-design). Wave 0 is now FULLY complete and
   verified. Run the Wave-0 GATE (scope-diff.py full run + F-01 oracle + coverage/CI) before
   generating wave-1-prompts.md."
3. IF issues remain: fix-forward remediation prompt.
```

---

## Wave-0 GATE (run once Prompt 8 is clean)

```
Run the Wave-0 exit gate per redesign-execution-plan.md's GATE step type:
1. python3 docs/db-redesign/code/code-analysis/project/scope-diff.py — full run, zero drift across
   every Wave-0 clause (P-*, T-*, F-01/F-06).
2. The F-01/F-06 executable oracle (from Prompt 2) — full run, all 10 contract items green.
3. cd src/backend && make coverage-tests — confirm CI-gate-overall passes enforced_baseline; report
   how far each tier still sits from ratchet_target (do not edit the gate).
4. Confirm every Wave-0 row in redesign-execution-plan.md's Status column reads verified.

OUTPUT REQUIRED: a single "Wave 0 GATE PASSED" commit message (docs-only, the status-sync), and
confirmation that wave-1-prompts.md can now be generated — Wave 1 step 1.0's only dependency (0.7)
is satisfied.
```
