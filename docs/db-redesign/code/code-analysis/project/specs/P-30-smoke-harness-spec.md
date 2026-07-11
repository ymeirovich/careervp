---
spec_id: P-30-SMOKE-HARNESS
title: "Deploy smoke harness: health, exact-origin CORS, authed read, presigned upload"
status: draft
owner: backend
tier: T1
scope_lock_clause: P-30
claude_code: {model: opus, effort: high}
codex: {model: gpt-5-codex, reasoning: high}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; smoke scripts/tests are written later at IMPLEMENT time."
---

# Spec - P-30: 4-Wire Deploy Smoke Harness

## Problem Statement

Every risky deploy needs the same live proof before and after: health, exact-origin OPTIONS+GET CORS, authenticated read, and presigned upload. P-26 custom-domain work specifically needs this smoke through `https://api.dev.careervp.com`.

## Evidence

- `infra/careervp/api_construct.py:2881-2936` defines the route map used to select smoke endpoints.
- `src/backend/tests/e2e/test_e2e_contract_gate_validation.py:25-37` already probes representative generation endpoints.
- `src/backend/tests/e2e/e2e_helpers.py:63-66` reads API base and timeout from env, a pattern the smoke harness can reuse.
- `src/backend/careervp/handlers/vpr_status_handler.py:73-104` returns/caches presigned URLs, proving a download leg exists; upload smoke must cover presigned upload separately.
- Scope-lock P-30 requires health, OPTIONS+GET exact-origin, authed read, and presigned upload baseline green before/after each change.

## Fix Plan

1. Build a CLI smoke harness parameterized by `API_BASE`, frontend origin, and Cognito test user token.
2. Wire four checks: `GET /health`, OPTIONS+GET exact-origin on a protected route, authenticated read such as `/users/me`, and presigned upload.
3. Emit JSON evidence with request ids, status codes, headers, and assertion results.
4. Make P-26 run the same harness against raw invoke URL and custom domain.
5. Keep test accounts and tokens out of committed files.

## RED Tests to Write First

- `test_p30_harness_requires_four_wires`: parse harness config and assert exact checks `health`, `cors_exact_origin`, `authed_read`, `presigned_upload`.
- `test_p30_cors_asserts_exact_origin_not_wildcard`: fixture response with `Access-Control-Allow-Origin: *` fails for success CORS leg.
- `test_p30_authed_read_rejects_unauthenticated_success`: unauthenticated 200 fixture fails the authed read leg.
- `test_p30_outputs_machine_readable_evidence`: dry run emits JSON with `api_base`, `origin`, `checks[]`, `passed`, and per-check status.
- `test_p30_custom_domain_smoke_uses_api_dev_domain`: O-9 fixture asserts harness can run with `API_BASE=https://api.dev.careervp.com`.

## Acceptance Criteria

**AC-P30-1** - Given baseline dev, when the harness runs, then all four wires pass and evidence is saved.

**AC-P30-2** - Given a P-26 blue/green candidate, when smoke runs on raw and custom-domain URLs, then both pass before any human base-path flip.

**AC-P30-3** - Given CORS changes, when success responses are checked, then allowed origins are exact and wildcard success CORS fails.

## Done-when

All RED tests pass; smoke JSON evidence exists for baseline and post-change runs; no real secrets are committed.

## Sequencing / Dependencies

Wave 0 dependency for P-12 and P-26. P-30 also gates P-10 CORS cutover.

