# Post-Wave-2 — Amplify → CDK, and streamlining deployments

**Status:** DRAFT runbook, authored 2026-07-26. Not a Wave-2 step. Runs AFTER the Wave-2 GATE passes.
Follows `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md`
(the seventeen standing rules) — same rigor: full absolute paths, RED-first where code changes,
human-gated deploys, every bet and every deferral written with a stopping condition.

**Who this is for.** The single human deployer (you). The goal you set: *bring the frontend under
CDK so its config cannot silently drift from the backend, and remove manual deploy steps wherever
possible — without risking the 908 live users on the old stack.*

---

## §0 — The live reality this runbook must respect (read first, re-verify before acting)

Everything here was read from source/live on 2026-07-26. Re-confirm each before you touch anything —
this is exactly the out-of-band state the project keeps getting burned by.

1. **There are TWO separate frontend-hosting stories, and only one is live for db-redesign.**
   - **Console-managed AWS Amplify app `d3j2wnm8g5clnw`** — this is what actually serves the
     `db-redesign` branch. It builds on git push via Amplify's own git integration. Its per-branch
     env vars (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_COGNITO_USER_POOL_ID`, …) are **set by hand in the
     console** and are NOT in any repo file. Verified: `grep -rn "amplify" ` over
     `/Users/yitzchak/Documents/dev/careervp/infra/careervp/` finds only CORS-origin strings, never a
     `CfnApp`/`CfnBranch`/`aws_amplify` construct.
   - **CDK `FrontendStack`** at
     `/Users/yitzchak/Documents/dev/careervp/infra/careervp/frontend_stack.py` — manages a DIFFERENT
     path: CloudFront + S3 + ACM + Route53 (line 1 docstring). It does not manage Amplify at all. Do
     not assume editing `FrontendStack` changes what db-redesign users see — today it does not.

2. **The Amplify branch env is drift-prone by construction.** Because it lives only in the console,
   anyone selecting "use app defaults" reverts `db-redesign` to the APP-level defaults, which are
   still the OLD dev pool / `api.dev.careervp.com`. The current correct live values (verify with
   `aws amplify get-branch --app-id d3j2wnm8g5clnw --branch-name db-redesign`):
   - `NEXT_PUBLIC_API_URL` = the devx raw invoke URL
     `https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/`
   - `NEXT_PUBLIC_COGNITO_USER_POOL_ID` = `us-east-1_bAZ6jb6HP` (devx pool)

3. **The API URL is baked at BUILD time.** Next.js inlines `NEXT_PUBLIC_*` at build. So changing an
   env var — by hand or by CDK — does nothing until a rebuild runs. Any streamlining that "sets env
   from CDK" is only half a fix unless a rebuild is also triggered.

4. **O-9: the frontend CI deploy pipeline is BROKEN and has been since 2026-05-03.**
   `/Users/yitzchak/Documents/dev/careervp/.github/workflows/deploy-frontend.yml` is **validate-only**
   (`validate-amplify-build` job; push to `main`; it builds but never calls `aws amplify start-job`),
   and its fallback env values point at the OLD dev pool (`us-east-1_WiHMRqLpe`,
   `https://api.dev.careervp.com`). Nothing here auto-deploys Amplify today.

5. **The backend `main`-push path still targets the OLD stack.**
   `/Users/yitzchak/Documents/dev/careervp/.github/workflows/deploy.yml:37` hardcodes
   `STACK_NAME: 'CareerVpCrudDev'`. Only the `workflow_dispatch` path resolves to `CareerVpCrudDevx`
   (line 279), gated by the GitHub `devx` environment's required reviewer. This is B-2-4's open item.

6. **The IMMUTABLE laws still bind.** Never move the live RestApi (a cross-stack move is delete+create
   → invoke URL changes → the Amplify FE, which bakes `NEXT_PUBLIC_API_URL` at build, dies for 908
   users). Never move the Cognito user pool (unrecoverable loss of 908 users). The P-26 blue/green
   lesson applies to Amplify too: **importing a live resource wrong = deleting it.**

---

## §1 — What "streamlined" means here, ranked by payoff-over-risk

Two independent goals. Do them in this order; each earlier one de-risks the next.

| # | Manual step to remove | Mechanism | Risk | Prereq |
|---|---|---|---|---|
| A | Backend devx deploy needs `workflow_dispatch` + change-set approval | Auto-deploy `CareerVpCrudDevx` on push to `db-redesign`; keep the gate for staging/prod | LOW (devx is disposable) | §2 (fix deploy.yml:37) |
| B | FE env vars set by hand; drift reverts to dev pool | Bring the Amplify **branch** under CDK with env wired FROM backend stack outputs | MED–HIGH (resource import of a live app) | O-9 fixed; A landed |
| C | FE rebuild triggered by hand | `aws amplify start-job` in CI on backend-output change | LOW once O-9 fixed | O-9 fixed |

**Recommendation:** ship **§2 → A → C first** (all low risk, big toil reduction), and treat **B**
(true Amplify-in-CDK) as a deliberate, separately-gated migration — not because it is wrong, but
because importing the app that serves live users is the highest-blast-radius move in this document and
must not ride along casually.

---

## §2 — Prerequisite fixes (do these before any auto-deploy)

Neither is optional; auto-deploy on a mis-targeted pipeline is worse than manual deploy.

**§2.1 — Repair the backend `main`/dispatch stack targeting (B-2-4).** Make the deploy workflow's
default and `main`-push path resolve to the intended stack explicitly, never fall back to
`CareerVpCrudDev`. Change `/Users/yitzchak/Documents/dev/careervp/.github/workflows/deploy.yml:37` so
the old-stack literal is not the ambient default; keep the fail-closed "Validate resolved stack name"
step (line 281) as the backstop. Done-when: a dry-run of every trigger path prints the stack it will
touch and none silently resolves to `CareerVpCrudDev`.

**§2.2 — Fix O-9 (the FE CI pipeline).** Make
`/Users/yitzchak/Documents/dev/careervp/.github/workflows/deploy-frontend.yml` either actually deploy
(call `aws amplify start-job --app-id d3j2wnm8g5clnw --branch-name <branch> --job-type RELEASE`) or be
deleted in favor of the §C job below. Remove the stale dev-pool fallback literals (lines 26–31) — a
deploy pipeline must never carry a silent wrong-pool default. Done-when: a push to the target branch
produces a real, green Amplify build whose baked env matches the intended pool, verified in the built
artifact, not just a passing job.

---

## §A — Auto-deploy the devx BACKEND on push (keep staging/prod gated)

**Plain English.** devx is a disposable pre-launch environment. Requiring a manual dispatch + human
change-set approval for every devx backend change is toil with little safety payoff *for devx*. Add a
push-triggered job that creates AND executes the change-set against `CareerVpCrudDevx` automatically,
while leaving the human `environment:` approval in place for `staging`/`prod`.

**How.** In `/Users/yitzchak/Documents/dev/careervp/.github/workflows/deploy.yml`, add a job that
runs on `push` to `db-redesign`, resolves `STACK_NAME=CareerVpCrudDevx` through the SAME ternary +
validate-name backstop the dispatch path uses (lines 279–287), and executes the change-set WITHOUT the
`environment: ${{ inputs.environment }}` gate — but ONLY when the resolved stack is `CareerVpCrudDevx`.
Guard it so it can never execute against staging/prod.

**Safety invariants (rule-5 stop if any cannot hold):** the IMMUTABLE laws (no RestApi move, no
Cognito move) are enforced by `cdk diff` showing zero stateful replacement BEFORE execute — keep the
existing "create-change-set never overwrites, execute is a separate step" shape; auto-execute may only
skip the *human* gate, never the *zero-replacement* check. If a devx change-set ever shows a
stateful replacement, the auto path must FAIL CLOSED and fall back to manual review.

**Done-when.** A push to `db-redesign` deploys `CareerVpCrudDevx` end-to-end with no human click, the
post-deploy `tests/aws_cli_smoke.sh devx` stays green, and an attempted staging/prod resolution on that
job path is refused.

**Deferral / stopping condition (rule 10):** if auto-execute cannot be made to fail-closed on
stateful replacement by the end of the first implementation session, SHIP the smaller thing —
auto-*create* the change-set on push, leave *execute* as the one manual click — and record that here
with the date. Never ship an auto-execute that cannot prove zero replacement.

---

## §C — Auto-trigger the FE rebuild when the backend outputs change

**Plain English.** Once the backend deploys automatically, the FE still needs a rebuild to bake the
current API URL / pool id. Automate that so the two never drift.

**How.** After a successful devx backend deploy (or on the same push), a CI step reads the deployed
stack outputs (API invoke URL, Cognito pool id) and calls
`aws amplify start-job --app-id d3j2wnm8g5clnw --branch-name db-redesign --job-type RELEASE`, having
first ensured the branch env matches those outputs (see §B — until §B lands, this step must SET the
env from the outputs via `aws amplify update-branch` before starting the job, so a manual console value
can't win). Done-when: a backend output change results in a rebuilt FE whose baked `NEXT_PUBLIC_API_URL`
equals the just-deployed devx invoke URL, with no human step.

**Bet B-PW2-1.** *Belief:* the devx invoke URL is stable across devx redeploys (so baking it is safe).
*Cheapest check:* read `aws apigateway get-rest-apis` / the stack output twice across a redeploy and
compare — a live-state read, no build. *Fallback:* if the URL is NOT stable, move the FE onto the
custom domain first (the P-26 custom-domain slice) so the baked value is a stable hostname, and bake
that instead.

---

## §B — Bring the Amplify BRANCH under CDK (the durable drift-kill; highest blast radius)

This is the real "Amplify → CDK." It is worth doing because it makes FE-env drift **structurally
impossible** — the branch env vars become CDK-managed values sourced from the backend stack's own
outputs, so "use app defaults" can no longer revert the pool. But it imports a resource that serves
live users, so it is gated on its own.

**Three ways to get there — pick with eyes open:**

| Option | What it does | Pro | Con / risk |
|---|---|---|---|
| **B-1 Import** | `CfnApp`/`CfnBranch` (or `aws_amplify_alpha.App`/`Branch`) that `cdk import`s the EXISTING app `d3j2wnm8g5clnw` + `db-redesign` branch | Keeps the app id, domain, history; no repoint | Resource-import of a live app; a mis-mapped import = delete+recreate = FE outage. Same danger class as P-26 Job-1. |
| **B-2 New app, blue/green** | Define a FRESH CDK-managed Amplify app; cut `db-redesign` over to it | Clean isolation, no import risk to the live app | New app id + default domain → a repoint + a rebuild; two apps to reconcile during cutover |
| **B-3 Abandon Amplify** | Serve the FE from the CDK `FrontendStack` (CloudFront+S3) that already exists, retire Amplify | One frontend story, fully in CDK | Largest change; loses Amplify's build integration; needs a build/publish pipeline to S3 |

**Recommendation:** **B-1 for devx-scope first, staged like P-26.** Prove the import on a
throwaway/non-prod branch (or a copy) with `cdk import` + `cdk diff` showing ZERO changes to the live
branch's settings before you touch the real one. Only then import `db-redesign`. Wire env from stack
outputs so the values are CDK-owned. Do NOT import the app in the same session that changes its env —
import first, prove zero-diff, THEN change env as a separate reviewed step.

**Hard gates (any failure = STOP, human review, no silent proceed):**
- `cdk import` dry-run/diff must show ZERO property change to the live branch before adoption. A
  non-zero diff means the CDK definition does not match live — fix the definition, never the live app.
- The imported definition must reproduce the CURRENT correct env (devx URL + `us-east-1_bAZ6jb6HP`)
  byte-for-byte before any change is layered on.
- Termination/deletion protection semantics for the app must be set so a `cdk destroy` or a failed
  update cannot delete the live app (mirror the P-27 termination-protection posture on the stack that
  owns it).

**Bet B-PW2-2.** *Belief:* the existing console Amplify app can be `cdk import`ed without a
delete+recreate. *Cheapest check:* `cdk import` a NON-prod branch / a scratch copy and read the diff —
no live change made. *Fallback:* if import forces replacement, go **B-2** (new CDK app, blue/green
repoint) — never force the import on the live app.

**Deferral / stopping condition (rule 10):** if B is not landed by the time paid launch is scheduled,
the SMALLER shipped thing is §C's "set env from outputs before every build" — it does not make drift
structurally impossible, but it makes every deploy overwrite any manual drift, which is enough to
launch on. Record the date and which fallback shipped.

---

## §D — Bets and stopping conditions (consolidated; mirror into ISSUES.md before executing)

| Bet | Belief | Cheapest check | Fallback |
|---|---|---|---|
| B-PW2-1 | devx invoke URL is stable across redeploys | read the stack output twice across a redeploy | move FE to the custom domain first, bake the hostname |
| B-PW2-2 | the console Amplify app imports into CDK without replacement | `cdk import` a scratch/non-prod branch, read the diff | B-2 new CDK app + blue/green repoint |
| B-PW2-3 | skipping the human gate for devx backend is safe | devx is disposable + zero-replacement check holds | auto-create change-set only, keep manual execute |

**Stopping conditions (observable, per rule 10):**
- §A: if fail-closed-on-replacement is not provable in the first session → ship auto-create-only.
- §B: if not landed before paid-launch scheduling → ship §C env-overwrite-on-build instead.
- §C: if the invoke URL proves unstable → block on the custom-domain slice, do not bake a raw URL.

---

## §E — What this runbook explicitly does NOT authorize

- Touching the live RestApi or the Cognito user pool in any way (IMMUTABLE laws).
- Importing or repointing the Amplify app that serves the OLD `CareerVpCrudDev` / 908 live users as a
  side effect of devx work.
- Removing the human `environment:` approval for `staging` or `prod` deploys. §A's auto-deploy is
  **devx-only** and must refuse any other resolved stack.
- Any change that lands without the RED-first / zero-replacement / human-gate discipline the rest of
  the db-redesign work uses.
