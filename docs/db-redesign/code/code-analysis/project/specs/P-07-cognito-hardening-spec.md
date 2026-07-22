---
spec_id: P-07-COGNITO-HARDENING
title: "Cognito MFA, advanced security, auth-code PKCE, and public SPA scope hardening"
status: draft
owner: auth
tier: T1
scope_lock_clause: P-07
claude_code: {model: sonnet, effort: medium}
codex: {model: gpt-5-codex, reasoning: medium}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest/vitest files are written later at IMPLEMENT time."
---

# Spec - P-07: Cognito Hardening

## Problem Statement

The public SPA client still uses implicit OAuth flow and includes `COGNITO_ADMIN`, while MFA/advanced security is not enforced safely. The fix crosses the frontend boundary deliberately: migrate the frontend to authorization-code + PKCE first, keep a dual-flow soak, then remove implicit and remove `COGNITO_ADMIN` only after proving no self-service flow needs it.

## Evidence

- `infra/careervp/cognito_construct.py:39-58` defines the app client callback/logout URLs.
- `infra/careervp/cognito_construct.py:44` enables `implicit_code_grant=True`.
- `infra/careervp/cognito_construct.py:47` includes `cognito.OAuthScope.COGNITO_ADMIN` on the public SPA client.
- `infra/careervp/cognito_construct.py:71-73` sets token validity windows; stale implicit-flow tokens must be soaked before P-04 cleanup.
- Scope-lock P-07 requires verification before removing `COGNITO_ADMIN`, a dual-flow migration window, and MFA optional-to-enforced with grace.

## Fix Plan

1. Before changing scopes, grep `src/frontend` for `signin.user.admin`, `AssociateSoftwareToken`, `UpdateUserAttributes`, `ChangePassword`, and TOTP enrollment flows. If present and no backend proxy exists, stop and emit an amendment or keep the scope temporarily with a migration plan.
2. Enable authorization-code grant + PKCE while keeping implicit grant during the migration window.
3. Update frontend auth configuration to use code+PKCE, run frontend checks, deploy, and soak.
4. Remove implicit grant only after soak proves no implicit tokens are needed.
5. Roll MFA optional -> enforced with an enrollment grace window, not immediate lockout.
6. Keep API response contracts unchanged; auth failures must continue to satisfy §3 item 10 and the one-refresh-then-sign-out behavior.

## RED Tests to Write First

- `test_p07_frontend_scope_usage_inventory_complete`: scan frontend source and assert each `COGNITO_ADMIN`-requiring API call is classified `none`, `backend_proxy`, or `temporarily_allowed`.
- `test_p07_app_client_supports_code_pkce_before_implicit_removed`: synth Cognito app client and assert code grant is enabled while implicit remains enabled during migration.
- `test_p07_public_spa_client_has_no_cognito_admin_after_cutover`: post-cutover synth asserts `COGNITO_ADMIN` absent from OAuth scopes.
- `test_p07_mfa_rollout_has_grace_state`: assert MFA config supports optional/enrollment grace before enforced mode.
- `test_p07_401_contract_still_refreshes_once`: frontend oracle asserts 401 still triggers exactly one refresh retry then sign-out.

## Acceptance Criteria

**AC-P07-1** - Given the current frontend, when `COGNITO_ADMIN` removal is considered, then all browser-side admin-scope usages are inventoried and either absent or migrated behind a backend proxy.

**AC-P07-2** - Given the migration starts, when CDK synthesizes, then code+PKCE and implicit coexist until the frontend has deployed and soaked.

**AC-P07-3** - Given the soak completes, when implicit and `COGNITO_ADMIN` are removed, then auth login, logout, refresh, and MFA enrollment flows remain green.

**AC-P07-4** - Given MFA enforcement, when existing users without devices sign in during the grace window, then they can enroll rather than being locked out.

## Done-when

All RED tests pass; required frontend checks pass if frontend changes; `cdk diff` zero stateful replacement; naming validator passes after infra changes.

## Sequencing / Dependencies

~~Must complete and soak before P-04/P-05 handler cleanup.~~ **AMENDED 2026-07-22 — see below.** Does not move the Cognito user pool.

---

## Amendment 2026-07-22 — the soak is replaced by verification, and P-07 is split

Recorded per `RUNBOOK-RULES.md` rule 8. Full evidence and reasoning:
`runbooks/wave-1-status.md` §"Soak reinterpretation (2026-07-22)".

### What went wrong with the original sequencing

Fix Plan step 3 says "deploy, and soak"; step 4 gates implicit-grant removal on that soak. **The
deploy never happened, so the soak never started.** The PKCE commit `4228346` exists only on the
`db-redesign` branch, and Amplify app `d3j2wnm8g5clnw` builds `main`, `ui-upgrade`, and
`front/ui-update-amplify1` — never `db-redesign`. The browser has been served the pre-PKCE implicit
SPA the entire time. The backend half *did* land (dev pool `Tier: PLUS`,
`AdvancedSecurityMode: ENFORCED`, 2026-07-19). A soak clock with no start date does not advance by
waiting.

### The clause splits in two

**P-07 (this spec, delivery step 1.6) — gates P-04/P-05.** Deploy the PKCE SPA to an Amplify branch
configured against `CareerVpCrudDevx`, and prove one real end-to-end login round-trip. Discharged
by evidence, not elapsed time: `docs/evidence/pkce-devx-verification-*.json`. On devx the
stale-token concern is vacuous — the pool was created 2026-07-20, holds one smoke-test user, and
has never issued an implicit-flow token to a browser.

**P-07b (new, deferred) — gates STAGING promotion, not P-04/P-05.** Fix Plan steps 1 and 4 and
AC-P07-1/AC-P07-3 remain fully in force and are **not** discharged by 1.6: the SPA still holds
`aws.cognito.signin.user.admin` so the browser can perform password-change and TOTP enrollment
directly. The scope-usage inventory in `4228346` classifies all five usages `temporarily_allowed`
and **none** as `backend_proxy`. Removing the scope before those flows move behind a backend
endpoint breaks password change and MFA enrollment for real users. Tracked in
`redesign-execution-plan.md` as **P-07b, blocking staging promotion** — staging has 3 real accounts,
so this stops being theoretical there.

P-07b does not gate P-04/P-05, because those remove a header-trust identity fallback and a dead env
var and do not touch OAuth flows at all. A header fallback cannot be broken by the presence of an
OAuth scope; the original runbook bundled them under one gate out of caution, not necessity.

### Additional finding: config-fallback hazard (folded into step 1.6)

`src/frontend/lib/pkce.ts:11,15` and `src/frontend/lib/auth.ts:12,16` fall back to the hardcoded
**dev** pool `us-east-1_WiHMRqLpe` and client `7blipbarsisbctqh6hlsj46sqa` when env vars are
missing. A devx build with a typo'd variable therefore authenticates against **dev**, silently and
successfully. Step 1.6 makes missing config fail loudly instead. This is not in the original Fix
Plan and is the highest-value single fix in the set.

Related, flagged not fixed: Amplify app-level `NEXT_PUBLIC_COGNITO_REGION` is `" us-east-1"` with a
**leading space**, inherited by `main`; `NEXT_PUBLIC_COGNITO_DOMAIN` and `NEXT_PUBLIC_COGNITO_REDIRECT_URI`
are unset at app level, so real builds rely on the `pkce.ts` fallback. Branch-level variables
override app-level, so 1.6 routes around this for `db-redesign` without touching `main`.

### Token-validity note (do not mistake this for the fix)

`cognito_construct.py:103` sets `refresh_token_validity=Duration.days(30)`. Shortening it to 7 days
is worth doing as steady-state posture for non-prod, but Cognito applies this **at issuance** — it
does not shorten tokens already in circulation, and it is therefore not a remedy for stale tokens.
Do not record it as one.

### Citation corrections 2026-07-22 (the Evidence section above has drifted)

Verified against the working tree on 2026-07-22 — re-verify before relying on them:

| Evidence cites | Actually at |
|---|---|
| `cognito_construct.py:39-58` — callback/logout URLs | **`cognito_construct.py:26-47`** |
| `cognito_construct.py:44` — `implicit_code_grant=True` | **`cognito_construct.py:86`** |
| `cognito_construct.py:47` — `COGNITO_ADMIN` scope | **`cognito_construct.py:89`** |
| `cognito_construct.py:71-73` — token validity windows | **`cognito_construct.py:101-103`** |

Same stale-citation class already flagged by the 1.3a and 1.2 ledger rows.

