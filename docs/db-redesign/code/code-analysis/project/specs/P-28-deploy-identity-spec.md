---
spec_id: P-28-DEPLOY-IDENTITY
title: "Deploy identity safety + CI pipeline closure: automation read-only + CreateChangeSet only, human-only ExecuteChangeSet; hard-pin account/region in app.py (fail-fast); branch-protect main + required-reviewer GitHub env + concurrency max=1 no cancel-in-progress; approval artifact = machine-parsed DescribeChangeSet Replacement report"
status: draft
owner: infra
tier: T1
scope_lock_clause: P-28
tooling:
  P-28: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}
format_note: "RED tests are TDD-first, not optional; RED-test descriptions inline (v1.3.0); pytest files written at IMPLEMENT in the real careervp repo. Clause carries an AC-### Given/When/Then block (§8.5)."
---

# Spec — Clause P-28: Deploy Identity Safety + CI Pipeline Closure

- **Status:** SPEC ONLY — do **not** implement here. Apply under TDD in the redesign implementation wave (Wave 0).
- **Governs clause:** `P-28` (deploy identity safety + CI pipeline closure). Model/effort in frontmatter above.
- **Code anchor:** `github.com/ymeirovich/careervp @ 0709bbd`. All file:line refs are at that commit.
- **Env note for the implementer:** `infra/app.py` is the CDK entry point; `.github/workflows/deploy.yml` is the deployment workflow. Both must change. GitHub repository settings (branch protection, deployment environment reviewer) require human-applied GitHub UI/API steps — document the procedure, do not attempt to automate it.
- **TDD contract:** each fix below lists the **RED test(s) to write and watch fail FIRST**, then the minimal GREEN change. No production edit without a failing test first.
- **Constraints (all sub-clauses):** the solo model means the automation agent prepares change sets and the human executes them — this boundary is the security invariant; never weaken it. The scope-lock contract files (`project-scope-lock.md`, `project-scope-lock.yaml`) are write-protected from agent sessions (§0.3); the CI check that enforces this belongs here under P-28.

---

## Current state (confirmed, grounded in live evidence)

**`infra/app.py` (lines 1–38 at anchor commit):**
```python
account = os.environ.get("AWS_DEFAULT_ACCOUNT") or os.environ.get("CDK_DEFAULT_ACCOUNT")
region = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("CDK_DEFAULT_REGION")
# ... falls back to session.Session().region_name, then STS, then "us-east-1"
```
Both `account` and `region` are inferred at runtime from environment variables, AWS session, or STS. A wrong-profile deploy silently targets a different account or region with no fail-fast check.

**`.github/workflows/deploy.yml` (lines 16–18 at anchor commit):**
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
The concurrency block has `cancel-in-progress: true`. A second push to `main` cancels an in-flight CloudFormation update, leaving the stack in a partial `UPDATE_IN_PROGRESS` or `UPDATE_ROLLBACK_IN_PROGRESS` state.

**`.github/workflows/deploy.yml` — deploy-dev job (lines 33–37):**
```yaml
deploy-dev:
  if: github.ref == 'refs/heads/main'
  runs-on: ubuntu-latest
  environment: dev
```
The `deploy-dev` job references the `dev` environment but this environment has **no required reviewer** configured in GitHub repository settings. Every push to `main` triggers a full `cdk deploy` (via `make deploy`) without human approval. The automation role (`secrets.AWS_ROLE`) executes `ExecuteChangeSet` directly.

**Root causes:**
1. `app.py` uses ambient account/region inference — wrong profile → wrong account.
2. `deploy.yml` cancels in-flight CFN updates (`cancel-in-progress: true`).
3. `deploy.yml` auto-executes `ExecuteChangeSet` without a human gate.
4. No `DescribeChangeSet` Replacement report is generated or checked before execution.
5. No CI check rejects scope-lock file changes that lack the §12 change-log row.

---

## Fix (GREEN — five sub-clauses)

### Sub-clause A — Hard-pin account and region in `infra/app.py`

Replace the ambient inference block with hard-coded constants. The target account is `788159322332` (single-account solo model, O-8) and the target region is `us-east-1`.

```python
# P-28: Hard-pinned account and region — fail fast on wrong-profile deploy.
PINNED_ACCOUNT = "788159322332"
PINNED_REGION = "us-east-1"

environment = os.getenv("ENVIRONMENT", constants.ENVIRONMENT)
# Validate: if CDK_DEFAULT_ACCOUNT is set and does not match, abort.
inferred_account = os.environ.get("CDK_DEFAULT_ACCOUNT") or os.environ.get("AWS_DEFAULT_ACCOUNT")
if inferred_account and inferred_account != PINNED_ACCOUNT:
    raise SystemExit(
        f"P-28 FAIL-FAST: CDK_DEFAULT_ACCOUNT={inferred_account!r} "
        f"does not match pinned account {PINNED_ACCOUNT!r}. "
        "Wrong AWS profile — aborting to prevent cross-account deploy."
    )
env_value = Environment(account=PINNED_ACCOUNT, region=PINNED_REGION)
```

Remove all fallback logic (`session.Session().region_name`, STS call, env-agnostic synth). The `env_value` is never `None` after this change — the `if account and region` guard is deleted.

**Decision (pinned):** the `env_value = Environment(account=..., region=...)` is ALWAYS set, never `None`. Env-agnostic synth is DISABLED for this repo after P-28 lands. A future multi-account expansion (O-8 stage/prod) adds an allow-list, not a revert to ambient inference.

### Sub-clause B — Remove `cancel-in-progress: true` from deploy workflow

In `.github/workflows/deploy.yml`, change the concurrency block:

```yaml
# P-28: max-parallel=1, NO cancel-in-progress.
# A second push to main MUST NOT cancel an in-flight CFN update.
# The second run will queue and wait.
concurrency:
  group: deploy
  cancel-in-progress: false
```

> **Note:** Using `group: deploy` (not `${{ github.workflow }}-${{ github.ref }}`) ensures all deploy triggers (push + workflow_dispatch) share one concurrency slot. `cancel-in-progress: false` means a queued run waits until the active run completes. This is MANDATORY — a cancelled mid-flight CFN update leaves the stack in `UPDATE_ROLLBACK_IN_PROGRESS` and requires human intervention.

### Sub-clause C — Split automation vs human roles; automation gets CreateChangeSet only

The deploy workflow must be restructured into two jobs:

**Job 1 — `create-change-set` (automation, no human gate):**
- Builds Lambda artifacts and synthesizes the CDK template.
- Calls `aws cloudformation create-change-set` with the synthesized template.
- Calls `aws cloudformation describe-change-set` and generates the **Replacement report** (see Sub-clause D).
- Writes the report as a GitHub Actions job summary and as a step output.
- Does NOT call `ExecuteChangeSet`.

The IAM role used by `create-change-set` MUST have ONLY:
```
cloudformation:CreateChangeSet
cloudformation:DescribeChangeSet
cloudformation:DescribeStacks
cloudformation:ListChangeSets
s3:GetObject          # for template upload bucket
ssm:GetParameters     # for CDK lookups
```
It MUST NOT have `cloudformation:ExecuteChangeSet`, `cloudformation:DeleteStack`, or any `Update:*` data-plane permissions.

**Job 2 — `execute-change-set` (human-gated):**
- `needs: create-change-set`
- `environment: deploy-prod` (or `deploy-dev`) — this environment has a **required human reviewer** in GitHub settings.
- The human reviewer reads the Replacement report from the job summary BEFORE approving.
- On approval, calls `aws cloudformation execute-change-set`.
- Runs smoke tests and evidence-integrity checks post-deploy.

The IAM role for `execute-change-set` may have `ExecuteChangeSet` but NOT `CreateStack` or `DeleteStack` — it executes only pre-approved change sets.

> **Implementation note:** CDK's `cdk deploy` command combines create + execute in one call. After P-28, automation MUST NOT call `cdk deploy` directly. Instead: `cdk synth` → `aws cloudformation package` (if needed) → `aws cloudformation create-change-set` → `describe-change-set` → stop. The `execute-change-set` job uses the raw CloudFormation CLI. The `make deploy` target in `src/backend/Makefile` must be split into `make create-changeset` and `make execute-changeset`.

### Sub-clause D — Approval artifact: machine-parsed DescribeChangeSet Replacement report

After `create-change-set` completes, the workflow generates a Replacement report by parsing `describe-change-set` output:

```bash
aws cloudformation describe-change-set \
  --stack-name "$STACK_NAME" \
  --change-set-name "$CHANGESET_NAME" \
  --output json > /tmp/changeset.json

# Parse per-resource Replacement field
python3 - <<'EOF'
import json, sys

with open("/tmp/changeset.json") as f:
    cs = json.load(f)

PROTECTED_TYPES = {
    "AWS::ApiGateway::RestApi",
    "AWS::DynamoDB::Table",
    "AWS::S3::Bucket",
    "AWS::Cognito::UserPool",
}

report = []
auto_fail = False
for change in cs.get("Changes", []):
    rc = change.get("ResourceChange", {})
    rtype = rc.get("ResourceType", "")
    replacement = rc.get("Replacement", "False")
    logical_id = rc.get("LogicalResourceId", "")
    entry = {
        "LogicalId": logical_id,
        "Type": rtype,
        "Action": rc.get("Action"),
        "Replacement": replacement,
    }
    report.append(entry)
    if replacement == "True" and rtype in PROTECTED_TYPES:
        auto_fail = True
        entry["AUTO_FAIL"] = True

print(json.dumps({"changes": report, "auto_fail": auto_fail}, indent=2))
if auto_fail:
    print("AUTO-FAIL: Replacement:True detected for a protected resource type.", file=sys.stderr)
    sys.exit(1)
EOF
```

- If the script exits non-zero (auto-fail), the `create-change-set` job FAILS and the `execute-change-set` job never runs.
- The `report` JSON is written to the GitHub Actions job summary using `$GITHUB_STEP_SUMMARY`.
- The human reviewer sees this report inline in the GitHub UI before approving.

**Rationale (scope-lock v2.0.0/A2):** `DescribeChangeSet`'s `Replacement` field is CFN's own computation, stronger than `cdk diff` string-heuristic. `cdk diff` may say "may be replaced" when CFN knows it is not, or vice versa. The machine-parsed report is the authoritative approval artifact.

### Sub-clause E — Contract self-protection CI check (§0.3)

Add a CI job that rejects any PR or push that modifies `project-scope-lock.md` or `project-scope-lock.yaml` without meeting ALL of the following criteria:

1. **Both files changed together** — a diff that touches one but not the other fails.
2. **A §12 change-log row is present** — the change-log YAML block in `project-scope-lock.yaml` must contain a new entry with the date of the change.
3. **`Version:` is bumped** — the `version` field in `project-scope-lock.yaml` must be strictly greater than the version on `main`.
4. **A human-signed approval trailer is present** — the commit message or PR description must contain a trailer of the form `Scope-Lock-Approved-By: <name> <date>`.

Implement as `.github/workflows/scope-lock-guard.yml` (a new workflow triggered on `pull_request` and `push` targeting `main`). The check script is `scripts/ci/check_scope_lock_integrity.py`.

If a push touches only non-scope-lock files, this check is a no-op (passes immediately).

---

### RED tests to write first (watch fail)

All tests live in `tests/infra/test_p28_deploy_identity.py` (authored at IMPLEMENT time, not now).

**`test_app_py_pins_account_and_region`**
- Read `infra/app.py` as a string.
- Assert: the string contains `"788159322332"` as a literal (not only in a comment) AND contains `"us-east-1"` as a literal assigned to a variable used in the `Environment(...)` call.
- Assert: the string does NOT contain `os.environ.get("CDK_DEFAULT_ACCOUNT")` as the primary account source (i.e., it must not fall back to ambient inference without a fail-fast check).
- Assert: the string does NOT contain `session.Session().region_name` (the old fallback is removed).
- This test MUST FAIL before Sub-clause A is implemented — at anchor commit `infra/app.py:13-14` uses `CDK_DEFAULT_ACCOUNT`/`CDK_DEFAULT_REGION` as the primary sources with no fail-fast.

**`test_deploy_workflow_has_required_reviewer`**
- Read `.github/workflows/deploy.yml` as a string (and/or parse as YAML).
- Assert: the file references an `environment:` key in the deploy job(s) that requires human review.
- Assert: the environment name references a named environment (string value, not an inline `environment: name: ... url: ...` block without a reviewer — the reviewer must be configured in GitHub settings, but the spec test asserts the `environment:` key is present so GitHub settings can enforce it).
- Assert: the job that calls `ExecuteChangeSet` (or `make deploy`) is NOT the same job that runs without an environment gate — it is a separate job with `needs:` on the change-set creation job AND an `environment:` block.
- This test MUST FAIL before Sub-clause C is implemented — at anchor commit the `deploy-dev` job has `environment: dev` but no separation between create and execute, and the `dev` environment has no required reviewer in GitHub.

**`test_deploy_workflow_no_cancel_in_progress`**
- Parse `.github/workflows/deploy.yml` as YAML.
- Navigate to the top-level `concurrency:` block.
- Assert: `concurrency.cancel-in-progress` is `false` (boolean) or absent (absence defaults to `false` in GitHub Actions).
- Assert: `concurrency.group` is the literal string `"deploy"` (not a template expression that would create per-branch concurrency groups allowing parallel deploys).
- This test MUST FAIL before Sub-clause B is implemented — at anchor commit `cancel-in-progress: true` is set (line 18 of `deploy.yml`).

**`test_scope_lock_ci_check_rejects_missing_changelog`**
- This is a unit test of the `scripts/ci/check_scope_lock_integrity.py` script.
- Construct a synthetic diff that modifies both `project-scope-lock.md` and `project-scope-lock.yaml` but does NOT add a new `version:` entry or change-log row to `project-scope-lock.yaml`.
- Call the check script (or its importable `check_integrity(diff, yaml_content)` function) with this synthetic input.
- Assert: the return code / raised exception / return value indicates FAILURE.
- Also test the PASS path: a diff that touches both files, has a bumped `version:`, has a new change-log row in the YAML `changelog:` section, and has a `Scope-Lock-Approved-By:` trailer in the commit message → assert PASS.
- This test MUST FAIL before Sub-clause E is implemented (the script does not exist).

---

### Acceptance Criteria

**AC-P28-1** — *Given* a deploy is triggered with the wrong AWS profile (i.e., `CDK_DEFAULT_ACCOUNT` resolves to an account other than `788159322332`), *When* `infra/app.py` runs, *Then* it raises `SystemExit` with a P-28 fail-fast error message before any CDK stack synthesis occurs. No CloudFormation API call is made.

**AC-P28-2** — *Given* a second push lands on `main` while a CloudFormation update is in-flight*, *When* the second deploy workflow starts, *Then* it waits in the queue (not cancelled) until the first CFN update completes. The first update finishes or rolls back cleanly; the second then runs.

**AC-P28-3** — *Given* the updated `deploy.yml`, *When* automation creates a change set (Job 1), *Then* it CANNOT call `ExecuteChangeSet` (the IAM role lacks the permission). The `execute-change-set` job (Job 2) is blocked until a human reviewer approves the GitHub deployment environment gate.

**AC-P28-4** — *Given* the Replacement report contains `Replacement: True` for any `AWS::ApiGateway::RestApi`, `AWS::DynamoDB::Table`, `AWS::S3::Bucket`, or `AWS::Cognito::UserPool`, *When* the report script runs, *Then* it exits non-zero and the `execute-change-set` job never runs. The human reviewer sees the AUTO-FAIL annotation in the job summary.

**AC-P28-5** — *Given* a PR or push that modifies `project-scope-lock.md` or `project-scope-lock.yaml` without a §12 change-log row, a bumped version, both files changed, and a human-signed approval trailer, *When* the `scope-lock-guard` CI check runs, *Then* it fails the check and the PR is blocked from merging to `main`.

**AC-P28-6** — *Given* a push to any non-`main` branch (feature branch), *When* the deploy workflow runs, *Then* it does NOT execute `ExecuteChangeSet` (even if triggered via `workflow_dispatch`). Only the `main` branch path reaches the human-gated execute job.

---

### Done-when

All four RED tests pass; `ruff`/`mypy` clean; AC-P28-1..6 hold; `infra/app.py` contains the pinned account and region with a fail-fast guard; `.github/workflows/deploy.yml` has `cancel-in-progress: false` and a two-job split (create / execute); `.github/workflows/scope-lock-guard.yml` exists and the check script passes its unit tests; no application handler code changed; the GitHub repository settings (branch protection on `main`, required reviewer on `deploy-dev` and `deploy-prod` environments) are documented in a human-apply runbook (not automated).

---

## Sequencing within Wave 0

P-28 is a Wave 0 guardrail. Sub-clauses A and B (account pin + cancel-in-progress fix) are low-risk and ship first in a single commit. Sub-clauses C and D (job split + Replacement report) are the structural change and ship second. Sub-clause E (scope-lock guard) ships third, as a standalone CI workflow with no CDK dependency.

The human-apply GitHub steps (branch protection, required reviewer on environments) MUST be completed by the human BEFORE the first change-set-only deploy runs — otherwise `execute-change-set` has no gate.

P-28 is a hard prerequisite for P-27 (the P-27 termination-protection deploy must go through the P-28 change-set gate), and for all subsequent additive waves (the human-gated execute is the safety mechanism for the entire redesign).
