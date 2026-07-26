# Wave 3 — DB seams (copy-paste runbook)

> **Generated:** 2026-07-26, against
> `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/redesign-execution-plan.md`
> (Wave-3 table, rows 3.1–3.5) and `project-scope-lock.yaml`. **Authored AHEAD of the Wave-2 GATE
> by explicit human decision** — authoring is gate-safe (no code, no test, no deploy crosses the
> barrier). See the ⛔ banner below and in
> [`wave-3-status.md`](./wave-3-status.md).
>
> **Branch:** `db-redesign` · **Deploy target: `CareerVpCrudDevx`** (not `CareerVpCrudDev`)
> **Canonical docs tree:** `docs/db-redesign/code/` (`code1`/`code2` are stale — ignore)
>
> **Companion files every prompt below depends on — read all before starting:**
> - [`RUNBOOK-RULES.md`](./RUNBOOK-RULES.md) — the seventeen standing rules. Rule 7 (RED/GREEN in
>   separate sessions), rule 11 (first prompt full, rest skeleton), rule 14 (spec-before-test),
>   rules 15–16 (both models stated, Codex picked by rubric), and rule 17 (full paths) all shape
>   this file.
> - [`wave-3-status.md`](./wave-3-status.md) — the LIVE ledger. This file describes *intent*; that
>   one describes *what actually happened*. Check it before starting, update it when you finish or
>   stop.
> - [`../ISSUES.md`](../ISSUES.md) — where the Wave-3 bets `B-3-*` live. They are **seeded** in
>   `wave-3-status.md` and must be promoted here before the wave runs (rule 9).

---

## ⛔ 0. READ FIRST

### 0.0 — This file may not be RUN yet (hard barrier)

Per `redesign-execution-plan.md`: *"Wave gates are hard barriers — never parallelize across a gate."*
This file was **authored** in parallel with an open Wave-2 gate, which is allowed. **Executing** any
prompt below is not, until the `GATE` row in
`/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md`
reads **PASSED** and that is confirmed from git, not from a status column. At authoring time it reads
`not started`, with open human-gated items (the AC-P31-1 DLQ live-delivery drill, the P-02/P-20 devx
deploys, and bet `B-2-3`, the CFN resource ceiling). The first session to run 3.1-RED re-checks this
for real and STOPS if the Wave-2 GATE has not actually passed.

### 0.1 — This file is deliberately incomplete, and that is the design

Per `RUNBOOK-RULES.md` rule 11: **step 3.1 is written in full (both its RED and GREEN halves). Every
later step is a contractual skeleton.** A skeleton carries its clause ids, its acceptance-criteria
ids, its dependencies, its deploy target, its done-when, its model/effort pair, and the bets it
rests on — enough to see the whole wave and how it wires together, not so much that it rots before
it is run. A skeleton is filled into a full prompt only when its dependencies have actually landed,
by a session that has first read every ledger row above it. Clause ids, acceptance-criteria ids, and
done-when come from the contract and the spec and **may not be invented or widened at fill-in time**
— if filling one in requires changing its clause, that is a rule-5 stop and a §0.3 amendment.

### 0.2 — Verify from live, not from docs

Trust git history, the file on disk, live AWS in **devx**, and a command you just ran. Never a status
column or a prior runbook's "current state" paragraph — **including this one.** Wave 1 and Wave 2
both recorded the same lesson repeatedly: deploy states read from a diff and wrong the next day,
stale line-number citations, gates protecting nothing. Every Wave-3 step re-checks its own
prerequisites live (rule 4).

### 0.3 — devx is the primary environment; nothing merges to `main`

Deploys go **only** to `CareerVpCrudDevx`, manual-dispatch only, and **no Wave-3 work merges to
`main`** — the push-to-`main` CI path (`deploy.yml`) still hardcodes the OLD `CareerVpCrudDev` stack
(Wave-2 bet `B-2-4`, item 1, still open). Anything at `api.dev.careervp.com` is the OLD stack; use
the raw invoke URL `https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/`.

### 0.4 — The two immutable laws, and the no-contract-drift law

Every row that touches `infra/` keeps the live API (`RestApi`) and the Cognito user pool byte-stable
— never moved. Every row that touches keying changes only *internal* PK/SK/table structure: the
frontend §3 identifiers and response shapes may not drift, and the executable oracle
(`/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/F-frontend-oracle-spec.md`)
is the check. A Wave-3 change that alters a §3 identifier is a rule-5 stop.

---

## 1. What Wave 3 contains

Wave 3 fixes **the actual break** — the artifact-id / dual-read drift behind the failing
cover-letter and interview-prep paths (clause P-01). Every Track D spec it needs already exists.

| # | Clause(s) | Plain-English step | Spec | Depends on | Detail |
|---|---|---|---|---|---|
| 3.1-RED / 3.1-GREEN | D-H2, D-H3 | One module owns every DynamoDB key; surface `ValidationException` instead of hiding it as "not found"; build the reusable dual-read migration-parity harness | `D-H2-D-H3-key-authority-spec.md` | 0.6 + Wave-2 GATE | **full, below** |
| 3.2 | D-H4, P-01 | Store a canonical `artifact_id` + resolved upstreams → fixes cover-letter/interview-prep | `D-H4-P-01-canonical-artifact-spec.md` | 3.1 | skeleton |
| 3.3 | D-H7 | Eliminate request-path Scans | `D-H7-request-path-scans-spec.md` | 3.1 | skeleton |
| 3.4 | D-M1, D-M2, D-M3, D-M5, D-M6, D-Q | God-class split; stop dual-key CV write; minimized GSI; retire `userEmail` PK; access-pattern doc; quick wins | `D-M-seams-bundle-spec.md` | 3.1 | skeleton |
| 3.5 | D-H9 | Complete the FE-UI-044 CR canonical-store migration; retire the legacy `users-table` CR read path | `D-H9-company-research-migration-spec.md` | 3.1 | skeleton |
| GATE | — | Re-runnable wave demonstration + re-read all `B-3-*` bets | — | all | skeleton |

## 2. Serialization — which steps may not run at the same time

`CoreRepository` / `TableRegistry` (created by 3.1) is the Wave-3 contention hotspot — the analogue
of `api_construct.py` in Wave 2. **3.2, 3.3, 3.4, and 3.5 all extend it.** Never run two of those
concurrently against the same module. 3.4 additionally touches `infra/` (the minimized GSI and the
`userEmail` PK retirement) — serialize its infra edits the way Wave 2 serialized `api_construct.py`.

```
3.1-RED → 3.1-GREEN ─┬─→ 3.2 ─┐
                     ├─→ 3.3 ─┤
                     ├─→ 3.5 ─┼─→ GATE
                     └─→ 3.4 ─┘   (3.4 is highest blast radius: infra GSI + PK retirement)
```

- **Nothing in Wave 3 starts before 3.1-GREEN lands** — 3.1 builds the key authority *and* the
  parity harness that 3.2/3.4/3.5 all reuse. The spec is explicit: D-H2/D-H3 "must precede D-H4,
  D-H7, D-M*, D-H9, and P-01."
- After 3.1-GREEN, 3.2 / 3.3 / 3.5 touch **different feature read paths** and can be filled in and
  run in parallel — but each edits `CoreRepository`, so coordinate ownership (one open editor at a
  time) exactly as §2 warns.
- **3.4 last, or carefully coordinated:** it retires the `userEmail` PK and reshapes a GSI (stateful
  infra), the highest blast radius in the wave. Run it alone against `infra/` and gate every stateful
  change on `cdk diff` showing zero replacement (bet `B-3-4`).

---

# PROMPT 3.1-RED — key-authority repository + parity harness + ValidationException surfacing (tests only)

> **Clause:** D-H2, D-H3 · **Spec:** [`specs/D-H2-D-H3-key-authority-spec.md`](../specs/D-H2-D-H3-key-authority-spec.md)
> (full path: `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H2-D-H3-key-authority-spec.md`)
> **Acceptance criteria:** AC-DH2-1, AC-DH2-2, AC-DH3-1
> **Claude:** opus/high · **Codex:** gpt-5-codex/high
> (rule 15/16 — from `redesign-execution-plan.md` step 3.1 and the spec's `tooling` frontmatter,
> which pins `gpt-5-codex`; not widened here.)
> **Rule 7 applies — this touches key authority and data durability.** RED and GREEN are two
> different sessions. This one writes tests only and carries an **absolute prohibition** on touching
> implementation files.

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md.
This is the first step of Wave 3, so there is no prior Wave-3 row; instead:

  1. Confirm the HARD BARRIER is cleared. Open
     /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md
     and confirm its GATE row reads PASSED. Confirm it from git, not the column:
        cd /Users/yitzchak/Documents/dev/careervp && git log --oneline -8
     If the Wave-2 GATE has not actually passed, STOP — Wave 3 may not run across an open gate.

  2. Confirm THIS step's own prerequisites are met right now, with real commands (not memory):
        cd /Users/yitzchak/Documents/dev/careervp && git log --oneline -3
        cd /Users/yitzchak/Documents/dev/careervp/src/backend && uv run pytest tests/unit -q 2>&1 | tail -5
        ls /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/dal/
     There must be NO existing CoreRepository / TableRegistry yet (this step creates them):
        grep -rl "class CoreRepository\|class TableRegistry" /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/ || echo "none yet — expected"
     If one already exists, STOP and say so in plain English — a prior partial run may need cleanup.

BEFORE WRITING ANY TEST (rule 14): confirm, with a real command, that
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H2-D-H3-key-authority-spec.md
exists, that its "RED Tests to Write First" section names tests covering AC-DH2-1, AC-DH2-2, and
AC-DH3-1, and that each cited test states exact assertion values (no "or"-shaped assertions, no
undefined placeholders). If any of that is not true, STOP — author or fix the spec section first;
do not write tests against a spec that does not say what it is testing.

You are implementing clauses D-H2 and D-H3, acceptance criteria AC-DH2-1, AC-DH2-2, AC-DH3-1, from
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H2-D-H3-key-authority-spec.md.

You are the RED session. You write TEST FILES ONLY. You may not create or edit any file under
/Users/yitzchak/Documents/dev/careervp/src/backend/careervp/ except to READ it. Not temporarily,
not "to see if it works." If you believe an implementation file must change, write the test that
proves it and stop.

--------------------------------------------------------------------------------
FIRST — settle the Wave-3 bets that shape these tests. Seeded in wave-3-status.md; promote to
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/ISSUES.md as
B-3-1 and B-3-2, then record what you find.
--------------------------------------------------------------------------------

BET B-3-1 ("the parity harness can assert EXACT public-projection equality with no benign diffs")
decides the shape of test_dh2_migration_parity_harness_reports_identical_projection. Before writing
it, seed one legacy-shaped item and one canonical-shaped item for a SINGLE artifact type in moto and
reason about what "identical projection" means: if field ordering, an internal-only attribute, or a
timestamp differs for a benign reason, an exact-equality assertion will fail for the wrong reason and
every later step that reuses the harness (3.2/3.4/3.5) inherits that flakiness. Decide NOW (record
in B-3-1): does the harness compare raw items, or a normalized PUBLIC projection against a documented
internal-field allowlist? Write the test to the decision you record — do not leave it "or".

BET B-3-2 ("the swallowed ValidationExceptions D-H3 targets are actually reachable") decides whether
test_dh3_validation_exception_not_returned_as_not_found tests a live behavior change or a guard-rail.
Before writing it, grep the DAL/handler except-sites that convert a DynamoDB ValidationException into
None/404 and confirm at least one is reachable on a request path (the spec's Evidence section cites
dynamo_dal_handler.py:101 and the handler table-name precedence sites). Record in B-3-2 which site
you will force in the test. If NONE is reachable, say so — D-H3 then ships as surface-and-log +
regression only, and the next session needs to know that before GREEN.

--------------------------------------------------------------------------------
THEN — write these tests, and only these (from the spec's "RED Tests to Write First")
--------------------------------------------------------------------------------

  test_dh2_all_artifact_keys_built_by_core_repository
      Static scan: assert NO handler builds `pk`, `sk`, `USER#`, or artifact SK strings outside the
      approved key-authority module(s). Name the exact approved module path(s) the scan allows.
      Cite AC-DH2-1.

  test_dh2_migration_parity_harness_reports_identical_projection
      Seed a legacy record and a canonical record for one artifact type; assert the harness returns
      passed=True and exact projection equality per your B-3-1 decision (raw vs normalized-with-
      allowlist — state which). Cite AC-DH2-2.

  test_dh3_validation_exception_not_returned_as_not_found
      moto/stub DynamoDB raises ValidationException on the site you named in B-3-2; assert the
      repository returns a typed schema error/result (name the exact type), NOT None and NOT a 404.
      Cite AC-DH3-1.

  test_dh2_no_env_table_precedence_in_handlers
      Static scan: assert the `ARTIFACTS_TABLE_NAME -> DYNAMODB_TABLE_NAME -> TABLE_NAME` fallback
      chain is ABSENT from handlers after migration. Cite AC-DH2-1. (This test is RED now — the chain
      still exists per the spec Evidence; it goes green only once GREEN routes handlers through the
      repository.)

RULE 13 — a test that has not been observed to fail is not a test. Run every test above and capture
the failure output VERBATIM. For each, state WHY it failed. A test failing on ImportError, a
collection error, or a missing fixture is NOT RED — it is broken, and it will go green later for
reasons unrelated to the fix. CoreRepository/TableRegistry and the harness do not exist yet, so an
ImportError is the expected first result: structure the tests (or a minimal conftest skip-guard) so
that each one fails on ITS OWN ASSERTION, not on the import. Say explicitly which technique you used.
For the two static-scan tests, this means the scan must run and REPORT the offending sites (proving
the violation exists today), not fail to import the scanner.

No real network calls in any test — moto/stub only. Secrets stay under the P-06 rules.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. Confirmation (rule 14) that the spec existed, named AC-DH2-1/AC-DH2-2/AC-DH3-1, and stated exact
   assertion values — or, if it did not, what you found and where you stopped.
2. Your B-3-1 decision (raw vs normalized projection, with the internal-field allowlist if any) and
   your B-3-2 finding (which ValidationException site is reachable, or that none is). Write both into
   ISSUES.md as B-3-1 and B-3-2.
3. Verbatim failure output for every test, with a one-line why for each, and — for the two static
   scans — the list of offending sites they found today.
4. Confirmation that ZERO files under /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/
   were modified (`git diff --stat`).
5. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clauses D-H2
  and D-H3 in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md:
  update the 3.1-RED row with a plain-English status, the commit, today's date, and anything 3.1-GREEN
  must resolve first (or write "none").
```

---

# PROMPT 3.1-GREEN — make them pass

> **Clause:** D-H2, D-H3 · **Spec:** [`specs/D-H2-D-H3-key-authority-spec.md`](../specs/D-H2-D-H3-key-authority-spec.md)
> **Acceptance criteria:** AC-DH2-1, AC-DH2-2, AC-DH3-1
> **Claude:** opus/high · **Codex:** gpt-5-codex/high (rule 15/16 — same source as 3.1-RED)
> Run in a **FRESH session** that has not seen 3.1-RED's reasoning. `/clear` is the minimum; a
> separate invocation is preferred. The failing tests are a contract you did not write and **may not
> edit** — that clause is the entire firewall. No relaxing an assertion, no widening a scan's
> exclusion list, no `xfail`, no `skip`. If a test looks genuinely *wrong* (not merely
> inconvenient), STOP and raise a §0.3 amendment.

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md
and read the 3.1-RED row. If it left anything open (a B-3-1/B-3-2 decision, a "none reachable"
finding for D-H3), deal with that FIRST. Confirm the RED tests exist and FAIL right now, with a real
command — do not trust the ledger:

  cd /Users/yitzchak/Documents/dev/careervp/src/backend && uv run pytest tests/unit -q -k "dh2 or dh3" 2>&1 | tail -30

If they pass, or fail on import/collection errors rather than their own assertions, STOP and say so.

You are implementing clauses D-H2 and D-H3 (AC-DH2-1, AC-DH2-2, AC-DH3-1). You make the RED tests
pass by writing implementation code ONLY. You may not edit any test file, and you may not edit the
spec's RED-test brief. If a test looks genuinely wrong, STOP and raise a §0.3 amendment — never a
quiet edit.

--------------------------------------------------------------------------------
WHAT TO BUILD (from the spec's Fix Plan)
--------------------------------------------------------------------------------
1. A `TableRegistry` / `CoreRepository` under
   /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/dal/ as the SOLE artifact key
   builder and repository entry point. All `pk`/`sk`/`USER#`/artifact-SK construction lives here.
2. Route the handlers the spec cites (cv_tailoring_handler.py, cover_letter_handler.py, and the
   dynamo_dal_handler.py legacy-alias site) through the repository, REMOVING the
   `ARTIFACTS_TABLE_NAME -> DYNAMODB_TABLE_NAME -> TABLE_NAME` env-var precedence chain. Begin with
   characterization tests so you do not change observable behavior while re-homing the keys.
3. The reusable dual-read migration-parity harness: reads a legacy item and the candidate
   core/canonical read and asserts identical PUBLIC projection per the B-3-1 decision recorded in
   the 3.1-RED row. It MUST be importable and reusable by D-H4 (3.2), D-M2/D-M5 (3.4), and D-H9
   (3.5) — that reusability is the done-when, not an afterthought.
4. On a DynamoDB `ValidationException`, return a typed error/result and log the schema/key mismatch
   — NEVER convert it to a false 404 (D-H3).
5. Preserve frontend §3 identifiers and response shapes exactly. Internal PK/SK changes are not API
   changes — prove it against the oracle
   (/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/F-frontend-oracle-spec.md).

--------------------------------------------------------------------------------
VERIFY — with fresh evidence, not assertion
--------------------------------------------------------------------------------
  cd /Users/yitzchak/Documents/dev/careervp/src/backend && uv run pytest tests/unit -q -k "dh2 or dh3" 2>&1 | tail -20   # the 4 RED tests now pass
  cd /Users/yitzchak/Documents/dev/careervp/src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict
  cd /Users/yitzchak/Documents/dev/careervp/src/backend && uv run pytest tests/unit/ tests/integration/ -q 2>&1 | tail -10   # full suite green, zero regressions
  cd /Users/yitzchak/Documents/dev/careervp/src/backend && make coverage-tests   # coverage gate exit 0, every tier at/above enforced baseline
Then run the coverage gate and confirm the core-branch ratchet did not regress (the enforced
baselines carried from Wave 2; see wave-2-status.md for the last measured numbers).

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. Fresh verbatim pass output for the 4 RED tests, the full suite, mypy --strict, and the coverage
   gate (with the measured numbers).
2. Confirmation that ZERO test files and ZERO spec RED-briefs were modified (`git diff --stat` over
   the test dirs and the spec).
3. Confirmation the parity harness is importable/reusable — name its module path and the import line
   3.2/3.4/3.5 will use.
4. Confirmation the oracle still passes (no §3 identifier / response-shape drift).
5. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clauses D-H2
  and D-H3 in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow, THEN the technical detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md:
  update the 3.1-GREEN row with a plain-English status, the commit, today's date, and anything the
  NEXT step (3.2/3.3/3.4/3.5) must resolve first — in particular the parity-harness import path (or
  write "none").
```

---

# SKELETONS — fill in one at a time, when dependencies have landed

Each skeleton below is **contractual**: its clause ids, acceptance-criteria ids, model/effort pair,
and done-when come from `redesign-execution-plan.md`, `project-scope-lock.yaml`, and the spec files.
Filling one in means expanding it into a full prompt in the shape of 3.1 above — adding the
standing-check block (with the rule-14 spec-existence check and the rule-7 RED/GREEN split where it
applies), the concrete commands, and the two standard output blocks — **without changing anything
already written here.** If you cannot fill it in without widening its clause, that is a rule-5 stop.

**Before filling in any skeleton:** read every ledger row above it in `wave-3-status.md` (especially
the parity-harness import path 3.1-GREEN records), and re-read the `B-3-*` bets it lists.

**Rule 7 applies to 3.2, 3.4, and 3.5** — they touch data durability / migration cutover, so each
splits into RED and GREEN in separate sessions. 3.3 (eliminating Scans) is a contained change; a
single session that writes RED first and pastes the failing output before GREEN is acceptable — say
which you used.

**Rule 16 note on the Codex slug:** the execution-plan rows carry the bare `codex/high` form for
Wave 3. Per RUNBOOK-RULES rule 16 and the "next wave" checklist item 5, do not copy that forward
verbatim — resolve it to the real model at fill-in time. The Track D specs' `tooling` frontmatter
pins `gpt-5-codex`, so `gpt-5-codex/high` is the resolved value for every Wave-3 step below unless a
step's own spec frontmatter says otherwise; changing a spec's pinned model is a rule-8 action, not a
fill-in edit.

---

## 3.2 — Canonical artifact_id + resolved upstreams (fixes the actual break)

| | |
|---|---|
| **Clause** | D-H4, P-01 |
| **Spec** | `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H4-P-01-canonical-artifact-spec.md` |
| **Acceptance criteria** | (read from the spec's "RED Tests to Write First" / "Acceptance Criteria" at fill-in; do not invent) |
| **Claude / Codex** | opus/high · gpt-5-codex/high |
| **Depends on** | 3.1-GREEN (needs `CoreRepository` + the parity harness) |
| **Deploy target** | `CareerVpCrudDevx` (manual-dispatch only; no merge to `main`) |
| **Rule 7** | RED and GREEN separate — this is the P-01 fix, a migration cutover |
| **Bets** | `B-3-1` (parity harness proves every pre-migration `artifact_id` still resolves via the status endpoint post-cutover — the legacy-id probe belongs in the oracle) |

**In plain English.** Store a canonical `artifact_id` and its resolved upstream ids so cover-letter
and interview-prep stop failing to find their VPR/CV. Migration-parity gated: dual-read until the
contract phase; every pre-migration `artifact_id` must still resolve after cutover, proven by the
harness and by a legacy-id probe in the oracle.

---

## 3.3 — Eliminate request-path Scans

| | |
|---|---|
| **Clause** | D-H7 |
| **Spec** | `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H7-request-path-scans-spec.md` |
| **Acceptance criteria** | (read from the spec at fill-in) |
| **Claude / Codex** | opus/high · gpt-5-codex/high |
| **Depends on** | 3.1-GREEN |
| **Deploy target** | `CareerVpCrudDevx` (manual-dispatch only; no merge to `main`) |
| **Rule 7** | Contained change — single session, RED-first with pasted failing output, is acceptable |
| **Bets** | none new — relies on 3.1's key authority to replace Scans with keyed Queries/GSIs |

**In plain English.** Replace every `Scan` on a request path with a keyed `Query`/GSI lookup, so
read latency and cost stop scaling with table size. No money-path or reconcile Scan is in scope here
(those were settled in Wave 2, step 2.5).

---

## 3.4 — Seams bundle: god-class split, dual-key CV write, minimized GSI, retire userEmail PK, access-pattern doc

| | |
|---|---|
| **Clause** | D-M1, D-M2, D-M3, D-M5, D-M6, D-Q |
| **Spec** | `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/D-M-seams-bundle-spec.md` |
| **Acceptance criteria** | (read from the spec at fill-in — this is a multi-clause bundle; map each AC to its D-M* clause) |
| **Claude / Codex** | opus/high · gpt-5-codex/high |
| **Depends on** | 3.1-GREEN |
| **Deploy target** | `CareerVpCrudDevx` (manual-dispatch only; no merge to `main`) — **touches `infra/` (GSI + PK), highest blast radius in the wave** |
| **Rule 7** | RED and GREEN separate — D-M2/D-M5 are migration cutovers; the `userEmail` PK retirement is stateful infra |
| **Bets** | `B-3-4` (GSI/PK changes stay under the CFN ceiling and cause ZERO stateful replacement — `cdk diff` per change; add-new → dual-read → drop-old, never a single replacing change) · `B-3-1` (D-M2/D-M5 parity-gated) |

**In plain English.** Split the god-class read/write path behind `CoreRepository`, stop the dual-key
CV write, minimize the GSI, retire the `userEmail` primary key, and produce the access-pattern doc
(D-M6) that proves every §1a endpoint and every §1b/§1c async path maps to a named Query/GSI with
zero Scan — including status-by-`artifact_id` and a sparse in-flight index. D-M6 is a hard dependency
of the Wave-6 D-H8 single-table collapse; get it right here. Serialize all `infra/` edits.

---

## 3.5 — Complete the FE-UI-044 CR canonical-store migration

| | |
|---|---|
| **Clause** | D-H9 |
| **Spec** | `/Users/yitzchak/Documents/dev/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H9-company-research-migration-spec.md` |
| **Acceptance criteria** | (read from the spec at fill-in) |
| **Claude / Codex** | opus/high · gpt-5-codex/high |
| **Depends on** | 3.1-GREEN |
| **Deploy target** | `CareerVpCrudDevx` (manual-dispatch only; no merge to `main`) |
| **Rule 7** | RED and GREEN separate — backfill + dual-read cutover of live data |
| **Bets** | `B-3-3` (the "239 legacy CR items" figure is still accurate — count live in devx before starting; backfill whatever the live count actually is) · `B-3-1` (dual-read parity via the harness) |

**In plain English.** Finish moving Company Research into the canonical store: verify the legacy
items are backfilled, confirm dual-read parity with the 3.1 harness, then retire the legacy
`users-table` CR read path — closing the dual-read-fallback family that is the root of the P-01 drift.
This is the step that actually removes the fallback, so it comes after 3.2 has proven canonical
resolution works.

---

## GATE — Wave 3 close-out

| | |
|---|---|
| **Clause** | — (whole-wave demonstration) |
| **Depends on** | 3.1, 3.2, 3.3, 3.4, 3.5 all done |
| **Claude / Codex** | opus/high · gpt-5-codex/high (rule 16 — a re-runnable close-out script over data-migration work; `high` matches the wave's steps, not `max`) |
| **Deploy target** | `CareerVpCrudDevx` |

**What the GATE is (rule 12).** Not "every row says done and `scope-diff.py` agrees." A **script**
someone who was not there can run, that emits a dated evidence file under
`/Users/yitzchak/Documents/dev/careervp/docs/evidence/`, and gives the same answer twice from a cold
start. It must cover, at minimum: the 4 D-H2/D-H3 tests plus every D-H4/P-01/D-H7/D-M*/D-H9 test
green; the parity harness passing for every migrated slice (D-H4, D-M2, D-M5, D-H9); the oracle green
with the legacy-`artifact_id` probe (proving pre-migration ids still resolve); `scope-diff.py` exit 0
with no orphan specs; `cdk diff` showing zero stateful replacement for the 3.4 GSI/PK changes; and a
live devx count confirming the CR legacy read path is retired (3.5). Checks that genuinely need a
human print `HUMAN REQUIRED` and exit non-zero until their evidence file exists — six honest checks
beat eight pretended ones.

**Re-read all `B-3-*` bets** at the GATE (rule 9) and record each as settled TRUE/FALSE with the
concrete artifact that settled it, in `wave-3-status.md`. Only then may Wave 4 be authorized.
