# HANDOFF 11 — baseline, predict, merge, validate

**Model: Opus 5, high effort.** Fresh session at the repo root, on
`tools/proof-harness`.

Executes in strict order. **Each phase gates the next.** If a phase cannot
complete, stop and report — do not proceed with a partial baseline, because a
partial baseline makes every later claim unfalsifiable.

This handoff validates *whatever is on `tools/proof-harness` when you run it*.
Phase 0.4 makes you enumerate that first; do not assume you know.

---

## The ordering question, answered — read before Phase 2

**The prediction is written and committed BEFORE the push and merge. Not after.**

This is not a style preference, and you should not re-derive it:

- A prediction's entire value is that it cannot be adjusted once the result is
  visible. Stated afterwards it is a description, not a prediction.
- By the time a merge completes, CI logs, job durations, the changeset contents
  and the deploy's own success/failure have already leaked the answer. You will
  not notice yourself adjusting. Nobody does.
- Committing it first makes the ordering **structural**: git history proves the
  prediction predates the result. It stops being a matter of your discipline.

Therefore: **Phase 2 commits `docs/evidence/prediction-<date>.md`, and Phase 3
pushes.** In that order, in separate commits.

**If the result contradicts the prediction, you do not edit the prediction
file.** Add a new `## Result` section below it recording the miss and what it
implies. A prediction quietly corrected after the fact is worse than no
prediction, because it manufactures a track record of being right. Two
predictions were made on 2026-09-21; one was wrong, and it was recorded as
wrong. Do the same.

---

## Phase 0 — preconditions

**0.1 Trial budget.** `make journey` consumes one trial application per run.
This handoff runs it **twice** (Phase 1 baseline, Phase 4 post-deploy), and
`TRIAL_LIMIT_APPLICATIONS = 3`. Reset first so you hold 3 credits for 2 planned
runs plus one spare:

```bash
NOW=$(python3 -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())")
python3 -c "
import json,sys
json.dump({'pk':{'S':'USER#848834a8-4061-703d-419c-0294d4e88d66'},'sk':{'S':'TRIAL'},
 'created_at':{'S':sys.argv[1]},'updated_at':{'S':sys.argv[1]},
 'application_count':{'N':'0'},'trial_active':{'BOOL':True}}, open('/tmp/trial.json','w'))
" "$NOW"
aws dynamodb put-item --region us-east-1 --table-name careervp-users-table-devx --item file:///tmp/trial.json
```

Verify: `application_count` is `0`. Without this you will run out mid-validation
and misread `403 trial_expired` as a regression from your own change.

**0.2 Tree state.** Only the four operator-owned `docs/handoff/*.md` files may
be dirty. Anything else: commit or stash before starting. Proofs record
`git_dirty`, and a proof from a tree with your uncommitted work in it proves
nothing about the code you merged.

**0.3 Baseline stack SHA.**

```bash
aws cloudformation describe-stacks --stack-name CareerVpCrudDevx --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='DeployedGitSha'].OutputValue" --output text
```

Expected today: `7c08d89286d181885ebefd49702159c0d5d08667-dirty`. **Write it
down — it is your rollback target.**

**0.4 Enumerate what you are about to merge.** Do not assume.

```bash
git log --oneline origin/db-redesign..HEAD
git diff --stat origin/db-redesign..HEAD
git diff --name-only origin/db-redesign..HEAD | grep -E '^(src/frontend|src/backend|infra)/'
```

The third command is the deploy trigger. If it prints anything at all, the
merge deploys `CareerVpCrudDevx` — **including when the only match is a test
file or a comment.** The path filter does not read the diff. See `CLAUDE.md` →
"What actually fires".

---

## Phase 1 — capture the baseline (before merge, against currently-deployed code)

```bash
cd src/backend
make preflight
BASE_URL=https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com make journey
make state
```

**Reading `preflight` honestly:** two things, not one.

First, `premise_tables` changed behaviour in `0c04fc9` — it previously matched
only `AWS::DynamoDB::Table`, so every real `GlobalTable` was reported
*unmanaged* regardless of stack ownership. Your baseline runs the fixed script.
**Do not compare this run's table premise against any preflight proof recorded
before `0c04fc9`** — it will differ for reasons that have nothing to do with
your deploy.

Second, the premise `deployed commit is known` will **FAIL**. Every CI deploy stamps `DeployedGitSha` with `-dirty`
(`src/backend/Makefile:28`, handoff 08 Step 2, still undecided). That failure is
pre-existing and unrelated to your change. Read the other seven premises
individually. Do not let one permanently-red check train you to skim the report.

Expected journey result as of 2026-09-21: **3 of 9**, J4 failing because
gap-question generation is a synchronous LLM call in a Lambda with a 30s
timeout. If you get a different number, **stop** — the ground moved before you
started, and you must find out why before merging anything.

Commit the proofs:

```bash
git add docs/evidence/
git commit -m "docs(evidence): pre-merge baseline against <sha>"
```

**Do not run anything else that writes a journey proof until Phase 4.**
`make compare --kind journey` takes the two most recent proofs; a stray third
run silently destroys the comparison.

---

## Phase 2 — state expected results, and commit them

Write `docs/evidence/prediction-2026-09-21.md`. Cover, for **each** change you
enumerated in 0.4:

1. the observable you expect to change,
2. the exact command that will show it,
3. what you expect **not** to change,
4. a single headline number: the journey result you predict, as `N of 9`.

Reference table for Handoff 09's changes — extend it for whatever else is in
your diff, and do not treat it as complete:

| Change | Expect | Command | Do **not** expect |
|---|---|---|---|
| `ENVIRONMENT` on 26 Lambdas | `get_subscription failed` stops appearing | `aws logs filter-log-events --log-group-name /aws/lambda/careervp-gap-api-lambda-devx --filter-pattern 'get_subscription failed' --start-time <post-deploy-ms>` → empty | the journey number to move; J4 is a timeout, not a quota failure |
| capability table | synth fails loudly on an unknown env name | `ENVIRONMENT=nonsense cdk synth` → `ValueError` | any devx runtime change from this alone |
| artifact chain enabled | `list-executions` becomes non-empty | `aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-east-1:788159322332:stateMachine:careervp-artifact-chain-statemachine-devx --query 'length(executions)'` | `9 of 9` |

If the chain is enabled and J4 **passes**, say plainly that the 30s ceiling was
*bypassed*, not fixed — the synchronous path still breaks for anyone who reaches
it. Remember the chain has a second consumer at
`company_research_worker_handler.py:385`.

```bash
git add docs/evidence/prediction-2026-09-21.md
git commit -m "docs(evidence): prediction, recorded before merge"
```

**This commit must precede the push. That is the point of the phase.**

---

## Phase 3 — record, then push and merge

**3.1** Confirm the rollback target from 0.3 is written into your prediction
file or the PR body. It is the only cheap reversal you have: CloudFormation
performs **no automatic rollback after a successful update**, so reversal means
redeploying the prior template.

**3.2 Blast radius, mandatory.** Run and paste before acting:

```bash
scripts/ops/blast-radius.sh push tools/proof-harness
scripts/ops/blast-radius.sh pull_request db-redesign
scripts/ops/blast-radius.sh push db-redesign
```

Measured 2026-09-21 — re-verify, do not trust this table:

```
push tools/proof-harness  → 0 workflows. No AWS change.
PR → db-redesign          → 4 workflows, DEPLOY JOBS: none
                            (cdk-diff, pr-validation, infra-tests, refactoring-validation)
merge (= push db-redesign) → deploy-backend-dev, CareerVpCrudDevx,
                            CREATE+EXECUTE, gate environment=devx (real)
                            + Amplify db-redesign auto-build (no gate)
```

Paste the three-line statement:

```
Action:   <exactly what will run>
Triggers: <every workflow/deploy/stack/Amplify build it sets off>
Undo:     <the specific reversal, or "none — irreversible">
```

**3.3 Push the branch** (inert — 0 workflows):

```bash
git push origin tools/proof-harness
```

**3.4 Open a PR into `db-redesign`.** Do not fast-forward push directly.
`db-redesign-checks.yml` triggers only on `push: branches: [db-redesign]`, so
the PR is the **only** place `cdk-diff` shows you the CloudFormation delta
before it applies. A direct push skips the one control that would have caught
the 2026-09-20 nested-stack dissolution.

**3.5 Read `cdk-diff` properly**, not its summary line:

- resource count — nested devx synths ~261; un-nested ~491 against a 600
  ceiling. A jump toward 491 means the nesting flag was lost.
- any nested stack being removed. `make review` **cannot** detect this; it looks
  like an ordinary refactor. You must look yourself.
- any **replacement** of a stateful resource (table, bucket, user pool). The
  automated data-loss check was blind to this until `0c04fc9`, which is *in
  this merge*: `changeset_replacement_report.py` listed only
  `AWS::DynamoDB::Table` in `PROTECTED_TYPES` while every table here is an
  `AWS::DynamoDB::GlobalTable`, so its AUTO-FAIL could never fire — the same
  gap that let the 2026-09-20 incident through. Both types now match. **Until
  this merge lands, that gate has never once protected a deploy, so do not
  treat its silence on the PR as evidence.** Read the diff yourself.

**Stop and ask** on a nested-stack removal or any stateful replacement.

**3.6 Merge**, then wait for `deploy-backend-dev` to finish and confirm the new
`DeployedGitSha`.

---

## Phase 4 — validate, in this order

Configuration before behaviour. A behavioural test run against a half-applied
deploy produces a number that means nothing.

**4.1 Did the change do what it claims?**

```bash
for fn in $(aws lambda list-functions --region us-east-1 \
    --query 'Functions[?ends_with(FunctionName,`-devx`)].FunctionName' --output text); do
  printf '%-48s %s\n' "$fn" "$(aws lambda get-function-configuration --region us-east-1 \
    --function-name "$fn" --query 'Environment.Variables.ENVIRONMENT' --output text)"
done | grep -v ' devx$'
```

Any output is a Lambda the fix missed. Then check no env var value ends in a
foreign environment suffix (`-dev`, `-staging`, `-prod`).

**4.2 Cold-start canary — the failure this deploy will not report.**

If `resource_env()` now raises on a missing variable, a missed Lambda dies at
**cold start**, not at deploy. CloudFormation reports success and the stack
looks healthy; the breakage surfaces on first real use. Roughly five Lambdas do
not use `_build_shared_table_env()`, so 4.1 passing is not sufficient.

Invoke every `-devx` Lambda at least once, or drive the surfaces that reach
them, and confirm no `Runtime.ImportModuleError` or `RuntimeError: ENVIRONMENT
unset` in any log group. **This is the single most likely way this deploy
breaks something while appearing green.**

**4.3 Behaviour — run the journey.**

```bash
cd src/backend
BASE_URL=https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com make journey
```

**4.4 Diff the proofs.**

```bash
make compare KIND=journey
```

It returns one of four verdicts — use its vocabulary in your report:

- **CODE** — the commit changed; bisect between the two SHAs.
- **DEPLOYMENT** — same commit, different code running. A deploy shipped
  something unexpected, or did not ship.
- **CONFIGURATION** — same code and deploy, different stack/context.
- **EXTERNAL** — nothing observable changed but the result did. Suspect data, a
  third-party API, credentials, or flakiness.

**4.5 `make preflight` and `make state`** against the new stack. Commit all
Phase 4 proofs to `docs/evidence/`.

---

## Phase 5 — report

State, in this order:

1. **Predicted vs actual**, headline numbers side by side. If they differ, say
   so in the first sentence. Do not edit Phase 2's file — append a `## Result`
   section.
2. `make compare`'s verdict, and whether you agree with it.
3. Every check in 4.1/4.2 that did **not** pass, with the command output.
4. What you did **not** validate. J5–J9 have never executed against deployed
   code; if the journey still stops before them, say they remain unmeasured
   rather than implying they are fine.
5. Rollback status: whether the prior template is still the obvious reversal,
   and the SHA from 0.3.

---

## Ground rules

- Verify the environment; never infer it from a plan document — including this
  one. Every table here was measured on 2026-09-21 and may be stale.
- Stop and ask on `CREATE+EXECUTE` you did not expect, `NO ENVIRONMENT GATE`, or
  an environment with `0 rules`.
- Run `CLAUDE.md`'s mandatory checks for every path you touch before committing.
  **Do not use `scripts/git/safe_commit.sh`** — four `docs/handoff/*.md` files
  are the operator's and stay dirty.
- One concern per commit. Baseline, prediction and results are three commits.
- A repo grep is not an inventory, and a green deploy is not a working system.
