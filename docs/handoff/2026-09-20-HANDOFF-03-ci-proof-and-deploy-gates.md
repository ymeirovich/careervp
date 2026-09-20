# HANDOFF 03 — prove CI runs, then close the ungated deploy workflows

**Model: Sonnet 5, high effort.** Most of this is verification and YAML
gating against a known list — mechanical, well-scoped, no architecture.
Escalate to **Opus 5, high** only if Step 1 shows the per-directory gate
failing in CI in a way that does not reproduce locally (that would mean a
CI-environment difference nobody has characterised yet). **Fresh session at
the repo root, on `tools/proof-harness`.**

Parent plan: `docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md`. Read its
"The handoff chain" section before starting.

Paste everything below the line.

---

You are executing **handoff 03** of a chain. Handoff 02 fixed the whole-suite
test contamination: the combined backend run went from 601 failed / 100 errors
to **0 failed / 0 errors**, reproduced three times. It could not push, so the
CI wiring from handoff 01 is *still* unverified against a real Actions run —
that is now two handoffs deep as deferred proof, and it is your first job.

## Read first, in this order

1. This document.
2. `docs/evidence/handoff-02-20260920T114133Z-9134ff8.json` — the proof file
   this handoff verifies. **Read it before any prose.** Pay particular
   attention to `step0_9_real_actions_run` and `git_dirty_adjudication`.
3. `docs/HARNESS.md` — proof discipline and the three-result rule.
4. `CLAUDE.md` — mandatory check commands per changed path.

Do **not** open the `ASTRA-*` docs or `docs/evidence/p1-repro/`. Settled
history. **Exception:** `docs/evidence/astra-pass-b/iam-authorization-details.json`
is in scope, but only for the secret described in Step 0.9 — do not read it
for content (it is 24 MB).

## Step 0 — Verify handoff 02's claims

Run these from `src/backend/` before doing anything else. Do not read handoff
02's prose first — run the commands, then compare.

| # | Command | Handoff 02 recorded |
|---|---|---|
| 0.1 | `uv run pytest --collect-only -q \| tail -1` | `2118 tests collected` (up from 1862; +256 is the new regression file) |
| 0.2 | `uv run pytest -q --tb=no -p no:cacheprovider -p no:randomly \| tail -1` | `2058 passed, 48 skipped, 12 xfailed` — **0 failed, 0 errors** |
| 0.3 | `uv run pytest -q --tb=no -p no:cacheprovider \| tail -1` (x2, random order) | identical to 0.2 both times |
| 0.4 | `uv run pytest tests/infrastructure/test_k9_artifact_cleanup_env.py tests/infrastructure/test_p02_billing_reconcile_entrypoint.py -q -p no:randomly \| tail -1` | `3 passed` (was `1 failed`) |
| 0.5 | `grep -rc 'sys\.modules\.pop\|del sys\.modules' tests/ \| grep -v ':0' \| grep -v import_isolation` | empty — no test file evicts by hand |
| 0.6 | `uv run pytest tests/regression/test_careervp_import_isolation.py -q \| tail -1` | `256 passed` |
| 0.7 | the 8-directory loop | 0 failed / 8 (infrastructure now `82 passed, 1 skipped`; regression `294 passed, 1 xfailed`) |
| 0.8 | `uv run mypy careervp --strict \| tail -1` | `Success: no issues found in 137 source files` |

**If 0.2 or 0.3 shows any failure or error, stop and investigate before
continuing** — handoff 02's entire result is that number, and a regression
there means something after `2af3816` broke it.

**Expect 0.1 and 0.7 to drift** if anyone added tests. Small drift is fine;
what must hold is 0 failed / 0 errors.

### A note on `git_dirty`

Running the suite rewrites three tracked files
(`docs/beta/evidence/I{1,2,3}_*/*.json`) with new timestamps. This is
sweep-00's finding #2 and it is still unfixed — see Step 3. Your proof will be
`git_dirty: true` unless you fix it or restore those paths first. Handoff 02
adjudicated rather than hid this; do the same.

## Step 1 — The real Actions run (handoff 01's deferred proof, still unpaid)

This has been deferred twice. It is the reason this handoff exists.

### 1a — Clear the push blocker (needs the user)

`git push` is **blocked by GitHub push protection**:

```
Amazon AWS Access Key ID
  commit: 51129b1c3bcf1c15457d617a1807ed5823db5269
  path:   docs/evidence/astra-pass-b/iam-authorization-details.json:15
```

Handoff 02 confirmed the key is still present at HEAD in that file and in
`docs/evidence/sweep-00-20260920T082517-b587127.md`. It sits in an IAM
authorization-details dump whose surrounding entry lists `AdminAccess`.

**Do not bypass push protection.** Ask the user to pick:

- **Allow via GitHub's unblock URL** (in the push error output) — a web flow
  only they can complete. Fastest.
- **Rewrite history** to strip it — 182 commits, a 24 MB file. Slow and
  destructive; needs explicit approval.

Either way, tell them plainly: **that key ID should be rotated.** It has been
in the repository since 2026-09-14. Rotation is theirs to do, not yours.

If they choose neither, record Step 1 as blocked *again* and skip to Step 2 —
but say so loudly, because a CI gate nobody has ever seen run is not a gate.

### 1b — Verify against the run, not the YAML

Handoff 02 already established that pushing this branch and opening a PR is
**deploy-safe** (only `security.yml` fires on push, and every deploy job in
every PR-triggered workflow is gated on `push`/`workflow_dispatch`). That
analysis is in the proof file under `pre_push_safety_check` — **re-run it
yourself rather than trusting it**, since workflows may have changed:

```bash
# for each workflow: does it trigger on this branch, and does its deploy job gate on the event?
```

Then:

```bash
git push -u origin tools/proof-harness
gh pr create --base main --title "..." --body "..."
gh run list --workflow=pr-validation.yml --limit 5
gh run view <run-id> --log | grep -c "::group::tests/"
```

You are looking for:

- **8** `::group::tests/...` markers in the Pytest job log, one per directory.
- A `Jest (unit + integration)` / `Vitest` job log showing **real collected
  test counts**, not `0 tests found`.
- The job **passing**. If the per-directory loop is green locally and red in
  CI, that difference is the finding — capture the failing directory's output
  verbatim before touching anything.

Reading `pr-validation.yml` is not verification. Reading the run is.

## Step 2 — W5: close the ungated `make deploy` workflows

This was the **plan's original scope for handoff 02** (see the plan's handoff
sequence table, row 02: *"Verify 01's CI actually ran; W5 — close the 9 ungated
`make deploy` workflows"*). The actual handoff-02 document replaced that scope
with test isolation. **W5 was never done and is still open exposure.**

Handoff 02 measured part of it incidentally while checking push safety, and the
picture is better than sweep-00 implied — verify this yourself:

| Workflow | Push trigger | Deploy job gate |
|---|---|---|
| `company-research.yml` | `feature/company-research` | `push \|\| (workflow_dispatch && inputs.deploy=='true')`, env `dev` |
| `cover-letter.yml` | `feature/cover-letter` | same |
| `cv-tailoring.yml` | `feature/cv-tailoring`, `front/vpr-cv-fixes` | same |
| `gap-analysis.yml` | `feature/gap-analysis` | same |
| `db-redesign-checks.yml` | `db-redesign` | **auto-deploys to devx** (sweep-00 finding #5) |
| `ui-upgrade-checks.yml` | `ui-upgrade` | deploys |
| `deploy-staging.yml` | `develop` | deploys |
| `deploy-vpr-async.yml` | `main` | `push && ref==main`, change-set only (no execute) |
| `gap-remediation.yml` | `feature/gap-remediation` | `workflow_dispatch && inputs.deploy=='true'` only |

**The actual exposure is not the `if:` conditions — it is that the `dev`
GitHub environment has `protection_rules: []`** (sweep-00 finding #5). A push
to any of those feature branches deploys with no human approval. Confirm that
first:

```bash
gh api repos/:owner/:repo/environments --jq '.environments[] | {name, protection_rules}'
```

**Three results, not two** (`HARNESS.md`): if you cannot read the environment
config, that is UNKNOWN, not "gated".

Then close the gap the cheapest way that actually holds. Adding required
reviewers to the `dev` environment is one change that gates all of them, and is
strictly better than editing nine `if:` conditions. Cost both options for the
user and let them decide — do not pick for them.

`db-redesign-checks.yml` auto-deploying to **devx** is the sharpest edge: that
is the stack `make journey` measures, so an unrelated branch push silently
invalidates the journey number.

## Proof obligations for this handoff

Declared before the work.

| Claim | Command | Before | After (target) |
|---|---|---|---|
| CI ran the 8 backend directories | `gh run view <id> --log \| grep -c "::group::tests/"` | never run | `8` |
| CI ran the frontend suites | the Jest/Vitest job log | never run | real collected counts, not `0 tests found` |
| The PR gate is green | `gh pr checks` | unknown | all required checks pass, or the failure captured verbatim |
| `dev` environment gating | `gh api .../environments` | `protection_rules: []` (sweep-00, unverified since) | measured; PASS / FAIL / **UNKNOWN** |
| Ungated deploy paths closed | re-run the trigger/gate analysis | 9 workflows reach `make deploy` | each one either gated or explicitly accepted with a reason |
| Handoff 02's suite result holds | `uv run pytest -q --tb=no -p no:cacheprovider \| tail -1` | 0 failed / 0 errors | unchanged |

## Step 3 — Cheap, in scope, unblocks every future proof

`sweep-00` suggested this and nobody has done it. It costs minutes and every
subsequent handoff pays for its absence:

- Point the three beta evidence writers at a temp path (or gitignore them):
  `tests/integration/test_l0_phase_integration.py:353`,
  `test_l1_phase_integration.py:74`, `test_l2_auth_integration.py:175`.
  They `write_text()` then `assert exists()` — nothing reads prior content, so
  redirecting them is safe.
- `src/frontend/dist/tsconfig.tsbuildinfo` is a **committed build artifact**
  that `npm run typecheck` rewrites. Gitignore it.

After this, "run the mandatory checks, then write the proof" can produce
`git_dirty: false` for the first time in this chain.

## Ground rules

- Per `CLAUDE.md`, run the mandatory checks for every path you touch before
  each commit.
- **Do not use `scripts/git/safe_commit.sh` while foreign changes are
  uncommitted** — it runs `git add -A`. Handoff 02 hit this: three handoff docs
  from a prior session were dirty and would have been swept in. Use explicit
  `git add <paths>` plus `pre-commit run`.
- **One concern per commit.**
- **Do not deploy. Do not push without asking** (Step 1a is the asking).
- **Do not bypass GitHub push protection.**
- Do not fix unrelated product bugs. The carry-forward list below is long
  enough already.

## Carry forward — do not rediscover these

**From handoff 02:**

- **The eviction dance may be deletable outright.** An editable-install finder
  (`__editable___service_cdk_1_0_finder`) already maps the bare name `careervp`
  to `infra/careervp`, and the two packages' submodules are disjoint (only
  `__init__` collides). `careervp_root()` may therefore be unnecessary
  belt-and-braces. Cheap to test, needs its own proof. **Do not remove it
  casually** — it is currently the only thing holding a 0/0 suite.
- **Residual shared-state hazards, none currently failing:** 8 test files
  mutate `os.environ[...]` directly instead of via `monkeypatch`;
  `careervp/logic/auth_service.py:84` has a never-cleared
  `@lru_cache(maxsize=1)`; ~28 test files still `sys.path.insert(0, INFRA_SRC)`
  without restoring (harmless while nothing evicts, and the new static guard
  prevents eviction).

**From handoff 01, still untouched:**

- **`filterwarnings = ["error"]` produces 137 failures**, ~126 of them one
  systemic cause (`aws_lambda_powertools` "No application metrics to publish").
  Separately, `RuntimeWarning`/`PytestUnraisableExceptionWarning` about
  **coroutines never awaited** (`generate_gap_questions`,
  `_async_process_record`) — these read as real missing-`await` bugs and
  deserve a dedicated session. **This is the strongest candidate for handoff
  04.**
- **`vpr_handler.py` is dead code.** `infra/careervp/api_construct.py` says so;
  `_add_vpr_lambda_integration` is never called. The real path is
  `vpr_submit_handler.py` → SQS → `vpr_worker_handler.py`. Journey step J5's
  real health is still unmeasured.
- `CVTailoringRequest.vpr_id` (`careervp/models/api_models.py:343`) has no
  `= None` default — breaks the missing-VPR CV-tailoring flow at validation.
  Quarantined `xfail(strict=True)`.
- `DynamoDalHandler` API mismatch in `test_dal_migration_integration.py`.
  Quarantined.
- `interview_prep_prompt` renamed API. Quarantined.
- 48 unit + 7 integration files call `now()`/`utcnow()`/`today()` with
  `freezegun` available but unused.

**From sweep-00:**

- `preflight.py:366` and `scripts/ci/changeset_replacement_report.py` query
  `AWS::DynamoDB::Table` while every table is `AWS::DynamoDB::GlobalTable` —
  the deploy gate's DynamoDB auto-fail **can never trigger**. Load-bearing.
- 31 of 32 devx Lambdas have 1-day log retention.
- `careervp/handlers/knowledge_base_handler.py` is routed to nothing.
- Five jest "e2e" billing files are pure tautologies; `npm run test:e2e` was
  deliberately kept out of the PR gate.
- `CLAUDE.md`'s naming-check command uses `python`, which does not exist on
  this machine (`python3` / `uv run python` only).

---

*Handoff 02's actual stopping point: four commits (`f8f6bf3`, `0ca1313`,
`9134ff8`, `2af3816`). The backend suite is 2118 tests, 0 failed / 0 errors,
stable under random ordering. The branch is unpushed — blocked on push
protection, not on choice. No product code was touched; the suite is green
because the instrument was repaired, not because behavior changed.*
