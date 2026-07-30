# Wave 3 — DB seams (copy-paste runbook)

> **Generated:** 2026-07-26, against
> `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/redesign-execution-plan.md`
> (Wave-3 table, rows 3.1–3.5) and `project-scope-lock.yaml`. **Authored AHEAD of the Wave-2 GATE
> by explicit human decision** — authoring was gate-safe (no code, no test, no deploy crossed the
> barrier). Wave 2 has since passed; see the authorization note below and in
> [`wave-3-status.md`](./wave-3-status.md).
>
> **Branch:** `db-redesign` · **Deploy target: `CareerVpCrudDevx`** (not `CareerVpCrudDev`)
> **Repo root:** `/Users/yitzchak.meirovich/Documents/code5/careervp` (rule 17a — declared once here;
> every full path below is built from it, and every shell block anchors on
> `cd "$(git rev-parse --show-toplevel)"` so a relocated checkout needs one edit, not an excavation)
> **Canonical docs tree:** `docs/db-redesign/code/` (`code1`/`code2` are stale — ignore)
>
> **Companion files every prompt below depends on — read all before starting:**
> - [`RUNBOOK-RULES.md`](./RUNBOOK-RULES.md) — the eighteen standing rules. Rule 7 (RED/GREEN in
>   separate sessions), rule 11 (first prompt full, rest skeleton), rule 14 (spec-before-test),
>   rules 15–16 (both models stated, Codex picked by rubric), rule 17 (full paths), and rule 18
>   (Fable routed to long-horizon implementation only) all shape
>   this file.
> - [`wave-3-status.md`](./wave-3-status.md) — the LIVE ledger. This file describes *intent*; that
>   one describes *what actually happened*. Check it before starting, update it when you finish or
>   stop.
> - [`../ISSUES.md`](../ISSUES.md) — where the Wave-3 bets `B-3-*` live. They are **seeded** in
>   `wave-3-status.md` and must be promoted here before the wave runs (rule 9).

---

## ✅ 0. READ FIRST

### 0.0 — Wave 3 is authorized to run

Per `redesign-execution-plan.md`: *"Wave gates are hard barriers — never parallelize across a gate."*
This file was **authored** in parallel with an open Wave-2 gate, which was allowed because no code,
test, or deploy crossed the barrier. That barrier is now clear: the `GATE` row in
`/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md`
reads **PASSED**, with evidence `docs/evidence/wave2-gate-20260726T205022Z-d8707a.json`
(9 PASS, 0 FAIL, 0 HUMAN_REQUIRED, 2 RECORDED) and smoke evidence
`docs/evidence/smoke-20260726T205022Z-fdac58.json` at 4/4 green. The first 3.1-RED session should
still re-check the ledger before starting and stop if a newer contradiction appears.

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
(`/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/F-frontend-oracle-spec.md`)
is the check. A Wave-3 change that alters a §3 identifier is a rule-5 stop.

### 0.5 — Lessons from Waves 0–2, and where each one lands in Wave 3

Applied 2026-07-27. Each row is a real incident from this project, not general advice, with the
specific Wave-3 step it binds. **A step that ignores its row here is repeating a failure this
project has already paid for.**

| Incident (wave) | Lesson | Where it binds in Wave 3 |
|---|---|---|
| Ledger said "DEPLOYED"; a real change set showed **523 pending changes** the next day (W1) | Committed ≠ deployed. A `cdk diff` read is not a deploy state | Every row's ledger entry states deploy status explicitly. 3.4 may not claim a stateful change is live without a post-deploy read |
| Status ledger wrong three times running (W0) | **Verify from live, not docs — including this file** | §0.2. Every dated baseline in the D-H2/D-H3 spec is marked "re-confirm live before asserting" |
| 30-day soak protected nothing; the belief under it was never written as checkable (W1) | A belief with no check is a hope | All five `B-3-*` promoted to `ISSUES.md` **before** 3.1-RED ran, each with a cheapest-tier check and a fallback decided now |
| Brief named 2 files; a **third**, in a directory the scan didn't cover, was the one the app used (W1, step 1.6) | An Evidence section proves a defect exists; it does not size the work | The spec's 2026-07-27 Evidence addendum: the cited 3 files were ~⅓ of the real 9. 3.1-GREEN's file list is the enumerated baseline, not the citation |
| 2.2-RED enumerated a worker that wasn't an SQS consumer; GREEN correctly refused to special-case it → §0.3 amendment + a RED-fix session + a split step (W2) | **A RED test whose scope exceeds what GREEN may touch blocks the wave** | `B-3-5` and the spec's two scan-boundary pins. Both D-H2 scans carry named out-of-scope exclusions |
| P-31's spec said "add DLQs and alarms" but not *what shape*; a precision edit landed **first** (W2, `ac9841c`) | Pin assertion values in the spec before RED, as a separate visible action | Done 2026-07-27 for `D-H2-D-H3-key-authority-spec.md`. **Do the same for `D-H4-P-01`, `D-H7`, `D-M`, and `D-H9` at fill-in** — all four are ~55-line Wave-0 specs with the same thinness |
| Live `cdk diff` reported 6 stacks of drift that was pre-existing devx staleness, not the change under test (W2, 2.3-root-cause) | Isolate the change: synth at HEAD, synth with the change stashed, diff the **templates** | `B-3-4`'s check names this technique explicitly. 3.4 uses it, not a live diff |
| `api-client.test.ts` was permanently green over a sign-out path broken in production (W1) | A test not observed to fail is not a test — and `skip` is the quietest way to ship one | 3.1-RED's rule-13 block forbids the skip-guard and requires an explicit `pytest.fail` on missing imports |
| `wave-1-prompts.md` written whole, then needed 3 standing corrections, a 7-row stale-citation table, and a 3-way step split (W1) | Detail the first prompt; skeleton the rest | 3.2–3.5 stay skeletons until 3.1-GREEN records the `CoreRepository`/`TableRegistry` module paths |
| `scope-diff.py` never scanned `infra/tests/`, so the Wave-0 GATE was unpassable and nobody knew (W0) | A gate can be broken in a way that looks like a pass | Wave-3 GATE re-checks the tool, not just its output |
| Rule 17 produced 608 absolute paths to a checkout that had moved; the first command of 3.1-RED failed (W3, found 2026-07-27) | An absolute path is a hardcoded environment assumption | Rule **17a**: root declared once per file, shell blocks anchored on `cd "$(git rev-parse --show-toplevel)"` |
| Wave 2 accumulated 2.2 + P-19 + P-20 + P-31 undeployed, then reconciled all at once (W2) | Undeployed debt compounds and pollutes the next step's diff | 3.4 touches stateful infra: deploy `CareerVpCrudDevx` per infra-touching step, or state the undeployed debt in the row |
| Wave-2's `wave_gate.py` hardcodes `WAVE2_BETS`, `WAVE2_CLAUSES`, and a `wave2-gate-` filename | A forked gate script drifts from the original | The Wave-3 GATE **parameterizes** `src/backend/scripts/wave_gate.py` by wave — it does not fork a `wave3_gate.py` |

---

## 1. What Wave 3 contains

Wave 3 fixes **the actual break** — the artifact-id / dual-read drift behind the failing
cover-letter and interview-prep paths (clause P-01). Every Track D spec it needs already exists.

| # | Clause(s) | Plain-English step | Spec | Depends on | Detail |
|---|---|---|---|---|---|
| 3.1-RED / 3.1-GREEN | D-H2, D-H3 | One module owns every DynamoDB key; surface `ValidationException` instead of hiding it as "not found" | `D-H2-D-H3-key-authority-spec.md` | 0.6 + Wave-2 GATE | **full, below** |
| 3.2 | D-H4, P-01 | Store a canonical `artifact_id` + resolved upstreams → fixes cover-letter/interview-prep | `D-H4-P-01-canonical-artifact-spec.md` | 3.1 | **full, below** (3.2-SPEC → 3.2-RED → 3.2-GREEN) |
| 3.3 | D-H7 | Eliminate request-path Scans | `D-H7-request-path-scans-spec.md` | 3.1 | **full, below** (3.3-SPEC → 3.3-RED → 3.3-GREEN) |
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
  key authority that 3.2/3.4/3.5 all build on. The spec is explicit: D-H2/D-H3 "must precede D-H4,
  D-H7, D-M*, D-H9, and P-01."
- After 3.1-GREEN, 3.2 / 3.3 / 3.5 touch **different feature read paths** and can be filled in and
  run in parallel — but each edits `CoreRepository`, so coordinate ownership (one open editor at a
  time) exactly as §2 warns.
- **3.3 is the exception, pending its own evidence.** At the 2026-07-29 fill-in the pre-flight found
  no request-path Scan that is 3.3's own (bet `B-3-8`), which points at 3.3 touching neither module
  — in which case it needs **no lock at all** and runs freely alongside 3.4/3.5. That is **decision
  point DP-1 in §3.3**, resolved by 3.3-SPEC, not assumed here. A second decision, **DP-2**, can
  pull one line of `infra/api_construct.py` into 3.3 and therefore into 3.4's `infra/` lock; §3.3
  carries the rule-10 stopping condition that hands the large IAM reading to 3.4 instead. **Read the
  3.3-SPEC ledger row before scheduling 3.3 against anything else.**
- **3.4 last, or carefully coordinated:** it retires the `userEmail` PK and reshapes a GSI (stateful
  infra), the highest blast radius in the wave. Run it alone against `infra/` and gate every stateful
  change on `cdk diff` showing zero replacement (bet `B-3-4`).

---

# PROMPT 3.1-RED — key-authority repository + ValidationException surfacing (tests only)

> **Clause:** D-H2, D-H3 · **Spec:** [`specs/D-H2-D-H3-key-authority-spec.md`](../specs/D-H2-D-H3-key-authority-spec.md)
> (full path: `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H2-D-H3-key-authority-spec.md`)
> **Acceptance criteria:** AC-DH2-1, AC-DH3-1
> **Claude:** opus/high · **Codex:** gpt-5-codex/high
> (rule 15/16 — from `redesign-execution-plan.md` step 3.1 and the spec's `tooling` frontmatter,
> which pins `gpt-5-codex`; not widened here.)
> **Rule 7 applies — this touches key authority and data durability.** RED and GREEN are two
> different sessions. This one writes tests only and carries an **absolute prohibition** on touching
> implementation files.

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md.
This is the first step of Wave 3, so there is no prior Wave-3 row; instead:

  1. Confirm the HARD BARRIER is cleared. Open
     /Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md
     and confirm its GATE row reads PASSED. Confirm it from git, not the column:
        cd /Users/yitzchak.meirovich/Documents/code5/careervp && git log --oneline -8
     If the Wave-2 GATE has not actually passed, STOP — Wave 3 may not run across an open gate.

  2. Confirm THIS step's own prerequisites are met right now, with real commands (not memory):
        cd /Users/yitzchak.meirovich/Documents/code5/careervp && git log --oneline -3
        cd /Users/yitzchak.meirovich/Documents/code5/careervp/src/backend && uv run pytest tests/unit -q 2>&1 | tail -5
        ls /Users/yitzchak.meirovich/Documents/code5/careervp/src/backend/careervp/dal/
     There must be NO existing CoreRepository / TableRegistry yet (this step creates them):
        grep -rl "class CoreRepository\|class TableRegistry" /Users/yitzchak.meirovich/Documents/code5/careervp/src/backend/careervp/ || echo "none yet — expected"
     If one already exists, STOP and say so in plain English — a prior partial run may need cleanup.

BEFORE WRITING ANY TEST (rule 14): confirm, with a real command, that
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H2-D-H3-key-authority-spec.md
exists, that its "RED Tests to Write First" section names tests covering AC-DH2-1 and
AC-DH3-1, and that each cited test states exact assertion values (no "or"-shaped assertions, no
undefined placeholders). If any of that is not true, STOP — author or fix the spec section first;
do not write tests against a spec that does not say what it is testing.

You are implementing clauses D-H2 and D-H3, acceptance criteria AC-DH2-1, AC-DH3-1, from
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H2-D-H3-key-authority-spec.md.

You are the RED session. You write TEST FILES ONLY. You may not create or edit any file under
/Users/yitzchak.meirovich/Documents/code5/careervp/src/backend/careervp/ except to READ it. Not temporarily,
not "to see if it works." If you believe an implementation file must change, write the test that
proves it and stop.

--------------------------------------------------------------------------------
FIRST — settle the Wave-3 bets that shape these tests. All five (B-3-1 .. B-3-5) were PROMOTED into
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/ISSUES.md
on 2026-07-27, before this prompt ran. Read them there — belief, cheapest check, and the fallback
already decided. Your job is to RUN the checks and record what you find, not to re-invent the bets.
--------------------------------------------------------------------------------

BET B-3-1 is **RETIRED at scope-lock v2.7.0 — do not run its check, do not settle it, and do not
build what it shaped.** The migration-parity harness no longer exists: the RED test
`test_dh2_migration_parity_harness_reports_identical_projection`, `AC-DH2-2`, and the 10-attribute
allowlist were all deleted from `D-H2-D-H3-key-authority-spec.md`, and D-H2's `verification` is now
`unit` alone in both contract twins. All stored data is disposable test data (`O-3`, resolved
2026-07-27), so there is no cutover to prove parity for and no later step inherits a harness. Write
the four RED tests the spec names for AC-DH2-1/AC-DH3-1 and nothing else. Settle only `B-3-2` and
`B-3-5` in this step.

BET B-3-2 (are the swallowed ValidationExceptions reachable?) decides whether
test_dh3_validation_exception_not_returned_as_not_found tests a live behavior change or a guard-rail.
The tier-1 grep was already run on 2026-07-27 and found a live site:
`dynamo_dal_handler.py:629-637` catches ValidationException on the cover-letter read, retries the
legacy key schema, and on a miss returns Result(success=True, data=None, code=ResultCode.SUCCESS) —
a schema mismatch presented as an empty success. `:678-684` is the same shape on the scan path.
CONFIRM THAT LIVE (it is a line citation, and this project has been burned by stale ones), then force
that site in the test. If it turns out unreachable, say so — D-H3 then ships as surface-and-log +
regression only, and 3.1-GREEN needs to know that before it starts.

BET B-3-5 (can D-H2's scans be scoped to the artifacts/core table without leaving a hole?) shapes
BOTH static scans. The boundary was drawn on 2026-07-27 and is pinned in the spec; the enumerated
baselines are dated and **must be re-confirmed live before you assert against them.** If live
disagrees with the spec's baseline, that is the finding — record the delta, do not quietly adopt
either number.

--------------------------------------------------------------------------------
THEN — write these tests, and only these (from the spec's "RED Tests to Write First")
--------------------------------------------------------------------------------

The spec's "RED Tests to Write First" section was given a PRECISION EDIT on 2026-07-27 and now pins
every assertion value, scan boundary, and enumerated baseline. READ IT — do not re-derive these from
the summaries below, and do not widen them.

  test_dh2_all_artifact_keys_built_by_core_repository
      Static scan over src/backend/careervp/handlers/ and src/backend/careervp/logic/: artifacts/core
      pk/sk/USER#/artifact-SK strings are built ONLY in the two approved modules
      (dal/table_registry.py, dal/core_repository.py). Auth/trial/user-pool keying is OUT of scope
      (Wave-6 D-H8) and the scan names that exclusion explicitly. Re-confirm the spec's live baseline
      (9 USER# sites / 5 files) before asserting against it. Cite AC-DH2-1.

  test_dh3_validation_exception_not_returned_as_not_found
      moto/stub raises ClientError with Error.Code='ValidationException' and the VERBATIM message
      'The provided key element does not match the schema' — pin the message, do not improvise one.
      Assert the repository returns EXACTLY Result(success=False,
      code=ResultCode.TABLE_SCHEMA_MISMATCH), one code, no alternative — and specifically NOT
      Result(success=True, data=None, code=ResultCode.SUCCESS). Pinning the message pins the branch
      in _map_dal_error_code (dynamo_dal_handler.py:46-55), which is why no "or" is needed. The same
      verbatim string is already used by the passing test at
      tests/unit/test_dynamo_dal_handler.py:395-417 — reuse that proven stimulus.
      CORRECTED MECHANISM (do not repeat the old claim): _map_dal_error_code does NOT compute the
      code on the defective path. dynamo_dal_handler.py:629-637 catches the ValidationException,
      retries under the legacy {'pk','sk'} schema, and on a miss returns Result(success=True,
      data=None, code=SUCCESS) DIRECTLY — never reaching _dal_failure_result. :678-684 is the same
      shape on the scan path. Confirm both live before asserting.
      GREEN BOUNDARY (carry into 3.1-GREEN, do not let it fail the whole branch): retry-HITS stays
      success-with-item; retry-MISSES becomes TABLE_SCHEMA_MISMATCH; retry-RAISES unchanged.
      Cite AC-DH3-1.

  test_dh2_core_repository_reads_canonical_only_items
      Seed the artifacts table in moto with items carrying ONLY canonical key attributes
      (applicationId/artifactId, no pk/sk), then exercise EVERY CoreRepository read method for that
      artifact type and assert each returns the seeded item. This is the negative proof that the
      dual-shape write at dynamo_dal_handler.py:535-552 can later be reduced to one key convention
      without a read going dark — a static "no callers" scan cannot establish that, because the
      legacy key path is selected at RUNTIME. Cite AC-DH2-1.

  test_dh2_no_env_table_precedence_in_handlers
      Static scan asserting multi-key env fallback resolution of the ARTIFACTS/CORE table is absent
      from handlers. Scope: the ARTIFACTS_TABLE_NAME -> DYNAMODB_TABLE_NAME -> TABLE_NAME chain AND
      its two-key DYNAMODB_TABLE_NAME -> TABLE_NAME tail. Fallbacks resolving a DIFFERENT table
      (APPLICATIONS_/USERS_/GAP_QUESTIONS_/KNOWLEDGE_) are OUT of scope; a single unconditional
      os.environ['ARTIFACTS_TABLE_NAME'] is not a chain. Assert against the spec's enumerated
      baseline (9 files / 23 sites, re-confirmed live) as a RATCHET — may shrink, never grow — so a
      NEW precedence site fails even before the baseline reaches zero. Cite AC-DH2-1.

RULE 13 — a test that has not been observed to fail is not a test. Run every test above and capture
the failure output VERBATIM. For each, state WHY it failed. A test failing on ImportError, a
collection error, or a missing fixture is NOT RED — it is broken, and it will go green later for
reasons unrelated to the fix.

CoreRepository/TableRegistry do not exist yet, so an ImportError is the expected
naive first result. DO NOT resolve that with a skip-guard — a skipped test is not a red test, and
`skip` is the quietest way in this repo to ship a decorative assertion. Use an explicit
importability assertion instead: attempt the import inside the test, catch ImportError, and fail on
your own message naming the module path that must exist, e.g.
`pytest.fail(f'AC-DH2-1: CoreRepository not importable at {path}')`. The test then fails on ITS OWN
assertion, with a message describing the missing contract, and goes green for exactly the right
reason. Say explicitly which technique you used for each of the four.

For the two static-scan tests this does not arise — they scan source text, so they must run TODAY
and REPORT the offending sites, proving the violation exists now. If either scan reports ZERO sites,
STOP: the scan is mis-scoped or mis-rooted, not the codebase clean.

No real network calls in any test — moto/stub only. Secrets stay under the P-06 rules.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. Confirmation (rule 14) that the spec existed, named AC-DH2-1/AC-DH3-1, and stated exact
   assertion values — or, if it did not, what you found and where you stopped.
2. **B-3-1 is RETIRED (scope-lock v2.7.0) — the harness no longer exists; do not look for it.**
   **B-3-2 is pre-settled toward "reachable"** by the corrected mechanism above (the swallow sits on
   a live, default-on compatibility path gated by COVER_LETTER_LEGACY_READ_ENABLED, not in a dead
   defensive except). CONFIRM that live — name the site and show the flag's default — and write the
   confirmation into ISSUES.md as B-3-2. If you find it is NOT reachable, that contradicts the
   spec's corrected mechanism: STOP and flag it rather than quietly recording the opposite finding.
3. Verbatim failure output for every test, with a one-line why for each, and — for the two static
   scans — the list of offending sites they found today.
4. Confirmation that ZERO files under /Users/yitzchak.meirovich/Documents/code5/careervp/src/backend/careervp/
   were modified (`git diff --stat`).
5. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clauses D-H2
  and D-H3 in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md:
  update the 3.1-RED row with a plain-English status, the commit, today's date, and anything 3.1-GREEN
  must resolve first (or write "none").
```

---

# PROMPT 3.1-GREEN — make them pass

> **Clause:** D-H2, D-H3 · **Spec:** [`specs/D-H2-D-H3-key-authority-spec.md`](../specs/D-H2-D-H3-key-authority-spec.md)
> **Acceptance criteria:** AC-DH2-1, AC-DH3-1
> **Claude:** fable/high · **Codex:** gpt-5-codex/high
> (rule 15 — copied verbatim from `redesign-execution-plan.md`'s Wave-3 row `3.1-GREEN`. **Fable per
> rule 18:** long-horizon implementation against an already-pinned spec, multi-file, key-authority
> blast radius. 3.1-RED stays `opus/high` — rule 14 has already fixed every assertion value there,
> so RED is precision authoring with no judgment left for a larger tier to buy.)
>
> **Running this step on Fable — read rule 18 before you start.** Everything in the standing check,
> the rule-14 spec verification, the rule-5 stop conditions, the file-touching prohibition, the
> drift-comparison block, and the status-ledger update is **contract enforcement and stays verbatim**.
> What changes is the body: state the goal, the constraints, and the acceptance criteria **up front
> in one turn**, then let it run — do not feed the task in progressively across turns, and do not
> add step-by-step implementation choreography. Expect a single request to run for minutes; that is
> normal, not a hang. Treat `stop_reason: "refusal"` as a real outcome to handle, not an error. If
> every request 400s immediately, check the organization's data-retention configuration before
> debugging the payload — Fable is unavailable under zero data retention.
> Run in a **FRESH session** that has not seen 3.1-RED's reasoning. `/clear` is the minimum; a
> separate invocation is preferred. The failing tests are a contract you did not write and **may not
> edit** — that clause is the entire firewall. No relaxing an assertion, no widening a scan's
> exclusion list, no `xfail`, no `skip`. If a test looks genuinely *wrong* (not merely
> inconvenient), STOP and raise a §0.3 amendment.

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md
and read the 3.1-RED row. If it left anything open (a B-3-1/B-3-2 decision, a "none reachable"
finding for D-H3), deal with that FIRST. Confirm the RED tests exist and FAIL right now, with a real
command — do not trust the ledger:

  cd /Users/yitzchak.meirovich/Documents/code5/careervp/src/backend && uv run pytest tests/unit -q -k "dh2 or dh3" 2>&1 | tail -30

If they pass, or fail on import/collection errors rather than their own assertions, STOP and say so.

You are implementing clauses D-H2 and D-H3 (AC-DH2-1, AC-DH3-1). You make the RED tests
pass by writing implementation code ONLY. You may not edit any test file, and you may not edit the
spec's RED-test brief. If a test looks genuinely wrong, STOP and raise a §0.3 amendment — never a
quiet edit.

--------------------------------------------------------------------------------
WHAT TO BUILD (from the spec's Fix Plan)
--------------------------------------------------------------------------------
1. A `TableRegistry` / `CoreRepository` under
   /Users/yitzchak.meirovich/Documents/code5/careervp/src/backend/careervp/dal/ as the SOLE artifact key
   builder and repository entry point. All `pk`/`sk`/`USER#`/artifact-SK construction lives here.
2. Route the handlers through the repository, REMOVING the artifacts/core env-var precedence chain.
   **The file list is NOT the three files the spec's Evidence section names** — that was a sample,
   not the population (see the spec's 2026-07-27 Evidence addendum). The authoritative list is the
   enumerated baseline in the spec's RED-test section, re-confirmed live by 3.1-RED: **9 handler
   files, 23 sites** — `ai_assist_handler.py`, `company_research_handler.py`,
   `cover_letter_handler.py`, `cover_letter_submit_handler.py`, `cv_tailoring_handler.py`,
   `export_handler.py`, `interview_prep_handler.py`, `interview_prep_submit_handler.py`,
   `vpr_submit_handler.py` — plus the `dynamo_dal_handler.py` legacy-alias site. Note
   `cv_tailoring_handler.py` uses the two-key `DYNAMODB_TABLE_NAME -> TABLE_NAME` tail, not
   `ARTIFACTS_TABLE_NAME`; it is in scope, and the spec's original three-file citation was wrong
   about which key it uses. **Out of scope, and the scan agrees:** any fallback resolving a different
   table (`APPLICATIONS_`/`USERS_`/`GAP_QUESTIONS_`/`KNOWLEDGE_`), and auth/trial/user-pool keying.
   Begin with characterization tests so you do not change observable behavior while re-homing keys.

   **If clearing the full enumerated baseline in one session is not achievable, do NOT weaken the
   test.** The scan is a ratchet by design (B-3-5): shrink the baseline as far as you get, leave the
   remainder enumerated, and record the residue in the 3.1-GREEN ledger row with a named owner. A
   ratchet that holds is the shipped fallback; a loosened assertion is a rule-5 stop.
   core/canonical read and asserts identical PUBLIC projection per the B-3-1 decision recorded in
   the 3.1-RED row. It MUST be importable and reusable by D-H4 (3.2), D-M2/D-M5 (3.4), and D-H9
   (3.5) — that reusability is the done-when, not an afterthought.
4. On a DynamoDB `ValidationException`, return a typed error/result and log the schema/key mismatch
   — NEVER convert it to a false 404 (D-H3).
5. Preserve frontend §3 identifiers and response shapes exactly. Internal PK/SK changes are not API
   changes — prove it against the oracle
   (/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/F-frontend-oracle-spec.md).

--------------------------------------------------------------------------------
VERIFY — with fresh evidence, not assertion
--------------------------------------------------------------------------------
  cd /Users/yitzchak.meirovich/Documents/code5/careervp/src/backend && uv run pytest tests/unit -q -k "dh2 or dh3" 2>&1 | tail -20   # the 4 RED tests now pass
  cd /Users/yitzchak.meirovich/Documents/code5/careervp/src/backend && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict
  cd /Users/yitzchak.meirovich/Documents/code5/careervp/src/backend && uv run pytest tests/unit/ tests/integration/ -q 2>&1 | tail -10   # full suite green, zero regressions
  cd /Users/yitzchak.meirovich/Documents/code5/careervp/src/backend && make coverage-tests   # coverage gate exit 0, every tier at/above enforced baseline
Then run the coverage gate and confirm the core-branch ratchet did not regress (the enforced
baselines carried from Wave 2; see wave-2-status.md for the last measured numbers).

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. Fresh verbatim pass output for the 4 RED tests, the full suite, mypy --strict, and the coverage
   gate (with the measured numbers).
2. Confirmation that ZERO test files and ZERO spec RED-briefs were modified (`git diff --stat` over
   the test dirs and the spec).
   3.2/3.4/3.5 will use.
4. Confirmation the oracle still passes (no §3 identifier / response-shape drift).
5. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clauses D-H2
  and D-H3 in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow, THEN the technical detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md:
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
| **Spec** | `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H4-P-01-canonical-artifact-spec.md` |
| **Acceptance criteria** | **AC-DH4-1, AC-P01-1, AC-DH4-2** (read live from the spec's "Acceptance Criteria" section — confirmed present 2026-07-27) |
| **Claude / Codex** | opus/high · gpt-5-codex/high |
| **Depends on** | 3.1-GREEN (needs `CoreRepository` + `TableRegistry`) |
| **Deploy target** | `CareerVpCrudDevx` (manual-dispatch only; no merge to `main`) |
| **Rule 7** | RED and GREEN separate — this is the P-01 fix, on the request path of two broken features |
| **Bets** | `B-3-6`, `B-3-7` — **new at fill-in, promoted by 3.2-SPEC before 3.2-RED runs** (the `B-3-5` precedent). `B-3-1` remains retired at scope-lock v2.7.0 (no harness, no migration, no legacy-id probe) |

**In plain English.** Store a canonical `artifact_id` and its resolved upstream ids so cover-letter
and interview-prep stop failing to find their VPR/CV. **Canonical ids only — no dual-read window, no
cutover probe, no harness, no legacy-id resolution** (v2.7.0/`O-3`: the data is disposable, so there
is no pre-migration `artifact_id` to keep resolving).

**Filled in 2026-07-27.** Three sessions, in this order, and the order is the point:
**3.2-SPEC** (pin the spec's assertion values + promote the two new bets) → **3.2-RED** (four tests,
no implementation) → **3.2-GREEN** (fresh session, implementation only). 3.2-SPEC exists because
§0.5's W2/P-31 row names this spec explicitly: *"Do the same for `D-H4-P-01`, `D-H7`, `D-M`, and
`D-H9` at fill-in."* It is not optional politeness — the spec's current RED-test line for AC-P01-1
reads *"resolves owned canonical VPR **or** rejects"*, which is exactly the "or"-shaped assertion
rule 14 forbids. **3.2-RED may not start until 3.2-SPEC has landed**, and its standing check stops
if it hasn't.

**Model note, so nobody "helpfully" upgrades it.** `redesign-execution-plan.md`'s Wave-3 row 3.2
says `opus/high | codex/high`. Per rule 15 the Claude side is copied verbatim — **3.2-GREEN is
`opus/high`, not `fable/high`**, even though rule 18's three conditions arguably hold. Rows 3.1-GREEN
and 3.5 carry `fable` in the plan itself; 3.2 does not. Re-routing it is an edit to the execution
plan under rule 8, not something a fill-in session decides. The Codex side resolves `codex/high` →
`gpt-5-codex/high` per rule 16 and the spec's `tooling` frontmatter, which pins `gpt-5-codex`.

---

# PROMPT 3.2-SPEC — pin the assertion values, promote the two new bets (spec + ISSUES.md only)

> **Clause:** D-H4, P-01 · **Spec:** [`specs/D-H4-P-01-canonical-artifact-spec.md`](../specs/D-H4-P-01-canonical-artifact-spec.md)
> (full path: `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H4-P-01-canonical-artifact-spec.md`)
> **Acceptance criteria:** AC-DH4-1, AC-P01-1, AC-DH4-2 — **pinned, never renumbered, never widened**
> **Claude:** opus/high · **Codex:** gpt-5-codex/high
> (rule 16 — precision authoring against an existing contract. **Not Fable:** rule 18 routes
> precision authoring away from Fable for the same reason it routes RED away, and this session
> writes no implementation.)
>
> **What this session is.** The separate visible action §0.5 requires: a precision edit to one spec's
> "RED Tests to Write First" section, plus two bets into `ISSUES.md`. It writes **no test and no
> implementation**. It is the analogue of the 2026-07-27 precision edit already made to
> `D-H2-D-H3-key-authority-spec.md`, which is why 3.1-RED had nothing left to improvise.

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md
and read the 3.1-GREEN row — 3.2 is the first step that depends on it.

  1. Confirm 3.1-GREEN actually landed, from git and the filesystem, not the column:
        cd "$(git rev-parse --show-toplevel)" && git log --oneline -6
        ls src/backend/careervp/dal/core_repository.py src/backend/careervp/dal/table_registry.py
        cd "$(git rev-parse --show-toplevel)/src/backend" && uv run python -c "from careervp.dal.core_repository import CoreRepository; from careervp.dal.table_registry import TableRegistry; print('importable')"
     If either module is missing or not importable, STOP — 3.2 has no foundation to extend.

  2. Read the THREE residues 3.1-GREEN recorded as explicitly NOT ITS OWN, and treat all three as
     out of bounds for the whole of 3.2: (a) logic/company_research_store.py::_legacy_table_name
     reversed env order, (b) dal/dynamo_dal_handler.py still building keys internally, (c) the inner
     query-level fallback in _legacy_read_cover_letter_by_scan that still returns success-None.
     (a) and (c) belong to 3.5, (b) to a later wave. Fixing one here is scope drift, not diligence.

You are performing a PRECISION EDIT on
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H4-P-01-canonical-artifact-spec.md,
and promoting two bets into
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/ISSUES.md.

You may edit EXACTLY those two files. You may not touch any file under
/Users/yitzchak.meirovich/Documents/code5/careervp/src/, any test, or either
project-scope-lock twin.

--------------------------------------------------------------------------------
WHY THIS SESSION EXISTS (rule 14, and §0.5's W2/P-31 row)
--------------------------------------------------------------------------------
The spec is a ~57-line Wave-0 spec with the same thinness P-31's spec had. Its four RED-test lines
name behaviors but not values, and one of them — AC-P01-1's "assert repository resolves owned
canonical VPR or rejects" — is literally an "or"-shaped assertion. A RED session cannot legally
write tests from it (rule 14 check 3), and a GREEN session handed "or" will satisfy whichever
branch is cheaper. Pin the values here, once, visibly.

HARD BOUNDARY on what pinning means. You may make each RED-test description state exact values,
exact scope, and exact out-of-scope exclusions. You may NOT:
  - add, remove, rename, or renumber an acceptance criterion (AC-DH4-1, AC-P01-1, AC-DH4-2 stand),
  - add a fifth RED test,
  - change the Done-when, the Sequencing section, or the tooling frontmatter,
  - re-introduce anything v2.7.0 removed (no parity harness, no dual-read, no legacy-id probe, no
    cutover — Fix Plan item 5 records that removal; leave it),
  - change what D-H4 or P-01 require. That is the contract twins' text and a §0.3 amendment.
If pinning a value turns out to require any of the above, STOP and say which one and why.

--------------------------------------------------------------------------------
THE LIVE FINDINGS TO CONFIRM AND PIN (gathered 2026-07-27 at fill-in — CONFIRM EACH, then pin)
--------------------------------------------------------------------------------
Every line/count below is a citation, and this project has been burned by stale citations three
times (§0.2, §0.5). Re-read each site live. Where live disagrees, THE DELTA IS THE FINDING — record
it in the spec's Evidence section; do not quietly adopt either number.

A. The spec's own Evidence citations have already drifted. Live at fill-in:
   - `vpr_status_handler.py` — the spec cites `:184-192,253` for provenance projection.
     `_extract_vpr_provenance` is at approximately :181-188 and the provenance `setdefault` loop at
     approximately :253. Off by ~3 lines. Re-cite from live.
   - `cv_tailoring_handler.py` — the spec cites `:983-986` for path-parameter id extraction.
     `_extract_cv_tailoring_id` is at approximately :983-989 live. Re-cite.
   - `src/frontend/lib/types.ts:75` (`HubArtifact.artifact_id: string | null`) and `:517`
     (`CVTailoringRequest.vpr_id: string | null` + the load-bearing comment) both still read as
     cited. Confirm and leave.

B. **The canonical `artifact_id` write is best-effort and silently swallowed.** This is the D-H4
   defect with teeth and the spec's Evidence section does not mention it. Live:
   `src/backend/careervp/dal/application_repository.py` — `artifact_statuses.<type>_artifact_id` is
   written by a two-step update at approximately :340-390, and the step-2 `update_item` is wrapped
   in `except Exception: pass  # Non-fatal — frontend localStorage fallback handles missing
   artifact_id`. The hub read is `application_handler.py:_build_artifacts` (~:86-96), which serves
   `status_map.get(f'{artifact_type}_artifact_id')` — i.e. `None` when the write no-opped.
   AC-DH4-1's round-trip identity CANNOT hold while a swallowed exception can leave the hub serving
   `artifact_id: null` over an artifact that exists. Add this to Evidence and pin what
   `test_dh4_status_endpoint_resolves_hub_artifact_id` asserts about it. Note the shape is the same
   family as D-H3: a real failure presented as a benign empty. Do NOT widen D-H3's clause to cover
   it — D-H4 owns the artifact_id write; say so explicitly.

C. **The six-name id ladder IS the "3-schema / vpr_id routing" ambiguity, in code.** Live:
   `src/backend/careervp/logic/artifact_dependency_resolver.py::_artifact_id` (~:167-173) resolves
   an artifact's id by trying, in order: `artifact_id`, `artifactId`, `vpr_id`,
   `company_research_id`, `job_id`, `id`. A canonical id means this ladder collapses. Pin which
   names survive and which must be gone, as an enumerated list — not "prefer canonical".

D. **Cover letter resolves the CLIENT's vpr_id and checks ownership afterwards.** Live:
   `cover_letter_handler.py::_resolve_vpr_payload` (~:320-345) calls `dal.get_vpr(vpr_id)` on the
   client-supplied value, then post-hoc compares `user_id` and raises
   `ValueError('VPR ownership mismatch for cover letter: {vpr_id}')`. Two distinct defects, and the
   pin must separate them: (i) the read happens before the ownership decision, and (ii) the failure
   surfaces as a `ValueError` whose HTTP mapping must be pinned to an exact status and error shape,
   not left as "rejects". AC-P01-1 says *resolved owned upstreams, not arbitrary client keys* —
   pin the exact status code and the exact envelope for a stale/cross-tenant `vpr_id`.

E. **Interview prep has TWO resolution paths and the ownership failure falls through to the
   second.** Live: `interview_prep_handler.py::_resolve_vpr_from_jobs_table` (~:686-712) reads an
   env pair `VPR_JOBS_TABLE_NAME` or `JOBS_TABLE_NAME`, and on an ownership mismatch **returns
   `None`** — after which `~:791-827` falls through to `dal.get_vpr(api_request.vpr_id)` and only
   then raises. A cross-tenant id that is refused by path one and then looked up again by path two
   is the drift. Pin that the ownership refusal is terminal, with the same exact status/envelope as
   (D) so both features answer identically.

F. **`interview_prep_submit_handler.py:144` coerces an id chain into `application_id`:**
   `application_id = api_request.application_id or api_request.job_id or api_request.vpr_id`.
   §3 item 1 is `application_id == job_id`; `vpr_id` is a third thing. DECIDE AND PIN whether this
   site is in scope for 3.2 or is D-M/3.4 work, and state the decision either way — an undecided
   site is how 2.2 blocked the wave (§0.5). If in scope, name it in the pinned file list.

G. **AC-DH4-2 may already be satisfied — this is `B-3-6` below.** Live:
   `src/backend/careervp/models/api_models.py::CVTailoringRequest` (~:340-344) reads
   `vpr_id: str | None` with **no default**, so present-and-null validates and omitted is a
   required-field error. That is already §3 item 3's semantics. The F-01 oracle spec's F-04 evidence
   cites `api_models.py:282` as `str = Field(min_length=1)` — that citation is stale; the model has
   moved and changed. Pin `test_dh4_cv_tailoring_preserves_vpr_id_null` to assert BOTH halves at the
   layer that can actually fail (parse/validate AND the handler's observable response), and state in
   the spec what happens if it passes on day one — see the bet.

--------------------------------------------------------------------------------
PROMOTE TWO BETS TO ISSUES.md (rule 9) — the beliefs, checks and fallbacks are drafted; your job
is to CONFIRM and RECORD them, not re-invent them. B-3-5 is the precedent for adding a bet at
fill-in when the pre-flight finds one.
--------------------------------------------------------------------------------
B-3-6 — BELIEF: "AC-DH4-2 (`vpr_id: null` accepted, absent distinguishable from null) still fails
  against the live backend, so it is a behavior change."
  CHECK (tier 1, zero new code): read `CVTailoringRequest` in
  `/Users/yitzchak.meirovich/Documents/code5/careervp/src/backend/careervp/models/api_models.py`.
  PRE-SETTLED TOWARD FALSE at fill-in: it is `vpr_id: str | None`, no default. Confirm live.
  FALLBACK, decided now: if false, D-H4's `vpr_id` half ships as an explicit REGRESSION GUARD —
  the test stays, is labelled as a guard, and the ledger row records that it passed on day one and
  why. It does NOT get deleted (§3 item 3 is IMMUTABLE and unguarded today) and it does NOT get
  bent into failing. Additionally: F-04 is a Wave-4 clause, still `status: TARGET,
  current_state: live_bug` in `project-scope-lock.yaml:152`, whose cited violation appears already
  fixed at the model layer. FLAG that overlap for human review — a Wave-3 step may not silently
  close a Wave-4 clause, and F-04's real remaining surface (if any) belongs to Wave 4.

B-3-7 — BELIEF: "AC-DH4-1's hub round-trip is broken on the READ side; the write path is sound."
  WHY IT IS A BET: if the write is the cause, 3.2's file list grows to include
  `dal/application_repository.py` and the fix takes D-H3's shape (surface, don't swallow) — a
  materially larger step than a read-path change, and discovering that mid-GREEN is exactly the
  W1/1.6 incident in §0.5.
  CHECK (tier 3, one minimal moto test): seed an application, force the step-2 `update_item` to
  raise, then read the hub — if it serves `artifact_id: null` over an existing artifact, the write
  path is implicated and the belief is FALSE.
  FALLBACK, decided now: if false, `application_repository.py` is named in the pinned file list
  BEFORE 3.2-RED writes a line, and the swallowed `except` becomes a surfaced typed failure in the
  same shape D-H3 used — recorded in the spec, not improvised in GREEN.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. For each of A–G: the live command you ran, what you found, and whether it CONFIRMS the fill-in
   citation or is a DELTA. Every delta recorded in the spec's Evidence section.
2. The edited "RED Tests to Write First" section, quoted in full, with every assertion value pinned
   and every out-of-scope exclusion named. No "or"-shaped assertion may remain anywhere in it.
3. Explicit confirmation that AC-DH4-1 / AC-P01-1 / AC-DH4-2 are unchanged in id, count, and text,
   and that nothing v2.7.0 removed came back.
4. `B-3-6` and `B-3-7` written into ISSUES.md under "Wave-3 bets", each with belief / why-it-is-a-bet
   / cheapest-tier check / fallback-decided-now / settled-status, plus the index rows added to
   `wave-3-status.md`'s bets table so the GATE's rule-9 re-read finds seven bets, not five.
5. Confirmation that ZERO files under
   /Users/yitzchak.meirovich/Documents/code5/careervp/src/ and ZERO test files were modified
   (`git diff --stat`).
6. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clauses D-H4
  and P-01 in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md:
  add a 3.2-SPEC row with a plain-English status, the commit, today's date, and what 3.2-RED must
  resolve first — in particular how B-3-6 and B-3-7 settled (or write "none").
```

---

# PROMPT 3.2-RED — canonical artifact_id + resolved upstreams (tests only)

> **Clause:** D-H4, P-01 · **Spec:** [`specs/D-H4-P-01-canonical-artifact-spec.md`](../specs/D-H4-P-01-canonical-artifact-spec.md)
> (full path: `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H4-P-01-canonical-artifact-spec.md`)
> **Acceptance criteria:** AC-DH4-1, AC-P01-1, AC-DH4-2
> **Claude:** opus/high · **Codex:** gpt-5-codex/high
> (rule 15/16 — Claude side verbatim from `redesign-execution-plan.md` Wave-3 row 3.2; Codex side
> resolved from the bare `codex/high` per rule 16 and the spec's `tooling` frontmatter pin.
> **Not Fable — rule 18 forbids routing RED to it.**)
>
> **Rule 7 applies — this is the P-01 fix on two live request paths, and it decides ownership
> behavior for cross-tenant ids.** RED and GREEN are two different sessions. This one writes tests
> only and carries an **absolute prohibition** on touching implementation files.
>
> **Requires 3.2-SPEC to have landed.** Without the precision edit there is no legal set of
> assertion values to write against, and the standing check below stops.

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md
and read the 3.1-GREEN row AND the 3.2-SPEC row. If either left anything open, deal with that first.

  1. Confirm 3.1-GREEN's foundation is real, from the filesystem and the interpreter, not the column:
        cd "$(git rev-parse --show-toplevel)" && git log --oneline -8
        cd "$(git rev-parse --show-toplevel)/src/backend" && uv run python -c "from careervp.dal.core_repository import CoreRepository; from careervp.dal.table_registry import TableRegistry; print(sorted(n for n in dir(CoreRepository) if not n.startswith('_')))"
     Expect the 3.1-GREEN surface: get_cover_letter_by_artifact_id, list_cover_letters,
     list_tailored_cvs, get_company_research, plus registry/dal properties. There is NO VPR read
     method and no interview-prep read method yet — 3.2 adds what it needs. If CoreRepository is
     missing or unimportable, STOP.

  2. Confirm the suite is green before you add a failing test, so a later failure is unambiguous:
        cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit -q 2>&1 | tail -5

  3. Confirm the D-H2/D-H3 ratchets from 3.1 still hold — you must not regress them:
        cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit -q -k "dh2 or dh3" 2>&1 | tail -10

BEFORE WRITING ANY TEST (rule 14): confirm, with a real command, that
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H4-P-01-canonical-artifact-spec.md
exists, that its "RED Tests to Write First" section names tests covering AC-DH4-1, AC-P01-1 and
AC-DH4-2, and that each cited test states exact assertion values. **Specifically grep it for the
word "or" inside the RED-test section** — if AC-P01-1's line still reads "resolves owned canonical
VPR or rejects", 3.2-SPEC has NOT landed. STOP. Do not write tests against it and do not pin the
values yourself inside this session; that is 3.2-SPEC's separate visible action (§0.5).

You are implementing clauses D-H4 and P-01, acceptance criteria AC-DH4-1, AC-P01-1, AC-DH4-2, from
the spec above.

You are the RED session. You write TEST FILES ONLY. You may not create or edit any file under
/Users/yitzchak.meirovich/Documents/code5/careervp/src/backend/careervp/ or
/Users/yitzchak.meirovich/Documents/code5/careervp/src/frontend/ except to READ it. Not temporarily,
not "to see if it works." If you believe an implementation file must change, write the test that
proves it and stop.

--------------------------------------------------------------------------------
FIRST — read how B-3-6 and B-3-7 settled
--------------------------------------------------------------------------------
Both were promoted to
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/ISSUES.md
by 3.2-SPEC. Read them there — belief, cheapest check, fallback already decided, and how each
settled. Your job is to write the tests the settled position implies, not to re-litigate either.

  - If B-3-6 settled FALSE (expected): `test_dh4_cv_tailoring_preserves_vpr_id_null` is a
    REGRESSION GUARD that passes on day one. Write it, label it in its docstring as a guard with the
    reason, and report it as such in the rule-13 block below. **Do not bend it into failing**, do
    not delete it, and do not treat its green as evidence that D-H4 is done.
  - If B-3-7 settled FALSE, `dal/application_repository.py` is in the pinned file list and
    `test_dh4_status_endpoint_resolves_hub_artifact_id` must force the swallowed step-2 failure.

--------------------------------------------------------------------------------
THEN — write these tests, and only these (from the spec's pinned "RED Tests to Write First")
--------------------------------------------------------------------------------
Four tests. The spec is authoritative for every assertion value after 3.2-SPEC's precision edit —
READ IT. Do not re-derive values from the summaries below, and do not widen them. The summaries
exist so you can tell whether you are reading the right section, not so you can skip it.

  test_dh4_status_endpoint_resolves_hub_artifact_id
      Seed a hub artifact; assert the status endpoint resolves the SAME opaque artifact_id —
      round-trip identity, exact string equality, not "an id is present". Per B-3-7, force the
      `application_repository` step-2 write failure and assert the hub does NOT serve
      `artifact_id: null` over an artifact that exists. Cite AC-DH4-1.

  test_p01_cover_letter_uses_resolved_vpr_not_client_key
      Call cover-letter generation with a stale AND with a cross-tenant `vpr_id`; assert the exact
      status code and exact error envelope the spec pins, and assert no read of another user's VPR
      is performed at all (not "performed then rejected"). Cite AC-P01-1.

  test_p01_interview_prep_uses_resolved_vpr_not_client_key
      Same stimulus and the SAME pinned status/envelope as the cover-letter test — both features
      must answer identically. Additionally assert the ownership refusal is TERMINAL: the jobs-table
      path refusing must not fall through to a second `dal.get_vpr` lookup of the same client key.
      Cite AC-P01-1.

  test_dh4_cv_tailoring_preserves_vpr_id_null
      Request with `vpr_id` present-and-null: accepted. Request with `vpr_id` omitted:
      distinguishable, per the spec's pinned outcome for each. Assert at both the model-validation
      layer and the handler's observable response. Cite AC-DH4-2. See B-3-6 above for what to do
      when this passes immediately.

OUT OF SCOPE, and say so explicitly in the test module docstring so 3.2-GREEN inherits the boundary:
  - The three residues 3.1-GREEN recorded (`company_research_store::_legacy_table_name`,
    `dynamo_dal_handler` internal key building, the inner `_legacy_read_cover_letter_by_scan`
    query-level fallback). (a) and (c) are 3.5's, (b) is a later wave's.
  - Anything under `infra/` — 3.2 touches no infrastructure. That is 3.4.
  - Auth/trial/user-pool keying (Wave-6 D-H8), and the D-M god-class split (3.4).
  - Clause F-04 (Wave 4). If B-3-6 shows F-04's cited violation is already fixed, that is a FLAG for
    human review, not a Wave-3 deliverable.

RULE 13 — a test that has not been observed to fail is not a test. Run every test above and capture
the failure output VERBATIM. For each, state WHY it failed. A test failing on an ImportError, a
collection error, or a missing fixture is NOT RED — it is broken, and it will go green later for
reasons unrelated to the fix.

Where 3.2 needs a `CoreRepository` method that does not exist yet (VPR/interview-prep resolution),
an ImportError or AttributeError is the naive first result. DO NOT resolve that with a skip-guard —
a skipped test is not a red test, and `skip` is the quietest way in this repo to ship a decorative
assertion (§0.5, `api-client.test.ts`). Attempt the import/attribute access inside the test, catch
it, and fail on your own message naming the exact symbol that must exist, e.g.
`pytest.fail('AC-P01-1: CoreRepository.<method> not available at careervp.dal.core_repository')`.
The test then fails on ITS OWN assertion and goes green for exactly the right reason. Say explicitly
which technique you used for each of the four, and name the exact symbols 3.2-GREEN must create.

The two behavioral tests (cover letter, interview prep) exercise code that exists today — they must
RUN today and fail on their pinned assertions. If either passes today, STOP: the stimulus is wrong,
not the codebase correct.

No real network calls in any test — moto/stub only. Secrets stay under the P-06 rules.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. Confirmation (rule 14) that the spec existed, named AC-DH4-1/AC-P01-1/AC-DH4-2, and stated exact
   assertion values with no "or"-shaped assertion — including the grep you ran for it. Or, if not,
   what you found and where you stopped.
2. How B-3-6 and B-3-7 settled per ISSUES.md, and what each implied for the tests you wrote. If
   B-3-6 settled FALSE, the F-04 overlap flagged in plain English for human review.
3. Verbatim failure output for every test, with a one-line why for each, and the exact list of
   symbols 3.2-GREEN must create.
4. Confirmation that the D-H2/D-H3 ratchets from 3.1 still pass unchanged.
5. Confirmation that ZERO files under
   /Users/yitzchak.meirovich/Documents/code5/careervp/src/backend/careervp/ and
   /Users/yitzchak.meirovich/Documents/code5/careervp/src/frontend/ were modified
   (`git diff --stat`).
6. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clauses D-H4
  and P-01 in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md:
  update the 3.2-RED row with a plain-English status, the commit, today's date, and anything
  3.2-GREEN must resolve first (or write "none").
```

---

# PROMPT 3.2-GREEN — make them pass

> **Clause:** D-H4, P-01 · **Spec:** [`specs/D-H4-P-01-canonical-artifact-spec.md`](../specs/D-H4-P-01-canonical-artifact-spec.md)
> **Acceptance criteria:** AC-DH4-1, AC-P01-1, AC-DH4-2
> **Claude:** opus/high · **Codex:** gpt-5-codex/high
> (rule 15 — copied verbatim from `redesign-execution-plan.md`'s Wave-3 row 3.2. **Deliberately
> `opus`, not `fable`:** the plan's row says `opus/high`, and rule 18 does not license a fill-in
> session to re-route a step the plan already tiered. See the model note in §3.2 above.)
>
> Run in a **FRESH session** that has not seen 3.2-RED's reasoning. `/clear` is the minimum; a
> separate invocation is preferred. The failing tests are a contract you did not write and **may not
> edit** — that clause is the entire firewall. No relaxing an assertion, no widening an exclusion,
> no `xfail`, no `skip`. If a test looks genuinely *wrong* (not merely inconvenient), STOP and raise
> a §0.3 amendment.
>
> **You are editing the Wave-3 contention hotspot.** `CoreRepository` / `TableRegistry` is what 3.3,
> 3.4 and 3.5 all extend (§2). One open editor at a time; do not start if another Wave-3 step is
> mid-flight against those modules.

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md
and read the 3.2-RED row (and, above it, 3.2-SPEC and 3.1-GREEN). If any left something open — a
B-3-6/B-3-7 decision, the F-04 overlap flag, a symbol list — deal with that FIRST. Confirm the RED
tests exist and FAIL right now, with a real command; do not trust the ledger:

  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit -q -k "dh4 or p01" 2>&1 | tail -40

If they pass, or fail on import/collection errors rather than their own assertions, STOP and say so.
If `test_dh4_cv_tailoring_preserves_vpr_id_null` passes and the 3.2-RED row records it as a B-3-6
regression guard, that ONE is expected — confirm it against the row rather than assuming.

You are implementing clauses D-H4 and P-01 (AC-DH4-1, AC-P01-1, AC-DH4-2). You make the RED tests
pass by writing implementation code ONLY. You may not edit any test file and you may not edit the
spec's RED-test brief. If a test looks genuinely wrong, STOP and raise a §0.3 amendment — never a
quiet edit.

--------------------------------------------------------------------------------
WHAT TO BUILD (from the spec's Fix Plan, as pinned by 3.2-SPEC)
--------------------------------------------------------------------------------
1. Characterization first. Before changing a resolution path, pin today's observable behavior for
   VPR, CV-tailoring, cover-letter and interview-prep artifact ids in NEW characterization tests —
   the technique 3.1-GREEN used (`tests/unit/test_table_registry_characterization.py`). New test
   files are allowed; editing the RED file is not.

2. ONE canonical opaque `artifact_id` per artifact, and status reads routed through it. Extend
   `careervp/dal/core_repository.py` / `careervp/dal/table_registry.py` — they are the key and
   repository authority 3.1 established, and 3.2 does not create a second one. Collapse the
   six-name id ladder in `logic/artifact_dependency_resolver.py::_artifact_id` to exactly the names
   the spec pins.

3. Resolve upstream VPR/CR/CV dependencies THROUGH the repository, never from a raw client-supplied
   key: `cover_letter_handler.py::_resolve_vpr_payload` and both interview-prep resolution paths
   (`_resolve_vpr_from_jobs_table` and its `dal.get_vpr` fallback). Ownership is decided BEFORE the
   read, the refusal is terminal, and both features return the identical pinned status and envelope.

4. If B-3-7 settled FALSE, make the canonical `artifact_id` write authoritative:
   `dal/application_repository.py`'s swallowed step-2 `except Exception: pass` becomes a surfaced
   typed failure in the same shape D-H3 used. A write that silently no-ops cannot underwrite a
   round-trip guarantee. **Do not widen D-H3's clause to cover it — D-H4 owns this.**

5. Public semantics stay byte-stable: `application_id == job_id`, `artifact_id`, and `vpr_id`
   null-vs-absent. Internal keying changes are not API changes — prove it against the oracle
   (/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/F-frontend-oracle-spec.md),
   specifically §3 items 1, 2 and 3, which is this step's Done-when. **No route versioning** — the
   spec's Done-when says none is required, and adding one is a rule-5 stop.

FORWARD-THINKING ONLY (v2.7.0 / `O-3`). Canonical ids only. No migration, no dual-read window, no
backfill, no cutover probe, no legacy-id resolution, no parity harness — there is nothing to import
and nothing to build. A record in a legacy shape is deleted and rewritten. If you find yourself
writing a compatibility path for an old id, STOP: that is the exact family this wave is removing.

OUT OF SCOPE — leave every one of these alone, they belong to a named later step:
  - The three residues 3.1-GREEN recorded (`company_research_store::_legacy_table_name`,
    `dynamo_dal_handler` internal key building, the inner `_legacy_read_cover_letter_by_scan`
    fallback) — 3.5 and a later wave.
  - `infra/` — nothing in 3.2 touches it; the GSI and PK work is 3.4.
  - The D-M god-class split (3.4), request-path Scans (3.3), auth/trial keying (Wave-6 D-H8).
  - Clause F-04 (Wave 4) and the carried-in P-07b / I-05 / I-06 items. Do not fix I-05's red test
    as a side effect.

--------------------------------------------------------------------------------
VERIFY — with fresh evidence, not assertion
--------------------------------------------------------------------------------
  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit -q -k "dh4 or p01" 2>&1 | tail -20      # the 4 RED tests now pass
  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit -q -k "dh2 or dh3" 2>&1 | tail -20      # 3.1's ratchets NOT regressed
  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict
  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit/ tests/integration/ -q 2>&1 | tail -10  # full suite green, zero regressions
  cd "$(git rev-parse --show-toplevel)/src/backend" && make coverage-tests                                             # exit 0; core-branch ratchet held (3.1-GREEN measured core 55.52)
  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit/test_frontend_oracle_schema_emission.py tests/unit/test_route_parity_openapi.py -q 2>&1 | tail -10
  cd "$(git rev-parse --show-toplevel)/src/frontend" && npm run typecheck && npm run test:unit
  cd "$(git rev-parse --show-toplevel)" && uv run python src/backend/scripts/check_scope_lock_integrity.py --base HEAD

P-01's contract verification is `e2e+characterization` and D-H4's is `contract+integration` — a unit
suite alone does not discharge them. Either deploy `CareerVpCrudDevx` (manual-dispatch only, no
merge to `main`) and characterize the two fixed features against the raw invoke URL
`https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/`, or state the undeployed debt
explicitly in the ledger row. §0.5: Wave 2 accumulated four undeployed steps and then had to
reconcile them all at once into the next step's diff. Do not repeat it silently.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. Fresh verbatim pass output for the 4 RED tests, the 3.1 ratchets, the full suite, mypy --strict,
   the coverage gate (with measured numbers), the oracle tests, and the frontend checks.
2. Confirmation that ZERO test files and ZERO spec RED-briefs were modified (`git diff --stat` over
   the test dirs and the spec) — new characterization test files listed separately and named.
3. The exact `CoreRepository` / `TableRegistry` surface 3.2 added, since 3.3 / 3.4 / 3.5 all extend
   the same modules and need to know what is now there.
4. Confirmation the oracle still passes and §3 items 1, 2 and 3 hold — no identifier or
   response-shape drift, and no route versioning added.
5. Deploy status stated explicitly: deployed to `CareerVpCrudDevx` with the characterization result,
   or the undeployed debt named.
6. Any residue you could not clear, enumerated with a named owner step — the ratchet-that-holds
   pattern 3.1-GREEN used. A loosened assertion is a rule-5 stop; an enumerated residue is not.
7. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clauses D-H4
  and P-01 in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow, THEN the technical detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md:
  update the 3.2-GREEN row with a plain-English status, the commit, today's date, deploy status, and
  anything 3.3 / 3.4 / 3.5 must resolve first — in particular the added repository surface and any
  enumerated residue (or write "none").
```

---

## 3.3 — Eliminate request-path Scans

| | |
|---|---|
| **Clause** | D-H7 |
| **Spec** | `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H7-request-path-scans-spec.md` |
| **Acceptance criteria** | AC-DH7-1, AC-DH7-2 |
| **Claude / Codex** | opus/high · gpt-5-codex/high (rule 15 — Claude side verbatim from `redesign-execution-plan.md:314`; Codex side resolved per rule 16 from that row's bare `codex/high` using the spec's `tooling` frontmatter pin, exactly as 3.2 did. **Not Fable — rule 18 forbids routing RED to it.**) |
| **Depends on** | 3.1-GREEN |
| **Deploy target** | `CareerVpCrudDevx` (manual-dispatch only; no merge to `main`) |
| **Rule 7** | **RED and GREEN are separate sessions.** The Wave-0 skeleton said a single session was acceptable for a "contained change"; the 2026-07-29 fill-in **overrides that**, for two reasons stated here so the override is visible rather than inherited: (a) DP-2 below can pull `infra/` into this step, which is not contained; (b) `B-3-8` makes this likely a **guard-rail** step, and a guard-rail is the exact case where one session writes the assertion around whatever the code already does. A separate RED session cannot do that. |
| **Bets** | **`B-3-8`** (added 2026-07-29, pre-settled toward FALSE — see `ISSUES.md`): *there is a live request-path Scan that is 3.3's own to remove.* If false, 3.3 is guard-rail + regression test only. **`B-3-4`** applies only if DP-2 resolves toward `infra/`. |

**In plain English.** Make it impossible for a request path to call DynamoDB `Scan` — so read
latency and cost stop scaling with table size, and one tenant's query can never walk another
tenant's rows. Reconcile and offline-migration scans stay (Wave-2 step 2.1-GREEN settled that
explicitly).

**Read `B-3-8` in `ISSUES.md` before anything else in this step.** The pre-flight inventory found
**three** `.scan(` sites repository-wide and **all three are already owned by other decisions** —
the reconcile scan Wave 2 chose to keep, the legacy cover-letter scan that belongs to 3.5, and the
offline backfill script the spec itself allow-lists. So the honest expectation is that 3.3 removes
nothing and instead *nails the door shut*: a static guard that fails the build when a scan reappears,
plus a GSI-shape assertion. That is a real deliverable, and pretending otherwise is how a step grows
scope to stay interesting.

**The spec is stale and must be pinned before RED (rule 14).** Its Evidence cites
`subscription_repository.py:127-129` as a surviving "money-path scan fallback"; live, that function
already queries `customer-id-index` and the money-path scan was removed in Wave-2 2.1-GREEN. It also
never mentions the two findings that actually give 3.3 content (DP-2 below). Rule 14 forbids a RED
session from pinning its own spec, which is why **3.3-SPEC exists as a separate visible action** —
the same split 3.2 used, for the same reason.

### Two decision points — DEFERRED ON PURPOSE, each with the test that resolves it

Neither is decided here, because neither can be decided honestly from the Wave-0 spec. Both are
**resolved by evidence during 3.3**, and rule 10 requires each deferral to carry a stopping
condition rather than just a home. **Whoever resolves one owes a plain-English explanation in the
`wave-3-status.md` row** — which option, what evidence chose it, and what it means for the steps
that come after. A silently-taken option is a rule-5 stop.

**DP-1 — Does 3.3 touch `CoreRepository` / `TableRegistry` at all?**
This is the §2 serialization question, and it has three possible answers:

| Option | What it means | When it applies |
|---|---|---|
| **A — no touch** | 3.3 adds only a static source guard and an infra/synth assertion. No repository edit. **No serialization conflict; runs fully parallel to 3.4 and 3.5.** | If `B-3-8` settles FALSE — the expected outcome. |
| **B — new write to the module** | A genuine artifacts/core request-path scan exists, so 3.3 adds a keyed query helper to `table_registry.py` / `core_repository.py`. **Serialization lock applies:** one open editor, do not run concurrently with 3.4 or 3.5. | If `B-3-8` settles TRUE *and* the site is on the artifacts/core table. |
| **C — read-only use** | 3.3 calls an *existing* 3.2-era helper to build a replacement query and adds nothing. A dependency, not an edit — **no contention.** | If `B-3-8` settles TRUE and the existing surface already covers the replacement. |

- **Resolved by:** `B-3-8`'s tier-1 inventory, executed in **3.3-SPEC** (its first action).
- **Stopping condition (rule 10):** if 3.3-SPEC cannot classify all three known sites — plus any
  new one — as *kept*, *another step's*, or *3.3's own*, using a decision that already exists in
  `wave-2-status.md`, `wave-3-status.md`, or the spec, then **STOP and escalate**. Do not resolve an
  ambiguous site by assigning it to 3.3; that is how a step annexes 3.5's work.
- **Note:** subscription/billing keying is **not** `TableRegistry`'s (users table, `USER#{id}` /
  `SUBSCRIPTION#CURRENT`), and `B-3-5` parks user/application keying for Wave-6 D-H8. A scan found
  there is Option A regardless.

**DP-2 — Does AC-DH7-1 mean "no Scan in source" or "no Scan permitted by IAM"?**
AC-DH7-1 reads *"when handlers/repositories execute, then DynamoDB Scan is never called"* and does
not say which. The two readings are very different in size, and the live findings force the question:

- `infra/careervp/api_construct.py:941` still grants `dynamodb:Scan` on the artifacts table and its
  `type-index` to a runtime Lambda. Wave-2 2.1-GREEN removed the Scan action from `BillingLambda`
  **only**; this grant survived and nothing tests it.
- CDK's `grant_read_data` / `grant_read_write_data` **include `dynamodb:Scan` implicitly**, and
  `api_construct.py` calls them ~20 times — **live count pinned at 3.3-SPEC: exactly 22.** Under the
  IAM reading, every runtime Lambda currently *can* scan even with zero scans in source. **Confirmed
  live:** these land in the shared role's attached `ServiceRoleArnDefaultPolicy2B096FD3`, which
  carries `dynamodb:Scan` independently of the inline `artifacts_table` statement — so the two
  readings are not merely different in size, they have different *homes* in the template.

| Option | What it means | Cost |
|---|---|---|
| **Source-only** | The guard is static analysis over `handlers/`+`dal/`+`logic/`. `infra/` untouched. **No collision with 3.4.** | Small. Leaves the IAM surface open, which must then be named as enumerated residue with an owner. |
| **Source + the one explicit grant** | Also removes the literal `"dynamodb:Scan"` at `api_construct.py:941`. Touches `infra/`, one line, one synth assertion. | Small, but **takes the `infra/` serialization lock** and needs `B-3-4`'s isolated-template-diff proof. |
| **Source + IAM closure** | Also narrows ~20 (**live: 22**) `grant_*_data` calls to explicit action lists. | **Large, and 3.4 is already reshaping the same file.** Almost certainly belongs in 3.4 or later, not here. |

- **Resolved by:** **3.3-SPEC**, as a pinned decision recorded in the spec's Evidence and Fix Plan.
- **Stopping condition (rule 10):** if 3.3-SPEC resolves toward *Source + IAM closure*, **STOP
  before RED** and hand the IAM half to 3.4 — `api_construct.py` is the file 3.4 already serializes,
  and two steps reshaping it concurrently is the Wave-2 `api_construct.py` incident replayed. Record
  the handoff in both rows.
- **Whichever option is taken,** the untouched remainder is enumerated residue with a named owner
  step (3.1-GREEN's ratchet-that-holds pattern), never silence.

---

# PROMPT 3.3-SPEC — pin the D-H7 assertion values, settle `B-3-8`, resolve DP-1/DP-2 (spec + ISSUES.md only)

> **Clause:** D-H7 · **Spec:** [`specs/D-H7-request-path-scans-spec.md`](../specs/D-H7-request-path-scans-spec.md)
> (full path: `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H7-request-path-scans-spec.md`)
> **Acceptance criteria:** AC-DH7-1, AC-DH7-2 — **pinned, never renumbered, never widened**
> **Claude:** opus/high · **Codex:** gpt-5-codex/high
> (rule 16 — precision authoring against an existing contract. **Not Fable:** rule 18 routes
> precision authoring away from Fable for the same reason it routes RED away, and this session
> writes no implementation.)
>
> **What this session is.** The separate visible action rule 14 requires: a precision edit to one
> spec's Evidence + "RED Tests to Write First" sections, `B-3-8` settled in `ISSUES.md`, and DP-1 and
> DP-2 decided **on evidence, in writing, before a single test exists**. It writes **no test and no
> implementation**. It is the direct analogue of 3.2-SPEC.

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md
and read the 3.1-GREEN row and the 3.2-GREEN row. 3.3 depends on 3.1-GREEN only, but 3.2-GREEN
landed first and left named open items — read them so you do not trip over one.

  1. Confirm 3.1-GREEN's foundation is real, from the interpreter, not the column:
        cd "$(git rev-parse --show-toplevel)" && git log --oneline -8
        cd "$(git rev-parse --show-toplevel)/src/backend" && uv run python -c "from careervp.dal.core_repository import CoreRepository; from careervp.dal.table_registry import TableRegistry; print(sorted(n for n in dir(CoreRepository) if not n.startswith('_')))"
     If either module is missing or unimportable, STOP — 3.3 has no foundation.

  2. Read 3.2-GREEN's open items. Three matter to you and NONE of them are yours to fix:
     (a) the v3.0.0 adversarial review is not discharged — a human owes it;
     (b) 3.2 is UNDEPLOYED debt against CareerVpCrudDevx;
     (c) the residue list with named owners.
     You are a docs-only session: none of these block you, and none of these are yours. Do not
     "help" with any of them.

  3. Confirm the suite is green right now, so 3.3-RED's later failures are unambiguous:
        cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit -q 2>&1 | tail -5

You are performing a PRECISION EDIT on
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H7-request-path-scans-spec.md,
and settling one bet in
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/ISSUES.md.

You may edit EXACTLY those two files, plus the 3.3-SPEC row in wave-3-status.md. You may not touch
any file under /Users/yitzchak.meirovich/Documents/code5/careervp/src/ or
/Users/yitzchak.meirovich/Documents/code5/careervp/infra/, any test, or either
project-scope-lock twin.

--------------------------------------------------------------------------------
WHY THIS SESSION EXISTS (rule 14)
--------------------------------------------------------------------------------
D-H7-request-path-scans-spec.md is a 52-line Wave-0 spec, status: draft. Its three RED-test lines
name behaviors but not values ("assert no .scan( calls outside allow-list" does not say what the
allow-list IS). Its Evidence is provably stale in a way that points the wrong direction. And it
never mentions the IAM surface at all. A RED session cannot legally write tests from it.

HARD BOUNDARY on what pinning means. You may make each RED-test description state exact values,
exact scope, and exact out-of-scope exclusions; you may correct and extend the Evidence section; and
you may record the DP-1/DP-2 decisions in the Fix Plan. You may NOT:
  - add, remove, rename, or renumber an acceptance criterion (AC-DH7-1 and AC-DH7-2 stand),
  - add a fourth RED test,
  - change what D-H7 requires. That is the contract twins' text and a §0.3 amendment.
  - re-introduce anything v2.7.0 removed (no parity harness, no dual-read, no backfill).
If pinning a value turns out to require any of the above, STOP and say which one and why.

--------------------------------------------------------------------------------
STEP 1 — SETTLE B-3-8 (rule 9). This is your FIRST action; everything else depends on it.
--------------------------------------------------------------------------------
Read B-3-8 in ISSUES.md in full — belief, why-it-is-a-bet, tier-1 check, fallback already decided.
Your job is to CONFIRM or REFUTE it live, not re-invent it.

Run the tier-1 check:
    cd "$(git rev-parse --show-toplevel)/src/backend" && grep -rn "\.scan(" careervp/ scripts/
    cd "$(git rev-parse --show-toplevel)/src/backend" && grep -rn "dynamodb:Scan" ../../infra/careervp/

Then classify EVERY hit against a decision that ALREADY EXISTS — in wave-2-status.md,
wave-3-status.md, or the spec — never against your own judgement of what looks like a request path.
The pre-flight (2026-07-29) found exactly three source hits and one IAM hit; confirm each live, and
where live disagrees, THE DELTA IS THE FINDING. Record it; do not quietly adopt either number.

  - subscription_repository.py:415 (scan_active_subscriptions) — Wave-2 2.1-GREEN's row says
    "preserve scan_active_subscriptions and BillingReconcileLambda Scan access". KEPT. Not yours.
  - dynamo_dal_handler.py:800 (legacy_read_cover_letter ValidationException fallback) — request-path
    but legacy; 3.1-GREEN's residue (c) assigns the legacy cover-letter scan family to 3.5. NOT
    YOURS. Do not annex it, however tempting: it is the only site that would make 3.3 a "real" fix,
    and taking it is exactly the scope drift this runbook keeps paying for.
  - scripts/cr_migration_backfill.py:261 — offline; the spec's own Fix Plan item 3 allow-lists
    offline scripts, and v2.7.0 deletes this file at 3.5.

If all sites are owned elsewhere, B-3-8 is FALSE and its pre-decided fallback is IN FORCE: 3.3 ships
as guard-rail + regression test only. Write that into ISSUES.md as the settled status, with the
concrete artifact that settled it. Do NOT treat "the step turned out smaller" as a problem to solve.

If you find a FOURTH site the pre-flight missed, that is the finding of the session: classify it,
and if it is genuinely 3.3's own, B-3-8 is TRUE and the fallback does not fire.

--------------------------------------------------------------------------------
STEP 2 — RESOLVE DP-1 AND DP-2, IN WRITING, ON EVIDENCE
--------------------------------------------------------------------------------
Both are specified in wave-3-prompts.md §3.3 ("Two decision points"), with their options, what
resolves each, and their rule-10 stopping conditions. Read that section, then decide each and record
the decision in the spec's Fix Plan plus the ledger row. Name the OPTION LETTER, the evidence, and
the consequence for later steps. An undecided site is how Wave 2 blocked itself (§0.5).

  DP-1 (does 3.3 touch CoreRepository/TableRegistry?) follows directly from Step 1. If B-3-8 is
  FALSE, the answer is Option A — no touch, no serialization conflict, 3.3 runs parallel to 3.4/3.5.
  Say so explicitly so 3.4 and 3.5 can be scheduled without asking.

  DP-2 (does AC-DH7-1 mean source-only or IAM?) you must decide on cost, and confirm both live
  findings first:
      cd "$(git rev-parse --show-toplevel)/infra" && sed -n '930,950p' careervp/api_construct.py
      cd "$(git rev-parse --show-toplevel)/infra" && grep -c "grant_read_data\|grant_read_write_data" careervp/api_construct.py
  RECOMMENDED, and say why if you depart from it: "Source + the one explicit grant" — the static
  guard over handlers/dal/logic PLUS removing the literal "dynamodb:Scan" at api_construct.py:941.
  It is one line of infra, it closes the one grant that is demonstrably wider than any caller needs,
  and it is provable with a synth assertion. The ~20 implicit grant_*_data calls are NOT in scope:
  3.4 is already reshaping api_construct.py, and two steps in that file concurrently is the Wave-2
  incident replayed. Enumerate the implicit-grant surface as residue owned by 3.4, with the count.
  If you take the one-line infra option, say in the row that 3.3 now holds the infra/ lock for that
  edit and B-3-4's isolated-template-diff technique applies to it.

--------------------------------------------------------------------------------
STEP 3 — PIN THE THREE RED TESTS
--------------------------------------------------------------------------------
The spec names three. Keep exactly three; pin each to exact values.

  test_dh7_no_scan_in_runtime_handlers_or_dal (AC-DH7-1)
      Pin: the exact directories scanned; the exact allow-list, ENUMERATED SITE BY SITE with the
      decision that allow-lists each (not a directory wildcard); whether the check is a
      frozen-baseline ratchet (may shrink, never grow — B-3-5's pattern from 3.1) or an absolute
      zero-occurrences assertion, and WHY that choice fits what 3.3 is actually scoped to satisfy.
      Pin how the scan is performed (AST vs regex) and how a false negative is prevented — a regex
      for ".scan(" misses `getattr(table, 'scan')` and `table.__getattr__`. State the known limits.
      If DP-2 took the infra option, pin the IAM half here too: exactly which policy statement, and
      the exact synth assertion that proves "dynamodb:Scan" is absent from it.

  test_dh7_subscription_lookup_uses_query (AC-DH7-1)
      NOTE THE TRAP: the money-path fix already landed in Wave-2 2.1-GREEN, and
      tests/unit/test_l1_list_endpoints.py:225-276 already asserts query-not-scan on the list paths.
      Pin what this test adds that those do not, or pin it explicitly as a LABELLED REGRESSION GUARD
      over get_subscription_by_customer_id's customer-id-index query. Pin that it must NOT assert
      anything about scan_active_subscriptions, which is deliberately retained — an over-broad
      assertion here would break the reconcile path Wave 2 chose to keep.

  test_dh7_no_status_only_gsi_partition_key (AC-DH7-2)
      Pre-flight found this ALREADY SATISFIED: infra/careervp/api_db_construct.py:384-393 defines
      "status-index" with partition_key=userId and sort_key=status — user-scoped, high-cardinality,
      status only in the sort position. The name is a red herring. CONFIRM live, then pin this as a
      LABELLED REGRESSION GUARD that passes on day one, enumerating every GSI in
      api_db_construct.py by name and asserting the shape of each partition key. Pin the exact list
      of index names so a newly-added GSI fails the test rather than slipping past it.

Every test that passes on day one is labelled a guard IN THE SPEC, with the reason — B-3-6's
handling. A guard is not a failure of the step; an unlabelled guard is.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. The tier-1 inventory: every .scan( and dynamodb:Scan hit, with its classification and the
   EXISTING decision that owns it. Deltas from the pre-flight's four hits called out explicitly.
2. B-3-8 settled TRUE or FALSE in ISSUES.md, with the concrete settling artifact, and whether its
   pre-decided fallback is in force.
3. DP-1 and DP-2 each resolved, by option letter, with the evidence and the consequence for 3.4/3.5.
   If DP-2 resolved toward IAM closure, the rule-10 STOP and the handoff to 3.4 instead.
4. The edited Evidence and "RED Tests to Write First" sections, quoted in full, with every assertion
   value pinned, every allow-list entry enumerated, and every day-one-green test labelled a guard.
5. Explicit confirmation that AC-DH7-1 and AC-DH7-2 are unchanged in id, count, and text.
6. Confirmation that ZERO files under /Users/yitzchak.meirovich/Documents/code5/careervp/src/ and
   /Users/yitzchak.meirovich/Documents/code5/careervp/infra/ were modified (`git diff --stat`).
7. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clause D-H7 in
  project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md:
  add a 3.3-SPEC row with a plain-English status, the commit, today's date, and what 3.3-RED must
  resolve first — in particular how B-3-8 settled and which option DP-1 and DP-2 took, each in one
  sentence a non-engineer could follow.
```

---

# PROMPT 3.3-RED — request-path Scan elimination (tests only)

> **Clause:** D-H7 · **Spec:** [`specs/D-H7-request-path-scans-spec.md`](../specs/D-H7-request-path-scans-spec.md)
> (full path: `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H7-request-path-scans-spec.md`)
> **Acceptance criteria:** AC-DH7-1, AC-DH7-2
> **Claude:** opus/high · **Codex:** gpt-5-codex/high
> (rule 15/16 — Claude side verbatim from `redesign-execution-plan.md:314`; Codex side resolved from
> that row's bare `codex/high` per rule 16 and the spec's `tooling` frontmatter pin.
> **Not Fable — rule 18 forbids routing RED to it.**)
>
> **Rule 7 applies** — see the override note in §3.3's field table. RED and GREEN are two different
> sessions. This one writes tests only and carries an **absolute prohibition** on touching
> implementation files.
>
> **Requires 3.3-SPEC to have landed.** Without the precision edit there is no legal set of
> assertion values, no settled `B-3-8`, and no DP-1/DP-2 decision — the standing check below stops.

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md
and read the 3.3-SPEC row AND the 3.1-GREEN row. If either left anything open, deal with that first.

  1. Confirm 3.1-GREEN's foundation is real, from the interpreter, not the column:
        cd "$(git rev-parse --show-toplevel)/src/backend" && uv run python -c "from careervp.dal.core_repository import CoreRepository; from careervp.dal.table_registry import TableRegistry; print('importable')"

  2. Confirm the suite is green before you add a failing test:
        cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit -q 2>&1 | tail -5

  3. Confirm the ratchets from 3.1 and the contracts from 3.2 still hold — you must not regress them:
        cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit -q -k "dh2 or dh3 or dh4 or p01" 2>&1 | tail -10

  4. NOTE THE TWO TEST ROOTS. `pytest tests/unit -k "dh7"` will NOT see the synth-based D-H7 tests.
     Whenever you or a later step select the D-H7 suite, name both roots explicitly:
        cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit tests/infrastructure -q -k "dh7" 2>&1 | tail -20
     (plus `cd infra && uv run pytest tests/ -q -k "dh7"` if you homed the synth tests there instead).
     Reporting a partial selector as "all D-H7 tests pass" is a false green.

BEFORE WRITING ANY TEST (rule 14): confirm, with a real command, that
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H7-request-path-scans-spec.md
exists, that its "RED Tests to Write First" section names tests covering AC-DH7-1 and AC-DH7-2, and
that each cited test states exact assertion values. Specifically:
  - confirm no ASSERTION VALUE is "or"-shaped — i.e. no test is told to accept either of two
    outcomes ("assert the key is userId or user_id"), which is the vagueness rule 14 exists to catch.
    **Check assertion values, NOT the bare word.** A grep for `\bor\b` over this section is the WRONG
    check and will fire on ordinary prose: the pinned section legitimately contains "annexing 3.5's
    site or dropping dal/ from scope", "a variable, or eval/exec", and — quoting an option it
    explicitly REJECTS — "every PK is user-scoped or high-cardinality". The test name
    `test_dh7_no_scan_in_runtime_handlers_or_dal` and AC-DH7-2's own text also contain the word. Seven
    prose hits were confirmed at pinning time; **none is an assertion, and none is a reason to stop.**
    Read the value each assertion pins and judge whether it names one outcome or a choice.
  - confirm the allow-list is ENUMERATED SITE BY SITE, not a directory wildcard. An unenumerated
    allow-list is an undefined placeholder and fails rule 14 check 3 exactly as a vague value does.
If either fails, 3.3-SPEC has NOT landed properly. STOP. Do not pin the values yourself inside this
session — that is 3.3-SPEC's separate visible action, and folding it in here is the precise thing
rule 14 forbids.

You are implementing clause D-H7, acceptance criteria AC-DH7-1 and AC-DH7-2, from the spec above.

You are the RED session. You write TEST FILES ONLY. You may not create or edit any file under
/Users/yitzchak.meirovich/Documents/code5/careervp/src/backend/careervp/,
/Users/yitzchak.meirovich/Documents/code5/careervp/src/frontend/, or
/Users/yitzchak.meirovich/Documents/code5/careervp/infra/careervp/ except to READ it. Not
temporarily, not "to see if it works." If you believe an implementation file must change, write the
test that proves it and stop.

--------------------------------------------------------------------------------
FIRST — read how B-3-8 settled, and which options DP-1 and DP-2 took
--------------------------------------------------------------------------------
B-3-8 is in
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/ISSUES.md.
DP-1 and DP-2 are recorded in the 3.3-SPEC ledger row and the spec's Fix Plan. Read all three. Your
job is to write the tests the settled position implies, not to re-litigate any of them.

  - If B-3-8 settled FALSE (expected): 3.3 is a GUARD-RAIL STEP. Some or all of your tests will pass
    on day one. Write them, label each in its docstring as a guard WITH THE REASON, and report them
    as such in the rule-13 block below. Do not bend a guard into failing, do not delete it, and do
    not treat its green as evidence that D-H7 is done. A guard that fails when a scan reappears is
    the deliverable.
  - If DP-2 took the source-only option, you write NO infra test for IAM. If it took "source + the
    one explicit grant", you write the synth assertion the spec pins for api_construct.py:941 — and
    that one WILL fail today, because the grant is live.
  - If DP-1 took Option A (expected), you add nothing to CoreRepository/TableRegistry and there is no
    serialization lock to hold.

--------------------------------------------------------------------------------
THEN — write these tests, and only these (from the spec's pinned "RED Tests to Write First")
--------------------------------------------------------------------------------
Three tests. The spec is authoritative for every assertion value after 3.3-SPEC's precision edit —
READ IT. Do not re-derive values from the summaries below, and do not widen them. The summaries
exist so you can tell whether you are reading the right section, not so you can skip it.

  test_dh7_no_scan_in_runtime_handlers_or_dal        [TWO PARTS, ONE TEST — do not split it]
      Part A — static analysis over the exact directories the spec pins, asserting no scan call
      survives outside the spec's ENUMERATED allow-list (exactly two entries). Use the detection
      technique the spec pins (AST — a regex for ".scan(" misses getattr-style access AND
      false-positives on ScanIndexForward and on log strings) and state its known limits in the
      docstring. Day-one green: label it a guard. The spec pins a FROZEN-BASELINE RATCHET, not an
      absolute zero-occurrences assertion — do not "tighten" it to zero, which is unsatisfiable
      without annexing 3.5's site.
      Part B — the IAM half, because DP-2 resolved AC-DH7-1 to mean source AND the one explicit
      grant. This is the ONLY assertion in 3.3 that is red today. **Read the spec's ⛔ block before
      writing it:** assert on the inline `artifacts_table` statement ONLY. Do NOT union it with the
      role's attached DefaultPolicy — Scan is present there too, from the 22 implicit grants that are
      3.4's, so a union assertion can never go green in 3.3 and GREEN may not edit your test.
      Both parts cite AC-DH7-1. **Part B is NOT a fourth test** — the spec keeps exactly three.

  test_dh7_subscription_lookup_uses_query
      Exactly what the spec pins, and NOT MORE. It must NOT assert anything about
      scan_active_subscriptions: that scan is deliberately retained for BillingReconcileLambda per
      Wave-2 2.1-GREEN, and an over-broad assertion here silently breaks the reconcile path. Keep
      scan.assert_not_called() bounded to the single get_subscription_by_customer_id invocation. Cite
      AC-DH7-1. Day-one green, and a DELIBERATE DUPLICATE of AC-P15-1's existing coverage at
      tests/unit/test_p14_p15_billing_idempotency.py:198-220 — label it a guard whose added value is
      AC ownership, not new coverage. Say that plainly in the docstring rather than dressing it up.

  test_dh7_no_status_only_gsi_partition_key
      Synth the tables and assert EXACTLY what the spec pins, which is NOT "every partition key is
      user-scoped, high-cardinality, or sparse". That broader assertion was considered and REJECTED
      at 3.3-SPEC: `entity-index` has partition key `knowledgeType`, so it would FAIL on day one and
      could only be made green by reshaping the knowledge table — which belongs to D-M5 (3.4) and
      Q-07 (Wave 4). Writing it is a rule-5 scope-drift stop.
      The pinned assertions are: (a) no GSI's partition key is `status` or `status#`-prefixed — the
      prohibition the clause actually states; and (b) set equality against the frozen 8-entry
      (IndexName, KeySchema) baseline, so a NEWLY ADDED GSI fails rather than slipping past. Use
      resource type AWS::DynamoDB::GlobalTable (tables are TableV2; AWS::DynamoDB::Table counts ZERO
      and asserting against it passes vacuously) and assert the resource set is non-empty first.
      `entity-index` is a named, owned exception recorded IN the baseline — enumerated, not hidden.
      Expected to pass on day one — label it a guard. Cite AC-DH7-2.

WHERE THE TEST FILES GO — pin this, because the D-H7 suite spans TWO pytest roots and a careless
selector silently skips half of it:
  - Part A and test_dh7_subscription_lookup_uses_query are pure Python / mock →
    src/backend/tests/unit/test_dh7_request_path_scans.py
  - Part B and test_dh7_no_status_only_gsi_partition_key need a CDK synth →
    src/backend/tests/infrastructure/test_dh7_scan_iam_and_gsi_shape.py
    (that is the established home for synth-based IAM contracts — see the P-15 precedent
    test_p15_billing_iam.py, whose parent+nested-stack template collection technique you SHOULD
    reuse; only its action-set BREADTH is wrong for D-H7, per the spec's ⛔ block.)
  - `infra/tests/infrastructure/` is the alternative home and its conftest offers ready-made
    `synthesized_template` / `features_template` fixtures. Either root is acceptable; PICK ONE,
    state which, and make sure the verification selector below actually reaches it.
  - Writing under src/backend/tests/ and infra/tests/ is permitted. The prohibition covers
    src/backend/careervp/, src/frontend/, and infra/careervp/ — implementation, not tests.

OUT OF SCOPE, and say so explicitly in the test module docstring so 3.3-GREEN inherits the boundary:
  - `dal/dynamo_dal_handler.py:800` — the legacy cover-letter ValidationException scan fallback.
    It IS a request path and it IS a real scan, and it belongs to **3.5** (D-H9 legacy-path
    demolition; 3.1-GREEN residue (c)). Do not write a test that would force its removal here.
  - `dal/subscription_repository.py:415` (`scan_active_subscriptions`) — retained on purpose.
  - `scripts/cr_migration_backfill.py:261` — offline; allow-listed, and deleted at 3.5.
  - The **22** implicit `grant_read_data` / `grant_read_write_data` Scan grants in `api_construct.py`
    (live count pinned at 3.3-SPEC; the earlier "~20" was an estimate) — 3.4's, per DP-2. Do not
    narrow them here, and do not write an assertion that would require them narrowed.
  - The three residues 3.1-GREEN recorded, and everything 3.2-GREEN listed with a named owner.
  - Auth/trial/user-pool keying (Wave-6 D-H8) and the D-M god-class split (3.4).

RULE 13 — a test that has not been observed to fail is not a test. This step needs MORE care here
than 3.1 or 3.2 did, because most of these tests are expected to pass on day one, and rule 13's own
incident (`api-client.test.ts`) was exactly a permanently-green test nobody had watched fail.

For EVERY test that passes on day one, you must prove it CAN fail and paste the failure output
verbatim. **Prove it WITHOUT editing any implementation file** — the prohibition above is absolute and
has no "temporarily" exemption, so structure each guard as a pure function over an input you control
and feed it a poisoned input. All three are provable this way:
  - the static guard (Part A): write a throwaway `.py` file containing `table.scan(...)` into pytest's
    `tmp_path` and point the AST detector at that directory. It must report the site. Also feed it
    `getattr(table, 'scan')(...)`, `fn = table.scan`, and `get_paginator('scan')` to prove forms 2-4
    are caught, plus `ScanIndexForward=False` and a `"list-scan fallback"` log string to prove neither
    false-positives. No source file is touched.
  - the GSI test: pass the assertion helper a hand-built template dict whose GSI has
    `KeySchema=[{'AttributeName':'status','KeyType':'HASH'}]` and confirm it fails; and a dict with a
    9th index to confirm the frozen-baseline set equality fails on an addition.
  - the subscription test: no mutation needed anywhere — configure the MagicMock so the repository's
    call lands on `scan` instead of `query` (that is the whole point of the double) and confirm the
    assertion fails.
Paste all three. An unmutated guard is decorative, and this repo has shipped one before. Factor each
detector so it takes its input as a parameter; a guard that can only run against the real tree is a
guard you cannot prove, and that is a design smell, not an excuse.

Do NOT resolve a missing symbol with a skip-guard — a skipped test is not a red test. Attempt the
import/attribute access inside the test, catch it, and fail on your own message naming the exact
symbol, e.g. `pytest.fail('AC-DH7-1: <symbol> not available at <module>')`.

No real network calls in any test — moto/stub/synth only. Secrets stay under the P-06 rules.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. Confirmation (rule 14) that the spec existed, named AC-DH7-1/AC-DH7-2, stated exact assertion
   values with no "or"-shaped assertion, and carried an ENUMERATED allow-list — including the greps
   you ran. Or, if not, what you found and where you stopped.
2. How B-3-8 settled and which options DP-1/DP-2 took, and what each implied for the tests you wrote.
3. For each test: RED or day-one-green guard. For every RED, verbatim failure output and a one-line
   why. For every guard, the verbatim mutation-failure output proving it can fail, plus confirmation
   the mutation was reverted and `git diff --stat` is clean over the implementation trees.
4. The exact list of symbols (if any) 3.3-GREEN must create.
5. Confirmation that the 3.1 ratchets and 3.2 contracts still pass unchanged.
6. Confirmation that ZERO files under src/backend/careervp/, src/frontend/, and infra/careervp/ were
   modified (`git diff --stat`).
7. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clause D-H7 in
  project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md:
  update the 3.3-RED row with a plain-English status, the commit, today's date, which tests are
  guards versus RED, and anything 3.3-GREEN must resolve first (or write "none").
```

---

# PROMPT 3.3-GREEN — make them pass

> **Clause:** D-H7 · **Spec:** [`specs/D-H7-request-path-scans-spec.md`](../specs/D-H7-request-path-scans-spec.md)
> **Acceptance criteria:** AC-DH7-1, AC-DH7-2
> **Claude:** opus/high · **Codex:** gpt-5-codex/high
> (rule 15 — Claude side verbatim from `redesign-execution-plan.md:314`. **Deliberately `opus`, not
> `fable`:** the plan's row says `opus/high`, and rule 18 does not license a fill-in session to
> re-route a step the plan already tiered.)
>
> Run in a **FRESH session** that has not seen 3.3-RED's reasoning. `/clear` is the minimum; a
> separate invocation is preferred. The failing tests are a contract you did not write and **may not
> edit** — that clause is the entire firewall. No relaxing an assertion, no widening an allow-list,
> no `xfail`, no `skip`. If a test looks genuinely *wrong* (not merely inconvenient), STOP and raise
> a §0.3 amendment.
>
> **Whether you hold the contention lock depends on DP-1** (§3.3). Under Option A — the expected
> outcome — 3.3 touches neither `CoreRepository` nor `TableRegistry`, and runs safely in parallel
> with 3.4/3.5. Under Option B you hold the lock: one open editor, do not start if another Wave-3
> step is mid-flight against those modules. **Read the 3.3-SPEC row and know which one you are
> before you write a line.**

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md
and read the 3.3-RED row (and, above it, 3.3-SPEC and 3.1-GREEN). If any left something open — a
B-3-8 outcome, a DP-1/DP-2 option, a symbol list, a guard-versus-RED classification — deal with that
FIRST. Confirm the current state with a real command; do not trust the ledger:

  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit tests/infrastructure -q -k "dh7" 2>&1 | tail -40

**Name BOTH roots.** The D-H7 suite spans `tests/unit/` (static guard + subscription) and
`tests/infrastructure/` (the IAM synth assertion + the GSI shape test); if 3.3-RED homed the synth
tests in `infra/tests/` instead, run `cd infra && uv run pytest tests/ -q -k "dh7"` as well. A
selector that reaches only `tests/unit/` will show you a clean pass while the one genuinely-red test
was never collected — read the 3.3-RED row for where the files landed and confirm the collected count
matches.

Expect a MIX: the tests 3.3-RED classified as day-one guards pass, and only the tests it classified
as RED fail. Check that mix against the 3.3-RED row rather than assuming.
  - If a test the row calls RED is passing, STOP — the stimulus is wrong, not the codebase correct.
  - If a test the row calls a guard is FAILING, STOP — something regressed between RED and now.
  - If EVERY dh7 test passes and the row says so (B-3-8 FALSE + DP-2 source-only), then this GREEN
    session has no failing test to fix. That is a legitimate outcome, not a problem to solve by
    inventing work: verify, record, and close. Do NOT go find a scan to remove.

You are implementing clause D-H7 (AC-DH7-1, AC-DH7-2). You make the RED tests pass by writing
implementation code ONLY. You may not edit any test file and you may not edit the spec's RED-test
brief. If a test looks genuinely wrong, STOP and raise a §0.3 amendment — never a quiet edit.

--------------------------------------------------------------------------------
WHAT TO BUILD (from the spec's Fix Plan, as pinned by 3.3-SPEC)
--------------------------------------------------------------------------------
1. Whatever the RED tests actually demand, and nothing else. Under the expected outcome (B-3-8
   FALSE) that is: the static guard is already satisfied by the source tree, and the only genuine
   failure is DP-2's one-line infra edit — remove the literal "dynamodb:Scan" action from the
   artifacts_table policy statement at infra/careervp/api_construct.py:941, leaving PutItem,
   GetItem, UpdateItem, DeleteItem, Query intact on the table and its type-index.

2. If DP-1 took Option B, add the keyed query helper to
   careervp/dal/table_registry.py / careervp/dal/core_repository.py — they are the key and
   repository authority 3.1 established and 3.2 extended, and 3.3 does not create a second one.

3. Public semantics stay byte-stable. Replacing a Scan with a Query changes internal access, never
   the response shape. Prove it against the oracle
   (/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/F-frontend-oracle-spec.md),
   §3 items 1, 2 and 3. **No route versioning** — adding one is a rule-5 stop.

BEFORE THE INFRA EDIT, if DP-2 put one in scope — prove zero stateful replacement with the ISOLATED
TEMPLATE DIFF, not a live `cdk diff` (§0.5, W2 2.3-root-cause, and B-3-4's named technique):
    cd "$(git rev-parse --show-toplevel)/infra" && ENVIRONMENT=devx uv run cdk synth CareerVpCrudDevx > /tmp/after.json
    cd "$(git rev-parse --show-toplevel)" && git stash
    cd "$(git rev-parse --show-toplevel)/infra" && ENVIRONMENT=devx uv run cdk synth CareerVpCrudDevx > /tmp/before.json
    cd "$(git rev-parse --show-toplevel)" && git stash pop
    diff /tmp/before.json /tmp/after.json
An IAM policy-action removal must show as an IAM-only diff with ZERO stateful resource changes. If
the diff touches a table, a GSI, the RestApi, or the Cognito pool, STOP — the two IMMUTABLE laws are
in play and this is no longer a one-line change.

FORWARD-THINKING ONLY (v2.7.0 / O-3). No migration, no dual-read, no backfill, no cutover.

OUT OF SCOPE — leave every one of these alone; each belongs to a named later step:
  - dal/dynamo_dal_handler.py:800, the legacy cover-letter scan fallback — **3.5**. This is the one
    that will tempt you, because removing it would make this step feel substantial. It is 3.5's, it
    is gated on 3.5's retirement-register evidence, and taking it here is a rule-5 stop.
  - dal/subscription_repository.py:415 (scan_active_subscriptions) — retained on purpose (Wave-2
    2.1-GREEN). Removing it breaks BillingReconcileLambda.
  - scripts/cr_migration_backfill.py — offline, allow-listed, deleted at 3.5.
  - The **22** implicit grant_*_data Scan grants in api_construct.py — 3.4's, per DP-2. They put
    dynamodb:Scan in the shared role's ATTACHED DefaultPolicy, which is why RED's IAM assertion is
    scoped to the inline artifacts_table statement only. Removing line 941 does NOT clear the union,
    and it is not supposed to. Do not "finish the job" by narrowing them — that is 3.4's file lock.
  - The D-M god-class split and all other infra/ work (3.4); auth/trial keying (Wave-6 D-H8);
    F-04 (Wave 4); the carried-in P-07b / I-05 / I-06. Do not fix I-05's red test as a side effect.

--------------------------------------------------------------------------------
VERIFY — with fresh evidence, not assertion
--------------------------------------------------------------------------------
  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit tests/infrastructure -q -k "dh7" 2>&1 | tail -20  # BOTH ROOTS — the D-H7 tests pass
  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit -q -k "dh2 or dh3 or dh4 or p01" 2>&1 | tail -20  # 3.1 ratchets + 3.2 contracts NOT regressed
  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit/test_l1_list_endpoints.py -q 2>&1 | tail -10      # the pre-existing no-scan list tests still pass
  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit/test_p14_p15_billing_idempotency.py -q 2>&1 | tail -10  # AC-P15-1 money-path scan test (spec Done-when)
  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run ruff format . && uv run ruff check --fix . && uv run mypy careervp --strict
  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit/ tests/integration/ tests/infrastructure/ -q 2>&1 | tail -10   # full suite; tests/infrastructure/ is where the D-H7 synth tests live — omitting it is a false green
  cd "$(git rev-parse --show-toplevel)/src/backend" && make coverage-tests                                                        # exit 0; core-branch ratchet held (3.2-GREEN measured core 55.79)
  cd "$(git rev-parse --show-toplevel)/src/backend" && uv run pytest tests/unit/test_frontend_oracle_schema_emission.py tests/unit/test_route_parity_openapi.py -q 2>&1 | tail -10
  cd "$(git rev-parse --show-toplevel)" && uv run python scripts/ci/check_scope_lock_integrity.py --base HEAD   # NOTE: scripts/ci/, NOT src/backend/scripts/ — the old path in this runbook did not exist
If the infra edit is in scope, additionally:
  cd "$(git rev-parse --show-toplevel)/infra" && uv run pytest tests/ -q 2>&1 | tail -10
  cd "$(git rev-parse --show-toplevel)" && uv run python src/backend/scripts/validate_naming.py --path infra --strict

D-H7's verification tier is in the clause — read it, and if it is not satisfied by the unit and
synth suites alone, either deploy CareerVpCrudDevx (manual-dispatch only, no merge to `main`) and
characterize against the raw invoke URL
https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/, or state the undeployed debt
explicitly in the ledger row. **3.2-GREEN already left undeployed debt as Wave-3's first** — its row
says "do not let it accumulate as Wave 2 did." If you also do not deploy, say so plainly and say
that the debt is now two steps deep. Do not let the count go unstated.

--------------------------------------------------------------------------------
OUTPUT REQUIRED
--------------------------------------------------------------------------------
1. Fresh verbatim output for the D-H7 tests, the 3.1/3.2 ratchets, the pre-existing list-endpoint
   no-scan tests, the full suite, mypy --strict, the coverage gate (with measured numbers), the
   oracle tests, and — if infra was touched — the infra suite and naming check.
2. Confirmation that ZERO test files and ZERO spec RED-briefs were modified (`git diff --stat` over
   the test dirs and the spec); any new characterization test files listed separately and named.
3. If infra was touched: the isolated before/after template diff, quoted, showing an IAM-only change
   with zero stateful replacement, and explicit confirmation the RestApi and Cognito pool logical
   ids are byte-stable.
4. The exact CoreRepository / TableRegistry surface 3.3 added — or an explicit statement that it
   added none (Option A), so 3.4 and 3.5 know the module is untouched and unlocked.
5. Confirmation the oracle still passes and §3 items 1, 2 and 3 hold — no identifier or
   response-shape drift, no route versioning added.
6. Deploy status stated explicitly: deployed to CareerVpCrudDevx with the characterization result,
   or the undeployed debt named AND the running count of undeployed Wave-3 steps.
7. Any residue you could not clear, enumerated with a named owner step — in particular the surviving
   scan sites and the implicit IAM grant surface, each with its owner and count. A loosened
   assertion is a rule-5 stop; an enumerated residue is not.
8. A git commit message.

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) clause D-H7 in
  project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow, THEN the technical detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md:
  update the 3.3-GREEN row with a plain-English status, the commit, today's date, deploy status, and
  anything 3.4 / 3.5 must resolve first — in particular whether CoreRepository/TableRegistry was
  touched (DP-1), whether the infra/ lock was taken (DP-2), and the enumerated residue with owners
  (or write "none").
```

---

## 3.4 — Seams bundle: god-class split, dual-key CV write, minimized GSI, retire userEmail PK, access-pattern doc

| | |
|---|---|
| **Clause** | D-M1, D-M2, D-M3, D-M5, D-M6, D-Q |
| **Spec** | `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-M-seams-bundle-spec.md` |
| **Acceptance criteria** | (read from the spec at fill-in — this is a multi-clause bundle; map each AC to its D-M* clause) |
| **Claude / Codex** | opus/high · gpt-5-codex/high |
| **Depends on** | 3.1-GREEN |
| **Deploy target** | `CareerVpCrudDevx` (manual-dispatch only; no merge to `main`) — **touches `infra/` (GSI + PK), highest blast radius in the wave** |
| **Rule 7** | RED and GREEN separate — the `userEmail` PK retirement is stateful infra (D-M2/D-M5 are canonical-shape rewrites, **not** migration cutovers — v2.7.0/`O-3`) |
| **Bets** | `B-3-4` (GSI/PK changes stay under the CFN ceiling and cause ZERO stateful replacement — isolated synth-template diff per change, never a single replacing change) — `B-3-1` **retired** at scope-lock v2.7.0, so D-M2/D-M5 are not parity-gated |

**In plain English.** Split the god-class read/write path behind `CoreRepository`, stop the dual-key
CV write, minimize the GSI, retire the `userEmail` primary key, and produce the access-pattern doc
(D-M6) that proves every §1a endpoint and every §1b/§1c async path maps to a named Query/GSI with
zero Scan — including status-by-`artifact_id` and a sparse in-flight index. D-M6 is a hard dependency
of the Wave-6 D-H8 single-table collapse; get it right here. Serialize all `infra/` edits.

**Zero-replacement proof uses the ISOLATED template diff, not a live `cdk diff`** (§0.5, W2
2.3-root-cause): `ENVIRONMENT=devx cdk synth CareerVpCrudDevx` at HEAD, then again with the change
stashed, and diff the two synthesized templates directly — no live stack involved. Wave 2 lost a
session to a live diff reporting six stacks of drift that turned out to be pre-existing devx
staleness unrelated to the change under test. Deploy `CareerVpCrudDevx` per infra-touching change
rather than accumulating undeployed debt; if you do not deploy, say so in the ledger row.

---

## 3.5 — Legacy-path demolition, gated by a retirement register

| | |
|---|---|
| **Clause** | D-H9 |
| **Spec** | `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H9-legacy-path-demolition-spec.md` (adopted 2026-07-27 at scope-lock v2.7.0; the CR-migration spec it replaced is deleted) |
| **Acceptance criteria** | AC-DH9-1, AC-DH9-2, AC-DH9-3 |
| **Claude / Codex** | fable/high · gpt-5-codex/high (rule 15 — from `redesign-execution-plan.md` row 3.5. **Fable per rule 18:** multi-file, irreversible, against a pinned spec. Read rule 18's prompt-shape guidance before filling this in — goal and constraints up front in one turn, no step-by-step choreography, rules and gates verbatim.) |
| **Depends on** | 3.1-GREEN, 3.2, 3.3, 3.4 — **all four**, because every deletion cites a positive proof owned by an earlier step. Do not run this early. |
| **Deploy target** | `CareerVpCrudDevx` (manual-dispatch only; no merge to `main`) |
| **Rule 7** | RED and GREEN separate — irreversible deletion of legacy read paths |
| **Bets** | none — `B-3-1` and `B-3-3` were **both retired** at scope-lock v2.7.0 (no harness, no backfill). The demolition gate asks "does anything still read this?", not "how many items are there?" |

**In plain English.** Demolish every legacy read path, dual-shape write, overloaded table-name
variable, and migration script — each removed **only** on evidence that nothing still depends on it
(fault injection for error-path items, an observed zero hit count for flag-gated items, a source scan
plus a canonical-only read test for static items). Legacy CR items are **deleted, not backfilled**
(v2.7.0/`O-3`). This closes the dual-read-fallback family that is the root of the P-01 drift.
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
`/Users/yitzchak.meirovich/Documents/code5/careervp/docs/evidence/`, and gives the same answer twice from a cold
start. It must cover, at minimum: the 4 D-H2/D-H3 tests plus every D-H4/P-01/D-H7/D-M*/D-H9 test
green; the oracle green
with the legacy-`artifact_id` probe (proving pre-migration ids still resolve); `scope-diff.py` exit 0
with no orphan specs; `cdk diff` showing zero stateful replacement for the 3.4 GSI/PK changes; and a
live devx count confirming the CR legacy read path is retired (3.5). Checks that genuinely need a
human print `HUMAN REQUIRED` and exit non-zero until their evidence file exists — six honest checks
beat eight pretended ones.

**Build it by parameterizing the existing script, not by forking it.**
`/Users/yitzchak.meirovich/Documents/code5/careervp/src/backend/scripts/wave_gate.py` already
implements rule 12 correctly — one command, dated evidence under `docs/evidence/`, non-zero exit on
any failure, four honest states (PASS / FAIL / HUMAN_REQUIRED / RECORDED), and pure verdict logic
unit-tested to fail on purpose. But it hardcodes `WAVE2_BETS`, `WAVE2_CLAUSES`, and a
`wave2-gate-<stamp>.json` filename. Add a `--wave` parameter and per-wave clause/bet tables; do
**not** create `wave3_gate.py`. A forked gate script drifts from the original, and then two scripts
disagree about what a wave close means.

**Re-read all eight `B-3-*` bets** at the GATE (rule 9) and record each as settled TRUE/FALSE with
the concrete artifact that settled it, in `wave-3-status.md`. The count has grown twice since this
line was written — `B-3-6`/`B-3-7` at 3.2-SPEC and `B-3-8` at the 3.3 fill-in — so count them in
`ISSUES.md` rather than trusting this number. Retired bets (`B-3-1`, `B-3-3`) are re-read too: rule
9 keeps them precisely so a vanished bet is not mistaken for an unsettled one. Only then may Wave 4
be authorized.

**Also re-check the tooling, not just its output** (§0.5, W0): `scope-diff.py`'s hardcoded
`--tests-dir` default made the Wave-0 GATE unpassable in a way that looked like a clean run.
Confirm the gate's checks are actually scanning what they claim to scan.
