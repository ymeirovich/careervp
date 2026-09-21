# HANDOFF 08 — J3 fails client-side; and the baseline you inherited was fiction

**Model: Opus 5, high effort.** Fresh session at the repo root, on
`tools/proof-harness`.

Parent plan: `docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md`. **Do not trust its
W0/W1 sections** — see "What the plan gets wrong" below. Handoff 06 is marked
SUPERSEDED; handoff 07 is executed.

---

## Read this first: the headline number changed meaning

`N = 2 of 9`, measured 2026-09-21 against the **deployed** frontend and devx.

The `3 of 9` that has anchored this program since 2026-09-14 was measured
against **`http://localhost:3000`** with an empty `deployed_sha`. Compare the
proofs yourself:

```bash
python3 -c "
import json
for f in ['docs/evidence/journey-20260914T100043-5022510.json',
          'docs/evidence/journey-20260921T125027-39ef4b3.json']:
    d=json.load(open(f)); print(f.split('/')[-1], d['base_url'], d['deployed_sha'], d['journey_reached'])
"
# 2026-09-14  http://localhost:3000            ''                      3
# 2026-09-21  https://db-redesign...amplifyapp.com  7c08d89...-dirty   2
```

**2 is not a regression from 3.** The 3 described a developer's laptop.
`HARNESS.md` had already marked that proof non-reproducible and nobody noticed
what it was actually measuring. **2 of 9 is the first honest baseline this
project has.** Do not "restore" the 3.

---

## Step 0 — Verify this session's claims

| # | Command | Expected |
|---|---|---|
| 0.1 | `git show origin/main:.github/workflows/pr-validation.yml \| grep -c 'tests/regression'` | `1` |
| 0.2 | `git show origin/main:.github/workflows/cdk-diff.yml \| grep -c 'secrets.AWS_ACCESS_KEY_ID'` | `0` |
| 0.3 | `gh workflow list --all --json name,state --jq '.[]\|select(.name=="Deploy")\|.state'` | `disabled_manually` |
| 0.4 | `aws iam list-access-keys --user-name careervp_user --query 'AccessKeyMetadata[].[AccessKeyId,Status]' --output text` | **two** keys, both `Active` (`…DGMPMWNS` old, `…HAFZ64UG` new) |
| 0.5 | `aws cloudformation describe-stacks --stack-name CareerVpCrudDevx --region us-east-1 --query "Stacks[0].Outputs[?OutputKey=='DeployedGitSha'].OutputValue" --output text` | `7c08d89…-dirty` |
| 0.6 | `aws cloudformation describe-stack-resources --stack-name CareerVpCrudDevx --region us-east-1 --query "StackResources[?contains(LogicalResourceId,'CrudFeaturesNestedStack')].ResourceStatus" --output text` | `UPDATE_COMPLETE` (nested stack intact) |
| 0.7 | `cd src/backend && uv run pytest -q --tb=no -p no:cacheprovider -p no:randomly \| tail -1` | `2058 passed, 48 skipped, 12 xfailed` |
| 0.8 | `./scripts/ops/blast-radius.sh push db-redesign` | `deploy-backend-dev`, stack `CareerVpCrudDevx`, gate `environment=devx` |

**0.8 must read `devx`, not `dev`.** `dev` has 0 protection rules. If it reads
`dev`, a push to `db-redesign` deploys your real backend with no approval.

---

## Step 1 — J3: the submit click never reaches the API

This is the work. Everything downstream of J3 has never executed.

### What is already ruled out — do not re-derive these

| Hypothesis | Verdict | Evidence |
|---|---|---|
| Form didn't fill | **No** | `docs/evidence/journey/20260921T125027-39ef4b3/J3-create-application.png` shows title, company, description, URL and "Yitzchak Probe / UPLOADED CV" all set |
| Credits exhausted | **No** | `TRIAL` record: `application_count 0`, `trial_active true`. The UI's "Credits: 0 / 3" is used-of-total, not remaining |
| Backend rejected it | **No** | `/aws/lambda/careervp-application-api-lambda-devx` has **zero** invocations that day; last log event `2026/09/14` |
| Row created, redirect failed | **No** | both application rows for this user date from `2026-08-03` |
| Wrong API URL in the build | **No** | Amplify `db-redesign` sets `NEXT_PUBLIC_API_URL` to `https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod`, which matches the devx API Gateway output exactly |
| Cognito broken | **No** | test user `CONFIRMED` + `Enabled`; J1 passes |

**Therefore: the failure is client-side, between the click and the fetch.** No
network request is issued.

### The sharpest clue

J3 **passed on `localhost:3000`** on 2026-09-14 and **fails on the deployed
build** today, with the same backend. So this is environment-dependent — a
production-build or hydration difference, not plain logic. Suspects worth
checking in that order:

1. `handleSubmit` in `src/frontend/app/applications/new/page.tsx` — the comment
   in `journey.spec.ts:314-318` says it only calls `generateGapQuestions` when a
   `cvId` is available and "falls back silently to a bare application
   otherwise". A silent fallback that also fails silently would look exactly
   like this.
2. A client-side exception during submit — nothing in the harness captures
   browser console errors. **Adding that capture is probably the fastest path
   to the answer**, and is worth doing permanently.
3. Next.js production-build behaviour differing from dev (hydration, env
   inlining, route handlers).

### Reproduce it

```bash
cd src/backend
BASE_URL=https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com make journey
```

Artifacts land in `src/frontend/test-results/journey-THE-JOURNEY-J3-*/`
including `video.webm`. **Watch the video** — it shows what the page did after
the click, which no log can tell you.

Faster loop: drive it by hand in a real browser with devtools open, against
the same URL, signed in as the test user. A single console error probably ends
this investigation.

---

## Step 2 — `DeployedGitSha` is permanently `-dirty` from CI

Every CI deploy stamps `-dirty`, so `preflight` reports **FAIL** on
"deployed commit is known" (`preflight.py:170`) and every journey proof produced
this way is non-reproducible under `HARNESS.md`. It is not a transient.

**Cause, traced:** `GIT_STAMP :=` in `src/backend/Makefile:28` is
*simply-expanded*, so make evaluates it at **parse** time. CI step 5 runs
`make build` → `deps`, which regenerates `lambda_requirements.txt` and
`dev_requirements.txt` — **both tracked**. CI step 7's `make deploy-devx` then
parses the Makefile against an already-dirty tree. Locally the two files
regenerate byte-identically; in CI they do not.

Four options, **costed, not picked** (`HARNESS.md` rule 5):

| | Change | Buys | Costs |
|---|---|---|---|
| A | Untrack both generated files, add to `.gitignore` | Removes the cause outright | They are build inputs for the Lambda image; confirm nothing reads them from git |
| B | Pin `uv export` so CI output is byte-identical | Keeps them in git | Fragile across `uv` versions; will silently rot |
| C | In CI, stamp from `github.sha` instead of the worktree | Honest for CI, one line | Loses local dirty detection on that path |
| D | Move `deps` to run after `GIT_STAMP` is evaluated | Minimal surface | Make ordering is fiddly; easy to regress |

---

## Step 3 — Re-measure, and record what you find

After Step 1, re-run the journey and commit the proof to `docs/evidence/`.

**Six of nine steps have still never executed.** J4–J9 are unknown, not
"expected to pass". J1–J4 each hid their own defect; assume J5–J9 do too until
measured. State your prediction before the run so the result cannot be
rationalised afterwards.

---

## What the plan gets wrong

`PRODUCTION-PROGRAM.md` assumes `main` is the deploy target. Measured:

```
main ──8013618f
  └─ ui-upgrade        +6    ⊆ db-redesign
      └─ db-redesign   +147  ⊆ tools/proof-harness
```

Real pipeline: `db-redesign` → `db-redesign-checks.yml` → `environment: devx`
(1 required reviewer) → `make deploy-devx` (passes `p26_rehome_features=true`,
i.e. nested stacks) → `CareerVpCrudDevx`. Frontend is Amplify branch
`db-redesign`. **`main` is not a deploy target for this project.**

Specifically wrong in the plan:

- **W0.1** tells you to use `deploy.yml`'s `workflow_dispatch` devx path. That
  path calls `create-changeset`, which omits `p26_rehome_features=true`, and
  would **dissolve the nested stack devx actually runs** — 491 synthesized
  resources vs 261. Use `db-redesign-checks.yml`.
- **W0.3** is stale: zero untracked files, and its stated purpose was
  unreachable anyway (a recorded proof's `git_dirty: true` cannot be changed
  retroactively).
- **W1** was blocked on "the harness is not on main" — moot, because the deploy
  does not happen from main.

---

## Open decisions — the operator's, not yours

1. **`CareerVpCrudDev`.** On 2026-09-20 a merge to `main` triggered an ungated
   `make deploy` that applied main's older template to Dev, deleting ~70
   resources: the `CrudFeatures` nested stack, the WAFv2 WebACL, the API Gateway
   custom domain, 19 alarms, 17 CodeDeploy deployment groups, 15 Lambda
   versions, 7 aliases, 2 SQS DLQs. **No data lost** — zero tables, buckets or
   user pools. Dev was later found to be *superseded* by devx in the P-26
   cutover (last deployed 2026-07-30 from `db-redesign`@`05da819`, when that
   workflow still targeted Dev). Restore is feasible — synth of
   `ENVIRONMENT=dev` + `p26_rehome_features=true` yields 263 resources with WAF,
   domain and 5 nested stacks. Options: restore from current branch / restore
   from `05da819` / leave it.
2. **Retire the old key** `…DGMPMWNS` once every machine uses `…HAFZ64UG`.
   **Do not delete it** — ~145 branches still carry the pre-OIDC `cdk-diff.yml`
   that consumes `secrets.AWS_ACCESS_KEY_ID`.
3. **Permanently remove the `push:` trigger from main's `deploy.yml`** — it is
   only `disabled_manually`, which a future session could undo.
4. **`careervp_user` holds AdministratorAccess** via a 7-member group.
5. **The 23 MB IAM dump in git history.** It contains the old key id as a tag
   name, account id and 456 IAM ARNs — **no secret**. Reconnaissance, not
   access, and the key is now rotated. Purging needs a history rewrite and a
   force-push.
6. **`dev` environment has 0 protection rules**; four feature workflows deploy
   through it on push. Accepted in handoff 03 — re-confirm or fix.

---

## Ground rules

- **`scripts/ops/blast-radius.sh <event> <branch>` before any merge, deploy,
  deletion or credential change**, then paste Action / Triggers / Undo before
  acting. Mandatory in `CLAUDE.md`. It exists because a "one-file workflow PR"
  merge deleted 70 resources in Dev.
- Stop and ask if it reports `CREATE+EXECUTE`, `NO ENVIRONMENT GATE`, or an
  environment with `0 rules`.
- **Verify the environment; never infer it from a plan document.** Four Amplify
  branches auto-build. `main` is not a deploy target. The headline metric
  measured localhost. All three were one command away and were assumed for
  multiple handoffs.
- **A repo grep is not an inventory.** Deactivating the "unused" key broke the
  operator's own access; they held the secret outside the repo.
- Run `CLAUDE.md`'s mandatory checks for every path you touch before each
  commit. **Do not use `scripts/git/safe_commit.sh`** — four
  `docs/handoff/*.md` files remain dirty and are the operator's.
- One concern per commit.

---

## Carry forward — do not rediscover

- `preflight.py:366` and `scripts/ci/changeset_replacement_report.py` query
  `AWS::DynamoDB::Table` while every table is `AWS::DynamoDB::GlobalTable` — the
  data-loss auto-fail **can never trigger**. Load-bearing; it is why the Dev
  incident was not caught.
- `make review` cannot detect a nested-stack dissolution; it looks like an
  ordinary refactor.
- Plan A (un-nested) synthesizes **491 resources against a 600 ceiling**.
  Nesting is load-bearing. Consider making it the default instead of a flag one
  path forgets.
- `.env.e2e` was never loaded by anything until `playwright.config.ts` was
  fixed on 2026-09-21; `dotenv` is still not a dependency. `auth.ts` names two
  different paths for it; both are honoured now.
- Nothing in CI runs `make journey`. The journey has no CI path at all — it
  depends on one laptop and a gitignored credentials file.
- `-q` suppresses pytest's header including the `pytest-randomly` seed, so CI
  failures under random ordering are **not reproducible**.
- `filterwarnings = error::RuntimeWarning` does **not** fail an un-awaited
  coroutine; `error::pytest.PytestUnraisableExceptionWarning` is required.
- `env -u` does not neutralise `~/.aws/credentials`; also set
  `AWS_SHARED_CREDENTIALS_FILE` and `AWS_CONFIG_FILE`.
- `gh pr checks` shows push-event rows; use
  `gh run list --branch <b> --event pull_request`.
- `timeout` (GNU coreutils) is not installed on this machine.
- 308 e2e test blocks exist, ~1187 `TODO`-bodied, 0 `test.fixme()`. W4.1 not
  started. `docs/FEATURE-STATE.md`, `table_map.py`, `dead_api.py`,
  `dead_code.py` do not exist — W2/W3/W4.3 not started.
- `origin/tools/proof-harness` is ahead of `origin/db-redesign`. Fast-forward
  with `git push origin tools/proof-harness:db-redesign` — but that triggers a
  devx deploy needing approval. Run blast-radius first.

---

*Stopping point: the CI gate is on `main` and has been exercised by a real PR
(#223). The exposed admin key is rotated — new key live, GitHub secrets
updated, old key still Active pending the operator's machines. main's
auto-deploy is disabled. devx is deployed from `db-redesign` through a
reviewer-gated path with the nested stack intact. The journey harness was
repaired and **the journey ran against deployed code for the first time: 2 of
9**, with J3 failing client-side before any network call. Three measurement
defects were found that the plan did not know about: the journey could not run,
the headline metric measured localhost, and every CI deploy stamps `-dirty`.*
