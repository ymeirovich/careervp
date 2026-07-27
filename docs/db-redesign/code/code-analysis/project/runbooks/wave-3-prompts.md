# Wave 3 — DB seams (copy-paste runbook)

> **Generated:** 2026-07-26, against
> `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/redesign-execution-plan.md`
> (Wave-3 table, rows 3.1–3.5) and `project-scope-lock.yaml`. **Authored AHEAD of the Wave-2 GATE
> by explicit human decision** — authoring was gate-safe (no code, no test, no deploy crossed the
> barrier). Wave 2 has since passed; see the authorization note below and in
> [`wave-3-status.md`](./wave-3-status.md).
>
> **Branch:** `db-redesign` · **Deploy target: `CareerVpCrudDevx`** (not `CareerVpCrudDev`)
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
  key authority that 3.2/3.4/3.5 all build on. The spec is explicit: D-H2/D-H3 "must precede D-H4,
  D-H7, D-M*, D-H9, and P-01."
- After 3.1-GREEN, 3.2 / 3.3 / 3.5 touch **different feature read paths** and can be filled in and
  run in parallel — but each edits `CoreRepository`, so coordinate ownership (one open editor at a
  time) exactly as §2 warns.
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
| **Acceptance criteria** | (read from the spec's "RED Tests to Write First" / "Acceptance Criteria" at fill-in; do not invent) |
| **Claude / Codex** | opus/high · gpt-5-codex/high |
| **Depends on** | 3.1-GREEN (needs `CoreRepository` + `TableRegistry`) |
| **Deploy target** | `CareerVpCrudDevx` (manual-dispatch only; no merge to `main`) |
| **Rule 7** | RED and GREEN separate — this is the P-01 fix, a migration cutover |
| **Bets** | none — `B-3-1` retired at scope-lock v2.7.0 (no harness, no migration, no legacy-id probe) |

**In plain English.** Store a canonical `artifact_id` and its resolved upstream ids so cover-letter
and interview-prep stop failing to find their VPR/CV. **Canonical ids only — no dual-read window, no
cutover probe, no harness, no legacy-id resolution** (v2.7.0/`O-3`: the data is disposable, so there
is no pre-migration `artifact_id` to keep resolving).

---

## 3.3 — Eliminate request-path Scans

| | |
|---|---|
| **Clause** | D-H7 |
| **Spec** | `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/D-H7-request-path-scans-spec.md` |
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

**Re-read all five `B-3-*` bets** at the GATE (rule 9) and record each as settled TRUE/FALSE with the
concrete artifact that settled it, in `wave-3-status.md`. Only then may Wave 4 be authorized.

**Also re-check the tooling, not just its output** (§0.5, W0): `scope-diff.py`'s hardcoded
`--tests-dir` default made the Wave-0 GATE unpassable in a way that looked like a clean run.
Confirm the gate's checks are actually scanning what they claim to scan.
