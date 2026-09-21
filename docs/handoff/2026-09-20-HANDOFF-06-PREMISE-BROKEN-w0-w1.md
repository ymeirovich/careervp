> ## ⚠️ SUPERSEDED — do not act on this document's recommendations
>
> **Superseded by `2026-09-21-HANDOFF-07-first-real-journey-measurement.md`.**
>
> This was written as a stop-and-hand-back report. It was never actually handed
> to a fresh session — the same session continued and resolved the blocker,
> which is itself a deviation from the chain's rule that a session may not
> certify its own work. Recorded rather than hidden.
>
> **Its central framing is wrong.** It treats "get the harness onto `main`" as
> the blocker and costs three options for doing so. It contains **zero mentions
> of `db-redesign` and zero of Amplify** — the two facts that resolved it.
> Measured afterwards: `ui-upgrade` ⊆ `db-redesign` ⊆ `tools/proof-harness`, the
> real pipeline is `db-redesign` → `environment: devx` → `make deploy-devx` →
> `CareerVpCrudDevx`, and four Amplify branches auto-build. `main` is not a
> deploy target for this project, so the harness never needed to go there and
> all three costed options answer a question that did not need asking.
>
> **What in here is still valid evidence:**
> - the `CareerVpCrudDev` incident accounting (~70 resources deleted, no data lost)
> - the p26 nested-stack measurement: 491 resources without the flag vs 261 with it
> - W0.2 shipped; W0.3 was already done and could not have worked as specified
> - the harness genuinely is absent from `main` — true, just not the relevant blocker
>
> **What is stale:** every recommendation, the three integration options, and the
> "Recommended Step 0 for handoff 07" section. Use handoff 07's Step 0 instead.

# HANDOFF 06 — PREMISE BROKEN: W0/W1 cannot run from `main`

**Status: stopped at the premise, per the production program's own rule** —
*"A premise in the handoff is false → Stop. Do not adapt the goal to fit the
discovered reality — that is how scope silently drifts. Write a premise-broken
report naming the false premise and the evidence, and hand back."*

Branch `tools/proof-harness`. Everything below is measured; commands included.

---

## What landed first — the thing five handoffs were blocked on

**PR #222 is merged.** The CI gate is on `main`.

```bash
git show origin/main:.github/workflows/pr-validation.yml | grep -c 'tests/regression'
# 0 before  ->  1 after
```

main tip `40de836`. Nine jobs: ruff · mypy · pytest across 8 test directories ·
Jest · Vitest · CDK synth · CV Tailoring Delete Observability · Deployed Parity
Gate · Evidence Integrity Gate. Trigger is `pull_request:
[opened, synchronize, reopened]` with **no branch filter**, so it fires on a PR
to any base.

**Deferred proof:** no PR has exercised it yet. The six PRs currently open
against `main` (`#144`, `#143`, `#100`, `#99`, `#98`, `#7`) predate the merge.
The next PR opened or synchronized against `main` is the proof. Verify with
`gh run list --branch <branch> --event pull_request`, never with `gh pr checks`
(which shows push-event rows and makes an empty gate look populated).

---

## W0 — two of three done, one was already done

| | Outcome |
|---|---|
| **W0.1** | Done — `23ff488`. Documented in `docs/HARNESS.md`, plus a blocker the plan did not know about (below). |
| **W0.2** | Done — `4dce22c`. `create-changeset` now passes `--context git_sha=$(GIT_STAMP)`. |
| **W0.3** | **Already done.** No action taken. |

**W0.3 was stale, and could not have worked as specified.** The plan says to
commit `docs/evidence/journey/20260914T081644-3fc5e54/` and the 09-14 handoff
because they are untracked. Measured: `git status --porcelain | grep '^??'`
returns **zero lines**; both paths are tracked. A prior handoff committed them.

More importantly, the stated purpose was unreachable either way. The plan says
committing them makes the current journey proof admissible. It does not:
`journey-20260914T100043-5022510.json` has `git_dirty: true` **recorded inside
it**. Committing files afterwards does not retroactively change a recorded
proof. Only a new journey run produces an admissible one.

**W0.2 proof** — by synth, not deploy:

```bash
ENVIRONMENT=devx npx cdk synth CareerVpCrudDevx \
  --context "git_sha=$(git rev-parse HEAD)" --context "p26_rehome_features=true"
# Outputs.DeployedGitSha.Value = "7b102bc05be5cd71d66158f46e57aa98d7b03691"
```

Without the context, `service_stack.py:180` emits the literal string
`"unstamped"`. Measured: none of the three live stacks exposes the output at
all.

| Stack | `DeployedGitSha` | `CrudFeatures` nested? | Last updated |
|---|---|---|---|
| `CareerVpCrudDev` | *(absent)* | no | 2026-07-30 |
| `CareerVpCrudDevx` | *(absent)* | **YES** | 2026-08-08 |
| `CareerVpCrudStaging` | *(absent)* | no | 2026-04-12 |

---

## THE BLOCKER — the harness does not exist on `main`

This is why W1 stops here.

```bash
for T in journey preflight state compare review create-changeset \
         execute-changeset deploy-devx; do
  echo "$T main=$(git show origin/main:src/backend/Makefile | grep -c "^$T:")"
done
# every one: main=0   (branch=1)
```

```bash
git cat-file -e origin/main:src/backend/scripts/preflight.py      # ABSENT
git cat-file -e origin/main:src/backend/scripts/review_change.py  # ABSENT
git cat-file -e origin/main:docs/HARNESS.md                       # ABSENT
git cat-file -e origin/main:src/frontend/tests/e2e/journey.spec.ts # ABSENT
```

**Zero of the eight harness targets, and none of the four key files, are on
`main`.** `HARNESS.md` — the document W0.1 edits — does not exist there.
`journey.spec.ts` — the project's definition of done — does not exist there.

### Two program-plan statements that are true only of the branch

1. **"Use `deploy.yml`'s `workflow_dispatch` devx path (`deploy.yml:279`)."**
   Measured on `main`: `git show origin/main:.github/workflows/deploy.yml |
   grep -c CareerVpCrudDevx` → **0**. There is no devx path on main. Main's
   `deploy.yml` hardcodes `STACK_NAME: 'CareerVpCrudDev'` (line 30) and runs
   `make deploy` — create **and** execute, the ungated path P-28 exists to
   eliminate.

2. **"W0 is three small commits."** Two of them modify files that do not exist
   on `main`, so neither can be PR'd there on its own. A cherry-pick of
   `4dce22c` onto `origin/main` conflicts immediately: main's
   `src/backend/Makefile` has no `create-changeset` target and no `GIT_STAMP`
   variable to stamp with.

### What this means

**Step 5's integration decision is not deferrable work — it is a hard
prerequisite for W0/W1.** You cannot run a gated deploy from `main`, because
`main` has no `create-changeset` target, no devx path, and no way to measure
the result afterwards. The deploy track runs from `tools/proof-harness` or it
does not run.

---

## A second blocker, found while verifying W0.1

**The gated devx changeset path is destructive today**, independent of the
above.

`deploy.yml:378` (branch) calls `make create-changeset`, which does **not**
pass `--context p26_rehome_features=true`. `make deploy-devx` does
(`Makefile:137`). That context decides whether CRUD features nest under
`CrudFeaturesNestedStack` or sit on the parent (`api_construct.py:93`).
Synthesized both ways:

| synth of `CareerVpCrudDevx` | resources on the parent stack |
|---|---|
| without the flag — what the gated path does | **491** |
| with the flag — what `deploy-devx` does | **261** |

234 resources differ: 29 Lambda functions, 30 log groups, 28 event-invoke
configs, 28 permissions, 17 SQS queues, 17 alarms, 17 CodeDeploy deployment
groups, 17 Lambda versions.

The live devx stack **has** the nested stack deployed
(`CrudFeaturesNestedStackResource4518FF9C`, `UPDATE_COMPLETE`), so a changeset
created through the gated path today would dissolve it and recreate its
contents on the parent.

Two qualifiers, both measured, both important:

- **No stateful resource diverges.** Zero DynamoDB tables, S3 buckets or
  Cognito user pools appear on one side only. This is compute and messaging
  churn, **not data loss**.
- **`make review` cannot catch it.** The replacement report rules on
  `Replacement: True` for stateful types; a nested-stack dissolution presents
  as ordinary adds and removes of Lambdas and queues — indistinguishable from a
  legitimate refactor. Separately, and already known from sweep-00:
  `scripts/ci/changeset_replacement_report.py` and `preflight.py:366` query
  `AWS::DynamoDB::Table` while every table here is `AWS::DynamoDB::GlobalTable`,
  so the DynamoDB auto-fail cannot fire at all.

`Dev` and `Staging` are deployed **without** the nested stack, so the gated
path is correct for them as-is. The context must therefore be **conditional on
the target environment** — adding it unconditionally makes the Dev changeset
destructive in the other direction.

---

## Options — costed, not picked (`HARNESS.md` rule 5)

### For the integration blocker

| | Cost | Buys | Loses |
|---|---|---|---|
| **A. Merge the harness to main first** | The Step 5 decision, incl. what happens to the 23.3 MB IAM dump | W0/W1 become possible from main; the gate guards the harness | Puts the branch's 772-file diff — and the IAM dump — on main permanently |
| **B. Run the deploy track from `tools/proof-harness`** | ~0 | Unblocks W1 today; harness and deploy path are co-located | The deployed code is not main's; "is my change live" answers about a branch |
| **C. Port only the harness** (`Makefile` targets, `preflight.py`, `review_change.py`, `HARNESS.md`, `journey.spec.ts`) to main | 1 focused PR, gated by the new CI gate | main gets the measurement apparatus without the 93%-docs diff | A second integration seam to maintain until the rest lands |

### For the devx p26 blocker

| | Cost | Buys | Loses |
|---|---|---|---|
| **D. Make the context conditional on `ENVIRONMENT`** in `create-changeset` | ~3 lines + a synth diff to prove it | Gated devx path becomes non-destructive | Another environment-conditional branch in the Makefile |
| **E. Deploy devx via `make deploy-devx`** | 0 | Matches what devx already has | Violates P-28 — create+execute with no human gate between |
| **F. Accept the churn** | 0 | Converges devx onto the un-nested layout | Recreates 230 compute resources; downtime; `make review` will not flag it |

---

## Recommended Step 0 for handoff 07

Re-run, and compare against the values above:

```bash
git show origin/main:.github/workflows/pr-validation.yml | grep -c 'tests/regression'   # 1
git show origin/main:src/backend/Makefile | grep -c "^create-changeset:"                # 0
git show origin/main:.github/workflows/deploy.yml | grep -c CareerVpCrudDevx            # 0
gh run list --branch <any-pr-branch> --event pull_request                               # gate present?
```

If the first is not `1`, someone reverted the gate — say so before doing
anything else.

---

## Housekeeping

- Local branch `ci/w0-deploy-prereqs` was created for a cherry-pick experiment
  that conflicted and was aborted. Its worktree is removed; deleting the branch
  was denied by the sandbox. It is local-only and never pushed —
  `git branch -D ci/w0-deploy-prereqs` when convenient.
- `ci/gate-on-main` should be kept until you are satisfied `40de836` is good.
- Four `docs/handoff/*.md` files remain dirty from a prior session and are still
  the operator's to handle.
