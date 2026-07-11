---
spec_id: P-08-P-10-P-11-CORS-WAF
title: "CORS allow-lists and WAF rate protection"
status: draft
owner: infra
tier: T1
scope_lock_clause: [P-08, P-10, P-11]
tooling:
  P-08: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}
  P-10: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}
  P-11: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest/vitest files are written later at IMPLEMENT time."
---

# Spec - P-08/P-10/P-11: CORS and WAF

## Problem Statement

S3 and API Gateway CORS are still broad, and WAF is not guaranteed across all envs with a rate rule. Tightening CORS must preserve the frontend §3 401 behavior: gateway error responses may retain `Access-Control-Allow-Origin: *` only where needed so 401 is visible to the browser and the refresh/sign-out flow works.

## Evidence

- `infra/careervp/api_construct.py:356-358` sets API Gateway default CORS to `Cors.ALL_ORIGINS` and `ALL_METHODS`.
- `infra/careervp/api_db_construct.py:184,561`, `infra/careervp/s3_stack.py:40,63`, and `infra/careervp/frontend_stack.py:48` define S3 CORS rules that must be origin-audited.
- `infra/careervp/waf_construct.py:28-109` creates a WebACL with managed rules and API association.
- `infra/careervp/waf_construct.py:41-103` lists managed rule groups but no explicit rate-based rule is visible in the evidence.
- `src/backend/careervp/handlers/cors_utils.py:4,17` supports Lambda-layer origin validation using `ALLOWED_ORIGINS`.

## Fix Plan

1. P-08: replace CV/generated bucket wildcard CORS with explicit frontend origins per env, including localhost only for dev.
2. P-10: replace API Gateway `ALL_ORIGINS` for normal success responses with the same allow-list. Keep `GatewayResponse` wildcard only if tests prove it is required for §3 item-10 401 visibility.
3. Before API CORS cutover, run P-30 OPTIONS+GET exact-origin smoke and prepare an inverse changeset; set low max-age first.
4. P-11: ensure WAF WebACL and API association exist in every env and add a rate-based rule with an env-tuned threshold.
5. Do not change route request/response payloads.

## RED Tests to Write First

- `test_p08_s3_cors_has_no_wildcard_origin`: synth buckets and assert no CORS `AllowedOrigins` contains `*` for CV/generated buckets.
- `test_p10_api_cors_success_allowlist_only`: synth RestApi and assert default CORS origins equal the env allow-list, not `ALL_ORIGINS`.
- `test_p10_gateway_401_cors_exception_is_documented`: assert GatewayResponse keeps enough CORS headers for browser-visible 401 and refresh retry; if wildcard remains, assert it is only on GatewayResponse.
- `test_p11_waf_rate_rule_exists_all_envs`: synth all envs and assert a `RateBasedStatement` is present and associated with the API stage.
- `test_p30_exact_origin_smoke_required_before_cors_cutover`: assert the implementation checklist blocks P-10 until P-30 OPTIONS+GET smoke is green.

## Acceptance Criteria

**AC-P08-1** - Given S3 CORS on upload/generated buckets, when synthesized, then only explicit allowed origins are present and wildcard origin is absent.

**AC-P10-1** - Given API CORS success responses, when a request comes from an allowed origin, then it receives the exact origin; when from a disallowed origin, then it receives no permissive ACAO.

**AC-P10-2** - Given a 401, when the frontend receives it, then the §3 item-10 refresh-once-then-sign-out flow still sees the response.

**AC-P11-1** - Given any env, when the API stack synthesizes, then WAF is associated with the API and includes a rate-based rule.

## Done-when

All RED tests pass; P-30 pre/post smoke is green; `cdk diff` zero stateful replacement; naming validator passes.

## Sequencing / Dependencies

P-08 lands before P-10 as the low-blast-radius pilot. P-10 requires P-30 smoke. P-11 may ship with P-07 in Wave 1 but must not be combined with a risky CORS flip unless smoke and rollback are ready.

