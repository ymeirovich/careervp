# Runbook Standing Rules

**What this file is:** the rulebook every wave-prompt file (`wave-0-prompts.md`,
`wave-1-prompts.md`, `wave-2-prompts.md`, …) must follow. Whoever writes a new wave's prompt
file — human or agent — must apply every rule in this file to every prompt in it, and must link
this file from the top of the new wave-prompts file. This is the fix for a real problem found
while building `wave-1-prompts.md`: status lived only in loose prose inside the prompt file
itself, so it went stale and nothing forced the next prompt to notice.

> **Amended 2026-07-22:** rules 7 and 8 added while planning Wave-1 step 1.1. Both come from real
> incidents in this project, described in each rule. Rules 1–6 are unchanged.

> **Amended 2026-07-24:** rules 9–13 added while planning Wave 2, from a review of what Wave 1
> actually cost. Rules 1–8 govern **how a prompt runs**. Rules 9–13 govern **what gets built, in
> what order, and how you know it worked** — a different layer. Rules 1–8 are unchanged.
>
> One rule from that review was deliberately **not** adopted: requiring every spec to declare what
> it does not touch. It is a good idea and it is cheap, but the single incident it would have caught
> (commit `2513ee6` editing a CDK construct under a CI-only title) converged harmlessly and was
> correctly flagged at review. Fold it into the spec template when one is next edited; it does not
> justify a session of its own. Recorded here so the next reader knows it was considered, not missed.

---

## The seventeen rules

### 1. Every prompt ends by writing a git commit message

Not "commit the work" — literally output the commit message text as part of the prompt's
required output, every time, even for a docs-only or spec-authoring step.

### 2. Every prompt updates a status ledger the next prompt actually reads

Each wave gets its own ledger file: `wave-N-status.md`, sitting next to `wave-N-prompts.md` in
this `runbooks/` folder. It is a small table, not prose — a table stays scannable; prose goes
stale and gets skimmed past. When a prompt finishes (or stops on a problem), it adds or updates
its own row: plain-English status, commit hash, date, and — critically — anything left open that
the *next* prompt needs to deal with first. The prompt file (`wave-N-prompts.md`) describes
*intent*; the ledger (`wave-N-status.md`) describes *what actually happened*. Never let the two
merge into one document — that's exactly how Wave 0's status table went stale three times.

### 3. Whatever a prompt leaves open, the next prompt handles first

Before a prompt does anything of its own, it opens the ledger and checks the row for the step
immediately before it in dependency order. If that row says something is still broken, missing,
or waiting on a human — the new prompt's very first job is to deal with that, not to start its
own checklist with unfinished business sitting behind it.

### 4. Every prompt checks its own prerequisites before doing anything else

Not "trust the plan says step 1.0 is done" — run an actual command (a test, `git log`, `cdk
diff`) and confirm it for real, right now, in this session. If a prerequisite isn't actually met,
the prompt stops immediately and says so — it does not improvise around a missing dependency.

### 5. Every prompt checks its own finished work against two things, and flags any mismatch instead of quietly fixing it

At the end, before declaring the step done, the prompt compares what it actually built against:
(a) what this specific prompt told it to do, and (b) the matching entry in
`project-scope-lock.yaml` — the master contract file that defines every piece of required work.
If those two things don't line up — it built something the instructions didn't ask for, skipped
something they required, or had to weaken a rule/test to get something to pass — **it stops and
flags it for a human to look at.** It does not fix the mismatch itself and does not mark the step
"done" while a mismatch is open.

### 6. Every explanation of a problem is written for a human first, jargon second

When a prompt flags something (rule 5, or any other stop condition), the explanation has to work
for someone who is *not* reading code all day. That means: **one plain sentence saying what went
wrong and why it matters, in normal words** — then, after that, the technical detail (file paths,
clause IDs, line numbers) for whoever picks it up to actually fix it. Never lead with the jargon.
A useful test: if the plain-English sentence were the *only* thing a person read, would they
understand the problem and roughly how serious it is? If not, rewrite it.

### 7. For any correctness-critical clause, RED and GREEN are two different sessions

The reason is simple: **whoever writes the test must not be whoever writes the code.** If the same
reasoning does both, the test agrees with the implementation's bugs and goes green for the wrong
reason. It is a student grading their own exam — not dishonesty, just no independent check.

The ceremony:

- **RED session.** Writes only the test files (plus any checked-in evidence artifact the spec asks
  for, like a route matrix). Carries an **absolute prohibition** on touching implementation files —
  not even temporarily, not even "to see if it works." Runs the tests, captures the failure output
  verbatim, and states for each one *why* it failed. **A test that fails on an ImportError, a
  collection error, or a missing fixture is not RED — it is broken**, and it will go green later
  for reasons unrelated to the fix. Commits tests only.
- **GREEN session.** A **fresh session** that has not seen the RED session's reasoning. `/clear` is
  the minimum; a separate `claude` invocation is preferred. It reads the failing tests as a
  contract it did not write and **may not edit** — that clause is the entire firewall. No relaxing
  an assertion, widening an exclusion list, adding an `xfail`/`skip`, or extending a public-route
  exception to make something pass. If a test looks genuinely *wrong* (not merely inconvenient),
  it **STOPS and raises a §0.3 amendment**. Never a quiet edit.

Apply this to every clause where being wrong is worse than being late — anything touching auth,
tenancy, money, or data durability. For small isolated clauses, a single session that still writes
RED first and pastes the failing output before going GREEN is acceptable; say which you used.

Subagents are not a substitute. A fresh subagent works only if you do not paste the RED reasoning
into its prompt — and the safe use of subagents remains read-only recon (enumeration searches),
never writing tests or implementation.

### 8. A written gate satisfied differently needs a dated ledger entry with its reasoning

Sometimes a gate written in a spec or runbook turns out to be satisfiable another way, or to be
protecting nothing. That can be legitimate — but **it may never be an unexplained shortcut.**

If you conclude a written gate should be satisfied differently, write a dated section in
`wave-N-status.md` containing: what the gate said; what you found (with the live commands you ran,
not a summary); which concerns the gate actually bundles, taken one at a time; which of those are
now discharged, by what concrete artifact; and which remain open, with an explicit new home. Then
amend the gate's original text by **appending**, never by rewriting — the original sentence stays
readable so the history is intact.

The test of a good entry: a session six weeks from now that hits the original gate and is inclined
to refuse should find **reasoning it can evaluate and disagree with**, not an assertion it has to
take on faith. Worked example: `wave-1-status.md` §"Soak reinterpretation (2026-07-22)", where a
30-day soak was replaced by about an hour of verification because the 30-day clock provably never
started.

Two things this rule is not. It is not permission to shorten gates that are merely inconvenient —
the reasoning has to actually hold. And it does not extend to `project-scope-lock.yaml`/`.md`:
changing a **clause definition** still requires the twin-sync ceremony with a version bump and a
signed `Scope-Lock-Approved-By` trailer. This rule governs *how a locked requirement is delivered*,
never *what is required*.

### 9. Every belief a wave rests on is written down, with the check that would disprove it and the fallback if it does

A clause says what will be built. A **bet** says what has to be true for building it to be worth
anything. Three parts, all required, none optional:

| Part | What it has to be |
|---|---|
| **The belief** | Stated so it could turn out false. "The mock's signature check matches Stripe's" — not "signature verification works." |
| **The check** | **The cheapest command, query, or run that would show it false.** Not "review this later" — and not "implement it and run the test suite" either, when something cheaper would answer the same question. |
| **The fallback** | What we do instead, decided **now**, while the answer is still genuinely unknown. |

A belief with no check is a hope. A belief with no fallback is a single point of failure that
nobody has planned around. Bets live in `ISSUES.md` (agents may write there); a bet that turns out
to underwrite a locked decision gets promoted into `project-scope-lock.yaml` by human amendment.
**Every wave's bets are re-read at that wave's gate** — an unread register is just more text.

**The check is not free to be expensive.** "A check exists" is satisfied just as well by "build
the feature and see if it breaks" as by a two-line probe — and the first one is the exact failure
this rule exists to prevent: the cost of being wrong discovered only after the cost of building on
top of it was already spent. Pick the cheapest tier that can actually answer the belief, cheapest
first:

1. **Read live state** — an AWS/GitHub/git query. Zero new code.
2. **Check the type system** — assert it with the existing type checker. Near-zero new code.
3. **One minimal test** — the smallest red test that could answer it, not the whole suite.
4. **A dry-run** — synth, plan, `--no-execute`. Never a real mutation.
5. **Build the real thing.** Last resort — and the check must say why nothing cheaper applied.

If a bet's check lands on tier 5, that is a decision to record, not a default to reach for.

**The incident.** Wave 1's 30-day waiting period rested on "stale implicit-era refresh tokens are
in circulation on the target pool." That was never written as something checkable, so nobody
checked it. It surfaced four days later only because someone happened to run
`describe-user-pool-client` and `git merge-base --is-ancestor`. Written as a bet, the whole soak
reinterpretation was available on day zero for three lines — and **the check is exactly the command
that eventually found it.**

**The ladder is not theoretical — it already paid for itself twice, before this amendment existed.**
Both times, the cheap check reversed a more expensive plan already in motion:

- Devx's Amplify branch. Before writing any CDK fix for "the frontend still points at dev," a
  tier-1 read (`aws amplify get-branch`) showed it was already devx-wired. Zero fix code written
  for a problem that had already been solved by hand.
- The webhook-secret parameter. A tier-1 read (`aws ssm get-parameters-by-path` on both prefixes)
  disproved a more complex plan already being written into these docs — a "2.0→2.1 handoff"
  section treating the secret as dependent on step 2.0's output — and collapsed it to a five-value
  copy.
- Bet `B-2-5` inside `wave-2-prompts.md`'s own `PROMPT 2.0-RED` is a tier-2 check *by construction*:
  two annotations changed from `Any` to the real Protocol type, `mypy --strict` run, then reverted —
  before any of the step's five planned tests are written. It surfaces every port violation for the
  cost of a diagnostic, not the cost of discovering it mid-suite.

**Free consequence, worth taking.** Once a wave's bets are listed, ask which one, if wrong, deletes
the most downstream work — and schedule that first. This project already does that by instinct and
records it as an amendment afterward: token metering was pulled forward so a measured baseline would
exist before the model-routing decisions; the canary was pulled ahead of the auth flip so the flip
had a fire-drilled revert; the research-cost guard was pulled ahead of the chain reorder so volume
was bounded before it multiplied. Three correct orderings, each discovered late. Ask the question up
front instead.

### 10. Every deferral carries a stopping condition, not just a home and a trigger

`ISSUES.md` already asks for a **Trigger** — the condition that forces an item back onto the table.
That is half of it. The other half is: **when the trigger fires and the work still has not been
done, what smaller thing ships instead?** Written at the same time as the deferral, while the
outcome is unknown.

The condition must be **observable** — a date, or a state you can query. "When it feels urgent" is
not a stopping condition, and a soft one is decoration.

**The incident.** The deferred removal of the admin scope from the browser login client has a home
and a trigger (staging promotion). It has no stopping condition, and the migration window has been
open since 2026-07-18 with the insecure grant still live. Every extension was individually
reasonable — that is precisely how extension works. Worse, it never went into `ISSUES.md` at all;
it is a row in a plan table. **The mechanism built to catch exactly this was bypassed by the case
it was built for.** A deferral that skips this file has not been deferred, it has been mislaid.

A project without written stopping conditions does not stop. It extends.

### 11. Detail the first prompt in full; skeleton the rest of the wave

Do not instantiate a whole wave of prompts up front, and do not write them strictly one at a time
either. Both fail differently: a full wave goes stale and then fights sunk cost to rewrite, while
one-at-a-time loses the whole-wave view and hides work that could run in parallel.

The split:

- **The first prompt is written in full** — every check, every command, every output requirement.
- **Every later prompt is written as a skeleton**: its clause id(s), its acceptance-criteria ids
  from the spec, its dependencies, its deploy target, its done-when, and the bets it rests on.
  Enough to see the whole wave and its wiring; not so much that it rots.
- **A skeleton is filled in to a full prompt only when its dependencies have actually landed**, and
  it is filled in *by a session that has read the ledger rows above it* — so real deviations from
  earlier steps get absorbed rather than contradicted.

**The skeleton is contractual.** Clause ids, acceptance-criteria ids, and done-when come from
`project-scope-lock.yaml` and the spec, and **may not be invented or widened at fill-in time**. If
filling one in requires changing its clause or its acceptance criteria, that is a rule-5 stop and a
§0.3 amendment — not an edit.

**The incident.** `wave-1-prompts.md` was written whole, up front. It then needed three standing
corrections, a seven-row stale-citation table, a three-way split of step 1.1, and a supersession
banner on 1.3d. In places it now carries more correction than original text, and every reader has
to hold "which parts of this are still true" in their head. The rule already existed *between*
waves ("a wave's prompt file is only generated once the prior GATE is truly verified"). This
applies it *within* a wave, without giving up the map.

### 12. A wave closes on a demonstration someone else can re-run

Not "every row says done and `scope-diff.py` agrees." A wave-closing gate is a **script** that
someone who was not there can run, that emits a dated evidence file, and that gives the same answer
twice from a cold start.

Checks that genuinely need a human (did a real person complete a login?) stay human — the script
prints them as `HUMAN REQUIRED` and exits non-zero until their evidence file exists. **A gate script
that honestly covers six of eight checks is worth more than one that pretends to cover eight.**

**The incident.** On 2026-07-18 a session read a `cdk diff` and concluded five clauses were
`DEPLOYED`. On 2026-07-19 a real change set showed **523 pending changes** and the entry was
corrected — "committed to the repo" had been read as "live," in a ledger that already had eight
standing rules. Wave 1's GATE was a genuine improvement (eight checks adjudicated against live AWS
and git), but it was still an agent reading and asserting. A reading error is the one kind of error
a script cannot make. `src/backend/scripts/smoke_harness.py` is the right instrument and the right
precedent — it is applied per step and has never been applied to a wave.

### 13. A test that has not been observed to fail is not a test

Rule 7 governs *who* writes the test. This governs whether it **can** fail at all. Before a
regression test is trusted, break the implementation on purpose, watch it go red, and **paste the
failure output** — do not assert that you did it. If it stays green, it is decorative, and it will
be believed anyway, because regression tests are the ones trusted most and examined least.

For infrastructure and synth tests this is fiddlier than for unit tests. Do it anyway: flip the
asserted property in the construct, re-synth, capture the failure, revert.

**The incident, twice over.** The technique was already invented here — the 1.2 session verified its
RED tests by `git stash` round-trip against the pre-fix tree, and 1.1-RED did the same. It was
standard practice for nobody. And Wave 1 shows the cost of skipping it: `api-client.test.ts` proved
the 401 retry interceptor worked *when something registered it*, and **nothing in the running
application ever did** — a permanently green test over a sign-out path that was broken in
production, found only by logging in for real. Standardizing this is the cheapest rule in this file.

> **Amended 2026-07-25 (later same day):** rule 9's "check" requirement tightened — a check must
> now be the *cheapest* tier that can answer the belief (a five-tier ladder: live-state read, type
> check, one minimal test, dry-run, real build — in that order), not merely "a check exists." A
> bet whose check jumps to building the real thing must say why nothing cheaper applied. Grounded
> in two checks that already paid for themselves this session before the rule existed (the Amplify
> branch read, the SSM parameter-parity read) and in `B-2-5`'s own tier-2 design. Closes a real gap
> in the original rule 9: "build it and see" technically satisfied "a check exists."

> **Amended 2026-07-25:** rules 14 and 15 added while writing Wave 2's `2.0-RED` prompt — both
> caught live, inside the very prompt meant to demonstrate the discipline. Rules 1–13 unchanged.

### 14. A prompt confirms the spec exists — with real RED-test descriptions naming exact assertions — before writing a single test

Spec-before-test is not new; it is this project's standing convention
(`project-scope-lock.yaml` v1.3.0): a spec's "RED Tests to Write First" section is authored first,
naming exact assertions per acceptance criterion, and the pytest files that make those tests real
are written later, at implement time, never as a separate artifact. This rule makes that ordering
an **enforced check inside the standing-check block**, not an assumption inherited from the fact
that Wave 0 happened to author the specs first.

Before writing any test file, the standing check confirms, with a real command, not memory:

1. The named spec file exists at the path the prompt (or skeleton) cites.
2. It has a "RED Tests to Write First" section naming the exact acceptance-criteria IDs this
   prompt implements.
3. Each cited RED-test description states exact assertion values — no "or"-shaped assertions, no
   undefined placeholders (`spec_time_lint`, `project-scope-lock.yaml` `spec_test_acceptance`).

If any of the three fails, **STOP.** Do not write a test against a spec that does not exist or
does not say what it is testing — author or fix the spec section first, as a separate, visible
action, never as a silent workaround folded into the test-writing step.

If a RED session concludes a needed test is not in the spec's list, it says so explicitly, names
what discovered the need, and does not silently fold it in as if the spec had always covered it —
this is rule 5's flag-don't-fix, applied specifically to test coverage the spec never anticipated.

**This applies identically when a skeleton is filled in.** A skeleton's `Spec` and
`Acceptance criteria` fields are a claim made when the wave was planned, not a proof — the session
filling it in re-verifies all three checks live, exactly as it would starting from nothing. This is
rule 4 (check your own prerequisites), applied specifically to the spec/test ordering, and it is
why a skeleton is not itself sufficient to start writing tests.

**The incident.** Found live, inside this file's own Wave-2 work: `wave-2-prompts.md`'s
`PROMPT 2.0-RED` cites `specs/P-25-payment-provider-spec.md` in its header and lists tests drawn
from that spec's "RED Tests to Write First" section — but its standing check verified git history
and package structure and never verified the spec file itself existed or contained what the prompt
was about to build tests from. It happened to be true (the spec was authored in Wave 0's step 0.4
fan-out, before any wave began) — but nothing in the prompt checked that; it was inherited on
faith. The same class of unverified assumption rule 9's bets exist to catch, here applied to
spec/test sequencing instead of an infrastructure belief.

### 15. Every prompt states both Claude's and Codex's model and effort — never one alone

The execution plan's wave tables (`redesign-execution-plan.md`, one row per step) carry two model
columns, because this project routes work to either engine. A prompt or skeleton that states only
one silently narrows that choice for whoever runs it next, and drifts from the plan that is
supposed to be authoritative over it.

Every full prompt's header, and every skeleton's field table, states **both** —
`Claude: <model>/<effort>` and `Codex: <model>/<reasoning>` — copied verbatim from the execution
plan's per-step columns for that clause. Never invented at prompt-writing time, never left
Claude-only.

**The incident.** `wave-2-prompts.md`'s `PROMPT 2.0-RED` and `PROMPT 2.0-GREEN` headers stated
`Model: opus/high` and said nothing about Codex — even though `redesign-execution-plan.md`'s own
Wave-2 table row for step 2.0 (P-25) names both `opus/high` and `codex/high`. Found live when a
human read the header and noticed the omission, in the same session rule 14 was found in — two
gaps in the one prompt meant to model the discipline for the rest of the wave.

> **Amended 2026-07-25 (later same day):** rule 16 added. Rule 15 fixed *whether* both engines'
> model and effort are stated. It does not say how the Codex side gets *decided* — and
> `redesign-execution-plan.md`'s own "Model + effort convention" table only covers three coarse
> buckets (Mechanical/Standard/Hard). Anything that falls outside those three, or is filled in
> later by a different session, has nothing to consult but instinct. Rules 1–15 unchanged.

### 16. Codex's model and reasoning are picked by rubric, never guessed independently or defaulted to the largest setting

Rule 15 says both engines' model and effort must be stated, copied verbatim from the execution
plan. It says nothing about how that Codex value is *arrived at* in the first place — and that gap
is not hypothetical. `wave-2-prompts.md`'s own "GATE — Wave 2 close-out" skeleton has an unfilled
`Claude / Codex` field that says, verbatim, *"Whoever fills this in should pick a model/effort and
record it here"* — with no method attached. Left as-is, two different sessions filling in two
different skeletons will pick differently, for the same class of work, and rule 15 will faithfully
record two inconsistent answers as if they were both authoritative.

This rule is the method. Whenever a step's Claude model/effort is chosen — authoring or extending
`redesign-execution-plan.md`'s convention table, or filling in a skeleton/GATE row rule 15 left for
"whoever gets to it" — the paired Codex model/reasoning is derived from the rubric below, not
invented independently and not defaulted to the largest tier "to be safe." Both engines are being
pointed at **the same task**, so they should track the same difficulty judgment, just expressed in
each engine's own vocabulary. This is the same instinct as rule 9's cheapest-check ladder, applied
to tooling cost instead of verification cost: **pick the cheapest model and lowest reasoning level
that can reliably satisfy the acceptance criteria, not the largest one available.**

**Bare `codex` is not a model.** `codex/high` names the vendor, not the model — rule 15's
`Codex: <model>/<reasoning>` requires the actual slug in `<model>`, and "codex" is not one. **The
incident:** every Wave-2 row in `wave-2-prompts.md` (both `PROMPT 2.0` headers and all seven
skeleton/GATE tables) carried exactly this — `codex/high`, `codex/med` — until fixed on 2026-07-25.
`redesign-execution-plan.md`'s convention table and every wave's per-step Codex column carry the
same bare form today; that is a known, tracked gap in the plan, not something this rule silently
papers over — it is not being swept in the same pass, but every new row and every row filled in
from here forward names the real model (`gpt-5-codex/high`, not `codex/high`), per the table below.

**Model choice.** Use the newest Codex-optimized model available in the executing environment for
real implementation work, unless the task is explicitly cost-sensitive:

| Model | When |
|---|---|
| `gpt-5.3-codex` | Default for serious agentic coding — multi-file changes, debugging, refactors, migrations, test repair, anything requiring many steps of inspect-then-act. |
| `gpt-5-codex` | Only if the environment/runbook does not expose a newer Codex model, or compatibility requires this exact slug. This is this project's current pin (`scope_lock_clause` frontmatter exemplar, `redesign-execution-plan.md`'s convention table) — this rule does not license silently renaming those; a change to an already-authored spec's pinned model is a written value being satisfied differently and goes through rule 8, not a global find-and-replace. |
| `gpt-5.6-sol` / `gpt-5.6-terra` / `gpt-5.6-luna` | Fallback only if no Codex-specific model is available — highest / balanced / cheapest of the general GPT-5.6 family, respectively. |

**Reasoning choice.** Reasoning is the difficulty dial, not a prestige label — moving it up does
not make correct what an unclear prompt made ambiguous.

| Tier | Use for | This project's flavor |
|---|---|---|
| `low` | Mechanical, localized, low-risk: rename, one config value, formatting, a simple assertion change. Spec is clear, files are known, failure modes are obvious. | A single doc update or a one-line tag/log-retention change — cheaper than today's floor of `medium`. |
| `medium` | Default for normal implementation: a feature across a few files, handler/logic/DAL wiring, a focused bug fix, unit tests, a small infra change. | The convention table's **Mechanical** row (config/IaC edits, prompt-slot wiring) already lands here. |
| `high` | Complex or cross-cutting: needs careful sequencing and more than one verification pass, but the blast radius is contained. | The convention table's **Standard** row (handlers, DAL, contract/oracle tests) already lands here. |
| `xhigh` | High blast radius: data-model migration, auth/tenancy-sensitive change, hard concurrency/state bug, production-adjacent infra, ambiguous legacy behavior. Reserve — cost and latency rise. | Reserved for the same class of step the plan already marks `opus/xhigh` (P-24 identity surrogate, P-26 CFN decomposition) — this rule does not by itself promote anything into this tier that plan authorship hasn't already flagged. |
| `max` | Only for the hardest quality-first work where the extra cost is justified by clear evaluation criteria: review of a dangerous migration, a rollback plan, security-critical design review. | The convention table's **Hard** row already lands here (`codex/high(max)`, paired with `opus/xhigh`). |

**Fast decision table**, for the common shapes:

| Prompt shape | Selection |
|---|---|
| Edit one file / fix one small test | `gpt-5.3-codex` + `low` |
| Implement a spec with tests | `gpt-5.3-codex` + `medium` |
| Trace a cross-cutting failure (backend/frontend/infra) | `gpt-5.3-codex` + `high` |
| Plan or review a dangerous deploy/migration | `gpt-5.3-codex` + `high` or `xhigh` |
| Large ambiguous architecture change | `gpt-5.3-codex` + `xhigh` |
| Bulk repetitive edits, obvious pattern | Codex model + `low` |
| Cheap exploratory summary, no code edits | cheapest available model + `low` or `medium` |

**Rule of thumb.** Start at `medium`. Drop to `low` only when the task is genuinely mechanical.
Raise to `high` when the work crosses file/module boundaries, can break production behavior, or
needs non-obvious reasoning. Reserve `xhigh`/`max` for when the cost of a subtle mistake is high —
never as a default. **Never use a higher reasoning tier to compensate for a vague prompt.** If the
acceptance criteria, target files, or safety boundary aren't clear, that is a rule-14/rule-4
problem — fix the prompt, don't paper over it with more Codex reasoning.

**What this does not change.** It does not retroactively re-tier anything already recorded in
`redesign-execution-plan.md`'s table or in a landed prompt header — those stand as written; rule 8
governs revisiting a written value, this rule does not do it silently. It refines the resolution
available *going forward*, and fills the specific gap rule 15 left open: a skeleton or GATE row
with no `Claude/Codex` pair yet gets one from this rubric, not from whoever happens to fill it in
first guessing alone.

> **Amended 2026-07-25 (later same day):** rule 17 added while filling in Wave 2's `2.5` prompt —
> caught live, the same way rules 14–16 were, inside a prompt that names one spec file three
> different ways. Rules 1–16 unchanged.

### 17. Every file a prompt names is written as one full path from the repository root, never a bare relative fragment

A prompt is copy-pasted into a fresh session whose working directory is the repository root, not
the folder the prompt file happens to live in. A relative reference — `runbooks/wave-2-status.md`,
`../specs/P-25-payment-provider-spec.md`, `specs/P-25-payment-provider-spec.md` — only resolves if
the reader already knows which directory the author had in mind, and different lines in the same
prompt silently assume different ones. Write every file reference as the single full path from the
filesystem root:
`/Users/yitzchak.meirovich/Documents/code5/careervp/docs/db-redesign/code/code-analysis/project/runbooks/wave-2-status.md`,
never the bare fragment. This applies to **every** place a file is named — prose, a markdown link's
target *and* its visible text, a "confirm it exists" check, the header's `Spec` field, and a
commit-message file citation alike.

**The one carve-out is a shell snippet.** A command block may use paths relative to its own working
directory, but only when that directory is set by an explicit `cd <full absolute path>` at the top
of the same block — the `cd` is the anchor that makes the rest unambiguous. So
`cd src/backend && uv run pytest tests/unit/...` becomes
`cd /Users/yitzchak.meirovich/Documents/code5/careervp/src/backend && uv run pytest tests/unit/...`, never a
bare `cd src/backend` that assumes the reader started at the repo root. The paths *inside* pytest
or grep arguments then stay relative to that anchored `cd`, which is correct — a shell needs a cwd.

**The incident.** Found live while writing this rule: `wave-2-prompts.md`'s filled-in `2.0b` prompt
names the P-25 spec three different ways in the space of a few lines — the header's markdown link
points at `../specs/P-25-payment-provider-spec.md` (relative to `runbooks/`), its visible link text
reads `specs/P-25-payment-provider-spec.md` (relative to `project/`), and the STANDING CHECK's
`open specs/P-25-payment-provider-spec.md` line resolves only from a directory the block never names.
All three happen to point at one real file, but nothing in the prompt says so, and a reader who
starts from the wrong base gets a "file not found" on a spec that exists — the exact confusion
rule 14's spec-existence check exists to remove, reintroduced one layer down in how the path itself
is written.

**What this does not change.** Like the other amendments, it is not a retroactive rewrite of landed
prompts — those stand as written. It governs every prompt or skeleton written or filled in from here
forward, including the standard blocks below: wherever a template placeholder like `<spec file path>`
or `wave-N-status.md` is instantiated, it is instantiated as a full path.

> **Amended 2026-07-27 (rule 17a — the repo root is declared, not assumed):** rule 17 turned against
> itself. Rules 1–17 unchanged.

### 17a. The repository root is declared once per file, and every full path is built from it

**The incident.** The repository moved from `/Users/yitzchak/Documents/dev/careervp` to
`/Users/yitzchak.meirovich/Documents/code5/careervp`. Rule 17 had faithfully written **608
occurrences** of the old absolute path across the docs tree — including all 33 in
`wave-3-prompts.md` and every command in `PROMPT 3.1-RED`'s standing check. The rule whose entire
purpose is *"a cold session can paste this and it resolves"* had produced a runbook where the very
first command fails with `No such file or directory`, on a path that looks authoritative because it
is absolute. Rule 17 is still right — a bare relative fragment is worse — but an absolute path is a
**hardcoded environment assumption**, and this project already has a rule about those.

**What to do instead — three parts:**

1. **Declare the root once, at the top of the file**, as a labelled line:
   `**Repo root:** `/Users/yitzchak.meirovich/Documents/code5/careervp`` — so relocating the
   checkout is a one-line edit plus one mechanical sweep, not an archaeology exercise.
2. **Keep writing full paths in prose, headers, links, and checks** (rule 17 unchanged) — they are
   unambiguous, and a reader who is *not* pasting into a shell needs to see the real location.
3. **Anchor every shell block on the live root, not on a literal**:
   `cd "$(git rev-parse --show-toplevel)" && …`, or `cd "$(git rev-parse --show-toplevel)/src/backend" && …`.
   This is the carve-out rule 17 already grants, made self-healing: the block works on any checkout,
   and a wrong-directory paste fails loudly instead of silently reading the wrong tree.

**What was explicitly rejected, and why.** A *shim* — a header note saying "read every
`/Users/yitzchak/Documents/dev/careervp` in this file as the repo root" — is cheaper to write once
and more expensive forever: it leaves literal dead paths that a cold agent pastes into `ls`/`open`
and gets a not-found on, and it reintroduces exactly the "the reader must know what the author had
in mind" ambiguity rule 17 was written to delete. A *wholesale rewrite to bare repo-relative
fragments* fails the same test for the same reason. The mechanical rewrite is `sed`, whose authoring
cost is **one command regardless of occurrence count** — the expensive part was never the
replacement, it was reviewing a diff across archived documents that nobody will run again.

**Scope discipline for the sweep.** Fix the **live execution surface** — the current wave's prompts
and ledger, `RUNBOOK-RULES.md`, the prompt-authoring instruction, any runbook still queued to run,
and the root agent-instruction files. **Do not** sweep closed waves' prompt files or the archived
`docs/refactor*`, `docs/tasks/`, `docs/upgrade/` trees: those are history, they are not going to be
pasted into a shell, and churning them buries the real change in review noise. On 2026-07-27 that
was 63 occurrences across 7 files fixed, and ~545 in archived documents deliberately left alone.

---

## The two blocks every prompt must contain

Every copy-paste prompt in every wave-N-prompts.md file must include these two blocks, near
verbatim (swap in the correct wave number, file names, spec path, and acceptance-criteria IDs).
They implement rules 2–6 and 14 above.

The others are structural rather than per-prompt, and fire at different moments:

| Rule | When it fires |
|---|---|
| 7 (RED/GREEN are separate sessions) | when a clause is *split into prompts* |
| 8 (reinterpreting a written gate) | only when a gate is satisfied differently |
| 9 (bets) | when the wave is *planned*, and re-read at its gate |
| 10 (stopping conditions) | whenever anything is deferred |
| 11 (first prompt full, rest skeleton) | when the wave's prompt file is *created*, and again at each fill-in |
| 12 (re-runnable demonstration) | at the wave GATE |
| 13 (a test must be seen to fail) | inside every RED session, before GREEN starts |
| 15 (both models stated) | when the prompt/skeleton header is *written*, never left to the runner to guess |
| 16 (Codex side picked by rubric) | when a step's Claude model/effort is *decided* — plan authorship, or filling in a skeleton/GATE row rule 15 left open — never invented at prompt-writing time |
| 17 (file references are full paths) | when any prompt or skeleton is *written or filled in* — every file it names is a full path from the repo root |
| 17a (repo root declared, shell blocks anchored on `git rev-parse --show-toplevel`) | same moment as 17, plus whenever the checkout moves — then sweep the live execution surface only |

**Every prompt header states, without exception:** the clause id(s), the spec file path, the
acceptance-criteria IDs, and both `Claude: <model>/<effort>` and `Codex: <model>/<reasoning>` —
copied from the execution plan's row for that step (rule 15), with the Codex side derived per
rule 16 wherever that row didn't already exist. **`<model>` means the actual slug** (`gpt-5-codex`,
`gpt-5.3-codex` — rule 16's table) — `Codex: codex/high` is not a filled-in value, it is the bare
vendor name where a model belongs, and fails this check exactly as `Codex:` left blank would.

**Near the top, right after the prompt states what it's implementing:**

```
STANDING CHECK — before doing anything else: open wave-N-status.md. If the step immediately
before this one (in dependency order) left something open or unresolved, deal with that FIRST —
do not start this step's own work with unfinished business behind you. Then confirm THIS step's
own prerequisites are actually met right now, using a real command (not memory, not this file) —
if they are not, STOP and say so in plain English.

BEFORE WRITING ANY TEST (rule 14): confirm, with a real command, that <spec file path> exists, that
it has a "RED Tests to Write First" section naming <the acceptance-criteria IDs this prompt
implements>, and that each cited test names exact assertion values (no "or", no undefined
placeholders). If any of that is not true, STOP — author or fix the spec section first; do not
write tests against a spec that does not say what it is testing.
```

**At the end, inside "OUTPUT REQUIRED":**

```
ALSO REQUIRED (standing rule for every wave prompt — see runbooks/RUNBOOK-RULES.md):
- Compare what you actually built against (a) this prompt's own instructions and (b) the matching
  clause in project-scope-lock.yaml. If everything matches, say so in one plain sentence.
- If ANYTHING drifted — extra work not asked for, required work skipped, or a test/rule had to be
  weakened — STOP. Do not fix it yourself. Write one plain-English sentence a non-engineer could
  follow (what should have happened, what actually happened, why it matters), THEN the technical
  detail, and flag it for human review. Do not mark the step done.
- Update wave-N-status.md: add/update this step's row with a plain-English status, the commit,
  today's date, and anything the NEXT step must resolve first (or write "none").
```

> **Amended 2026-07-27:** rule 18 added when Fable was routed to Wave-3 implementation work for the
> first time. Rules 1–17 unchanged.

### 18. Fable is routed by rubric to long-horizon implementation, never to recon, RED, or security work

Rule 16 gives a rubric for picking Codex's tier against Claude's. It assumes Claude's own tier is a
choice among Sonnet and Opus. It is not any more: `claude-fable-5` is available, it is materially
more capable on long-horizon agentic work, and it costs **$10/$50 per MTok against Opus 5's
$5/$25** — 2×. Without a rule, "use the best model" collapses into "use Fable for everything",
which is the same failure rule 16 exists to prevent, one tier up.

Fable is not new to this project. `fable-infra-mitigation-plan` and `fable-findings-digest` are
already cited across `project-scope-lock.yaml` and drove clauses P-27 through P-30 — but those were
Fable used as an *analysis source*, one-off and human-run. This rule is about routing **steps** to
it.

**Route to Fable when all three hold:**

1. The work is **implementation against an already-pinned spec** — a GREEN step, a multi-file
   conversion, a demolition sweep. The specification exists and is not being discovered during the
   run.
2. It is **long-horizon**: many files, many steps, one coherent goal. Fable's documented strength is
   first-shot implementation of well-specified systems and sustained autonomous execution.
3. The cost is justified by the blast radius of getting it wrong — key authority, data shape,
   irreversible deletion.

**Never route to Fable:**

- **RED steps.** Writing tests against a spec whose assertion values are already pinned is precision
  work, not exploration. Rule 14 has already removed the judgment Fable would be paying for.
- **Recon, enumeration, and census work.** Counting call sites, listing env-var injections, parsing
  a synth template. This is breadth and care, not reasoning depth. Paying 2× for mechanical
  completeness is the exact waste rule 16 forbids.
- **Anything security-focused** — the P-04/P-05 IDOR work, P-07, X-01, X-02, and any auth or
  secrets slice. Two independent reasons: Fable's cyber classifiers can decline a request outright
  (HTTP 200, `stop_reason: "refusal"`), and its bug-finding gains are documented as **excluding**
  security-focused analysis. It is both less reliable and less available here. Use Opus.
- **Steps whose real blocker is a human decision.** A more capable model does not settle a question
  that requires the human's intent; it produces a more articulate recommendation. Route those to
  Opus and ask.
- **GATE steps.** A gate reads evidence and checks it against a contract. That is not the shape.

**Two hard gates to confirm before writing `fable` into any row:**

- **30-day data retention is required.** Fable is unavailable under zero data retention; a ZDR
  organization gets a `400 invalid_request_error` on **every** request regardless of payload. If a
  Fable-routed step fails immediately with a 400 and the payload looks fine, check the org's
  retention configuration before debugging anything else.
- **Refusals are a normal outcome, not an error.** A declined request returns HTTP 200 with
  `stop_reason: "refusal"`. A session that reads `content[0]` unconditionally will look like it
  produced nothing.

**Prompt shape changes for a Fable-routed step — and precisely how far.** Prompts written for prior
models are documented as *too prescriptive* for Fable, reducing output quality. That does **not**
license loosening this runbook. The distinction:

| Keep verbatim | Drop |
|---|---|
| The standing check, rule-14 spec verification, rule-5 stop conditions, the drift-comparison block, the status-ledger update | Step-by-step implementation scaffolding in the body — "first do X, then Y, then Z" |
| Acceptance criteria, exact assertion values, scope boundaries, the file-touching prohibition | Worked examples of *how* to write the code |
| Every full path (rule 17) | Redundant restatements of the same instruction in three places |

The rules and gates are contract enforcement and are non-negotiable. The implementation choreography
is what Fable does better unaided. **State the goal, the constraints, and the acceptance criteria up
front in one turn, then let it run** — its worst results come from a task specified progressively
across many turns. Expect single requests to run for minutes; that is normal, not a hang.

**Recording it.** Fable rows are written `fable/high` or `fable/xhigh` in
`redesign-execution-plan.md`'s per-step Claude column and copied verbatim into the prompt header per
rule 15. In a spec's `tooling:` frontmatter the form is `{claude_code: {model: fable, effort: high}}`.
`scope-diff.py` validates only that a tooling entry *exists* per clause, never the model string, so
this adds no drift-checker risk — and equally, no automated check will catch a mis-routed step.
That is what this rule is for.

**The Codex pairing is unchanged.** Rule 16's rubric still governs the Codex column; Fable on the
Claude side does not imply the largest Codex tier. Both engines are pointed at the same task and
should track the same difficulty judgment.

---

## For whoever writes the next wave's prompt file

1. Copy this file's link into the top of the new `wave-N-prompts.md` (see `wave-1-prompts.md`
   for the exact placement — right after the "READ FIRST" section).
2. Create `wave-N-status.md` before writing any prompts — seed it with one row per step, all
   marked "not started."
3. **Write the wave's bets before its prompts** (rule 9), into `ISSUES.md`. Planning the wave is
   when you know least and can still change the order cheaply; the gate is when you find out.
4. **Write the first prompt in full and the rest as contractual skeletons** (rule 11). Do not
   instantiate the whole wave.
5. Bake the two standard blocks above into every single prompt, not just the risky ones — including
   the rule-14 spec-verification line inside the standing check and both models on the header line
   (rule 15), the Codex side picked by rule 16's rubric wherever the execution plan doesn't already
   name it. **If the plan's own row still has the bare `codex/<tier>` form** (true today for every
   wave past Wave 2 — rule 16's known, tracked gap), do not copy that forward verbatim: resolve it
   to the real model (rule 16's table) in the new prompt file, the same fix already applied to
   Wave 2. A skipped small step is exactly where a silent problem hides. A skeleton carries these
   by reference (its `Spec`, `Acceptance criteria`, and model/effort fields); a filled-in prompt
   carries them verbatim, re-verified live, not copied on faith from the skeleton.
6. If you're validating a wave's prompt file against `project-scope-lock.yaml` (as was done for
   Wave 1), and you find a discrepancy between what the working plan says and what the contract
   file says — that is itself a rule-5 situation. Flag it in plain language, and don't treat the
   working plan as authoritative over the contract file, ever.
