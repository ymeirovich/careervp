# How to write a Wave-2 prompt — the fixed instruction for Codex

**What this file is.** A single, copy-paste instruction you hand to Codex before it writes or fills
in *any* Wave-2 prompt in
`/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-prompts.md`.
It tells Codex exactly **what** a prompt is, **where** it goes, **when** to write it, **how** to
build it, and **why** each part exists. It is the operational front-end to
`/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md`
(the seventeen standing rules) — that file is the law; this file is the checklist that makes a
prompt obey it without re-deriving it every time.

Everything below the line is the prompt. Paste it verbatim.

---

## PROMPT — Codex, read this in full before you write one word of a Wave-2 prompt

You are authoring (or filling in) one prompt in the Wave-2 runbook. A "prompt" here is a
**copy-paste unit of work**: a self-contained block that a *fresh* Codex or Claude session, with
no memory of this conversation and its working directory at the repository root
`/Users/yitzchak.meirovich/Documents/code5/careervp`, can paste in and execute correctly with nothing else in
front of it. If your prompt only works because the runner remembers what you were thinking, you
have failed. Write for a stranger who starts cold.

### WHY you are being this careful (read this first — it is not ceremony)

Every rule below traces to a real incident on this project where being casual cost a day or shipped
a silent bug. A deploy state was read from a `cdk diff` and called "live" — a real change set the
next day showed 523 pending changes. A 30-day security waiting period protected nothing because the
belief under it was never written down as checkable. A green regression test guarded a sign-out path
that was broken in production, because nobody ever watched it fail. A prompt named one spec file
three different ways in four lines. **These are the failures you are preventing.** When a rule feels
like overhead, that is the rule doing its job — it is buying back a day someone already lost.

### WHERE everything lives (use these exact full paths — never a bare relative fragment; RULE 17)

A prompt is pasted into a session sitting at the repo root, not in the `runbooks/` folder. A path
like `specs/P-25-...md` or `../specs/P-25-...md` resolves differently depending on where the reader
started, and different lines silently assume different bases. So **every file you name — in prose,
in a markdown link's target AND its visible text, in a "confirm it exists" check, in the header's
`Spec` field, in a commit-message citation — is the single full path from the filesystem root:**

| Thing | Full path |
|---|---|
| The rulebook (the law) | `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md` |
| The prompt file you are editing | `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-prompts.md` |
| The live status ledger | `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md` |
| The bets register | `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/ISSUES.md` |
| The contract (master requirements) | `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml` |
| The execution plan (model/effort per step) | `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/redesign-execution-plan.md` |
| Spec files | `/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/specs/<spec-file>.md` |

**The one carve-out is a shell snippet.** A command block may use paths relative to its own working
directory, but only when an explicit `cd <full absolute path>` sits at the top of that same block as
the anchor — e.g. `cd /Users/yitzchak.meirovich/Documents/code5/careervp/src/backend && uv run pytest tests/unit/...`,
never a bare `cd src/backend`.

### WHEN you write which prompt (RULE 11 — do not instantiate the whole wave)

Wave 2 is deliberately part full-prompt, part skeleton. Your job is one of two things, and you must
know which:

1. **Authoring a full prompt from scratch** (only the *first* step of a wave is written this way).
2. **Filling in a skeleton** — expanding an existing contractual skeleton in `wave-2-prompts.md`
   into a full prompt in the shape of `PROMPT 2.0-RED`.

**A skeleton may be filled in only once its dependencies have actually landed** — verified from git
and live state, not from a status column. And it is filled in **by a session that has first read
every ledger row above it** in the status file, so real deviations from earlier steps get absorbed,
not contradicted.

**The skeleton is contractual.** Its clause ids, its acceptance-criteria ids, its `Depends on`, its
deploy target, its `Done-when`, and its `Claude / Codex` model line come from the contract, the
spec, and the execution plan. You **may not invent or widen any of them** at fill-in time. If
filling one in *requires* changing its clause or its acceptance criteria, **STOP** — that is a
rule-5 flag and a §0.3 amendment, not an edit you make.

### WHAT a full prompt is made of (the anatomy — every part is mandatory)

Produce exactly these four parts, in this order:

**1. The header** — one blockquote, stating without exception:
   - The clause id(s), e.g. `Clause: P-14, P-15`.
   - The **full path** to the spec file, as both the link target and the visible link text.
   - The acceptance-criteria IDs this prompt implements, e.g. `AC-P14-1, AC-P15-1`.
   - **Both engines' model and effort, never one alone (RULE 15):** `Claude: <model>/<effort>` and
     `Codex: <model>/<reasoning>`, copied verbatim from the execution plan's row for this step.
   - **`<model>` is the real slug, not the vendor name (RULE 16).** `Codex: gpt-5.3-codex/high` —
     never `Codex: codex/high`. "codex" names the vendor, not a model; `Codex: codex/high` fails
     this check exactly as a blank `Codex:` would. If the execution plan's own row still carries the
     bare `codex/<tier>` form, resolve it to the real model per the RULE 16 table below — do not copy
     the stale form forward.
   - If this is a RED or GREEN split (RULE 7 — any clause touching auth, tenancy, money, or data
     durability), say so and state the firewall: RED writes tests only and may touch **zero**
     implementation files; GREEN is a fresh session that has not seen RED's reasoning and **may not
     edit any test file**.

**2. The STANDING CHECK block** — pasted near-verbatim from the template below, opening the prompt
   body. It implements rules 3, 4, and 14.

**3. The work body** — the concrete, numbered instructions: exact files to build, exact commands to
   run, exact things to verify. Everything an executor needs and nothing it has to guess. Name the
   verification commands explicitly (unit suite, integration, `ruff`, `mypy --strict`, the coverage
   gate, `scope-diff.py`). State the deploy target, or state "no deploy" and why.

**4. The OUTPUT REQUIRED block** — pasted near-verbatim from the template below, closing the prompt.
   It implements rules 1, 2, 5, and 6.

### HOW to build one — the procedure, in order

1. **Read the three companion files first**, from disk, at the full paths above: `RUNBOOK-RULES.md`
   (the law), `wave-2-status.md` (what actually happened — read every row above your step), and
   `ISSUES.md` (the bets your step rests on; some are already known partly false).

2. **Confirm your dependencies actually landed** — with a real command (`git log`, a test run, a
   `cdk diff`), right now, this session. Not "the plan says 2.0-GREEN is done." If a prerequisite is
   not truly met, **STOP and say so in plain English.**

3. **Confirm the spec before writing any test (RULE 14).** With a real command, confirm: the spec
   file exists at the full path you cite; it has a "RED Tests to Write First" section naming the
   exact acceptance-criteria IDs your prompt implements; and each cited RED-test description states
   exact assertion values — no "or"-shaped assertions, no undefined placeholders. If any of the
   three fails, **STOP** and author/fix the spec section first, as a separate visible action — never
   fold it silently into the test-writing step.

4. **Set the header** per WHAT §1. Copy both models from the execution-plan row. Where the Codex
   model/reasoning has to be *chosen* (a skeleton/GATE row left blank, or a step outside the plan's
   coarse buckets), derive it from the RULE 16 rubric — cheapest model and lowest reasoning tier
   that can reliably satisfy the acceptance criteria, never the largest "to be safe," never a higher
   tier to compensate for a vague prompt:

   | Prompt shape | Codex selection |
   |---|---|
   | Edit one file / fix one small test | `gpt-5.3-codex` + `low` |
   | Implement a spec with tests | `gpt-5.3-codex` + `medium` |
   | Trace a cross-cutting failure (backend/frontend/infra) | `gpt-5.3-codex` + `high` |
   | Plan/review a dangerous deploy or migration | `gpt-5.3-codex` + `high` or `xhigh` |
   | Large ambiguous architecture change | `gpt-5.3-codex` + `xhigh` |
   | Bulk repetitive edits, obvious pattern | Codex model + `low` |

   Start at `medium`; drop to `low` only when genuinely mechanical; raise to `high` when the work
   crosses module boundaries or can break production behavior; reserve `xhigh`/`max` for high blast
   radius (data-model migration, auth/tenancy, hard concurrency, production-adjacent infra).

5. **Paste the STANDING CHECK block** (template below), instantiating every placeholder — the wave
   number, the full status-file path, the spec's full path, and the acceptance-criteria IDs.

6. **Write the work body** — concrete files, concrete commands, concrete verification. If this is a
   RED session, it writes tests only and confirms zero implementation files changed
   (`git diff --stat`). A test that fails on an ImportError, a collection error, or a missing fixture
   is **not RED — it is broken**; it must fail on its own assertion. Before trusting any regression
   test, break the implementation on purpose, watch it go red, and **paste that failure output**
   (RULE 13) — do not assert you did it.

7. **Paste the OUTPUT REQUIRED block** (template below), instantiating the clause id and the full
   status-file path.

8. **State the bets (RULE 9), if you are authoring the wave or the step introduces one.** A bet is
   three parts, all required: the belief (stated so it could be false), the cheapest check that
   would show it false (a live-state read beats a type check beats one minimal test beats a dry-run
   beats building the real thing — cheapest first), and the fallback decided now. Bets live in
   `ISSUES.md`.

9. **Every deferral carries a stopping condition (RULE 10)** — not just a home and a trigger, but an
   *observable* condition (a date, or a state you can query) for what smaller thing ships if the
   trigger fires and the work still is not done. Deferrals go in `ISSUES.md`, not a plan table.

### The two blocks — paste these near-verbatim into every prompt (swap the placeholders)

**STANDING CHECK (opens the prompt body):**

```
STANDING CHECK — before doing anything else: open
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md.
If the step immediately before this one (in dependency order) left something open or unresolved,
deal with that FIRST — do not start this step's own work with unfinished business behind you. Then
confirm THIS step's own prerequisites are actually met right now, using a real command (not memory,
not this file) — if they are not, STOP and say so in plain English.

BEFORE WRITING ANY TEST (rule 14): confirm, with a real command, that
<full path to spec file> exists, that it has a "RED Tests to Write First" section naming
<the acceptance-criteria IDs this prompt implements>, and that each cited test names exact assertion
values (no "or", no undefined placeholders). If any of that is not true, STOP — author or fix the
spec section first; do not write tests against a spec that does not say what it is testing.
```

**OUTPUT REQUIRED (closes the prompt):**

```
OUTPUT REQUIRED
- <the step-specific outputs: verbatim test output with a one-line why for each, confirmation that
  the correct set of files was/was not touched via git diff --stat, any bet-decision this step
  settles, etc.>
- A git commit message (literally output the text — every prompt ends this way, rule 1).

ALSO REQUIRED (standing rule for every wave prompt — see
/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) the matching
  clause <clause id> in
  /Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml.
  If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update
  /Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md:
  add/update this step's row with a plain-English status, the commit, today's date, and anything the
  NEXT step must resolve first (or write "none").
```

### The hard STOPs — when you must stop and flag, never quietly fix (rules 5, 7, 8, 14)

- The spec does not exist, or does not name the acceptance criteria you are about to build tests for.
- Filling in the skeleton would require widening its clause or acceptance criteria.
- A test looks genuinely *wrong* (not merely inconvenient) — raise a §0.3 amendment; never edit it
  to pass.
- A prerequisite is not actually met when you check it live.
- What got built does not match both this prompt's instructions and the `project-scope-lock.yaml`
  clause — flag it in plain English first (one sentence a non-engineer follows: what should have
  happened, what happened, why it matters), then the technical detail. Do not mark the step done.
- A written gate turns out satisfiable a different way — that can be legitimate, but it needs a
  dated section in `wave-2-status.md` with the live commands you ran and the reasoning a future
  session can disagree with; append to the gate's original text, never rewrite it (RULE 8).

Changing a **clause definition** in `project-scope-lock.yaml` is never in scope for a prompt-writing
session — that needs the twin-sync ceremony with a version bump and a signed
`Scope-Lock-Approved-By` trailer.

### Before you hand the prompt back — self-check every one of these

- [ ] Every file named is a full path from the repo root (RULE 17) — prose, link targets, link
      text, checks, header, commit citations. The only relative paths sit under an explicit
      `cd <full absolute path>` at the top of their block.
- [ ] Header states clause id(s), full spec path, acceptance-criteria IDs, and **both**
      `Claude: <model>/<effort>` and `Codex: <model>/<reasoning>` — with a real Codex model slug,
      not `codex/<tier>`.
- [ ] The STANDING CHECK block is present and includes the rule-14 spec-verification line.
- [ ] The OUTPUT REQUIRED block is present, ends by requiring a commit message, requires the
      build-vs-contract comparison, and requires a `wave-2-status.md` row update.
- [ ] If the clause touches auth/tenancy/money/durability, RED and GREEN are separate sessions with
      the firewall spelled out (RULE 7).
- [ ] Any regression test in the prompt is required to be *seen failing* first, with pasted output
      (RULE 13).
- [ ] Any bet has a belief + a cheapest-tier check + a fallback (RULE 9); any deferral has an
      observable stopping condition (RULE 10); both live in `ISSUES.md`.
- [ ] You did not invent or widen anything the skeleton fixed; deviations are flagged, not absorbed
      silently (rules 5, 11).

If any box is unchecked, the prompt is not done. Fix it before returning it.
