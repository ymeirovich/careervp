---
spec_id: P-30-SMOKE-HARNESS
title: "Deploy smoke harness: health, exact-origin CORS, authed read, authed upload"
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

Every risky deploy needs the same live proof before and after: health, exact-origin OPTIONS+GET CORS, authenticated read, and authenticated upload. P-26 custom-domain work specifically needs this smoke through `https://api.dev.careervp.com`.

## Evidence

- `infra/careervp/api_construct.py:2881-2936` defines the route map used to select smoke endpoints.
- `src/backend/tests/e2e/test_e2e_contract_gate_validation.py:25-37` already probes representative generation endpoints.
- `src/backend/tests/e2e/e2e_helpers.py:63-66` reads API base and timeout from env, a pattern the smoke harness can reuse.
- `src/backend/careervp/handlers/vpr_status_handler.py:73-104` returns/caches presigned URLs, proving a *download* leg exists. There is **no presigned _upload_** route (all 58 deployed routes enumerated 2026-07-12): `POST /users/me/cv` takes the file inline as base64 `cv_content` and `cv_upload_handler.py:129-137` performs the S3 put itself. The upload wire therefore exercises that real route. The presigned-upload *feature* (and the ~4.5 MB inline ceiling it would lift) is tracked as ISSUES.md I-01.
- Scope-lock P-30 (v2.3.0) requires health, OPTIONS+GET exact-origin, authed read, and authed upload baseline green before/after each change.

## Fix Plan

1. Build a CLI smoke harness parameterized by `API_BASE`, frontend origin, and Cognito test user token.
2. Wire four checks: `GET /health`, OPTIONS+GET exact-origin on a protected route, authenticated read such as `/users/me`, and authenticated upload (`POST /users/me/cv` with base64 `cv_content`, then read the CV back so the wire proves its own write landed).
3. Emit JSON evidence with request ids, status codes, headers, and assertion results.
4. Make P-26 run the same harness against raw invoke URL and custom domain.
5. Keep test accounts and tokens out of committed files.

## RED Tests to Write First

- `test_p30_harness_requires_four_wires`: parse harness config and assert exact checks `health`, `cors_exact_origin`, `authed_read`, `authed_upload`.
- `test_p30_upload_wire_posts_base64_cv_content_to_the_real_route`: the upload wire POSTs `{cv_content: <base64>, file_name}` to `/users/me/cv` (the real contract), not a presigned-URL request.
- `test_p30_upload_wire_fails_when_upload_is_not_readable_back`: a write absent from the read-back fails the wire.
- `test_p30_upload_wire_fails_when_response_has_no_cv_id`: a 201 carrying no `cv_id` fails the wire (no empty successes).
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

