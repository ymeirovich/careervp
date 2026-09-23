---
spec_id: P-04-P-05-AUTH-IDOR
title: "Auth cleanup and owner-enforced route access"
status: draft
owner: backend
tier: T1
scope_lock_clause: [P-04, P-05]
tooling:
  P-04: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  P-05: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-04/P-05: Auth Cleanup and IDOR Closure

## Problem Statement

P-04 is now a cleanup clause, not an auth flip: live dev already uses Cognito authorizers, and `AUTHORIZER_DISABLED` is dead config. The remaining risk is that handlers can still contain `x-user-id` or client-supplied identity fallback paths, and P-05 requires every authenticated route to prove tenant ownership with the internal authenticated user identity. The implementation must delete bypasses and enforce owner checks without changing the frontend wire contract.

## Evidence

- `infra/careervp/api_construct.py:2811-2817` marks `/billing/webhook` as the public exception and lists public routes separately; all other routes must be Cognito-protected.
- `infra/careervp/api_construct.py:2864-2936` registers the canonical route map, including authenticated user, job, artifact, VPR, CV tailoring, cover letter, interview prep, company research, and billing routes that need a route-by-route owner-check table.
- `src/backend/careervp/handlers/ai_assist_handler.py:128` comments that `application_id` must belong to the JWT user, showing the intended ownership rule exists locally but must be made systematic.
- `src/backend/careervp/handlers/cv_tailoring_handler.py:345,577,732,803,858,946,1001-1002,1038` still uses table-name precedence and DAL access paths that must be checked for authenticated-user ownership before resolving artifacts.
- Scope-lock P-04 recon says dev Cognito auth is already enforced, `AUTHORIZER_DISABLED` has zero code readers, and the remaining work is deleting the dead CDK env var plus removing `x-user-id` handler fallback.

## Fix Plan

1. Generate a route x handler ownership matrix from `infra/careervp/api_construct.py` `route_map`, excluding only documented public routes (`/health`, auth routes, billing webhook, error reports).
2. For P-04, grep every handler and middleware for `x-user-id`, `AUTHORIZER_DISABLED`, and body/query/path `user_id` trust. Delete fallback identity paths; identity comes only from validated JWT claims or the P-24 resolver context.
3. For P-05, make each authenticated handler resolve records by authenticated owner. A request for another tenant's `job_id`, `artifact_id`, `cv_id`, `vpr_id`, or `application_id` returns 404 or 403 using the flat §3 item-10 error envelope.
4. Add a P-24 resolver-failure metric hook expectation to this spec, but do not implement P-24 here. Aggregate 401-rate is not enough.
5. Preserve §3 frontend behavior: no route shape changes, no enum changes, no nested error envelope. Any changed error response must satisfy the F-01 oracle.

## RED Tests to Write First

- `test_p04_no_x_user_id_fallbacks_remain`: scan `src/backend/careervp/handlers/**/*.py`; assert zero occurrences of `x-user-id` outside test fixtures and docs.
- `test_p04_no_authorizer_disabled_runtime_switch`: scan `infra/` and `src/backend/`; assert `AUTHORIZER_DISABLED` is absent from Lambda env and runtime code.
- `test_p05_route_matrix_has_owner_assertion_for_every_authenticated_route`: build the route x handler matrix from CDK; assert every non-public route has an explicit test case name and owner-check assertion.
- `test_p05_cross_tenant_authenticated_routes_deny`: parameterize every authenticated route; seed tenant A and tenant B records; assert tenant B gets HTTP 403 or 404 and never tenant A data.
- `test_p05_error_envelope_is_flat`: for an IDOR denial, assert keys include one of `error`/`message`, plus `classification`, `error_code`, and `field`, and assert no nested `error.code` object is returned.

## Acceptance Criteria

**AC-P04-1** - Given live dev already has Cognito auth at API Gateway, when P-04 lands, then no handler can derive identity from `x-user-id`, body `user_id`, query `user_id`, or `AUTHORIZER_DISABLED`.

**AC-P04-2** - Given a request without a valid Cognito authorizer context, when it reaches any protected handler in tests, then it fails closed and emits a resolver-failure metric where P-24 owns identity mapping failures.

**AC-P05-1** - Given two authenticated users and a route x handler table from CDK `route_map`, when user B requests user A's job or artifact identifier, then every route denies access and returns no cross-tenant data.

**AC-P05-2** - Given any P-05 denial, when the frontend oracle parses it, then the §3 item-10 flat error envelope remains valid.

## Done-when

All RED tests pass; the route matrix is checked in as evidence; no production route or response shape changes except correct denials; F-01 oracle is green. For any infra/CDK edit, implementer must run `cdk diff` and prove zero stateful replacements plus `python src/backend/scripts/validate_naming.py --path infra --verbose`.

## Sequencing / Dependencies

P-23 canary/rollback must land before handler fallback removal. ~~P-07 SPA auth-code+PKCE cutover must soak before any auth enforcement change.~~ **AMENDED 2026-07-22 — see below.** P-24 owns the durable `sub -> user_id` resolver; this spec must not invent a separate identity authority.

### Amendment 2026-07-22 — the P-07 soak precondition is superseded, not waived

The struck sentence above is replaced by: **runbook step 1.6 must close green**, evidenced by
`docs/evidence/pkce-devx-verification-*.json` showing a complete real login round-trip against
`CareerVpCrudDevx` (authorization-code redirect -> `/callback` -> token exchange -> authenticated
call -> forced 401 -> exactly one refresh -> sign-out).

Why: the soak was never startable. The PKCE commit (`4228346`) exists only on `db-redesign`, and
Amplify has never built that branch, so the PKCE SPA has never been served to a browser and the
30-day clock has no start date. Separately, on `devx` the stale-token concern is vacuous — that
pool was created 2026-07-20, holds one smoke-test user, and has never issued an implicit-flow token
to a browser. Waiting protects nothing; one verified login proves what the wait could not.

**Not waived by this amendment:** `COGNITO_ADMIN` and implicit-grant removal still require backend
proxies for password-change/TOTP. That is tracked as **P-07b and blocks STAGING promotion**. It
does not gate this spec, because P-04/P-05 remove a header-trust fallback and a dead env var and do
not touch OAuth flows — a header fallback cannot be broken by the presence of an OAuth scope.

Full reasoning, live evidence, and the epistemic caveats: `runbooks/wave-1-status.md`
§"Soak reinterpretation (2026-07-22)". Recorded per `RUNBOOK-RULES.md` rule 8.

### Amendment 2026-07-22 — implementation is split across two sessions

Per `RUNBOOK-RULES.md` rule 7, this spec is implemented as `PROMPT 1.1-RED` (tests + route matrix
only, zero implementation files touched) followed by `PROMPT 1.1-GREEN` in a **fresh session** that
may not edit the test files. This is the most correctness-critical clause in Wave 1; the author of
the tests must not be the author of the code.

### Citation corrections 2026-07-22 (the Evidence section above has drifted)

Verified against the working tree on 2026-07-22 — re-verify before relying on them:

| Evidence cites | Actually at |
|---|---|
| `api_construct.py:2864-2936` — `route_map` | **`api_construct.py:3251-3323`** |
| `api_construct.py:2811-2817` — public-route exception | **`api_construct.py:3190-3196`** |

Also worth naming explicitly, since the Evidence section does not: the live `x-user-id` fallback
site is **`src/backend/careervp/handlers/auth_utils.py:44`**, and the dead `AUTHORIZER_DISABLED`
env is at **`infra/careervp/api_construct.py:2106`** (the Wave-1 prompt's `:1720` was stale). When
scanning for `AUTHORIZER_DISABLED`, exclude `infra/cdk.out/` — it is build output, and a hit there
is a stale-artifact false positive rather than a source finding.

