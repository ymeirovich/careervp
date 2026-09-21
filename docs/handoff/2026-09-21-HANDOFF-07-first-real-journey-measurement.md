# HANDOFF 07 — deploy devx from db-redesign and get a real N

**Model: Opus 5, high effort.** Fresh session at the repo root, on
`tools/proof-harness`.

Parent plan: `docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md` — **but read the
correction in "The plan's root premise is wrong" below before you trust any of
its W0/W1 instructions.**

---

## Step 0 — Verify handoff 06's claims

Run these first. Commands, then prose.

| # | Command | Handoff 06 recorded |
|---|---|---|
| 0.1 | `git show origin/main:.github/workflows/pr-validation.yml \| grep -c 'tests/regression'` | `1` |
| 0.2 | `git show origin/main:.github/workflows/cdk-diff.yml \| grep -c 'secrets.AWS_ACCESS_KEY_ID'` | `0` |
| 0.3 | `aws iam list-access-keys --user-name careervp_user --query 'AccessKeyMetadata[].Status' --output text` | `Inactive` |
| 0.4 | `gh workflow list --all --json name,state --jq '.[]\|select(.name=="Deploy")\|.state'` | `disabled_manually` |
| 0.5 | `git rev-parse origin/db-redesign origin/tools/proof-harness` | identical SHAs |
| 0.6 | `cd src/backend && uv run pytest -q --tb=no -p no:cacheprovider -p no:randomly \| tail -1` | `2058 passed, 48 skipped, 12 xfailed` |
| 0.7 | `./scripts/ops/blast-radius.sh push db-redesign` | `deploy-backend-dev`, stack `CareerVpCrudDevx`, gate `environment=devx` |

**0.3 is the security one.** If it reads `Active`, someone reactivated the key —
find out who and why before doing anything else.

**0.7 must read `environment=devx`, not `dev`.** `dev` has 0 protection rules;
`devx` has 1 required reviewer. If it says `dev`, the gate has regressed and a
push to `db-redesign` will deploy to your real backend with no approval.

---

## The plan's root premise is wrong — read this before W0/W1

`PRODUCTION-PROGRAM.md` assumes `main` is the deploy target. **It is not, and
never was for this project.** Measured 2026-09-21:

```
main ──8013618f
  └─ ui-upgrade        +6    ⊆ db-redesign
      └─ db-redesign   +147  ⊆ tools/proof-harness
          └─ tools/proof-harness  +54
```

`db-redesign` has **zero** commits that `tools/proof-harness` lacks. The real
pipeline is:

| | |
|---|---|
| Code | `db-redesign` (now fast-forwarded to `tools/proof-harness` @ `7c08d89`) |
| Backend | `CareerVpCrudDevx` via `db-redesign-checks.yml` |
| Gate | `environment: devx` — 1 required reviewer |
| Deploy cmd | `make deploy-devx` (passes `p26_rehome_features=true` → nested stacks) |
| Frontend | Amplify branch `db-redesign` → `https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com` |

Consequences for the parent plan, all measured:

- **W0.1 is wrong.** It says to use `deploy.yml`'s `workflow_dispatch` devx path.
  That path calls `create-changeset`, which does **not** pass
  `p26_rehome_features=true`, and would therefore dissolve the
  `CrudFeaturesNestedStack` that devx actually runs. Synth proves it: 491
  resources without the flag vs 261 with it. **Do not use that path.**
  `db-redesign-checks.yml` → `make deploy-devx` is the correct one.
- **W0.3 is stale.** Zero untracked files exist. It also could never have
  achieved its stated purpose: the journey proof has `git_dirty: true` recorded
  *inside* it, and committing files afterwards cannot change a recorded proof.
- **W1 was blocked** because the harness (`make journey`, `make preflight`,
  `journey.spec.ts`, `HARNESS.md`) does not exist on `main`. That is now moot —
  it does exist on `db-redesign`, which is where the deploy happens.

---

## Step 1 — Approve the devx deploy, then measure. This is the whole point.

The fast-forward of `db-redesign` to `7c08d89` triggered
`DB Redesign — Pre-merge Checks`. Its `deploy-backend-dev` job waits at the
`devx` environment gate for a human.

1. Approve the run (or re-run it) — GitHub Actions → the run → Review deployments → `devx`.
2. Confirm it deployed what you expect:

```bash
aws cloudformation describe-stacks --stack-name CareerVpCrudDevx --region us-east-1 \
  --query 'Stacks[0].[StackStatus,LastUpdatedTime]' --output text
# the nested stack MUST still be there — if it is gone, the wrong deploy path ran
aws cloudformation describe-stack-resources --stack-name CareerVpCrudDevx --region us-east-1 \
  --query "StackResources[?contains(LogicalResourceId,'CrudFeaturesNestedStack')].ResourceStatus" --output text
```

3. **Then measure, which has never successfully happened:**

```bash
cd src/backend
make preflight
BASE_URL=https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com make journey
```

`HARNESS_STACK` already defaults to `CareerVpCrudDevx` — do not override it.

### What to expect, stated before the run so it cannot be rationalised after

- **Journey is 3 of 9.** J1–J3 pass, **J4 (gap analysis submit) fails.**
- J5–J9 have **never executed.** Any of them may hide its own defect; J1–J4 each
  did. Do not read "J5 failed" as one bug until you have looked.
- `DeployedGitSha` should now be a real SHA rather than absent — `create-changeset`
  was fixed in `4dce22c`, but **`deploy-devx` is the path that runs here** and it
  already passed `git_sha`. If the output is still missing, say so; that is a
  finding.
- Preflight was 7 PASS / 1 UNKNOWN / 1 FAIL. The UNKNOWN is "deployed commit is
  known" and **should now flip to PASS**. If it does not, do not proceed to J5
  debugging — find out why first.

**Record the result as a proof file** under `docs/evidence/`, with `git_sha` and
`git_dirty`, per `HARNESS.md`.

---

## Step 2 — Whatever J4 actually is

Only after Step 1 produces a number. The last recorded J4 failure was a
Playwright `toBeVisible` timeout, which is a symptom, not a cause. Read the
trace before forming a hypothesis.

Carried forward and **unverified**: `vpr_handler.py` is dead code (real path is
`vpr_submit_handler.py` → SQS → `vpr_worker_handler.py`). If J5 fails, that is
the first thing to check — but check it, do not assume it.

---

## Step 3 — Finish the key retirement (small, and it is nearly done)

The key `AKIA3PAP…MWNS` on `careervp_user` (AdministratorAccess) is **Inactive**
as of 2026-09-21. The vulnerability is closed — an inactive key cannot
authenticate. What remains is cleanup, deliberately deferred so a rollback stays
possible:

```bash
./scripts/security/remediate-exposed-key.sh 3-delete            # dry run
APPLY=1 ./scripts/security/remediate-exposed-key.sh 3-delete    # after the observation window
```

**Before running it**, confirm nothing broke while the key was inactive:

```bash
aws cloudtrail lookup-events --region us-east-1 --max-results 50 \
  --lookup-attributes AttributeKey=Username,AttributeValue=careervp_user \
  --query 'Events[].[EventTime,EventName,ErrorCode]' --output text
```

Any `AccessDenied` means something still depends on it — find it before deleting.
If nothing appears, phase 3 deletes the key, the leaking tag, and the two
vestigial GitHub secrets.

**Phase 4 (purging the 23 MB dump from git history) is still open and is the
operator's call.** It rewrites public history and forces every collaborator to
re-clone. Note what is actually exposed: the file is a
`get-account-authorization-details` dump containing the key **id as a tag name**,
account id `788159322332`, and 456 IAM ARNs — **no secret**. It is
reconnaissance, not access, and phases 2–3 already neutralised the key.

---

## Open decisions the operator has NOT made

Do not decide these for them.

1. **`CareerVpCrudDev`.** Merging PR #222 on 2026-09-20 triggered an ungated
   `make deploy` that applied main's older template to Dev, deleting ~70
   resources: the `CrudFeatures` nested stack, the WAFv2 WebACL, the API Gateway
   custom domain, 19 alarms, 17 CodeDeploy deployment groups, 15 Lambda versions,
   7 aliases, 2 SQS DLQs. **No data was lost** — zero tables, buckets or user
   pools. Subsequently measured: Dev was superseded by Devx in the P-26 cutover
   and last deployed 2026-07-30 from `db-redesign` @ `05da819`, when
   `db-redesign-checks.yml` still targeted Dev. Restore is feasible — synth of
   `ENVIRONMENT=dev` + `p26_rehome_features=true` produces 263 resources
   including the WAF, the domain and 5 nested stacks — but it may be rebuilding
   an environment that was deliberately abandoned. Options: restore from current
   branch / restore faithfully from `05da819` / leave it.
2. **Permanently remove the `push:` trigger from main's `deploy.yml`.** It is
   currently only `disabled_manually`, which a future session could undo.
3. **`careervp_user` holds AdministratorAccess** via a 7-member `AdminAccess`
   group. A CI deploy identity rarely needs `*:*`.
4. **`dev` environment has 0 protection rules.** Four feature workflows still
   deploy through it on push. Accepted in handoff 03 — re-confirm or fix.
5. **The 23 MB dump / history rewrite** (above).

---

## Ground rules

- **`scripts/ops/blast-radius.sh` before any merge, deploy, deletion or
  credential change.** This is mandatory in `CLAUDE.md`. Paste the three-line
  Action/Triggers/Undo statement before acting. It exists because a "one-file
  workflow PR" merge deleted 70 resources in Dev on 2026-09-20.
- If the tool reports `CREATE+EXECUTE`, `NO ENVIRONMENT GATE`, or an environment
  with `0 rules`, **stop and ask**.
- **Verify the environment; never infer it from a plan document.** Four Amplify
  branches auto-build, not one. `main` is not a deploy target. Both facts were
  one API call away and were assumed instead of checked for several handoffs.
- Per `CLAUDE.md`, run the mandatory checks for every path you touch before each
  commit. **Do not use `scripts/git/safe_commit.sh`** while foreign changes are
  uncommitted — four `docs/handoff/*.md` files remain dirty and are the
  operator's.
- One concern per commit.
- **Do not delete `ci/gate-on-main` or `security/oidc-cdk-diff`** until the
  operator confirms.

---

## Carry forward — do not rediscover

- `preflight.py:366` and `scripts/ci/changeset_replacement_report.py` query
  `AWS::DynamoDB::Table` while every table is `AWS::DynamoDB::GlobalTable` — the
  deploy gate's data-loss auto-fail **can never trigger**. Load-bearing, and the
  reason the Dev incident was not caught.
- `make review` cannot detect a nested-stack dissolution; it looks like an
  ordinary refactor.
- Plan A (un-nested) synthesises **491 resources against a 600 ceiling**. Nesting
  is load-bearing, not cosmetic. Consider making it the default rather than a
  flag one path forgets.
- `env -u` does not neutralise `~/.aws/credentials`; also set
  `AWS_SHARED_CREDENTIALS_FILE` and `AWS_CONFIG_FILE`.
- `-q` suppresses pytest's header, including the `pytest-randomly` seed — CI
  failures under random ordering are currently **not reproducible**.
- `filterwarnings = error::RuntimeWarning` does **not** fail an un-awaited
  coroutine; `error::pytest.PytestUnraisableExceptionWarning` is required.
- A `pull_request` on a conflicting PR gets no merge ref and runs no workflows;
  `gh pr checks` still shows push rows. Use
  `gh run list --branch <b> --event pull_request`.
- `timeout` (GNU coreutils) is not installed on this machine.
- 308 e2e test blocks exist, 0 use `test.fixme()`, and ~1187 are `TODO`-bodied —
  they pass while asserting nothing. W4.1 has not started.
- `docs/FEATURE-STATE.md`, `table_map.py`, `dead_api.py`, `dead_code.py` do not
  exist. W2/W3/W4.3 have not started.

---

*Stopping point: the CI gate is on `main` and has been exercised by a real PR
(#223). The exposed admin key is Inactive with its last consumer removed.
main's auto-deploy is disabled. `db-redesign` is fast-forwarded to `7c08d89`,
which upgrades its own deploy gate from ungated `dev` to reviewer-gated `devx`.
The devx deploy is queued and waiting for a human. **The journey has still never
been measured against a current deploy — that is Step 1 and it is the only thing
that moves N off 3.***
