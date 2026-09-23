# HANDOFF 14 — land two PRs, fix the gap contract, close J9

**Model: Opus 5, high effort.** Handoff 13 took the journey from 7/9 to **8/9**
and repaired the four CI defects. What remains is smaller but not mechanical:
two PRs whose blast radii differ sharply, a live data-contract defect that J8's
green tick actively conceals, and J9 — which has now been measured exactly once
and failed for a reason that is *not* the product.

Fresh session at the repo root, on `tools/proof-harness`.

---

## The one-sentence version

**J8 passes and the CI cluster is fixed; what is left is to land PR #232
(inert) and PR #230 (fires a gated deploy), repair the gap-response contract
that silently strips the candidate's own answers out of interview prep, and fix
the J9 selector so the export path gets measured for the first time.**

---

## Step 0 — verify before trusting this document

| # | Command | Expected |
|---|---|---|
| 0.1 | `aws cloudformation describe-stacks --stack-name CareerVpCrudDevx --region us-east-1 --query "Stacks[0].Outputs[?OutputKey=='DeployedGitSha'].OutputValue" --output text` | `4385fc98bc4bce25da930dff9c33824dd0aacfce-dirty` |
| 0.2 | `git log -1 --oneline origin/db-redesign` | `4385fc9 Merge pull request #229 …` |
| 0.3 | `git log -1 --oneline origin/tools/proof-harness` | `4d0c906 docs(evidence): J8 passes, J9 measured for the first time` or later |
| 0.4 | `gh pr view 230 --json state -q .state` | `OPEN` — the CVE bumps |
| 0.5 | `gh pr view 232 --json state -q .state` | `OPEN` — the spec-check repair |
| 0.6 | `python3 -c "import json;d=json.load(open('docs/evidence/journey-20260922T203146-caa38e4.json'));print(d['journey_reached'], d['steps']['J9'][:40])"` | `8 fail: TimeoutError: page.waitForEvent: T` |
| 0.7 | `aws dynamodb get-item --region us-east-1 --table-name careervp-users-table-devx --key '{"pk":{"S":"USER#848834a8-4061-703d-419c-0294d4e88d66"},"sk":{"S":"TRIAL"}}' --query 'Item.application_count.N' --output text` | `1` — **2 runs left of 3** |
| 0.8 | `python3 -c "import json;print(json.load(open('.claude/settings.local.json'))['autoMode']['allow'])"` | `['$defaults']` — the temporary rule is **gone**; see the hazard below |

If 0.1–0.3 diverge, someone has deployed or moved a branch since this was
written — re-derive before trusting anything below.

---

## Part 0 — read this before you plan anything

**You cannot reset the trial budget without asking.** Handoff 13's temporary
`autoMode.allow` rule was removed when J9 was measured, exactly as its consent
was scoped. `make journey` consumes one of three credits and **one is already
spent**. You have two runs. The reset command lives in HANDOFF-11 §0.1; running
it needs the operator to re-grant permission, time-boxed again. **Ask for that
grant at the start, not at the moment you need it** — discovering the block
mid-measurement wastes a credit.

**Fixing the J9 test triggers a CloudFormation deploy.** `journey.spec.ts` lives
at `src/frontend/tests/e2e/journey.spec.ts`, which matches
`db-redesign-checks.yml`'s `src/frontend/**` path filter. A one-line selector
change to a test file fires `deploy-backend-dev` → `CareerVpCrudDevx` →
`CREATE+EXECUTE`. This is the trap `CLAUDE.md` documents verbatim: *"the trigger
does not read the diff."* Plan for the gate; do not be surprised by it.

---

## Part 1 — the two open PRs

### What is actually in them

**PR #232 — `fix/ci-infra-spec-consistency` (head `c3dc58a`)**

One file, `.github/workflows/refactoring-validation.yml` (+49/−8). Three fixes:

1. The DynamoDB check opened `infra/careervp/dynamodb_stack.py`, deleted in the
   refactor → `FileNotFoundError`. Now scans `infra/careervp/**/*.py`.
2. The S3 check opened `infra/careervp/s3_stack.py`, also deleted. It had never
   been *seen* to fail, because check 1 aborted the job first.
3. The workflow is added to its own `pull_request` path filter (matching
   `infra-tests.yml`'s existing convention), so a workflow-only PR runs the jobs
   it edits. Without this, #225's `CDK Validation` fix went unproven.

It also teaches the S3 check that `GENERATED_BUCKET_NAME` is **planned, not
missing**, by reading `deployment_spec.yaml`'s `planned_refactor_contract`
(`status: PLANNED_NOT_WIRED_IN_SERVICE_STACK`) rather than duplicating the fact.
**Nothing was deleted from any spec.** See the hazard note below.

Current state: `Infra Spec Consistency`, `CDK Validation`, `Spec Validation`,
`Phase Spec Consistency` all **pass**. Only `python-security` is red, and #230
fixes that.

**PR #230 — `fix/deps-cve-bumps` (head `e0afdb5`)**

Three files, all under `src/backend/`: `pyproject.toml` (+3/−3), `uv.lock`,
`lambda_requirements.txt`. Clears all 23 pip-audit CVEs across four packages:

| Package | From → To | Findings | Direct? |
|---|---|---:|---|
| `cryptography` | 46.0.5 → 50.0.1 | 11 | yes |
| `pypdf` | 6.14.2 → 6.19.0 | 8 | yes |
| `anyio` | 4.12.1 → 4.15.1 | 2 | **transitive** (anthropic/httpx) |
| `soupsieve` | 2.8.4 → 2.9.2 | 2 | yes |

`anyio` had to be upgraded explicitly; refreshing the lock alone left it at
4.12.1 because nothing in the tree required newer.

**The risk here is `cryptography`, not the count.** It crosses four major
versions and `auth_service.py` imports `cryptography.hazmat` directly for RSA
JWT keys. Verified before opening: `mypy --strict` clean over 138 files, 1440
unit tests pass, `pip-audit` reports no known vulnerabilities. That verification
was on the pre-#229 base — **re-run it after rebasing.**

### Blast radius — they are not the same

`db-redesign-checks.yml` fires only when changed paths match `src/frontend/**`,
`src/backend/**`, or `infra/**`.

| PR | Paths touched | Deploy job | Gate |
|---|---|---|---|
| **#232** | `.github/workflows/**` | **none — no match** | n/a |
| **#230** | `src/backend/**` | **`deploy-backend-dev` → `CareerVpCrudDevx`, `CREATE+EXECUTE`** | `environment: devx`, 1 reviewer — real, verified live |

Both also rebuild the Amplify `db-redesign` branch, which auto-builds on any
push and carries no gate. For #232 that is a rebuild of byte-identical frontend
source.

**Run `scripts/ops/blast-radius.sh merge db-redesign` and paste
Action/Triggers/Undo before either merge anyway.** The table above is a claim;
the tool is the measurement. `CLAUDE.md` requires you to stop and ask on
`CREATE+EXECUTE` — that applies to #230.

### Order

Land **#232 first**. It is inert, and it turns `Infra Spec Consistency` green so
that #230's merge is judged against a CI baseline with exactly one known red
(`python-security`, which #230 itself clears). Then rebase #230, re-run the
backend checks, blast-radius, ask, merge, and validate the deploy the way
handoff 13 §2.7 did — baseline the 22 stack outputs **before** the merge and
diff after; only `DeployedGitSha` should move.

---

## Part 2 — the third defect: interview prep still has no gap answers

**J8 is green and the artifact is still wrong.** This is the important item in
this handoff, and the green tick is what makes it easy to skip.

### What happens

Handoff 13's IAM grant fixed the CV half: the worker now reads
`careervp-cvs-table-devx` successfully. The gap half still fails, for an
entirely different reason — a data-contract mismatch, not permissions:

```
DynamoDB DAL operation failed  table=careervp-gap-responses-table-devx
operation=get_gap_responses  error_code=ValidationError
  2 validation errors for GapResponse
    question  Field required
    answer    Field required
```

`dynamo_dal_handler.py:1075` does `GapResponse.model_validate(item)`.

| Side | Location | Shape |
|---|---|---|
| **Writer** | `gap_handler.py:868` (`_normalize_submitted_response_entry`) | `{'question_id', 'response'}` + optional `quantifiable_data`, `tags` |
| **Reader** | `models/job.py:71` `GapResponse` | requires `question_id`, **`question`**, **`answer`**; `destination` defaults |

`question` is never written at all. `answer` is written under the name
`response`. The handler catches the failure, logs
`"Interview prep context gap responses lookup empty"` at **INFO**, and generates
anyway — so interview prep is produced from the CV plus the VPR, with the
candidate's own gap answers silently absent. The step passes; the artifact is
built from partial context.

### Before you pick a fix

**`GapResponse` is shared.** Consumers: `logic/cover_letter.py:55`,
`logic/prompts/cover_letter_prompt.py:37,83`, `models/vpr.py:611`, and the DAL.
Cover letter and VPR accept `list[GapResponse | dict[str, Any]]` — they tolerate
raw dicts, which is plausibly why J6/J7 pass. **Establish what each consumer
actually receives today before changing the model**; a field rename that fixes
interview prep could quietly change cover-letter or VPR prompt content.

Options, in rough order of preference — none is obviously right, so justify the
choice:

1. **Map at the DAL boundary.** Translate the stored shape into `GapResponse`
   inside `get_gap_responses` (`response` → `answer`, and source `question`
   from the gap-questions record). Narrowest blast radius; leaves the model and
   every other consumer untouched. Requires the question text to be
   retrievable — verify it is.
2. **Widen the model.** Make `question` optional and accept `response` as an
   alias for `answer` (pydantic `AliasChoices`). Smaller change, but relaxes a
   contract three other call sites rely on.
3. **Fix the writer.** Persist the full shape. Correct long-term, but it does
   nothing for records already stored — including the one this journey wrote.

**Whatever you choose, the INFO-level swallow is its own defect.** A context
resolution that fails should not be indistinguishable from one that legitimately
found nothing. At minimum it should be WARNING with the error attached, and the
generated artifact should record that it was built without gap answers.

### Proving it

A green J8 does not prove this. The regression test must assert the *content*:
that a stored `{question_id, response}` record reaches the generation prompt.
Verify end-to-end by reading the worker log for the run and confirming the gap
lookup no longer reports empty.

---

## Part 3 — J9

### What the first-ever measurement found

```
TimeoutError: page.waitForEvent: Timeout 240000ms exceeded while waiting for event "download"
```

`journey.spec.ts:523` clicks
`getByRole("button", {name:/export|download|pdf|docx/i}).first()`. In
`ExportDropdown.tsx` that matches the **"Export" toggle** (line 80), whose only
behaviour is `setOpen(o => !o)`. The real download buttons are at line 92,
rendered *inside* the menu that toggle opens. The test opened the dropdown and
waited four minutes for a download that needed a second click.

Corroboration: **zero invocations** of `careervp-export-lambda-devx` during the
run. The click never reached the backend. The captured screenshot
(`docs/evidence/journey/20260922T203146-caa38e4/J9-export-FAILED-dropdown-open.png`)
shows the menu open with both items unclicked.

**So J9's export path is unmeasured, not broken.** Export is fully implemented —
`handleExport` calls `api.exportArtifact`, fetches the bytes, and triggers a
same-origin blob download. `'Export is coming soon!'` renders only on a `501`.
The `title="Export coming soon"` attribute on the menu items is a stale tooltip
and should not be read as the feature being stubbed.

### What to do

Click the toggle, then the menu item. `data-testid="export-dropdown"` (line 79)
is a stable anchor for scoping. Open the download-event listener **before** the
click that actually triggers it, not before the toggle.

Then run it and find out what the backend does. **Treat a green J9 as
unproven until you see it.** Every step from J5 onward has concealed a distinct
defect that only appeared once the step before it started passing, and this step
has never once reached the export Lambda. Plan for it to surface something.

The existing assertions are good and should survive: a download path that
exists, and a file over 1000 bytes — a zero-byte download is a
successful-looking failure.

**Remember Part 0: editing this file triggers a gated deploy.** Batch it with
the Part 2 backend fix so the two share one deploy and one trial credit rather
than two of each.

---

## Part 4 — if an assumption is false

### 4.1 If #230 no longer passes after rebase
The `cryptography` jump is the suspect. Diagnose before layering fixes; report
rather than pinning back to a vulnerable floor without saying so.

### 4.2 If the gap-contract fix breaks cover letter or VPR
Expected if you widened or renamed on the shared model. Fall back to option 1
(map at the DAL boundary) and leave `GapResponse` alone.

### 4.3 If J9 still fails after the selector fix
Read `careervp-export-lambda-devx`'s logs first. A non-zero invocation count
moves this from a frontend-wiring problem to a backend one; zero invocations
means the selector is still wrong. A `501` means export genuinely is not
implemented server-side and the tooltip was right.

### 4.4 If the trial budget runs out
Stop. Do not keep re-running. `403 trial_expired` misread as a regression from
your own change is the failure mode HANDOFF-11 warned about.

---

## What's next, after this handoff

Ordered by what unblocks the most:

1. **Close J9 honestly** — a 9/9 journey where every step's artifact is correct,
   not merely green. That is the first end-to-end proof this product works.
2. **The `-dirty` GIT_STAMP defect** — open since handoff 08. `preflight` fails
   `deployed commit is known` on every single run, and the journey stamps
   `DIRTY TREE — this proof is not reproducible` on every proof it writes. Nine
   of nine means little while no proof is reproducible. This is now the oldest
   unaddressed item and it undermines the entire evidence harness.
3. **`GENERATED_BUCKET_NAME` / the S3 spec** — not drift (phase-6 planning,
   correctly recorded; see #232's comments). But `s3_spec.yaml` declares 2
   buckets while infra builds 6, so the repaired check validates one direction
   against an incomplete spec and would not notice four of the six disappearing.
   Decide whether the spec should be completed or explicitly scoped.
4. **`Security Audit` on `db-redesign`** — should go green once #230 lands.
   Confirm it, rather than assuming.

---

## Carried forward — operational hazards

- **`deployed commit is known` FAILs preflight on every run** (the `-dirty`
  GIT_STAMP issue). Expect 8 pass / 1 fail. Do not let it train you to skim.
- **The `devx` reviewer gate needs a human.** An agent session cannot approve
  it; the auto-mode classifier blocks both the approval call and any attempt to
  self-grant it. Ask the operator and wait.
- **Amplify `db-redesign` auto-builds with no gate** on every push, regardless
  of path filter. The `devx` gate covers the backend job only.
- **Two trial credits remain**, and resetting them now requires a fresh,
  time-boxed permission grant from the operator (Part 0).

## Ground rules

- `scripts/ops/blast-radius.sh <event> <branch>` before any merge, deploy,
  deletion or credential change; paste Action/Triggers/Undo **before** acting.
- Stop and ask on a `CREATE+EXECUTE` you did not expect, `NO ENVIRONMENT GATE`,
  or an environment with `0 rules`.
- Verify the environment; never infer it from a plan document — **including
  this one.**
- One concern per commit. Every fix gets a regression test that fails before and
  passes after — and **run it the way CI runs it.** Handoff 13 shipped a shell
  quoting bug in a `python -c "…"` workflow step because the logic was validated
  in isolation; the defect lived at the shell boundary and only executing the
  step exposed it.
- A repo grep is not an inventory, a green deploy is not a working system, a
  green step is not a correct artifact, and **a check that fails during setup
  has not scanned your change** — it didn't scan and pass, it never ran.
