# P1 reproduction artifacts

Four scratch tests written during the P1 adversarial-validation session
(2026-09-12, repo @ `cea0799`). They are **not** part of the project test suite
and are deliberately excluded from `tests/` — they exist so a second reviewer can
re-run the P1 session's claims rather than trust its transcript.

Two of them (`s0a_*`, `s0b_*`) import the project's own P-05 integration seeding
harness, so they must be run with `src/backend` as both the import root and the
pytest rootdir.

## Exact invocations

Run all four from the repository root:

```bash
cd src/backend

# S0a — authenticated cross-tenant VPR export
PYTHONPATH=$PWD uv run pytest \
  ../../docs/evidence/p1-repro/s0a_export_idor_test.py::test_s0a_authenticated_attacker_exports_victim_vpr \
  -v -s -p no:cacheprovider --rootdir=$PWD

# S0a — all 9 registered P-05 routes re-run with an AUTHENTICATED attacker
PYTHONPATH=$PWD uv run pytest \
  ../../docs/evidence/p1-repro/s0a_export_idor_test.py::test_p05_cases_with_real_authenticated_attacker \
  -v -p no:cacheprovider --rootdir=$PWD

# S0b — S3 fallback, with a matched control
PYTHONPATH=$PWD uv run pytest \
  ../../docs/evidence/p1-repro/s0b_status_fallback_test.py \
  -v -s -p no:cacheprovider --rootdir=$PWD

# S11d — GPA float
PYTHONPATH=$PWD uv run pytest \
  ../../docs/evidence/p1-repro/s11d_gpa_float_test.py -v -s -p no:cacheprovider

# S25 — empty user_id state transition, with a control
PYTHONPATH=$PWD uv run pytest \
  ../../docs/evidence/p1-repro/s25_state_machine_test.py -v -s -p no:cacheprovider
```

## Reading the assertions — important

These tests are written **inverted**: they PASS when the defect is present.
`test_s0a_…` asserts `status == 200 and leaked_via_docx`, i.e. it passes when the
attacker successfully exfiltrates. A green run is a demonstration of the bug, not
of correctness. Invert the assertion to convert any of them into a regression
test after a fix.

`s0b_status_fallback_test.py` and `s25_state_machine_test.py` each ship a
**control** case alongside the defect case. The control is the load-bearing part:
it shows the mechanism works correctly under the expected condition, which is
what separates a real defect from a broken harness.

## Known harness caveats — audit these before trusting the results

1. All four run against **moto**, in-process. They exercise handler logic only.
   They do **not** traverse API Gateway, the Cognito authorizer, WAF, or any IAM
   policy. A handler-level leak proved here could in principle be blocked at the
   edge; the P1 session checked the deployed method's authorizer separately and
   found `COGNITO_USER_POOLS` with no resource-level authorization, but that is
   a separate observation, not part of these tests.
2. `s0a`/`s0b` construct events with `seeding.authed_event(...)`, which builds a
   REST-v1-shaped event with `requestContext.authorizer.claims.sub`. If the
   deployed API ever moves to HTTP API v2, these events stop being representative.
3. `s11d_gpa_float_test.py` constructs a `UserCV` directly with `gpa=3.8`. It
   proves the DAL rejects a float; it does **not** prove the live CV parser ever
   emits one. That step needs a deploy.
4. Bucket/table names are test-local (`p05-*`), not the devx resources.
