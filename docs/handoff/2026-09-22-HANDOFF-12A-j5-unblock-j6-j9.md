# HANDOFF 12A — unblock J5, proceed through J6-J9

**Model: Opus 5, high effort recommended** (J5's root cause is unknown — a live
browser repro plus backend log correlation, the same shape of investigation
that found and fixed J4's regression the session before this one). Fresh
session at the repo root, on `tools/proof-harness`.

This is the execution half of a two-part handoff split from a combined
document. Its sibling, `2026-09-22-HANDOFF-12B-plan-assessment.md`, has the
full handoff-chain history (00-11) and the workstream-by-workstream mapping
against `PRODUCTION-PROGRAM.md`. Read this one to do the work; read B if you
need to understand how the project got here or report on overall progress.

---

## The one-sentence version

**The journey reaches J1-J4 (all passing, including a real AI-assist LLM
round trip) against deployed `devx` code at commit `86cb6b0b`** — the highest
it has ever genuinely measured — **and J5 is the sole blocker for J6-J9**,
failing on a pre-existing bug unrelated to anything fixed recently: the
company-research "Generate" button click never reaches the backend (zero
worker invocations in the failure window).

---

## Step 0 — verify before trusting this document

Run these before starting. If any diverges from the expected column, **stop
and reconcile before starting J5 work** — everything below assumes the state
here is current.

| # | Command | Expected |
|---|---|---|
| 0.1 | `aws cloudformation describe-stacks --stack-name CareerVpCrudDevx --region us-east-1 --query "Stacks[0].Outputs[?OutputKey=='DeployedGitSha'].OutputValue" --output text` | `86cb6b0be2bb2d65dc199e86f9ca8c32d37ed4b2-dirty` |
| 0.2 | `git log -1 --oneline origin/tools/proof-harness` | `2bb94af docs(handoff): handoff 12 — full chain progress assessment...` or later |
| 0.3 | `git merge-base origin/db-redesign origin/tools/proof-harness` vs `git rev-parse origin/db-redesign` | equal — `db-redesign` is still a strict subset of `tools/proof-harness`, per `CLAUDE.md`'s topology table |
| 0.4 | `cat docs/evidence/journey-20260922T104455-2b41d0a.json \| python3 -c "import json,sys; d=json.load(sys.stdin); print(d['journey_reached'], d['steps']['J5'])"` | `4 fail: Error: ...toHaveText... failed` |
| 0.5 | `aws dynamodb get-item --region us-east-1 --table-name careervp-users-table-devx --key '{"pk":{"S":"USER#848834a8-4061-703d-419c-0294d4e88d66"},"sk":{"S":"TRIAL"}}' --query 'Item.application_count.N' --output text` | check the number — **reset before running `make journey`** if it's not `0`; see Ground rules |
| 0.6 | `gh pr view 225 --json state -q .state` | `OPEN` — the CI `ENVIRONMENT=devx` wiring fix, still unmerged (see "Carried forward, unresolved" below) |

If 0.1/0.2 don't match, someone else has moved the branch or deployed since
this was written — re-derive the current state (`git log --oneline
origin/db-redesign..HEAD`, a fresh `make journey` run) before trusting
anything below.

---

## Context — how we got to "J1-J4 pass, J5 blocks"

Full narrative in HANDOFF-12B's "Part 2." The essentials:

- The prior session executed `HANDOFF-11-merge-and-validate.md` (baseline →
  predict → merge → validate), which merged HANDOFF-09's environment-coupling
  fixes and an async rework of gap-question generation (PR #224, deployed as
  `7d17968`).
- Post-merge validation found the async backend worked but a frontend polling
  bug left the gap-analysis page stuck on "Generating..." forever. Root
  cause: the poll loop re-armed via a `useEffect` keyed on React state that
  doesn't re-fire when two consecutive polls return the same in-progress
  value — which is guaranteed once a real LLM call outlives one 3-second
  tick. **Fixed in PR #226**, deployed as `0d99e901`.
- Re-testing that fix (and exercising the RichTextEditor's **AI Assist**
  button for real, per operator request) surfaced a second bug: the LLM call
  succeeded, but a downstream usage-metering write failed
  (`AccessDeniedException` — ai-assist's IAM role is deliberately read-only,
  by design, per its own least-privilege guardrail test), and that failure
  propagated up and discarded the already-successful response. **Fixed in
  PR #227**, deployed as `86cb6b0b`, by making the metering write
  non-fatal at its one shared call site (`llm_metering.py`) instead of
  widening IAM.
- Both fixes are now confirmed live: journey reaches **4 of 9**, J1-J4 all
  pass. J5 is next.

---

## What's known about J5 (MEASURED)

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
  the very first Phase 1 baseline (pre-merge, before *any* of the recent
  session's changes) and was already flagged in `prediction-2026-09-21.md`
  as "a pre-existing UI-locator issue unrelated to this merge." It predates
  HANDOFF-09's async work, HANDOFF-11's merge, and both bugs fixed since.
- Playwright's serial journey suite stops after the first failing test —
  confirmed by the last two runs both showing "N did not run" for every step
  after J5. **This is the only thing currently standing between the project
  and a real J6-J9 measurement.**

## What isn't known yet

- Whether the click handler fires at all (a frontend JS error would explain
  zero backend invocations without a network-level failure).
- Whether the POST that should start generation is issued but rejected before
  reaching the worker (e.g. a validation error, an auth issue, or something
  in the submit handler that fails silently — the same shape of bug an
  earlier handoff found for J3, before HANDOFF-09 fixed it as a side effect
  of the environment-coupling work).
- Whether `company_research_worker_handler.py:385`'s `_send_chain_signal` —
  the artifact chain's second consumer, called out explicitly in HANDOFF-09 as
  "budget for that" — interacts with this at all now that
  `ARTIFACT_CHAIN_ENABLED` is `true` in devx (it wasn't, when the original
  "Generate" bug was first observed in the Phase 1 baseline; it is now, as of
  PR #224's merge).

## Suggested starting point

1. Live browser reproduction with console/network capture — the same
   technique that found the frontend polling bug in the prior session,
   applied to the company-research "Generate" click. `journey.spec.ts`'s
   `attachDiagnostics(page)` helper already captures `console.error` and
   `requestfailed`; check whether the click even issues a request at all
   before assuming a backend problem.
2. If a request *is* issued: check `careervp-company-research-api-lambda-devx`'s
   logs for the specific request (not just the read-side GETs already
   confirmed) — was it received, and what did it return?
3. Given `ARTIFACT_CHAIN_ENABLED` flipped to `true` recently, specifically
   check whether company-research generation now routes through the Step
   Functions chain instead of (or in addition to) the standalone SQS path,
   and whether that routing is what's silently swallowing the request.
   HANDOFF-09 flagged this exact risk in advance: *"enabling the flag changes
   behaviour in two places, not one. Budget for that."*
4. Once fixed: re-run the journey. Given J5-J9 have never executed against
   deployed code even once, expect — per the master plan's own effort
   table — that reaching J9 surfaces its own defects at each step, the same
   way J1-J4 each hid one. Don't assume J6-J9 are clean just because J5 is
   fixed. Investigate and fix each in turn, same discipline as before: root
   cause from logs, not guesses; regression test that fails-before/passes-
   after; blast-radius before merge; confirm deployed before re-measuring.

---

## Carried forward, unresolved (operational hazards for this work)

- **`deployed commit is known` FAILs preflight on every run** — a `-dirty`
  GIT_STAMP issue open since handoff 08, present in every proof file so far.
  Not a blocker, but don't let it train you to skim the rest of the report.
- **PR #225** (CI `ENVIRONMENT=devx` fix for `cdk-diff`, `CDK Synth`,
  `CDK Validation`, `iac-security`) is open, unmerged. Until it lands, any PR
  touching infra loses the automated pre-merge diff check — repeat the
  manual-local-`cdk-diff` workaround (`ENVIRONMENT=devx npx cdk diff
  <stack> --app=".venv/bin/python3 ../../infra/app.py" --context
  "p26_rehome_features=true" ...`, same context flags `make deploy-devx`
  uses) before merging anything that touches `infra/`.
- **`python-security`, `iac-security` (pre-#225), `Infra Spec Consistency`**
  are known-red CI checks with diagnosed, uncontested, unrelated causes —
  don't mistake them for a regression caused by J5 work.

---

## Ground rules

- `scripts/ops/blast-radius.sh <event> <branch>` before any merge, deploy,
  deletion or credential change; paste Action/Triggers/Undo before acting.
- Stop and ask on `CREATE+EXECUTE` you didn't expect, `NO ENVIRONMENT GATE`,
  or an environment with `0 rules`.
- Verify the environment; never infer it from a plan document — including
  this one.
- **Reset the trial budget before running `make journey`** —
  `TRIAL_LIMIT_APPLICATIONS = 3`. Command is in
  `docs/handoff/2026-09-21-HANDOFF-11-merge-and-validate.md` §0.1.
- One concern per commit.
- A repo grep is not an inventory, and a green deploy is not a working
  system.
