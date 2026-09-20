# HANDOFF 04 — make the suite hermetic, then put the gate on main

**Model: Sonnet 5, high effort** for Steps 1 and 2 — three named failing tests
and a one-file PR. Escalate to **Opus 5, high** for Step 4, the
coroutine-never-awaited work: that is a real async correctness investigation
across two code paths and the plan names it as an escalation trigger.
**Fresh session at the repo root, on `tools/proof-harness`.**

Parent plan: `docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md`. Read its
"The handoff chain" section before starting.

Paste everything below the line.

---

You are executing **handoff 04** of a chain. **Handoff 03 paid the CI proof
that handoffs 01 and 02 both deferred.** `pr-validation.yml` has now run —
run `35524435480`, PR #221 — and it produced two findings that change what
"the suite is green" means.

**The gate works. The suite is not hermetic.** Seven of eight backend
directories match local exactly. `tests/unit` does not: three tests pass on the
development laptop and cannot pass anywhere else. The chain has been quoting
"0 failed / 0 errors" as a property of the code for three handoffs. It is a
property of the code **plus one machine's AWS credentials and a stale
`infra/cdk.out`.**

## Read first, in this order

1. This document.
2. `docs/evidence/handoff-03-20260920T154932Z-d7dc6cd.json` — **read it before
   any prose.** Go straight to `step1_real_actions_run.THE_FINDING_THE_SUITE_IS_NOT_HERMETIC`
   and `task_b_clean_integration_branch`.
3. `docs/HARNESS.md` — proof discipline and the three-result rule.
4. `CLAUDE.md` — mandatory check commands per changed path.

Do **not** open the `ASTRA-*` docs or `docs/evidence/p1-repro/`. Settled
history. `docs/evidence/astra-pass-b/iam-authorization-details.json` is 23 MB —
do not read it.

## Step 0 — Verify handoff 03's claims

Run from `src/backend/` unless noted. Commands first, prose after.

| # | Command | Handoff 03 recorded |
|---|---|---|
| 0.1 | `uv run pytest --collect-only -q \| tail -1` | `2118 tests collected` |
| 0.2 | `uv run pytest -q --tb=no -p no:cacheprovider -p no:randomly \| tail -1` | `2058 passed, 48 skipped, 12 xfailed` |
| 0.3 | the 8-directory loop | 0 failed / 8 **locally** |
| 0.4 | `uv run mypy careervp --strict \| tail -1` | `Success: no issues found in 137 source files` |
| 0.5 | repo root: `git checkout -- docs/beta/evidence/I{1,2,3}_*/*` then `uv run pytest tests/integration/test_l{0,1,2}_*.py -q` then `git status --short docs/beta/` | `4 passed`, then **empty** |
| 0.6 | `cd src/frontend && npm run typecheck` then `git status --short src/frontend/` | clean, then **empty** |
| 0.7 | `gh api repos/:owner/:repo/environments --jq '.environments[] \| "\(.name): \([.protection_rules[].type] \| join(","))"'` | `deploy-dev: required_reviewers,branch_policy` / `dev:` (empty) / `devx: required_reviewers` / `staging: required_reviewers,branch_policy` |
| 0.8 | `gh run view 35524435480 --json jobs --jq '.jobs[] \| "\(.name): \(.conclusion)"'` | 7 success, `Pytest: failure` |

**0.8 is the new chain link.** It is a historical run — it cannot change. If it
does not read back as recorded, someone deleted or re-ran it; say so.

**On the group-marker count:** the handoff-03 obligation was
`gh run view <id> --log | grep -c "::group::tests/"` expecting 8. The API
renders the marker as `##[group]tests/...`, so the literal grep returns **0**
against a fetched log. Use:

```bash
gh api repos/:owner/:repo/actions/jobs/106114031038/logs | grep -ac '##\[group\]tests/'   # -> 8
```

Do not record 0 as a failure. This is a log-rendering detail, not a result.

## Step 1 — Make the suite hermetic. Everything else is blocked behind this.

Three tests, named, with their verbatim CI output in the proof file:

| Test | Cause |
|---|---|
| `tests/unit/test_l3_state_recovery.py::TestArtifactsCompletedRecovery::test_artifacts_completed_recovery` | `botocore.exceptions.NoCredentialsError` |
| `tests/unit/test_l3_state_recovery.py::TestArtifactsGeneratingRecovery::test_artifacts_generating_recovery` | `botocore.exceptions.NoCredentialsError` |
| `tests/unit/infra/test_p03_api_surface.py::test_cdk_synth_has_no_api_gateway_resource_named_api` | `AssertionError: P-03: infra/cdk.out not found` |

Two different bugs wearing the same shirt:

- **The two `test_l3_state_recovery` tests make real boto3 calls from a unit
  test.** No `moto`, no mock. They pass on any machine with credentials
  configured. Fix with `mock_aws`, the way the rest of the suite does — do
  **not** fix by setting fake credentials in CI, which converts a hermeticity
  bug into a silent network-dependency.
- **`test_p03_api_surface` asserts against `infra/cdk.out`,** a directory
  produced by a prior `cdk synth` that is not in git and that CI never creates.
  Decide deliberately: either synthesise in the job, or skip when absent. A
  skip is honest; a pass that depends on someone having synthesised last Tuesday
  is not. Per `HARNESS.md`, **never soften a step to make it pass** — if you
  skip, the skip must be visible.

**Reproduce the CI condition locally before changing anything:**

```bash
env -u AWS_PROFILE -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY \
    -u AWS_SESSION_TOKEN AWS_EC2_METADATA_DISABLED=true \
    uv run pytest tests/unit -q --tb=short
```

If that does not reproduce 3 failures, find out what else the laptop is
supplying before you write a fix.

**Corroborating evidence you do not need to rediscover:**
`refactoring-validation.yml`'s Backend Tests job (run `35524435461`) runs
`uv run pytest tests/unit/ -v` with **no AWS env at all** and reports
**22 failed, 1408 passed**. `pr-validation.yml` sets `AWS_REGION` and
`AWS_DEFAULT_REGION` but supplies no credentials, which is why it sees 3 and not
22. The gap between 3 and 22 is a second list of non-hermetic tests, already
paid for — read that log rather than re-deriving it.

## Step 2 — Put the gate on main. This is the fastest real production step.

**Measured in handoff 03: pristine `main` is green.**

```
tests/unit 1288 passed · tests/integration 154 passed · tests/infrastructure 11 passed
tests/e2e 4 passed · tests/models 18 passed · tests/regression 39 passed
tests/security 3 passed · tests/infra no tests ran
mypy: Success: no issues found in 126 source files
```

And here is the thing nobody has stated in four handoffs:

> **`main`'s copy of `pr-validation.yml` has no 8-directory loop.** A
> `pull_request` workflow runs from the merge ref, so a PR only gets the gate
> if the merge ref carries it. **Today, no PR from any branch except
> `tools/proof-harness` is gated at all.**

So the highest-value production change in this repo is **one file**:

```bash
git diff --stat origin/main tools/proof-harness -- .github/workflows/pr-validation.yml
# 1 file changed, 71 insertions(+), 16 deletions(-)
```

Branch off `main`, take that one file, PR it. Once Step 1 lands, it will be
green, and from that moment **every** PR runs ruff, mypy, 8 pytest directories,
Jest and Vitest. Do Step 1 first — landing the gate while three tests fail in CI
blocks every PR in the repo.

## Step 3 — The integration problem, stated honestly

Handoff 03 tried to land the CI + test-isolation work on main as a small PR and
**abandoned it on measurement.** Do not retry it the same way. What was found:

| Measurement | Value |
|---|---|
| `src/backend/careervp/` branch vs main | **57 files, +3498 / −676** |
| New source files on branch only | **11** (incl. a whole `careervp/payment_providers/` package, `careervp/logic/utils/secret_provider.py`) |
| `infra/` branch vs main | **52 files, +4643 / −706** |
| Tests: branch 2058 vs main ~1517 | branch adds ~540 tests |
| PR #221 total | **768 files, +699,006 / −3,456** |

**`tools/proof-harness` is not a CI branch. It is a feature branch carrying
unmerged backend product code and unmerged CDK infrastructure.** A 27-file
cherry-pick produced 6 mypy errors and 19 test failures because it took
`billing_handler.py` without `careervp/payment_providers/`. The CI wiring
cannot be extracted cleanly, because the tests it wires up assert against source
and stacks that exist only here.

This needs a real integration decision from the operator, not a cherry-pick.
Cost the options; **do not pick for them** (`HARNESS.md` rule 5). At minimum:
what happens to the 436 `docs/` files and the 23 MB IAM dump — **which contains
an AWS Access Key ID that is now on a PUBLIC remote and is still not rotated.**

## Step 4 — The missing `await`s

Untouched since handoff 01. Two things hide behind `filterwarnings = ["error"]`:

- **~126 of 137 failures are one systemic cause** — `aws_lambda_powertools`
  emitting "No application metrics to publish". Noise; suppress it narrowly.
- **The residue is the interesting part:** `RuntimeWarning` /
  `PytestUnraisableExceptionWarning` about **coroutines never awaited**, in
  `generate_gap_questions` and `_async_process_record`.

```bash
uv run pytest -q -W error::RuntimeWarning 2>&1 | grep -i "never awaited"
```

A coroutine created and never awaited does nothing and raises nothing — it
fails silently. If `generate_gap_questions` is one, that is journey step J4
quietly not running. **Prove the behavioural consequence with a test before
changing the code.**

## Step 5 — Two red gates nobody owns

- **`security.yml` python-security**: 23 CVEs in 4 packages — `anyio` 4.12.1,
  `cryptography` 46.0.5, `pypdf` 6.14.2, `soupsieve` 2.8.4. `cryptography` wants
  46.0.5 → 50.0.0 for full coverage, which is not a patch bump. Cost it against
  the suite; **do not silently bump `uv.lock` as a side effect of other work.**
- **`refactoring-validation.yml` Infra Spec Consistency**: fails with
  `FileNotFoundError: 'infra/careervp/dynamodb_stack.py'` — it references a file
  that does not exist, so it has been failing on structure, not findings. Either
  repoint it or delete it; a gate that cannot evaluate is not a gate.

## Proof obligations for this handoff

Declared before the work.

| Claim | Command | Before | After (target) |
|---|---|---|---|
| Suite is hermetic | `env -u AWS_PROFILE -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY uv run pytest tests/unit -q` | 3 failed | 0 failed |
| The gate goes green in CI | `gh run view <new-id> --json jobs` on PR #221 | `Pytest: failure` | `Pytest: success` |
| The gate exists on main | `git show origin/main:.github/workflows/pr-validation.yml \| grep -c 'tests/regression'` | `0` | `1` |
| No regression on the branch | `uv run pytest -q --tb=no -p no:cacheprovider \| tail -1` | 2058 passed, 0 failed | 0 failed |
| Churn stays fixed | `git status --short docs/beta/ src/frontend/` after the checks | empty | empty |
| Coroutine sites enumerated | `uv run pytest -q -W error::RuntimeWarning \| grep -i "never awaited"` | unmeasured | a named list |

## Ground rules

- Per `CLAUDE.md`, run the mandatory checks for every path you touch before each
  commit.
- **Do not use `scripts/git/safe_commit.sh` while foreign changes are
  uncommitted** — it runs `git add -A`. Three handoff docs from a prior session
  are still dirty and are the operator's to handle. Use explicit
  `git add <paths>` plus `pre-commit run --files`.
- **One concern per commit.**
- **Do not deploy.** `db-redesign` and `ui-upgrade` pushes now require a reviewer
  on the `devx` environment — intentional, not a bug.
- **Do not delete the `ci/proof-base` branch.** PR #221 is based on it; deleting
  it closes the PR and destroys the only reproducible path to a firing gate.

## Carry forward — do not rediscover these

**Operator actions, not engineering:**

- **The AWS Access Key ID is on a PUBLIC remote and is NOT rotated.** In the repo
  since 2026-09-14. The push-protection allow made it public; it did not remove
  it. `docs/evidence/astra-pass-b/iam-authorization-details.json:15` and
  `docs/evidence/sweep-00-20260920T082517-b587127.md`.
- Four feature-branch workflows (`company-research`, `cover-letter`,
  `cv-tailoring`, `gap-analysis`) still deploy on push via the ungated `dev`
  environment. **Explicitly accepted** by operator decision in handoff 03.
  Required reviewers on `dev` closes all four in one change.
- `production` and `gap-remediation` environments **do not exist**; GitHub
  auto-creates a referenced environment with no protection on first use.

**Mechanics worth keeping:**

- A conflicting PR gets **no merge ref**, so **no `pull_request` workflow runs**.
  `gh pr checks` still shows rows — they come from the *push* event when the head
  SHA matches, which makes an empty gate look populated. The disambiguating
  command is `gh run list --branch <b> --event pull_request`.
- Retargeting a PR (`gh pr edit --base`) fires `pull_request` action **`edited`**,
  which is not in `types: [opened, synchronize, reopened]`. Use `gh pr close &&
  gh pr reopen` to fire `reopened`.
- A PR base does not have to be `main`. Basing on a pinned ancestor makes it
  `MERGEABLE` by construction — that is how this gate was finally observed.
- `tests/infra/test_p28_deploy_identity.py:95` asserts an execute job declares
  `environment:` — it **cannot** assert that environment is protected. `dev`
  satisfied it with `protection_rules: []`.
- A plain `grep 'make deploy'` over the workflows false-positives on
  `deploy-staging.yml` (the match is a comment). Parse the YAML.
- zsh does **not** word-split unquoted `$VAR`. `git checkout -- $PATHS` passes the
  whole list as one pathspec. Use `xargs -0`.

**From handoff 02:**

- **The eviction dance may be deletable outright.**
  `__editable___service_cdk_1_0_finder` already maps bare `careervp` to
  `infra/careervp` and the submodules are disjoint. `careervp_root()` may be
  unnecessary. Needs its own proof. **Do not remove it casually** — it is
  currently the only thing holding a 0/0 suite.
- 8 test files mutate `os.environ[...]` directly instead of via `monkeypatch`;
  `careervp/logic/auth_service.py:84` has a never-cleared `@lru_cache(maxsize=1)`;
  ~28 test files `sys.path.insert(0, INFRA_SRC)` without restoring.

**From handoff 01:**

- **`vpr_handler.py` is dead code.** `infra/careervp/api_construct.py` says so;
  `_add_vpr_lambda_integration` is never called. Real path is
  `vpr_submit_handler.py` → SQS → `vpr_worker_handler.py`. J5 unmeasured.
- `CVTailoringRequest.vpr_id` (`careervp/models/api_models.py:343`) has no
  `= None` default. Quarantined `xfail(strict=True)`.
- `DynamoDalHandler` API mismatch in `test_dal_migration_integration.py`, and the
  renamed `interview_prep_prompt` API. Both quarantined.
- 48 unit + 7 integration files call `now()`/`utcnow()`/`today()` with `freezegun`
  available but unused.

**From sweep-00:**

- `preflight.py:366` and `scripts/ci/changeset_replacement_report.py` query
  `AWS::DynamoDB::Table` while every table is `AWS::DynamoDB::GlobalTable` — the
  deploy gate's DynamoDB auto-fail **can never trigger**. Load-bearing.
- 31 of 32 devx Lambdas have 1-day log retention.
- `careervp/handlers/knowledge_base_handler.py` is routed to nothing.
- Five jest "e2e" billing files are pure tautologies; `npm run test:e2e` is
  deliberately out of the PR gate.
- `CLAUDE.md`'s naming-check command uses `python`, which does not exist on this
  machine (`python3` / `uv run python` only).

---

*Handoff 03's actual stopping point: four commits (`b638b35`, `cb279d7`,
`d7dc6cd`, `0f19beb`). The branch is pushed. PR #221 is open and **MERGEABLE**
against `ci/proof-base`. **`pr-validation.yml` has run** — 8 directory groups,
Jest 23+18 suites / 149+87 tests, Vitest 67 files / 739 tests, and a Pytest
failure on exactly 3 non-hermetic tests. W5 is closed for the two workflows that
auto-deployed with no guard. Both sources of working-tree churn are fixed. No
product code was touched. The deferred proof that opened this handoff is
**paid** — and it immediately falsified a number the chain had been quoting for
three handoffs.*
