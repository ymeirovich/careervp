# Plain English: where we are and what happens next

No jargon. Where a term is unavoidable it is defined the first time it appears.

---

## Part 1 — the words, decoded

| Term | What it actually means |
|---|---|
| **S0a, S0b, S1, S6, S7, S8, S10, S11, S11d, S23, S25, S26, K9** | Just ID numbers for suspected bugs, from an automated scan that produced ~100 of them. `S0` = the scanner thought it was worst. They carry no meaning beyond "bug #X". |
| **G1, G4** | Two things the scanner said were *fine*. We double-checked them on purpose, because a wrong "this is safe" is more dangerous than a wrong "this is broken". |
| **P-04, P-05, P-12, P-28, P-30…** | Numbered clauses in the project contract (`project-scope-lock.yaml`). "P" = must-do-before-launch. Plain versions: **P-04** = identity comes only from the login system. **P-05** = no user can read another user's data. **P-12** = databases can't be accidentally deleted. **P-28** = a human must approve every deploy. **P-30** = a smoke test runs before and after each deploy. |
| **T1 / T2 / T3** | Priority tiers. T1 = you cannot launch without it. |
| **Freeze line** | The list of work that must be finished before launch — currently **72 items** (51 T1 + 21 T2). Called "freeze" because once you're working it, you stop adding new features. |
| **Executable oracle green** | There is a script that checks the backend actually returns what the frontend expects. "Green" = it passes. It is an automated contract check between the two halves of the app. |
| **deployed_sha** | A stamp on the running system saying "the code live in AWS right now is exactly this version." Without it, a test result can't be tied to code you can read. Ours is missing — though we proved correspondence another way (below). |
| **Wilson interval** | Honesty about small samples. We checked 10 suspected bugs and 7 were real. "70%" sounds precise; with only 10 samples the true figure is somewhere between **40% and 89%**. The interval stops us over-trusting a small check. |
| **moto** | A fake AWS that runs on a laptop. Free and instant, but a simulator — passing there does not prove it works in real AWS. |
| **UNPROVABLE-WITHOUT-DEPLOY** | "We could not check this without a running system." It is **not** "it's fine." Treating it as fine is the mistake that already cost this project months. |
| **IDOR** | User A can fetch user B's data just by knowing or guessing an ID. |
| **Mutation testing** | Deliberately break the code and see whether any test notices. If nothing fails, that code is untested no matter what the coverage number says. |
| **Base rate** | Of the suspected bugs we actually checked, what share were real. |
| **Pass A / B / C, Tier 1-4, P1** | Labels for the review sessions themselves, not project concepts. **P1** = the first audit. |
| **devx** | The live test environment in AWS. Confusingly, its API stage is named `prod` — that is a name, not a production system. **There is no production environment yet.** |
| **CDK / CloudFormation / stack** | The code that creates the AWS infrastructure, and the group of AWS resources it creates. |
| **`make journey`** | The one command that matters. It drives a real browser through the whole product and reports **"REACHED N of 9"**. |

## Part 2 — what "done" actually means

Strip away the contract language and production readiness is one sentence:

> **A real person can sign in, upload a CV, create an application, get a VPR, answer gap questions, get a tailored CV, a cover letter, interview prep, and export the result — nine steps in a row, without a developer helping.**

That is literally what `make journey` measures. The nine steps:

| Step | What the customer does |
|---|---|
| J1 | Sign in |
| J2 | Upload their CV |
| J3 | Create an application for a job |
| J4 | Get their VPR (the core value-proposition report) |
| J5 | Answer the gap-analysis questions |
| J6 | Get a tailored CV |
| J7 | Get a cover letter |
| J8 | Get interview prep |
| J9 | Export it all to a document |

**This has never been run to completion. There is no result on record — not a low score, no score at all.** We do not know if the number today is 1 or 8.

## Part 3 — what the audits actually bought us

Blunt answer: **the three audit passes fixed nothing.** Zero code changed, zero infrastructure changed. Every prompt said "do not fix." They bought accuracy, not progress.

What accuracy is worth here:

- **Two suspected bugs were false.** S1 (a claimed data leak in CV tailoring) is unreachable — a real ownership check upstream blocks it. S2 (a claimed authentication bypass) can't be triggered the way it was described. Both would have been "fixed" at real cost, changing nothing.
- **One deletion was stopped.** The recommendation to delete the knowledge-base table rested on a single text search. That does not prove nothing uses it. Deleting it could have destroyed something.
- **One fix was pointed the right way.** The cancel bug is a same-key race, not the cross-database-schema problem originally described — so the originally proposed remedy would not have fixed it.
- **A trusted safety net turned out to be fake.** There is a test suite that certifies "no user can read another user's data" across nine routes. It is green. It proves nothing: it tests an attacker with no login at all, so every route stops at the front door and the actual ownership checks are never reached. One of its fixtures returns "not found" *even for the rightful owner*. This is the most important thing we learned, because that test was going to be the evidence for a launch gate.
- **We proved the deployed code matches the source.** All 137 backend files hash-matched against the live AWS bundle. This is a prerequisite for any live evidence meaning anything.

**What we did NOT do: close a single one of the 72 launch-blocking items.** If the next session is another audit, that is waste. The next session must produce working code.

## Part 4 — the plan

Five steps, in order. Do not reorder — step 1 tells you whether the rest of the list is even right.

### Step 1 — Get a number (half a day)
Run `make journey`. Record "REACHED N of 9."

Everything below is currently a guess about which step breaks first. This replaces the guess with a fact. It is also the first entry in the project's own scoreboard, which has been empty since the scoreboard was built.

### Step 2 — Fix whatever blocks the earliest failing step (days, depends on N)
Aim every change at step N+1. Re-run `make journey` after each one. If N goes up, commit. If N goes down, revert immediately and investigate second.

Confirmed real bugs, mapped to the step they touch, so you can pick the ones that matter:

| Step | Confirmed bug | Plain description |
|---|---|---|
| J4 | **S7** | When the AI fails quality checks twice, the system serves generic filler text as a finished VPR and reports success. A warning flag is set but nothing anywhere reads it. |
| J5 | **S6** | If the AI response can't be parsed, the system invents 10 template questions from the job description and returns success. Total AI failure looks identical to success. |
| J5 | **S25** | An application's status update always fails, because the code passes an empty user ID where a real one is required. The error is silently discarded. |
| J7 | **S8** | Cover letters are generated with **no gap answers at all**. The code looks them up in the wrong database table; the lookup always fails and the failure is swallowed. |
| J9 | **S0a** | **Any logged-in user can export any other user's VPR** by knowing the job ID, and gets a download link to it. Proven by test. |
| any | **S0b** | Same class: if the job record is missing (or the database hiccups), the status endpoint hands over another user's VPR plus a download link. Proven by test, with a control showing it correctly refuses when the record exists. |
| background | **K9** | The cleanup job has failed **336 times out of 336 runs over 14 days** — it requires a setting that its infrastructure never provides. It has never cleaned anything. |
| J6/J7 | **S10, S11** | Cancelling reports success even when every underlying write fails. Work and spending can continue while the user is told it stopped. |

Start with **S0a, S0b and K9**. They are confirmed, cheap, and independent of the journey result.

### Step 3 — Repair the fake safety net (1-2 days)
The cross-tenant test suite must actually test ownership:
- attack as a **logged-in** user, not an anonymous one;
- test **every** export type, not just the one that happens to be safe;
- add an **owner-positive control** to every denial test — prove the rightful owner *can* fetch the thing, otherwise "the attacker got nothing" means nothing.

Until this is done, no security gate can be honestly signed off.

### Step 4 — Close the deploy gate (half a day)
The contract (P-28) requires a human to approve every deploy. In reality three workflows deploy to AWS automatically on a push, and the approval gate points at a GitHub environment that doesn't exist. Fix the workflows, create the environment with a required reviewer, and provision genuinely read-only AWS credentials — the audits ran with full administrator access under self-restraint.

### Step 5 — Then, and only then, work the 72
With a real journey number, a trustworthy test suite, and a gated deploy, the launch checklist can be worked with instruments you have reason to believe.

## Part 5 — honest status

- **Product completeness:** unknown. Never measured end to end.
- **Launch checklist:** 72 items; the contract tracks each one's current state separately, and no independent count of closed items exists. That count is itself a task.
- **Known real defects:** 12 confirmed, listed above.
- **Known false alarms:** 2, removed from the queue.
- **Security:** two confirmed cross-user data leaks at the code level. Not yet demonstrated through the real login-protected URL — that test still needs running.
- **Biggest risk right now:** it is not any single bug. It is that the project has been measuring itself with instruments that report green without checking anything, and has 72 gates to close using exactly those instruments.
