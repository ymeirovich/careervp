# Runbook Standing Rules

**What this file is:** the rulebook every wave-prompt file (`wave-0-prompts.md`,
`wave-1-prompts.md`, `wave-2-prompts.md`, …) must follow. Whoever writes a new wave's prompt
file — human or agent — must apply these six rules to every prompt in it, and must link this
file from the top of the new wave-prompts file. This is the fix for a real problem found while
building `wave-1-prompts.md`: status lived only in loose prose inside the prompt file itself,
so it went stale and nothing forced the next prompt to notice.

---

## The six rules

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

---

## The two blocks every prompt must contain

Every copy-paste prompt in every wave-N-prompts.md file must include these two blocks, near
verbatim (swap in the correct wave number and file names). They implement rules 2–6 above.

**Near the top, right after the prompt states what it's implementing:**

```
STANDING CHECK — before doing anything else: open wave-N-status.md. If the step immediately
before this one (in dependency order) left something open or unresolved, deal with that FIRST —
do not start this step's own work with unfinished business behind you. Then confirm THIS step's
own prerequisites are actually met right now, using a real command (not memory, not this file) —
if they are not, STOP and say so in plain English.
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
3. Bake the two standard blocks above into every single prompt, not just the risky ones. A
   skipped small step is exactly where a silent problem hides.
4. If you're validating a wave's prompt file against `project-scope-lock.yaml` (as was done for
   Wave 1), and you find a discrepancy between what the working plan says and what the contract
   file says — that is itself a rule-5 situation. Flag it in plain language, and don't treat the
   working plan as authoritative over the contract file, ever.
