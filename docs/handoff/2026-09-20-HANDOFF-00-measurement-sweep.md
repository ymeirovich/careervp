# HANDOFF 00 — measure everything cheap, verify everything inherited

**Model: Sonnet 5, high effort.** Read-only measurement against known commands.
No judgment calls, no architecture. **Fresh session at the repo root, on
`tools/proof-harness`.**

This handoff runs **before** handoff 01. Its entire purpose is to stop the plan
from being rewritten every session by a discovery that a five-minute command
would have surfaced.

Parent plan: `docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md`. Read its
"The handoff chain" and "Validating this plan" sections first.

Paste everything below the line.

---

You are executing **handoff 00** of a chain. You change **no code**. You run
commands and record what they print.

## Why this session exists

Over three planning sessions, every significant discovery came from running a
command nobody had run — not from analysis. A 1.1M-line review (`ASTRA`) five
days earlier found none of them. The plan has therefore been rewritten
repeatedly, and its author's own audit found that the deploy track (handoff 03)
rests almost entirely on **inherited, unverified claims**.

Your job is to convert that inherited layer into measured fact, and to run every
cheap measurement nobody has run, **all at once**, so the remaining plan is built
on ground that has been stood on.

**Expect bad news.** Finding it here is the success condition. A sweep that
surfaces six new problems has done its job; a sweep that surfaces none either got
lucky or did not look.

## Rules for this session

1. **Change no code.** No fixes, however tempting. If you find something broken,
   write it down and keep going. A fix here would be untested and would
   contaminate the sweep.
2. **Record the command and its literal output** for every row. Not a summary —
   the output. A row with a conclusion but no output is not evidence.
3. **Three results, never two.** PASS / FAIL / **UNKNOWN**. "I could not check"
   is UNKNOWN and must never be written as PASS.
4. **Do not stop at the first failure.** Run every row.
5. If a command is expensive or dangerous, mark it UNKNOWN with the reason
   rather than improvising a substitute.

## Output

`docs/evidence/sweep-00-<timestamp>-<sha>.md`, committed. One table per section
below, every row filled. Plus `docs/evidence/sweep-00-<...>.json` with
`git_sha` / `git_dirty` per `HARNESS.md`.

**Commit the untracked evidence directories first** so `git_dirty` is false.
A dirty proof is non-reproducible and handoff 01 will reject it.

---

## Section A — Verify the inherited claims (highest value)

None of these have been checked by anyone in the current chain. Each is
load-bearing for handoff 03. **Any FAIL here changes the deploy plan.**

| # | Claim (source: 2026-09-14 handoff) | How to check |
|---|---|---|
| A1 | GitHub environment `deploy-dev` exists with **ymeirovich** as required reviewer | `gh api repos/:owner/:repo/environments/deploy-dev` |
| A2 | GitHub environment `staging` exists with required reviewer | `gh api repos/:owner/:repo/environments/staging` |
| A3 | Both are branch-restricted as claimed | same payload, `deployment_branch_policy` |
| A4 | IAM user `careervp-review-readonly` exists | `aws iam get-user --user-name careervp-review-readonly` |
| A5 | Policy `CareerVpReviewReadOnly` is genuinely read-only | `aws iam list-attached-user-policies`, then get the policy document; confirm no write verbs |
| A6 | Harness account `harness-d2892d12d4@careervp.com` exists in pool `us-east-1_bAZ6jb6HP` | `aws cognito-idp admin-get-user` |
| A7 | That account has an **active** subscription | `aws dynamodb get-item` on `careervp-users-table-devx`, pk `USER#8428d4e8-d071-7088-a9c3-9e630806436b`, sk `SUBSCRIPTION#CURRENT` |
| A8 | `scripts/ci/changeset_replacement_report.py` runs and flags protected types | read it; confirm it checks `RestApi`/`Table`/`Bucket`/`UserPool` |
| A9 | The four committed fixes have tests that **fail without the fix** | for S0a, S0b, K9, quota: `git stash` the source hunk, run its test, confirm red, restore. Do this carefully — `git status` first |
| A10 | The P-05 suite attacks as a real authenticated tenant | read `test_p05_cross_tenant_idor.py`; confirm a real login and an owner-positive control per denial case |

**A9 is the important one.** Four fixes are about to be deployed on the strength
of commit messages. A test that was written after the fix and never observed
failing proves only that it is consistent with current behavior.

## Section B — Run everything that has never been run

| # | Measurement | Command |
|---|---|---|
| B1 | Backend suite, combined | `cd src/backend && uv run pytest -q --tb=no \| tail -3` |
| B2 | Backend suite, per directory | the 8-directory loop from HANDOFF-01 Step 1 |
| B3 | Frontend jest | `cd src/frontend && npx jest --config jest.config.ts 2>&1 \| tail -8` |
| B4 | Frontend vitest | `npx vitest run --config vitest.config.ts 2>&1 \| tail -8` |
| B5 | Backend type check | `cd src/backend && uv run mypy careervp --strict 2>&1 \| tail -5` |
| B6 | Backend lint | `uv run ruff check . 2>&1 \| tail -5` |
| B7 | Frontend type check | `cd src/frontend && npm run typecheck 2>&1 \| tail -5` |
| B8 | CDK synth | `cd infra && uv sync && cdk synth 2>&1 \| tail -10` |
| B9 | Naming validation | `python src/backend/scripts/validate_naming.py --path infra --strict` |
| B10 | Preflight, current | `cd src/backend && make preflight` |
| B11 | `cdk diff` devx — what would a deploy actually change? | `cd infra && cdk diff CareerVpCrudDevx` |

**Recorded predictions** (from the 2026-09-19 planning session — score each):

- B1 → `606 failed, 1100 passed, 54 skipped, 4 xfailed, 100 errors`
- B2 → unit 1430p/0f · integration 185p/11f · infrastructure 81p/1f ·
  regression 37p/2f · e2e 4p/21s · models 18p · security 3p · infra 34p
- B3 → `85 suites, 429 passed, 26 skipped, 0 failed`
- B4 → `67 files, 739 passed, 0 failed`
- B5, B6, B7, B8, B9 → **no prediction; never run.** These are the highest-value
  unknowns in this section.
- B10 → 7 PASS / 1 UNKNOWN / 1 FAIL

B11 matters more than it looks: the devx stack has 10 tables **no
CloudFormation stack owns**. `cdk diff` will show whether a deploy intends to
*create* them — which would either fail or, worse, succeed against different
physical tables. Handoff 03 must not run until this is known.

## Section C — Environment and deploy reality

The planning session assumed no staging stack existed. **It does.** Assumptions
in this area have already proven wrong once.

| # | Question | How |
|---|---|---|
| C1 | Which CareerVp stacks exist, status, last-updated | `aws cloudformation list-stacks` filtered to `CareerVp` |
| C2 | Is `CareerVpCrudStaging` current or abandoned? | last-updated is 2026-04-12 — ~5 months stale. Check whether its Lambdas match current code |
| C3 | Does a production stack exist? | expected: **no** |
| C4 | Does GitHub environment `production` exist? | `gh api .../environments/production` — expected 404 |
| C5 | Which of the 9 ungated `make deploy` workflows actually deploy vs. no-op? | read each; a workflow whose deploy job is unreachable is not an exposure |
| C6 | Do the devx tables have PITR? | `aws dynamodb describe-continuous-backups` per table — spot-checked ENABLED on 2 of 10; confirm all |
| C7 | Log retention across Lambdas | gap-api is **1 day** (`api_construct.py`). Enumerate all; 1 day makes post-incident diagnosis impossible |

## Section D — Scope reality (V1 vs. what is measured)

**The journey's 9 steps are narrower than the V1 feature scope in `CLAUDE.md`.**
This was found on 2026-09-20 and is not yet reflected anywhere in the plan.

V1 per `CLAUDE.md`: Auth · VPR · CV Tailoring · Cover Letter · Gap Analysis ·
Interview Prep · **Company Research** · **Knowledge Base** · **English + Hebrew**.

The journey covers: sign in, upload CV, create application, gap analysis, VPR,
tailored CV, cover letter, interview prep, export.

| # | Question | Why it matters |
|---|---|---|
| D1 | Is Company Research reachable in the UI, and is it covered by any test? | V1 scope; not a journey step |
| D2 | Is Knowledge Base reachable and covered? | same |
| D3 | Is Hebrew/RTL functional? Six pages reference `locale`; the only e2e test for it (`cv-center.spec.ts:179`) is a TODO stub | V1 scope, zero real coverage |
| D4 | Is the **billing / trial / subscription** flow covered end to end anywhere? | It is not a journey step. It is the flow that takes money |
| D5 | Do Terms of Service / Privacy Policy pages exist? | none found under `src/frontend`; a paid product taking card details needs both |
| D6 | Is `STRIPE_SECRET_KEY` sourced from a secret store, and is there a live/test guard? | `stripe_provider.py` reads it from env |

**D4 is the one to weigh.** `N = 9` is the project's definition of done, and it
does not include the purchase path. A product can reach 9 of 9 and still not be
sellable.

## Section E — Score the predictions

Close the file with a table: prediction · observed · HELD / MISSED, and a hit
rate. This is the first entry in the plan's prediction ledger, and it is how the
planning process gets measured rather than trusted.

If the hit rate is below ~70%, say so plainly and recommend re-grounding the
plan before handoff 01 proceeds. That recommendation is a legitimate and valuable
outcome of this session.

## What success looks like

Every row has a command, a literal output, and PASS/FAIL/UNKNOWN. The prediction
ledger is scored. Anything newly discovered is written down — **not fixed**.

**These are complete outcomes, not failures:**

- *"A9 showed two of the four fixes have tests that pass without the fix."*
  Exactly what this session is for, and it changes handoff 03.
- *"B5 mypy --strict produces 400 errors."* Now it is a known number instead of
  an assumption inside `CLAUDE.md`'s mandatory-check list.
- *"B11 shows cdk diff wants to create 10 tables that already exist."* That
  stops handoff 03 from destroying data.
- *"Prediction hit rate was 9/13."* Useful. Say which four missed and why.

## Write handoff 01's Step 0 before you finish

Handoff 01 already exists (`2026-09-19-HANDOFF-01-ci-wiring.md`). **Do not
rewrite it.** Instead append a short block recording which of its Step 0
predictions your sweep already confirmed or refuted, so handoff 01 does not
re-run work you just did — and so any refuted premise is visible at the top of
that session rather than discovered halfway through it.

If your sweep contradicts handoff 01's premise badly enough that its work no
longer makes sense, say so and write the replacement scope. That is the chain
working, not the chain breaking.
