# HANDOFF 04 — make the gate fire, then chase the missing `await`s

**Model: Sonnet 5, high effort** for Step 1 (one merge conflict in a markdown
file, then reading a run). Escalate to **Opus 5, high** for Step 3 — the
coroutine-never-awaited work is a real async correctness investigation across
two code paths, and the plan's own escalation trigger names it. **Fresh session
at the repo root, on `tools/proof-harness`.**

Parent plan: `docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md`. Read its
"The handoff chain" section before starting.

Paste everything below the line.

---

You are executing **handoff 04** of a chain. Handoff 03 finally pushed the
branch and opened a PR — and discovered why the CI gate from handoff 01 has
never been seen running. It is not push protection. It never was, after the
first blocker.

**PR #221 is `mergeable: CONFLICTING`. GitHub does not build
`refs/pull/221/merge` for a conflicting PR, and `pull_request`-triggered
workflows run on that merge ref. One add/add conflict in one markdown file has
been holding the entire backend and frontend CI gate shut.**

## Read first, in this order

1. This document.
2. `docs/evidence/handoff-03-20260920T154932Z-d7dc6cd.json` — **read it before
   any prose.** Pay particular attention to `step1_real_actions_run.the_finding`
   and `step2_w5_deploy_gating.environment_gating_measured`.
3. `docs/HARNESS.md` — proof discipline and the three-result rule.
4. `CLAUDE.md` — mandatory check commands per changed path.

Do **not** open the `ASTRA-*` docs or `docs/evidence/p1-repro/`. Settled
history. `docs/evidence/astra-pass-b/iam-authorization-details.json` is 23 MB —
do not read it.

## Step 0 — Verify handoff 03's claims

Run these from `src/backend/` unless noted. Run the commands first, compare
after.

| # | Command | Handoff 03 recorded |
|---|---|---|
| 0.1 | `uv run pytest --collect-only -q \| tail -1` | `2118 tests collected` |
| 0.2 | `uv run pytest -q --tb=no -p no:cacheprovider -p no:randomly \| tail -1` | `2058 passed, 48 skipped, 12 xfailed` — **0 failed, 0 errors** |
| 0.3 | the 8-directory loop | 0 failed / 8 |
| 0.4 | `uv run mypy careervp --strict \| tail -1` | `Success: no issues found in 137 source files` |
| 0.5 | from repo root: `git checkout -- docs/beta/evidence/I1_generators/generator-output-audit.json docs/beta/evidence/I2_persistence/persistence-roundtrip-report.json docs/beta/evidence/I3_auth/auth-abuse-matrix.json` then `uv run pytest tests/integration/test_l{0,1,2}_*.py -q` then `git status --short docs/beta/` | `4 passed`, then **empty** |
| 0.6 | `cd src/frontend && npm run typecheck && cd ../.. && git status --short src/frontend/` | clean, then **empty** |
| 0.7 | `gh api repos/:owner/:repo/environments --jq '.environments[] \| "\(.name): \([.protection_rules[].type] \| join(","))"'` | `deploy-dev: required_reviewers,branch_policy` / `dev:` (empty) / `devx: required_reviewers` / `staging: required_reviewers,branch_policy` |
| 0.8 | `python3 -c "import yaml; [print(f, yaml.safe_load(open(f'.github/workflows/{f}.yml'))['jobs']['deploy-backend-dev']['environment']) for f in ['db-redesign-checks','ui-upgrade-checks']]"` | both `devx` |

**0.5 and 0.6 are the new ones.** They are the proof that handoff 03 closed
sweep-00 finding #2. If either leaves a modified tracked file, the fix
regressed.

**If 0.2 shows any failure or error, stop and investigate.** Note that Step 1
below *will* change this number — record the pre-merge value first.

## Step 1 — Make the gate fire. This is the whole point of this handoff.

Three handoffs have now recorded "CI unverified" as deferred proof. The cause
is finally measured and it is one file wide.

### 1a — The decision the operator deferred

Handoff 03 costed the options and the operator chose to defer. **Ask again,
with the numbers below, and do not pick for them** (`HARNESS.md` rule 5).

| Option | What it costs |
|---|---|
| **Merge `origin/main` in** | Resolve one add/add conflict in `docs/db-redesign/code/code-analysis/project/runbooks/wave-1-status.md`. `main` is 10 commits / 16 files / +2779−30 ahead, of which **4 are under `src/backend`**: `careervp/handlers/artifact_dependency_utils.py`, `careervp/handlers/company_research_worker_handler.py`, and their two unit test files. Test count will rise. The 0/0 baseline must be re-established after the merge, not assumed. |
| **Rebase onto `main`** | Same end state, linear history, same one conflict replayed — but rewrites all 28 local-only commit SHAs, breaking the `git_sha` values recorded in the handoff-01/02/03 proof files (`1cdc88a`, `9134ff8`, `d7dc6cd`, and handoff 02's four commits). A real break in this repo's proof discipline. |
| **Close #221, open a narrow PR** | Branch a small head off `origin/main` carrying only `.github/workflows/pr-validation.yml` plus enough of the test-isolation work to matter, and PR that. Proves the gate fires. Does **not** prove it fires for *this* branch, which is the claim on the table. |

### 1b — Then verify against the run, not the YAML

Once #221 reports `mergeable: MERGEABLE`:

```bash
gh pr view 221 --json mergeable,mergeStateStatus
gh run list --branch tools/proof-harness --event pull_request --limit 10
gh run view <run-id> --log | grep -c "::group::tests/"
```

You are looking for:

- **8** `::group::tests/...` markers in the Pytest job log, one per directory.
- A `Jest (unit + integration)` / `Vitest` job log showing **real collected
  test counts**, not `0 tests found`.
- The job passing, or its failure captured verbatim.

**Two traps handoff 03 hit — do not repeat them:**

1. **`gh pr checks` lies by omission.** It returned five green-looking rows for
   #221. All five came from `security.yml` via the *push* event; GitHub
   surfaces push check-runs on a PR when the head SHA matches. The
   disambiguating command is
   `gh run list --branch <b> --event pull_request`. If that returns 0, no PR
   workflow ran, whatever `gh pr checks` shows.
2. **CI runs Python 3.12 in `pr-validation.yml`'s `env:`, but there is no
   `uv python install` step and `requires-python = ">=3.13"`. Local is 3.14.6.**
   Nobody has ever observed which interpreter CI actually resolves. If the
   per-directory loop is green locally and red in CI, look here first — and
   capture the failing directory's output verbatim before touching anything.

## Step 2 — Decide on the red security gate

`security.yml` is the **only** workflow that runs on a push to this branch, and
it is **red**. Run 35520223998, job `python-security`:

```
Found 23 known vulnerabilities in 4 packages
anyio        4.12.1  CVE-2026-63374, CVE-2026-64847        -> 4.14.2
cryptography 46.0.5  PYSEC-2026-35/36/3552/3553/3554,
                     GHSA-537c-gmf6-5ccf                    -> up to 50.0.0
pypdf        6.14.2  PYSEC-2026-3655/3656/3910/3911/3912/3913 -> up to 6.16.1
soupsieve    2.8.4   CVE-2026-85999, CVE-2026-86000         -> 2.9.0
```

This is a **new** finding — no prior handoff or sweep recorded it. `cryptography`
wants a jump from 46.0.5 to 50.0.0 for full coverage, which is not a patch bump
and may move transitive pins.

Cost the upgrade against the 0/0 suite and let the operator decide. **Do not
silently bump `uv.lock` as a side effect of other work.**

## Step 3 — The missing `await`s (handoff 01's strongest carry-forward)

Untouched since handoff 01. Two separate things hide behind
`filterwarnings = ["error"]`:

- **~126 of 137 failures are one systemic cause** — `aws_lambda_powertools`
  emitting "No application metrics to publish". Noise; suppress it narrowly,
  do not blanket-ignore.
- **The residue is the interesting part:** `RuntimeWarning` /
  `PytestUnraisableExceptionWarning` about **coroutines never awaited**, in
  `generate_gap_questions` and `_async_process_record`. These read as real
  missing-`await` bugs in product code, not test artifacts.

Reproduce before theorising:

```bash
uv run pytest -q -W error::RuntimeWarning 2>&1 | grep -i "never awaited"
```

A coroutine that is created and never awaited does nothing and raises nothing —
it fails silently. If `generate_gap_questions` is one of them, that is journey
step J4 quietly not running. **Prove the behavioural consequence with a test
before changing the code**, and do not "fix" it by adding `await` until you can
show what currently does not happen.

## Proof obligations for this handoff

Declared before the work.

| Claim | Command | Before | After (target) |
|---|---|---|---|
| The PR can be built | `gh pr view 221 --json mergeable` | `CONFLICTING` | `MERGEABLE` |
| pr-validation actually fired | `gh run list --branch tools/proof-harness --event pull_request` | **0 runs** | ≥1 run |
| CI ran the 8 backend directories | `gh run view <id> --log \| grep -c "::group::tests/"` | never run | `8` |
| CI ran the frontend suites | the Jest/Vitest job log | never run | real collected counts |
| The suite survives the merge | `uv run pytest -q --tb=no -p no:cacheprovider \| tail -1` | 2058 passed, 0 failed | 0 failed / 0 errors at the new count |
| Churn stays fixed | `git status --short docs/beta/ src/frontend/` after the checks | empty | empty |
| Coroutine warnings enumerated | `uv run pytest -q -W error::RuntimeWarning \| grep -i "never awaited"` | unmeasured | a named list of call sites |

## Ground rules

- Per `CLAUDE.md`, run the mandatory checks for every path you touch before
  each commit.
- **Do not use `scripts/git/safe_commit.sh` while foreign changes are
  uncommitted** — it runs `git add -A`. Three handoff docs from a prior session
  are still dirty and are the user's to handle. Use explicit `git add <paths>`
  plus `pre-commit run --files`.
- **One concern per commit.**
- **Do not deploy.** Note that `db-redesign` and `ui-upgrade` pushes now require
  a reviewer on the `devx` environment — that is intentional, not a bug.
- Do not fix unrelated product bugs.

## Carry forward — do not rediscover these

**Outstanding operator actions (not engineering):**

- **The AWS Access Key ID is now on a PUBLIC remote and is NOT rotated.** In the
  repo since 2026-09-14; the push-protection allow made it public, it did not
  remove it. `docs/evidence/astra-pass-b/iam-authorization-details.json:15` and
  `docs/evidence/sweep-00-20260920T082517-b587127.md`.
- Four feature-branch workflows (`company-research`, `cover-letter`,
  `cv-tailoring`, `gap-analysis`) still deploy on push via the ungated `dev`
  environment. **Explicitly accepted** by operator decision in handoff 03.
  Adding required reviewers to `dev` closes all four in one change.
- The `production` and `gap-remediation` GitHub environments **do not exist**;
  GitHub auto-creates a referenced environment with no protection on first use.

**Structural, found in handoff 03:**

- `tests/infra/test_p28_deploy_identity.py:95` asserts an execute job declares
  `environment:` — it **cannot** assert that environment is protected. `dev`
  satisfied it with `protection_rules: []`. Half-checkable invariant.
- A plain `grep 'make deploy'` over the workflows produces a false positive on
  `deploy-staging.yml` (the match is a comment). Parse the YAML.

**From handoff 02:**

- **The eviction dance may be deletable outright.** `__editable___service_cdk_1_0_finder`
  already maps bare `careervp` to `infra/careervp` and the two packages'
  submodules are disjoint. `careervp_root()` may be unnecessary. Cheap to test,
  needs its own proof. **Do not remove it casually** — it is currently the only
  thing holding a 0/0 suite.
- 8 test files mutate `os.environ[...]` directly instead of via `monkeypatch`;
  `careervp/logic/auth_service.py:84` has a never-cleared `@lru_cache(maxsize=1)`;
  ~28 test files `sys.path.insert(0, INFRA_SRC)` without restoring.

**From handoff 01:**

- **`vpr_handler.py` is dead code.** `infra/careervp/api_construct.py` says so;
  `_add_vpr_lambda_integration` is never called. Real path is
  `vpr_submit_handler.py` → SQS → `vpr_worker_handler.py`. J5 unmeasured.
- `CVTailoringRequest.vpr_id` (`careervp/models/api_models.py:343`) has no
  `= None` default. Quarantined `xfail(strict=True)`.
- `DynamoDalHandler` API mismatch in `test_dal_migration_integration.py`, and
  the renamed `interview_prep_prompt` API. Both quarantined.
- 48 unit + 7 integration files call `now()`/`utcnow()`/`today()` with
  `freezegun` available but unused.

**From sweep-00:**

- `preflight.py:366` and `scripts/ci/changeset_replacement_report.py` query
  `AWS::DynamoDB::Table` while every table is `AWS::DynamoDB::GlobalTable` —
  the deploy gate's DynamoDB auto-fail **can never trigger**. Load-bearing.
- 31 of 32 devx Lambdas have 1-day log retention.
- `careervp/handlers/knowledge_base_handler.py` is routed to nothing.
- Five jest "e2e" billing files are pure tautologies; `npm run test:e2e` is
  deliberately out of the PR gate.
- `CLAUDE.md`'s naming-check command uses `python`, which does not exist on this
  machine (`python3` / `uv run python` only).

---

*Handoff 03's actual stopping point: three commits (`b638b35`, `cb279d7`,
`d7dc6cd`). The branch is PUSHED for the first time and PR #221 is open against
main, CONFLICTING. W5 is closed for the two workflows that auto-deployed with no
guard; the four feature-branch workflows are accepted exposure. Both sources of
working-tree churn are fixed, so the next proof can be the first `git_dirty:
false` in this chain. The backend suite is unchanged: 2118 tests, 0 failed /
0 errors, stable under random ordering. No product code was touched. The CI
gate has still never executed — but for the first time the reason is a measured
one-file blocker rather than an open question.*
