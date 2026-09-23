# HANDOFF 02 — test isolation (the contamination behind the 606)

**Model: Opus 5, high or xhigh effort.** Handoff 01 downgraded this from the
program plan's "Sonnet 5, high" because the root cause is no longer a black
box — you are starting from a confirmed, minimal, two-file reproduction and a
named list of 7 more suspect files, not from 606 failures. But bisecting
`sys.modules` pollution across the remaining unknown culprits and deciding
how to restore state safely is exactly the kind of debugging where a wrong
first guess costs a full session. Escalate to **xhigh** if the fix touches
more than the CDK-synth test files named below. **Fresh session at the repo
root, on `tools/proof-harness`** (or wherever this branch has landed after
review — check with the user first if unsure).

Parent plan: `docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md`. Read its
"The handoff chain" section before starting.

Paste everything below the line.

---

You are executing **handoff 02** of a chain. Handoff 01 wired CI to the
1,864 (now 1,862 — see Step 0) tests that already exist, running per
directory to sidestep a whole-suite contamination bug it deliberately did
not fix. Your job is that bug.

## Read first, in this order

1. This document.
2. `docs/handoff/2026-09-19-HANDOFF-01-ci-wiring.md` in full — it now carries
   a sweep-00 appendix too; read that.
3. `docs/evidence/handoff-01-20260920T105523Z-1cdc88a.json` — the proof file
   this handoff verifies. **Read it before reading handoff 01's prose
   summary** — the JSON is the ground truth; the prose is one session's
   account of it.
4. `docs/HARNESS.md` — proof discipline and the three-result rule.
5. `CLAUDE.md` — mandatory check commands per changed path.

Do **not** open the `ASTRA-*` docs or `docs/evidence/p1-repro/`. Settled
history, not open questions.

## Step 0 — Verify handoff 01's claims

Run these from a clean checkout **before doing anything else**. Do not read
handoff 01's prose first — run the commands, then compare.

| # | Command | Handoff 01 recorded |
|---|---|---|
| 0.1 | `cd src/backend && uv run pytest --collect-only -q \| tail -1` | `1862 tests collected` (down from 1864 — 2 stale tests were deleted, not lost by accident; see the proof file) |
| 0.2 | `cd src/frontend && npx jest --config jest.config.ts --listTests \| wc -l` | `63` (unchanged — the "un-orphaned" files became Playwright specs, not Jest tests; see 0.3) |
| 0.3 | `cd src/frontend && npx playwright test --list \| grep -c 'application-hub-flow\|artifact-viewers'` | `7` (5 + 2 tests across the two renamed `.spec.ts` files) |
| 0.4 | `grep -c 'tests/' .github/workflows/pr-validation.yml` | `8` |
| 0.5 | `grep -c "npm run test" .github/workflows/pr-validation.yml` | `2` |
| 0.6 | `grep -rc 'passWithNoTests' .github/workflows/` (summed) | `0` |
| 0.7 | `cd src/backend && uv run pytest --collect-only -q 2>&1 \| grep -c PytestUnknownMarkWarning` | `0` |
| 0.8 | `cd src/backend && for d in tests/unit tests/integration tests/infrastructure tests/e2e tests/models tests/regression tests/security tests/infra; do uv run pytest "$d" -q --tb=no; done` | all 8 directories `0 failed` (some `xfailed`/`xpassed`/`skipped`, never `failed`) |

**If any of these differ:** that is itself a finding. 0.1 and 0.2/0.3 are the
two most likely to drift (a later session could add or remove tests) — a
small drift there is not alarming. **If 0.8 shows any directory `failed`,
stop and investigate before continuing** — handoff 01's whole premise was a
green per-directory gate, and a regression there means something after
`1cdc88a` broke it.

### 0.9 — The real Actions run (do this one for real, not "was the file edited")

Handoff 01 could not push. If the branch has since been pushed and merged (or
is open as a PR), run:

```bash
gh run list --workflow=pr-validation.yml --limit 5
gh run view <run-id> --log | grep -c "::group::tests/"
```

You are looking for **8** `::group::tests/...` markers in the Pytest job's
log (one per directory) and a job log for `Jest (unit + integration)` /
`Vitest` that shows real collected-test counts, not `0 tests found`. If the
branch has not been pushed yet, **that is your first action** — ask the user
to push and open a PR, or ask their explicit approval to do it yourself, then
come back to this step. Reading `pr-validation.yml` is not verification;
reading the run is.

## What handoff 01 found — your starting point

Handoff 01 was supposed to leave whole-suite contamination alone and mostly
did, but investigating the 14 per-directory failures produced a **concrete,
minimal, reproducible root cause** for at least one slice of it, plus a
second finding that changes how you should think about the bug's shape.

### Finding 1 — the smoking gun: an unrestored `sys.modules` eviction

`tests/infrastructure/test_k9_artifact_cleanup_env.py` (`_all_resources()`,
around line 39) does this to force a clean re-import of infra's CDK modules:

```python
sys.path.insert(0, INFRA_SRC)
for module_name, module in list(sys.modules.items()):
    if module_name == 'careervp' or module_name.startswith('careervp.'):
        module_file = str(getattr(module, '__file__', '') or '')
        if not module_file.startswith(INFRA_SRC):
            sys.modules.pop(module_name, None)

from careervp.naming_utils import NamingUtils
from careervp.service_stack import ServiceStack
```

This evicts the **backend's** `careervp` package (and everything under it —
`careervp.handlers`, `careervp.dal`, all of it) from `sys.modules`, then lets
the next `import careervp` resolve fresh. Because `infra/` was just inserted
at `sys.path[0]`, that fresh import binds `sys.modules['careervp']` to
`infra/careervp/__init__.py` — which has no `handlers` subpackage — **for the
rest of the process.** Nothing ever restores the backend's `careervp`.

**Minimal reproduction** (confirmed in handoff 01):

```bash
cd src/backend
uv run pytest tests/infrastructure/test_k9_artifact_cleanup_env.py \
               tests/infrastructure/test_p02_billing_reconcile_entrypoint.py
# -> 1 failed: ModuleNotFoundError: No module named 'careervp.handlers'
uv run pytest tests/infrastructure/test_p02_billing_reconcile_entrypoint.py
# -> 1 passed (alone, no eviction happened)
```

`test_p02_billing_reconcile_entrypoint.py` is quarantined with
`xfail(strict=False, reason=...)` — **not** `strict=True**, deliberately (see
Finding 2) — citing this exact mechanism. **The same unrestored-pop pattern
appears in 6 more files:**

```
test_p16_rate_limited_consumers.py
test_p17_dlq_depth_alarms.py
test_p17_sqs_event_sources_partial_failures.py
test_p18_sqs_visibility_timeout.py
test_p19_sfn_retries_full_jitter.py
test_p20_throttle_load_harness.py
test_p31_eventbridge_target_dlqs.py
```

None of these were investigated for whether they *also* trigger the eviction
in practice (some may guard it differently, or may always run in an order
that doesn't matter within `tests/infrastructure` today) — that check is
yours. **Your highest-value first move** is almost certainly: write one
shared, tested helper (context manager or fixture) that does the
evict-for-clean-CDK-import dance *and restores it on exit*, then point all 7
files at it. That is a much smaller, safer change than trying to make CDK
imports and backend imports coexist without eviction at all.

### Finding 2 — the contamination is order-dependent, not just directory-dependent

Handoff 01 also added `pytest-randomly` (kept — 0 failures per directory
across 5+ runs each with different seeds, a real and valuable result on its
own). But running the **combined** suite (`uv run pytest -q`, no directory
filter) with `pytest-randomly` active — which is now the default, since it
auto-activates — produces a **different total every run**:

```
uv run pytest -q --tb=no                    # random order (default now)
  run 1: 465 failed, 1258 passed, 78 errors
  run 2: 655 failed, 1049 passed, 97 errors

uv run pytest -q --tb=no -p no:randomly     # deterministic order
  601 failed, 1100 passed, 100 errors        # ~matches the original 606/100
```

**The `606 failed, 100 errors` baseline from the program plan and handoff 00
was measured under a fixed, alphabetical-ish default order.** It is not a
stable target — the contamination itself is sensitive to *which* CDK-synth
file runs relative to *which* backend-import file, at whole-suite scale, not
only within `tests/infrastructure`. Concretely: **run your bisection with
`-p no:randomly` for determinism while you're isolating a specific pair of
files, then re-verify with `pytest-randomly` on (the default) once you have
a fix**, since a fix that only holds under one fixed order is not a fix.

### What this changes about your approach

- Don't start by trying to explain "606 failures." Start from the two
  confirmed mechanisms above and the concrete reproduction command. Widen
  from there.
- The `sys.modules.pop`-without-restore pattern is a strong hypothesis for
  being the majority contributor, not the whole story — Finding 2 says
  order matters beyond just "did a CDK-synth test run first," so there may
  be a second, independent contamination source (a different global, a
  cache, a monkeypatched env var without teardown). Don't stop looking once
  the 7 named files are fixed; re-run the combined suite (`-p no:randomly`
  fixed order, then confirm with randomly on) and see what's left.
- `tests/conftest.py` already imports the backend's `careervp` at module
  level (line ~13), which is why isolated/small runs tend to "just work" —
  the backend package gets cached before any test body executes. The bug
  only bites when something *evicts* that cache later and re-resolves
  against a `sys.path` that now prefers `infra/`.

## Proof obligations for this handoff

Declared before the work.

| Claim | Command | Before | After (target) |
|---|---|---|---|
| Combined run, deterministic order | `uv run pytest -q --tb=no -p no:randomly \| tail -1` | `601 failed, 100 errors` (handoff-01's re-measurement) | Materially fewer errors — ideally 0, but **a partial reduction with a clear list of what's left is a legitimate, complete outcome** (see below) |
| Combined run, random order (2 samples) | `uv run pytest -q --tb=no \| tail -1` (x2) | varies (465–655 failed) | Both samples' **error** count (not failed — see note) trends toward 0, and the two samples converge closer to each other than 465 vs 655 did |
| The 7 named CDK-synth files no longer evict without restoring | manual read + a regression test (see below) | 1 confirmed offender (test_k9), 6 unconfirmed | All 7 either fixed or confirmed not to reproduce, each with the command that checked it |
| test_p02's xfail can go back to `strict=True` | `uv run pytest tests/infrastructure -p no:randomly` then with random order 5x | currently `strict=False` (order-dependent) | If your fix makes it deterministic, flip back to `strict=True` and say so; if it's still order-dependent, leave `strict=False` and say why |
| No new per-directory failures | the Step 3 loop from handoff 01 | 0 failed/8 | 0 failed/8, still |

Write a **new regression test** that pins this bug class down: something like
"import `careervp.handlers.<anything>` after running any CDK-synth test in
the same process must succeed" — parametrized over the 7 files (8 with
test_k9) if that's tractable, or at minimum a single test that runs
`test_k9_artifact_cleanup_env.py`'s eviction pattern and then asserts
`careervp.handlers` is still the backend's version. This is the test that
would have caught this on day one; write it so it catches it on day two if
it comes back.

**A note on "errors" vs "failed" in the combined run:** Some of the ~601
failed tests are likely genuinely order-independent product-code assertions
(real bugs, not contamination) that you are not obligated to fix here — that
was handoff 01's Step 1b territory for the per-directory 14, and there may
be a handful of others visible only in the combined run. Focus your
attention on the **100 errors** (or however many remain) — those are the
`ModuleNotFoundError`/import-shape signature specific to this contamination
class. A combined run that goes from 601 failed / 100 errors to, say, 550
failed / 5 errors is a strong, complete result even though it isn't 0/0.

## Deferred proof — belongs to whoever picks this up next

You may not be able to prove **zero** contamination in one session — Finding
2 suggests there could be more than one source. State plainly what you
fixed, what you verified is now clean, and what's still red, with the exact
counts. Do not write "contamination is fixed." Write "X of Y known
contamination sources fixed; combined run went from A/B to C/D; here is what
remains and my best hypothesis for it."

## Ground rules

- Per `CLAUDE.md`, run the mandatory checks for every path you touch before
  each commit.
- **One concern per commit** — the shared eviction-safe fixture/helper is one
  commit; each file's migration onto it can be its own commit or batched if
  they're mechanically identical; the new regression test is its own commit.
- **Do not deploy. Do not push without asking.**
- Do not fix unrelated product bugs you find while in here. The handoff-01
  proof file lists several already found and deliberately left alone
  (`CVTailoringRequest.vpr_id` missing a default, the DAL API mismatch in
  `test_dal_migration_integration.py`, the renamed `interview_prep_prompt`
  API, `vpr_handler.py` being dead code). Carry them forward to whichever
  handoff is next; don't absorb them into this one.
- If Finding 2 turns out to point at something bigger than `sys.modules`
  hygiene in 7-8 files — e.g. a real architectural issue with how tests
  share process state — stop and report rather than redesigning the test
  harness unilaterally.

## Carry forward (not yours, but don't rediscover them)

From the handoff-01 proof file's `what_was_not_fixed_deliberately`:

- **`vpr_handler.py` is dead code.** `infra/careervp/api_construct.py` says so
  explicitly ("Original synchronous VPR generator removed... `self.
  vpr_generator_func = None`"), and its own Lambda-wiring method
  (`_add_vpr_lambda_integration`) is defined but never called. The real
  `POST /api/vpr` path is `vpr_submit_handler.py` → SQS →
  `vpr_worker_handler.py`, which persists via
  `core_repository.save_vpr_artifact()`. **This means most of the original
  "12 of 14 touch VPR" finding from the program plan was exercising a
  handler production traffic never reaches** — journey step J5's real health
  is still largely unmeasured. Whoever picks up J5 needs to know this before
  trusting `vpr_handler.py`-based test coverage as a signal.
- `CVTailoringRequest.vpr_id: str | None` has no `= None` default
  (`careervp/models/api_models.py:343`) — breaks the missing-VPR CV-tailoring
  flow at validation, before the correctly-implemented handler logic runs.
  Quarantined at `tests/regression/test_no_placeholder_fallbacks.py::
  test_cv_tailoring_no_raise_on_missing_vpr`.
- `DynamoDalHandler` requires a `table_name` constructor arg and has no
  `save_gap_analysis` / `get_gap_analysis` / `save_interview_prep` methods —
  `tests/integration/test_dal_migration_integration.py` assumes an API that
  doesn't exist. Quarantined, all 3 tests in the file.
- `careervp.logic.prompts.interview_prep_prompt.build_interview_prep_prompt`
  was split into `build_system_prompt()` + `build_user_prompt(...)`;
  `careervp.logic.interview_prep.generate_interview_prep_questions` was
  renamed to the async `generate_interview_prep`. 4 tests in
  `tests/integration/test_interview_prep_context_sources.py` silently
  skipped on the old names forever; now quarantined with `xfail(strict=True)`.
- **`filterwarnings = ["error"]` produces 137 failures**, ~126 of them one
  systemic cause (`aws_lambda_powertools` "No application metrics to
  publish" `UserWarning`, fired by every test that invokes a
  `@metrics.log_metrics`-decorated handler without recording an app metric).
  Separately: a handful of `RuntimeWarning`/`PytestUnraisableExceptionWarning`
  about **coroutines never awaited** (`generate_gap_questions`,
  `_async_process_record`, `AsyncMockMixin._execute_mock_call`) — these read
  as real bugs (a missing `await`), not noise, and are worth a dedicated look
  independent of the metrics-warning mass. Full breakdown in the proof file.
- 48 unit + 7 integration files call `now()`/`utcnow()`/`today()` with no
  time freezing applied. `freezegun` is now a dependency (handoff 01); no
  call site uses it yet.

---

*Handoff 01's actual stopping point, for context: all 6 of its steps landed,
all 8 backend directories are 0-failed, frontend runs on PR, the two orphaned
e2e files are real (executable, credential-blocked) Playwright specs, markers
are registered, and `pytest-randomly` is on. The branch is unpushed pending
review.*
