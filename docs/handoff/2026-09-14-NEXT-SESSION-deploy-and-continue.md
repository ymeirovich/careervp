# Next session — deploy the fixes, then keep pushing the journey number

**Model: Sonnet 5, high effort** for the deploy/re-measure loop (routine execution
against an established harness). Escalate to **Opus 5, high effort** only if J4's
generation-reliability defect (below) turns out to need an architectural fix
(sync → async), since that's a different kind of problem than everything else in
this doc. **Fresh session at the repo root, on `tools/proof-harness`.**

Paste everything below the line.

---

You are continuing work from a prior session that ran `make journey` for the
first time, fixed three confirmed bugs, repaired a hollow security test suite,
and closed the automated-deploy gate. **None of the code fixes are deployed
yet** — that session was explicitly told not to deploy, and the branch itself
was never pushed. That is today's first job.

## Read first, in this order

1. This document.
2. `docs/HARNESS.md` — the five `make` commands and the proof discipline.
3. `CLAUDE.md` — mandatory check commands per changed path.
4. `git log --oneline cea0799..HEAD` — twelve commits, each with a full
   explanation in its message. Read the messages before touching the code they
   describe; do not re-derive what they already established.

Do **not** re-open `docs/evidence/p1-repro/` or the `ASTRA-*` audit docs unless
a specific fix needs a detail from them — they're settled history, not open
questions.

## Where things stand (established, do not re-litigate)

- Branch `tools/proof-harness`, 12 commits ahead of `cea0799`, **entirely
  local** — `git ls-remote origin tools/proof-harness` returns nothing. Nothing
  has been pushed, no PR exists, nothing is deployed.
- `make journey` against `CareerVpCrudDevx`: **REACHED 3 of 9**, reproducibly
  (two separate runs, same result). J1 sign-in, J2 upload CV, J3 create
  application pass. J4 (gap analysis) fails — see below, this is a real
  backend defect, not a test bug.
- Three confirmed bugs fixed with real regression tests: **S0a** (VPR export
  IDOR), **S0b** (VPR status S3-fallback IDOR), **K9** (cleanup Lambda missing
  its jobs-table env var + IAM grant, 336/336 failed invocations). None of
  these three are exercised by journey steps J1–J4, so their fix won't move N
  on its own — they matter regardless of N.
- A **new bug found and fixed along the way**: `_check_create_job_access` in
  `job_handler.py` re-ran a raw trial check after `QuotaService` had already
  allowed access via an active subscription — any customer who subscribed
  after exhausting trial credits was permanently blocked from creating a job.
  Fixed; this is the one fix among the four that *could* move N, once deployed
  (a fresh account only hits the old bug after its first 3 applications).
- The P-05 cross-tenant IDOR suite was hollow (attacked with no login at all,
  which the removed P-04 header-fallback made moot; the export case was
  pinned to the one moduleType that was already safe). Rewritten to attack as
  a real authenticated different tenant, cover all four export types, and
  give every denial case an owner-positive control. All green for real now.
- P-28 deploy gate: `deploy-staging.yml` was silently deploying **dev**, not
  staging (`make deploy` hardcodes `CareerVpCrudDev`), with no human gate.
  `deploy-vpr-async.yml` ran a full auto-execute `cdk deploy --all` on every
  push touching VPR paths — `cdk list` confirms that resolves to
  `CareerVpCrudDev` (the same stack `deploy.yml` already gates) plus
  `CareerVpFrontend-Dev`. Both converted to changeset-create + human-gated
  execute, mirroring `deploy.yml`'s already-compliant pattern.
- Created GitHub environments `deploy-dev` and `staging`, both with
  **ymeirovich** as required reviewer, restricted to their respective
  branches. Neither existed with protection before — the gate the compliant
  workflow referenced would have auto-created unprotected on first run.
- Provisioned genuinely read-only AWS credentials: IAM user
  `careervp-review-readonly`, policy `CareerVpReviewReadOnly` (Get/List/
  Describe only — verified a DynamoDB `PutItem` is denied). Access key saved
  to that session's scratchpad as `careervp-review-readonly-key.json` — **it
  has not been handed to you in this doc; retrieve it from wherever the user
  saved it, or re-issue via `aws iam create-access-key --user-name
  careervp-review-readonly` if it's been lost/rotated.**
- **New finding, not fixed** (out of scope for the prior session, still open):
  `.github/workflows/main-serverless-service.yml` runs `make deploy` directly
  for both `staging` and `production` on `workflow_dispatch`, no changeset
  gate. Lower risk than the two fixed workflows (needs a manual trigger, not a
  bare push) but the same class of gap, and its `production` GitHub
  environment doesn't exist yet either — would auto-create unprotected on
  first use exactly like the other two did.
- `make preflight` reports 7 pass / 1 unknown / 1 fail, unchanged across the
  whole session — both pre-existing, both out of scope for that session:
  - **UNKNOWN** — no `DeployedGitSha` stack output yet. This will resolve
    itself on the next real deploy: `service_stack.py` already emits it from
    `--context git_sha=$(git rev-parse HEAD)`, which `make deploy-devx` passes
    but the plain changeset targets (`create-changeset`/`execute-changeset`,
    what P-28 now requires) do not. Decide whether to also pass `git_sha`
    through those Makefile targets, or accept this stays UNKNOWN under the
    gated flow.
  - **FAIL** — `careervp-applications-table-devx`, `-artifacts-table-devx`,
    `-company-research-cache-table-devx`, `-cvs-table-devx` exist but no
    CloudFormation stack owns them. A rebuild would not recreate them. This
    needs a `cdk import` or equivalent, not a code fix — flagging again
    because it's real and still unaddressed, not because it's this session's
    job.

## The one rule that matters (unchanged from last time)

```
preflight   →  are my facts true?
journey     →  how far does a customer get?   (N of 9)
one change  →  aimed at step N+1
journey     →  did N go up?
                 up   → commit
                 down → REVERT FIRST, investigate second
                 flat → the change didn't do what you predicted; read the failing step
```

## Step 1 — Get the fixes reviewable and deployable

The four code fixes (S0a, S0b, K9, the quota double-check) and the test-suite
repair are sitting in local commits on `tools/proof-harness`. They cannot help
anyone, and `make journey` cannot reflect them, until they're deployed — and
per this project's own P-28 rule (which this session helped close), **you do
not execute that deploy yourself.**

1. Confirm with the user before pushing anything (this is the kind of action
   that needs a nod first, not blanket pre-authorization from an old
   instruction). Once confirmed: push `tools/proof-harness` and open a PR
   against `main`.
2. Ask the user (ymeirovich) to review and merge it, then either:
   - push to `main`, which now runs `deploy.yml`'s `create-change-set-dev`
     job automatically (changeset-create only, no execute), or
   - trigger `deploy-staging.yml` / `deploy-vpr-async.yml` if those paths are
     more appropriate for a subset of the changes.
3. The user, not you, approves the `deploy-dev` (or `staging`) environment gate
   to let the paired `execute-change-set-*` job actually run
   `execute-change-set`. Read the Replacement report in the job summary first
   — if `scripts/ci/changeset_replacement_report.py` flags any protected
   resource (`RestApi`/`Table`/`Bucket`/`UserPool`) as `Replacement: True`,
   that changeset must not be approved; it means CloudFormation intends to
   delete and recreate a stateful resource.
4. Once deployed, confirm the `DeployedGitSha` stack output (if wired through)
   or at minimum confirm via `aws lambda get-function-configuration` /
   CloudWatch that the new code is live before trusting any subsequent
   `make journey` result against it.

## Step 2 — Re-measure once the quota fix is live

Once deployed, reset the harness account's trial state is **no longer
required for job creation** (that was a workaround for the quota bug you just
shipped) — but you may still need it once if the account's trial genuinely
expired again by then:

```bash
cd src/backend
E2E_TEST_EMAIL=harness-d2892d12d4@careervp.com E2E_TEST_PASSWORD=<see below> \
BASE_URL=http://localhost:3000 make journey
```

The harness account is `harness-d2892d12d4@careervp.com` in the devx Cognito
pool (`us-east-1_bAZ6jb6HP`), given an active subscription this session (so it
no longer needs a trial at all) — check `SUBSCRIPTION#CURRENT` under
`USER#8428d4e8-d071-7088-a9c3-9e630806436b` in `careervp-users-table-devx`
before assuming it's still active. If you don't have the password, reset it:

```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_bAZ6jb6HP \
  --username harness-d2892d12d4@careervp.com \
  --password '<new-password-meeting-policy>' --permanent --region us-east-1
```

Running the frontend locally against devx needs `next dev` in `src/frontend`
with `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_COGNITO_USER_POOL_ID`,
`NEXT_PUBLIC_COGNITO_CLIENT_ID`, `NEXT_PUBLIC_COGNITO_REGION`, and
`NEXT_PUBLIC_COGNITO_DOMAIN` set as real environment variables in the shell
that starts it (not a `.env.local` file — writing one was blocked by this
session's permission settings, and exporting them in-shell works identically
since `next.config.js` reads them from `process.env`). Values are in
`infra/careervp/api_construct.py`'s CDK outputs for `CareerVpCrudDevx`, or `aws
cloudformation describe-stacks --stack-name CareerVpCrudDevx`.

## Step 3 — J4 is a real backend defect, not a test problem

`journey.spec.ts`'s J4 step (gap analysis) is correctly written — it drives
the actual product UI (Answer → fill → Save per question, one at a time, per
the page's own edit-guard). It fails because **gap-question generation is a
synchronous, LLM-backed call embedded inside the create-application request**,
and it intermittently:

- exceeds the API Gateway integration timeout (confirmed via network trace: a
  504 `DEFAULT_5XX` while the Lambda kept running and persisted its result
  minutes later), and, separately,
- sometimes doesn't complete at all within an 8-minute window, with nothing
  logged at ERROR level (CloudWatch shows `GapQuestionEmptyReads` firing
  repeatedly, no exception).

The failure UI has no working recovery: the page's `fetchQuestions` runs once
on mount; the empty-state branch it lands in (no questions found yet) only
offers "Back to Hub" — the `data-testid="retry-button"` Retry affordance exists
solely on a *different* branch (a genuine fetch error), which this case never
hits. `journey.spec.ts` currently just reload-polls for up to 8 minutes as a
workaround, which is honest (it does not weaken the assertion) but is not a
fix.

This is a real, standalone reliability problem worth its own investigation —
likely candidates: make gap-question generation genuinely async (the same
queue-based pattern `useGenerateModule` already uses for VPR/tailored-CV/
cover-letter/interview-prep — gap questions on create appears to be the one
remaining synchronous LLM call in the whole app), or at minimum give the
empty-state branch on `/gap-analysis` its own retry action instead of only
"Back to Hub". Don't guess at scope before looking at
`careervp/handlers/gap_handler.py::generate_questions` and how long the LLM
call inside it actually runs versus the ~29s API Gateway limit.

## Step 4 — Once J4 is unblocked, keep the loop going

The `PLAIN-PLAN.md` doc from two sessions ago (safe to skim now, since it's a
map of the remaining confirmed bugs mapped to journey steps) lists what's
likely to block J5 onward once J4 clears:

| Step | Confirmed bug (unverified against current code — recheck) |
|---|---|
| J5 | S7 — VPR quality-check failure silently serves generic filler as success |
| J5 | S25 — application status update always fails on an empty user_id |
| J7 | S8 — cover letters generate with no gap answers (wrong table lookup) |
| J6/J7 | S10, S11 — cancel reports success even when the underlying write fails |

Same discipline as before: one change, one `make journey`, read what actually
moved before touching the next thing.

## Step 5 — the rest of the freeze line

Once N is meaningfully higher and the P-05 suite + deploy gate are proven live
(not just committed), the 72-item launch checklist becomes workable with
instruments you have reason to trust. Not this session's job to start unless
Steps 1–4 are done and there's real time left.

## Ground rules (same as last time)

- Per `CLAUDE.md`, run the mandatory checks for every path you touch before
  each commit: backend `ruff format . && ruff check --fix . && mypy careervp
  --strict` and `pytest tests/unit/`; frontend `npm run typecheck && npm run
  test:unit`. Run `pytest tests/integration/` too for anything touching P-05
  files — that's precisely how the hollow suite survived undetected before.
- **Do not deploy.** Prepare change sets or push branches for review; a human
  executes and approves.
- One fix per commit, journey number before/after in the message where
  relevant.
- If a fix turns out bigger than described here (J4's async-generation
  question is the likely candidate), stop and report rather than redesigning
  unilaterally.
- If you find something new, write it down and keep going — this document
  itself is proof that pattern works.

## What success looks like

The four fixes reviewed, merged, and deployed by a human through the gate this
session closed; a higher journey number than 3, proven by a committed proof;
and J4's generation-reliability defect either fixed or scoped into a specific,
sized piece of follow-up work — not still an open question at the end of the
session.
