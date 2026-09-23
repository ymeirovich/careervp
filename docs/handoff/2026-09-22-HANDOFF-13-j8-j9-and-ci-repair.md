# HANDOFF 13 — validate, then land J8 and reach J9

**Model: Opus 5, high effort.** This handoff is deliberately structured as
*validate → implement → report*. Part 1 is not paperwork: several of the
assumptions below were formed while debugging under time pressure and one has
already been found partially wrong (A2). **Think hard in Part 1.** If an
assumption fails, Part 4 tells you what to do instead of proceeding anyway.

Fresh session at the repo root, on `tools/proof-harness`.

---

## The one-sentence version

**The journey reaches 7 of 9** against deployed `devx` at `2ce05bcd` — J5, J6
and J7 were unblocked by PR #228 — **J8's two root causes are diagnosed and
fixed in the open PR #229**, and the remaining work is to validate that fix's
assumptions, land it, measure J9 for the first time in the project's history,
and repair the four independent CI defects that have made the infra checks
decorative.

---

## Step 0 — verify before trusting this document

| # | Command | Expected |
|---|---|---|
| 0.1 | `aws cloudformation describe-stacks --stack-name CareerVpCrudDevx --region us-east-1 --query "Stacks[0].Outputs[?OutputKey=='DeployedGitSha'].OutputValue" --output text` | `2ce05bcd32e1300d2323c329cdcac582f3323203-dirty` |
| 0.2 | `git log -1 --oneline origin/tools/proof-harness` | `1a402e6 fix(infra): grant the interview-prep worker read on the CV and gap tables` or later |
| 0.3 | `git log -1 --oneline origin/db-redesign` | `2ce05bc Merge pull request #228 …` |
| 0.4 | `gh pr view 229 --json state -q .state` | `OPEN` — the J8 fix, not yet merged |
| 0.5 | `gh pr view 225 --json state -q .state` | `OPEN` — the CI `ENVIRONMENT=devx` fix, still unmerged |
| 0.6 | `python3 -c "import json;d=json.load(open('docs/evidence/journey-20260922T132504-7fb3cf6.json'));print(d['journey_reached'], d['steps']['J8'][:40])"` | `7 fail: Error: …` |
| 0.7 | `aws dynamodb get-item --region us-east-1 --table-name careervp-users-table-devx --key '{"pk":{"S":"USER#848834a8-4061-703d-419c-0294d4e88d66"},"sk":{"S":"TRIAL"}}' --query 'Item.application_count.N' --output text` | `1` — **2 runs left of 3.** Reset before measuring; command in HANDOFF-11 §0.1 |

If 0.1–0.3 diverge, someone has deployed or moved a branch since this was
written — re-derive before trusting anything below.

**Note on 0.2/0.3:** `db-redesign` is *not* an ancestor of `tools/proof-harness`
at the commit level. Each PR merge creates a merge commit on `db-redesign` whose
second parent is the proof-harness commit. The **code trees are identical**;
verify with `git diff --name-only origin/db-redesign origin/tools/proof-harness
-- src infra` (docs-only differences are expected). `CLAUDE.md`'s "strict
superset" wording describes content, not commit ancestry.

---

## Part 1 — validate these assumptions. Think hard.

Each is falsifiable. Run the check. **If an assumption is false, stop and go to
Part 4** rather than proceeding on a broken premise.

### A1 — J8's fatal cause is the output-token cap *(high confidence)*

**Claim:** `LLMClient._invoke_model` hardcoded `max_tokens=4096`; interview prep
asks for up to `MAX_QUESTIONS`(15) × `ANSWER_MAX_WORDS`(300) ≈ 6000 tokens of
answer bodies alone, so the completion truncated and the JSON never closed.

**Evidence already gathered:** worker logs at `2ce05bcd` show both parse
attempts dying on `Unterminated string` at char 18910 and 16628 — ~4096 tokens'
worth of characters — and `git show 2ce05bcd:src/backend/careervp/logic/llm_client.py`
confirms the hardcoded cap with no parameter.

**Check:** re-read those two facts. If the log signature were a *malformed*
rather than *truncated* JSON (e.g. an unescaped quote mid-document), the fix is
wrong — but "unterminated string at the end of output" is truncation, and both
attempts truncated at the same token ceiling despite halving the question count.

### A2 — `max_tokens=16000` is valid for the model interview prep actually uses *(VALIDATED, with a correction)*

**This is the assumption that was partially wrong, and it is the one most worth
your attention.**

Interview prep calls `LLMClient.generate()`, which uses
`DEFAULT_MODEL = 'claude-haiku-4-5-20251001'` — per `CLAUDE.md`'s model strategy,
interview prep is deliberately a **Haiku 4.5** (Template-tier) workload.

The commit message and the code comment justify `16000` as "matching what
`vpr_generator` already uses." **That justification is cross-tier:**
`vpr_generator` sets `self._model_name = 'claude-sonnet-4-6'` (line 215) — its
16000 runs on **Sonnet 4.6**, a different model with a different ceiling. The
number was borrowed from a caller on another tier.

**The fix is still correct:** Claude Haiku 4.5 has a **64K max-output ceiling**
(200K context), so 16000 sits comfortably inside it with 4× headroom. Verified
against the `claude-api` skill's model catalog. **Do not** re-derive this from
memory — if you want to re-verify, query the Models API
(`client.models.retrieve("claude-haiku-4-5").max_tokens`) rather than guessing.

**Action:** the code is fine; **correct the misleading comment** in
`interview_prep.py` (`GENERATION_MAX_TOKENS`) so it cites Haiku 4.5's own
ceiling rather than a Sonnet caller. A future reader who trusts that comment and
raises the number further could exceed a real limit.

### A3 — 16000 is *sufficient*, not merely valid *(medium confidence — unproven end-to-end)*

**Claim:** 16000 output tokens is enough for the 10-question interview prep the
journey requests.

**Unproven.** The fix has never completed a real generation — J8 has not been
re-measured since. Arithmetic says 10 × 300 words ≈ 4000 tokens of answers plus
question text, STAR fields and JSON scaffolding; 16000 should be ample. But the
model that truncated at 4096 was *also* expected to fit.

**Check:** this is validated by the J8 measurement in Part 3, not before it. If
J8 still fails on `Unterminated string` after deploy, the cap is still binding —
see Part 4.

**Second-order risk worth knowing:** `_invoke_model` is a **non-streaming**
`messages.create`. Anthropic's guidance puts ~16000 at the practical ceiling for
non-streaming before SDK HTTP timeouts become a factor. The worker's Lambda
timeout is 300s and the observed failing run used ~80s for two attempts, so
there is room — but if you ever raise `GENERATION_MAX_TOKENS` above ~16000, the
call must move to streaming first.

### A4 — the IAM gap is real and read-only is sufficient *(high confidence)*

**Claim:** the worker was never granted `dynamodb:Query` on
`careervp-cvs-table-devx` or `careervp-gap-responses-table-devx`, so interview
prep was generated with neither the CV nor the gap answers — and read-only
grants fix it.

**Evidence:** two `AccessDeniedException`s in the worker logs, both at WARNING,
generation continuing regardless; `_build_shared_table_env` supplies both table
names; the sibling cover-letter worker grants `cvs_table.grant_read_data`.

**Check:** confirm the worker only *reads* these two tables — `get_cv` and
`get_gap_responses` are both Query operations. If anything writes to them, the
grant is insufficient and the infra test's no-write-actions assertion will need
revisiting.

### A5 — fixing both makes J8 pass *(medium confidence)*

Truncation was fatal; the IAM gap was not. So A1's fix alone may turn J8 green.
**That is not the same as J8 being correct** — without A4's fix the artifact is
built from empty context. Both ship together for that reason. Validated by
measurement in Part 3.

### A6 — J9 (export) works once J8 passes *(UNVERIFIED — assume nothing)*

**J9 has never executed against deployed code.** Not once, in the project's
history. Every step from J5 onward concealed a distinct defect that only
surfaced when the step before it started passing — J5 a frontend wiring bug, J8
two backend bugs that were unrelated to each other. Treat a green J9 as a
pleasant surprise, not the expected outcome.

`journey.spec.ts:519` drives an export and waits on a `download` event. Plan for
it to surface something.

### A7–A10 — the four CI defects *(high confidence, one gap)*

| # | Claim | Evidence | Gap |
|---|---|---|---|
| A7 | PR #225 fixes the `P-64 ENVIRONMENT unset` failure | On #225's own CI, `CDK Synth` **pass** and `iac-security` **pass** — both previously red | `CDK Validation`'s fix is **unproven**: `refactoring-validation.yml`'s path filter (`docs/refactor/**`, `src/backend/careervp/{logic,handlers,models,dal}/**`, `infra/careervp/**`) does not match #225's workflow-only diff, so it never ran on it |
| A8 | `cdk-diff`'s *remaining* failure is the GitHub comment size limit | #225's `cdk-diff` job ran the diff successfully then died on `Validation Failed: … Body is too long (maximum is 65536 characters)` | None — but note this means #225 alone leaves `cdk-diff` red |
| A9 | `Infra Spec Consistency` fails solely on a missing file | `FileNotFoundError: 'infra/careervp/dynamodb_stack.py'` at `refactoring-validation.yml:132`; that file does not exist — tables live in `infra/careervp/api_db_construct.py` | Whether the spec actually matches once repointed is unknown — the check has been dead since the refactor |
| A10 | `python-security` is dependency CVEs only | `anyio 4.12.1` (CVE-2026-63374, -64847) → 4.14.2; `soupsieve 2.8.4` (CVE-2026-85999, -86000) → 2.9.0. `soupsieve` is pinned directly in `pyproject.toml`; `anyio` is transitive via `anthropic`/`httpx` | The audit reported "23 vulnerabilities in 4 packages" — only 2 packages were enumerated. Identify the other 2 before claiming the scope |

### A11 — merging #225 fires no deploy *(verify, don't assume)*

**Claim:** `db-redesign-checks.yml`'s path filter is `src/frontend/**`,
`src/backend/**`, `infra/**`; #225 touches only `.github/workflows/**`, so no
deploy job fires.

**Check:** `scripts/ops/blast-radius.sh merge db-redesign` and read the output.
**Do not infer this from the table in `CLAUDE.md`.** The 2026-09-20 incident was
a one-file *workflow* PR merged as "paperwork" that triggered an ungated deploy
and deleted ~70 resources. The shape of this change is the shape of that
incident. The tool exists precisely so this is measured, not reasoned about.

---

## Part 2 — if the assumptions hold, implement in this order

The ordering is deliberate: **fix CI before landing the infra PR**, so #229's
IAM change gets real automated scrutiny instead of a local `cdk diff`.

### 2.1 Correct the A2 comment (small, do it first)

In `src/backend/careervp/logic/interview_prep.py`, `GENERATION_MAX_TOKENS`'s
comment cites `vpr_generator` as precedent. Rewrite it to cite **Haiku 4.5's own
64K output ceiling** and note that `vpr_generator` is a Sonnet-tier caller.
Backend checks per `CLAUDE.md`. This lands on `tools/proof-harness` and joins
PR #229 automatically.

### 2.2 Land PR #225 (unblocks the CI checks)

Rebase onto current `db-redesign` first — **#225 is 13 commits behind.** Then
blast-radius, paste Action/Triggers/Undo, merge.

### 2.3 Fix `cdk-diff`'s reporting (own PR)

`.github/workflows/cdk-diff.yml` pipes raw `cdk diff --json` straight into
`marocchino/sticky-pull-request-comment`. With 557 resources across 6 stacks the
body will exceed GitHub's 65,536-char cap on essentially every PR. Write the
full diff to `$GITHUB_STEP_SUMMARY` or upload it as an artifact and post only a
bounded summary comment.

**Why this matters more than it looks:** #225 alone turns three checks green and
leaves `cdk-diff` red, which reads as "still broken, keep ignoring it" — the
exact dynamic that let this cluster become wallpaper. Fix both or the habit
survives.

### 2.4 Repoint `Infra Spec Consistency` (own PR)

`refactoring-validation.yml:132` opens `infra/careervp/dynamodb_stack.py`.
Repoint to `infra/careervp/api_db_construct.py`. **Then read what it reports** —
the check has been crashing rather than validating since the refactor, so it may
surface real spec drift. That drift, if any, is a separate finding; don't paper
over it to get a green tick.

### 2.5 Bump the CVE dependencies (own PR)

`soupsieve>=2.8.4` → `>=2.9.0` in `src/backend/pyproject.toml`; refresh the lock
for transitive `anyio`. Identify the two unenumerated packages first (A10).

### 2.6 Land PR #229 (the J8 fix)

With `cdk-diff` and `iac-security` genuinely running, rebase #229 and let them
scrutinise the IAM change. Compare CI's `cdk-diff` against the local one already
recorded in the PR body — they should agree: two read statements added, nothing
destroyed.

Then blast-radius → merge → **the `devx` reviewer gate will park the deploy
awaiting a human.** The operator is the sole reviewer. (An agent session cannot
approve it: the auto-mode classifier blocks both the approval call and any
attempt to self-grant permission for it. Ask the operator; do not work around
it.)

### 2.7 Validate the deploy

Exactly as HANDOFF-12A's successor did, and it caught nothing only because
nothing was wrong:

1. `DeployedGitSha` == the new merge SHA, `StackStatus` == `UPDATE_COMPLETE`
2. **Diff all 22 stack outputs against a baseline captured before the merge** —
   only `DeployedGitSha` should move
3. Amplify `db-redesign` job `SUCCEED` on the same commit
4. `make preflight` — expect 8 pass / 1 fail (the known `-dirty` GIT_STAMP issue)

---

## Part 3 — get through J8, then measure J9

**Reset the trial budget first** (HANDOFF-11 §0.1). Count is at 1 of 3; you have
two runs.

```bash
cd src/backend && BASE_URL=https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com make journey
```

**Expected:** J8 passes. **Do not assume it.** If J8 fails again, the failure
signature tells you which assumption broke:

| Signature | Meaning | Go to |
|---|---|---|
| CTA reads `Retry`, logs show `Unterminated string` | A3 false — 16000 still insufficient | Part 4.1 |
| CTA reads `Retry`, logs show a *different* error | A1 was incomplete — a third defect | Diagnose from logs; same discipline |
| CTA reads `Generate`, zero worker invocations | A frontend wiring bug, J5's shape | Compare against the J5 fix |
| J8 passes, J9 fails | Expected per A6 | Diagnose; it has never run |

**When J9 runs for the first time**, whatever it does, record it. A first-ever
measurement of the final journey step is worth an evidence commit regardless of
outcome.

---

## Part 4 — if an assumption is false

### 4.1 If 16000 is still insufficient (A3 false)

Do **not** simply raise the number. Non-streaming `messages.create` is the
binding constraint above ~16000 (A3). Options, in order of preference:

1. **Reduce the ask.** `ANSWER_MAX_WORDS = 300` × 15 questions is a large
   document. V1 scope per `CLAUDE.md` is "Interview Prep (10 Q max)" while
   `MAX_QUESTIONS = 15` — reconciling those reduces the worst case by a third.
2. **Move `generate()` to streaming**, then raise the cap. This is a real change
   to `llm_client.py` affecting four other callers — scope it deliberately.
3. **Chunk the generation** — request questions in batches and assemble. Largest
   change; last resort.

### 4.2 If the IAM fix is insufficient (A4 false)

If the worker turns out to write to those tables, `grant_read_data` is wrong and
the infra test's forbidden-actions assertion will fail. Widen deliberately and
narrowly — do not reach for `grant_read_write_data` on a generation worker
without establishing exactly which write it needs and why.

### 4.3 If merging #225 would fire a deploy (A11 false)

Stop. That contradicts the documented path filter and means `CLAUDE.md`'s
topology table is stale. Re-derive the topology and correct the table **before**
merging anything — a wrong topology table is more dangerous than a red check.

### 4.4 If PR #225 no longer passes its own checks after rebase

13 commits of drift. If `CDK Synth`/`iac-security` no longer pass on it, the
`ENVIRONMENT=devx` fix is necessary but no longer sufficient — diagnose the new
failure before merging, and report rather than layering fixes.

---

## Carried forward — operational hazards

- **`deployed commit is known` FAILs preflight on every run** — the `-dirty`
  GIT_STAMP issue, open since handoff 08. Not a blocker; don't let it train you
  to skim.
- **`Security Audit` is red on `db-redesign` itself**, independent of any PR —
  same `python-security`/`iac-security` causes. 2.5 and 2.2 should clear it.
- **The `devx` reviewer gate needs a human.** Budget for the wait; it is the only
  human checkpoint between a merge and a CloudFormation CREATE+EXECUTE.

## MANDATORY cleanup — do not skip

**`.claude/settings.local.json` contains a temporary `autoMode.allow` rule**,
added with the operator's explicit, time-boxed consent: *"Grant permission rule
as long as the rule does NOT persist past J6-J9."*

It permits the trial-budget `put-item` on `careervp-users-table-devx`. It is
marked `TEMPORARY (remove after the J5-J9 journey measurement work, handoff
12A)`. A backup of the original file is at the prior session's scratchpad; the
rule is the second entry in `autoMode.allow`, after `$defaults`.

**When J9 has been measured — pass or fail — remove that rule and tell the
operator you have.** The consent was scoped to this work. If J6-J9 work
continues into a further handoff, carry this obligation forward verbatim rather
than dropping it.

## Ground rules

- `scripts/ops/blast-radius.sh <event> <branch>` before any merge, deploy,
  deletion or credential change; paste Action/Triggers/Undo **before** acting.
- Stop and ask on a `CREATE+EXECUTE` you didn't expect, `NO ENVIRONMENT GATE`,
  or an environment with `0 rules`.
- Verify the environment; never infer it from a plan document — **including this
  one.**
- Reset the trial budget before `make journey`. `TRIAL_LIMIT_APPLICATIONS = 3`.
- One concern per commit. Every fix gets a regression test that fails before and
  passes after.
- A repo grep is not an inventory, a green deploy is not a working system, and
  **a check that fails during setup has not scanned your change** — it didn't
  scan and pass, it never ran.
