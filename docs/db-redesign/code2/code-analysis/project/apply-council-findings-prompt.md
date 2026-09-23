# Apply the Eval-Council Findings — Bring CareerVP's Plan to Production-Ready

## Context

An implementation-plan evaluation council (6 blind lenses: Architecture ×2, Correctness/site-break ×2,
Security, Cost/margin, Spec & test quality, Delivery/red-team-solo) just finished reviewing CareerVP's
full planning corpus. Verdict: **SOUND-WITH-CONDITIONS** across every domain — the architecture and
method are right, but a specific, cheap-to-fix set of gaps stands between this plan and a safe production
launch. Full output, including all 6 verbatim lens reports, the ranked blocking-gap list, and 14
ready-to-file amendment proposals (A1–A14), is at:

`/Users/yitzchak.meirovich/Documents/code/code-analysis/project/eval-council-output.md`

**Your job in this session: apply those findings to the actual project docs** — process the contract
amendments through the scope-lock's own amendment discipline, apply the runbook/spec fixes directly, patch
the exemplar spec, and close the production-readiness gaps the council identified as out-of-plan. When
you're done, the corpus should reflect a plan that is genuinely ready to execute toward production, not
just dev-certified.

## Read first (in this order)

1. `/Users/yitzchak.meirovich/Documents/code/code-analysis/project/eval-council-output.md` — the council's
   full findings. Read section "3. Required plan changes" and "5. GO/NO-GO" closely — that's your work
   order. Also read the "PRODUCTION-READINESS ANSWER" at the bottom — Layers 1/2/3.
2. `/Users/yitzchak.meirovich/Documents/code/code-analysis/project/project-scope-lock.md` — the contract
   (v1.3.0/v1.4.0). Note §0.3 (amendment procedure), §0.4 (tier definitions), §12 (changelog).
3. `/Users/yitzchak.meirovich/Documents/code/code-analysis/project/project-scope-lock.yaml` — machine
   twin; every amendment to the .md must be mirrored here.
4. `/Users/yitzchak.meirovich/Documents/code/code-analysis/project/redesign-execution-plan.md` — the
   runbook (steps, waves, deps).
5. `/Users/yitzchak.meirovich/Documents/code/code-analysis/project/test-strategy.md`
6. `/Users/yitzchak.meirovich/Documents/code/code-analysis/project/handoff.md`
7. `/Users/yitzchak.meirovich/Documents/code/code-analysis/project/specs/Q-gap-analysis-track-spec.md` —
   the exemplar; has specific defects named by the council (Lens 5, Lens 1).
8. `/Users/yitzchak.meirovich/Documents/code/code-analysis/redesign/evidence/live-truth-2026-07-11.md` —
   ground truth; nothing you write may contradict it without flagging why.

## What to do

### Step 1 — Contract amendments (bucket b), through proper §0.3 discipline

Work through the council's amendment table (A1–A14) one at a time. For each:
- Locate the exact clause in both `project-scope-lock.md` and `project-scope-lock.yaml`.
- Apply the council's proposed change (the table gives clause + semver + rationale — use it as a strong
  draft, not gospel; sanity-check it against the clause's current text and the live-truth file before
  writing).
- Bump the version per semver (PATCH/MINOR as specified — nothing in this batch is MAJOR).
- Add a changelog row in §12 for every amendment, dated 2026-07-11, citing the council run as the source.
- Keep `project-scope-lock.md` and `.yaml` in sync (twin-sync) — do not let them drift.
- For contract-touching amendments the council flagged as needing adversarial review (P-26, P-04, P-07,
  P-24-adjacent), do NOT skip that step yourself: after drafting the amendment, spawn a fresh subagent via
  the Agent tool with a prompt like "adversarially refute this amendment — find the way it's still wrong"
  before finalizing. Record the outcome.

Do all 14 (A1–A14). Where two lenses proposed overlapping fixes for the same clause (e.g. P-26 touched by
both Lens 1 and Lens 2, P-04 by Lens 2 and Lens 3), the eval-council-output.md's §4 "Consensus vs
disagreement" already reconciled which version wins — use that reconciliation, not either lens's raw text.

### Step 2 — Runbook/spec fixes (bucket a)

Apply all items in council §3(a) directly — these are not amendments, just edits:
- Dependency wiring fixes in `redesign-execution-plan.md` (step 0.65 ← 0.61/0.62/0.63; step 0.7 ← 0.62;
  reorder 0.61/0.62 before 0.6; split step 1.3 into 1.3a/b/c; swap CR margin-guard ordering in Wave 4).
- `handoff.md`: rewrite the "your only jobs" section to include all four human duties (O-# decisions, wave
  gate approvals, every ExecuteChangeSet, every amendment confirmation); delete the stale
  `prompt:`-block instruction (replace with the actual v1.3.0 format).
- The exemplar spec (`Q-gap-analysis-track-spec.md`) — this is the highest-leverage single file to fix,
  since ~20 more specs will imitate it. Patch it to:
  - Add `AC-###` Given/When/Then sections per clause (currently has none — Lens 5 finding 1).
  - Conform its frontmatter to the mandated §8.5 schema, or explicitly extend §8.5 to permit list-valued
    `scope_lock_clause` + the `tooling:` map (pick one — don't leave the contradiction).
  - Add RED tests for CR failure/timeout: `test_chain_cr_failure_degrades_not_blocks`,
    `test_chain_cr_timeout_policy`.
  - Define the Q-04 CR digest: field list + explicit token cap + counting method (don't leave
    `<digested CR>` undefined).
  - Remove the "(or logged fallback)" ambiguity in the missing-CV test; pin Q-02's error to the coverage-
    matrix §2 item-10 envelope + explicit status code.
  - Replace or supplement the hand-mocked RED test (`DynamoDalHandler.get_cv_by_id` patch) with at least
    one moto-backed, real-key-schema test — the whole point of T-02 is banning exactly this pattern.
- Operationalize §8.6 gates 3 and 5 in `test-strategy.md` per Lens 5/6's fix: gate 3 becomes a fresh-
  subagent dry-run that must return an empty `questions: []`; gate 5 splits into a spec-time lint (no
  ambiguous "or" assertions, no undefined constants) and an implement-time recorded red-green step, with
  the mutmut spot-check moved to the Wave-3 gate instead of Wave 5.
- Add the missing invariant to `project-scope-lock.yaml`'s `invariants:` list:
  `gsi_pk_user_or_high_cardinality_scoped_or_sparse_never_status`.
- Reconcile the TO-AUTHOR spec count in `redesign-execution-plan.md` (currently lists ~30 entries with
  duplicates) against T-06's "~15–20" — dedupe and make the two numbers agree.

### Step 3 — The three hard blockers (do these with extra care — council flagged them GO/NO-GO gates)

1. **P-26 (step 0.65)** — after amendment A1 lands, re-read step 0.65's text in the execution plan and
   rewrite it to match the amended clause (custom domain+ACM first, blue/green new RestApi in its own
   stack, human-only base-path flip, retire-old-API-later, explicit "do not move the Cognito pool"
   exclusion, precondition to read the P-29 evidence pack for `NEXT_PUBLIC_API_URL`).
2. **Step 0.4 (mass spec fan-out)** — do not just patch the exemplar; add an explicit runbook gate: "run
   one full author→implement red-green cycle on Q-02 before authoring the remaining ~20 specs." Write this
   as a real step insertion in the execution plan, not a footnote.
3. **Step 1.1 (P-04/P-05 auth flip)** — resequence: pull P-23 (canary/alias rollback + CodeDeploy) into
   Wave 1 ahead of P-04/P-05; add a 401-rate CloudWatch alarm to P-04's definition of done; add the
   exhaustive 31-handler route×handler table requirement to the P-05 spec's future acceptance criteria
   (you won't have the actual route list in this session unless you can read the CDK source — if you
   can't reach it, write the requirement into the clause/spec so the future spec-author subagent produces
   the table, rather than trying to enumerate handlers from stale docs).

### Step 4 — Layer 2: production-readiness gaps the plan never claimed to cover

The council's synthesis names 7 items production needs beyond the current plan's own dev-only finish
line (C-7). Decide, for each, whether it becomes a new scope-lock clause (if it changes committed scope)
or a note/open-question (if it's a future decision):
1. Real payment provider + signature verification before a *paid* launch (this is P-25b from the
   amendment table — should already be covered by Step 1).
2. A priced denominator for the >70% margin gate (add to Q-10's spec content, not necessarily a new
   clause).
3. A load/perf test harness that actually measures O-1's go/no-go metric (fold into P-20/P-32 per the
   council's fix, already in Step 2).
4. A measured (not estimated) rollback RTO — add as a Wave-0 "fire drill" runbook step.
5. Prod promotion mechanics (account/credential separation from dev, prod backups, the certification gate
   itself) — this is currently unscoped. Propose it as a new OPEN question (O-#) or a new post-launch
   track, not a silent addition — the contract's own discipline (§0.3) requires this to go through the
   same review, and it may need the human's input on account structure. If you're not confident on the
   shape, write it up as a clearly-flagged open question rather than inventing clauses unilaterally.
6. End-to-end XSS closure verification (backend encoding is owned by X-02; the sink is the frontend,
   nominally out of scope by C-6) — flag this as a cross-boundary risk needing one explicit test task, and
   note it plainly; don't silently expand scope past C-6 without flagging that you're doing so.
7. An operator-continuity / safe-pause procedure for mid-wave stops — add as a short runbook addendum
   (not a contract amendment; this is operational guidance).

### Step 5 — Verify internal consistency before you finish

- Confirm `project-scope-lock.md` and `.yaml` are still twin-synced (every clause, invariant, and
  changelog row matches across both files).
- Confirm no amendment you made contradicts `live-truth-2026-07-11.md` — if it seems to, flag it
  explicitly rather than silently reconciling.
- Confirm the version number and changelog in §12 reflect the full batch of changes as one coherent
  release (decide: one version bump for the whole batch, e.g. v1.5.0, or itemize — your call, but be
  consistent and explain the choice).
- Re-read the "GO/NO-GO" section of the council output one more time and confirm each of the three named
  blockers is actually resolved by what you wrote, not just gestured at.

## Constraints (do not violate)

- **Solo dev, no team assumed.** Every fix must be executable by one person; don't introduce anything
  requiring parallel human reviewers.
- **DynamoDB stays.** No infra swap.
- **No GDPR gold-plating.** Don't expand compliance scope beyond what's already committed.
- **Don't touch code.** This session edits planning documents only — no CDK, no Lambda handlers, no
  actual deploys. The council reviewed a plan; you are fixing the plan.
- **Amendment discipline is not optional even for your own edits.** If you find yourself wanting to change
  an IMMUTABLE clause's substance (not just its safety conditions), stop and flag it as a question for the
  user rather than doing it — per the plan's own §9.3 anti-pattern list, silently rewriting locked
  decisions to fit convenience is exactly the failure mode this whole exercise exists to prevent.
- **Don't invent scope the council didn't name.** If you spot something adjacent that looks broken while
  you're in these files, note it as a new open question rather than fixing it inline — stay inside the
  council's findings for this pass.

## Deliverable

When done, produce a short summary (not a new document unless useful) covering: which of the 14
amendments landed and at what version, which runbook/spec fixes were applied, what changed in the
exemplar, how the three hard blockers were resolved, and which Layer-2 items became new clauses/open
questions vs. which were folded into existing specs. Flag anything you could not resolve without the
human's input (e.g., account-structure decisions, pricing numbers) as explicit open questions rather than
guessing.
