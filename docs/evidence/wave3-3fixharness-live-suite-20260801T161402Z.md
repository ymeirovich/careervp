# Wave-3 step 3.FIX-HARNESS — the live-API suites, before and after

**Target:** `CareerVpCrudDevx`, raw invoke URL
`https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/`
**Date:** 2026-08-01 · **Scope:** test code only — no file under `src/backend/careervp/`,
`src/frontend/` or `infra/` was modified.

**Command (both runs):**

```
cd src/backend && API_BASE=... uv run pytest tests/e2e \
  tests/integration/test_full_pipeline_integration.py \
  tests/integration/test_api_credential_token_use.py -q
```

Raw logs: `.before.txt`, `.after.txt` (JWT strings redacted; no token value appears in
this evidence, in any assertion, or in any log line the suites emit).

---

## 1. Before

With `API_BASE` **unset** — the state every prior Wave-3 session saw:

```
4 passed, 20 skipped, 4 warnings in 0.34s
```

With `API_BASE` **set**:

```
8 failed, 4 passed, 12 skipped, 4 warnings in 37.06s

FAILED tests/e2e/test_e2e_contract_gate_validation.py::test_e2e_contract_gate_validation
FAILED tests/e2e/test_e2e_error_handling.py::test_e2e_unauthorized_access_returns_401
FAILED tests/e2e/test_e2e_error_handling.py::test_e2e_invalid_input_returns_400
FAILED tests/e2e/test_e2e_error_handling.py::test_e2e_not_found_returns_404
FAILED tests/e2e/test_e2e_error_handling.py::test_e2e_prerequisites_not_met_returns_422
FAILED tests/e2e/test_e2e_happy_path_full_job_application.py::test_e2e_happy_path_full_job_application
FAILED tests/e2e/test_e2e_quality_gates.py::test_e2e_quality_gates
FAILED tests/integration/test_full_pipeline_integration.py::test_full_pipeline_integration
```

Representative failures — every one at the first authenticated hop, none reaching an
artifact wire:

```
E  AssertionError: POST /jobs returned 401; expected [400];
   body={"error": "UNAUTHORIZED", "code": "UNAUTHORIZED", ...}
E  AssertionError: All payload attempts failed for POST /users/me/cv; expected status 201.
   Attempts: payload={'text_content': ...} -> status=401;
             payload={'file_content': ..., 'file_type': 'txt'} -> status=401
E  AssertionError: GET /vpr/nonexistent-id returned 403; expected [200, 401, 404];
   body={"error": "DEFAULT_4XX", "code": "DEFAULT_4XX", ...}
```

## 2. After

```
3 failed, 13 passed, 12 skipped, 4 warnings in 405.17s (0:06:45)

FAILED tests/e2e/test_e2e_happy_path_full_job_application.py::test_e2e_happy_path_full_job_application
FAILED tests/e2e/test_e2e_quality_gates.py::test_e2e_quality_gates
FAILED tests/integration/test_full_pipeline_integration.py::test_full_pipeline_integration
```

The three remaining failures, verbatim:

```
E  AssertionError: assert '8428d4e8-d07...b@example.com' == 'harness-d289...@careervp.com'
E    - harness-d2892d12d4@careervp.com
E    + 8428d4e8-d071-7088-a9c3-9e630806436b@example.com
   tests/e2e/test_e2e_happy_path_full_job_application.py:37

E  AssertionError: POST /cover-letter/generate returned 409; expected [200, 202, 422];
   body={"status": "upstream_required", "generating": [], "missing": ["vpr"],
         "chain_execution_arn": null, "requested_artifact": "cover_letter"}
   tests/e2e/test_e2e_quality_gates.py

E  AssertionError: POST /cover-letter/generate returned 409, expected [200, 201, 202].
   body={"status": "upstream_required", "generating": [], "missing": ["vpr"],
         "chain_execution_arn": null, "requested_artifact": "cover_letter"}
   tests/integration/test_full_pipeline_integration.py
```

With `API_BASE` unset: `4 passed, 24 skipped, 4 warnings in 0.39s`.

## 3. What now passes, what still fails, what skips

**Passes (13).** Authentication itself, and every wire from register through VPR and
CV tailoring:

| | |
|---|---|
| `test_e2e_contract_gate_validation` | the hardened gate — 36 checks across five declared outcomes, no 401 tolerated on an authenticated check, no unrouted response tolerated anywhere |
| `test_e2e_api_credential_token_use` (2) | ID-token regression guard, both directions |
| `test_api_credential_token_use` (2) | same, for the integration helper |
| `test_e2e_unauthorized_access_returns_401` | now pins the authorizer's own envelope, not just "not 2xx" |
| `test_e2e_invalid_input_returns_400` | |
| `test_e2e_not_found_returns_404` | |
| `test_e2e_prerequisites_not_met_returns_409_upstream_required` | renamed; asserts the deployed 409 `upstream_required` contract and the named unmet artifact |
| `test_vpr_async_polling` (4) | unchanged; does not authenticate |

`test_e2e_quality_gates` and `test_full_pipeline_integration` both now reach and pass:
CV upload (201), job create (201), company research (202), gap questions (10), gap
responses (200), **VPR generate → 202 → `/vpr/{id}/status` → `completed`**, CV tailoring
→ `completed` with `ats_score` and `fact_verification_detail.passed`. They fail one wire
later.

**Fails (3).**

1. **`F-DEVX-1`, two tests** — `POST /cover-letter/generate` → `409
   {"status":"upstream_required","missing":["vpr"]}` *after* the same request's VPR
   reached `completed`. Owned by step `3.CORR`; deliberately not touched here. This is
   the expected terminal state for this step: the failure is now legible and names its
   own cause instead of being an opaque 401.
2. **New finding — `GET /users/me` never returns the registered identity.**
   `POST /auth/register` writes a trial record only; the profile row is lazily
   auto-provisioned on first `/users/me` by `user_repository.ensure_user`
   (`src/backend/careervp/dal/user_repository.py:85`) with
   `email = f'{user_id}@example.com'` and `name = ''`. Every user therefore sees a
   placeholder email and a blank name. Confirmed directly against
   `careervp-users-table-devx`. **Not fixed here** — product code. The assertion was left
   at full strength.

**Skips (12).** The `@pytest.mark.e2e` / `@pytest.mark.slow` modules
(`test_e2e_async_failure_recovery`, `test_vpr_generation_flow`,
`test_vpr_regeneration_flow`, `test_placeholder`) — unchanged by this step.

## 4. The three defects this step fixed

### F-DEVX-2 — wrong token type

The deployed authorizer is a **`COGNITO_USER_POOLS`** authorizer
(`CareerVpCrudDevxCrudCognitoAuth…`, provider
`us-east-1_bAZ6jb6HP`), which validates **ID tokens only**. Both helpers now take
`id_token` from the login response, matching the frontend
(`src/frontend/lib/auth.ts` `getCurrentToken` → `session.getIdToken()`).

**Where the access token is still used: nowhere on a product route.** Two Cognito/OAuth
wires sit outside the product authorizer (`/auth/*` is `authorizationType: NONE` at the
gateway) and are unaffected by the switch:

- `POST /auth/refresh` consumes the **refresh token** (`auth_handler.py:118-135`); the
  helpers now hand it the refresh token, and it returns a fresh `id_token`.
- `POST /auth/logout` decodes whichever Cognito token it is given without verifying
  (`auth_handler.py:234-241`). Neither helper calls it.

The access token is retained in both helper return values as `cognito_access_token`
solely so the regression test can prove it is a *different* token type and that the
authorizer rejects it.

**Regression guard** (`test_e2e_api_credential_token_use.py`,
`test_api_credential_token_use.py`): decodes the credential's claim set without verifying
and asserts `token_use == 'id'`, asserts the access token's is `'access'`, and does the
controlled live comparison (`GET /users/me` → 200 with the ID token, 401 with the access
token). `decode_token_claims` returns claims only; no token value is logged, asserted on,
or written to evidence.

### F-DEVX-3 — stale request shapes

Corrected to the **canonical** shapes the real client sends, not the transitional
aliases:

| Wire | Was | Now | Canonical source |
|---|---|---|---|
| `POST /users/me/cv` | `{text_content}` / `{file_content,file_type}` (the legacy shape `cv_upload_handler._normalize_request_payload` still accepts) | `{cv_content, file_name, file_type}` | `src/frontend/app/cv-center/page.tsx:78-82` |
| `POST /jobs` | `{title, company, job_description}` (the `company` → `company_name` alias at `job_handler.py:230`) | `{title, company_name, description, url}` | `CreateJobInput`, `src/frontend/lib/types.ts:53` |
| `POST /company-research/fetch` | `{domain}` | `{job_id, company_name, url}` | `CompanyResearchRequest`, `api_models.py:577`; `methods.ts:101` |
| `POST /jobs/{id}/gap-responses` | `{cv_id, job_id, responses}` expecting **201** | `{responses}` expecting **200** | `methods.ts:154`; `GapResponseRequest`, `api_models.py:303` |

The multi-payload fallback helper (`post_with_payload_fallback`) is **deleted**: trying
aliases until one sticks is what let a stale shape pass as a green wire.

Two fixture facts had to change with them, both recorded rather than silently adopted:
`POST /jobs` live-fetches `url` for reachability, so `https://example.com/jobs/backend-1`
(a 404) is rejected as `unreachable` and the fixture now uses `https://example.com/`; and
the CV fixture text now names employers and dates, because `F-DEVX-6` 500s the upload
when the extractor emits a work entry with no company.

### F-DEVX-4 — polls on unrouted methods

All four artifact polls now target `/{id}/status`. `poll_completed` and
`poll_until_terminal` **refuse** a path that does not end in `/status`, so the defect
cannot be reintroduced silently. Verified against the deployed route table: `/vpr/{vprId}`
carries `OPTIONS` only, `/cv-tailoring/{id}` `DELETE|OPTIONS|PATCH`, `/cover-letter/{id}`
and `/interview-prep/{id}` `OPTIONS|PATCH`; only the `/status` children carry `GET`.

## 5. The contract gate is now a gate

`test_e2e_contract_gate_validation.py` was 27 rows of broad status sets
(`{200,401,404}`, `{202,400,401,422}`) plus a `'Missing Authentication Token'` text check
that the API's customised `DEFAULT_4XX` response had already defeated. It is now 36
checks, each declaring one of five required outcomes:

- `AUTHENTICATED_OK` — must succeed. **401 fails the gate here.**
- `PUBLIC_OK` — unauthenticated route, must succeed.
- `VALIDATION_FAILURE` — exactly 400, with a machine-readable error identity.
- `NOT_FOUND` — exactly 404, with a machine-readable error identity.
- `UNAUTHORIZED_NEGATIVE` — deliberately uncredentialled, exactly 401 **and** the
  authorizer's own `code: UNAUTHORIZED` envelope.

Two responses fail the gate regardless of the declared outcome: any 5xx, and any API
Gateway default response (`403 DEFAULT_4XX` or "Missing Authentication Token"), which
means the method is **not routed**. That check is by body, not status, because an
unrouted 403 is indistinguishable from an auth failure by status alone.

## 6. Judgment calls, stated rather than buried

Four expectations were corrected to the deployed contract rather than left to fail
opaquely. None weakens what was being checked; each replaces a status-only guess with an
assertion on the published envelope.

1. **`/company-research/{id}` for an absent record is 200, not 404.** It returns
   `{"status":"not_generated","company_research":null}` — the envelope the frontend
   consumes (`methods.ts:105-110`). The test now asserts that exact envelope.
2. **Unmet prerequisites are 409 `upstream_required`, not 422.** 422 never occurs.
   `test_e2e_prerequisites_not_met_returns_422` is renamed
   `test_e2e_prerequisites_not_met_returns_409_upstream_required` (**node id changed**)
   and now asserts the status, the `upstream_required` marker and the named unmet
   artifact — strictly more than the bare 422 it replaced.
3. **Two validation envelopes are published.** Most handlers return `{error, ...}`;
   CV tailoring returns `{success:false, code, message, errors[]}`. `'error' in res.data`
   was pinning one of the two. The tests now require an explicit machine-readable
   identity — `error`, or `code` **and** `message` — and still fail a 400/404 carrying
   neither. **The divergence itself is a finding, not something this step fixed.**
4. **`fvs_validation` is not on the status response.** `cv_tailoring_handler.py:1114`
   states it is deliberately withheld; `fact_verification_detail.passed` is the published
   form. The happy-path test now asserts that, and asserts it unconditionally — the old
   `if isinstance(fvs, dict)` guard was dead code that had never executed.

Also structural: artifact status responses nest the generated content under `result`
(`{status, id, result:{uvp, differentiators, …}}`). A shared `artifact_result()` helper
descends one level; every content assertion reads through it.

## 7. Two environment limits hit while running this, both recorded

**Cognito daily email cap.** Mid-session `POST /auth/register` began returning 500 for
every address, new or existing:

```
Registration failed: An error occurred (LimitExceededException) when calling the SignUp
operation: Exceeded daily email limit for the operation or the account.
```

The pool uses Cognito's built-in email sender (50 SignUp verification mails/day, pool-wide).
The suites register a fresh user per test, so roughly five full runs exhaust the day's
quota for the whole `devx` pool — after which **every** registration 500s, including
re-registering an existing address. **Not fixed here** (the remedy is an SES
configuration on the pool, which is `infra/`). Mitigated in test code only: setting
`TEST_USER_EMAIL` and `TEST_USER_PASSWORD` reuses an existing account and skips
`/auth/register` entirely. `test_auth_flow_integration` opts out via
`require_fresh_registration=True`, because registration is what it tests.

**Trial exhaustion on a reused account.** A reused account carries its trial counters
forward, and the 3-application trial is smaller than one pass of this suite, so the
second run 403s `trial_exhausted` on `POST /jobs`. The reuse path calls
`POST /users/me/trial/reset` (a route the deployed API already exposes) once per
authentication. This runs **only** on the reuse path; a freshly registered user never
touches it.

The quoted "after" run used the reuse path, because the day's registration quota was
already spent by the earlier runs in this session.

## 8. Verification

- `git status --porcelain -- src/backend/careervp/ src/frontend/ infra/` → **empty**.
- Neither scope-lock twin edited; `test_dh4_p01_canonical_artifact.py` not edited.
- `uv run ruff format` / `uv run ruff check` on `tests/e2e tests/integration` → clean.
- `uv run mypy careervp --strict` → **Success: no issues found in 136 source files**.
- `uv run mypy tests/e2e tests/integration --strict`: **91 → 74** errors. Zero in any file
  this step created or edited; the reduction comes from `# type: ignore` on the
  `except ImportError` fallback import in the two files already being edited.
- `uv run pytest tests/unit/ -q` → **1397 passed, 15 skipped, 4 xfailed, 1 xpassed**.
