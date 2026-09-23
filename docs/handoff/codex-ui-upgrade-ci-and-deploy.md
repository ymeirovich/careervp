# Handoff: Finish CI green on `ui-upgrade`, merge to `main`, deploy, and confirm Tavily key in SSM

You are taking over an in-flight task in the **careervp** repo. Your job is to get the
`ui-upgrade → main` PR (**PR #219**) fully green, merge it, let the `main` deploy run, and
confirm the Tavily API key lands in SSM. Read this whole document before doing anything.

## Mission (definition of done)
1. All required checks on **PR #219** (`ui-upgrade` → `main`) pass.
2. PR #219 is merged to `main` (use the repo's git helpers, see below).
3. The `Deploy` workflow runs on `main` and succeeds.
4. SSM parameter `/careervp/dev/tavily-api-key` exists/updated (the deploy writes it from the
   `TAVILY_API_KEY` GitHub secret — see "Tavily → SSM" section). Confirm it.

## Repo facts you must know
- Working dir for backend: `src/backend`. Tests/lint/types are run from there.
- Mandatory backend checks before any commit (per `CLAUDE.md`):
  - `cd src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict`
- Test commands:
  - Unit: `cd src/backend && uv run pytest tests/unit -q`
  - Integration: `cd src/backend && uv run pytest tests/integration -q`
  - Infra: `cd src/backend && uv run pytest tests/infrastructure -q` (CI: `make infra-tests`)
- Git helpers (USE THESE; do not hand-roll):
  - Commit: `scripts/git/safe_commit.sh "<message>"` (stages all, runs pre-commit, commits)
  - Merge to main: `scripts/git/safe_merge_to_main.sh <feature-branch>` (pushes, creates/uses PR,
    `gh pr merge --merge`, verifies merge commit on origin/main, then syncs main)
  - **Never** use `gh pr merge --delete-branch` in this repo.
- End commit messages with: `Co-Authored-By: <your-attribution>`

## ⚠️ The #1 gotcha: CI has NO ambient AWS region; your laptop does
Most "passes locally, fails in CI" issues in this repo are because your shell has an AWS region
(`~/.aws/config` or env) that masks bugs. **Always reproduce CI conditions** by stripping the
region and AWS config:

```bash
cd src/backend
env -u AWS_DEFAULT_REGION -u AWS_REGION \
    AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null \
    uv run pytest tests/unit tests/integration -q -p no:cov --tb=line
```
If it's green under that command AND mypy is clean, it will be green in CI's unit/integration jobs.

## State of the branch (already committed & pushed to `origin/ui-upgrade`)
Latest commits on `ui-upgrade` (most recent first):
- `5de2695` Fix CI-only unit failures: region env leak + ripgrep dependency
- `c30a4ec` Merge remote-tracking branch 'origin/main' into ui-upgrade  (conflict resolution)
- `5ca2f9f` Fix CI: mypy decorator typing + 8 failing integration tests
- (older) `04a07dd`, `4ab2930`, `c2f5e21`, ...

### Already fixed and verified locally (mypy clean; full unit+integration 1437 passed / 0 failed under the no-region command above):
1. **mypy decorator typing** — `src/backend/careervp/handlers/utils/rest_api_resolver.py` uses a
   `typed_exception_handler` cast wrapper. `mypy.ini` has, scoped to that module:
   `disable_error_code = annotation-unchecked, untyped-decorator, redundant-cast`.
   Rationale: powertools' `exception_handler` resolves as *typed* in CI but *untyped* locally; the
   two error codes cover both. Do not add inline `# type: ignore` here — formatters strip it and CI
   flags it unused.
2. **Integration tests** (`tests/integration/`):
   - `test_export_handler_integration.py`: cover_letter item needs `ARTIFACT#COVER_LETTER#<job>`
     key; cv_tailored item needs a `job_id` field (handler filters on it) and the fixture pins
     `DYNAMODB_TABLE_NAME` so it's hermetic under full-suite ordering.
   - `test_manual_endpoints_regression.py`: VPR-trigger tests patch
     `vpr_submit_handler.load_confident_company_research_artifact` to clear the CR dependency gate;
     CR-retry tests rewritten for the FE-UI-053 async SQS enqueue flow (handler no longer calls
     `research_company` synchronously — it enqueues via `boto3.client('sqs').send_message` and
     requires `COMPANY_RESEARCH_QUEUE_URL`; also patch `write_cr_processing`).
   - `test_deployed_parity_contract.py`: now recognizes **proxy mounts** (`("/auth", ...)`,
     `("/billing", ...)`, `("/gap-analysis", ...)`) so routes served by a proxy Lambda aren't
     reported missing. See `_load_infra_proxy_prefixes()` / `_is_covered_by_proxy()`.
   - `test_tavily_research_e2e.py`: a hard-fail writes a terminal `status='failed'` row
     (FE-UI-053 R6), so it asserts `status == 'failed'` instead of expecting no row.
3. **Unit tests** (CI-only failures from the no-region condition):
   - `tests/unit/test_dynamo_dal_handler.py`: its `aws_env` fixture used to `os.environ.pop(...)`
     `AWS_DEFAULT_REGION` (+creds) in teardown, leaking a region-less env to later tests →
     `botocore.NoRegionError` in CI for gap-analysis / trial-enforcement / vpr-worker tests.
     Now uses `monkeypatch.setenv` so teardown restores the conftest baseline. **Pattern to watch:**
     any test that mutates `os.environ` for AWS vars must use `monkeypatch`, never raw set/pop.
   - `tests/unit/test_web_search.py::test_duckduckgo_removed`: replaced `subprocess.run(['rg', ...])`
     with pure-Python file scanning (`rg`/ripgrep isn't installed on CI runners).

## The merge situation (important context)
- PR #218 "merged ui-upgrade → main" at 15:02 today, but main only contains the **merge commit**
  (`cbf3253`) — the current `ui-upgrade` (158 commits) was a different/rebased lineage, so main was
  effectively **missing the whole feature branch**. PR #219 brings it in.
- The `ui-upgrade ← origin/main` merge (`c30a4ec`) had 11 conflicts; ALL were resolved to **ours**
  (`ui-upgrade`), which is the newer, correct lineage. Verified e.g. `export_handler.py` keeps the
  `experience: list | str` handling the cv_tailored test relies on. `api_construct.py` was
  **auto-merged** (not a conflict) — see the open blocker below; double-check it.

## ⛔ OPEN BLOCKER — fix this next
CI infra tests fail (`make infra-tests` → `tests/infrastructure/test_l2_api_gateway_authorizer.py`):
```
FAILED test_public_routes_are_unauthenticated  - AssertionError: missing route POST /auth/refresh
FAILED test_protected_routes_use_cognito_auth  - assert False (some protected method != COGNITO_USER_POOLS)
```
These assert against the **synthesized CloudFormation template** (CDK synth), and are
**auth-security-sensitive**. Do NOT blindly edit the test to pass. Investigate properly:

1. Reproduce: `cd src/backend && uv run pytest tests/infrastructure/test_l2_api_gateway_authorizer.py -q --tb=short`
2. Read the test (`PUBLIC_ROUTES`, `_method_records`, `_template`) and
   `infra/careervp/api_construct.py` (auth routes are mounted via the `/auth` **proxy**:
   `("/auth", self.auth_api_func, False)` — the `False`/`True` is the auth flag). Proxy mounts
   synthesize a `/{proxy+}` `ANY` method, not discrete `POST /auth/refresh`, which likely explains
   "missing route".
3. Decide the correct fix by determining INTENT:
   - Is `/auth/refresh` meant to be **public** (no Cognito) or **protected**? The api_construct
     comments historically say: public = `/health`, `/auth/register`, `/auth/login`,
     `/billing/webhook`; protected = `/auth/refresh` and everything else. Confirm against the
     current source and the auth handler.
   - If the test's expectation list is stale vs. a deliberate routing change in the merged
     `api_construct.py`, update the test. If the **merged `api_construct.py` is wrong** (auto-merge
     produced an incorrect auth flag / route), fix the infra instead. Compare:
     `git show origin/main:infra/careervp/api_construct.py` vs the current file, and
     `git log -p --follow infra/careervp/api_construct.py` to see what each lineage intended.
   - Whatever you conclude, ensure the **actual** synthesized template has: public routes with
     `AuthorizationType: NONE` and all other (non-OPTIONS, non-/swagger) routes with
     `COGNITO_USER_POOLS`. Security correctness wins over making the test green.
4. Re-run infra tests + the full no-region unit/integration command + mypy. All must pass.
5. Commit via `scripts/git/safe_commit.sh "<message>"` and push.

After this, re-check PR #219: `gh pr checks 219`. Note some required `pull_request` workflows are
**path-filtered on `src/backend/**`**, so they only re-run when backend files change (your fixes do).
Also: GitHub won't run PR checks while the PR is in a CONFLICTING/DIRTY state — keep it MERGEABLE.

## When PR #219 is fully green → merge
```bash
cd <repo root>
scripts/git/safe_merge_to_main.sh ui-upgrade
```
(or `gh pr merge 219 --merge` if the helper's PR auto-detect misbehaves; never `--delete-branch`).
Verify the merge commit is on `origin/main`.

## Tavily key → SSM (mission step 4)
- `/.github/workflows/deploy.yml` triggers on **push to `main`** and, at the dev step, runs:
  ```
  if [ -n "$TAVILY_KEY" ]; then aws ssm put-parameter --name "/careervp/dev/tavily-api-key" --value "$TAVILY_KEY" --type SecureString --overwrite; fi
  ```
  where `TAVILY_KEY=${{ secrets.TAVILY_API_KEY }}`. The secret was set 2026-06-27, so the
  merge-triggered deploy populates SSM automatically. **You cannot `put-parameter` it manually** —
  the value only exists in GitHub secrets, not on disk.
- After the merge, watch the deploy: `gh run watch <run-id>` (find via `gh run list --branch main`).
- Confirm SSM after deploy succeeds:
  `aws ssm get-parameter --name "/careervp/dev/tavily-api-key" --query "Parameter.Name" --output text`
  (requires AWS creds for the dev account; if you can't auth locally, confirm via the deploy log's
  SSM step output instead).

## Guardrails
- Reproduce every CI failure under the **no-region** command before fixing; don't trust a bare
  local run.
- Prefer fixing the test when the production code is correct; prefer fixing code when the test
  encodes the right contract (especially for **auth** — never weaken auth to pass a test).
- Run mandatory checks before each commit; keep PR #219 MERGEABLE so checks run.
- Don't commit test-regenerated evidence JSONs (e.g.
  `docs/beta/evidence/I2_persistence/persistence-roundtrip-report.json`,
  `docs/beta/evidence/I3_auth/auth-abuse-matrix.json`) — `git checkout --` them before committing.
