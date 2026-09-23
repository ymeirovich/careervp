# Production program — from N=3 to a product you can sell

This supersedes `2026-09-14-NEXT-SESSION-deploy-and-continue.md` as the top-level
plan. That document is still correct about the deploy track; it is one of five
workstreams here, not the whole job.

Every number in this document was measured on 2026-09-19 against
`tools/proof-harness` @ `eed027b`. Commands are given so any claim can be
re-checked rather than believed.

---

## Position — measured, not assumed

| Fact | Value | How to re-check |
|---|---|---|
| Branch state | 12 commits, **unpushed**, no PR | `git ls-remote origin tools/proof-harness` (empty) |
| Journey | **3 of 9** | `docs/evidence/journey-20260914T100043-5022510.json` |
| Latest journey proof | `git_dirty: true`, `deployed_sha: ""` | same file — **non-reproducible per HARNESS.md** |
| Preflight | 7 PASS / 1 UNKNOWN / 1 FAIL | `docs/evidence/preflight-20260914T101001-5022510.json` |
| DynamoDB tables unmanaged by CFN | **10 of 10** in devx | preflight `premises[].observed.unmanaged` |
| Workflows still running ungated `make deploy` | **9** | `grep -rln "make deploy" .github/workflows/` |
| Lambdas | 31 | `grep -c "_lambda.Function(" infra/careervp/api_construct.py` |
| Distinct table env var names | 18+ | `grep -rhoE "[A-Z_]+TABLE[A-Z_]*" src/backend/careervp/ \| sort -u` |
| Table env assignments | 52 | `grep -c 'TABLE_NAME":' infra/careervp/api_construct.py` |
| Backend / frontend LOC | 36,084 / 16,319 | `find ... \| xargs wc -l` |
| e2e specs | 26 files, 291 blocks, 127 assertions | `src/frontend/tests/e2e/` |
| e2e excluding `journey.spec.ts` | **282 blocks, 113 assertions** | see W4 |
| V1 features with zero e2e spec | **6 of 9** | VPR, interview prep, company research, knowledge base, auth, export |

**The two facts that should govern sequencing:**

1. The instruments are not yet trustworthy. 282 test blocks report green while
   asserting nothing, and the one journey proof we have is marked
   non-reproducible by the harness's own rule.
2. Nothing is deployed. Four verified fixes sit in local commits.

Work that depends on trustworthy instruments must not start until W4 has made
them trustworthy. Work that is pure static analysis (W2, W3) can start now.

---

## Workstream map

```
W0  Deploy-track prerequisites  ──┐
W1  Gated deploy + re-measure   ──┴─→ needs human approval, blocks nothing else
W2  Table architecture           ──┐
W3  Dead code / dead API sweep  ──┴─→ static, can run today, no deploy needed
W4  Test integrity + per-feature e2e + feature ledger  ← gates "production ready"
W5  P-28 completion (9 workflows)                      ← gates "safe to deploy"
W6  Environment rebuildability
W7  Lambda runtime configuration ──┐
W8  Performance and load           │  added 2026-09-23 — the running system,
W9  API contract correctness       │  not the deploy path. None was covered
W10 Security (authz, keys, deps) ──┘  by W0-W6.
```

W2/W3/W4 are independent of W0/W1 and of each other. W5 is independent of
everything and is the only one with an active exposure (auto-deploy on push).

**W7-W10 were added 2026-09-23** after an AWS audit found that W0-W6 cover the
deploy path, the table map and the test estate, but never the configuration,
performance, contract integrity or authorization model of the running system.
W7's log-retention item blocks the others: at 1-day retention, any diagnosis
performed under W8-W10 is unreproducible the next day.

---

## W0 — Deploy-track prerequisites (blocking, small, do first)

These are three small commits. Without them the first gated deploy produces a
result nobody can act on.

**W0.1 — The deploy and the measurement point at different stacks.**
`make journey` measures `HARNESS_STACK ?= CareerVpCrudDevx` (`src/backend/Makefile:29`).
Merging to `main` auto-runs `create-change-set-dev`, hardcoded
`STACK_NAME: 'CareerVpCrudDev'` (`.github/workflows/deploy.yml:37`). Following
the old handoff literally deploys **Dev** and then measures **Devx** — N stays
at 3 and the session debugs a fix that was never deployed.

A gated devx path already exists: `deploy.yml`'s `workflow_dispatch` maps
`environment: devx → CareerVpCrudDevx` (`deploy.yml:279`). Use that
deliberately. **Action:** document it in the deploy runbook; do not rely on the
on-merge job.

**W0.2 — `create-changeset` does not stamp the git SHA.**
`Makefile:146-152` passes only `allowed_origins`. Only `deploy-devx` passes
`--context git_sha=$(GIT_STAMP)` (`Makefile:135`). So the P-28-compliant route
produces a stack with **no `DeployedGitSha` output** → `make journey` records
`deployed_sha: unstamped` → you cannot prove the journey ran against the new
code. This is the UNKNOWN in preflight, and under the gated flow it is permanent
rather than self-resolving. **Action:** add `--context "git_sha=$(GIT_STAMP)"`
to `create-changeset`. One line.

**W0.3 — Commit the untracked evidence.**
`docs/evidence/journey/20260914T081644-3fc5e54/` and the 09-14 handoff are
untracked, which is why the latest proof carries `git_dirty: true`. Per
`HARNESS.md`, a dirty proof is non-reproducible — so the current "3 of 9" is not
admissible as a baseline. **Action:** commit both, then the post-deploy proof is
a valid comparison.

## W1 — Gated deploy and re-measure (human-executed)

1. Push `tools/proof-harness`, open PR against `main`. **Requires explicit
   go-ahead.**
2. Human review and merge.
3. Create the changeset against **`CareerVpCrudDevx`** via `workflow_dispatch`
   (not the on-merge dev job — see W0.1).
4. Read the Replacement report. If `scripts/ci/changeset_replacement_report.py`
   flags any `RestApi`/`Table`/`Bucket`/`UserPool` as `Replacement: True`, **do
   not approve** — CloudFormation intends to delete and recreate a stateful
   resource.
5. Human approves the `deploy-dev` environment gate.
6. Confirm `DeployedGitSha` matches HEAD before trusting any subsequent journey
   result.
7. Re-run `make journey`. Expected: the quota fix (`ce850d5`) may move N; S0a,
   S0b and K9 are not exercised by J1–J4 and will not.

**Do not deploy yourself.** A human executes and approves.

---

## W2 — Table architecture normalization

**The problem, concretely.** From `infra/careervp/api_construct.py:2517-2526`,
the gap Lambda:

```python
"GAP_QUESTIONS_TABLE_NAME": self.api_db.db.table_name,
"USERS_TABLE_NAME":         self.api_db.db.table_name,
"DYNAMODB_TABLE_NAME":      self.api_db.db.table_name,
"JOBS_TABLE_NAME":          self.api_db.jobs_table.table_name,
# Gap questions use pk/sk keys — must point to the users table, not artifacts_table.
```

Four table env vars, three aliasing one physical table, and a code comment
memorializing a prior misrouting bug. Across the stack: 18+ distinct table env
var names, 52 assignments, 31 Lambdas. Open bug **S8** is literally *"cover
letters generate with no gap answers (wrong table lookup)"* — the same
pathology, already shipped.

This is the class of defect where an artifact writes to one table and reads from
another. It cannot be found by reading code linearly; it needs a map.

**W2.1 — Build `scripts/table_map.py` as a harness instrument** (sibling of
`preflight.py`). It must emit, as a reproducible JSON proof:
- every env var name → the physical table it resolves to, per Lambda
- every alias group (N env names → 1 table)
- every read site and write site per artifact type (VPR, gap, tailored CV,
  cover letter, interview prep, company research, knowledge)
- **flagged:** any artifact type whose read table ≠ its write table
- **flagged:** any env var referenced in code but never set in CDK, or set but
  never read

Output is a report, not prose. It re-runs after every change and can gate CI.
This is the same move the repo already made with `preflight`, applied to code.

**W2.2 — Fix what it finds**, one artifact type per commit, each with a test
that fails before and passes after.

**W2.3 — The architectural decision, separately.** Whether this should be
single-table or multi-table, and what the migration looks like, is a genuine
design question with live data at stake — made harder by the fact that 10 of 10
devx tables are not CloudFormation-managed (see W6). Do not answer it inside a
bug-fix commit. Scope it as its own piece of work once `table_map.py` has
produced the actual map.

## W3 — Dead code, dead APIs, unreachable frontend

Same instrument pattern, same reason: these are decidable mechanically, and the
failure mode is *missing things*, not misjudging them.

**W3.1 — `scripts/dead_api.py`:** every API Gateway route → handler → frontend
caller. Flags routes with no caller, handlers with no route, and routes whose
handler no longer exists.

**W3.2 — `scripts/dead_code.py`:** unreferenced modules, functions and exports
across 35 handlers / 28 logic modules / 16 DAL modules / 24 frontend pages.

**W3.3 — Remove what they find,** in reviewable batches, each verified by the
existing unit suite plus `make journey`.

---

## W4 — Test integrity, per-feature e2e, and the feature ledger

**This workstream gates any claim of production readiness.** It is also the one
with an active hazard: adding good tests to a suite that lies produces a suite
that lies more convincingly.

### W4.00 — The whole test estate (measured 2026-09-19, AST pass)

**The backend suite is healthy. The problem is that almost nothing runs it.**

| Suite | Files | Tests | No assertion | Empty body |
|---|---|---|---|---|
| `tests/unit` | 163 | 1,322 | 14 | 3 |
| `tests/integration` | 39 | 180 | 5 | 0 |
| `tests/infrastructure` | 25 | 78 | 5 | 0 |
| `tests/regression` | 5 | 39 | 0 | 0 |
| `tests/e2e` (pytest) | 10 | 25 | 2 | 0 |
| `tests/infra` · `models` · `security` | 8 | 48 | 0 | 0 |
| **backend total** | **250** | **~1,692** | **26 (1.5%)** | **3** |

Frontend: **jest 63 files · vitest 65 files · playwright 26 specs.**

**The finding that matters most — CI runs almost none of it:**

- `pr-validation.yml` is the only workflow on `pull_request`. Its pytest step
  runs **four named files**: `test_auth_handler.py`, `test_health_handler.py`,
  `test_billing_service.py`, `test_cv_tailoring_delete_roundtrip.py`. Four, out
  of 250.
- The **only** workflow running a full `uv run pytest` is
  `gap-remediation.yml`, and it is path-filtered to `**/gap*`. A PR touching
  `export_handler.py` never triggers it.
- Every other pytest job is `-k`-filtered to one feature.
- **No frontend test runs on a pull request at all.**
  `ui-upgrade-checks.yml` and `db-redesign-checks.yml` are branch-filtered to
  the `ui-upgrade` / `db-redesign` branches; `deploy-frontend.yml` runs on
  **push to `main`** — i.e. after merge. All three pass `--passWithNoTests`,
  which turns a broken project selector into a green check.
- The 26 Playwright specs run **only** via `e2e-smoke.yml`, which is
  `workflow_dispatch`-only and requires a hand-supplied Amplify preview URL.
  They have no automatic trigger of any kind.

~1,692 backend tests and 128 frontend test files exist. A typical PR validates
**4 backend files and 0 frontend files.** The safety net is built; it is not
attached to anything.

### The suite was run in full for the first time — 2026-09-19

Nobody had ever done this. The result reframes the workstream.

```
uv run pytest -q            →  606 failed, 1100 passed, 54 skipped, 100 errors
```

**But run one directory at a time, the same tests pass:**

| Directory | Isolated result |
|---|---|
| `tests/unit` | **1430 passed**, 15 skipped, 4 xfailed, 0 failed |
| `tests/integration` | 185 passed, **11 failed**, 17 skipped |
| `tests/infrastructure` | 81 passed, **1 failed**, 1 skipped |
| `tests/regression` | 37 passed, **2 failed** |
| `tests/e2e` · `models` · `security` · `infra` | 59 passed, 21 skipped, 0 failed |
| **total** | **~1792 passed, 14 failed** |

**606 failures collapse to 14 when directories run separately.** ~592 failures
and all 100 errors are **cross-test contamination**, not broken behavior —
`tests/unit/test_job_handler.py` passes 7/7 alone and raises
`ModuleNotFoundError` in the combined run, the signature of something earlier
mutating `sys.modules` / `sys.path`.

**This is the root cause of the CI wiring problem**, and it is more interesting
than "nobody wired it." The narrow `-k` filters and hand-named file lists
throughout CI are not an oversight — they are a **workaround for a suite that
cannot run as a whole**. Nobody wrote that down, so it reads as carelessness
when it is actually an unpaid debt.

**Consequence for sequencing:** CI can be wired *today* by running each
directory as its own job, which sidesteps contamination entirely and puts ~1792
tests in front of every PR. Fixing isolation is a separate, later piece of work
and must not block the gate.

### The 14 real failures cluster on VPR

| Count | Location |
|---|---|
| 5 | `tests/integration/test_company_research_vpr.py` |
| 3 | `tests/integration/test_vpr_e2e.py` |
| 2 | `tests/integration/test_vpr_pipeline_contract.py` |
| 1 | `tests/regression/test_pipeline_stages.py::test_generate_vpr_function_signature_unchanged` |
| 1 | `tests/regression/test_no_placeholder_fallbacks.py::test_cv_tailoring_no_raise_on_missing_vpr` |
| 1 | `tests/integration/test_l0_phase_integration.py` |
| 1 | `tests/infrastructure/test_p02_billing_reconcile_entrypoint.py` |

**12 of 14 touch VPR — and journey step J5 is "VPR generates."** The suite
already knows the next journey step is broken; nothing was running it to say so.
This is consistent with open bug **S7** ("VPR quality-check failure silently
serves generic filler as success"), though that linkage is inference, not yet
verified.

**Two test files are executed by nothing:**

| File | Tests | Assertions | Why orphaned |
|---|---|---|---|
| `tests/e2e/application-hub-flow.e2e.test.ts` | 5 | 17 | in jest's `testPathIgnorePatterns`, absent from vitest `include`, wrong extension for Playwright |
| `tests/e2e/artifact-viewers.e2e.test.ts` | 2 | 4 | same |

These are *real* tests with *real* assertions, silently excluded. Confirmed via
`npx jest --listTests` (collects 63 files; neither appears).

**Three runners, two hand-maintained allowlists.** Jest owns
`tests/**/*.test.ts` minus a hardcoded `testPathIgnorePatterns` list; Vitest
owns a hardcoded `include` list of ~27 named files plus two globs; Playwright
owns `tests/e2e/*.spec.ts`. The two hand-maintained lists must mirror each
other, and nothing enforces that they do — which is exactly how the two orphans
above happened. Today's count is 0 double-run / 2 orphaned, but the
configuration is **orphan-prone by construction**: a new `tests/unit/*.test.tsx`
matches neither Jest's unit `testMatch` (`*.test.ts` only) nor Vitest's
allowlist, and would join the orphans silently.

### Self-validating / self-contained / self-cleaning — measured

**Self-validating — backend yes, Playwright no.** 26 of ~1,692 backend tests
(1.5%) assert nothing. The Playwright suite is 282 blocks / 113 assertions
(see W4.0 below). The backend is not the problem here.

**Self-contained — structurally good.** `tests/conftest.py` sets dummy AWS
credentials process-wide *"so tests never reach real AWS"*, and moto is a
declared dependency used by 42 files. Raw `boto3.client(...)` appears in 58 unit
and 19 integration files, but under the conftest guard those fail closed rather
than touching a real account.

**The leak is silent skipping.** `tests/integration/integration_helpers.py:100`
does `pytest.skip('API_BASE is not set. Skipping integration tests.')`, and nine
more `pytest.skip()` calls fire on a missing module or missing payload
(`test_interview_prep_context_sources.py` skips three times on
*"module not available"*). A skip on "the module isn't importable" is a **test
suite reporting green for a broken import**. These must become failures, or be
marked `xfail(strict=True)`, not skips.

**Self-cleaning — partial.** Teardown exists in 26 of 163 unit files and 12 of
39 integration files. moto-backed tests are self-cleaning by construction
(in-memory, torn down with the mock); the un-mocked remainder is the risk
surface and should be enumerated.

**Deterministic — no.** 48 unit files and 7 integration files call
`now()`/`utcnow()`/`today()`, and **no time-freezing library is a dependency at
all** — no `freezegun`, no `time-machine`. Nine integration files use
`uuid4`/`random`. Time-dependent assertions cannot be pinned, which is latent
flakiness that will surface as intermittent CI failures nobody can reproduce.

### Framework and configuration gaps

Good, already in place: pytest fixtures (100 in unit), moto, the conftest
credential guard, tiered coverage gates (`scripts/check_coverage_gates.py`),
Playwright `trace: "on-first-retry"`, and `fullyParallel: false` with a
documented reason (shared auth state).

Missing, all cheap:

- `[tool.pytest.ini_options]` declares `testpaths` and two markers and nothing
  else. No `addopts`, no `--strict-markers` (so a typo'd marker silently
  applies nothing), no `xfail_strict`, no `filterwarnings = ["error"]`.
- No time-freezing dependency (see above).
- No test-ordering randomization (`pytest-randomly`). Inter-test coupling is
  therefore undetectable — order-dependent tests pass forever until the day
  they don't.
- `--passWithNoTests` on all three frontend CI invocations converts "the
  selector matched nothing" into a pass.
- `npm run test:e2e` runs **jest** against `tests/e2e/**/*.test.ts` — five
  billing files. It does not run the 26 Playwright specs, despite the name.

### W4.01 — Fix the wiring before writing a single new test

This is the highest return per unit of effort anywhere in this document,
because the tests already exist and are already honest.

1. **Un-orphan the two dead files** — decide jest or vitest, wire one, delete
   the ignore entry. 7 tests and 21 assertions rejoin the suite immediately.
2. **Make `pr-validation.yml` run the backend suite as one job per directory** —
   not a single bare `uv run pytest`, which is 606-red from contamination. Per
   directory it is ~1792 green and 14 red, and the 14 are named above. Fix or
   quarantine those 14 with recorded reasons, then the gate is real.
3. **Run the frontend suites on `pull_request`** — jest + vitest — and drop
   `--passWithNoTests` so a broken selector fails.
4. **Give the Playwright suite an automatic trigger** — at minimum
   `journey.spec.ts` on PR against a deployed devx, since it is the one spec
   that meets the bar. Do this *after* W4.1 so the hollow specs aren't what
   gets automated.
5. **Turn silent skips into failures** — `API_BASE` unset and "module not
   available" must fail or `xfail(strict=True)`, never skip.
6. **Tighten pytest config** — `--strict-markers`, `xfail_strict = true`,
   `filterwarnings = ["error"]`, and add `freezegun` plus `pytest-randomly`.

Items 1-3 and 5-6 touch no product code and can land today, independent of the
deploy track.

### W4.0 — What the Playwright suite actually is

26 spec files, 291 blocks, 127 assertions. Excluding `journey.spec.ts`: **282
blocks, 113 assertions.** The hollowness mechanism is *not* commented-out
assertions (only 2 exist) — it is **test blocks with empty bodies that pass
because they assert nothing**:

```ts
// badge.spec.ts
test.beforeEach(async ({ page }) => {
  // TODO: authenticate — call shared auth helper (e.g. loginAs(page, 'test-user'))
  // TODO: navigate to a known /applications/[id] route
});

test('test_soft_success_badge_renders_green_tinted_on_page', async ({ page }) => {
  // TODO: locate a badge element ...
  // TODO: assert computed background-color ...
});
```

That test passes. It does not log in, does not navigate, does not assert.

Three further findings:

- **No spec outside `journey.spec.ts` authenticates.** Zero uncommented
  `loginAs(` calls exist in the other 25 files — every reference is inside a
  `TODO` comment. These specs cannot be exercising authenticated product
  surface, whatever their names say.
- **`application-hub.spec.ts` navigates to a literal placeholder:**
  `page.goto('/applications/<test-application-id>')`. That route cannot resolve.
- **The `spec_id` / `AC-001` references do not resolve.** Specs cite acceptance
  criteria (`// spec_id: FE-UI-001`) with no registry in `docs/` defining them.
  Either the registry lives outside the repo or it was never written; until it
  is located, those tests cannot be checked against their own stated criteria.

`journey.spec.ts` is the only spec that meets the bar — it authenticates,
navigates real routes, and carries 14 live assertions across 9 steps. **It is
the template for everything below.**

### W4.1 — Per-spec disposition (you chose: decide per file)

All 282 non-journey blocks accounted for. Four dispositions:

**A. Wrong test type — move to unit/component (vitest), delete from e2e.**
Pure rendering behavior; Playwright buys nothing and costs a browser.

| Spec | Blocks | Assertions |
|---|---|---|
| `badge.spec.ts` | 4 | 1 |
| `spinner.spec.ts` | 5 | 1 |
| `progressbar.spec.ts` | 4 | 1 |
| `error-boundary.spec.ts` | 6 | 1 |
| `rich-text-editor.spec.ts` | 6 | 2 |
| **subtotal** | **25** | **6** |

Action: confirm equivalent unit coverage exists, then delete the e2e files.
Error-boundary is the one to check carefully — a genuine error path may deserve
an e2e case inside the parent feature spec.

**B. Sub-components of a feature — merge into the parent feature spec.**
These test pieces of a page. Their behavior belongs inside that page's
feature journey, asserted through the UI a customer actually drives.

| Spec | Blocks | Assertions | Parent feature |
|---|---|---|---|
| `tailored-cvs-list-table.spec.ts` | 28 | 6 | CV tailoring |
| `gap-question-card.spec.ts` | 16 | 4 | Gap analysis |
| `cover-letters-list-table.spec.ts` | 16 | 5 | Cover letter |
| `choose-base-cv-modal.spec.ts` | 14 | 2 | CV center |
| `appheader.spec.ts` | 12 | 2 | Shell / nav |
| `appsidebar.spec.ts` | 11 | 3 | Shell / nav |
| `base-cvs-table.spec.ts` | 11 | 2 | CV center |
| **subtotal** | **108** | **24** | |

**C. Feature-level — rebuild on the `journey.spec.ts` template.**
These map to real user-facing features and should become the per-feature deep
e2e specs you asked for.

| Spec | Blocks | Assertions | Feature |
|---|---|---|---|
| `cv-center.spec.ts` | 16 | 8 | CV center |
| `new-application.spec.ts` | 16 | 4 | Application creation |
| `gap-analysis.spec.ts` | 14 | 3 | Gap analysis |
| `billing.spec.ts` | 11 | 8 | Billing |
| `cover-letters.spec.ts` | 10 | 5 | Cover letter |
| `tailored-cvs.spec.ts` | 10 | 5 | CV tailoring |
| `application-hub.spec.ts` | 9 | 2 | Application hub |
| `dashboard.spec.ts` | 4 | 1 | Dashboard |
| **subtotal** | **90** | **36** | |

**D. Billing/subscription cluster — highest existing density, fill in place.**
These are the closest to real (`plan-card` 11 assertions / 10 blocks) and are
worth filling rather than rebuilding.

| Spec | Blocks | Assertions |
|---|---|---|
| `subscription-card.spec.ts` | 14 | 7 |
| `billing-billinginfocard.spec.ts` | 13 | 12 |
| `plans-section.spec.ts` | 12 | 11 |
| `plan-card.spec.ts` | 10 | 11 |
| `usage-card.spec.ts` | 10 | 6 |
| **subtotal** | **59** | **47** |

25 + 108 + 90 + 59 = **282.** Every block has a disposition.

**Immediate action regardless of disposition:** the assertion-free blocks must
stop reporting green *before* new specs land beside them. Cheapest honest move
is a single commit converting every empty-bodied block to `test.fixme()`, which
reports as pending rather than passing, and removes the false signal in one step
without losing the scaffold. Then work the dispositions above.

### W4.2 — Six features have no e2e spec at all

VPR · interview prep · company research · knowledge base · auth · export.

Each needs a spec built on the `journey.spec.ts` template: real login, real
navigation, real assertions, no TODOs. These are new construction, not repair.

### W4.3 — The feature-state ledger

`docs/FEATURE-STATE.md` — every V1 feature × every user-visible behavior:

| State | Meaning |
|---|---|
| `WORKS` | a live assertion passes against a deployed stack, proof cited |
| `BROKEN` | a live assertion fails, or a confirmed defect is open, ID cited |
| `UNVERIFIED` | no assertion exists |

`UNVERIFIED` is first-class, exactly as preflight has UNKNOWN. Treating "no
test" as "works" is the specific failure this whole harness exists to prevent.
Generated from the suite, not hand-maintained — a hand-maintained ledger goes
stale the same way the ASTRA findings did.

### W4.4 — Codify testing with every fix (definition of done)

Add to `CLAUDE.md`:

> Every bug fix ships with a test that **fails before the fix and passes after**,
> and the commit message shows both runs. A test written after the fix, never
> observed failing, proves only that it is consistent with current behavior.
> Every new feature ships with an e2e spec on the `journey.spec.ts` template
> before it is considered done. No `TODO`-bodied test blocks, ever — the rule
> already in `HARNESS.md` applies to the whole suite, not just the journey.

---

## W5 — P-28 is ~20% closed, not closed

Commit `5022510` reads "close the two non-compliant deploy pipelines." **Nine
workflow files still call `make deploy` (create + execute, no changeset, no
gate):**

`main-serverless-service.yml` · `company-research.yml` · `cover-letter.yml` ·
`cv-tailoring.yml` · `gap-analysis.yml` · `gap-remediation.yml` ·
`ui-upgrade-checks.yml` · `db-redesign-checks.yml` · `pr-serverless-service.yml`

(`deploy-staging.yml` matches the grep only via its own explanatory comment; it
is genuinely fixed.)

Several deploy **on push**, not merely on dispatch — e.g.
`company-research.yml:132`: `if: github.event_name == 'push' || ...`. Same in
`cover-letter.yml` and `gap-analysis.yml`. That is exactly the auto-execute
class closed for `deploy-vpr-async.yml`.

**Worse:** `main-serverless-service.yml`'s `production` job (line 84,
`run: make deploy` at line 125) — and `make deploy` hardcodes
`npx cdk deploy CareerVpCrudDev` (`Makefile:118`). A "production" deploy in that
workflow deploys **dev**. Same defect `deploy-staging.yml` had, still live, on
the production path.

Treat this as an active exposure, not cleanup. It is the only item in this
document where doing nothing has an ongoing cost.

## W6 — Environment is not rebuildable

Preflight FAIL: **10 of 10** devx tables exist with no CloudFormation stack
owning them — including `users-table-devx` and `jobs-table-devx`. The 09-14
handoff names four; the proof lists ten.

Consequence: the environment cannot be recreated from source, and a changeset
that believes it is creating these tables will behave unpredictably. Needs
`cdk import` or a written, owned decision to accept it. Until then, "we can
rebuild this environment" is false, and no production cutover plan is credible.

Also open: no `production` GitHub environment exists, and it would auto-create
**unprotected** on first use — the same trap `deploy-dev` and `staging` were in
before this branch created them with required reviewers.

---

## W7 — Lambda runtime configuration

**Added 2026-09-23.** Everything in this section is MEASURED against the 32
deployed `devx` Lambdas on that date. No prior workstream covers Lambda
configuration; it has never been reviewed.

**Healthy:** runtime is `python3.13` uniformly. X-Ray tracing is `Active` on
every function sampled. Async failure handling exists and is real — SQS DLQs
plus three dedicated handler Lambdas (`vpr-dlq-handler`,
`artifact-failure-handler`, `cr-failure-handler`).

**Open, in severity order:**

- **31 of 32 Lambdas retain logs for 1 day.** Every diagnosis this chain has
  produced — J3, J4, J5, J8 — was made by reading CloudWatch after a failure.
  That evidence evaporates in 24 hours. This is not a cosmetic setting; it is
  the single point of failure in the project's own debugging method.
- **`export-lambda` has a 29-second timeout behind API Gateway's hard 30-second
  integration limit** — one second of margin for a build-and-upload round trip.
  J9 has never successfully measured this path, so whether it fits has never
  been observed. `ai-assist` sits at 25s on the same ceiling.
- **Reserved concurrency is set on exactly 6 async workers, at 5 each.** The
  other 26 functions are unreserved against an account ceiling of 1000. Two
  consequences: a runaway API Lambda can starve every worker, and total
  system throughput for LLM generation is 5 concurrent jobs.
- Memory is 128–1024 MB and appears to be a CDK-default choice per function
  rather than a measured one; no duration-vs-memory data exists.

**W7.1 — Instrument.** Extend `preflight.py` (or add `lambda_config.py` as a
sibling) to emit per-Lambda runtime, memory, timeout, log retention, reserved
concurrency and DLQ wiring as a reproducible JSON proof, flagging: any timeout
within 2s of its invoker's limit; any retention below 14 days; any async worker
with no reserved floor; any function whose memory has never been tuned against
observed p99 duration.

**W7.2 — Fix what it finds.** Raise log retention before any further journey
diagnosis — this one blocks the others. Give `export` headroom or move it off
the synchronous request path. Set concurrency floors deliberately rather than
by omission.

**Exit criteria.** No Lambda within 2s of its invoker's timeout. Log retention
≥ 14 days everywhere. Every async worker carries a stated reserved floor.
`lambda_config.py` reports clean.

---

## W8 — Performance and load

**Added 2026-09-23.** Nothing in this project has ever measured latency,
throughput, or cost. There is no p50, no p95, no cost-per-journey, and no load
test. The `35-70 session` effort table mentions "load testing" once, bundled
with legal work, and no workstream owns it.

**MEASURED 2026-09-23:**

- API Gateway stage `prod` has `throttleSettings.rateLimit = None` and
  `burstLimit = None`. **There is no stage-level throttle**; the account default
  applies. The only brake in front of 61 routes — including every LLM-backed
  endpoint — is the WAF rate-based rule.
- Six workers are capped at 5 concurrent executions with 300–600s timeouts.
  System-wide LLM generation throughput is therefore 5 concurrent jobs; the
  sixth user queues behind a job that may run ten minutes.
- Observed journey costs, incidentally: J5 took 3.2 minutes end to end; J8
  performs two LLM round trips; `GENERATION_TIMEOUT_MS` budgets 240s per step.
  None of this was measured deliberately — it is a by-product of e2e runs.

**W8.1 — Instrument.** A per-journey cost and latency ledger: p50/p95/p99 per
journey step, dollars per completed journey, tokens per artifact type. The
journey harness already produces timing; this makes it a tracked output rather
than an incidental one.

**W8.2 — Set the limits deliberately.** Stage throttle and per-route limits;
an explicit concurrency model for the worker fleet.

**W8.3 — Load test at a stated volume.** Pick the trial-conversion volume the
business actually plans for and test at it. A number nobody has committed to is
not a target.

**Exit criteria.** Documented p95 per journey step. A stage throttle exists.
A measured dollar cost per completed journey. A load test at N concurrent
users, with N written down and justified.

---

## W9 — API contract correctness

**Added 2026-09-23.** W3.1's `dead_api.py` answers *"does this route have a
caller."* It does not answer *"do the caller and the handler agree."* That gap
is not theoretical — it is where the currently-live defect lives.

**The proof that every existing instrument misses this class.** Interview prep
reads gap answers as `{question, answer}`; the gap writer stores
`{question_id, response}`. The handler logs `lookup empty` at INFO and generates
anyway, so interview prep is built without the user's gap answers and served as
though complete. Against that defect: `dead_api.py` sees a live route with a
live caller. `table_map.py` sees a matching read and write table. The unit
suite passes. `make journey` reports J8 **pass**. Every instrument this project
has built reports green on a feature that is silently producing degraded
output.

This is the same pathology as open bug **S8** (*"cover letters generate with no
gap answers"*), which W2 named in advance. W2 addresses *which table*; W9
addresses *which shape*.

**W9.1 — Instrument.** A contract check that compares, for every route, the
request/response model the handler validates against the shape the frontend
sends and expects; and for every persisted artifact, the writer's shape against
the reader's model. Fail on mismatch. This is decidable statically — both sides
are Pydantic models and TypeScript types.

**W9.2 — Fix what it finds,** one contract per commit, each with a test that
fails before and passes after.

**W9.3 — Make degraded paths fail loud.** A handler that cannot load a required
dependency must not log at INFO and continue. Every such site needs an explicit,
tested decision: fail the request, or serve a response that states what is
missing.

**Exit criteria.** Zero contract mismatches. No handler proceeds past an empty
required dependency without an explicit tested decision. The check gates CI.

---

## W10 — Security

**Added 2026-09-23.** W5 covers deploy-path security only. Nothing covers the
running system's authorization model, key management, or dependency posture.

**Healthy, and worth recording so it is not re-litigated:** a WAF is attached
to the API (`careervp-core-waf-devx`) carrying four AWS managed rule groups —
Common, IP Reputation, Anonymous IP, Known Bad Inputs — none overridden to
Count, plus a rate-based Block rule. All 11 DynamoDB tables have deletion
protection enabled and 10 of 11 have PITR. IAM is tighter than expected: every
Lambda role sampled carries only `AWSLambdaBasicExecutionRole`, and
`Resource: "*"` appears only on X-Ray, AppConfig and KMS actions. The ai-assist
least-privilege guardrail test is real and already blocked one widening attempt
during J8 work.

**Open:**

- **No per-route authorization model.** 61 routes exist. Beyond P-05's IDOR
  tests there is no documented statement of who may call each route, whose data
  it may touch, and which test proves the isolation holds.
- `kms:Decrypt` and `kms:GenerateDataKey` are granted on `Resource: "*"` rather
  than scoped to specific key ARNs.
- All tables use the AWS-owned default key; no customer-managed key exists, and
  no decision records whether one is required.
- **`careervp-knowledge-table-devx` partitions on `userEmail`** — PII as a
  partition key, and inconsistent with the `userId` convention every other
  user-scoped table uses.
- 23 known CVEs across 4 packages remain open (PR #230).

**W10.1 — Build the per-route authorization matrix:** route → who may call →
whose data it touches → the test that proves it. Rows with no test are
`UNVERIFIED`, in the same spirit as `FEATURE-STATE.md`.

**W10.2 — Scope the KMS grants** to key ARNs; make an explicit, recorded
decision on customer-managed keys.

**W10.3 — Close the CVEs and put `pip-audit` on a schedule** so the count
cannot silently drift again.

**W10.4 — Resolve the `userEmail` partition key** — it is both a privacy
question and a W2 consistency question; scope it with W2.3 rather than alone.

**Exit criteria.** Every route appears in the authorization matrix with a
passing isolation test and zero `UNVERIFIED` rows. No unscoped KMS grant.
Zero known-exploitable CVEs, with a scheduled re-check.

---

## Sequencing

**Now, no dependencies, no deploy needed:**
- **W4.01 (highest return per unit of effort in this document)** — wire CI to
  the ~1,692 tests that already exist. Touches no product code.
- W5 (active exposure — the only item where doing nothing has an ongoing cost)
- W4.1 immediate action (`test.fixme()` the assertion-free blocks)
- W2.1 and W3.1 (build the instruments)

**On your go-ahead:**
- W0 → W1 (push, PR, gated deploy, re-measure)

**After the instruments exist:**
- W2.2, W3.3 (fix what the maps find)
- W4.2, W4.3 (per-feature specs, then the ledger generated from them)

**Needs a scoped decision, not a session:**
- W2.3 (single vs multi-table) — the one place a top-tier model is justified
- W6 (`cdk import` vs accept)

**Not started until the above are real:**
- The 72-item launch checklist. Running it against instruments that report
  false green produces confident, wrong answers.

## Does finishing this plan make you production-ready? No.

Stated plainly because the gap is not obvious: **completing W0-W6 gets you a
correct, well-instrumented product running in a dev environment.** It does not
get you a sellable one. Measured 2026-09-20:

### Gap 1 — the definition of done is narrower than V1 scope

`N = 9` is the project's definition of done. V1 scope in `CLAUDE.md` is: Auth ·
VPR · CV Tailoring · Cover Letter · Gap Analysis · Interview Prep · **Company
Research** · **Knowledge Base** · **English + Hebrew**.

The journey's nine steps are sign in · upload CV · create application · gap
analysis · VPR · tailored CV · cover letter · interview prep · export.

So **Company Research, Knowledge Base, Hebrew, and the entire billing / trial /
subscription path are not in the definition of done.** Hebrew appears in six
page files; its only e2e test (`cv-center.spec.ts:179`) is a TODO stub. The
purchase flow — the thing that takes money — is not a journey step.

**A product can reach 9 of 9 and still not be sellable.** Either the journey
grows steps (per its rule 3, which permits it when the product genuinely grows)
or a second instrument covers the rest. That is a decision, not an oversight to
fix silently.

### Gap 2 — no production environment exists

MEASURED: stacks in AWS are `CareerVpCrudDev`, `CareerVpCrudDevx`,
`CareerVpCrudStaging`, `CareerVpFrontend-Dev`. **No production stack.** No
`production` GitHub environment. `infra/app.py` does parameterize it (domain map
has `app.careervp.com`), so this is configuration and a first deploy, not new
architecture — but it is unbuilt and unexercised.

`CareerVpCrudStaging` exists but was last updated **2026-04-12**, roughly five
months stale. Whether it reflects current code is unknown.

### Gap 3 — commercial and legal prerequisites

- **No Terms of Service or Privacy Policy pages** found under `src/frontend`.
  A paid product collecting card details for a 14-day trial needs both, plus a
  data-deletion path if any EU or Israeli users are in scope.
- Stripe is wired (`payment_providers/stripe_provider.py`, key from
  `STRIPE_SECRET_KEY`), but live-key handling, webhook verification in
  production, refunds, failed-payment recovery and tax have not been exercised
  end to end.
- No load or performance testing has ever been run.
- Gap-API Lambda log retention is **1 day** (`api_construct.py`), which makes
  post-incident diagnosis impossible. Several other retentions are 7 days.

Good news, MEASURED: PITR is enabled on the tables checked, a WAF construct
exists, and 11 CloudWatch alarms are defined. The foundations are present.

### What plan completion actually buys you

A product whose behavior is **measured rather than asserted**: a real CI gate, a
trustworthy test suite, a rebuildable environment, one owner per table, no
ungated deploys, and a customer journey proven to 9 of 9. That is the
precondition for a launch decision — not the launch itself.

The remaining work above is ordinary and mostly known. It is dangerous only if
mistaken for already-done.

## What "production ready" means when this is done

- `make journey` reports **9 of 9** against a deployed stack, with
  `git_dirty: false` and `deployed_sha` matching HEAD.
- `make preflight` reports **0 FAIL, 0 UNKNOWN**.
- `docs/FEATURE-STATE.md` has **zero `UNVERIFIED`** rows.
- **Zero** workflows execute a deploy without a human gate.
- Every table has exactly one owner and one name per role; `table_map.py`
  reports no read/write mismatches.
- The environment can be destroyed and rebuilt from source.

Added 2026-09-23, from W7-W10 — the running system, not the deploy path:

- No Lambda sits within 2s of its invoker's timeout; log retention is **≥ 14
  days** everywhere; every async worker carries a stated concurrency floor.
- A **p95 per journey step** and a **measured dollar cost per completed
  journey** are documented, and a load test has run at a written-down N.
- The contract check reports **zero mismatches**, and no handler proceeds past
  an empty required dependency without an explicit tested decision.
- Every route appears in the **authorization matrix** with a passing isolation
  test and zero `UNVERIFIED` rows; no unscoped KMS grant; zero known-exploitable
  CVEs.

## Validating this plan

A plan cannot be validated by review. Review produces more claims at the same
unverified rate — `ASTRA` was a three-pass, 1.1M-line audit five days before
this plan and surfaced none of the ten findings above, because it reviewed
claims instead of executing commands. **Every discovery here came from running
something nobody had run.**

Three mechanisms keep this plan honest.

### 1. Provenance tags

Every load-bearing claim carries one:

- **MEASURED** — a command was run, output recorded, date given.
- **INFERRED** — reasoning from measured facts. Plausible, unverified.
- **INHERITED** — asserted by an earlier document, never checked in this chain.

Audit of this plan as of 2026-09-20:

| Tag | Claims |
|---|---|
| MEASURED | suite state (606/14, per-directory), contamination repro, orphaned test files, CI wiring, workflow counts, table env sprawl, Lambda timeouts, journey 3/9, preflight state, frontend suites green (429 + 739), stack inventory, PITR, WAF/alarms present |
| INFERRED | deploying Dev then measuring Devx leaves N at 3; async is the right J4 fix; the narrow `-k` filters are a contamination workaround; the 14 VPR failures relate to S7 |
| INHERITED | the GitHub environments exist with required reviewers; the read-only IAM credentials work; the harness account has an active subscription; the four committed fixes are correct; the P-05 repair is real; the J4 CloudWatch diagnosis |

**The distribution is the point.** Handoffs 01 and 02 are built almost entirely
on MEASURED claims — low churn risk. **Handoff 03, the deploy track, is built
almost entirely on INHERITED ones.** That is where the plan is thinnest, and it
is invisible unless tagged. Handoff 00 exists to convert that row to MEASURED
before anything is deployed.

### 2. The prediction ledger

Each handoff records what it expects; the next session scores it. After three or
four handoffs there is a **measured accuracy rate for the planning process
itself** — the literal answer to "will these prompts return expected results."

This is `preflight` applied to the plan. If the hit rate holds above ~70%, the
plan is calibrated and can be trusted further ahead. If it drops, stop and
re-ground rather than pushing on.

First entry: handoff 00, Section E.

### 3. Bounded surprise, not zero surprise

Discoveries fall into three categories, and only one is irreducible:

| Category | Bounded? | Handling |
|---|---|---|
| **(a)** Cheap measurements never taken | **Yes** — finite and enumerable | Handoff 00 burns them down in one read-only session |
| **(b)** Claims inherited from earlier docs | **Yes** — finite and enumerable | Handoff 00 Section A verifies or drops each |
| **(c)** Sequential discoveries — only findable by deploying, or by reaching J5 | **No** | The handoff chain absorbs them; each handoff declares where it expects them |

Nearly all churn in this plan's first three drafts was (a) and (b). Both have a
bottom. **(c) does not, and no amount of planning removes it** — you cannot learn
what J6 does before J5 passes. What the chain does is ensure a (c) discovery
lands *inside* a handoff that expected uncertainty there, rather than
invalidating the plan.

**Every handoff must therefore state where it expects surprises.** A surprise
where the plan claimed stability is a process failure worth investigating. A
surprise where the plan said "expect one here" is the plan working.

## The handoff chain — how this plan gets executed

This plan is not executed in one session. It is executed as a **chain of
handoff prompts**, each run in a fresh session, each numbered, each stored in
`docs/handoff/` as `2026-MM-DD-HANDOFF-NN-<slug>.md`.

The chain exists for one reason: **a session cannot be trusted to certify its
own work.** A session that spent four hours on a change has every incentive to
read an ambiguous result as success. Putting the verification in the *next*
session, with no memory of the effort spent, removes that incentive.

### The three obligations every handoff carries

**1. Validate the previous handoff before doing anything else.**
Every handoff opens with a `## Step 0 — Verify handoff NN-1` section that
re-runs the prior session's proof commands *from a clean checkout* and compares
against the numbers the prior session recorded. Do not read its prose summary
first; run the commands, then read the summary and see whether it matches.

- Numbers reproduce → proceed, and say so.
- Numbers do not reproduce → **stop.** Do not start this handoff's work. Write
  `docs/handoff/<date>-HANDOFF-NN-VERIFY-FAILED.md` recording expected vs.
  observed, and report. A broken link in the chain is more important than the
  next task.
- Prior session claimed something it recorded no command for → treat the claim
  as unproven, note it, and re-derive it if this handoff depends on it.

**2. Declare the proof up front, before the work.**
Every handoff states, in a table, the exact commands whose output constitutes
proof and the expected before/after values. Written *before* the work, so the
bar cannot be moved to fit the result. Output is committed as a proof file
under `docs/evidence/`, stamped with `git_sha` and `git_dirty` per
`HARNESS.md`. A handoff with no runnable proof command is not a handoff — it is
a wish, and must be reshaped until it has one.

**3. Separate "what I can prove here" from "what needs the next session."**
Some claims cannot be proven in the session that makes the change — anything
requiring a push, a deploy, or a human approval. Those go in an explicit
`Deferred proof` section and become the *next* handoff's Step 0. Never write
"this will work once deployed" as though it were a result.

### When a handoff returns something unexpected

Named outcomes, with a required response each. The response is not a judgment
call — pick the matching row and follow it.

| Outcome | Required response |
|---|---|
| **Goal met, proof matches** | Commit. Write the next handoff. Record the proof file path. |
| **Goal met, proof differs from prediction** | The prediction was wrong, which means the model of the system was wrong. Do **not** quietly update the expected value. Commit the work, then record what you predicted, what happened, and why — the gap is a finding. |
| **Partially met** | Commit only the parts with passing proof. Do not commit the rest. Write the unfinished remainder into the next handoff *with the measured blocker*, not with a restatement of the original task. |
| **A premise in the handoff is false** | **Stop.** Do not adapt the goal to fit the discovered reality — that is how scope silently drifts. Write a premise-broken report naming the false premise and the evidence, and hand back. |
| **Goal met but something else regressed** | Revert first, investigate second (`HARNESS.md`). A net-negative change does not ship because its own metric improved. |
| **Blocked on a human (push, approve, deploy)** | Stop at the boundary. Record everything proven up to it. The blocked item becomes the next handoff's Step 0, verified against the real artifact (an Actions run, a stack output), never against an assumption that it happened. |
| **Ran out of session before finishing** | Commit what has proof. Write the next handoff from the *actual* stopping point, including what was learned that would change the approach. |

**The rule that binds all of them:** a handoff may only report an outcome it can
name a command for. "It should now work" is not an outcome. "I ran X, it printed
Y, expected Y" is.

### Handoff sequence (revised by the W4.00 measurement)

| # | Scope | Why here | Needs a human? |
|---|---|---|---|
| **00** | Measurement sweep — verify every INHERITED claim, run every cheap unrun command | Converts the plan's weakest row to MEASURED before anything is built on it; read-only | No |
| **01** | W4.01 — wire CI to the 1,864 tests that already exist | Highest return per unit of effort; touches no product code; makes every later handoff verifiable | Push only |
| 02 | Verify 01's CI actually ran; W5 — close the 9 ungated `make deploy` workflows | 01's deferred proof lands here; W5 is the only active exposure | No |
| 03 | W0 + W1 — deploy prerequisites, PR, gated deploy, re-measure journey | Needs 01/02's gate to be real first | Review, merge, approve |
| 04 | W2.1 + W3.1 — build `table_map.py`, `dead_api.py`, `dead_code.py` | Static; independent; produces the maps everything later needs | No |
| 05+ | W4.1/W4.2 e2e rebuild · W2.2/W3.3 fixes · W4.3 ledger | Each gated on the proof from its predecessor | Varies |

Later handoffs are written by the session that finishes the previous one, from
the real stopping point — not pre-written here. Pre-writing handoff 05 today
would encode assumptions that handoffs 01-04 exist to test.

## Level of effort

In sessions, since that is the unit this chain executes in. Confidence stated
per band — **the spread is the honest part**, and it is driven almost entirely
by the fact that six of nine journey steps have never executed.

| Phase | Sessions | Confidence | Why |
|---|---|---|---|
| Handoff 00 — measurement sweep | 1 | **High** | Fixed command list, read-only |
| Handoff 01 — CI wiring | 1-2 | **High** | Scope measured; the 14 failures are named |
| Handoff 02 — test isolation | 1-3 | Medium | Bisecting contamination across 250 files; could be one bad import or many |
| Handoff 03 — deploy track | 1-2 + human | Medium | Depends entirely on handoff 00 Section A; the `cdk diff` against 10 unmanaged tables is the risk |
| W5 — close 9 ungated workflows | 1 | **High** | Mechanical, pattern already established |
| W2 — table map + fixes | 3-5 | Medium | Instrument is 1-2; fixes depend on what the map finds |
| W3 — dead code / dead API | 2-3 | Medium | Same shape |
| W6 — `cdk import` 10 tables | 1-3 | Low-Med | Import is fiddly and touches live data |
| J4 — async gap generation | 2-4 | Medium | Architectural; the plan's own escalation trigger |
| **J5-J9 — unblock six unexecuted steps** | **5-15** | **Low** | 12 of 14 real test failures are VPR (= J5); S7/S25/S8/S10/S11 unverified. This is the wildcard |
| W4 — e2e rebuild + feature ledger | 7-11 | Medium | 6 features with no spec, 26 specs to disposition, ledger generated |
| Staging refresh + production stack | 2-4 | Low-Med | Staging 5 months stale; prod never built |
| Billing / trial / Stripe live path | 2-4 | Low | Never exercised end to end |
| Hebrew + Company Research + Knowledge Base coverage | 3-5 | Low | V1 scope, essentially unmeasured |
| Legal, load testing, log retention, 72-item checklist | 3-6 | Low | Partly not engineering work |
| **Total** | **≈ 35-70 sessions** | | |

**Read the total as a range, not a number.** The bottom of the range assumes
J5-J9 are blocked by the five already-suspected bugs and nothing more; the top
assumes each of the six unexecuted steps hides its own defect, which is what
J1-J4 did.

**What would tighten this estimate,** in order of value:

1. **Handoff 00** — collapses several Low confidences by measuring them. Cheapest
   estimate improvement available.
2. **Reaching J9 once**, even with failures — converts the 5-15 band, the single
   largest source of spread, into a known list.
3. **The table map** — turns W2's "3-5" into a count of actual mismatches.

Do not commit to a launch date before item 2. Six of nine steps have never run;
any date set today is a guess about code nobody has executed.

## Standing rules

- `HARNESS.md`'s five investigation rules apply. Label claims OBSERVATION /
  INFERENCE / OPINION.
- One change, one `make journey`, read what actually moved.
- Per `CLAUDE.md`, run the mandatory checks for every path touched before each
  commit. Run `pytest tests/integration/` for anything touching P-05 files —
  that is precisely how the hollow suite survived undetected.
- **Do not deploy.** Prepare changesets; a human executes and approves.
- If a fix turns out bigger than described here, stop and report rather than
  redesigning unilaterally.

## Correction to `docs/HARNESS.md`

`HARNESS.md` states the older specs' assertions are "commented out." Measured:
only **2** commented assertions exist. The actual mechanism is empty
`TODO`-bodied test blocks. This changes the remediation — there is nothing to
uncomment, the tests were never written. Worth fixing in that doc so the next
reader does not go looking for comments to remove.
