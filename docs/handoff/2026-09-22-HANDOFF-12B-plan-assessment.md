# HANDOFF 12B — where the project actually stands against the plan

This is the assessment half of a two-part handoff split from a combined
document. Its sibling, `2026-09-22-HANDOFF-12A-j5-unblock-j6-j9.md`, is the
execution brief for unblocking J5 and proceeding through J6-J9. Read this one
to understand how the project got here and where it stands against
`docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md`; read A to do the next piece
of work.

---

## The one-sentence version

**The journey now reaches J1-J4 (all passing, for the first time ever,
including a real AI-assist LLM round trip) against deployed `devx` code at
commit `86cb6b0b`** — up from an inherited, never-actually-measured "3 of 9"
that anchored the whole program a week ago, and higher than any number this
project has genuinely measured before.

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
| **01** | Wire CI to the ~1,864 tests that already exist (W4.01) | Goal met, proof differs from prediction | All 6 steps landed: 8-directory-per-job pytest wiring, jest+vitest on PR, 2 orphaned e2e files un-orphaned (became 7 real Playwright tests), silent skips converted to `xfail(strict=True)`, `pytest-randomly` + `freezegun` added. **Major reframe found mid-work:** `vpr_handler.py` is dead code — `api_construct.py` nulls `self.vpr_generator_func = None`; production VPR runs through `vpr_submit_handler.py`→SQS→`vpr_worker_handler.py`. Meant most of "12 of 14 real failures touch VPR" was exercising an unreachable path — J5's real health was still unmeasured after this. `filterwarnings=["error"]` surfaced 137 failures, ~126 from one Powertools metrics warning, plus 8 genuine "coroutine never awaited" warnings that looked like a live async bug (later falsified — see 04). Branch left unpushed pending approval. |
| **02** | Fix whole-suite `sys.modules` contamination, starting from a confirmed 2-file repro | *(No execution record in the document set; likely absorbed into 03's Step 0 verification, which confirmed the fix landed: 2118 tests collected, 2058 passed/0 failed/0 errors under two orderings)* | Root cause: `test_k9_artifact_cleanup_env.py` evicted the backend's `careervp` package from `sys.modules` and never restored it, so a later `import careervp` resolved against `infra/careervp/__init__.py` instead — same unrestored-pop pattern found in 6 more files. **Also found:** the failure count is order-dependent, not just directory-dependent (`pytest-randomly` produced 465-655 failed / 78-97 errors across different random seeds) — the "606/100" figure was one specific ordering, not a stable target. |
| **03** | Prove CI actually runs (deferred 3x since handoff 01); close W5's 9 ungated `make deploy` workflows | Goal met, proof differs from prediction | First-ever real GitHub Actions run captured (`35524435480`): **7 jobs success, Pytest failure.** The chain's repeated claim "0 failed / 0 errors" turned out to be **a property of the local machine's AWS credentials + a stale `cdk.out`, not of the code** — falsified the premise 3 prior handoffs had carried. W5: closed for 2 of 9 (`db-redesign-checks.yml`, `ui-upgrade-checks.yml`, now `devx: required_reviewers`-gated). PR #221 opened against `ci/proof-base` — still open, unmerged, as of the most recent session. |
| **04** | Fix the 3 hermeticity failures CI found; gate `pull_request` on `main` itself; investigate the "coroutine never awaited" warnings for a live J4 async bug | Goal met, proof differs from prediction, applied 3 times | **The named root cause was wrong**: not 2 credential-touching tests, but one `autouse` fixture wiping the session-wide AWS credential baseline. True hermetic result (real no-credential run): **1429 passed, 16 skipped, 4 xfailed, 0 failed**, proven in CI twice. Gate-on-main PR #222 opened MERGEABLE. **The J4 async-bug hypothesis — carried as the chain's top escalation risk since handoff 01 — was falsified**: both real call sites (`gap_handler.py:185`, `company_research_worker_handler.py:443`) await correctly; all 8 warnings trace to 3 test files patching `asyncio.run` at the stdlib level instead of the coroutine. **Blocked on a human**: merging PR #222 (couldn't merge its own PR). Only 1 of 5+ files with the credential-mutation pattern was fixed; 4 more remained (`tests/integration/conftest.py`, `tests/integration/p05_seeding.py`, `tests/unit/test_llm_client.py`, `tests/unit/test_vpr_handler.py`). |
| **05** | Merge PR #222 (human); finish hermeticity on the remaining 4 files; execute one of 3 costed red-gate fixes; actually fix the asyncio.run test-patch bug | *(No HANDOFF-06 in this numbering continues this thread directly — the next document pivots topic. **PR #222 was in fact merged**, confirmed 2026-09-20T20:39:38Z, separately from this document.)* | Whether the remaining 4-file hermeticity fix and the asyncio.run test fix actually landed is **unverified** — worth a 5-minute check before assuming either is done (see "Carried forward, unresolved" below). |
| **06** | W0 (deploy-track prerequisites) → W1 (gated deploy + re-measure) | **A premise is false** (explicit, by filename) | Discovered the harness (Makefile targets, `preflight.py`, `journey.spec.ts`) **does not exist on `main` at all** — zero of 8 targets, none of 4 key files. `PRODUCTION-PROGRAM.md` assumed `main` was the deploy target; it never was. Also found the gated devx changeset path (`deploy.yml`'s `workflow_dispatch`) omits `p26_rehome_features=true`, which would **dissolve the live nested stack** (491 vs 261 resources) — a second landmine, independent of the main-vs-branch issue. A same-session addendum later states the doc's own central framing was wrong and points to handoff 07 instead — a deviation from "a session cannot certify its own work," recorded rather than hidden. |
| **07** | Deploy devx from `db-redesign` for real; get the first honest journey number | Goal met, proof differs from prediction | Confirmed `tools/proof-harness` ⊇ `db-redesign`, zero commits missing either way, and `main` was never the deploy target for this project, full stop. **First-ever journey measurement against deployed code: `2 of 9`**, J3 failing — the inherited "3 of 9" turned out to have been measured against `localhost:3000`, never a deployed environment. Two stated predictions were wrong (preflight's UNKNOWN→FAIL not PASS; 2-of-9 not 3-of-9) — recorded as misses, not corrected. Separately: an exposed admin IAM key was deactivated (broke the operator's own access — a repo grep is not a credential inventory), reactivated, then properly rotated. |
| **08** | Diagnose J3 (now the actual first failure) | Partially met | Six hypotheses eliminated (form fill, credits, backend rejection, redirect failure, wrong API URL, Cognito) — concluded **client-side, between click and fetch, no network request issued at all**, narrowed to 3 ranked suspects, not pinpointed. Restated plainly: "2 is not a regression from 3... do not restore the 3." Separately traced the `-dirty` stamping mechanism to `Makefile:28`'s simple-expansion timing vs CI's `make build` regenerating tracked files — 4 options costed, none picked. **This bug is still open** (`deployed commit is known` still FAILs preflight every run — see "Carried forward, unresolved"). |
| **09** | Environment-coupling: `ENVIRONMENT` unset defaults silently to another live environment's resources | Goal met | Root cause of J4's failure and of a silent subscription-quota bug: `ENVIRONMENT` was set on exactly 1 of ~31 Lambdas; six Class-A sites guessed `'dev'` when unset, meaning a devx Lambda could silently read `careervp-users-table-dev`. Fixed: `ENVIRONMENT` propagated to all Lambdas, `resource_env()` fails loud instead of guessing, a declared capability table (`environments.py`) replaced `naming.environment == "dev"` branching. This is also where J3's client-side mystery from handoff 08 got its real fix, alongside making gap-question generation properly async (SQS worker, off the 30s request path) — landed as commit `f96ad31`, written by a concurrent session mid-way through the HANDOFF-11 execution's own Phase 0 (see Part 2). |
| **10** | Dead-code / dead-API / table-map sweep (W2.1, W3.1, W4.3) | Goal met | Built `dead_code.py`, `dead_api.py`, `table_map.py`. **Inventory only — nothing deleted**, per the handoff's own ordering rule. Findings: an orphaned CDK stack (`cv_tailoring_stack.py`) shipped inside every one of ~31 Lambda deployment artifacts; 16 orphaned backend modules; a dead Lambda-construction method (`_add_vpr_lambda_integration`, confirming handoff 01's `vpr_handler.py` finding by a second method); 8 API routes with no frontend caller; 2 genuinely dead env vars (`TOKEN_BLACKLIST_TABLE_NAME`, `VPR_TABLE_NAME`); the `AWS::DynamoDB::Table` vs `GlobalTable` gate blind spot (from handoff 00) fixed in commit `0c04fc9`, closing the same class of gap that let the 2026-09-20 incident through. Full findings in `docs/DEAD-CODE.md`. |
| **11** | Baseline, predict, merge, validate | Goal met, proof differs from prediction (twice), extended well beyond its own scope | See Part 2 below. |

**The distribution, in the plan's own provenance vocabulary:** every number
above is MEASURED (a command was run, a file was read). The one place this
table itself is INFERRED rather than MEASURED is handoff 05's actual
execution (no HANDOFF-06 continuing that specific thread exists in this
numbering) — flagged explicitly in the row rather than silently assumed.

---

## Part 2 — HANDOFF-11's execution, in full

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
fixed and live. J5 is the new, sole blocker — see `HANDOFF-12A`.

---

## Part 3 — mapping to `PRODUCTION-PROGRAM.md`'s workstreams, honestly

| Workstream | Plan's definition | Status now |
|---|---|---|
| **W0** — deploy prerequisites | Fix wrong-stack measurement, stamp git SHA, commit evidence | **Partially done.** The wrong-stack confusion (measuring Devx, deploying Dev) is resolved — `main` was never the real target; `db-redesign`→`devx` is. The `-dirty` git-SHA stamping bug (found handoff 08) is **still open** — every deploy stamped `-dirty` despite a genuinely clean tree, because of a Makefile parse-time/CI-build-time ordering issue never fixed. |
| **W1** — gated deploy + re-measure | Push, PR, gated deploy, re-measure | **Done, repeatedly.** The pattern (blast-radius → PR → local `cdk-diff` review → merge → approve devx gate → wait → validate) is now well-exercised — 3 full cycles happened in HANDOFF-11's execution alone (PRs 224, 226, 227). |
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
in the current count is backed by a proof file with a matching `deployed_sha`.

**On the plan's own effort estimate (35-70 sessions, "J5-J9 unblock" scored
Low confidence / 5-15 sessions as the single largest source of spread):**
reaching J4 — 4 of the 6 previously-unexecuted steps — without yet reaching
J9 partially tightens that band per the plan's own stated logic ("reaching
J9 once, even with failures, converts the 5-15 band... into a known list").
It is not yet fully collapsed; J5-J9 remain the wildcard until J9 is reached
at least once.

---

## Carried forward, unresolved (do not silently drop these)

Compiled from the outcome table in Part 1 plus HANDOFF-11's execution:

- **`deployed commit is known` FAILs preflight on every run** — the
  `-dirty` GIT_STAMP issue, open since handoff 08, still present in every
  proof file recorded so far.
- **PR #225** (CI `ENVIRONMENT=devx` fix for `cdk-diff`, `CDK Synth`,
  `CDK Validation`, `iac-security`) is open, unmerged. Until it lands, every
  future PR touching infra loses the automated pre-merge diff check and must
  repeat the manual-local-`cdk-diff` workaround.
- **PR #221** (handoffs 01-03's broader CI wiring work) is open against
  `ci/proof-base`, not `main` or `db-redesign` — unclear if still relevant
  given how much has landed since; worth a quick check, not urgent.
- **Whether handoff 05's remaining hermeticity fix (4 files) and the
  asyncio.run test-patch fix actually landed is unverified** — no HANDOFF-06
  in this numbering continues that specific thread; PR #222 merged, but
  what exactly it contained wasn't re-verified.
- **7 of 9 workflows are still ungated `make deploy`** (W5).
- **`python-security`, `iac-security` (pre-#225), `Infra Spec Consistency`**
  are known-red CI checks with diagnosed, uncontested causes (upstream CVEs;
  the `ENVIRONMENT` CI gap; a reference to a deleted `dynamodb_stack.py`) —
  none fixed yet beyond PR #225 addressing `iac-security`.
- **`docs/DEAD-CODE.md`'s findings** — nothing deleted yet, by design.
- **No `docs/FEATURE-STATE.md` ledger exists** (W4.3).
- **J5 blocks J6-J9** — see `HANDOFF-12A` for the execution brief.

---

## Ground rules for anyone planning from this document

- Verify the environment; never infer it from a plan document — including
  this one, and including `PRODUCTION-PROGRAM.md` itself, which Part 1 above
  shows contained a wrong foundational assumption (`main` as deploy target)
  that took 3 handoffs to surface and correct.
- A repo grep is not an inventory, and a green deploy is not a working
  system. `docs/DEAD-CODE.md` exists specifically because absence of a
  reference in this repository is not proof of absence of a caller.
- Don't restate this document's numbers as fresh findings in the next
  planning pass — re-run Step 0 from `HANDOFF-12A` (or re-derive equivalent
  checks) and update in place if reality has moved.
