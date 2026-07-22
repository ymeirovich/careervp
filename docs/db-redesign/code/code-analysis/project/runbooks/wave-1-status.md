# Wave 1 — Status Ledger

**Read this file FIRST before starting any Wave-1 prompt.** `wave-1-prompts.md` describes what
*should* happen; this file describes what *actually* happened, and is what every prompt checks
before starting its own work (see `RUNBOOK-RULES.md`, rules 2–3). Update your own row when you
finish a step or stop on a problem — do not leave this file stale for the next session to trip
over.

Rows are listed in dependency order. Before starting a step, read the row above it (or the rows
it depends on per `wave-1-prompts.md` §2) — if any of them show an open problem, resolve that
first.

| Step | Clause(s) | Status (plain English) | Open problem for the next step | Commit | Date |
|---|---|---|---|---|---|
| 1.0 | P-23 | Done: P-23 canary rollback code/tests are present in git, and the owner-tag replacement blocker was resolved by stable per-resource owner tags. | none | `3bb5446` | 2026-07-18 |
| 1.3c-gate | P-11 (enable WAF in all envs) | Done: removed the production-only WAF gate, so dev/non-production stacks now synthesize a WAF WebACL without changing WAF rule content. RED test failed first against the old gate, then passed after the gate removal. | None for the next spine step. Lane P2 Prompt 1.3c depends on this and can now land rate-rule content in `waf_construct.py`. | pending commit: `fix(infra): enable API WAF in all environments for P-11` | 2026-07-18 |
| 1.3c | P-07, P-11 (rate-rule content) | Migration-window implementation complete locally, not deployed: the SPA now starts authorization-code + S256 PKCE, code and implicit coexist, Cognito Plus threat protection is enabled, MFA is OPTIONAL with a settings-page TOTP enrollment grace flow, the 401 refresh-once contract stays green, and every env has an API-associated IP rate rule (dev 2000, staging 1500, prod 1000 requests per five minutes). No user-pool move or stateful replacement is proposed. | migration window OPEN — implicit and COGNITO_ADMIN are still enabled because browser-side password change and TOTP enrollment require the scope. Move both flows behind an approved backend auth service, deploy the PKCE frontend, soak for at least the 30-day refresh-token lifetime, then remove implicit + COGNITO_ADMIN and enforce MFA. 1.1 (P-04) MUST NOT START until that soak completes. Human review must also account for the unrelated owner-tag drift in the dev diff. | pending (see commit message in session output) | 2026-07-18 |
| 1.3a | P-08 | Done: CV and VPR-results ("generated") bucket S3 CORS wildcard origins replaced with explicit per-env origins (localhost only for dev). RED test written first, confirmed failing against the old wildcard code, then GREEN after the fix. `cdk diff` shows both buckets as in-place property updates only (`[~]`), zero replacement. | None for 1.3b itself, but see note: the prompt's cited evidence locations (`api_db_construct.py:184,561`, `s3_stack.py:40,63`, `frontend_stack.py:48`) were stale — `s3_stack.py` does not exist and `frontend_stack.py:48` already had an explicit (non-wildcard) origin, so it was correctly left untouched. The two real S3-CORS-with-wildcard sites were `api_db_construct.py:253` (CV bucket) and `api_db_construct.py:653-657` (VPR results bucket, which had a `https://*.amplifyapp.com` wildcard subdomain, not `"*"`). Scope/intent still matches the P-08 clause and spec; flagging the stale citations for whoever writes the next wave-prompt file. | pending (see commit message in session output) | 2026-07-18 |
| 1.3b | P-10 | Done: API Gateway default (success-path) CORS replaced `Cors.ALL_ORIGINS` with the env allow-list (`self.allowed_origins.split(",")`), rendering CDK's dynamic per-origin VTL echo (`Vary: Origin` + origin-match template) instead of a static `'*'`. `max_age` set to 60s. `GatewayResponse` (401/403/4xx/5xx) wildcard left untouched and is now asserted as a codified exception by both the new infra test and the un-poisoned frontend regression test. `cdk diff` against deployed dev: 5 stacks with drift, all pre-existing owner-tag noise or the expected OPTIONS-method/Deployment/Stage churn from the CORS definition change (Lambda `Version`/API `Deployment` are inherently hash-rotated, not stateful); **zero `[!]` replacement markers**, S3/DynamoDB/Cognito/RestApi all show in-place `[~]` only. P-30 precondition re-verified live (not just trusted from the Jul-17 evidence file): `GET /health` → 200, `OPTIONS /users/me` preflight → 204, both matching the stored evidence; did not re-run the full authenticated-upload wire live to avoid writing test data. `scope-diff.py` now reports P-10 `implemented`. | **Flag for human review (not blocking, but a real process violation):** a concurrent commit (`2513ee6`, titled "ci: use OIDC for cdk diff workflow", nominally step 1.5/P-22) also edited `infra/careervp/api_construct.py` — it made the identical `max_age: Duration.hours(1) -> Duration.seconds(60)` edit this prompt was told to make first. It converged harmlessly (same line, same target value, no conflict), but it violates this file's own standing note below ("`api_construct.py` is edited by most of these steps — never run two steps that touch it at the same time"). No code fix needed, but whoever runs 1.5/P-22 next should confirm that commit's scope was intentional and not a cross-contamination of prompts. Inverse (rollback) patch staged at `docs/evidence/p10-cors-cutover/inverse-changeset.patch` (verified `git apply --check` clean; reverts to `Cors.ALL_ORIGINS`). | pending (see commit message in session output) | 2026-07-18 |
| 1.2 | P-06 | Done: JWT private/public key env vars (6 Lambda sites) and payment-provider webhook secret env vars (billing Lambda) now carry only the SSM parameter *name* (`JWT_PRIVATE_KEY_SSM_PARAM`/`JWT_PUBLIC_KEY_SSM_PARAM`/`PAYMENT_PROVIDER_WEBHOOK_SECRET_SSM_PARAM`/`_PREVIOUS_SSM_PARAM`), never a CloudFormation-resolved value. Added a shared cached runtime secret provider (`careervp.logic.utils.secret_provider.get_ssm_secret`, `lru_cache`-scoped to the execution environment, `WithDecryption=True`, logs only the parameter name never the value) and wired it into `AuthService.from_env()` (JWT keys, with `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY` direct-value env vars kept as a local/test fallback, mirroring the existing `llm_client.py` Anthropic-key convention) and `billing_handler._get_webhook_service()` (webhook secrets, no existing tests depended on the old env var so no fallback needed). Added ARN-scoped `ssm:GetParameter` IAM grants: extended the shared `lambda_role`'s existing `ssm_parameters` policy to cover the two JWT parameter ARNs (covers CV Parser/Auth/User/Job/Authorizer Lambdas), plus one dedicated grant each for `CvUploadWorkerLambda` and `BillingLambda` (both have their own auto-generated roles, not the shared one). RED tests written first (`test_p06_secrets_hardening.py` ×3 infra + `test_p06_secret_provider.py` ×3 unit, citing AC-P06-1..3), confirmed failing against the pre-fix code (verified via `git stash` round-trip — 3/3 infra RED, unit RED via ImportError before the module existed), then GREEN after the fix. `cdk synth`/`cdk diff CareerVpCrudDev` clean: **zero `[!]` replacement markers** across all 5 stacks; diff shows only the 6 expected env-var renames, 3 new ARN-scoped IAM statements, 4 obsolete `SsmParameterValue...Parameter` CFN Parameters removed, and the pre-existing owner-tag drift noise (unrelated, already flagged by the 1.3b row). Full `pytest tests/unit` (1352 passed) and `tests/infrastructure` (48 passed) show no regressions. ruff/mypy --strict clean. Naming validator exit 0. `scope-diff.py` now reports P-06 `implemented` (after setting `impl_state: implemented` in `project-scope-lock.yaml`, same lightweight bookkeeping pattern P-08/P-10 used — no version bump, since this records status not a clause-definition change). Coverage: report-only per the two-phase gate; unchanged by this work (core branch 52.94% vs the 53.00% enforced_baseline was already failing on `main` before this change — confirmed by re-running `check_coverage_gates.py` against the pre-P-06 tree, identical failure, not introduced here). | **Flag for human review (non-blocking, spec-evidence correction, not a scope mismatch):** `specs/P-06-secrets-spec.md`'s Evidence section claims `api_construct.py:2569-2573` already sets webhook secret env vars "to SSM parameter names, which is the desired non-secret pattern" — that citation is stale/wrong. The actual pre-fix code called `self._parameter_value(...)`, which resolves the *live secret value* via a CloudFormation `value_for_string_parameter` dynamic reference, identical to the JWT anti-pattern, not a name-only reference. This did not change scope: the spec's own Fix Plan step 1 already listed "payment-provider webhook secrets" alongside JWT keys as needing the fix, so webhook secrets were fixed as part of this step exactly as planned — only the Evidence section's "already correct" claim was incorrect. Flagging per the same stale-citation precedent as the 1.3a row. | pending (see commit message in session output) | 2026-07-18 |
| 1.3d | P-26 Job-1 | **O-9 fix human-executed and live-verified.** `project-scope-lock.yaml`/`.md` at v2.6.0 (commit `3bbb963`); spec/runbook docs updated (commit `443dabe`). Investigated O-9: `_build_api_custom_domain()` (`api_construct.py:346-371`) already creates the `api.dev.careervp.com` `DomainName`+`BasePathMapping`, unconditionally invoked for non-prod/non-scratch — no new code needed. Created a review-only CloudFormation change set (`cdk deploy CareerVpCrudDev --no-execute`, name `p26-o9-review-20260719`) to get the authoritative P-28 Replacement report; found and resolved a live-account blocker (orphaned, deletion-protected `careervp-identity-map-table-dev` GlobalTable from an interrupted prior deploy — deleted per explicit human instruction), then re-formed the change set clean: **523 changes, `auto_fail: false`**, only 6 non-protected `Replacement:True` entries (`AWS::Lambda::Permission` swagger churn), zero `RestApi`/`DynamoDB::Table`/`S3::Bucket`/`Cognito::UserPool` replacements (evidence at `docs/evidence/p26-o9-changeset-review-20260719.json` + `-replacement-report-20260719.json`). **Human then executed the real deploy**, change set `p26-o9-execute-19-07-2026`: CloudTrail confirms `CreateChangeSet` at `2026-07-19T17:08:00Z` and `ExecuteChangeSet` at `2026-07-19T17:12:55Z` (principal `presgen_user`, `aws-cli/2.31.23`, request id `6b805e53-e7fa-4ddc-a171-6a37020ccbfe`); stack `CareerVpCrudDev` reached `UPDATE_COMPLETE` at `2026-07-19T17:20:20Z` (`aws cloudformation describe-stacks` / `describe-stack-events`, confirmed live, not from a cached report). This deploy recreated the `ApiDevCustomDomain` resource with a fresh ACM cert (`certificateUploadDate: 2026-07-19T20:13:05+03:00`) and a new `regionalDomainName` (`d-97qenqpec3.execute-api.us-east-1.amazonaws.com`, replacing the prior `d-ufdp03t4f1...`), which orphaned the existing Cloudflare CNAME for `api.dev.careervp.com` (NXDOMAIN on the old target, confirmed via `dig`/`host` against `1.1.1.1` and `8.8.8.8`). Human updated the Cloudflare CNAME to the new `d-97qenqpec3...` target; re-verified live resolution from two independent public resolvers post-fix. Ran the P-30 4-wire deploy smoke harness (`scripts/smoke_harness.py`) live against `https://api.dev.careervp.com`: **4/4 PASS** — `health` 200, `cors_exact_origin` exact-origin echo (no wildcard) for `https://main.d3j2wnm8g5clnw.amplifyapp.com`, `authed_read` 200 authed / 401 unauth-rejected, `authed_upload` CV posted and read back (`cv_id=5a96c222-06de-4cd9-a779-c18ce0fa8b19`) — evidence at `docs/evidence/smoke-20260719T173231Z-996d89.json`, matching the pre-deploy baseline (`docs/evidence/smoke-20260717T185228Z-37fe2d.json`, also 4/4). Also updated `specs/P-26-blue-green-api-spec.md` (dev-only Job-1 supersession note, AC-P26-9, domain-claim RED test) and `runbooks/p28-human-gated-deploy-runbook.md` (§5, devx cutover flows through the existing gate). | None — fully resolved and live-verified. `api.dev.careervp.com` resolves to `CareerVpCrudDev` and passes the full 4-wire smoke; devx creation (1.4) can now proceed on O-9. | `3bbb963`, `443dabe`, `ea882c3`; change-set execution + DNS fix are AWS/Cloudflare-side (no repo diff) | 2026-07-19 |
| 1.4 | P-09 | **Human executed the devx stack-creation change set; `CareerVpCrudDevx` is live.** Building on the prior review-only change set (below), the human formed and executed a fresh change set (`deploy-20260720T192943Z`, preceded by a `deploy-20260720T192517Z` review) against a not-yet-created `CareerVpCrudDevx`. Live-verified via `aws cloudformation describe-stacks --stack-name CareerVpCrudDevx`: **`StackStatus: CREATE_COMPLETE`**, `LastUpdatedTime: 2026-07-20T19:31:58Z`. Change-set evidence (`docs/evidence/careervpcruddevx-changeset-deploy-20260720T192943Z.json`, uncommitted): **257 changes, all `Action: Add`, zero `Replacement: True`** — matches the review change set's shape (292 template resources at synth-count granularity vs. 257 change-set entries vs. 211 deployed physical resources across parent + 2 nested stacks; the three counting methods disagree by a small, expected margin, not a discrepancy). Live resource-count check (`describe-stack-resources`): parent stack 100 direct resources + `AiAssistNestedStack` 11 + `CrudFeaturesNestedStack` (the P-26 re-homed features, flag-ON) 100 = **211 physical resources total**, well under the <400 target already established for this row. Stack outputs confirm a fresh, isolated `RawApiInvokeUrl` (`https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/`) and Cognito pool (`UserPoolId us-east-1_bAZ6jb6HP`), distinct from `CareerVpCrudDev`. **P-30 4-wire smoke run against the devx raw URL (`src/backend/scripts/smoke_harness.py`, not the nonexistent `scripts/smoke_harness.py` path — the correct path was the first thing that needed fixing): 3/4 PASS.** `health` 200, `cors_exact_origin` exact-origin echo, `authed_read` 200 authed / 401 unauth (using a fresh Cognito test user created via `admin-create-user`/`admin-set-user-password`/`initiate-auth` against devx's own pool, following the P-64 runbook's pattern). `authed_upload` initially **FAILED**: `cv-parser-lambda-devx` returned 500 because SSM parameter `/careervp/devx/anthropic-api-key` did not exist (confirmed via live CloudWatch logs, `requestId` matched to the smoke request's `correlation_id`) — `/careervp/dev/anthropic-api-key` and `/careervp/staging/anthropic-api-key` exist as `SecureString`, `/careervp/devx/...` was never seeded when devx was created. Human decision: copy dev's key value into devx (both are non-prod dev-tier envs; not a distinct-key requirement). Seeded via `aws ssm put-parameter --name /careervp/devx/anthropic-api-key --type SecureString` (value read from dev's parameter with `--with-decryption`, held only in a local shell var, never written to disk or logged). **Re-ran the full 4-wire smoke: 4/4 PASS**, including `authed_upload` (`cv_id=07e4a7c6-4664-4746-9c68-604d0953c075` uploaded and read back). Evidence: `docs/evidence/smoke-20260720T203115Z-434341.json` (pre-fix, 3/4) and `docs/evidence/smoke-20260720T203735Z-019ff0.json` (post-fix, 4/4). | None — devx creation, resource-count clearance, and full P-30 smoke are all live-verified and closed. Un-committed: the two changeset evidence JSONs and the two smoke evidence JSONs (3/4 pre-fix + 4/4 post-fix, kept for the record). Next: 1.1 (P-04/P-05, blocked on the 1.3c soak) is the only remaining open Wave-1 row. | `ea882c3`, `7c8a85c`; devx creation change-set execution + SSM parameter seed are AWS-side (no repo diff); evidence files pending commit | 2026-07-20 |
| 1.3c AMENDMENT | P-07 | **2026-07-22 — the soak gate in the row above is superseded, not satisfied.** The 1.3c row's closing sentence ("soak for at least the 30-day refresh-token lifetime… 1.1 (P-04) MUST NOT START until that soak completes") is left intact above for history. It is superseded because **that soak was never startable**: the PKCE commit `4228346` lives only on `db-redesign`, and Amplify app `d3j2wnm8g5clnw` builds `main` / `ui-upgrade` / `front/ui-update-amplify1` — never `db-redesign`. `git merge-base --is-ancestor 4228346 ee78796` (last successful Amplify build, 2026-07-18 18:36) returns **false**. The browser has never been served the PKCE SPA, so the 30-day clock has no start date and waiting longer changes nothing. The backend half of 1.3c *did* deploy (dev pool `us-east-1_WiHMRqLpe`: `Tier: PLUS`, `AdvancedSecurityMode: ENFORCED`, `LastModifiedDate: 2026-07-19T21:02`, via the O-9 deploy). Full reasoning in §"Soak reinterpretation (2026-07-22)" below — read it before accepting this. | **New step 1.6 replaces the soak** as 1.1's precondition. 1.1 stays blocked until 1.6 closes green with its evidence file. Separately still open and NOT closed by 1.6: `COGNITO_ADMIN` + implicit-grant removal still needs backend proxies for password-change/TOTP, now tracked as **P-07b, blocking STAGING promotion** (see `redesign-execution-plan.md`). | docs-only (this entry) | 2026-07-22 |
| 1.6 | P-07 (delivery) | **Code half landed and verified locally; the three human-only steps are NOT done, so 1.6 is NOT closed.** RED first (`08b4211`, tests only): 4 jest tests + 1 pytest test, all failing on their own assertions (`Received function did not throw`; offenders `["auth.ts","pkce.ts"]`; devx origin absent from the five registered CallbackURLs) — no import/collection errors. GREEN (`5b42321`): new `src/frontend/lib/auth-config.ts` resolves user-pool id, app-client id, and hosted domain lazily and **throws a named error when any is missing**, replacing the `?? '<dev value>'` fallbacks in `lib/pkce.ts` and `lib/auth.ts`; values are trimmed so a leading-space env var cannot silently mis-resolve. `cognito_construct.py` now registers `https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com` as a callback + logout URL (new module constant `DEVX_AMPLIFY_ORIGIN`). Verified: frontend typecheck clean, jest unit 149/149, integration 87/87, vitest 67 files/738 tests, backend infra 51/51, naming validator passed. `cdk diff CareerVpCrudDevx` (`ENVIRONMENT=devx -c p26_rehome_features=true`): UserPoolClient is an in-place `[~]` adding exactly one CallbackURL and one LogoutURL, **zero `[!]` replacement markers in the entire diff**. Prereqs re-verified live this session, not from this file: PKCE commit `4228346` exists; `CareerVpCrudDevx` is `CREATE_COMPLETE`; the devx pool/client/raw-API values and the leading-space `NEXT_PUBLIC_COGNITO_REGION=" us-east-1"` app-level typo all confirmed via `aws` calls. | **1.1 STAYS BLOCKED.** Three human-only steps remain, in order: (1) deploy the `cognito_construct.py` change to `CareerVpCrudDevx` through the P-28 change-set gate and attach the `changeset_replacement_report.py` output (`auto_fail: false`, zero `Replacement:True` on the Cognito UserPool); (2) create the Amplify `db-redesign` branch and build (exact command in the session output — set `NEXT_PUBLIC_COGNITO_REGION` at BRANCH level to route around the app-level typo); (3) ONE real login capturing all seven wires into `docs/evidence/pkce-devx-verification-<UTC-timestamp>.json`. A template with the required shape is committed at `docs/evidence/pkce-devx-verification-TEMPLATE.json` — it is explicitly `status: not_executed` and does NOT close the gate. **Three items flagged for human review, see the three bullets under "1.6 flags (2026-07-22)" below.** | `08b4211` (RED), `5b42321` (GREEN) | 2026-07-22 |
| 1.1-RED | P-04, P-05 | **not started.** Replaces the test half of 1.1. Isolated session, tests + checked-in route matrix ONLY, zero implementation files touched. Confirmed 2026-07-22 that none of the five tests exist: `grep -rl "AC-P04\|AC-P05" src/backend/tests infra/tests` returns **zero files**, and `scope-diff.py` reports `P-05 spec_written [NO TEST]`. | Blocked until 1.6 closes green. | — | — |
| 1.1-GREEN | P-04, P-05 | **not started.** Replaces the implementation half of 1.1. FRESH session that has not seen 1.1-RED's reasoning; may not edit the test files. Targets are `auth_utils.py:44` (x-user-id fallback) and `api_construct.py:2106` (dead `AUTHORIZER_DISABLED` — **not** `:1720` as the prompt originally cited). | Blocked until 1.1-RED commits five tests failing on their own assertions. Expected to close the 0.06pp core-branch coverage gap (see §"Coverage decision" below). | — | — |
| 1.1 | P-04, P-05 | **SPLIT 2026-07-22 — superseded by 1.1-RED + 1.1-GREEN.** Do not run `PROMPT 1.1` as a single session; it is retained in `wave-1-prompts.md` for its guardrail text only. | See the two rows above. | — | — |
| 1.5 | P-22 | **Fully landed, including the human AWS-side step.** Repo side unchanged from `2513ee6`: `cdk-diff.yml` uses GitHub OIDC role assumption, `id-token: write`, no long-lived keys; static shape asserted by `tests/infra/test_p22_oidc_cdk_diff.py`. Human created IAM role `careervp-cdk-diff-github-oidc` (trust policy federates `token.actions.githubusercontent.com`, `sts:AssumeRoleWithWebIdentity`, `aud=sts.amazonaws.com`, `sub` scoped to `repo:ymeirovich/careervp:pull_request`; inline permission policy grants only read-only CloudFormation actions on `CareerVpCrud*` stacks + `sts:AssumeRole` on the CDK bootstrap `lookup`/`deploy` roles, no `CreateChangeSet`/`ExecuteChangeSet`/`DeleteStack`) and stored the ARN in GitHub secret `AWS_CDK_DIFF_ROLE_ARN`. Added `src/backend/scripts/verify_oidc_cdk_diff.py` (live-AWS check, mirrors `verify_aws_state.py`'s pattern) to verify this end-to-end: OIDC provider exists, role's trust policy is correctly scoped (not wildcard — an unscoped `sub` would let any GitHub repo assume the role), permission policy has no forbidden deploy actions, and the GitHub secret exists. Ran it live: **all 8 checks PASSED.** `scope-diff.py` still reports P-22 `test_written` (that script only reads `impl_state` from `project-scope-lock.yaml`/spec+test presence, not live AWS state — the human step it was waiting on is now genuinely complete). | None. Fully unblocked — this was the last fully-independent Wave-1 item; the only remaining Wave-1 work is 1.1/1.3d/1.4/GATE, all gated on the P-07 soak or the O-9/devx human deploy. | `2513ee6` (repo); role/secret creation not committed (AWS-side + GitHub secret, no repo diff); `verify_oidc_cdk_diff.py` pending commit | 2026-07-19 |
| GATE | — | not started | — | — | — |

## 1.6 flags (2026-07-22) — three things a human should look at

**(1) A third hardcoded-fallback site existed that the step brief did not name — fixed, flagged.**

*Plain English:* the instructions said to remove the "wrong environment" safety hole from two
files. There was a third file with exactly the same hole, and it was the one the running app
actually uses. Fixing only the two named files would have left the problem fully in place while
looking solved. It was fixed, and this note exists so nobody thinks extra work was done quietly.

*Technical:* `contexts/AuthContext.tsx:47,51` carried the identical
`?? 'us-east-1_WiHMRqLpe'` / `?? '7blipbarsisbctqh6hlsj46sqa'` pair and constructs the
`CognitoUserPool` used by `AuthProvider` — the live runtime auth path. The brief named only
`lib/pkce.ts` and `lib/auth.ts`, and its literal-scan assertion was scoped to `src/frontend/lib/**`,
which does not cover `contexts/`. Now calls `getPoolConfig()`. This is delivery of P-07's locked
intent, not a clause change — but it is strictly more than the brief listed, so it is recorded here
per rule 5 rather than folded in silently.

**(2) `ymeirovich@gmail.com` does not exist in the devx pool — step 5 cannot run as written.**

*Plain English:* the final verification step says to log in as a specific account against the new
environment. That account only exists in the *old* environment. Somebody has to create it in the
new one first, or the login step simply cannot start.

*Technical:* `aws cognito-idp list-users --user-pool-id us-east-1_bAZ6jb6HP` returns exactly one
user, `p30-devx-20260720T202941Z@example.invalid` (the 1.4 smoke fixture). `ymeirovich@gmail.com`
lives in the dev pool `us-east-1_WiHMRqLpe`. Before step 5, create it in devx following the same
`admin-create-user` / `admin-set-user-password` pattern 1.4 used. Note this is a *real* mailbox, so
prefer `--message-action SUPPRESS` and a manually set permanent password over an invite email.

**(3) Pre-existing unrelated test failure in the infra-local suite — NOT introduced by 1.6.**

*Plain English:* one test in a different area was already broken before this step started, and is
still broken. It has nothing to do with this change, but it will show up in any full test run, so
here it is written down rather than left as a surprise.

*Technical:* `infra/tests/infrastructure/test_p64_scratch_path.py::test_scratch_configuration_and_ssm_names_are_explicit_and_isolated`
fails asserting `/careervp/<scratch-env>/jwt-private-key` is absent from the rendered template; the
P-06 ARN-scoped `ssm_parameters` IAM grant now legitimately puts that parameter ARN in the policy.
Confirmed pre-existing by `git stash` round-trip: identical failure on the unmodified tree
(1 failed, 26 passed). Belongs to P-06/P-64, not P-07 — needs its own owner.

---

## Soak reinterpretation (2026-07-22) — a written gate satisfied differently, with rationale

**Recorded per `RUNBOOK-RULES.md` rule 8.** A future session reading the 1.3c row will see "soak
for at least 30 days" and correctly refuse to start 1.1. This entry exists so that session finds
reasoning instead of an unexplained shortcut. If you disagree with the reasoning, the right move
is to reopen it with a human — not to quietly re-lengthen or quietly ignore the gate.

**In plain English:** step 1.1 was waiting 30 days for old login tokens to expire. Nobody was
waiting on anything — the new login code was never put in front of a browser, so the 30 days had
never started counting, and would not have started no matter how long we waited. On top of that,
the environment we actually care about has one test account and has never issued an old-style
token to anyone. So the wait was protecting nothing. We replace it with about an hour of
concrete checking (step 1.6), which tests the things the wait never could.

### The written gate bundles three separate concerns. Taken one at a time:

**(a) Stale implicit-era refresh tokens must expire.** *On devx: vacuous.* Pool
`us-east-1_bAZ6jb6HP` was created 2026-07-20 and holds exactly **one** user — the smoke-test
account created during 1.4. It has never issued an implicit-flow token to a browser. Zero wait
required.

A note on the config lever, because it is easy to misread: Cognito applies `refresh_token_validity`
**at issuance**. Shortening it now would not shorten tokens already in circulation. Setting it to
7 days (`cognito_construct.py:103`, currently 30) is worth doing as a steady-state posture, but it
is **not** the fix for (a) and must not be recorded as one.

**(b) Proof the PKCE flow actually works end to end.** *Not a function of time.* One real login
proves it; thirty days of nobody logging in proves nothing. The frontend unit suite mocks away
precisely the parts that can be wrong — the registered redirect URI, the hosted-domain config, the
`state`/`code_verifier` round-trip through `sessionStorage`, and the `/callback` route. **This is
the concern step 1.6 discharges**, with a captured evidence file rather than an elapsed timer.

**(c) `COGNITO_ADMIN` removal needs backend proxies for password-change/TOTP.** *Real, and NOT
discharged here.* But it gates the **final P-07 cutover**, not 1.1. 1.1 deletes a header-trust
fallback and a dead env var; it does not touch OAuth flows, and removing a header fallback cannot
be broken by the presence of an OAuth scope. Tracked as **P-07b, blocking STAGING promotion** —
it becomes non-theoretical the moment staging's 3 real users are in scope.

### Why the dev-pool user count does not rescue the original gate either

The dev pool `us-east-1_WiHMRqLpe` holds 122 users, which initially looked like a real population
worth soaking for. Enumerated in full 2026-07-22: **~119 are `test_<epoch>@example.com` /
`strict_<epoch>_<hash>@example.com` fixtures** from Mar–Apr 2026, plus
`testuser123@example.com` and `testuser1@careervp.com` (stuck in `FORCE_CHANGE_PASSWORD`), plus
**`ymeirovich@gmail.com` — the only real account.** There is no user population to protect and no
one to inconvenience. An earlier proposal to run `admin-user-global-sign-out` across those 122
users to collapse (a) to zero is therefore **withdrawn as unnecessary**, not merely unexecuted.

### What replaces the gate

Step **1.6**, and specifically its evidence file
`docs/evidence/pkce-devx-verification-<UTC-timestamp>.json`. Wave-1 GATE check #7 verifies that
artifact directly. **If that file is missing or partial, the soak gate is NOT satisfied**, whatever
this ledger says. Approximately one hour of verification replaces thirty days of waiting.

### Standing epistemic note

This reinterpretation was only findable because someone ran
`aws cognito-idp describe-user-pool-client` and `git branch --contains` instead of reading a status
column. The same class of error is already recorded twice in this file (the 2026-07-19 "DEPLOYED"
correction below; the 1.3a/1.2 stale-citation flags). **Verify from live, not from docs** — this
entry included.

---

## Coverage decision (2026-07-22) — recorded so it is not re-litigated

`src/backend/scripts/check_coverage_gates.py:42` sets `'core': CoverageGate(line_percent=71.0,
branch_percent=53.0)`. Actual core branch coverage is **52.94%** — failing by **0.06pp**, and
**already failing on `main` before P-06** (confirmed by the 1.2 session re-running the gate against
the pre-P-06 tree). Wave-1 GATE check #4 requires it to pass, so it would otherwise block the gate
on debt nobody in this wave created.

**Decision: let 1.1-GREEN's P-05 branch tests close it.** They are dense branch tests over `core`
auth paths and 0.06pp is a handful of branches — the honest fix, and nearly free because those
tests are being written anyway. Do not run `make coverage-tests` until after 1.1-GREEN.

**Rejected: re-baselining to 52.9%.** That is lowering a bar to walk under it. If 1.1-GREEN does
not clear the gap, the re-baseline needs the same dated human ledger treatment as any other
weakened rule — never a quiet edit to the threshold.

---

## Standing notes carried into every step (do not lose these)

- The two IMMUTABLE laws (never move the live RestApi or the Cognito user pool) apply to every
  row above that touches `infra/`. See `wave-1-prompts.md` for the exact logical ids.
- `api_construct.py` is edited by most of these steps — never run two steps that touch it at the
  same time. See `wave-1-prompts.md` §2 for the current serialization order.
- **(2026-07-22) `CareerVpCrudDevx` is the deploy target, not `CareerVpCrudDev`.** Human decision:
  devx *is* dev now, and old `CareerVpCrudDev` is scheduled for decommission (date still unset).
  Every prompt in `wave-1-prompts.md` says `cdk diff CareerVpCrudDev`; read that as
  `CareerVpCrudDevx` for any step not yet landed. Rows already closed above stay as written — they
  record what actually happened, and are not retroactively rewritten. Note that
  `api.dev.careervp.com` still points at the OLD stack, so devx is reachable only at its raw
  execute-api URL (`https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/`) until the
  human-only base-path flip. Anything configured with the friendly domain is talking to old dev.
- **(2026-07-22) Orphaned Cognito pools, pending human deletion** (all 0 users, verified
  unreferenced by any stack output): `us-east-1_ZRGBT6phK` (careervp-users-devx, 2026-07-19 23:04),
  `us-east-1_dfBh4yF48` (careervp-users-devx, 2026-07-19 22:13), `us-east-1_y5t4ZB77e`
  (careervp-users-staging, 2026-02-27). Leftovers from failed create attempts. **KEEP**
  `us-east-1_bAZ6jb6HP` (live devx, 1 user) and `us-east-1_21d5tatVO` (live staging, 3 users);
  `us-east-1_ZCMbRWDIK` ("PwdMgr", 2019) is unrelated to this project. Minor cost, but a real
  footgun — a future config edit can point at the wrong pool id, and three same-named pools make
  that mistake easy. **Before deleting an orphan, check for a stack in `ROLLBACK_COMPLETE` that
  owns it; if one exists, delete the stack rather than the pool**, so CloudFormation does not later
  trip on a missing resource. Deletion is irreversible and human-only.

## Deploy-state reconciliation (2026-07-18) — recordkeeping was stale

**CORRECTION 2026-07-19: the "zero substantive changes" / "DEPLOYED" claim below is WRONG.** A
real CloudFormation change set formed against live `CareerVpCrudDev` this session (2026-07-19,
`docs/evidence/p26-o9-changeset-review-20260719.json`) shows **523 pending changes** — including
the P-06 JWT/webhook env-var renames, P-08/P-10 CORS changes, the P-11 WAF WebACL, P-23's canary
CodeDeploy infra, P-24's identity-map table, and P-32's budgets. A plain `cdk diff` re-run the same
day shows 470 diff lines, not "owner-tag/asset-hash noise only." **None of P-06/P-08/P-10/P-11/P-23
is actually live yet** — each is "done" only in the sense of being committed to the repo, not
deployed. See `runbooks/wave-1-handoff-20260719.md` §0 and §1 for the corrected priority and the
prepared, human-executable fix (a change set already reviewed and proven safe, `auto_fail: false`,
zero stateful replacements — just not yet executed). The note below is left as-is for history; do
not trust its "DEPLOYED" conclusion.

Verified against git + a live flag-OFF `cdk diff CareerVpCrudDev` this session. Prior rows used
`pending (see commit message…)` placeholders and one prompt's "KNOWN-BUT-VERIFY" block carried
Jul-17 figures; both were stale. Corrected facts:

- **Real commit SHAs** (all committed, not "pending"): P-06 = `638f31e`, P-08 = `f2311b7`,
  P-10 = `e7beab0`, P-11 gate = `8f94b83`, P-07/P-11-rate (1.3c) = `4228346`, P-22 = `2513ee6`.
- **Live dev is CURRENT with HEAD's substantive infrastructure.** A flag-OFF `cdk diff` of HEAD
  against live `CareerVpCrudDev` shows **zero substantive changes** — no P-06 JWT/SSM env-var diff,
  no P-08/P-10 CORS diff, no P-11 WAF-rule diff. The entire diff is **owner-tag drift**
  (`owner: runner` live, from CI, vs `yitzchak` from a local synth — the tag is `getpass.getuser()`
  via `utils.get_username()` / `service_stack.py`) plus **Lambda code asset-hash churn** (local
  re-bundle) plus CDK metadata. **20 resource-level add/remove = hash-rotated `Lambda::Version` +
  1 `ApiGateway::Deployment` (inherent churn); 225 `[~]` = owner-tag/asset-hash/metadata only.
  Zero `[!]` stateful replacement. No DynamoDB table / S3 bucket / Cognito pool is destroyed,
  replaced, or substantively changed.** => P-06/P-08/P-10/P-11 (and P-23 canary) are DEPLOYED.
- **Corrected parent counts:** flag-OFF `CareerVpCrudDev` = **489** (the Jul-17 prep doc's 410 and
  the prompt's "412" predate the P-23 canary + P-11 WAF + P-06 IAM deploys). Flag-ON = **295**.
  Both clear the < 400 target.
- **`p26_rehome_features` is a CDK context flag** (`api_construct.py`, default OFF). The empty
  `CrudFeatures` nested stack synthesizes even when OFF (staged live by `7fe3c4d`); the 77 resources
  only populate it when `-c p26_rehome_features=true`. Nothing was "toggled back"; re-homing was
  always flag-gated and dormant.
- **`cdk refactor` kickoff precondition:** because `cdk refactor` forbids any add/remove/**update**
  and matches resources by content digest, the owner-tag + asset-hash drift between a local synth
  and the CI-deployed live stack makes even non-moving resources look "updated," aborting the
  refactor. It must be run where the synth matches live for non-moving resources — i.e. from the
  CI/deploy context (owner=`runner`, deployed asset hashes) or with `USER=runner` set and asset
  hashes normalized by a no-op flag-OFF deploy from that same context — then only the pure 77-move
  remains. See 1.3d and the prep artifact for the override-file.
