# Wave 3 — 3.FIX-SECURITY devx evidence

No bearer value is recorded in this file.

## Live reproductions before the fix

- IDOR: an authenticated disposable devx user posted the legacy CV shape with synthetic foreign user id `00000000-dead-beef-0000-f2e6a383912d`. The route returned HTTP 201 and `careervp-cvs-table-devx` stored that same foreign owner (`cvId eb3e88d9-ecb4-4ba4-96fc-0680d245b6c3`).
- Logging: a live interview-prep request with a synthetic sensitive body marker was followed by a read-only scan of the newest Lambda log stream. The stream contained the `api_gateway_event` key, the `Authorization` header field, and the marker. The raw message and token were never printed or persisted.

## Fix and unit evidence

- `POST /users/me/cv` now strips body `user_id` and injects the authorizer identity for both legacy and OpenAPI content shapes.
- Interview-prep submit logs only allow-listed metadata. It no longer logs the API Gateway event, request body, validated payload, DynamoDB item, SQS payload, or response body.
- Focused tests: `23 passed` (`test_cv_upload_handler`, `test_async_submit_handlers`, P-04/P-05 unit tests); the P-05 integration matrix passed `9 passed` after running with AWS access.
- Ruff format/check and `mypy careervp --strict` passed.

## Live re-test after current-source deploy

`CareerVpCrudDevx` reached `UPDATE_COMPLETE`. A new disposable user posted the legacy CV shape carrying synthetic foreign user id `00000000-dead-beef-0000-2999b39ff13e`.

- HTTP status: 201.
- Foreign table key: absent.
- Stored owner under the authenticated table key: `44389408-4091-70d7-d917-813321e751db` (the authorizer identity), never the foreign UUID.
- New interview-prep log entry: neither the synthetic sensitive body marker nor an `Authorization` field was present.

## Audits

- Body-supplied identity: `vpr_submit_handler` already derives OpenAPI identity from authorizer and rejects a legacy mismatch. `vpr_handler` accepts `VPRRequest.user_id`, but it is an old direct-generator Lambda with no current public route wiring; this is flagged as ambiguous legacy residue, not changed here. SQS worker `user_id` values are trusted internal message fields, not client HTTP body identity. No other live HTTP handler had the CV route's unauthenticated-body-to-storage flow.
- Whole-event logging: no remaining API Gateway whole-event logger was found after the submit-handler fix. Three worker/DLQ raw-record logs remain: `interview_prep_handler.py:130`, `vpr_dlq_handler.py:23`, and `vpr_dlq_handler.py:44`. They are SQS records, not API Gateway bearer events, but may expose worker payload data and should be separately redacted; out of this narrowly scoped bearer-log fix.

## Cleanup and token assessment

Deleted and read-after-delete confirmed absent: the original characterization item (`00000000-dead-beef-0000-000000000001` / `4d877e8e-0db8-428f-a98f-09c70cb08e52`) and three synthetic session probes. Result: `deleted_count=4`, `remaining_count=0`.

The affected log group retains entries for one day. Cognito devx ID tokens have a configured 60-minute lifetime, so the originally observed token is expired if it was issued before this session; retention is not redaction. The log group has no resource policy targeting it (the two account policies are WAF-only), but IAM policies can still grant `logs:GetLogEvents`/Insights access, so account IAM access must be reviewed by the account owner. No real token was copied into evidence or tests.

## Drift comparison

No contract, route, identifier, scope-lock, or infrastructure-source drift was introduced. The prompt's shorthand `wave-3-status.md` resolves in this repository to `docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md`; that path correction is recorded only. F-DEVX-1 and its 409 remain untouched.
