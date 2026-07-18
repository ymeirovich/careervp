# Wave-0 Closeout — Validated Handoff Prompts

> **Supersedes** `wave-0-prompts.md` Prompts 4 / 7 / 8. Those carry premises that were
> re-validated on **2026-07-17** and found wrong (details below). Fold this file in or
> keep it alongside — but where they conflict, **this file wins**.
>
> **Branch:** `db-redesign` · **Repo:** `/Users/yitzchak/Documents/dev/careervp`
> **Canonical docs tree:** `docs/db-redesign/code/` (`code1`/`code2` are stale artifacts — ignore)
>
> **Retroactive note (2026-07-18):** this file predates [`RUNBOOK-RULES.md`](./RUNBOOK-RULES.md),
> the standing rules every wave's prompt file follows from Wave 1 onward (status ledger, carryover
> handling, prerequisite checks, self-check against the contract, plain-language flags). Wave 0's
> prompts below were not retrofitted with it. **Anyone writing a new wave's prompt file — Wave 2
> onward — must read `RUNBOOK-RULES.md` first and apply it**, not copy this file's older pattern.

---

## 0. READ FIRST — the meta-lesson that shaped this file

**The status ledger and prior runbooks have been wrong three times in a row.** Not
maliciously — there is a *systematic* cause, identified below. Every prompt in this file
therefore opens with a **verify-before-acting** preamble. Do not trust a status column,
a memory, or a prior runbook's "confirmed current state" paragraph. Trust: git history,
the actual file on disk, and a command you just ran.

### Corrections this validation pass produced

| Claim (from ledger / prior runbook / prior session) | Reality (verified 2026-07-17) |
|---|---|
| "0.6 has zero tests" | **FALSE.** `infra/tests/infrastructure/test_p12_p13_retain_stateful.py` exists, 3 tests, **all passing**. Docstring says "P-12/P-13 RED tests" — written RED-first. |
| "0.56 / P-32 not started" | **FALSE.** Commits `4890086` + `56e6ba1` landed real CDK (`budgets.CfnBudget` + `ce.CfnAnomalyMonitor` in `monitoring.py`), 4 synth tests, an evidence script, and a formal scope-lock amendment. Only **live-account evidence capture** remains. |
| "0.3 / F-01/F-06 not started" | **FALSE.** Commit `8dab963`; scope-lock.yaml says `implemented`. |
| "0.0 blocked on open questions" | **FALSE.** O-2 and O-4 both `status: RESOLVED` in scope-lock.yaml. |

### THE ROOT CAUSE — a real tooling defect (fix this first)

There are **two** infra test directories:

- `infra/tests/infrastructure/` — 20 files (P-12, P-13, P-21, P-27, P-32, P-64 …)
- `src/backend/tests/infrastructure/` — 5 files (P-24, P-26 …)

`scope-diff.py` **line 175** hardcodes:
```python
tests_dir = repo_root / "src" / "backend" / "tests"
```
It **never scans `infra/tests/`**. Clauses whose only tests live there are invisible.

**Empirically confirmed** by running the tool both ways (not merely by reading line 175):

| Clause | Default (`src/backend/tests`) | `--tests-dir .` (repo root) | Effect |
|---|---|---|---|
| **P-12** | `spec_written [NO TEST]` | **`test_written [test:1]`** | **impl_state changes** |
| **P-13** | `spec_written [NO TEST]` | **`test_written [test:1]`** | **impl_state changes** |
| P-21 | `test_written [test:2]` | `test_written [test:7]` | evidence under-counted |
| P-27 | `test_written [test:1]` | `test_written [test:6]` | evidence under-counted |
| P-32 | `test_written [test:1]` | `test_written [test:4]` | evidence under-counted |

Board totals move `spec_written 47 → 44`, `test_written 17 → 20`.

Note the subtlety: `P-21`/`P-27`/`P-32` resolve correctly **by luck** — they happen to *also*
have tests under `src/backend/tests`. Only their evidence counts were wrong. `P-12`/`P-13` are
tested **exclusively** under `infra/tests/`, so they are the ones whose *state* is wrong.

**Good news:** `scope-diff.py` already accepts `--tests-dir`, and the scan works correctly when
pointed at the repo root. The defect is purely the hardcoded **default** at line 175 — so the
fix is small and low-risk, not a rework.

**Consequence:** the Wave-0 GATE requires "zero drift across every Wave-0 clause."
`scope-diff.py` **cannot** report P-12/P-13 as tested on its default invocation. **The GATE is
unpassable until this tooling defect is fixed.** That makes it a prerequisite, not housekeeping.

### The two IMMUTABLE laws (every prompt, no exceptions)

1. **NEVER** move the `service-rest-api` RestApi in place or across stacks. Logical id
   `CareerVpCrudDevCrudservicerestapi5E02FD49` must stay byte-identical. A cross-stack move
   is a CFN delete+create → the `execute-api` id/URL changes → **908 live dev users lose the
   backend** until the Amplify frontend rebuilds.
2. **NEVER** move or replace the Cognito `AWS::Cognito::UserPool` → unrecoverable loss of
   908 accounts.

Both are locked by `src/backend/tests/infrastructure/test_p26_blue_green_api.py` (12 tests,
currently green). **Never weaken a test to make a step pass** (scope-lock §0.3).

### What I could NOT validate (unknowns you inherit)

- **Is deploy #1 (RETAIN) actually live on dev?** Needs AWS creds (`cdk diff` vs deployed).
  This is the **most important unknown** — see the hazard note in §2.
- **Is the 0.3 oracle green right now?** Commit `8dab963` claims 145+87 passing; not re-run.
- **Does `cdk refactor` work on this stack?** Needs creds + a dry-run.

### Verified toolchain facts (use these exact invocations)

- CDK CLI **2.1105.0**. `cdk refactor` **exists** and supports:
  `--unstable` (**opt-in required — this is an UNSTABLE feature**), `--dry-run`,
  `--override-file`, `--revert`, `--additional-stack-name`.
- CLI notice recommends upgrading to `^2.1106.0` (a `cdk watch` bug; unrelated to refactor,
  but note the version sensitivity).
- Per-template resource counts (offline synth): dev parent **410**, prod **421**, rto 407;
  Monitoring nested 27; AiAssist/ErrorReport 7/7; CompanyResearch 4. **All < 500.**
- `scope-lock.yaml` `live_anchor.prod_exists: **False**` → **prod is not deployed**. Prod's
  421 is synth-only. Do not treat prod as a live blast radius.

---

## 1. Real remaining Wave-0 work (the honest scope)

| # | Step | Code | Tests | What actually remains |
|---|---|---|---|---|
| 1 | **0.6** (P-12/P-13) | ✅ `567320d` | ✅ 3 passing | Fix scope-diff blind spot; **confirm deploy #1 is live** |
| 2 | **0.65** (P-26 Job 1) | ❌ | ⚠️ guards only | **The whole migration.** Genuinely not started. |
| 3 | **0.56** (P-32) | ✅ `56e6ba1` | ✅ 4 passing | Live-account evidence capture (human) |
| 4 | **0.7** (P-24) | ✅ `09bd6f3` | ✅ 13 passing | Re-verify *after* 0.65 |
| 5 | **GATE** | — | — | Full scope-diff (needs #1's fix) + oracle + coverage + status sync |

**Only 0.65 is real engineering.** The rest is tooling, evidence, and verification.

---

## 2. Execution model — sessions, order, concurrency

### One session per prompt. Do not batch.

**Why (context rot):** 0.65 alone must hold `api_construct.py` (128 KB), `service_stack.py`,
the P-26 spec, the amendment, synth output, and a refactor mapping. Running 0.6 first in the
same session burns context on synth/test noise before the dangerous work begins. Every prompt
below is written to be **self-contained and cold-startable**.

### Order (hard dependencies)

```
  [Prompt D: 0.56 evidence] ──── runs CONCURRENTLY (it's your console work; agent-idle)
                                 touches no file 0.65 touches

  Prompt A (0.6 closeout)
        │  ⛔ HARD GATE: RETAIN must be confirmed live before any refactor
        ▼
  Prompt B (0.65 tests, RED)  ──►  Prompt C (0.65 implement, GREEN)   ← separate sessions
        ▼
  Prompt E (0.7 re-verify)
        ▼
  Prompt F (Wave-0 GATE)
```

**⚠️ The single most important sequencing hazard:** the *entire point* of 0.6-before-0.65 is
that `RETAIN` + `deletion_protection` is the **safety net** if the refactor goes wrong. If
Prompt A finds RETAIN is **not** live on dev, **STOP** — do not start 0.65. Get deploy #1
executed first. A resource-import migration without RETAIN live is surgery without anesthesia.

**Serialization:** `wave-0-prompts.md` already notes 0.6 / 0.65 / 0.7 all touch `app.py` and
CDK constructs — never run those concurrently. Only Prompt D is parallel-safe.

### Subagents: NO for the main work — with one exception

Do **not** delegate Prompts A–F to subagents. A subagent starts cold, re-derives context, and
returns only a summary — you lose mid-flight course-correction on the most dangerous step in
the programme. Separate **sessions** (not subagents) also give you the TDD firewall in §3.

**The one good use:** inside Prompt C, a read-only recon subagent for the fan-out search
*"enumerate every explicitly-named movable resource in `api_construct.py` + its consumers"* —
a big search whose output is a compact list. Optional. Never let a subagent write CDK.

---

## 3. The TDD firewall (why B and C are separate sessions)

Your requirement: *tests must not be self-closing, and must fail before the spec is implemented.*

**The mechanism:** the session that writes the tests must never be the session that makes them
pass. Otherwise the author unconsciously tailors assertions to whatever it built.

- **Prompt B** writes 0.65's outcome tests, derives every assertion from the **spec + amendment
  (never from an implementation — there isn't one)**, proves they **FAIL**, commits tests only.
- **Prompt C** is a **fresh session**. It reads the failing tests as a contract it did not write
  and may not edit. If a test looks wrong → **STOP + §0.3 amendment**, never a quiet edit.

**Honest caveat — where "fail first" does NOT apply:**
For **0.6** and **0.56**, the code already exists and the tests already pass. You cannot
retro-fit a RED phase onto shipped code, and manufacturing one would be theatre. Those are
**characterization tests** (already written, already green) and their prompts are verification,
not TDD.

**But there IS a genuine RED available in Prompt A** — the scope-diff blind spot is a real
defect: a test asserting *"scope-diff reports P-12 as tested"* **fails today** and goes green
when the tool is fixed. That is a true RED→GREEN cycle, and Prompt A uses it.

---

## PROMPT A — Step 0.6 closeout (scope-diff blind spot + deploy #1 confirmation)

**Model/effort:** Claude Code `sonnet / medium` · Codex `gpt-5-codex / medium`
**Deps:** none. **Touches:** `scope-diff.py`, a new tooling test. **Serialize** vs B/C/E.

```
Step 0.6 (P-12/P-13 RETAIN) — CLOSEOUT, NOT IMPLEMENT. Verify every claim below before acting;
the status ledger has been wrong repeatedly.

ALREADY DONE — DO NOT RE-IMPLEMENT:
- Code: commit 567320d. infra/careervp/api_db_construct.py defines self.removal_policy (RETAIN
  unless scratch_teardown_safe) + self.deletion_protection, applied with PITR at ~11 stateful
  sites. P-13 dead stacks (dynamodb_stack.py/s3_stack.py) already removed.
- Tests: infra/tests/infrastructure/test_p12_p13_retain_stateful.py — 3 tests, ALL PASSING.
  (Confirm: cd infra && uv run pytest tests/infrastructure/test_p12_p13_retain_stateful.py -v)

TASK 1 — Fix the scope-diff blind spot (a genuine RED->GREEN cycle).
  Defect: docs/db-redesign/code/code-analysis/project/scope-diff.py line ~175 hardcodes
  tests_dir = repo_root/"src"/"backend"/"tests" and NEVER scans infra/tests/. Clauses tested
  only there are invisible. Verified blind spots: P-12, P-13.
  a) FIRST write a RED test asserting scope-diff resolves P-12 and P-13 to test_written
     (i.e. it discovers infra/tests/infrastructure/test_p12_p13_retain_stateful.py). Run it.
     It MUST FAIL. Paste the failure output.
  b) THEN fix scope-diff.py to scan BOTH src/backend/tests AND infra/tests (additive — it must
     only ever find MORE tests, never fewer; do not weaken any existing drift detection).
  c) Re-run: the test passes; P-12/P-13 now report test_written.
  Do NOT "fix" this by sprinkling a P-12 marker comment into a src/backend test — that hides
  the defect instead of repairing the net.

TASK 2 — Determine deploy #1 status (READ-ONLY; needs AWS creds).
  cd infra && cdk diff CareerVpCrudDev
  Interpret and state plainly:
   - If the diff shows NO pending RETAIN/deletion_protection change -> RETAIN is ALREADY LIVE
     on dev (deploy #1 landed inside some later deploy). Say so explicitly.
   - If it shows a PENDING change -> deploy #1 has NOT happened. Say so explicitly and prepare
     the change set for the human. Do NOT execute it.
   - If creds/region are unavailable -> say "UNKNOWN — could not reach the account", do not guess.
  Known env quirk: CI has no ambient AWS region; if needed reproduce with
  `env -u AWS_DEFAULT_REGION ...` or set --profile explicitly.

GUARDRAILS / STOP CONDITIONS:
- Do NOT run cdk deploy or ExecuteChangeSet. Human-only per P-28.
- Do NOT edit project-scope-lock.md/.yaml (twin-sync ceremony, human-approved only).
- If a stateful site is genuinely missing RETAIN/deletion_protection, that is a REAL gap:
  report it loudly, do not silently patch it into a test.
- If scope-diff's totals move in a way you did not intend (e.g. previously-detected drift
  disappears), STOP — you have weakened the net.

SUCCESS CHECKLIST (all must be true):
[ ] The scope-diff RED test failed first; failure output pasted.
[ ] scope-diff.py now scans both test dirs; P-12 AND P-13 report test_written.
[ ] No previously-reported drift silently vanished (diff the before/after board).
[ ] test_p12_p13_retain_stateful.py still 3/3 green.
[ ] Deploy #1 status stated as exactly one of: ALREADY LIVE / PENDING (change set prepared) /
    UNKNOWN (no creds).
[ ] ruff + mypy clean on touched files.

OUTPUT REQUIRED:
1. A git commit message.
2. One line: "Deploy #1 (RETAIN) on dev = ALREADY LIVE | PENDING | UNKNOWN".
3. IF ALREADY LIVE or PENDING-then-human-executed: "Ready — 0.6 closed. Prompt B (0.65 tests)
   may start." IF PENDING or UNKNOWN: "STOP — 0.65 must not start until RETAIN is live on dev."
```

---

## PROMPT B — Step 0.65 Job 1: write the RED outcome tests (TESTS ONLY)

**Model/effort:** Claude Code `opus / high` · Codex `gpt-5-codex / high`
**Deps:** Prompt A reports RETAIN **live**. **Touches:** test files ONLY.

```
Write the RED outcome tests for P-26 Job 1. THIS SESSION WRITES TESTS ONLY — it must NOT touch
infra/careervp/*.py. A different session implements. This firewall is deliberate: it stops the
tests from being tailored to an implementation.

READ FIRST (derive every assertion from these, never from an implementation — none exists):
- specs/P-26-blue-green-api-spec.md  (esp. "Why this clause is uniquely dangerous")
- specs/amendments/P-26-job1-resource-import-amendment.md  (Option A, ACCEPTED 2026-07-15)
- The existing net you must NOT duplicate or weaken:
  src/backend/tests/infrastructure/test_p26_blue_green_api.py (12 tests, green — RestApi
  logical-id/URL invariant, Cognito singular, no template >=500, P-28 replacement auto-fail,
  flip/retire not automation-executable).

MECHANISM (amended — supersedes the spec's original Job-1 wording): Job 1 is a HUMAN-GATED
CloudFormation resource-import / `cdk refactor` migration (physical-id PRESERVED — no
delete/create). The movable Lambdas/log-groups/queues carry explicit physical names
(self.naming.lambda_name(...)) and are already deployed, so a plain nested-stack move fails with
"resource already exists" (documented in-code at api_construct.py:2105-2114).

WRITE these NEW outcome tests (they MUST FAIL today — the migration does not exist):
1. Parent template resource count drops below the 400 headroom target (it is 410 today).
2. The re-homed feature subtrees now live in per-feature nested stacks (assert by resource type
   + logical id presence in the nested template, absence in the parent).
3. PHYSICAL NAMES/ARNs PRESERVED for every re-homed resource — the whole point of resource-import
   over a plain move. Assert FunctionName / LogGroupName / QueueName are byte-identical to today's
   deployed values.
4. The artifact-chain export locks (api_construct.py:2156-2193 — state machine
   grant_start_execution / grant_task_response to the workers) still resolve after re-homing.
5. The P-24 authorizer Lambda (_add_api_authorizer_lambda, api_construct.py:2034 — dormant, no
   call site, landed AFTER the P-26 spec was written) is accounted for in the mapping.

RUN THEM. THEY MUST FAIL. Paste the failure output — that is this prompt's primary deliverable.
If any new test PASSES on the first run, it is asserting nothing real: fix or delete it.

GUARDRAILS / STOP CONDITIONS:
- Do NOT edit infra/careervp/*.py. Zero production changes this session.
- Do NOT modify the 12 existing guard tests.
- Do NOT weaken anything to make a test writable.
- If the spec/amendment is ambiguous about an assertion, STOP and emit a §0.3 Amendment
  Proposal — do not invent the requirement.

SUCCESS CHECKLIST:
[ ] Every new test FAILS, for the right reason (not an import/collection error). Output pasted.
[ ] Zero changes under infra/careervp/.
[ ] The 12 existing guard tests still pass untouched.
[ ] Tests carry a `scope_lock_clause: P-26` marker so scope-diff sees them.
[ ] Each assertion traces to a named spec/amendment line (cite it in a comment).

OUTPUT REQUIRED:
1. A git commit message (tests only).
2. The pasted RED failure output.
3. "Ready — 0.65 RED tests committed and failing. Prompt C (implement) may start IN A NEW SESSION."
```

---

## PROMPT C — Step 0.65 Job 1: prepare the resource-import migration (GREEN)

**Model/effort:** Claude Code `opus / xhigh` · Codex `gpt-5-codex / high (max)` — hardest step
in the wave; live-user blast radius. **Deps:** Prompt B committed + failing. **NEW SESSION.**

```
Implement P-26 Job 1 to make Prompt B's failing tests green. Read specs/P-26-blue-green-api-spec.md
(all of "Why this clause is uniquely dangerous") AND specs/amendments/
P-26-job1-resource-import-amendment.md (Option A, ACCEPTED) before writing anything.

THE TESTS ARE A CONTRACT YOU DID NOT WRITE AND MAY NOT EDIT. If a test seems wrong, STOP and emit
a §0.3 Amendment Proposal. Never weaken a test to pass (§0.3 forbids it explicitly).

NON-NEGOTIABLE (IMMUTABLE):
- NEVER move the RestApi (logical id CareerVpCrudDevCrudservicerestapi5E02FD49) in place or across
  stacks. 908 live users.
- NEVER move/replace the Cognito UserPool.

MECHANISM: human-gated `cdk refactor` resource-import, physical-id preserved. Verified available
in CDK CLI 2.1105.0. It is an UNSTABLE feature — requires --unstable. Flags available:
--unstable, --dry-run, --override-file, --revert, --additional-stack-name.

  cd infra && cdk refactor --unstable=refactor --dry-run    # inspect the computed mapping
  # use --override-file to correct the mapping where CDK guesses wrong

JOB 2 IS NOT TRIGGERED: every template is <500 (dev 410, prod 421, and prod_exists=False — prod
isn't even deployed). Do NOT stand up a new RestApi. Prepare NO base-path flip / retire change set.
If synth shows any template >=500, STOP per §0.3 — that contradicts the amendment's counts.

ACCOUNT FOR: the artifact-chain export locks (api_construct.py:2156-2193) must be broken/re-imported
in the SAME transaction; and the P-24 authorizer Lambda (api_construct.py:2034, dormant) postdates
the spec — include it in the mapping.

OPTIONAL: you may use ONE read-only recon subagent to enumerate every explicitly-named movable
resource + its consumers. Never let a subagent write CDK.

VERIFY:
cd infra && uv sync && cdk synth        # RestApi id BYTE-STABLE; parent count reduced
cd infra && cdk refactor --unstable=refactor --dry-run   # mapping shows IMPORT, physical-ids preserved
cd src/backend && uv run pytest tests/infrastructure -k p26 -v   # Prompt B's tests now GREEN
cd infra && uv run pytest tests/infrastructure -v                # no infra regressions
cd src/backend && uv run ruff format . && uv run ruff check . && uv run mypy careervp --strict

DO NOT EXECUTE: no cdk deploy, no `cdk refactor` without --dry-run, no ExecuteChangeSet. Hand the
prepared mapping + templates + the P-28 DescribeChangeSet Replacement report to the human (P-28).

STOP CONDITIONS:
- Any template >=500 -> STOP, §0.3.
- The dry-run shows a DELETE+CREATE (not IMPORT) for any named resource -> STOP, the mechanism is
  not behaving as the amendment assumes.
- RestApi or Cognito appears in the mapping AT ALL -> STOP immediately, IMMUTABLE breach.
- `cdk refactor` unavailable/errors without creds -> report honestly, do not fake a mapping.

SUCCESS CHECKLIST:
[ ] All 12 original guard tests STILL green (esp. RestApi logical-id + Cognito singular).
[ ] Prompt B's outcome tests now green — WITHOUT any edit to them.
[ ] cdk refactor --dry-run shows IMPORT/refactor with physical-ids preserved; zero DELETE+CREATE.
[ ] RestApi logical id still CareerVpCrudDevCrudservicerestapi5E02FD49.
[ ] Parent count < 400; no template >= 500.
[ ] ruff + mypy strict clean. cdk synth clean.
[ ] NOTHING executed against AWS.

OUTPUT REQUIRED:
1. A git commit message.
2. The exact list of resources being re-homed + which export locks are broken/re-imported +
   the prepared refactor artifact path awaiting human execution.
3. The rollback lever, stated explicitly (cdk refactor --revert + RETAIN safety net).
4. IF clean: "Ready — 0.65 Job 1 refactor PREPARED (Job 2 not triggered). Human executes; then
   run P-30 smoke; then Prompt E."
5. IF a live-truth contradiction surfaces: STOP per §0.3, emit an Amendment Proposal, do not guess.
```

---

## PROMPT D — Step 0.56 (P-32): live-account evidence capture · RUNS CONCURRENTLY

**Model/effort:** Claude Code `sonnet / medium`. **Deps:** none. **Touches:** no CDK file that
0.65 touches — safe to run in parallel. Mostly *your* console work.

```
Step 0.56 (P-32 budgets slice) — EVIDENCE CAPTURE ONLY, NOT IMPLEMENT.

ALREADY DONE — DO NOT RE-IMPLEMENT:
- CDK: commits 4890086 + 56e6ba1. infra/careervp/monitoring.py
  MonitoringNestedStack._build_cost_observability -> budgets.CfnBudget (monthly limit, 80%-actual
  + 100%-forecasted) + ce.CfnAnomalyMonitor/CfnAnomalySubscription, both routed to the P-21
  SNS topic; CrudMonitoring._build_topic grants budgets.amazonaws.com + costalerts.amazonaws.com
  sns:Publish (without which the subscriptions are silently undeliverable).
- Tests: infra/tests/infrastructure/test_p32_budgets_cost_anomaly.py (4, green).
- Evidence validators: src/backend/scripts/deploy_evidence.py
  (validate_budget_evidence / validate_cost_anomaly_evidence) + tests/unit/test_p32_budget_evidence.py
- Runbook: runbooks/p32-budgets-cost-anomaly-runbook.md
- Scope-lock already amended (v2.0.1/A15) recording the console->IaC move.

THE REMAINING GAP (scope-lock.yaml P-32 note, verbatim): "Post-deploy evidence capture ... remains
human-only -- synth passing is not proof of a real deploy."

TASK:
1. Read runbooks/p32-budgets-cost-anomaly-runbook.md.
2. Run the evidence validators against the live dev account (read-only).
3. If the budget/anomaly detector does NOT exist live, it means the CDK has never been deployed —
   say so plainly. Deploying it is a human P-28 action; do NOT execute it.
4. Produce the dated evidence artifact the spec requires.

GUARDRAILS:
- Read-only against AWS. No cdk deploy / ExecuteChangeSet.
- Do NOT mark 0.56 done on code existing alone — that is the exact anti-pattern P-27/P-28
  established a rule against, and the scope-lock note calls out by name.
- Do NOT edit project-scope-lock.*.

SUCCESS CHECKLIST:
[ ] Evidence artifact exists, is dated, and names the real AWS resources found (or explicitly
    records their absence).
[ ] Validators run green against live, OR absence is explicitly reported.
[ ] No AWS mutation performed.

OUTPUT REQUIRED:
1. A git commit message.
2. "0.56 evidence = CAPTURED (artifact at <path>) | NOT DEPLOYED (human deploy required) |
   UNKNOWN (no creds)".
```

---

## PROMPT E — Step 0.7 (P-24): re-verify post-refactor

**Model/effort:** Claude Code `sonnet / medium`. **Deps:** Prompt C's refactor **executed by the
human** + P-30 smoke green. **Touches:** none expected.

```
Step 0.7 (P-24) is ALREADY IMPLEMENTED (commit 09bd6f3, TDD, 13 tests): identity_resolver.py,
identity_map_repository.py, authorizer wiring, additive sub-keyed identity-map table (RETAIN/PITR).
It landed DORMANT BY DESIGN — _add_api_authorizer_lambda (api_construct.py:2034) has no call site;
the live authorizer is the CognitoUserPoolsAuthorizer. The resolver keeps a legacy user_id-else-sub
passthrough when IDENTITY_MAP_TABLE_NAME is unset.

DO NOT re-implement. DO NOT instantiate the custom authorizer — that is a Wave-1 P-04/P-07 auth flip
with its own P-23 canary + resolver-failure alarm, explicitly out of scope for Wave 0.

This prompt exists because 0.7 landed AHEAD of its own dependency (0.65). Its only job: confirm
0.65's resource-import did not disturb it.

VERIFY:
1. cd src/backend && uv run pytest -k "p24 or identity_surrogate" -v      # 13+ green
2. cd src/backend && uv run ruff format . && uv run ruff check . && uv run mypy careervp --strict
3. cd infra && uv sync && cdk synth   # Cognito UserPool + RestApi logical ids BYTE-STABLE;
   identity-map table + authorizer Lambda still synth correctly post-refactor
4. cd src/backend && uv run pytest tests/infrastructure -k p26 -v          # guards still green
5. scope-diff.py -> P-24 test_written/implemented

SUCCESS CHECKLIST:
[ ] 13+ P-24 tests green post-refactor.
[ ] Cognito UserPool logical id unchanged; RestApi logical id unchanged.
[ ] Identity-map table still RETAIN + PITR.
[ ] Written confirmation the resolver remains dormant-by-design, and that flipping it on is a
    Wave-1 deliverable — i.e. 0.7 = code+tests+synth verified, NOT live-behavior verified.

OUTPUT REQUIRED:
1. A git commit message (status/docs only, unless 0.65 broke something).
2. IF clean: "0.7 re-verified post-0.65, still dormant-by-design. Run Prompt F (Wave-0 GATE)."
```

---

## PROMPT F — Wave-0 GATE

**Model/effort:** Claude Code `opus / high` — judgment-heavy. Given the ledger has been wrong
three times, this step must *adjudicate* truth, not transcribe a table.
**Deps:** Prompts A–E all clean.

```
Run the Wave-0 exit gate. The status ledger has been wrong repeatedly — VERIFY EVERY ROW against
git history and files on disk. Do not transcribe the table; adjudicate it.

PRECONDITION: Prompt A must have fixed scope-diff's infra/tests blind spot. Without it, P-12/P-13
cannot report as tested and this gate CANNOT legitimately pass.

1. python3 docs/db-redesign/code/code-analysis/project/scope-diff.py — full run. Every Wave-0
   clause resolves. Explicitly confirm P-12 and P-13 now report test_written (the blind-spot fix).
2. Frontend oracle (F-01/F-06): cd src/frontend && npm run test:unit && npm run test:integration
   — all 10 §3 contract items green. (Commit 8dab963 claimed 145+87 passing — RE-RUN, don't trust.)
3. cd src/backend && make coverage-tests — confirm enforced_baseline passes; REPORT distance to
   ratchet_target. Do NOT edit the gate (report-only; a single human-approved §12 amendment bumps
   it later — see the coverage-gate two-phase model, v2.2.0).
4. cd infra && uv run pytest tests/infrastructure -v && cd ../src/backend && uv run pytest tests/infrastructure -v
   — BOTH infra test dirs. (There are two. This is the trap that caused three wrong status reports.)
5. Reconcile redesign-execution-plan.md's Status column to VERIFIED REALITY for every Wave-0 row,
   with a dated narrative Status line per corrected row (match the existing 0.55/0.61/0.62/0.63/0.75
   style). Rows currently stale-and-wrong: 0.0, 0.1, 0.1.5, 0.1.6, 0.2, 0.3, 0.56 (all done but
   marked not_started).
6. State whether Job-1's count-relief actually landed, or was deferred — and if deferred, that a
   Wave-1 row exists making it a hard blocker of P-09.

GUARDRAILS:
- Do NOT mark a row verified you have not personally proven this session.
- Do NOT edit project-scope-lock.md/.yaml without the twin-sync ceremony (+ §12 changelog row,
  version bump, Scope-Lock-Approved-By: Yitzchak Meirovich trailer) — human-approved only.
- If any Wave-0 clause cannot reach verified, say so and STOP. Do not generate wave-1-prompts.md
  on an amber gate. A wave's prompt file is only generated once the prior GATE is truly verified.

SUCCESS CHECKLIST:
[ ] scope-diff full run: zero Wave-0 drift; P-12/P-13 visible.
[ ] Oracle re-run green (all 10 items) — not taken on trust.
[ ] Coverage passes enforced_baseline; distance to ratchet_target reported; gate unedited.
[ ] Both infra test suites green.
[ ] Every Wave-0 Status column matches proven reality, each with a dated narrative line.
[ ] The two IMMUTABLE laws still hold (RestApi + Cognito logical ids byte-stable).

OUTPUT REQUIRED:
1. A single "Wave 0 GATE PASSED" commit message (docs-only status sync).
2. An explicit list of anything still open, with its Wave-1 home.
3. IF clean: "Wave 0 verified. wave-1-prompts.md may now be generated — Wave 1 step 1.0's only
   dependency (0.7) is satisfied."
4. IF not clean: name the failing rows and STOP.
```

---

## 4. Issues you should weigh

1. **`cdk refactor` is an UNSTABLE CDK feature** (`--unstable` opt-in). You are using it for the
   most dangerous migration in the programme, on a 908-user stack, on CLI 2.1105.0 (which already
   carries an upgrade notice). Mitigations: `--dry-run` first; `--revert` exists; RETAIN is the net;
   **rehearse on the 0.64 scratch rig** (`scratch_deployment.py`, eu-west-1, ~5.5 min, tears down
   to zero) before touching dev. Strongly recommended — that rig was built for exactly this.
2. **`cdk refactor` needs live AWS credentials** — it reads deployed stack state. 0.65 cannot be
   fully prepared offline. Plan for creds.
3. **RETAIN-before-refactor is the real gate** (§2). Unverified today.
4. **Two infra test dirs** is a standing trap that has now caused three wrong status reports.
   Consider consolidating them, or at minimum document the split in `CLAUDE.md`.
5. **The scope-diff blind spot silently under-reports the ledger** — the tool you trust to detect
   drift has drift of its own. Fix before the GATE.
6. **Deferral bookkeeping:** if you keep Option 1 (defer Job-1 count-relief), the impl_state
   vocabulary has no `deferred` state. Express it as a split row + narrative line + a Wave-1 row
   that hard-blocks P-09 — otherwise it silently evaporates.
7. **Prod is not deployed** (`prod_exists: False`). Prod's 421/500 is synth-only — do not let it
   drive urgency.
8. **Working tree is dirty** (`coverage.xml`, `wave-0-prompts.md`, beta evidence JSONs,
   `test_ai_assist_handler.py`). Commit or stash before starting, or diffs will be polluted.
9. **`Scope-Lock-Approved-By:` has never actually been used** in git history. Prompt F may be its
   first real exercise — expect friction with the scope-lock-guard CI workflow.
```
