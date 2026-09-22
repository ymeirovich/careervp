# HANDOFF 12 — where the project actually stands, and unblocking J5

**Model: Opus 5, high effort recommended** (J5's root cause is unknown — a live
browser repro plus backend log correlation, the same shape of investigation
that found and fixed J4's regression this session). Fresh session at the repo
root, on `tools/proof-harness`.

This document has two jobs: **(1)** answer "where does this project actually
stand against `docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md`" by walking the
full handoff chain (00 through this session's execution of 11) with measured
outcomes, not restated intentions; and **(2)** hand off J5, the current
blocker for J6-J9, with everything known about it so far.

---

## The one-sentence version

**The journey now reaches J1-J4 (all passing, for the first time ever,
including a real AI-assist LLM round trip) against deployed `devx` code at
commit `86cb6b0b`** — up from an inherited, never-actually-measured "3 of 9"
that anchored the whole program a week ago — **and J5 is now the sole blocker
for J6-J9**, failing on a different, pre-existing bug: the company-research
"Generate" button click never reaches the backend (zero worker invocations
in the failure window).

---

## Step 0 — verify before trusting this document

Run these before reading further. If any diverges from the expected column,
**stop and reconcile before starting J5 work** — this document's later
sections assume the state below is current.

| # | Command | Expected |
|---|---|---|
| 0.1 | `aws cloudformation describe-stacks --stack-name CareerVpCrudDevx --region us-east-1 --query "Stacks[0].Outputs[?OutputKey=='DeployedGitSha'].OutputValue" --output text` | `86cb6b0be2bb2d65dc199e86f9ca8c32d37ed4b2-dirty` |
| 0.2 | `git log -1 --oneline origin/tools/proof-harness` | `f128131 docs(evidence): both fixes confirmed live...` |
| 0.3 | `git merge-base origin/db-redesign origin/tools/proof-harness` vs `git rev-parse origin/db-redesign` | equal — `db-redesign` is still a strict subset of `tools/proof-harness`, per `CLAUDE.md`'s topology table |
| 0.4 | `cat docs/evidence/journey-20260922T104455-2b41d0a.json \| python3 -c "import json,sys; d=json.load(sys.stdin); print(d['journey_reached'], d['steps']['J5'])"` | `4 fail: Error: ...toHaveText... failed` |
| 0.5 | `aws dynamodb get-item --region us-east-1 --table-name careervp-users-table-devx --key '{"pk":{"S":"USER#848834a8-4061-703d-419c-0294d4e88d66"},"sk":{"S":"TRIAL"}}' --query 'Item.application_count.N' --output text` | `1` — **one credit left; reset before running `make journey`, see Ground rules** |
| 0.6 | `gh pr view 225 --json state -q .state` | `OPEN` — the CI `ENVIRONMENT=devx` wiring fix, still unmerged (see "Carried forward, unresolved" below) |
| 0.7 | `gh pr view 221 --json state -q .state` | `OPEN` — handoffs 01-03's CI wiring work, still open against `ci/proof-base`, not `main` or `db-redesign`. Unclear if still relevant; worth a five-minute check, not a blocker. |

If 0.1/0.2 don't match, someone else has moved the branch or deployed since
this was written — re-run this session's own Phase 0.4-equivalent
(`git log --oneline origin/db-redesign..HEAD`) before trusting anything below.

---

## Part 1 — the handoff chain, 00 through 11, what actually happened

This project's own methodology (`PRODUCTION-PROGRAM.md`, "The handoff chain")
requires every handoff to report one of seven outcomes and to separate
MEASURED from INFERRED from INHERITED claims. The table below is built from
reading all twelve documents in full (00-11) — not from their own prose
summaries, several of which were later corrected by the next handoff in the
chain. Where a handoff's stated cause was later falsified by a *subsequent*
handoff, both are shown, because that reversal is itself the finding worth
carrying forward.

| # | Scope (as executed, not as originally planned) | Outcome | What it actually left true |
|---|---|---|---|
| **00** | Read-only measurement sweep — convert 10 inherited claims to MEASURED, run 11 never-run commands | Goal met | Combined pytest run **606 failed / 1100 passed / 100 errors** reproduced exactly; collapses to **14 real failures** when run per-directory (~592 failures + all 100 errors are `sys.modules` contamination, not broken behavior). `mypy --strict`, `ruff`, frontend typecheck, `cdk synth` all clean — first time anyone had run them. `preflight.py`'s "10/10 tables unmanaged" was a **false positive**: it queried `AWS::DynamoDB::Table` while every table is `AWS::DynamoDB::GlobalTable`. Same blind spot in the deploy gate's data-loss auto-fail (load-bearing — this is the exact gap the 2026-09-20 incident went through). |
| **01** | Wire CI to the ~1,864 tests that already exist (W4.01) | Goal met, proof differs from prediction | All 6 steps landed: 8-directory-per-job pytest wiring, jest+vitest on PR, 2 orphaned e2e files un-orphaned (became 7 real Playwright tests), silent skips converted to `xfail(strict=True)`, `pytest-randomly` + `freezegun` added. **Major reframe found mid-work:** `vpr_handler.py` is dead code — `api_construct.py` nulls `self.vpr_generator_func = None`; production VPR runs through `vpr_submit_handler.py`→SQS→`vpr_worker_handler.py`. Meant most of "12 of 14 real failures touch VPR" was exercising an unreachable path — **J5's real health was still unmeasured after this.** `filterwarnings=["error"]` surfaced 137 failures, ~126 from one Powertools metrics warning, plus 8 genuine "coroutine never awaited" warnings that looked like a live async bug (later falsified — see 04). Branch left unpushed pending approval. |
| **02** | Fix whole-suite `sys.modules` contamination, starting from a confirmed 2-file repro | *(No execution record in the document set; likely absorbed into 03's Step 0 verification, which confirmed the fix landed: 2118 tests collected, 2058 passed/0 failed/0 errors under two orderings)* | Root cause: `test_k9_artifact_cleanup_env.py` evicted the backend's `careervp` package from `sys.modules` and never restored it, so a later `import careervp` resolved against `infra/careervp/__init__.py` instead — same unrestored-pop pattern found in 6 more files. **Also found:** the failure count is order-dependent, not just directory-dependent (`pytest-randomly` produced 465-655 failed / 78-97 errors across different random seeds) — the "606/100" figure was one specific ordering, not a stable target. |
| **03** | Prove CI actually runs (deferred 3x since handoff 01); close W5's 9 ungated `make deploy` workflows | Goal met, proof differs from prediction | First-ever real GitHub Actions run captured (`35524435480`): **7 jobs success, Pytest failure.** The chain's repeated claim "0 failed / 0 errors" turned out to be **a property of the local machine's AWS credentials + a stale `cdk.out`, not of the code** — falsified the premise 3 prior handoffs had carried. W5: closed for 2 of 9 (`db-redesign-checks.yml`, `ui-upgrade-checks.yml`, now `devx: required_reviewers`-gated). PR #221 opened against `ci/proof-base` — **still open, unmerged, as of this session.** |
| **04** | Fix the 3 hermeticity failures CI found; gate `pull_request` on `main` itself; investigate the "coroutine never awaited" warnings for a live J4 async bug | Goal met, proof differs from prediction, applied 3 times | **The named root cause was wrong**: not 2 credential-touching tests, but one `autouse` fixture wiping the session-wide AWS credential baseline. True hermetic result (real no-credential run): **1429 passed, 16 skipped, 4 xfailed, 0 failed**, proven in CI twice. Gate-on-main PR #222 opened MERGEABLE. **The J4 async-bug hypothesis — carried as the chain's top escalation risk since handoff 01 — was falsified**: both real call sites (`gap_handler.py:185`, `company_research_worker_handler.py:443`) await correctly; all 8 warnings trace to 3 test files patching `asyncio.run` at the stdlib level instead of the coroutine. **Blocked on a human**: merging PR #222 (couldn't merge its own PR). Only 1 of 5+ files with the credential-mutation pattern was fixed; 4 more remained (`tests/integration/conftest.py`, `tests/integration/p05_seeding.py`, `tests/unit/test_llm_client.py`, `tests/unit/test_vpr_handler.py`). |
| **05** | Merge PR #222 (human); finish hermeticity on the remaining 4 files; execute one of 3 costed red-gate fixes; actually fix the asyncio.run test-patch bug | *(No HANDOFF-06 in this numbering continues this thread directly — the next document pivots topic. **PR #222 was in fact merged**, confirmed 2026-09-20T20:39:38Z, separately from this document.)* | Whether the remaining 4-file hermeticity fix and the asyncio.run test fix actually landed is **unverified** — worth a 5-minute check before assuming either is done (see "Open, never resolved" below). |
| **06** | W0 (deploy-track prerequisites) → W1 (gated deploy + re-measure) | **A premise is false** (explicit, by filename) | Discovered the harness (Makefile targets, `preflight.py`, `journey.spec.ts`) **does not exist on `main` at all** — zero of 8 targets, none of 4 key files. `PRODUCTION-PROGRAM.md` assumed `main` was the deploy target; it never was. Also found the gated devx changeset path (`deploy.yml`'s `workflow_dispatch`) omits `p26_rehome_features=true`, which would **dissolve the live nested stack** (491 vs 261 resources) — a second landmine, independent of the main-vs-branch issue. A same-session addendum later states the doc's own central framing was wrong and points to handoff 07 instead — a deviation from "a session cannot certify its own work," recorded rather than hidden. |
| **07** | Deploy devx from `db-redesign` for real; get the first honest journey number | Goal met, proof differs from prediction | **`db-redesign` ⊇ `tools/proof-harness`... no — `tools/proof-harness` ⊇ `db-redesign`, zero commits missing either way** — confirmed `main` was never the deploy target for this project, full stop. **First-ever journey measurement against deployed code: `2 of 9`**, J3 failing — the inherited "3 of 9" turned out to have been measured against `localhost:3000`, never a deployed environment. Two stated predictions were wrong (preflight's UNKNOWN→FAIL not PASS; 2-of-9 not 3-of-9) — recorded as misses, not corrected. Separately: an exposed admin IAM key was deactivated (broke the operator's own access — a repo grep is not a credential inventory), reactivated, then properly rotated. |
| **08** | Diagnose J3 (now the actual first failure) | Partially met | Six hypotheses eliminated (form fill, credits, backend rejection, redirect failure, wrong API URL, Cognito) — concluded **client-side, between click and fetch, no network request issued at all**, narrowed to 3 ranked suspects, not pinpointed. Restated plainly: "2 is not a regression from 3... do not restore the 3." Separately traced the `-dirty` stamping mechanism to `Makefile:28`'s simple-expansion timing vs CI's `make build` regenerating tracked files — 4 options costed, none picked. **This bug is still open as of this session** (`deployed commit is known` still FAILs preflight every run — see "Carried forward, unresolved"). |
| **09** | Environment-coupling: `ENVIRONMENT` unset defaults silently to another live environment's resources | Goal met (executed **this session**, as part of running handoff 11) | Root cause of J4's failure and of a silent subscription-quota bug: `ENVIRONMENT` was set on exactly 1 of ~31 Lambdas; six Class-A sites guessed `'dev'` when unset, meaning a devx Lambda could silently read `careervp-users-table-dev`. Fixed: `ENVIRONMENT` propagated to all Lambdas, `resource_env()` fails loud instead of guessing, a declared capability table (`environments.py`) replaced `naming.environment == "dev"` branching. **This is also where J3's client-side mystery from handoff 08 got its real fix**, alongside making gap-question generation properly async (SQS worker, off the 30s request path) — landed as commit `f96ad31`, written by a concurrent session mid-way through this session's Phase 0 (see Part 2). |
| **10** | Dead-code / dead-API / table-map sweep (W2.1, W3.1, W4.3) | Goal met | Built `dead_code.py`, `dead_api.py`, `table_map.py`. **Inventory only — nothing deleted**, per the handoff's own ordering rule. Findings: an orphaned CDK stack (`cv_tailoring_stack.py`) shipped inside every one of ~31 Lambda deployment artifacts; 16 orphaned backend modules; a dead Lambda-construction method (`_add_vpr_lambda_integration`, confirming handoff 01's `vpr_handler.py` finding by a second method); 8 API routes with no frontend caller; 2 genuinely dead env vars (`TOKEN_BLACKLIST_TABLE_NAME`, `VPR_TABLE_NAME`); the `AWS::DynamoDB::Table` vs `GlobalTable` gate blind spot (from handoff 00) fixed in commit `0c04fc9`, closing the same class of gap that let the 2026-09-20 incident through. Full findings in `docs/DEAD-CODE.md`. |
| **11** | Baseline, predict, merge, validate — the handoff this session executed | Goal met, proof differs from prediction (twice), extended well beyond its own scope | See Part 2 below — this is this session's work in detail. |

**The distribution, in the plan's own provenance vocabulary:** every number
above is MEASURED (a command was run, a file was read). The one place this
table itself is INFERRED rather than MEASURED is handoff 05's actual
execution (no HANDOFF-06 continuing that specific thread exists in this
numbering) — flagged explicitly in the row rather than silently assumed.

---

## Part 2 — this session (executing HANDOFF-11, then following its own findings)

### What HANDOFF-11 asked for, and what actually happened

HANDOFF-11's brief was baseline → predict → merge → validate, strictly
ordered, for whatever was on `tools/proof-harness`. That ran to completion —
see `docs/evidence/prediction-2026-09-21.md` (prediction, committed before the
merge, plus a `## Result` section appended after, per the handoff's own rule
against editing a prediction after the fact). Three things happened that the
handoff didn't anticipate, each investigated and resolved in turn rather than
deferred:

1. **The tree wasn't clean at Phase 0.** A concurrent session was mid-edit on
   the async gap-analysis fix (HANDOFF-09's Step 2.4) while this session was
   starting. Files changed between two `git status` calls a minute apart —
   correctly read as a live-edit signal, not proceeded past until confirmed
   finished (landed as `f96ad31`).
2. **The baseline (4/9) didn't match the handoff's predicted 3/9.** Root
   cause: `journey.spec.ts` had been rewritten in the same commit as the async
   fix (real SysAid fixtures, dropped J4's manual reload-loop), so the "3/9"
   prediction was stale the moment it was written. Accepted the 4/9 baseline
   with the mechanism fully documented, since the before/after comparison
   stayed internally valid (same test file both times).
3. **CI's `cdk-diff` was broken by the very fix being merged.** `d825f84`
   (HANDOFF-09's fail-loud `ENVIRONMENT` change) broke 4 CI jobs across 4
   workflow files that never set `ENVIRONMENT` before calling
   `cdk synth`/`cdk diff` — including the one check that's supposed to show
   the CloudFormation delta before merge. Fulfilled that check's *purpose*
   manually (`ENVIRONMENT=devx cdk diff` locally, same context flags
   `make deploy-devx` uses: 261 resources, nesting intact, zero stateful
   replacements) rather than merging blind, and opened the CI fix separately
   as **PR #225 — still open, not merged**, per explicit instruction to land
   it "at the next PR," not inside 11's own merge.

PR #224 merged: HANDOFF-09's environment-coupling fixes + the async
gap-analysis rework, deployed to devx as `7d17968`.

### Post-merge validation found the async fix's backend half worked and its frontend half didn't

Post-deploy journey: **3 of 9**, down from the 4/9 baseline, against a
predicted 5/9. Root-caused via CloudWatch logs, not guessed: the backend
completed the async gap-question job correctly in ~23 seconds (submit → SQS →
worker → LLM → `status=completed`), but the frontend's poll loop
(`gap-analysis/page.tsx`) made exactly 2 status requests then went silent for
the rest of an 8-minute test window — the failure screenshot shows the page
still reading "Generating..." long after the backend had the answer.

Root cause, confirmed by reading the code and reproducing the exact boundary
in a unit test: the poll loop re-armed itself via a `useEffect` keyed on
`generationStatus` React state. Two consecutive polls returning the *same*
in-progress value — guaranteed once a job outlives one 3-second tick, which
any real LLM call does — never re-triggers that effect, since React doesn't
re-run an effect whose dependency didn't change. **Fixed in PR #226**
(merged, deployed as `0d99e901`): the poll now re-arms directly from the
freshly-fetched status, not from a state-change diff. Regression test added
and verified against both the pre-fix code (fails at exactly the second
identical-status poll) and the fix (passes) — see
`tests/unit/gap-analysis-page.test.tsx::keeps polling through repeated
identical in-progress statuses`.

Per operator instruction, `journey.spec.ts`'s J4 was also updated to exercise
the RichTextEditor's **AI Assist** button for real (`POST /ai/assist` →
`ai-assist-lambda`) on the first question, instead of a synthetic fill.

### That surfaced a second, independent bug

Re-running the journey against the polling fix: J1-J4 progressed further, but
the AI Assist click returned `500 INTERNAL_ERROR`. CloudWatch logs showed the
LLM call itself succeeded (200 OK, 1026 tokens, $0.002), but the *subsequent*
usage-metering write to `careervp-applications-table-devx` failed with
`AccessDeniedException` — ai-assist's IAM role is deliberately read-only
there, enforced by its own least-privilege guardrail test
(`test_ai_assist_lambda_policy_is_least_privilege`, which explicitly asserts
`UpdateItem` must never be granted). Widening that role's IAM would have
fixed this one call site but violated a real architectural boundary and left
every *other* LLM call site (any Lambda, any table hiccup) still capable of
discarding a successful generation over a pure cost-tracking side effect.

**Fixed in PR #227** (merged, deployed as `86cb6b0b`) at the shared root: the
metering write (`llm_metering.py::record_llm_usage`) now catches and logs a
failure instead of letting it propagate up through `llm_client.py`'s
`complete()`/`generate()` and discard an already-successful LLM response.
Regression test added, same discipline (fails against pre-fix code, passes
against the fix).

### Current confirmed state

Journey against `86cb6b0b`: **4 of 9 — J1, J2, J3, J4 all pass**, including
the AI Assist round trip end to end (generate → text lands in the editor →
save succeeds). Both bugs found during this session's own validation are
fixed and live. J5 is the new, sole blocker — see Part 3.

---

## Part 3 — J5, what's known, what isn't

### What's known (MEASURED this session)

- Failure: `module-card-companyResearch`'s `primary-cta` never leaves
  "Generate" within the 240s `GENERATION_TIMEOUT_MS` budget
  (`journey.spec.ts:298`, inside `generateFromHub()`).
- `careervp-company-research-worker-lambda-devx` shows **zero invocations**
  in the failure window (`docs/evidence/journey-20260922T104455-2b41d0a.json`,
  cross-checked against CloudWatch Logs directly — not inferred from the
  test alone).
- `careervp-company-research-lambda-devx` (the API-facing Lambda) *was*
  invoked repeatedly during the same window, all `status_code: 200` — but
  those are the hub's read/poll `GET` calls, not the `POST` that should start
  generation.
- **This is not new.** The identical locator/message signature appears in
  the very first Phase 1 baseline (pre-merge, before *any* of this session's
  changes) and was already flagged in the original `prediction-2026-09-21.md`
  as "a pre-existing UI-locator issue unrelated to this merge." It predates
  HANDOFF-09's async work, HANDOFF-11's merge, and both bugs fixed this
  session.
- Playwright's serial journey suite stops after the first failing test —
  confirmed by the last two runs both showing "N did not run" for every step
  after J5. **This is the only thing currently standing between the project
  and a real J6-J9 measurement.**

### What isn't known yet

- Whether the click handler fires at all (a frontend JS error would explain
  zero backend invocations without a network-level failure).
- Whether the POST that should start generation is issued but rejected before
  reaching the worker (e.g. a validation error, an auth issue, or something
  in the submit handler that fails silently — the same shape of bug HANDOFF-08
  found for J3, before HANDOFF-09 fixed it as a side effect of the
  environment-coupling work).
- Whether `company_research_worker_handler.py:385`'s `_send_chain_signal` —
  the artifact chain's second consumer, called out explicitly in HANDOFF-09 as
  "budget for that" — interacts with this at all now that
  `ARTIFACT_CHAIN_ENABLED` is `true` in devx (it wasn't, when the original
  "Generate" bug was first observed in the Phase 1 baseline; it is now, as of
  PR #224's merge in this session).

### Suggested starting point for the next session

1. Live browser reproduction with console/network capture — the same
   technique that found the frontend polling bug this session, applied to
   the company-research "Generate" click. `journey.spec.ts`'s
   `attachDiagnostics(page)` helper already captures `console.error` and
   `requestfailed`; check whether the click even issues a request at all
   before assuming a backend problem.
2. If a request *is* issued: check `careervp-company-research-api-lambda-devx`'s
   logs for the specific request (not just the read-side GETs already
   confirmed) — was it received, and what did it return?
3. Given `ARTIFACT_CHAIN_ENABLED` flipped to `true` in this session's merge,
   specifically check whether company-research generation now routes through
   the Step Functions chain instead of (or in addition to) the standalone SQS
   path, and whether that routing is what's silently swallowing the request.
   HANDOFF-09 flagged this exact risk in advance: *"enabling the flag changes
   behaviour in two places, not one. Budget for that."*
4. Once fixed: re-run the journey. Given J5-J9 have never executed against
   deployed code even once, expect — per the master plan's own effort
   table — that reaching J9 surfaces its own defects at each step, the same
   way J1-J4 each hid one. Don't assume J6-J9 are clean just because J5 is
   fixed.

---

## Part 4 — mapping to `PRODUCTION-PROGRAM.md`'s workstreams, honestly

| Workstream | Plan's definition | Status now |
|---|---|---|
| **W0** — deploy prerequisites | Fix wrong-stack measurement, stamp git SHA, commit evidence | **Partially done.** The wrong-stack confusion (measuring Devx, deploying Dev) is resolved — `main` was never the real target; `db-redesign`→`devx` is. The `-dirty` git-SHA stamping bug (found handoff 08) is **still open** — every deploy in this session stamped `-dirty` despite a genuinely clean tree, because of a Makefile parse-time/CI-build-time ordering issue never fixed. |
| **W1** — gated deploy + re-measure | Push, PR, gated deploy, re-measure | **Done, repeatedly**, this session and prior ones. The pattern (blast-radius → PR → local `cdk-diff` review → merge → approve devx gate → wait → validate) is now well-exercised — 3 full cycles happened in this session alone (PRs 224, 226, 227). |
| **W2** — table architecture | Build `table_map.py`, fix mismatches | **W2.1 done** (handoff 10). **W2.2/W2.3 not started** — inventory only, no fixes applied, no single-vs-multi-table decision made. |
| **W3** — dead code sweep | Build `dead_api.py`/`dead_code.py`, remove findings | **W3.1 done** (handoff 10). **W3.3 not started** — `docs/DEAD-CODE.md` exists, nothing in it has been deleted, per the handoff's own ordering rule (inventory first, deletion is a separate reviewable pass). |
| **W4** — test integrity, e2e, feature ledger | Wire CI (W4.01), rebuild e2e per feature (W4.1/4.2), generate a feature-state ledger (W4.3) | **W4.01 done** (handoffs 01-05, with one unresolved thread — see below). **W4.1/W4.2/W4.3 not started** — no `docs/FEATURE-STATE.md` exists yet; the per-feature e2e rebuild (282 blocks across 4 dispositions) hasn't begun. |
| **W5** — close 9 ungated `make deploy` workflows | Gate every deploy path | **2 of 9 closed** (`db-redesign-checks.yml`, `ui-upgrade-checks.yml`). **7 remain ungated**, unchanged since handoff 03. |
| **W6** — environment rebuildability | `cdk import` or accept 10 unmanaged tables | **Superseded, not resolved.** Handoff 00 found the "10/10 unmanaged" reading was itself a false positive (wrong DynamoDB type queried) — the tables *are* CFN-managed. Whether the environment is genuinely rebuildable from source was never re-verified after that correction. |

**The plan's own headline metric** — `make journey` reporting 9 of 9 — now
reads **4 of 9**, against an inherited "3 of 9" that turned out to have never
been a real measurement (handoff 07/08's finding) and a true first
deployed-code measurement of 2 of 9 (handoff 07). **This is the highest the
number has ever genuinely been**, and unlike the historical "3," every point
in this session's count is backed by a proof file with a matching
`deployed_sha`.

---

## Carried forward, unresolved (do not silently drop these)

Compiled from the outcome table in Part 1 plus this session's own findings —
each of these has been named at least once and not yet closed:

- **`deployed commit is known` FAILs preflight on every run** — the
  `-dirty` GIT_STAMP issue, open since handoff 08, still present in this
  session's every proof file.
- **PR #225** (this session's CI `ENVIRONMENT=devx` fix for `cdk-diff`,
  `CDK Synth`, `CDK Validation`, `iac-security`) is open, unmerged. Until it
  lands, every future PR touching infra loses the automated pre-merge diff
  check and must repeat this session's manual-local-`cdk-diff` workaround.
- **PR #221** (handoffs 01-03's broader CI wiring work) is open against
  `ci/proof-base`, not `main` or `db-redesign` — unclear if still relevant
  given how much has landed since; worth a quick check, not urgent.
- **Whether handoff 05's remaining hermeticity fix (4 files) and the
  asyncio.run test-patch fix actually landed is unverified** — no HANDOFF-06
  in this numbering continues that specific thread; PR #222 merged, but
  what exactly it contained wasn't re-verified in this document.
- **7 of 9 workflows are still ungated `make deploy`** (W5).
- **`python-security`, `iac-security` (pre-#225), `Infra Spec Consistency`**
  are known-red CI checks with diagnosed, uncontested causes
  (upstream CVEs; the `ENVIRONMENT` CI gap; a reference to a deleted
  `dynamodb_stack.py`) — none fixed yet beyond this session's PR #225
  addressing `iac-security`.
- **`docs/DEAD-CODE.md`'s findings** — nothing deleted yet, by design.
- **No `docs/FEATURE-STATE.md` ledger exists** (W4.3).

---

## Ground rules

Same as every prior handoff in this chain, restated because they're load-bearing:

- `scripts/ops/blast-radius.sh <event> <branch>` before any merge, deploy,
  deletion or credential change; paste Action/Triggers/Undo before acting.
- Stop and ask on `CREATE+EXECUTE` you didn't expect, `NO ENVIRONMENT GATE`,
  or an environment with `0 rules`.
- Verify the environment; never infer it from a plan document — including
  this one, and including `PRODUCTION-PROGRAM.md` itself, which this
  document's own Part 1 shows contained a wrong foundational assumption
  (`main` as deploy target) that took 3 handoffs to surface and correct.
- **Reset the trial budget before running `make journey`** —
  `TRIAL_LIMIT_APPLICATIONS = 3`, and Step 0.5 above shows only 1 credit
  remains. Command is in `docs/handoff/2026-09-21-HANDOFF-11-merge-and-validate.md`
  §0.1.
- One concern per commit. This session's evidence, prediction, and each fix
  landed as separate commits/PRs even when discovered in the same
  investigative arc — keep doing that.
- A repo grep is not an inventory, and a green deploy is not a working
  system. `docs/DEAD-CODE.md` exists specifically because absence of a
  reference in this repository is not proof of absence of a caller.
