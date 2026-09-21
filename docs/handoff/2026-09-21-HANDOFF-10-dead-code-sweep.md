# HANDOFF 10 — the non-environment dead code sweep

**Model: Opus 5, high effort.** Fresh session at the repo root, on
`tools/proof-harness`.

Runs **independently of HANDOFF 09** — 09 owns environment coupling and the
fix/test work in `infra/careervp/` and `src/backend/careervp/dal/`. This one is
read-and-inventory first. **Do not delete anything in your first pass.**

This is W2/W3/W4.3 of `PRODUCTION-PROGRAM.md`, which specified `dead_api.py`,
`dead_code.py` and `table_map.py`. Handoff 08 confirmed none of them exist.

---

## Read this first — two corrections to earlier sessions

**FVS is not dead.** `check_anti_ai_patterns` is imported directly by
`logic/cover_letter.py:13`, `logic/cv_tailoring.py:16` and
`logic/vpr_generator.py:25`, and runs unconditionally. It implements the
anti-AI-detection rules in `CLAUDE.md`. `models/fvs.py`, `models/fvs_models.py`
and `logic/fvs_validator.py` are all live.

What is dead is only the **`FVS_ENABLED` environment variable**: written once,
in a stack nothing imports, and read by no code anywhere in the repo. Deleting
the variable changes nothing. **Wiring it up would be the real mistake** — it
would add a switch capable of turning off a rule the product is supposed to
always apply. Verify before acting:

```bash
grep -rn 'FVS_ENABLED' src/ infra/ | grep -v cdk.out | grep -v '\.build'
# expect exactly one hit: infrastructure/stacks/cv_tailoring_stack.py:68
grep -rn 'check_anti_ai_patterns' src/backend/careervp/logic/ | wc -l
# expect > 1 — FVS is called
```

**`.build/` and `cdk.out/` will drown you.** Every dead-code grep in this repo
returns dozens of hits from `src/backend/.build/lambdas/`,
`src/backend/cdk.out/asset.*/` and `infra/cdk.out/asset.*/`, which are *copies*
of source, not callers. Every command below excludes them. A sweep that does
not exclude them will report everything as "used" and find nothing.

---

## Step 0 — verify the known findings

| # | Command | Expected |
|---|---|---|
| 0.1 | `grep -rn 'CVTailoringStack' src/backend infra --include='*.py' \| grep -vE '\.build/\|cdk\.out/' \| grep -v 'stacks/cv_tailoring_stack.py:'` | **empty** — nothing imports it |
| 0.2 | `ls src/backend/careervp/infrastructure/stacks/` | `__init__.py`, `cv_tailoring_stack.py` only |
| 0.3 | `git log --oneline --follow -- src/backend/careervp/infrastructure/stacks/cv_tailoring_stack.py \| tail -2` | `5919449` / `e179ba4` — "Complete CV Tailoring feature with FVS validation" |
| 0.4 | `grep -rn "region_name='us-east-1'" src/backend/careervp/handlers/auth_handler.py` | line 249 — hardcoded, no env fallback |

---

## Step 1 — the confirmed finding

`src/backend/careervp/infrastructure/stacks/cv_tailoring_stack.py` is a **CDK
stack living inside the Lambda runtime tree**.

- Nothing imports it (0.1).
- It predates the move of CV tailoring into `infra/careervp/api_construct.py`
  (0.3) — it is the original per-feature stack, left behind after the feature
  was rehomed.
- Because it sits under `src/backend/careervp/`, it is **packaged into every
  Lambda deployment artifact** — it appears in `.build/lambdas/` and in a dozen
  `cdk.out/asset.*/` bundles. Dead infrastructure code is shipping inside the
  runtime.

Worth resolving, but **confirm the packaging claim before deleting**: check
whether the Lambda build includes `careervp/infrastructure/**` by inspecting
`src/backend/Makefile`'s build target and the `BUILD_FOLDER` contents. If it is
excluded, this is untidy rather than shipped, and the urgency drops.

Deletion is not obviously safe: an orphaned CDK stack may still correspond to a
**deployed** CloudFormation stack. Check first:

```bash
aws cloudformation list-stacks --region us-east-1 \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  --query 'StackSummaries[?contains(StackName,`Tailor`)||contains(StackName,`CvTailoring`)].StackName'
```

Empty output means the file is orphaned in code only and deleting it is a
source-tree change. Non-empty means there is live infrastructure whose
definition you are about to remove — **stop and ask**.

---

## Step 2 — the sweep, by category

Each category gets a script in `src/backend/scripts/`, an inventory written to
`docs/` and **no deletions in the same commit as the tool**. One concern per
commit; the tool and its findings are two concerns.

### 2.1 Orphaned modules — `dead_code.py`

Every `.py` under `src/backend/careervp/` and `infra/careervp/` that no other
module imports, excluding entry points (Lambda handlers named in CDK
`handler=` strings, `app.py`, `conftest.py`).

The trap: Lambda handlers are referenced by **string** in CDK
(`handler="careervp.handlers.job_handler.lambda_handler"`), never by import. A
naive import-graph walk reports all 31 handlers as dead. Seed the reachable set
from those strings first.

### 2.2 Dead API routes — `dead_api.py`

Cross-check three sets:

1. routes declared in `api_construct.py` (the `("/path", "METHOD", func)` tuples
   around line 3461),
2. routes the backend handlers actually dispatch,
3. routes the frontend calls (`src/frontend/api/methods.ts`).

Report both directions: a route wired in CDK that no handler serves, and a
handler branch no route reaches. `/jobs` is explicitly excluded from one
registry (`api_construct.py:3435`) because several Lambdas own sub-paths — do
not report that as a defect.

### 2.3 Unreachable branches

Beyond the environment literals (HANDOFF 09 Step 3.3 adds a static guard for
those), look for:

- comparisons against literals that no longer occur — the same shape as
  `environment == "dev"`, but for status strings, module ids, plan names;
- state-machine transitions declared in `dal/application_repository.py:37-39`
  with no code that performs them;
- `except Exception: pass` blocks that silently swallow a branch into
  non-existence (there is one at `logic/auth_service.py:~230`).

### 2.4 Flags — covered by HANDOFF 09

The producer/consumer contract test in HANDOFF 09 Step 3.2 catches both
"written but never read" (`FVS_ENABLED`) and "read but never written"
(`ARTIFACT_CHAIN_ENABLED` in devx). **Do not build a second tool for this** —
coordinate, or you will produce a conflicting inventory.

### 2.5 Data — `table_map.py`

Every DynamoDB table and every `sk` prefix the code writes, against what it
reads. Note for whoever builds it: `preflight.py:366` and
`scripts/ci/changeset_replacement_report.py` query `AWS::DynamoDB::Table` while
every table is `AWS::DynamoDB::GlobalTable`, so their data-loss auto-fail can
never trigger. That is a live defect, not dead code, and it is why the
2026-09-20 Dev incident was not caught. Fix it while you are in there.

### 2.6 Frontend

`src/frontend/app/**` routes with no link or `router.push` reaching them, and
components no page imports. Handoff 08 recorded 308 e2e test blocks of which
~1187 are `TODO`-bodied with 0 `test.fixme()` — a test that asserts nothing is
dead code that reports green, which `journey.spec.ts`'s header calls out as the
failure mode that already cost this project months.

---

## Step 3 — what to do with the inventory

Produce `docs/DEAD-CODE.md`: one row per finding, with **evidence**, a
confidence level, and the command that proves it. Then bring it back before
deleting anything.

Ordering rule for removals, safest first:

1. unread environment variables (no behaviour change — `FVS_ENABLED`),
2. orphaned source files with no deployed counterpart,
3. unreferenced routes,
4. unreachable branches,
5. data — **last, and never without the operator.**

**A repo grep is not an inventory.** That line is in `CLAUDE.md` because
deactivating an "unused" IAM key by grep evidence broke the operator's own
access; the secret lived outside the repo. The same applies to every category
here: absence of a reference in this repository is not proof of absence of a
caller.

---

## Ground rules

- `scripts/ops/blast-radius.sh <event> <branch>` before any merge, deploy,
  deletion or credential change; paste Action / Triggers / Undo before acting.
- **A change under `src/frontend/**`, `src/backend/**` or `infra/**` triggers a
  full `CareerVpCrudDevx` deploy on push to `db-redesign`**, regardless of
  whether it is only a deleted comment. See `CLAUDE.md` → "What actually
  fires". Most of this handoff's output is `docs/**` and `scripts/**`, which
  fires nothing — keep it that way until the deletions are approved.
- Run `CLAUDE.md`'s mandatory checks for every path you touch before committing.
  **Do not use `scripts/git/safe_commit.sh`** — four `docs/handoff/*.md` files
  are the operator's and stay dirty.
- One concern per commit. The tool and its findings are two concerns.
- Deleting code is irreversible in effect even when reversible in git, because
  nobody re-reads a deletion. Inventory first, delete second, in a separate
  reviewable commit.
