# The harness

Five commands. They answer "where am I", "did I move", and "is this deploy safe".
Nothing here describes the project — everything here measures it.

```
make preflight    are the facts I am about to rely on true?
make journey      how far does a customer get?   (N of 9)
make state        show both on one page
make compare      what changed between the last two proofs?
make review       classify a change set before touching dev/staging/prod
```

Run all of them from `src/backend/`.

## The loop

```
preflight   →  are my facts true?
journey     →  how far does a customer get?   (N of 9)
one change  →  aimed at step N+1
journey     →  did N go up?
                 up   → commit
                 down → REVERT FIRST, investigate second
                 flat → the change didn't do what you predicted; read the failing step
```

You are done when N = 9 on a stack that can be rebuilt from scratch.

## Proofs

Every tool writes a JSON *proof* to `docs/evidence/`. A proof records what was
observed, when, and **which exact code** — `git_sha`, `git_dirty`, and
`deployed_sha` (what the stack says it is running, via the `DeployedGitSha`
stack output).

Without those fields a result cannot be reproduced, compared, or bisected
against. With them:

```
make compare KIND=journey        # subtract the last two proofs
```

...tells you whether a regression is CODE, DEPLOYMENT, CONFIGURATION, or
EXTERNAL — which decides what investigation is worth starting.

**`git_dirty: true` marks a proof as non-reproducible.** It describes code that
exists on one laptop and is not in git; you cannot check it out and cannot
bisect from it. Run anything you like while dirty — the restriction is on
*recording a claim*, not on working. `git commit -am wip` costs five seconds.

## Three results, never two

`preflight` reports PASS, FAIL, or **UNKNOWN**. UNKNOWN means the fact could not
be checked. It is not PASS. Reading "I could not check whether access logging is
on" as "access logging is on" is the specific mistake that cost this project
months, and the third state exists to make that impossible.

## The change-set review

For dev, staging, or prod — anywhere with data:

```
make create-changeset            # creates, does not execute
make review STACK=CareerVpCrudDev
```

Every change is ruled GO, READ, or STOP. The only AWS knowledge required is
which resource types hold data; that list is four entries long and lives at the
top of `scripts/review_change.py`.

**STOP means applying this destroys data.** Usually `Replacement: True` on a
DynamoDB table, S3 bucket, or Cognito user pool: CloudFormation deletes and
recreates it, and the application is then pointed at an empty one.

## Deploy and measure must name the same stack

`make journey` and `make preflight` measure `HARNESS_STACK ?= CareerVpCrudDevx`
(`src/backend/Makefile:29`). Merging to `main` auto-runs the on-merge job in
`.github/workflows/deploy.yml`, which hardcodes `STACK_NAME: 'CareerVpCrudDev'`
(line 37). **Deploying via the on-merge job and then running `make journey`
deploys Dev and measures Devx.** N does not move, and the session then debugs a
fix that was never deployed.

Use the gated devx path deliberately: `deploy.yml`'s `workflow_dispatch` maps
`environment: devx -> CareerVpCrudDevx` (line 279). Do not rely on the on-merge
job to put code where the harness is looking.

### Before using that path for devx, read this

**Measured 2026-09-20 — the gated changeset path is NOT yet safe for devx.**

`deploy.yml:378` calls `make create-changeset`, which does not pass
`--context p26_rehome_features=true`. `make deploy-devx` does
(`Makefile:137`). That context decides whether the CRUD features are nested
under `CrudFeaturesNestedStack` or sit directly on the parent
(`infra/careervp/api_construct.py:93`), so the two paths synthesize materially
different templates for the same stack name:

| synth of `CareerVpCrudDevx` | resources on the parent stack |
|---|---|
| without the flag (what the gated path does) | **491** |
| with the flag (what `deploy-devx` does)     | **261** |

234 resources differ: 29 Lambda functions, 30 log groups, 28 event-invoke
configs, 17 SQS queues, 17 alarms, 17 CodeDeploy deployment groups.

The live `CareerVpCrudDevx` stack **has** `CrudFeaturesNestedStack` deployed
(`describe-stack-resources` -> `...CrudFeaturesNestedStackResource4518FF9C`,
UPDATE_COMPLETE). So a changeset created through the gated path today would
dissolve that nested stack and recreate its contents on the parent.

Two things make this worth stating loudly rather than filing:

- **No stateful resource diverges.** Zero DynamoDB tables, S3 buckets or
  Cognito user pools appear on one side only. This is compute and messaging
  churn, not data loss.
- **`make review` cannot catch it.** The replacement report rules on
  `Replacement: True` for stateful types. A nested-stack dissolution shows up
  as ordinary adds and removes of Lambdas and queues, which is exactly what a
  legitimate refactor looks like. Separately,
  `scripts/ci/changeset_replacement_report.py` and `preflight.py:366` query
  `AWS::DynamoDB::Table` while every table in this project is
  `AWS::DynamoDB::GlobalTable`, so the DynamoDB auto-fail cannot fire at all.

`CareerVpCrudDev` and `CareerVpCrudStaging` are deployed **without** the nested
stack, so the gated path is correct for them as it stands. The context
therefore has to be conditional on the target environment; adding it
unconditionally would make the Dev changeset destructive in the other
direction.

### `DeployedGitSha`

`create-changeset` now passes `--context git_sha=$(GIT_STAMP)`. Without it
`service_stack.py:180` falls back to the literal string `"unstamped"`.
Measured 2026-09-20: none of `CareerVpCrudDev`, `CareerVpCrudDevx` or
`CareerVpCrudStaging` exposes a `DeployedGitSha` output at all, which is the
standing UNKNOWN in preflight. Setting an output value replaces nothing.

## The journey

`src/frontend/tests/e2e/journey.spec.ts` — nine steps in the order a paying
customer performs them. It is the definition of done, and the only artifact in
this repo that can *disprove* a claim of progress.

Two rules for editing it:

1. **Never add a `TODO`.** A step either asserts something real or it does not
   exist. The 25 older specs in that directory contain 282 test blocks and 113
   live assertions — the rest have empty `TODO` bodies, so they pass while
   proving nothing. Do not add to that pile.

   This doc previously said the rest were "commented out". Measured 2026-09-20:
   only **2** commented-out assertions exist in the whole directory, against
   1187 `TODO` occurrences. The distinction matters because it changes the
   remediation — there is nothing to uncomment, the tests were never written.
2. **Never soften a step to make it pass.** Lowering the bar moves the number
   without moving the product, which is the only way this instrument can lie.

## Rules for the AI, and for you

Paste this at the top of any investigation session:

```
1. If a command exists that answers the question, run it. Do not tell me what
   you think first.
2. Label every claim: OBSERVATION (command + output), INFERENCE, or OPINION.
3. If I assert a fact, verify it before relying on it. Report if it is wrong.
4. If my prompt names a suspect or a likely cause, flag it as contamination
   before you start.
5. Never recommend on a judgment call. Cost the options; I decide.
```

And before acting on any claim about AWS: *if this is false, what have I just
done that I cannot undo?* If the answer is not "nothing", get the command first.
