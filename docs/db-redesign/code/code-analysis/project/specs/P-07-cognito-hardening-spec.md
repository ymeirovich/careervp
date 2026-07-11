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

Must complete and soak before P-04/P-05 handler cleanup. Does not move the Cognito user pool.

