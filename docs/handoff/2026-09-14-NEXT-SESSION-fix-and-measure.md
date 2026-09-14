# Next session — measure, then fix

**Model: Sonnet 5, high effort** (this is implementation, not architecture; escalate
to Opus 5 only if step 2 turns into a redesign). **Fresh session at the repo root.**

Paste everything below the line.

---

You are implementing. **This is not an audit.** Three read-only review passes have
already run; their conclusions are settled and are given to you below as
established fact. Do not re-derive them, do not re-litigate them, and do not
produce another verdict document. **Your output is working code and a number.**

## Read first, in this order

1. `docs/handoff/2026-09-14-PLAIN-PLAN.md` — plain-English status and this plan.
2. `docs/HARNESS.md` — the five `make` commands and the proof discipline.
3. `CLAUDE.md` — mandatory check commands per changed path.

Do **not** read the audit YAMLs unless a specific fix needs a detail from them.
They are large and everything you need is summarized here.

## The one rule that matters

`make journey` drives a real browser through the whole product and prints
`REACHED N of 9`. **It has never been run to completion — there is no result on
record.** Every change you make is aimed at raising N.

```
journey  → get N
one change aimed at step N+1
journey  → did N go up?
             up   → commit
             down → REVERT FIRST, investigate second
             flat → the change didn't do what you predicted; read the failing step
```

Never batch several fixes between two journey runs. You will not know which one
moved the number, and a fix that silently breaks an earlier step is the exact
failure this loop exists to catch.

## Step 1 — Get the number (do this before any code change)

```bash
cd src/backend
make preflight          # are the facts I'm about to rely on true?
make journey            # REACHED N of 9
```

`make journey` needs `E2E_TEST_EMAIL` / `E2E_TEST_PASSWORD` and a `BASE_URL`.
If it cannot run, **fixing that is step 1** — report exactly what is missing and
what you did. A journey that cannot run is a worse problem than a low N.

Commit the proof JSON it writes to `docs/evidence/`. Note that
`preflight` reports PASS / FAIL / **UNKNOWN**, and UNKNOWN is never PASS.

Report N before proceeding. If N is already high, the fix list below reorders
around whatever actually blocks step N+1 — the list is a prior, not a plan.

## Step 2 — Fix these three first (confirmed, cheap, independent of N)

Each is verified by execution. Reproduction tests live in
`docs/evidence/p1-repro/` — **read that directory's README first: those tests are
written inverted, so they PASS when the bug is present.** After each fix, invert
the corresponding assertion so it becomes a real regression test, and move it
into the project suite.

### 2a. `S0a` — any logged-in user can export another user's VPR
`src/backend/careervp/handlers/export_handler.py:113-133`. `_read_artifact`
receives `user_id` and passes it to the `cover_letter`, `interview_prep` and
`cv_tailored` branches, then drops it for `vpr`: `_read_vpr(job_id)` reads
`results/{job_id}.json` from S3 with no ownership scoping.

Fix: scope the read to the owner. The VPR's owner is available both in the jobs
table and in the S3 payload's own `user_id` field — pick one deliberately and say
which in the commit message.

### 2b. `S0b` — same leak through the status endpoint's fallback
`src/backend/careervp/handlers/vpr_status_handler.py:542-558`. When `get_job`
returns `None`, line 547 calls `_try_build_response_from_s3(vpr_id)`, which takes
no `user_id` and returns the full VPR plus a presigned download URL. The owner
check sits at 555-558, *below* it.

Two triggers, both real: the job row is genuinely absent, **or** `get_job`
returned `None` because of a transient DynamoDB error
(`jobs_repository.py:217-223` catches `ClientError` and returns `None`). The
second needs no expiry and can happen at any time.

Fix: move the ownership check above the fallback, and make the fallback scope by
owner. Do **not** rely on the record's age — the "24 hour" framing in the
original report is wrong; completed jobs carry roughly one-year TTLs.

### 2c. `K9` — the cleanup job has never once succeeded
`src/backend/careervp/handlers/artifact_cleanup_handler.py:135` calls
`require_table_env('DYNAMODB_TABLE_NAME', purpose='jobs')`. Its Lambda
environment (`infra/careervp/api_construct.py:2716-2721`) is
`**self._build_shared_table_env()` plus `VPR_RESULTS_BUCKET_NAME`, and
`_build_shared_table_env` (`:1197-1211`) does not include `DYNAMODB_TABLE_NAME`.
Live metrics: **336 errors across 336 invocations in 14 days**, with a matching
`MissingTableEnvError` in the logs.

Fix: pass the correct jobs-table name from infrastructure. Do **not** add a
fallback default — that would hide the next occurrence of exactly this bug.
Add an alarm or a test that fails if the variable is absent.

## Step 3 — Repair the fake safety net

`tests/unit/test_p04_p05_auth_idor.py` contains a ratchet asserting every
authenticated route carrying someone else's resource ID has a cross-tenant probe.
It is green and it is hollow, for two independent reasons:

1. `tests/integration/test_p05_cross_tenant_idor.py` attacks with
   `forged_header_event` — **no login at all**. Since the identity-header bypass
   was removed, all nine cases stop at the 401 front door and never reach any
   ownership code. The file's own docstring admits this.
2. `tests/integration/p05_owner_check_registry.py:109` pins the export case to
   `moduleType: 'cv_tailored'` — one of the branches that *is* scoped. The `vpr`
   branch, the one that leaks, is never exercised.

Required changes:
- Attack as a **legitimately authenticated different user**. The helper already
  exists and is unused: `seeding.authed_event(...)` in
  `tests/integration/p05_seeding.py`.
- Parameterise the export case across **all four** `moduleType` values.
- **Add an owner-positive control to every denial case.** Pass B found the export
  fixture returns 404 *for the rightful owner* and the gap fixture returns empty
  *for the owner* — so "the attacker got nothing" proved nothing. A denial test
  without a positive control is not evidence.
- Keep the forged-header case as a separate P-04 regression test. It is fine; it
  just must not be what certifies ownership.

Also fix `docs/evidence/p1-repro/s0a_export_idor_test.py`: two of its assertions
label an empty HTTP 200 as "served cross-tenant data" when no data was served.
Split assertions into authentication / ownership-denial / actual-content-disclosure
/ fixture-validity. **Do not simply relax them until they pass.**

## Step 4 — Close the deploy gate (P-28)

The contract (`project-scope-lock.yaml:106`) requires automation to be read-only
with human-only change-set execution. Reality:

- `origin/main`'s `deploy.yml` runs `make deploy` (a full `cdk deploy
  --require-approval=never`) on every push to main;
- `deploy-vpr-async.yml:285` does the same with `cdk deploy --all`;
- `deploy-staging.yml` deploys on push to develop, and `make deploy` hardcodes
  the **dev** stack, so the staging workflow deploys dev;
- the branch's compliant workflow gates on GitHub environment `deploy-dev`,
  which **returns 404** and would be auto-created unprotected on first run.

Fix the workflows, create the environment with a required reviewer, and set
concurrency `max=1` without `cancel-in-progress` (a second merge must never
cancel an in-flight infrastructure update).

Separately: provision genuinely **read-only** AWS credentials for future review
work. All three audit passes ran as `presgen_user`, which is in the
`AdminAccess` group.

## Step 5 — Re-measure and report

```bash
cd src/backend && make journey && make state
```

Report the new N, and `make compare KIND=journey` against the first proof.

## Ground rules

- **Per `CLAUDE.md`, run the mandatory checks for every path you touch** before
  each commit: backend `ruff format . && ruff check --fix . && mypy careervp
  --strict` and `pytest tests/unit/`; frontend `npm run typecheck && npm run
  test:unit`. Use `scripts/git/safe_commit.sh`.
- Also run `pytest tests/integration/` when you touch the P-05 files. `CLAUDE.md`
  documents only `tests/unit/`, which is precisely how the hollow probe survived.
- **Do not deploy.** Prepare change sets; a human executes them.
- One fix per commit, with the journey number before and after in the message.
- If a fix turns out to be larger than described here, stop and report rather
  than redesigning. Two of the original reports were wrong about mechanism; a
  third may be.
- If you find something new, write it down and keep going. Do not start a fourth
  audit.

## What success looks like

A higher N than you started with, proven by a committed journey proof; three
confirmed security/reliability bugs fixed with real regression tests; a
cross-tenant suite that fails when ownership is broken; and a deploy pipeline
that cannot reach AWS without a human. Nothing about this session's success
depends on producing another analysis document.
