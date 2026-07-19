# Wave 1 — Handoff, 2026-07-19

**Read this after `wave-1-status.md`, not instead of it.** This file is a priority-ordered
execution plan built from that ledger's current state (all rows verified against git + a live
`cdk diff`/CloudFormation change set this session). It does not replace the ledger's standing
rules — see `RUNBOOK-RULES.md` — every step below still opens with its own STANDING CHECK.

---

## 0. FIRST: correct a stale, wrong claim already in the ledger

**Do this before anything else below — it affects whether you trust any other row.**

`wave-1-status.md`'s "Deploy-state reconciliation (2026-07-18)" section (near the bottom of the
file) claims a flag-OFF `cdk diff CareerVpCrudDev` showed **"zero substantive changes"** and that
P-06/P-08/P-10/P-11/P-23 are **already deployed** to live dev.

**This is contradicted by fresher, stronger evidence from 2026-07-19 (this session):**
- A real CloudFormation change set was formed against live `CareerVpCrudDev` (not just `cdk diff`'s
  string heuristic) — **523 changes**, `auto_fail: false`, saved at
  `docs/evidence/p26-o9-changeset-review-20260719.json` /
  `docs/evidence/p26-o9-replacement-report-20260719.json`.
- A plain `cdk diff CareerVpCrudDev` re-run just now (2026-07-19) shows **470 diff lines** (139
  resource creates, 42 deletes, many `[~]` modifies), not the "owner-tag/asset-hash noise only"
  the 07-18 note describes.
- The diff includes the P-06 JWT/webhook env-var renames, P-08/P-10 CORS changes, the P-11 WAF
  WebACL, P-23's canary CodeDeploy infra, P-24's identity-map table, and P-32's budgets — i.e.
  **none of this is live yet**, despite each clause's own wave-1-status row saying "Done."

**"Done" in every row above means "done in the repo," not "deployed."** That distinction was
always technically true per each row's wording, but the 07-18 reconciliation note asserted the
stronger, false claim that it was *also* live. Correct that note in place (add a dated
`**CORRECTION 2026-07-19:**` block immediately under it — do not delete the original, this repo's
convention is to preserve the history and layer corrections on top, same as O-9's reopening).
Do not spend time root-causing *why* the 07-18 note was wrong (different flags, misread output,
stale `cdk.out`) unless it recurs — flag it, correct it, move on.

---

## 1. HIGHEST PRIORITY — human executes the prepared O-9/P-26 change set

**Type:** human-only (P-28 `ExecuteChangeSet` gate). **Blocks:** 1.3d, 1.4, GATE. **Unblocks the
most work of anything on this list.**

This is a single deploy that lands O-9 (the `api.dev.careervp.com` domain fix) bundled with
everything else already sitting in the repo unreleased: P-06, P-08, P-10, P-11, P-23, P-24, P-32.
It has already been proven safe:

- Reviewed change set: 523 changes, **zero** `AWS::ApiGateway::RestApi`/`DynamoDB::Table`/
  `S3::Bucket`/`Cognito::UserPool` replacements. Only 6 `Replacement:True` entries, all
  `AWS::Lambda::Permission` (non-protected swagger-route churn).
- Evidence: `docs/evidence/p26-o9-changeset-review-20260719.json` (raw `describe-change-set`) and
  `docs/evidence/p26-o9-replacement-report-20260719.json` (the P-28 auto-fail verdict).

**Steps for the human:**
1. Read the two evidence files above (or re-run the review yourself — the previous review-only
   change set was deleted after evidence capture, so a fresh one must be created to execute):
   ```
   cd infra
   cdk deploy CareerVpCrudDev --no-execute --change-set-name p26-o9-execute-<date>
   aws cloudformation describe-change-set --stack-name CareerVpCrudDev \
     --change-set-name p26-o9-execute-<date> > /tmp/changeset.json
   python3 ../scripts/ci/changeset_replacement_report.py --changeset /tmp/changeset.json
   ```
2. Confirm `auto_fail: false` again on the fresh change set (state can drift between review and
   execute if anything else lands on `main`/`db-redesign` in between — re-check, don't trust the
   07-19 evidence blindly if time has passed).
3. Execute:
   ```
   aws cloudformation execute-change-set --stack-name CareerVpCrudDev \
     --change-set-name p26-o9-execute-<date>
   aws cloudformation wait stack-update-complete --stack-name CareerVpCrudDev
   ```
4. Verify O-9 live: `dig +short api.dev.careervp.com` should resolve; confirm
   `aws apigateway get-domain-name --domain-name api.dev.careervp.com` now returns the resource
   (it currently 404s — that's exactly what this deploy fixes).
5. Re-run P-30 4-wire smoke against `https://api.dev.careervp.com` (health, CORS preflight, authed
   read, authed upload) — must be 4/4 green, matching the pre-deploy baseline.
6. Update `wave-1-status.md` row 1.3d: mark the domain fix as **human-executed and live-verified**,
   with the real commit/execution evidence (change-set id, `wait` completion, P-30 results).

**Do not skip step 2.** State can have moved since the 07-19 review.

---

## 2. AGENT-ACTIONABLE NOW, PARALLEL-SAFE — fix the devx domain-claim code gap

**Type:** code + test, no deploy, no AWS mutation required. **Can start immediately, independent
of #1** (it doesn't touch `CareerVpCrudDev`'s own synthesized template — see why below).

`_build_api_custom_domain()` (`api_construct.py:346-371`) is hardcoded to
`domain_name="api.dev.careervp.com"` and invoked whenever `not is_production_env and not
self.scratch_mode` — which is true for **any** non-prod, non-scratch environment string, including
a future `ENVIRONMENT=devx`. Unfixed, creating `CareerVpCrudDevx` would try to claim the same
globally-unique API Gateway custom domain name `CareerVpCrudDev` already owns, and fail at deploy
time exactly like the orphaned-table conflict found this session.

**The fix is scoped narrowly enough to be safe to land right now, before or after #1:** gate the
call to only fire when `self.naming.environment == "dev"` (the literal reserved name), not merely
"not production and not scratch." For the existing `CareerVpCrudDev` stack, `self.naming.environment`
is already `"dev"`, so this change produces **zero diff** for that stack — safe to land independent
of whether #1 has executed yet.

**Steps:**
1. RED test first (spec already describes it —
   `specs/P-26-blue-green-api-spec.md`, `test_devx_does_not_claim_shared_domain_before_cutover`,
   AC-P26-9): synth with `ENVIRONMENT=devx`, assert no `AWS::ApiGateway::DomainName`/
   `BasePathMapping` in that template names `api.dev.careervp.com`; synth with `ENVIRONMENT=dev`
   as a positive control and assert it still owns that pair.
2. Confirm the test fails against current code (devx synth today claims the domain — this should
   error or, worse, silently produce a conflicting resource).
3. Add the `self.naming.environment == "dev"` guard (or equivalent) to
   `api_construct.py:327-328`.
4. Confirm the RED test goes GREEN, and re-run `cdk diff CareerVpCrudDev` to confirm **zero**
   change for the existing dev stack (this fix must be a no-op for `dev`).
5. `ruff format`/`ruff check --fix`/`mypy --strict`, naming validator.
6. Commit. Update `wave-1-status.md` row 1.3d with this sub-step's completion — it is a
   precondition for step 3 below, independent of whether #1 has landed yet.

---

## 3. AGENT-ACTIONABLE, AFTER #1 LANDS LIVE — prepare the devx creation change set

**Type:** code + review-only change set, no execution. **Deps:** #1 executed and live-verified
(the standing rule already in `wave-1-status.md` row 1.3d: "do not create/implement
`CareerVpCrudDevx` until [the domain] seam is restored and verified live"), #2 landed.

1. STANDING CHECK: confirm #1's row shows human-executed + live-verified, and #2's domain-claim
   guard is committed. If either is missing, STOP.
2. `ENVIRONMENT=devx cdk synth -c p26_rehome_features=true` — clean synth, distinct stack id from
   `CareerVpCrudDev` (verify via `naming_utils.py`, don't assume).
3. Form a review-only change set for the devx stack creation
   (`cdk deploy CareerVpCrudDevx --no-execute --change-set-name devx-review-<date>`), same
   pattern as #1's evidence capture: `describe-change-set` → `changeset_replacement_report.py` →
   confirm `auto_fail: false` → delete the review-only change set → confirm via `describe-stacks`
   that nothing executed.
4. Hand the prepared change set + Replacement report + domain-claim test result to the human.
5. Update `wave-1-status.md` row 1.3d.

**Do not execute this change set yourself.** Base-path flip and old-stack decommission are
separate, later, human-only steps (see `specs/P-26-blue-green-api-spec.md` Job 2 and
`runbooks/p28-human-gated-deploy-runbook.md` §5) — out of scope here.

---

## 4. HUMAN-ONLY, AFTER #3 — execute devx creation

1. Review the prepared change set + Replacement report from #3.
2. `aws cloudformation execute-change-set ...` for the devx stack.
3. P-30 4-wire smoke against devx's own **raw invoke URL** (not the shared custom domain — devx
   doesn't own it yet, by design of the domain-claim gate).
4. Update `wave-1-status.md` row 1.3d: devx live, smoke-tested.

---

## 5. AGENT-ACTIONABLE, AFTER #4 — assess and start P-09 (1.4)

**Deps:** 1.3d fully landed (devx live + smoke green). `wave-1-prompts.md` Prompt 1.4 governs
this — read it fresh; it was not touched this session and its content (one IAM role per function,
`api_construct.py:516-821`) is still accurate. Assess devx's actual resource count first (the
whole point of the devx path was CFN-limit relief) before starting the IAM-role work.

---

## 6. TIME-GATED, NO ACTION POSSIBLE YET — 1.1 (P-04/P-05) waits on the P-07 soak

The P-07 SPA auth-code+PKCE migration window opened **2026-07-18** and requires soaking for **at
least the 30-day refresh-token lifetime** before implicit grant + `COGNITO_ADMIN` can be removed
and MFA enforced. That puts the earliest safe start for 1.1 around **2026-08-17**. Nothing to
execute here — just don't start 1.1 before that date, and don't let anyone (agent or human)
short-circuit the soak because 1.1 looks like "the next spine item alphabetically." The ledger's
own row 1.3c already states this explicitly; this entry exists so it isn't missed in a
priority-ordered read of this handoff.

---

## 7. LAST — Wave-1 GATE

Only after 1.0, 1.3a, 1.3b, 1.3c (soak complete), 1.3c-gate, 1.3d, 1.4, 1.5, and 1.1 all show a
landed status with no open problem. Follow `wave-1-prompts.md`'s "Wave-1 GATE" section verbatim —
it already has its own STANDING CHECK and adjudication instructions; nothing here supersedes it.

---

## Priority order, summarized

1. Correct the stale deploy-state claim in `wave-1-status.md` (5 minutes, prevents future
   confusion).
2. Human executes the O-9/P-26 change set (highest leverage — unblocks 1.3d/1.4/GATE).
3. Agent fixes the devx domain-claim code gap (parallel-safe, no deploy needed).
4. Agent prepares the devx creation change set (after #2 is live).
5. Human executes devx creation.
6. Agent starts P-09 against devx.
7. *(parallel, no action)* Wait for the P-07 soak (~2026-08-17) before touching 1.1.
8. GATE, once everything above is clean.
