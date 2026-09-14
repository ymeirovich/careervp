# Handoff request → Codex: best practices for validating adversarial-validation output with Astra

**Paste everything below the line into a fresh Codex session. Do not give it the
findings themselves — this request is for methodology only.**

---

You are being asked for **methodology guidance only**. This is a request for a
best-practices document, not for analysis.

## Hard scope boundary — read this first

- **Do NOT ask me for the findings, the repository, the code, or any evidence.**
  None will be provided in this session, by design.
- **Do NOT validate, adjudicate, critique, or speculate about any specific
  technical finding.** You have none, and inventing plausible examples would
  defeat the purpose.
- **Do NOT write code, open files, or run repository tooling.**
- Your entire deliverable is a **methods document**: how to configure and prompt
  Astra for the task described below, and how to tell whether its output can be
  trusted.

If you find yourself starting to reason about a hypothetical bug, stop — that is
out of scope.

## The task these practices will serve

A prior agent session performed **adversarial validation** of an automated defect
inventory for a pre-launch AWS serverless application. Concretely, that session:

- Took ~100 machine-generated findings, each carrying a `file:line` citation, and
  treated every one as **unvalidated**.
- Adjudicated a subset using **three-state verdicts** — CONFIRMED / REFUTED /
  UNPROVABLE-WITHOUT-DEPLOY — where "I could not check this" is never recorded as
  "this is fine."
- Required **execution evidence** over reading: in-process tests against mocked
  AWS (moto), read-only live AWS API calls, mutation testing of security controls
  in throwaway git worktrees, and micro-benchmarks for performance claims.
- Labeled every assertion **OBSERVATION** (command + actual output), **INFERENCE**
  (reasoned from stated observations), or **OPINION** (judgment).
- Treated **refuting a claim as a higher-value outcome than confirming one**,
  because a false finding costs days of work on a bug that does not exist.
- Produced a base rate: what fraction of sampled findings were real, and what
  fraction carried a materially wrong premise, trigger, severity, or mechanism.

**The calibrating failure mode.** The single most expensive error class in this
project was *not* a hallucinated finding. It was a confident, specific, cited,
fully reproducible failure that turned out to be an artifact **of the measuring
instrument rather than the system** — a verification script matched one
CloudFormation resource type while the infrastructure synthesized a different
one, so a healthy system read as catastrophically broken. It survived two layers
of analysis before a raw API call caught it. Any methodology you recommend must
be judged primarily on whether it catches that class of error.

## What I now need Astra to do

A **second, independent pass that validates the validation** — second-order
adversarial review. Astra's job will be to determine whether the prior session's
verdicts, evidence, and reasoning hold up: whether its tests actually tested what
they claimed, whether its refutations were themselves correct, whether its
"confirmed" verdicts rest on sound instruments, and whether its base-rate
inference is defensible.

This is meaningfully harder than first-order review, because the prior session's
output is *fluent, cited, and internally consistent* — the exact profile most
likely to induce agreement. The failure mode I am most worried about is Astra
reading a well-structured verdict document and ratifying it.

## What to give me

Please answer the following. Where you are uncertain, say so explicitly rather
than producing confident filler — an honest "this depends on X, and I don't know
X" is more useful to me than a smooth answer.

### 1. Ground the model choice (answer this first)

I have been referring to **"Codex Astra."** Before anything else: **confirm
whether that is a real, current Codex model, tier, or mode, and correct me if the
name is wrong or stale.** If it does not exist under that name, tell me plainly
and map my intent to whatever the actual current capability is. Do not build
recommendations on a name you cannot verify.

Then cover:
- What Astra (or its real equivalent) is genuinely strong and weak at, relative
  to the other current Codex tiers.
- The reasoning-effort setting you would use for second-order adversarial review,
  and why — including when a *lower* effort tier is the better instrument.
- Whether this task should be one Astra session or several, and if several, how
  to split it so the passes stay independent rather than compounding each other's
  assumptions.

### 2. Input packaging and independence

- How much of the prior session's output should Astra see, and in what order?
  Is there value in withholding the prior verdicts and having it derive its own
  first, then diff — or does that waste effort?
- How do I stop Astra from **anchoring** on the prior session's conclusions,
  given that it must read them to check them?
- What belongs in the prompt versus in attached files versus left in the repo for
  it to discover? Any practical context-budget guidance.
- How should I represent evidence that was produced by a *command* (test output,
  AWS CLI JSON) so Astra treats it as a claim to re-run rather than a fact to
  accept?

### 3. Prompt structure that maximizes refutation

- Framing, role, and instruction patterns that measurably increase the rate at
  which a model challenges rather than ratifies prior work.
- How to make "REFUTED" a *rewarded* outcome in the prompt without biasing toward
  manufacturing disagreement — I want calibration, not contrarianism. How do you
  tune that balance, and how would I detect that I have overshot it?
- Specific wording or structural devices you have found effective for forcing a
  model to re-derive a mechanism instead of paraphrasing a citation.

### 4. Evidence standards and the instrument problem

- How to make Astra **run commands rather than assert**, and how to verify from
  its transcript that it actually did.
- Patterns for forcing a **control experiment** alongside every positive result
  (the prior session, for example, paired "attacker is denied when the record
  exists" against "attacker succeeds when it does not").
- How to get Astra to routinely ask *"is this failure a property of the system or
  of my test harness?"* — including any checklist or prompt scaffold you would
  embed for that specific question.
- How should three-state verdicts be enforced so UNPROVABLE does not silently
  decay into PASS?

### 5. Known failure modes to guard against

- Astra-specific (or current-Codex-specific) failure modes relevant here:
  sycophancy toward supplied reasoning, citation fabrication or drift, silent
  context truncation on long documents, premature convergence, tool-call
  avoidance, over-long autonomous runs that lose the thread.
- For each: the **detection signal** I can look for in the output, and the
  mitigation I should bake into the prompt.

### 6. Output contract

- A concrete output structure for Astra's verdicts that is easy to **diff against
  the prior session's verdicts** — ideally something machine-checkable.
- How to require reproduction commands and raw output inline, rather than prose
  describing them.
- How Astra should express disagreement with the prior session: what constitutes
  sufficient grounds to overturn a CONFIRMED, and what to do when both sessions
  are uncertain.

### 7. Operational limits

Context window, tool and sandbox availability, network/cloud access, timeout and
long-run behavior, cost profile, and any hard limits that would change how I
split the work.

### 8. Anti-patterns

The things people most often get wrong when pointing Codex at
validate-the-validator work, stated as "do not do X, because Y."

## Answer format

A single markdown document, organized under the eight headings above. Favor
specific, copy-pasteable prompt fragments and concrete settings over general
advice. Mark anything you are unsure about with **[UNCERTAIN]** and say what
would resolve it.

End with a short section titled **"Minimum viable prompt skeleton"** — the
smallest prompt structure you would consider adequate for this task, which I will
expand into the real one.

Remember the boundary: methods only. If you are unsure whether something is in
scope, it probably is not.
