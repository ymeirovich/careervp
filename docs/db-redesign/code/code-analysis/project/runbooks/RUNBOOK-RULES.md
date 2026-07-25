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

## The fifteen rules

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

**Every prompt header states, without exception:** the clause id(s), the spec file path, the
acceptance-criteria IDs, and both `Claude: <model>/<effort>` and `Codex: <model>/<reasoning>` —
copied from the execution plan's row for that step (rule 15).

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
   (rule 15). A skipped small step is exactly where a silent problem hides. A skeleton carries these
   by reference (its `Spec`, `Acceptance criteria`, and model/effort fields); a filled-in prompt
   carries them verbatim, re-verified live, not copied on faith from the skeleton.
6. If you're validating a wave's prompt file against `project-scope-lock.yaml` (as was done for
   Wave 1), and you find a discrepancy between what the working plan says and what the contract
   file says — that is itself a rule-5 situation. Flag it in plain language, and don't treat the
   working plan as authoritative over the contract file, ever.
