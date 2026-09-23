# HANDOFF 01 — attach the safety net that already exists

**Model: Sonnet 5, high effort.** This is mechanical, well-scoped work against
known files — no architecture, no ambiguity. Escalate to **Opus 5, high** only
if Task 6 turns the suite red in a way that implicates product code rather than
test config. **Fresh session at the repo root, on `tools/proof-harness`.**

Parent plan: `docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md`. Read its
"The handoff chain" section before starting — it defines the rules you work
under, including what to do when a result surprises you.

Paste everything below the line.

---

You are executing **handoff 01** of a chain. Each handoff runs in a fresh
session and verifies the previous one's claims before doing its own work,
because a session cannot be trusted to certify work it just did.

There is no handoff 00. Your Step 0 instead verifies the **measurements in the
program plan**, which were taken in a planning session that wrote no proof file
— so they are, by this chain's own rules, unproven claims until you reproduce
them.

## Read first, in this order

1. This document.
2. `docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md` — sections W4.00, W4.01, and
   "The handoff chain".
3. `docs/HARNESS.md` — proof discipline and the three-result rule.
4. `CLAUDE.md` — mandatory check commands per changed path.

Do **not** open the `ASTRA-*` docs or `docs/evidence/p1-repro/`. Settled
history, not open questions.

## Step 0 — Verify the plan's measurements

Run these before touching anything. Each has a predicted value. Record observed
values in your proof file whether they match or not.

| # | Command | Predicted |
|---|---|---|
| 0.1 | `cd src/backend && uv run pytest --collect-only -q 2>&1 \| tail -1` | `1864 tests collected` |
| 0.2 | `cd src/frontend && npx jest --config jest.config.ts --listTests \| wc -l` | `63` |
| 0.3 | `cd src/frontend && npx jest --config jest.config.ts --listTests \| grep -c 'application-hub-flow\|artifact-viewers'` | `0` |
| 0.4 | `grep -c 'passWithNoTests' -r .github/workflows/` (sum) | `3` |
| 0.5 | `grep -rn 'uv run pytest' .github/workflows/pr-validation.yml -A4` | four named files, no bare `pytest` |
| 0.6 | `grep -rln 'make deploy' .github/workflows/ \| wc -l` | `10` (9 real + `deploy-staging.yml`'s comment) |
| 0.7 | `cd src/backend && uv run pytest --collect-only -q 2>&1 \| grep -c PytestUnknownMarkWarning` | `≥1` (`pytest.mark.static` is unregistered) |
| 0.8 | `cd src/backend && uv run pytest tests/unit/test_job_handler.py -q \| tail -1` | `7 passed` — the same file errors in the combined run; this is the contamination reproduction |

**If any predicted value is wrong:** that is a finding, not a blocker. Record
expected vs. observed, note it in your handoff-02 draft, and continue — unless
0.1 or 0.5 is wrong, in which case the shape of this handoff's work has changed
and you should stop and report.

## Step 1 — Reproduce the baseline (the planning session already ran it)

The planning session ran the full suite for the first time in the project's
history and recorded the result below. **Reproduce it before trusting it** —
that is this chain's whole premise.

```bash
cd src/backend
uv run pytest -q --tb=no -p no:cacheprovider 2>&1 | tail -3
```
Recorded: **`606 failed, 1100 passed, 54 skipped, 4 xfailed, 100 errors`** (131s)

Then, one directory at a time:

```bash
for d in tests/unit tests/integration tests/infrastructure tests/e2e \
         tests/models tests/regression tests/security tests/infra; do
  printf "%-24s " "$d"
  uv run pytest "$d" -q --tb=no -p no:cacheprovider 2>&1 | tail -1
done
```

| Directory | Recorded isolated result |
|---|---|
| `tests/unit` | 1430 passed, 15 skipped, 4 xfailed, **0 failed** |
| `tests/integration` | 185 passed, **11 failed**, 17 skipped |
| `tests/infrastructure` | 81 passed, **1 failed**, 1 skipped |
| `tests/regression` | 37 passed, **2 failed** |
| `tests/e2e` | 4 passed, 21 skipped |
| `tests/models` · `security` · `infra` | 18 · 3 · 34 passed, 0 failed |

**606 combined → 14 isolated.** ~592 failures and all 100 errors are
**cross-test contamination**, not broken behavior. Demonstrated:
`tests/unit/test_job_handler.py` passes 7/7 on its own and raises
`ModuleNotFoundError` in the combined run — something earlier in the session
mutates `sys.modules` or `sys.path`. (Confirmed not a `PYTHONPATH` artifact: the
file passes identically with and without `PYTHONPATH` set.)

**If your numbers differ from the table**, record both and keep going — a
difference is itself a finding, and one likely cause would be order-dependence,
which would make the contamination worse than recorded, not better.

### What this means for your work

The branch point in the original draft of this handoff **has already fired**,
and it resolved in an unusual direction: the suite is not broken, it is **not
isolated**. So:

- **Do not** wire CI to a single bare `uv run pytest`. It is 606-red and would
  make the gate useless on day one.
- **Do** wire CI as **one job per directory** (Step 3). That sidesteps
  contamination entirely and puts ~1792 tests in front of every PR today.
- **Do not** fix the contamination in this session. It is handoff 02's scope.
  Diagnosing which module poisons `sys.modules` across 250 files is its own
  piece of work and will consume this session if you let it.

**Why CI looks the way it does.** The narrow `-k` filters and hand-named file
lists across the workflows are almost certainly a *workaround* for this, not an
oversight — someone hit the combined failure and never wrote down why. Treat the
existing narrow filters as evidence of a known-but-undocumented problem rather
than as carelessness.

## Step 1b — The 14 real failures, and what they point at

```
tests/integration/test_company_research_vpr.py          5  (VPR)
tests/integration/test_vpr_e2e.py                       3  (VPR)
tests/integration/test_vpr_pipeline_contract.py         2  (VPR)
tests/regression/test_pipeline_stages.py                1  (VPR signature)
tests/regression/test_no_placeholder_fallbacks.py       1  (VPR-adjacent)
tests/integration/test_l0_phase_integration.py          1
tests/infrastructure/test_p02_billing_reconcile_entrypoint.py  1
```

**12 of 14 touch VPR — and journey step J5 is "VPR generates."** The suite
already knows the next journey step after the J4 blocker is broken; nothing was
running it to say so. This is *consistent with* open bug **S7** ("VPR
quality-check failure silently serves generic filler as success"), but that link
is INFERENCE and has not been verified — do not report it as established.

**Your job here is to classify, not to fix.** For each of the 14, determine:
(a) genuinely broken product code, (b) stale test asserting removed behavior, or
(c) environment/setup. Record the classification in your proof file. Fix only
the (b) and (c) cases, which should be cheap. **Leave the (a) cases alone** —
if VPR generation is genuinely broken, that is a product defect worth its own
handoff and its own journey measurement, not a side quest inside a CI task.

Quarantine any (a) case with `pytest.mark.xfail(strict=True, reason="<bug id>")`
so the gate can go green without the failure being forgotten — `strict=True`
means it fails loudly the day someone fixes it.

## Proof obligations for this handoff

Declared before the work, so the bar cannot move to fit the result. Every row
must be filled in with an observed value, matched or not.

| Claim | Command | Before | After (target) |
|---|---|---|---|
| Combined-run baseline reproduces | `uv run pytest -q --tb=no \| tail -1` | `606 failed, 1100 passed` | same (unchanged — you are not fixing this) |
| Per-directory failures resolved | the Step 1 loop | 14 failed | **0 failed** (fixed or `xfail(strict=True)`) |
| Each of the 14 classified | your proof file | unclassified | 14 rows, each (a)/(b)/(c) |
| Two orphaned files now run | `npx jest --listTests \| grep -c 'application-hub-flow\|artifact-viewers'` | 0 | 2 |
| Jest collection grew by exactly 2 | `npx jest --listTests \| wc -l` | 63 | 65 |
| Their tests execute | run them | never run | 7 tests pass, or deleted with reason |
| PR validation runs all 8 directories | `grep -c 'tests/' .github/workflows/pr-validation.yml` | 1 | 8 |
| Frontend runs on PR | `grep -c 'npm run test' .github/workflows/pr-validation.yml` | 0 | ≥2 |
| No `--passWithNoTests` | `grep -rc 'passWithNoTests' .github/workflows/` | 3 | 0 |
| No silent skip on unset API_BASE | `grep -c "pytest.skip('API_BASE" src/backend/tests/integration/integration_helpers.py` | 1 | 0 |
| Markers registered | `uv run pytest --collect-only -q 2>&1 \| grep -c PytestUnknownMarkWarning` | ≥1 | 0 |

Note the first row: the combined 606 is expected to **stay 606**. You are not
fixing contamination in this session, and a changed number there means something
you did had a side effect worth understanding.

Write results to `docs/evidence/handoff-01-<timestamp>-<sha>.json` with
`git_sha` / `git_dirty` per `HARNESS.md`. **Commit the untracked evidence
directory first** so the proof is not marked `git_dirty: true` — a dirty proof
is non-reproducible and handoff 02 will reject it.

## Step 2 — Un-orphan the two dead test files

`tests/e2e/application-hub-flow.e2e.test.ts` (5 tests, 17 assertions) and
`tests/e2e/artifact-viewers.e2e.test.ts` (2 tests, 4 assertions) are executed by
nothing: both are listed in jest's `e2e` project `testPathIgnorePatterns`
(`jest.config.ts`), neither appears in `vitest.config.ts`'s `include`, and
neither has the `.spec.ts` extension Playwright matches.

Remove the two `testPathIgnorePatterns` entries and run them. Expect them to
fail first — they were excluded for a reason nobody recorded. **If they fail,
that is the expected outcome, not a setback.** Fix or, if they test removed
behavior, delete them with the reason in the commit message. Do not silently
re-ignore them; a third state of "excluded and forgotten" is what created this.

## Step 3 — Make PR validation actually validate

`.github/workflows/pr-validation.yml` is the only `pull_request` workflow. Its
pytest step names four files out of 250.

**Do not replace it with a bare `uv run pytest`** — that is 606-red (Step 1).
Run one step per directory so contamination cannot cross a boundary:

```yaml
- name: Backend suite (per-directory — see HANDOFF-01 Step 1)
  working-directory: src/backend
  run: |
    fail=0
    for d in tests/unit tests/integration tests/infrastructure tests/e2e \
             tests/models tests/regression tests/security tests/infra; do
      echo "::group::$d"
      uv run pytest "$d" -q --tb=short || fail=1
      echo "::endgroup::"
    done
    exit $fail
```

The loop must **not** stop at the first failing directory — a gate that hides
the other seven results teaches you one bug at a time. Collect all, fail once.

Leave a comment in the workflow pointing at this handoff, so the next person to
read it learns *why* it is per-directory rather than assuming it is clumsy and
"simplifying" it back into a single red command.

## Step 4 — Run the frontend suites on PR

No frontend test runs on a pull request today. `ui-upgrade-checks.yml` and
`db-redesign-checks.yml` are branch-filtered to `ui-upgrade` / `db-redesign`;
`deploy-frontend.yml` runs on push to `main`, i.e. after merge.

Add jest and vitest jobs to `pr-validation.yml`, and remove `--passWithNoTests`
from all three existing invocations — it converts "the selector matched
nothing" into a green check, which is the same class of lie as an
assertion-free test.

Do **not** add Playwright here. The 26 specs are 282 blocks / 113 assertions
and mostly hollow (plan section W4.0). Automating them now would automate a
false signal. `journey.spec.ts` gets a trigger in a later handoff, after the
hollow specs are dealt with.

## Step 5 — Turn silent skips into failures

`src/backend/tests/integration/integration_helpers.py:100`:
`pytest.skip('API_BASE is not set. Skipping integration tests.')`

Nine more skips fire on a missing module or payload — three in
`test_interview_prep_context_sources.py` on *"module not available"*. **A suite
that skips when an import is broken reports green for a broken import.**

Convert each: a missing module or unimportable target must **fail**. A genuinely
optional environment (a real deployed API) may stay conditional, but as
`pytest.mark.skipif` with an explicit named condition at collection time, never
an in-body `pytest.skip` that silently swallows a runtime problem.

Expect this to turn some tests red. That is the point — they were red already,
reported as skipped.

## Step 6 — Tighten pytest config (separate commit, expect discovery)

In `src/backend/pyproject.toml` under `[tool.pytest.ini_options]`:

1. **Register all markers and add `--strict-markers`.** At least
   `pytest.mark.static` is unregistered today (it warns on every collection).
   Registration first, then strict — reversing that order breaks collection.
2. **`xfail_strict = true`** — an xfail that passes should fail.
3. **Add `freezegun`** as a test dependency. 48 unit and 7 integration files
   call `now()`/`utcnow()`/`today()` with no time-freezing library available.
   Adding the dependency is this handoff's job; converting call sites is not —
   scope that from the count you observe.
4. **`filterwarnings = ["error"]`** and **`pytest-randomly`** — do these **last,
   in their own commit, as discovery instruments.** Both will likely turn the
   suite red: `filterwarnings` promotes every existing warning to a failure, and
   `pytest-randomly` exposes order-dependence that has been invisible forever.

   **If either produces more than ~10 failures, revert that commit, record the
   count and a sample, and hand it to handoff 02.** Do not spend this session
   chasing them. Knowing "random ordering produces N failures" is a complete and
   valuable result; fixing N of them is a different piece of work.

## Deferred proof — belongs to handoff 02, not you

You **cannot** prove the CI changes work. The branch is unpushed and pushing
needs the user's explicit approval (ask; do not assume). Editing a workflow file
is not evidence that GitHub runs it.

State this plainly in your report. Do not write "CI will now run the full
suite." Write "the workflow file now specifies the full suite; execution
unverified." Handoff 02's Step 0 verifies it against a **real Actions run** —
`gh run list --workflow=pr-validation.yml` and the job log showing the collected
test count — which cannot be self-rationalized.

## Ground rules

- Per `CLAUDE.md`, run the mandatory checks for every path you touch before each
  commit. Run `pytest tests/integration/` for anything touching P-05 files.
- **One concern per commit.** Step 2, 3, 4, 5, and each part of 6 are separate
  commits with their proof in the message.
- **Do not deploy.** Do not push without asking.
- Do not fix product bugs you find. Write them down, keep going. This handoff is
  about the instrument, not the product.
- If a step's premise turns out false, stop and report rather than adapting the
  goal to fit (plan → "When a handoff returns something unexpected").

## What success looks like

Every directory passes in isolation — the 14 failures fixed or quarantined with
`xfail(strict=True)` and a recorded reason each. The two orphaned files are
executed by something. `pr-validation.yml` runs all eight backend directories
plus both frontend runners, with no `--passWithNoTests`. Silent skips are
failures. Marker enforcement is on. Whatever `filterwarnings` /
`pytest-randomly` revealed is measured and written down, fixed or not.

**These are also complete, legitimate outcomes — do not treat them as failure:**

- *"Ten of the 14 are genuine VPR product bugs, so I quarantined them with bug
  IDs and the gate is green over 1,782 tests."* Correct. Fixing VPR is not this
  handoff.
- *"`pytest-randomly` produced 200 failures, so I reverted it per Step 6 and
  here is the count and a sample."* Correct. That count is the deliverable.
- *"My Step 1 numbers did not match the recorded ones."* Correct, and important.
  Record both and say so.

**This is not:** wiring the gate before the 14 are resolved, or reporting "CI now
runs the suite" when you could not push.

## Write handoff 02 before you finish

From your actual stopping point, not from this document's forecast. It must
contain:

1. A **Step 0** that verifies your claims — your proof commands with your
   recorded values, plus the real Actions run (`gh run list --workflow=
   pr-validation.yml` and the job log's collected-test count) if the branch was
   pushed. Reading the workflow file is not verification; reading the run is.
2. The next scope. Barring surprises, **the test-isolation contamination**:
   ~592 failures and 100 errors that appear only in the combined run. Give
   handoff 02 the specific reproduction you confirmed in Step 1 —
   `test_job_handler.py` passes alone, errors combined — so it starts from a
   known-good bisection point rather than from 606 failures.
3. Anything you found and deliberately did not fix, including the VPR
   classification from Step 1b. If those turn out to be genuine product bugs,
   say so plainly — it means journey step J5 is broken *and already proven
   broken by tests nobody was running*, which is a materially different starting
   position for the deploy track than the program plan currently assumes.

---

# Appended 2026-09-20 by handoff 00 — what the sweep already settled

Handoff 00 (`docs/handoff/2026-09-20-HANDOFF-00-measurement-sweep.md`) ran after
this document was written. Proof:
`docs/evidence/sweep-00-20260920T082517-b587127.md` / `.json`,
`tools/proof-harness` @ `b587127`, `git_dirty: false`.

**Nothing in this handoff's premise is refuted. Its scope stands unchanged.**
The work below is already done — do not repeat it.

## Step 0 rows the sweep already confirmed

| # | Predicted | Sweep observed | Do you still need to run it? |
|---|---|---|---|
| 0.6 | `10` files reference `make deploy` | **10** — confirmed, and each one adjudicated (see below) | **No** |

## Step 1 — reproduced in full. Do not re-run it.

The sweep ran both the combined and the per-directory baselines and reproduced
your recorded numbers **exactly, to the digit**, in all eight directories:

```
uv run pytest -q --tb=no -p no:cacheprovider
→ 606 failed, 1100 passed, 54 skipped, 4 xfailed, 53 warnings, 100 errors in 144.61s

tests/unit               1430 passed, 15 skipped, 4 xfailed, 0 failed
tests/integration        11 failed, 185 passed, 17 skipped
tests/infrastructure     1 failed, 81 passed, 1 skipped
tests/e2e                4 passed, 21 skipped
tests/models             18 passed
tests/regression         2 failed, 37 passed
tests/security           3 passed
tests/infra              34 passed
```

**606 combined → 14 isolated, confirmed.** Start at Step 1b (classifying the 14).
Your proof obligation "combined-run baseline reproduces" is discharged — cite
this sweep rather than re-running 144 seconds of it.

## Rows the sweep did NOT cover — still yours

**0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.8 were not run.** They are collection-time and
config-time measurements specific to your task and remain in scope. In
particular 0.1 and 0.5 are still the two that can change the shape of your work.

## Four things the sweep found that change your working assumptions

**1. `mypy --strict`, `ruff`, `tsc --noEmit` and `cdk synth` all pass — today.**

```
uv run mypy careervp --strict  → Success: no issues found in 137 source files
uv run ruff check .            → All checks passed!
npm run typecheck              → exit 0, no output
cdk synth                      → Successfully synthesized
```

Nobody had ever run these. They are clean, which means **Step 6 is working
against a green baseline** — any redness `filterwarnings` or `pytest-randomly`
produces is genuinely theirs, not pre-existing noise. It also means your
per-directory CI job in Step 3 can safely add mypy/ruff/typecheck steps without
importing a backlog.

**2. You cannot produce a `git_dirty: false` proof after running the checks.**

This is new, structural, and it will bite you at commit time:

```
M docs/beta/evidence/I2_persistence/persistence-roundtrip-report.json
M docs/beta/evidence/I3_auth/auth-abuse-matrix.json
M src/frontend/dist/tsconfig.tsbuildinfo
```

`tests/integration/test_l2_auth_integration.py` and `test_l1_phase_integration.py`
rewrite tracked evidence files; `npm run typecheck` rewrites a **committed build
artifact**. So the sequence "run the mandatory checks → write the proof" always
yields `git_dirty: true`, which `HARNESS.md` calls non-reproducible.

This is why the 09-14 journey proof was dirty. It is not carelessness.

**Suggested — cheap, in scope, and it unblocks your own proof obligation:**
gitignore `src/frontend/dist/tsconfig.tsbuildinfo`, and point the two evidence
writers at a temp path. Otherwise: run checks, `git checkout --` those three
paths, then write the proof.

**3. Your Step 5 premise is correct but understated.** The sweep did not
enumerate the skips, but it did find the same pathology one level up: five jest
"e2e" billing files (`tests/e2e/*.e2e.test.ts`, 43 assertions) are **pure
tautologies** — `mockApi.post.mockResolvedValue({status: 200})` followed by
`expect(response.status).toBe(200)`. No product code runs.

Relevant to you because **`npm run test:e2e` is what runs them**
(`jest --selectProjects e2e`), and Step 4 adds frontend jobs to PR validation.
Wiring `test:e2e` into the gate would add 43 green assertions that prove
nothing — the exact hazard your own plan warns about for Playwright.
**Recommendation: wire `test:unit`, `test:integration` and vitest in Step 4;
leave `test:e2e` out and hand the tautology cluster to handoff 02.**

Note also that the two orphaned files you un-orphan in Step 2
(`application-hub-flow.e2e.test.ts`, `artifact-viewers.e2e.test.ts`) live in that
same directory and are picked up by that same `--selectProjects e2e` project.
Check whether un-orphaning them changes what `npm run test:e2e` collects.

**4. `CLAUDE.md`'s naming-check command does not run.**

```
$ python src/backend/scripts/validate_naming.py --path infra --strict
command not found: python          (exit 127)
$ python3 src/backend/scripts/validate_naming.py --path infra --strict
                                   (exit 0, no output — passes)
```

There is no `python` on this machine, only `python3`. If you add this to CI or a
pre-commit chain, use `uv run python` or `python3`. In a `&&` chain the current
form is a hard stop; in a `;` chain it is a silently skipped check.

## For your handoff-02 draft — carry these forward

The sweep found these and deliberately did not fix them. They are not yours
either, but handoff 02 should not rediscover them:

- **`preflight.py:366` queries `AWS::DynamoDB::Table` while every table in this
  project is `AWS::DynamoDB::GlobalTable`.** The "10 of 10 tables unmanaged by
  CloudFormation" FAIL is a **false positive** — all 11 devx tables are
  CFN-managed, retained and deletion-protected. The same file's own
  `STATEFUL_TYPES` constant (l.62-63) has both types; only line 366 is wrong.
- **`scripts/ci/changeset_replacement_report.py` has the identical blind spot**,
  and it is load-bearing for the deploy gate — the DynamoDB auto-fail can never
  trigger.
- **31 of 32 devx Lambdas have 1-day log retention** (34 `ONE_DAY` declarations
  in `api_construct.py`, 2 `ONE_WEEK` in the whole tree).
- **`src/backend/careervp/handlers/knowledge_base_handler.py` is routed to
  nothing** — dead code; `/knowledge-base GET` is served by
  `company_research_func`.
- Five of the ten `make deploy` workflows **auto-deploy on a branch push with no
  human gate**, because the `dev` GitHub environment has
  `protection_rules: []`. `db-redesign-checks.yml` auto-deploys to **devx** —
  the stack `make journey` measures.
