# HANDOFF 05 — merge the gate, then finish the job handoff 04 started

**Model: Sonnet 5, high effort** for Steps 1–3 — a merge, a mechanical test
refactor, and two costed one-file gate repairs. Escalate to **Opus 5, high**
only if Step 2 turns up a second pollution class rather than the seven files
already named.
**Fresh session at the repo root, on `tools/proof-harness`.**

Parent plan: `docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md`. Read its
"The handoff chain" section before starting.

Paste everything below the line.

---

You are executing **handoff 05** of a chain. **Handoff 04 made the suite
hermetic and proved it in CI — twice — and opened the PR that puts the gate on
main.** It also falsified three premises it was handed, which is the more
important result.

**Do not repeat handoff 04's mistake of trusting a stated cause.** Three of its
five steps named a specific cause; measurement contradicted all three. The
instructions below name causes too. Check them.

## Read first, in this order

1. This document.
2. `docs/evidence/handoff-04-20260920T182339Z-d61ec4b.json` — **read it before
   any prose.** Go straight to `step1_hermeticity.THE_HANDOFF_PREMISE_WAS_FALSE`,
   `step1_hermeticity.why_CI_saw_3_and_a_bare_run_sees_23`, and
   `step2_gate_on_main.A_SECOND_FALSE_PREMISE_IN_THE_HANDOFF`.
3. `docs/HARNESS.md` — proof discipline and the three-result rule.
4. `CLAUDE.md` — mandatory check commands per changed path.

Do **not** open the `ASTRA-*` docs or `docs/evidence/p1-repro/`. Settled
history. `docs/evidence/astra-pass-b/iam-authorization-details.json` is 23 MB —
do not read it.

## Step 0 — Verify handoff 04's claims

Run from `src/backend/` unless noted. Commands first, prose after.

| # | Command | Handoff 04 recorded |
|---|---|---|
| 0.1 | `uv run pytest --collect-only -q \| tail -1` | `2118 tests collected` |
| 0.2 | `uv run pytest -q --tb=no -p no:cacheprovider -p no:randomly \| tail -1` | `2058 passed, 48 skipped, 12 xfailed` |
| 0.3 | `uv run mypy careervp --strict \| tail -1` | `Success: no issues found in 137 source files` |
| 0.4 | the hermeticity command below | `0 failed` |
| 0.5 | `gh run view 35528608346 --json jobs --jq '.jobs[] \| "\(.name): \(.conclusion)"'` | 8 jobs, **all success** |
| 0.6 | `gh run view 35527733635 --json jobs --jq '.jobs[] \| select(.name=="Pytest") \| .conclusion'` | `success` |
| 0.7 | repo root: `git show origin/main:.github/workflows/pr-validation.yml \| grep -c 'tests/regression'` | `0` **if #222 is unmerged**, `1` if merged |
| 0.8 | `gh pr view 222 --json state,mergeable --jq '"\(.state) \(.mergeable)"'` | `OPEN MERGEABLE` |

**0.4 is the one that matters.** Use this command, not the one handoff 04 was
given — `env -u` alone does **not** neutralise `~/.aws/credentials` and will
report a false green:

```bash
env -u AWS_PROFILE -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY \
    -u AWS_SESSION_TOKEN \
    AWS_SHARED_CREDENTIALS_FILE=/nonexistent/creds \
    AWS_CONFIG_FILE=/nonexistent/config \
    AWS_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 \
    uv run pytest tests/unit -q --tb=short -rs -p no:randomly | tail -1
# -> 1429 passed, 16 skipped, 4 xfailed   (0 failed)
```

**0.5 and 0.6 are historical runs — they cannot change.** If they do not read
back as recorded, someone deleted or re-ran them; say so.

**Run 0.2 at least twice without `-p no:randomly`.** Handoff 04's central
finding is that the failure count was order-dependent and nobody noticed for
three handoffs. Two random seeds is the cheapest possible guard against that
class of error returning.

## Step 1 — Merge PR #222. This is the whole point of the last four handoffs.

**PR #222 is open, MERGEABLE, and every gate job is green against main's own
code.** Handoff 04 measured main in a clean worktree before opening it:

```
tests/unit 1288 · integration 154 · infrastructure 11 · e2e 4 · models 18
regression 39 · security 3 · infra ABSENT (annotated, does not fail)
mypy: Success: no issues found in 126 source files · ruff: All checks passed
jest unit 21 suites/128 tests · jest integration 17 suites/83 tests
vitest 66 files/735 tests
```

Two failures on #222 are **pre-existing on main and unrelated**:
`python-security` (the 23 CVEs, Step 3 below) and `cdk-diff` (fails posting a
>65536-character PR comment, not on diff content).

**This needs a human to review and merge.** You cannot merge it yourself. Per
`CLAUDE.md`: merge via `gh` CLI directly from the feature branch, and **do not
use `gh pr merge --delete-branch`.**

After it merges, prove it:

```bash
git fetch origin main
git show origin/main:.github/workflows/pr-validation.yml | grep -c 'tests/regression'   # -> 1
```

From that moment every PR runs ruff, mypy, 8 pytest directories, Jest and
Vitest. **Until it merges, nothing else in this handoff matters as much.**

## Step 2 — Finish the hermeticity work. Seven files still carry the same bug.

Handoff 04 fixed **one** file. That one file caused **all 23** failures. The
same defect class is still live elsewhere, unfired only because of where those
files sit in the test order.

**Measured at the end of handoff 04** — these are counts, not estimates:

```bash
grep -rln "os\.environ\[" tests/ | wc -l                                          # -> 10
grep -rln "os\.environ\[" tests/ | xargs grep -ln "environ\.pop\|del os\.environ"  # -> 4
```

The 4 that both **set and manually delete** carry the exact defect that fired:

| File | Why it is dangerous |
|---|---|
| `tests/integration/conftest.py` | **A conftest** — its teardown applies to a whole directory, not one file |
| `tests/integration/p05_seeding.py` | `os.environ.update(env)` at line 68, wholesale |
| `tests/unit/test_llm_client.py` | set + manual delete |
| `tests/unit/test_vpr_handler.py` | set + manual delete |

The remaining 6 assign without deleting — they leak values rather than delete
them, which is a weaker but still real form of the same problem.

Note the carried-forward "8 test files" figure from handoff 02 does **not**
reproduce; the measured numbers above are 10 and 4. Trust these.

For each, convert to `monkeypatch.setenv` / `monkeypatch.delenv` and delete the
manual cleanup, exactly as `ba04eab` did for `test_cv_upload_handler.py`. Read
that commit first — it is the worked example.

**Prove each one before and after** with the two-file reproducer shape that
found the original:

```bash
uv run pytest <the-file> tests/unit/test_l3_state_recovery.py -q -p no:randomly
```

Do **not** assume a file is harmless because the suite is currently green. The
suite was green for three handoffs with this bug in it.

**Then close the loop that let it hide:** `pr-validation.yml` runs pytest
without `-p no:randomly`, so ordering differs every run. Consider pinning a
seed in CI (`-p randomly --randomly-seed=<n>`) so a failure is reproducible,
**or** deliberately keeping it random so pollution surfaces. **Cost both; do
not pick** (`HARNESS.md` rule 5) — this one is a real trade between
reproducibility and detection.

## Step 3 — The three red gates, all now costed. Pick up whichever the operator authorises.

Handoff 04 costed these; none was changed. Numbers are measured, not estimated.

- **`security.yml` python-security — 23 CVEs in 4 packages.** 10 clear with
  patch/minor bumps (`anyio` → 4.14.2, `soupsieve` → 2.9.0, `cryptography`
  → 46.0.7). 8 more clear with `pypdf` → 6.16.1, still within 6.x. The last 5
  need `cryptography` 46 → **50.0.0**, four majors. **Splitting the bump takes
  the gate from 23 to 5 at low risk and isolates the dangerous part.** Whether
  cryptography 50 passes the suite is **unmeasured** and needs its own branch.
  Per handoff 04's rule: do not bump `uv.lock` as a side effect of other work.

- **`refactoring-validation.yml` Infra Spec Consistency** — reads
  `infra/careervp/dynamodb_stack.py`, which **has never existed**. It has failed
  on structure, never on findings. All 4 constants in
  `infra/careervp/specs/dynamodb_spec.yaml` **are** referenced under
  `infra/careervp/` (measured 4/4), so repointing the script at the directory
  makes it pass today. Counter-argument, stated honestly: a gate that greps a
  directory for a constant name proves the string exists, not that the table is
  declared correctly — deleting it may beat repairing it. Three options
  (repoint / delete / leave), all cheap. **Cost them; do not pick.**

- **`cdk-diff` — new in handoff 04, in no prior handoff.** Fails with
  `Body is too long (maximum is 65536 characters)`. The diff succeeds; posting
  it fails. So it has never delivered output on a large PR — exactly when it
  would matter. Separately: **it runs with real `AWS_ACCESS_KEY_ID` /
  `AWS_SECRET_ACCESS_KEY` on the `pull_request` event.**

## Step 4 — The `asyncio.run` patches, now that the J4 scare is dead

**Handoff 04 falsified the silent-J4 hypothesis.** Both product call sites await
correctly — `gap_handler.py:185` and `company_research_worker_handler.py:443`,
the only non-definition references to either coroutine. All 8 "never awaited"
warnings come from 3 test files that `patch('asyncio.run')`.

What remains is a test-quality fix, not a correctness fix:

| File | Occurrences |
|---|---|
| `tests/unit/test_gap_handler_persistence_required.py` | 3 |
| `tests/integration/test_gap_read_after_write_roundtrip.py` | 3 |
| `tests/unit/test_company_research_worker_handler.py:451` | 1 (+1 AsyncMock residue) |

Patch the coroutine function itself, the way the other seven gap test files
already do, instead of patching a stdlib entry point process-wide. Then promote
`RuntimeWarning` in `filterwarnings` so this cannot come back.
`test_l0_gap_analysis_generation.py::test_handler_returns_questions_from_llm_generation`
already pins the real path and must stay passing.

## Step 5 — The integration decision. Still the operator's, still unmade.

Handoff 04 re-derived every number and added the one nobody had stated:

| Measurement | Value |
|---|---|
| `src/backend/careervp/` branch vs main | 57 files, +3498 / −676 |
| `infra/` branch vs main | 52 files, +4643 / −706 |
| `docs/` branch vs main | **436 files, +648,293 / −58** |
| Whole branch vs main | 758 files, +696,488 / −3,457 |
| **docs share of all inserted lines** | **93.1%** |

**The product change is 7% of the diff.** Four options with costs are in the
proof file at `step3_integration_problem_costed_not_decided`. **Do not pick for
the operator.**

The question that gates all four: **what happens to the 23.3 MB IAM dump.** It
holds an AWS Access Key ID, it is on a **PUBLIC** remote via
`origin/tools/proof-harness`, and it is **still not rotated**. It is **not on
main** — every option except leaving the branch unmerged puts it there
permanently.

## Proof obligations for this handoff

Declared before the work.

| Claim | Command | Before | After (target) |
|---|---|---|---|
| The gate is on main | `git show origin/main:.github/workflows/pr-validation.yml \| grep -c 'tests/regression'` | `0` | `1` |
| A real PR is gated by it | `gh run list --branch <any-new-branch> --event pull_request` | empty | PR Validation present |
| Remaining env polluters fixed | `grep -rln "os\.environ\[" tests/ \| xargs grep -ln "environ\.pop\|del os\.environ"` | `4` | `0` |
| Still hermetic | the Step 0.4 command | 0 failed | 0 failed |
| Order-independence | `uv run pytest tests/unit -q` ×2, no `-p no:randomly`, different seeds | unmeasured | identical counts |
| No regression | `uv run pytest -q --tb=no -p no:cacheprovider \| tail -1` | 2058 passed, 0 failed | 0 failed |
| Churn stays fixed | `git status --short docs/beta/ src/frontend/` after the checks | empty | empty |

## Ground rules

- Per `CLAUDE.md`, run the mandatory checks for every path you touch before each
  commit.
- **Do not use `scripts/git/safe_commit.sh` while foreign changes are
  uncommitted** — it runs `git add -A`. Three handoff docs from a prior session
  are **still** dirty and are the operator's to handle. Use explicit
  `git add <paths>` plus `pre-commit run --files`.
- **One concern per commit.**
- **Do not deploy.** `db-redesign` and `ui-upgrade` pushes require a reviewer on
  `devx` — intentional.
- **Do not delete the `ci/proof-base` branch.** PR #221 is based on it.
- **Do not delete `ci/gate-on-main` until #222 merges.**

## Carry forward — do not rediscover these

**Operator actions, not engineering:**

- **The AWS Access Key ID is on a PUBLIC remote and is NOT rotated.** In the
  repo since 2026-09-14. Confirmed still present in handoff 04.
  `docs/evidence/astra-pass-b/iam-authorization-details.json:15`.
- Four feature-branch workflows (`company-research`, `cover-letter`,
  `cv-tailoring`, `gap-analysis`) still deploy on push via the ungated `dev`
  environment. **Explicitly accepted** by operator decision in handoff 03.
- `production` and `gap-remediation` environments **do not exist**; GitHub
  auto-creates a referenced environment with no protection on first use.

**Mechanics worth keeping — the handoff-04 additions first:**

- **`env -u` does not neutralise `~/.aws/credentials`.** Any "no credentials"
  proof must also set `AWS_SHARED_CREDENTIALS_FILE` and `AWS_CONFIG_FILE`.
  Handoff 04 was handed a repro command that silently reported green.
- **A failure count under random ordering is a sample, not a property.** 3, 22
  and 23 were one defect seen from three orders.
- **`pytest` exits 4 for a missing directory and 5 for one that collects
  nothing.** Neither is a test failure; `|| fail=1` treats both as one.
- **`gh api repos/:owner/:repo/...` resolves the placeholders from the current
  directory's git remote.** Run it from `/tmp` and it fails with
  `unable to expand placeholder in path`.
- **`git worktree add` is how you measure another branch** with the operator's
  files dirty — no branch switch, no stash.
- **Running the suite in a clean `main` worktree dirties 7 tracked files.**
  Handoff 03's churn fixes live only on `tools/proof-harness`. Expect it, and
  `git checkout --` the churn before committing anything from a main worktree.
- A conflicting PR gets **no merge ref**, so **no `pull_request` workflow runs**.
  `gh pr checks` still shows rows from the *push* event, which makes an empty
  gate look populated. Use `gh run list --branch <b> --event pull_request`.
- Retargeting a PR (`gh pr edit --base`) fires action **`edited`**, which is not
  in `types: [opened, synchronize, reopened]`. Use `gh pr close && gh pr reopen`.
- A PR base does not have to be `main`. Basing on a pinned ancestor makes it
  `MERGEABLE` by construction.
- `tests/infra/test_p28_deploy_identity.py:95` asserts an execute job declares
  `environment:` — it **cannot** assert that environment is protected.
- A plain `grep 'make deploy'` over the workflows false-positives on
  `deploy-staging.yml`. Parse the YAML.
- zsh does **not** word-split unquoted `$VAR`. Handoff 04 hit this again with a
  command-prefix variable; use a shell function instead.

**From handoff 02:**

- **The eviction dance may be deletable outright.**
  `__editable___service_cdk_1_0_finder` already maps bare `careervp` to
  `infra/careervp`. `careervp_root()` may be unnecessary. Needs its own proof.
  **Do not remove it casually.**
- `careervp/logic/auth_service.py:84` has a never-cleared `@lru_cache(maxsize=1)`;
  ~28 test files `sys.path.insert(0, INFRA_SRC)` without restoring.

**From handoff 01:**

- **`vpr_handler.py` is dead code.** Real path is `vpr_submit_handler.py` → SQS
  → `vpr_worker_handler.py`. J5 unmeasured.
- `CVTailoringRequest.vpr_id` has no `= None` default. Quarantined
  `xfail(strict=True)`.
- `DynamoDalHandler` API mismatch in `test_dal_migration_integration.py`, and the
  renamed `interview_prep_prompt` API. Both quarantined.
- 48 unit + 7 integration files call `now()`/`utcnow()`/`today()` with
  `freezegun` available but unused.

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

*Handoff 04's actual stopping point: four commits on `tools/proof-harness`
(`ba04eab`, `0a52bdc`, `895491e`, `d61ec4b`) and one on `ci/gate-on-main`
(`2a2578b`). The suite is hermetic — 0 failed under a true no-credential
condition, proven in CI on runs `35527733635` and `35528608346`, both fully
green across all 8 jobs. **PR #222 is open and MERGEABLE against main with every
gate job green on main's own code.** The root cause was one autouse fixture
deleting the session-wide AWS credential baseline — not the two tests the
handoff named, which pass with zero credentials in isolation. Three of the
handoff's five premises were false and are recorded as such. No product code was
touched. The one thing this session could not do is merge its own PR.*
