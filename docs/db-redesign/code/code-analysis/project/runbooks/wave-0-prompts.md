# Wave 0 — Remaining Prompts (copy-paste runbook)

- **Generated:** 2026-07-12, against `redesign-execution-plan.md` v2.0.0.
- **Purpose:** Wave 0 has 20 rows (0.0 → 0.75). A fresh validation pass (code + git evidence, not
  the table's own Status column, which is known to lag) found the table **wrong for four rows**
  and found **two rows with a spec but zero implementation** that the table's `verified`-adjacent
  neighbors made easy to miss. This file contains: (1) one prep prompt to fix the drift itself, then
  (2) one prompt per genuinely unfinished step, in dependency order. Steps already verified by real
  evidence are listed for completeness but have no prompt — there is nothing left to run.

## Validation summary (source of truth for this file)

| Step | Real status | Note |
|---|---|---|
| 0.0, 0.1, 0.1.5, 0.2, 0.35, 0.4, 0.5, 0.55 | done | table accurate |
| 0.61, 0.62, 0.63, 0.75 | **done, table says `not_started`** | commits `926a061`, `e3839c4`/`e3d3051` — status-board drift only |
| 0.1.6 (P-03), 0.3 (F-01/F-06) | **spec_written only — zero implementation/tests** | genuine gap, not board drift |
| 0.56 (P-32 budgets slice) | not_started | no code, no evidence artifact |
| 0.6 (P-12/P-13 RETAIN) | not_started | `api_db_construct.py` uses `RemovalPolicy.DESTROY` everywhere, zero `deletion_protection` |
| 0.64 (fire drill) | not_started | incremental RTO (~7min) known; from-scratch RTO never measured |
| 0.64b (domain slice) | in_progress | CDK/DNS/cert done; Deploy Frontend workflow fix never proven green in actual CI |
| 0.65 (P-26 decomposition) | not_started | correctly blocked |
| 0.7 (P-24 identity surrogate) | not_started | authorizer is a bare `sub` passthrough, no resolver exists |

**Critical path to Wave 1:** `{0.6, 0.64, 0.64b}` → `0.65` → `0.7` → Wave 1 step 1.0. None of the
four board-drift fixes (0.61/0.62/0.63/0.75) shorten this — they were already off the critical path.

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

## Prompt 4 — Step 0.6 (P-12/P-13: RETAIN + deletion_protection, deploy #1) — IMPLEMENT

**Model/effort:** Claude Code `sonnet / medium` · Codex `gpt-5-codex / medium`.
**Deps:** 0.55, 0.61, 0.62 (all done). **Touches:** `api_db_construct.py`, `app.py` — **serialize**;
do not run concurrently with 0.65/0.7 prompts (they touch the same files later in the chain).

```
Implement clauses P-12+P-13 per
docs/db-redesign/code/code-analysis/project/specs/P-12-P-13-retain-stateful-spec.md. Confirmed
current state: infra/careervp/api_db_construct.py uses RemovalPolicy.DESTROY at all 15 stateful-
resource sites (lines 101,142,164,220,267,292,330,356,396,433,547,584,601,636,670) and
`deletion_protection` appears zero times repo-wide.

- P-12: flip every stateful resource (DynamoDB tables, S3 buckets, etc.) to RemovalPolicy.RETAIN +
  deletion_protection=True where applicable. This is deploy #1 — the smallest safe first slice, now
  gated on the evidence pack (0.61) and smoke baseline (0.62) both being in place, which they are.
- P-13: identify and remove any dead RETAIN-flagged stacks never actually instantiated.
Write the RED test(s) the spec describes first (assert RemovalPolicy.RETAIN / deletion_protection on
each stateful construct via synth template inspection), watch them fail, then the minimal GREEN
CDK change.

VERIFY:
cd infra && uv sync && cdk synth   # confirm RETAIN + deletion_protection on all 15 sites
cd infra && cdk diff               # MUST show zero stateful-resource replacement
cd src/backend && uv run pytest tests/infrastructure -k "retain or p12 or p13" -v

This is a real AWS deploy candidate (deploy #1) — do NOT run `cdk deploy` or `ExecuteChangeSet`
yourself. Per P-28, only the human executes change sets. Stop at "change set prepared and diffed
clean" and hand off.

SCOPE-LOCK CHECK-IN: python3 docs/db-redesign/code/code-analysis/project/scope-diff.py — confirm P-12
and P-13 show test_written/implemented.

COVERAGE REPORT: report actual vs enforced_baseline for touched infra test files (report-only).

OUTPUT REQUIRED:
1. A git commit message.
2. A note that a human-run `ExecuteChangeSet` is now the literal next action (per the P-28 runbook),
   NOT something the next prompt in this series can do.
3. IF clean: "Ready — 0.6 change set prepared. After the human executes it and confirms deploy #1
   landed clean, proceed to Prompt 5 (0.64b finish) and Prompt 6 (0.64 fire drill), which can then
   run in either order relative to each other."
4. IF issues remain: fix-forward remediation prompt.
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

## Prompt 7 — Step 0.65 (P-26 Job 1+2: CFN decomposition + blue/green migration) — IMPLEMENT, hard

**Model/effort:** Claude Code `opus / xhigh` · Codex `gpt-5-codex / high (max)` — hardest clause in
the wave; live-user blast radius.
**Deps:** 0.64b (fully closed, O-9 resolved), 0.6, 0.61, 0.62, 0.63, 0.64 — **all must be `verified`
before starting this prompt.** **Touches:** `api_construct.py`, `app.py` — serial, and do not start
until 0.6's deploy #1 has landed (this step must never move the RestApi or the Cognito pool; the RETAIN
policy from 0.6 is the safety net if anything goes wrong).

```
Implement clause P-26 (Job 1 + Job 2) per
docs/db-redesign/code/code-analysis/project/specs/P-26-blue-green-api-spec.md. This is the hardest,
most dangerous step in Wave 0 — read the spec's "Why this clause is uniquely dangerous" section in
full before writing anything. Non-negotiable laws: NEVER move the existing RestApi in place or across
stacks (it changes the execute-api id/URL — 908 live users lose backend access until frontend
rebuilds); NEVER move the Cognito user pool.

Job 1 (do this first): decompose AROUND the RestApi — move feature Lambdas/alarms/non-stateful
resources out of the near-500-resource parent template (ServiceStack, currently ~415/500) into
per-feature nested stacks, leaving the RestApi's logical id and URL untouched. This alone relieves
the CFN resource-count pressure blocking later additive waves (P-09/P-14/P-17/P-21).

Job 2 (only if API-GW resource count still needs to shrink after Job 1): stand up a NEW RestApi in
its OWN stack, verify it via the P-30 4-wire harness against its raw invoke URL, prepare (but do NOT
execute) the base-path-mapping cutover on the now-proven custom domain api.{env}.careervp.com, and
prepare (but do NOT execute) the old-API retire as a separately gated change set. The domain FLIP and
the RETIRE are human-only ExecuteChangeSet actions (P-28) — this step prepares them, a human executes
them later.

Write the RED test(s) the spec describes first (synth-based assertions: RestApi logical id/URL
unchanged, resource counts per nested stack, Cognito pool untouched), watch them fail, then the
minimal GREEN CDK change.

VERIFY:
cd infra && uv sync && cdk synth      # RestApi id/url unchanged; parent template resource count reduced
cd infra && cdk diff                  # zero stateful-resource replacement; RestApi shows no replace
cd src/backend && uv run pytest tests/infrastructure -k p26 -v
Run the P-30 smoke harness against BOTH the old and (if Job 2 ran) new API's raw invoke URL.

Do NOT run cdk deploy or ExecuteChangeSet — hand the prepared change set(s) to the human per P-28.

SCOPE-LOCK CHECK-IN: python3 docs/db-redesign/code/code-analysis/project/scope-diff.py — confirm P-26
shows test_written/implemented.

COVERAGE REPORT: report actual vs enforced_baseline for touched infra files (report-only).

OUTPUT REQUIRED:
1. A git commit message.
2. An explicit list of what change set(s) are now prepared and awaiting human ExecuteChangeSet.
3. IF clean: "Ready — 0.65 Job 1 (and Job 2, if triggered) prepared. Once the human executes and
   confirms, proceed to Prompt 8 (0.7 identity surrogate) — the last Wave-0 blocker before Wave 1."
4. IF the spec's investigation brief surfaces a live-truth contradiction (e.g. resource counts don't
   match the spec's current_state numbers): STOP per §0.3, emit an Amendment Proposal, do not guess.
```

---

## Prompt 8 — Step 0.7 (P-24: identity surrogate `user_id`) — IMPLEMENT

**Model/effort:** Claude Code `opus / xhigh` · Codex `gpt-5-codex / high`.
**Deps:** 0.65 (verified), 0.62 (done), O-4 (already RESOLVED in project-scope-lock.yaml).
**Touches:** `cognito_construct.py`, the authorizer — serial with the 0.65 chain, do not overlap.

```
Implement clause P-24 per
docs/db-redesign/code/code-analysis/project/specs/P-24-identity-surrogate-spec.md. Confirmed current
state: src/backend/careervp/handlers/api_gateway_authorizer.py:72-83 is a bare passthrough —
`claims.get('user_id') or claims.get('sub')` — with no surrogate/resolver/link-table logic anywhere
(grep for identity_surrogate/sub_to_user_id/resolve_user_id/IdentityLink returns nothing).

Build the conservative link-by-verified-email default resolver (per O-4's decision, already recorded
in project-scope-lock.yaml — read that resolution before starting, do not re-ask the question). Write
the RED test(s) the spec describes first (sub→user_id resolution, link-by-verified-email behavior,
authorizer wiring), watch them fail, then the minimal GREEN code. Do NOT move the Cognito pool
(shared exclusion with P-26, already enforced by P-27's stack policy).

VERIFY:
cd src/backend && uv run pytest tests/unit -k "p24 or identity_surrogate" -v
cd src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict
cd infra && cdk synth   # confirm authorizer/cognito_construct changes, Cognito pool untouched (no replace)

SCOPE-LOCK CHECK-IN: python3 docs/db-redesign/code/code-analysis/project/scope-diff.py — confirm P-24
shows test_written/implemented.

COVERAGE REPORT: report actual vs enforced_baseline for touched files (report-only).

OUTPUT REQUIRED:
1. A git commit message.
2. IF clean: "Ready — Wave 0 is now FULLY complete and verified. Run the Wave-0 GATE
   (scope-diff.py full run + F-01 oracle + coverage/CI) before generating wave-1-prompts.md."
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
