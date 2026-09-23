# HANDOFF 15 — after J9: the running system, and the V1 scope decision

**Model: Opus 5, high effort.** Fresh session at the repo root on
`tools/proof-harness`. This document takes over from a **read-and-assess
session** that wrote no product code; its output was a verification pass, an
AWS audit, and four new workstreams in `PRODUCTION-PROGRAM.md`.

Handoff 14 owns J9, the gap-response contract, and PRs #230/#232. **Do not
re-do that work.** Start here once 14 has landed, or run the parts of this
document that do not depend on it.

---

## The one-sentence version

**The journey is at 8 of 9 and the remaining blocker is a test selector, not a
product defect — so the interesting question is no longer "does the journey
pass" but "is the system underneath it configured, contract-correct, performant
and secure," which W0-W6 never asked and W7-W10 now do.**

---

## Step 0 — verify before trusting this document

| # | Command | Expected |
|---|---|---|
| 0.1 | `git log --oneline -1` (local) | `960bd0e` (W7-W10 added) or later. **Note: unpushed at the time of writing** — `origin/tools/proof-harness` was at `daa0703`. If the local branch lacks `960bd0e`, the W7-W10 commit was never pushed; recover it before planning. |
| 0.2 | `grep -c '^## W10' docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md` | `1` — the new workstreams are present |
| 0.3 | `python3 -c "import json;d=json.load(open(sorted(__import__('glob').glob('docs/evidence/journey-*.json'))[-1]));print(d['journey_reached'])"` | `8`, or `9` if handoff 14 closed J9 |
| 0.4 | `gh pr view 230 --json state -q .state` | `MERGED` if 14 finished; `OPEN` if not |
| 0.5 | `grep -n 'cdk deploy CareerVpCrudDev' src/backend/Makefile` | **line 118 — if this still matches, Part 1 is still live** |
| 0.6 | `aws logs describe-log-groups --region us-east-1 --log-group-name-prefix "/aws/lambda/careervp-" --query "length(logGroups[?retentionInDays==\`1\`])" --output text` | **`48`** (measured 2026-09-23, all environments). If it is `0`, W7.2 already landed. |

If 0.5 no longer matches, someone fixed the production-deploy defect — confirm
how before assuming it is safe.

---

## Part 0 — what the previous session established, and the one framing correction

That session did not execute the plan; it measured the project against it.
Five results carry forward.

### 1. The framing correction (the most useful thing in this document)

Progress reports through handoff 13 read as *instrumentation, not product
work*. That reading is wrong about the Plan and right about the execution.

**`PRODUCTION-PROGRAM.md` prescribes real fix work.** Every one of W2, W3, W5
and W6 is split into *build the measuring tool* → *fix what it finds*:

| Workstream | Instrument | The fix half | State |
|---|---|---|---|
| W2 table architecture | `table_map.py` ✅ | **W2.2** fix every read≠write artifact; **W2.3** the single-vs-multi-table decision | never started |
| W3 dead code / dead API | `dead_api.py`, `dead_code.py` ✅ | **W3.3** remove what they found | never started |
| W5 ungated deploys | n/a | close 9 workflows | 2 of 10 |
| W6 rebuildability | preflight ✅ | `cdk import` or an owned decision | never started |

**The instrument half landed in all of them. The fix half has never run in any
of them.** That is the real position, and it is a better summary of the last
fourteen handoffs than any journey number.

### 2. Handoff 05's open thread is closed — by measurement

Carried as "unverified" since handoff 12B. Both items landed:
- The 4-file hermeticity fix is real. A full suite run under handoff 04's
  **corrected** no-credential condition (`AWS_SHARED_CREDENTIALS_FILE` and
  `AWS_CONFIG_FILE` redirected to `/nonexistent`, not merely `env -u`) gives
  **2077 passed, 48 skipped, 12 xfailed, 0 failed.**
- The three `asyncio.run` files handoff 04 named carry **zero** stdlib-level
  patches. `filterwarnings = ["error::RuntimeWarning"]` is active, so a
  regression fails the suite outright.

### 3. `blast-radius.sh` silently under-reports

`scripts/ops/blast-radius.sh:48-49` reads `on = d.get('on') or d.get(True)`
then `if not isinstance(on, dict): continue`. `security.yml` declares
`on: [pull_request, push]`, which YAML parses to a **list** — so the workflow is
**skipped entirely and silently**, never reaching the deploy scan. The tool
reports "workflows that fire: 0" for `tools/proof-harness` while Security Audit
demonstrably fires on push.

No deploy job is hidden *today* (1 of 28 workflows uses that form and it has no
deploy step), but the skip is unconditional. This is the same class as handoff
00's `AWS::DynamoDB::Table` vs `GlobalTable` false negative: a safety check that
queries the wrong shape and returns a confident, clean answer. **One-line fix**
(`if isinstance(on, list): on = {k: None for k in on}`), owed its own commit and
a regression test.

### 4. W7-W10 were added to the Plan

An AWS audit on 2026-09-23 found W0-W6 cover the deploy path, the table map and
the test estate — and never the running system. Four workstreams now do:
**W7** Lambda runtime configuration, **W8** performance and load, **W9** API
contract correctness, **W10** security. The workstream map and the definition of
done were both extended. Read them before planning; the findings are recorded
there with their measurements and are not repeated here.

### 5. `-dirty` is half-fixed

`5f44f89` committed the `dev_requirements` drift that was dirtying the tree, and
the latest preflight now reports **`git_dirty: False`** with an empty
`dirty_paths`. The deployed stamp still reads `…-dirty` because it was baked at
deploy time from a then-dirty tree. **The next clean deploy should stamp
clean** — verify it rather than assuming, because it closes two of the Plan's
exit criteria at once.

---

## Part 1 — the severe item nobody has touched in fourteen handoffs

W5 named this on 2026-09-19. It is still true, verified 2026-09-23:

- `src/backend/Makefile:118` — `make deploy` hardcodes
  `npx cdk deploy CareerVpCrudDev`
- `.github/workflows/main-serverless-service.yml:84` — `environment: production`
- the same file, line 125 — `run: make deploy`

**The production job deploys the dev stack.** W6 adds that the `production`
GitHub environment does not exist and would **auto-create unprotected** on first
use. So a production deploy today would be both ungated and pointed at the wrong
stack.

The Plan's own words: *"Treat this as an active exposure, not cleanup. It is the
only item in this document where doing nothing has an ongoing cost."*

**This is the highest-severity open item in the repository.** It is also cheap:
the fix is a stack-name parameter and a protected environment. Do it before any
production conversation starts.

---

## Part 2 — the V1 scope decision is now due

The Plan's Gap 1 says 9 of 9 does not mean sellable, and names what is outside
the definition of done: Company Research, Knowledge Base, Hebrew, and the entire
billing path. **The operator has now set the priority order** — Company Research
first (core feature), billing second, Knowledge Base to be investigated, Hebrew
last. That investigation was done. Results:

### Company Research — implemented, thinly verified

Full async backend (`company_research_handler`, `company_research_worker_handler`,
`company_intel_cache`, `company_research`, `company_research_store`), a real
frontend page at `app/applications/[id]/company-research/page.tsx`, and unit and
integration tests. It runs live: J5 passes through the hub and PR #228 fixed its
CTA.

**The gap is verification, not implementation.** There is no dedicated Playwright
e2e, so its health rides incidentally on J5. The decision the Plan calls for is
whether it becomes its own journey step or gets a second instrument.

### Knowledge Base — effectively not implemented

- **No frontend at all.** No `app/knowledge*` directory; zero `knowledge`
  references anywhere in `app/` or `components/`.
- `knowledge_base_handler.py` exists with **zero references** in infra or
  backend — orphaned, exactly as `docs/DEAD-CODE.md` said.
- `infra/careervp/api_construct.py:3598` wires `/knowledge-base` GET to
  **`company_research_func`** — a different Lambda entirely.
- `careervp-knowledge-table-devx` exists, holds 0 items, and partitions on
  `userEmail` (PII as a key, inconsistent with the `userId` convention).

**This is a scope decision, not a bug.** Either build the frontend and route
`/knowledge-base` to its own handler, or cut it from V1 explicitly. It is
currently neither, which is the worst of the three states. The Plan's estimate
of *"3-5 sessions for Hebrew + Company Research + Knowledge Base coverage"*
assumed coverage gaps, not a missing feature — **that band is too low.**

### Billing — built, but the money path has never run

`billing_handler`, `billing_reconcile_handler`, `billing_service`,
`trial_service`, a `payment_providers` package with a real `stripe_provider.py`,
a frontend `app/billing`, and five e2e test files.

But `careervp-billing-lambda-devx` runs **`PAYMENT_PROVIDER = mock`**, and that
is deliberate: `api_construct.py:3150` returns `placeholder` for production and
`mock` everywhere else, with a comment deferring Stripe to *"the paid-launch
freeze line (P-25b)."* **`StripeProvider` is code no deployed environment can
reach.** The thing that takes money has never executed end to end.

---

## Part 3 — where to go next

Ordered by a mix of severity, cost, and what unblocks what. Adjust with the
operator; do not silently re-order.

1. **Finish handoff 14** — J9, the gap contract, PRs #230/#232. Already scoped.
2. **Fix the production-deploy defect** (Part 1). Highest severity, low cost.
3. **Fix `blast-radius.sh`** (Part 0.3). One line, and every other item in this
   list depends on that tool telling the truth before a merge.
4. **W7.2 log retention → ≥ 14 days.** This blocks W8, W9 and W10: at 1-day
   retention any diagnosis performed under them is unreproducible the next day.
   It also protects the method that produced every root cause in this chain.
5. **Build `docs/FEATURE-STATE.md` (W4.3).** The Company Research / Knowledge
   Base / billing investigation above was done by hand. The ledger is the
   instrument for exactly that question, it is one of the six original exit
   criteria, and building it now is how a second Knowledge Base surprise gets
   caught before it costs a session.
6. **W9 — the contract check.** The live gap-answers defect is the proof that
   every existing instrument misses this class: `dead_api.py` sees a live route
   with a live caller, `table_map.py` sees matching tables, the unit suite
   passes, and `make journey` reported J8 **pass** while interview prep was
   served without the user's answers. Expect more of these in artifact types the
   journey does not inspect closely.
7. **W2.2** — sweep the read≠write artifact types that `table_map.py` already
   found. Same pathology as open bug S8.
8. **Then the features, in the operator's order:** Company Research e2e →
   billing (wire Stripe, provision the SSM params, build a purchase-path
   instrument) → Knowledge Base build-or-cut → Hebrew.

**A recommendation on instrument shape, not a decision:** grow the journey for
Company Research, since it already passes incidentally; use a **separate**
purchase-path instrument for billing. A money flow does not belong in a serial
suite that stops at the first failure.

---

## Part 4 — if an assumption here is false

- **If J9 still fails after handoff 14** — do not assume the selector was the
  only defect. Export has never been measured; the first real measurement may
  expose its own bug, the same way J4-J8 each did.
- **If the next deploy still stamps `-dirty`** — handoff 00 found a second,
  independent cause: the mandatory checks themselves rewrite tracked files
  (test evidence JSON, `dist/tsconfig.tsbuildinfo`). `5f44f89` fixed one source.
  Do not assume it fixed the class.
- **If `PAYMENT_PROVIDER` is no longer `mock`** — someone started the Stripe
  path. Find out whether SSM params and a webhook secret exist before testing
  anything that could charge a card.
- **If `table_map.py` reports clean** — that does not mean contracts are
  correct. It compares tables, not shapes. That is exactly what W9 exists for.

---

## Carried forward — operational hazards

- **`deployed commit is known` FAILs preflight.** Expect 8 pass / 1 fail until a
  clean deploy lands. Do not let it train you to skim the rest.
- **`blast-radius.sh` under-reports** until Part 0.3 is fixed — cross-check
  `gh run list --branch <branch>` against what it claims.
- **The `devx` reviewer gate needs a human.** An agent session cannot approve it
  and must not try to self-grant the permission. Ask and wait.
- **Amplify `db-redesign` auto-builds on every push, with no gate.** The `devx`
  gate covers the backend job only.
- **Trial budget.** Check it before `make journey`; `TRIAL_LIMIT_APPLICATIONS`
  is 3, and resetting requires an explicit operator grant.
- **7 of 10 workflows still run `make deploy` ungated** (W5).
- **Nothing in `docs/DEAD-CODE.md` has been deleted** (W3.3) — including
  `knowledge_base_handler.py` and the orphaned `cv_tailoring_stack.py` that
  ships inside every Lambda artifact.

## Ground rules

- `scripts/ops/blast-radius.sh <event> <branch>` before any merge, deploy,
  deletion or credential change; paste Action/Triggers/Undo **before** acting —
  and until Part 0.3 lands, verify its answer against `gh run list`.
- Stop and ask on a `CREATE+EXECUTE` you did not expect, `NO ENVIRONMENT GATE`,
  or an environment with `0 rules`.
- Verify the environment; never infer it from a plan document — **including this
  one**, and including `PRODUCTION-PROGRAM.md`, which carried a wrong
  foundational assumption for three handoffs.
- One concern per commit. Every fix gets a regression test that fails before and
  passes after — and run it the way CI runs it.
- A repo grep is not an inventory, a green deploy is not a working system, a
  green step is not a correct artifact, and **an instrument reporting clean is
  not the same as the thing being correct** — W9 exists because four instruments
  reported green on a feature that was silently broken.
