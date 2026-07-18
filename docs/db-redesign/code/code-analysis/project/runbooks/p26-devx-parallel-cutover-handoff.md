---
handoff_id: P-26-DEVX-CUTOVER
title: "Parallel -devx stack + human-gated cutover: replace CareerVpCrudDev's count-relief problem by deploying a fresh CareerVpCrudDevx with the P-26 nested-feature topology already built in, validating it, then cutting the stable custom domain over to it and decommissioning the old stack. Disposable dev data supersedes the resource-import approach."
status: draft
owner: infra
scope_lock_clause: P-26
supersedes: docs/db-redesign/code/code-analysis/project/runbooks/p26-job1-refactor-handoff.md
tooling:
  codex: {model: gpt-5-codex, reasoning: high}
  rationale: "Cross-stack DNS/domain cutover, multi-service coordination (infra + frontend + Cognito), several existing artifacts to review/retire. Lower blast radius than the original P-26 spec assumed, because dev data/users are now declared disposable — but the cutover mechanics (domain flip, decommission) are still real, human-gated, shared-state operations."
---

# Handoff — P-26 count relief via parallel `-devx` stack + cutover (NOT resource-import)

## 0. Read this first — the decision that changes everything

**Human decision (2026-07-18, this session):** `CareerVpCrudDev` is a **pre-launch, non-production
environment**. Its data and its ~908 user accounts are **disposable** — nothing in it needs to
survive a rebuild. Analogy given by the human operator: *"we are renovating the restaurant before
the big opening — we don't need to keep serving the old menu while we do it."*

This **replaces** the prior plan (careful in-place `cdk refactor` resource-import of 76 named
resources into `CrudFeatures`, preserving physical ids because live data/users could not be lost).
That prior plan is now **unnecessary complexity** — it existed only to avoid delete/create on live
data, and that constraint no longer applies to `dev`. **Do not resume the refactor-import path
without a new human decision reversing this one.**

**Standing rule for this repo (see `RUNBOOK-RULES.md`) applies here too: verify current state from
git + live commands before trusting anything in this document, including the "verified" facts
below — they were true as of 2026-07-18 but the branch moves fast.**

---

## 1. The new mechanism — this is NOT a new invention, it's P-26 Job 2 extended

`docs/db-redesign/code/code-analysis/project/specs/P-26-blue-green-api-spec.md` **already
specifies** a blue/green pattern for exactly this class of problem (§"Job 2 — Blue/green a NEW
RestApi"): stand up a new stack alongside the old, verify it on its raw invoke URL, then cut
traffic over by re-pointing the `BasePathMapping` on the **stable custom domain**
(`api.{env}.careervp.com`) — never by replacing the live resource in place. **Reuse this exact
cutover mechanism.** The only change from the existing spec: because dev data is disposable, you
are no longer limited to moving *just the RestApi* — the **whole stack** (tables, buckets, Cognito
pool included) can be freshly created in `-devx` and the old one retired, instead of preserving
Job 1's data-preserving nested-stack decomposition-in-place.

Read that spec's "Why this clause is uniquely dangerous," Job 0 (custom-domain stabilization / O-9),
and the AC-P26-5 acceptance criterion before writing code — its cutover discipline (new stack
verified on raw URL BEFORE any traffic flip; old stack stays live until proven; flip is human-only
P-28 `ExecuteChangeSet`) still applies. What no longer applies: AC-P26-1's "zero replacement of any
DynamoDB table/S3 bucket/Cognito pool" — that constraint was about *not losing live data*, which is
moot now for `dev`. **Amend the spec to say so explicitly for the `dev` environment only** — do not
silently weaken it for `staging`/`prod`, which are not covered by this disposable-data decision.

---

## 2. Verified blockers/wrinkles (confirmed by reading the code this session — re-verify, don't trust blindly)

1. **`_build_api_custom_domain()` will collide if you deploy devx the naive way.**
   `infra/careervp/api_construct.py:327-328` calls it unconditionally whenever
   `not is_production_env and not self.scratch_mode` — i.e. for ANY plain environment name,
   including `devx`. The method (`api_construct.py:346-372`) is **hardcoded**: fixed ACM cert ARN
   (`arn:aws:acm:us-east-1:788159322332:certificate/d93bafb3-...`) and fixed domain
   `api.dev.careervp.com`. A naive `ENVIRONMENT=devx cdk deploy` will try to claim a `DomainName` +
   `BasePathMapping` that the **live dev stack already owns** → deploy failure or resource
   contention. **You must parameterize this construct (domain name + cert per environment, or an
   explicit "don't claim the shared domain yet" flag) before devx can deploy at all.** Validate
   devx first on its raw `execute-api` invoke URL (or a throwaway subdomain), and only wire the
   **shared** `api.dev.careervp.com` `BasePathMapping` at cutover time (Job 6 below) — exactly as
   the existing blue/green spec already prescribes for RestApi-only cutovers.

2. **The existing scratch-deployment path is NOT usable for this** — don't reach for it.
   `infra/careervp/scratch_deployment.py` hard-locks `region == "eu-west-1"` (`SCRATCH_REGION`) and
   requires `environment` to match `^rto-euw1-[0-9]{8}(-[a-z0-9-]+)?$`. It's built for the P-64 RTO
   teardown-drill rig, not a semi-permanent `us-east-1` `-devx` replacement. Use the **plain**
   (non-scratch) `build_app` path with `ENVIRONMENT=devx`, after fixing blocker #1.

3. **Naming is safe.** `infra/careervp/naming_utils.py`'s `_normalize_environment` only special-cases
   `dev/staging/prod`; any other slug-able string (e.g. `devx`) passes through and produces fully
   distinct physical names (`careervp-auth-api-lambda-devx`, etc.) — **no collision** with `-dev`
   resources on Lambdas, tables, buckets, or queues. Account/region are pinned literals in
   `infra/app.py` (`788159322332` / `us-east-1`) regardless of environment name for the non-scratch
   path, so devx lands in the **same account + region** as live dev, as intended.

4. **Removal policy defaults to RETAIN + deletion/termination protection ON** for any non-scratch
   deploy (`infra/careervp/api_db_construct.py:59-64`, `infra/careervp/service_stack.py:56-62`).
   This is **correct to keep** for devx once it's meant to become the new permanent dev — but it
   means decommissioning the *old* `CareerVpCrudDev` later requires a **deliberate, human-gated**
   lift of P-27 termination protection (it exists specifically to prevent exactly this kind of
   whole-stack delete). Do not automate that lift.

5. **`deploy.yml`'s `STACK_NAME` derivation doesn't know about `devx`.**
   `.github/workflows/deploy.yml` (~line 266) only branches `prod`/`staging`/else-`dev` — a
   `devx` input would silently fall through to `CareerVpCrudDev`, targeting the **live** stack.
   **Do not reuse `deploy.yml` as-is.** Either add a real `devx` branch (temporary, removed after
   cutover) or write a bespoke one-off deploy path for this job. Same caution applies to
   `.github/workflows/deploy-frontend.yml`, whose `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_COGNITO_*`
   env vars (lines 26-31) are sourced from GitHub secrets with **live-dev values hardcoded as
   fallback defaults** — cutover requires updating those secrets (or the workflow) to devx's
   freshly-created Cognito pool id/client id/domain, not just the API URL.

6. **`infra/careervp/rehome_map.py` and the P-26 resource-import test become dead code under this
   plan.** They exist to preserve **already-deployed** physical names during a live move — devx
   creates everything fresh, parented into `CrudFeatures` from birth via the existing
   `p26_rehome_features` CDK context flag (`infra/careervp/api_construct.py:91-96`), so no
   import/rehome step is needed. Flag for retirement, don't blindly delete (see §5).

---

## 3. Ordered jobs

**Job 0 — Record the decision (do this FIRST, before any code change).**
Author a `project-scope-lock.yaml` amendment (this session's canonical tree file:
`docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml`, currently `v2.5.0`) stating:
(a) dev data/users are declared disposable pre-launch, scoped to `dev` only; (b) P-26 Job-1's
mechanism pivots from live resource-import to a parallel `-devx` blue/green stack + cutover,
extending the existing Job 2 blue/green pattern to the whole stack for `dev`. Get explicit human
sign-off on the amendment (`Scope-Lock-Approved-By:`) before proceeding — this repo's culture
requires that for any contract-level change, and this changes several invariants (AC-P26-1's
data-preservation guarantee, specifically, for `dev` only).

**Job 1 — Re-verify the O-9/custom-domain seam's current state.** Prior session notes (may be
stale — confirm live) describe O-9 (Cloudflare CNAME + ACM cert for `api.dev.careervp.com`) as "in
progress." Confirm current state with a live check before assuming the domain is a stable seam to
cut over onto.

**Job 2 — Parameterize `_build_api_custom_domain`.** Make the domain name + cert ARN
environment-aware (or gate the shared-domain claim behind an explicit "is this the currently-active
stack for this domain" flag), so devx can synthesize/deploy without touching `api.dev.careervp.com`
until Job 6. Add/adjust an infra test asserting devx does NOT claim the shared domain pre-cutover.

**Job 3 — Deploy `CareerVpCrudDevx`.** `ENVIRONMENT=devx`, same account/region, non-scratch path,
**`p26_rehome_features=true` set from the start** (so the 77-resource nested-stack topology is
built in from birth — no refactor/import needed). Use a bespoke deploy path, not unmodified
`deploy.yml` (see blocker #5). Validate on the raw `execute-api` invoke URL first.

**Job 4 — Verify count relief + run the relevant test suites against devx.**
Confirm devx's parent template resource count is well under 400 (expect ~295, matching this
session's flag-ON synth proof) and no template ≥ 500. Run
`src/backend/tests/infrastructure -k "p26 or p24 or identity_surrogate"` and
`infra/tests/infrastructure -k "p26 or nested_split or artifact_chain"` against the new deploy —
update any test that still assumes a live-resource-import shape (see §5).

**Job 5 — P-30 smoke against devx** (raw URL, then any temp domain used) — must be 4/4 green before
touching the shared custom domain.

**Job 6 — Human-gated cutover.** Re-point `api.dev.careervp.com`'s `BasePathMapping` from the old
RestApi/stage to devx's (reusing the exact mechanism `P-26-blue-green-api-spec.md` Job 2 already
specifies: base-path-mapping-only change, human `ExecuteChangeSet` per P-28). Then update
`deploy-frontend.yml`'s Cognito secrets to devx's new pool/client/domain/redirect values and
redeploy the frontend. Create/seed whatever test users devx's fresh Cognito pool needs. **Old
`CareerVpCrudDev` stays live and mapped until devx is proven in this step** — same discipline as
the existing spec, don't skip the "old stays up until new is verified" order.

**Job 7 — Decommission old `CareerVpCrudDev`** (human-gated, deliberate P-27 termination-protection
lift, only after Job 6 is confirmed stable) — tear down the old stack and its RETAIN'd stateful
resources now that devx is serving traffic.

**Job 8 (optional, flag for a separate human decision, do not auto-execute):** whether `-devx`
should eventually be renamed back to a plain `dev` naming scheme, or whether `devx` becomes the
permanent name. Out of scope for this handoff — just note the open question in the status ledger.

---

## 4. Artifacts to review/retire (superseded by this pivot — this session's own prior work)

These were built for the now-abandoned in-place resource-import approach. Review each: keep for
historical reference (they're a legitimate pattern for the day this problem recurs against *real*
prod data), but mark clearly as **superseded/inactive** for the current dev-count-relief effort —
don't let a future session assume they're the active path.

- `.github/workflows/p26-refactor.yml`
- `infra/scripts/p26_refactor_gate.py`
- `docs/evidence/p26-job1-refactor-override.json`
- `docs/evidence/p26-job1-refactor-prep-20260718.md`
- `docs/db-redesign/code/code-analysis/project/runbooks/p26-job1-refactor-handoff.md`
- `infra/careervp/rehome_map.py` (dead code under this plan — devx never imports, it creates fresh)
- `src/backend/tests/infrastructure/test_p26_job1_resource_import_outcomes.py` (tests the
  now-unused import mechanism — review whether any assertions still apply to a fresh-deploy shape,
  retire the rest)

## 5. Docs/specs/status to update

- `docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml` — the Job 0 amendment.
- `docs/db-redesign/code/code-analysis/project/specs/P-26-blue-green-api-spec.md` — extend Job
  1/Job 2 language to cover the whole-stack `dev`-only disposable-data case; do not touch its
  staging/prod guarantees.
- `docs/db-redesign/code/code-analysis/project/runbooks/wave-1-status.md` — rows 1.3d and 1.4:
  replace the resource-import narrative with the devx-cutover plan and its actual progress.
- `.github/workflows/deploy.yml`, `.github/workflows/deploy-frontend.yml` — devx support or a
  clearly-scoped bespoke replacement, removed after cutover.
- `docs/db-redesign/code/code-analysis/project/runbooks/p28-human-gated-deploy-runbook.md` — note
  whether the devx cutover needs its own required-reviewer environment or reuses `deploy-dev`.
- Any infra test asserting the shared custom domain is claimed only by the currently-active stack
  (new test from Job 2).

## 6. STOP conditions (human review required, do not auto-proceed past these)

- Job 6 (domain flip) or Job 7 (old-stack decommission) run without explicit human approval of that
  specific step.
- devx has NOT passed Job 5 (P-30 smoke) before Job 6 begins.
- Job 2's parameterization accidentally causes devx to claim `api.dev.careervp.com` before cutover
  (verify via `cdk diff`/`cdk synth` against live BEFORE devx's first deploy).
- The scope-lock amendment (Job 0) is not committed/approved before Job 2 onward begins.
- Any staging/prod spec language gets weakened as a side effect of the `dev`-only amendment.
