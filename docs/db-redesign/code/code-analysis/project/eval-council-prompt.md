# CareerVP — Implementation-Plan Evaluation Council

You are one member of a multi-lens council **evaluating the QUALITY of CareerVP's current
implementation PLAN** — the immutable contract, the execution runbook, the test strategy, the
orchestration design, and the one authored spec. **You are NOT reviewing code** (little to none
is written yet) and **you are NOT re-evaluating the Fable infra mitigation plan** — that plan is
one piece of *evidence* you use to pressure-test the current plan. Your job: **find the risks,
problems, and issues in the plan before execution begins, and propose fixes.**

Reason **only** from the files below. Do not explore the repo beyond confirming a cited
`file:line`. Every lens works from the same evidence so findings stay comparable.

---

## What to read

### A. THE PLAN UNDER REVIEW (the subject — read in full)
1. `/Users/yitzchak.meirovich/Documents/code/code-analysis/project/project-scope-lock.md` — the immutable contract (v1.3.0)
2. `/Users/yitzchak.meirovich/Documents/code/code-analysis/project/project-scope-lock.yaml` — machine-checkable twin
3. `/Users/yitzchak.meirovich/Documents/code/code-analysis/project/redesign-execution-plan.md` — the ordered runbook (v1.3.0)
4. `/Users/yitzchak.meirovich/Documents/code/code-analysis/project/test-strategy.md` — the test program
5. `/Users/yitzchak.meirovich/Documents/code/code-analysis/project/handoff.md` — the orchestration/self-drive design
6. `/Users/yitzchak.meirovich/Documents/code/code-analysis/project/specs/Q-gap-analysis-track-spec.md` — the ONLY authored spec; the exemplar for the ~20 still TO-AUTHOR

### B. EVIDENCE (inputs to test the plan against — verify, don't trust)
7. `/Users/yitzchak.meirovich/Documents/code/code-analysis/redesign/evidence/fable-findings-digest.md` — an **8 KB distilled digest** of the Fable deployment-safety analysis (independent, 5-role) of shipping several clauses without breaking the live Amplify frontend. **Evidence, not gospel — verify its load-bearing claims (several already checked in the live-truth file).** *(Full 62 KB verbatim at `fable-infra-mitigation-plan.md` — read only if a lens needs to drill into a specific claim; the digest is the default read to save tokens.)*
8. `/Users/yitzchak.meirovich/Documents/code/code-analysis/redesign/findings-register.md` — live-verified findings + the **Live verification** section (the ground-truth the plan derives from)
9. `/Users/yitzchak.meirovich/Documents/code/code-analysis/redesign/coverage-matrix.md` **§2** — the frontend can't-break contract
10. *(context, optional)* `redesign/requirements.md`, `redesign/features.md`, `redesign/db-upgrade-priorities.md`
11. **Live truth** — `/Users/yitzchak.meirovich/Documents/code/code-analysis/redesign/evidence/live-truth-2026-07-11.md` (recon.py + CFN counts, run 2026-07-11; raw recon at `redesign/evidence/recon-output-2026-07-11.txt`). **Live truth supersedes any static claim in A or B** — including the CFN-count conflict, already resolved there: deployed dev = **415/500** (register correct; Fable's 476 is not the deployed figure).

---

## Framing (read carefully)

- **You are grading a plan, not discovering a system.** "Quality" = **correct · complete ·
  internally consistent · traceable (FR→spec→test→clause) · executable by a *solo* dev ·
  deployment-safe · appropriately scoped for < 10k users.**
- **Same-model panel → agreement is a weak signal.** You are explicitly tasked to find where the
  plan is wrong, incomplete, internally inconsistent, over/under-scoped, mis-sequenced, or resting
  on an unverified assumption. A lens that only praises the plan has failed.
- **The Fable infra plan is evidence to verify, not a second authority.** Where it and the
  contract disagree, decide *which is right against live truth* — don't assume either.

## Known tensions to resolve (do NOT merely restate — reconcile each, decisively)

1. **CFN headroom conflict.** The contract/register say the parent stack is **415/500**; the
   Fable evidence says **476/500** and calls 415 "stale math." Live-verifiable. Which is true?
   Does it change P-26's urgency or Wave-0 sequencing? Does the register need a correction (amendment)?
2. **P-26 strategy conflict.** The contract says *"nest the whole RestApi (~175 resources → 1)"*;
   the Fable evidence says *"never move the RestApi — blue/green a new one beside it, re-point the
   base-path mapping, retire the old API later."* Different strategies with different blast radii
   on a live frontend. Which is correct/safer? Is the contract's P-26 an amendment away from the
   Fable approach?
3. **Dead rollback lever.** The Fable evidence claims `AUTHORIZER_DISABLED` (the lever P-04's
   safety implicitly assumes) has **zero readers** and that "instant revert" is really a 15–30 min
   redeploy. Does the plan's P-04 rest on a lever that doesn't exist? Is that a plan defect?
4. **Solo vs. team.** The Fable evidence scores effort "for a team of 2–3" and makes "a **human**
   executes every `ExecuteChangeSet`" non-negotiable. The contract's C-3 is **solo**. Is the plan's
   deploy-safety model realistic when the operator *is* the reviewer? What breaks?
5. **Missing deploy-safety gates.** The Fable evidence lists blocking pre-Wave-1 gates — CFN stack
   policy, termination protection, agent/human **credential split**, an **evidence snapshot pack**,
   a **4-wire smoke harness**, RETAIN-first. Does the execution plan / scope-lock actually encode
   these as steps/clauses? If not, that is a **coverage gap in the plan** — name the missing clauses.
6. **Specs-not-written risk.** Only **1 of ~21** specs exists. Is the plan's guarantee — that the
   nets (`scope-diff.py`, oracle) + the §8.6 acceptance gate + fresh-subagent authoring hold at
   scale — *credible*, or unproven? Where could it break across 20 unwritten specs?

## Hard constraints (from the scope-lock — obey; flag any recommendation that violates one)

- **Solo dev** → penalize big-bang / high-coordination work; favor incremental, reversible, flag-gated steps.
- **DynamoDB kept** (closed); **>70% margin** (LLM tokens are the lever, not infra); **no GDPR gold-plating**;
  **backend + API contract only**; **< 10k concurrent**; **dev-only until certified**.
- **NEVER break the frontend contract** (coverage-matrix §2) — version a route instead.
- **Amendment discipline:** any fix that changes an `IMMUTABLE` invariant, a locked decision, or a
  frontend-contract item MUST be proposed as an **amendment** (with clause + semver), not asserted
  (scope-lock §0.3). Tag every fix accordingly.

---

## The core question

**Is this project architecturally and programmatically SOUND to implement — such that a solo dev
following this plan produces a system that is correct, secure, cost-viable (>70% margin), and does
NOT break the live site?** Each lens must return a **soundness verdict** (SOUND / SOUND-WITH-
CONDITIONS / NOT-SOUND) for its domain, backed by the specific gap(s) that would make it unsound.
Plan hygiene (traceability, sequencing) matters only insofar as it threatens soundness — do not stop
at "well-organized." **Hunt for the flaw that ships a bug, breaches a tenant, blows the margin, or
takes down the frontend.**

## The lenses (6 soundness lenses — assign one blind subagent each; **Architecture soundness and
Correctness/site-break each carry ×2 weight** — they are "is it programmatically sound" and "will it
break the site," the two questions that dominate the go/no-go)

Each lens: give a **domain soundness verdict**, then answer its **Hard questions** (each with
evidence + a yes/no/uncertain call + severity), then surface anything the plan misses.

1. **Architecture soundness (×2)** — is the *target design* correct, or does the plan bake in a latent
   architectural vulnerability that surfaces at <10k users?
   Hard questions: (a) Does keying `core` on a surrogate `user_id` (resolve 1-or-many Cognito `sub`→
   `user_id` at the edge) add a correctness/latency hazard on the hot auth path — cache miss, brand-new
   `sub`, or a linking race? (b) Does the single-table `core` SK layout satisfy **every** live access
   pattern (61 API resources + async), or will some still need a Scan/GSI the plan never specced?
   (c) Does the status/in-flight query respect the GSI-cardinality rule, or is a low-cardinality GSI PK
   still lurking? (d) CR-first (`CR→gap→vpr→…`): does making CR **blocking** on submit gate the whole
   chain on a slow/failure-prone Tavily+LLM step — what happens when CR fails or times out? (e) Does the
   `UpdateItem`+`version` 409 pattern actually hold for large-body-in-S3 artifacts (pointer swap +
   version bump atomicity)? (f) Is "seams now, physical `core` collapse deferred" a safe resting state,
   or a permanent half-migration that's worse than either endpoint?
2. **Correctness & the site-break gap (×2)** — the "what takes the frontend down" lens (folds
   deployment-safety + the FE can't-break contract + the Fable evidence).
   Hard questions: (a) **Name the single change most likely to break the live site on deploy** and its
   blast radius — RestApi recreate (invoke-URL change, tension #2), three-layer CORS mismatch, the P-01
   `artifact_id` fix touching the contract, or something unlisted. (b) Does the plan encode the Fable
   deploy-safety gates (stack policy, termination protection, credential split, evidence pack, smoke
   harness) as **actual clauses/steps**, or are they missing (tension #5)? (c) Is "don't break the UI"
   *provable* — does the F-01 oracle assert **all 10** contract items incl. `vpr_id: null`-vs-absent and
   409-on-stale-version, or is a contract item unasserted? (d) Which clauses are `contract_impact:true`
   and does each have a versioning/back-compat plan, or could one silently change a response shape?
3. **Security soundness** — does the plan actually *close* the known vulns AND introduce no new ones?
   Hard questions: (a) After P-04/P-05, is identity **provably** JWT-only on all 31 handlers (no
   client-supplied id path survives), or is IDOR-by-construction just asserted? (b) Does the surrogate
   `user_id` + link-by-verified-email (O-4) leave an account-takeover path? (c) The **mock payment
   provider** — does self-signing test webhooks faithfully exercise signature verification, or bake in a
   bypass that ships when Stripe is swapped in? (d) KB/PFACT cross-application memory — is the tenant
   filter enforced **by key**, or is there a cross-tenant recall leak? (e) Prompt-injection / generated-
   artifact XSS (NFR-SEC-9) — is it owned by a spec, or an orphan NFR? (f) Is keeping `GatewayResponse
   ACAO '*'` (Fable's rec) actually exposure-free?
4. **Cost / margin soundness** — will **>70% margin** actually survive implementation, or is a decision
   resting on an unmeasured number?
   Hard questions: (a) The margin claim (~88%) rests on VPR economics from **2 Haiku samples** — which
   plan decisions are load-bearing on that unmeasured figure? (b) Does Q-04 (CR + KB into gap/vpr/cover/
   interview) blow the token budget — is the per-step digest + 1,200-token cap sized from data or
   hand-waved? (c) Does the plan **instrument real token metering (retire `len/4`) BEFORE** the Sonnet
   routing + Sonnet-5-migration decisions, or optimize blind? (d) Are GSI-`ALL`→minimized and
   Scan-elimination actually specced clauses, or aspirational?
5. **Spec & test quality** — will the plan's method actually produce *correct code* and *catch bugs*?
   Hard questions: (a) Is the `Q-gap` exemplar spec genuinely self-sufficient (a fresh subagent ships
   correct code with no extra context — the §8.6 claim), or does it still assume tribal knowledge?
   (b) With **1 of 21** specs written, is there any evidence the pattern *scales*, or does the whole
   plan rest on an unproven exemplar? (c) Do the coverage tiers + `mutmut` + characterization-first
   actually catch the class of bug that broke cover-letter/interview-prep (P-01), or would that defect
   slip again? (d) Which named test types (migration-parity, cross-tenant negative, load/perf, LLM-eval)
   will **no spec actually produce**?
6. **Delivery soundness & red-team (solo)** — can one person execute this soundly, and where does the
   plan *look* rigorous but isn't?
   Hard questions: (a) The single assumption that, if false, invalidates the plan (anchor still valid;
   live-state matches; amendment discipline holds under pressure; solo can sustain the fresh-subagent
   orchestration)? (b) The nets (`scope-diff.py`, oracle) are themselves **unbuilt Wave-0 deliverables**
   — so the "requirements can't rot" guarantee doesn't cover early Wave 0 itself; is that a real hole?
   (c) Reconcile the Fable "team-of-2-3 / human-gates-every-`ExecuteChangeSet`" model with a solo
   operator who is *both* author and approver — does the safety model still hold? (d) Where does the plan
   stall (the `core` collapse), and does it matter given that's post-launch?

---

## Output format (each lens returns exactly this)

### Lens: <name>

**Soundness verdict:** SOUND / SOUND-WITH-CONDITIONS / NOT-SOUND — one line + the single reason.

**Hard questions** — answer each of your lens's Hard questions above: `Q(x): <answer>` with a
yes/no/uncertain call, cited evidence (§ / `file:line`), and severity if it's a problem.

**Findings** — for each gap/vulnerability found:
- **Title** + **type** (architecture / correctness / security / cost / spec-test / delivery).
- **Evidence** — cite the plan doc + § or `file:line` (e.g. "scope-lock P-26", "Fable digest §missing-gates").
- **Failure it causes** — concretely: *ships a bug / breaches a tenant / blows margin / breaks the site / stalls delivery* — and the trigger.
- **Recommended fix** — concrete, solo-friendly.
- **Amendment?** — `y/n`; if `y`, which clause + semver (patch/minor/major) + why.
- **Scores** — Importance (Critical/High/Med/Low) · LOE (S/M/L/XL) · Difficulty (Low/Med/High).

**Blind spots** — what the plan (or the prior analysis) misses from this lens.

**Dissent** — where you disagree with the plan, the Fable evidence, or other lenses.

---

## Synthesis (the council's combined deliverable)

1. **Overall soundness verdict** — one of SOUND / SOUND-WITH-CONDITIONS / NOT-SOUND for the project
   as a whole, plus a **per-domain scorecard** (architecture · correctness/site-break · security · cost ·
   spec-test · delivery, each SOUND / CONDITIONS / NOT-SOUND). Weight Architecture and Correctness ×2.
2. **The blocking gaps** — the specific vulnerabilities that make any NOT-SOUND / CONDITIONS domain so,
   ranked, each tagged with the failure it causes (bug / tenant breach / margin blow / site break / stall).
   Call out **the single gap most likely to break the live site.**
3. **Required plan changes, split into two buckets:**
   (a) **Spec/runbook fixes** (mutable — edit the plan/steps/test-strategy), and
   (b) **Contract amendments** (each with proposed clause text + semver + rationale, ready for §0.3).
4. **Consensus vs. disagreement** — where lenses agreed (a shared prior to stress, not corroboration)
   and where they genuinely conflicted (especially the two ×2 lenses vs. the rest).
5. **GO / NO-GO to implement** — a decisive verdict: is the project sound to start building as written,
   or what *specifically* must be fixed first (the blocking subset of 3a/3b). "Sound with conditions"
   must list the exact conditions.

---

## Success criteria (the run is DONE + trustworthy only when ALL hold)

- [ ] Every lens returned a **soundness verdict**, answered **all its Hard questions** (yes/no/uncertain + evidence), and gave Findings / Blind spots / Dissent.
- [ ] Every finding cites plan-or-evidence (§ / `file:line`) AND names the **concrete failure it causes** (bug / tenant breach / margin blow / site break / stall); uncited or consequence-free claims are dropped.
- [ ] The Synthesis contains all 5 parts, incl. the **per-domain soundness scorecard**, the **single most-likely site-break gap**, the fixes-vs-amendments split, and a decisive **GO/NO-GO to implement**.
- [ ] **Decisive answers on all 6 known tensions** — no "it depends."
- [ ] **Genuine dissent surfaced.** Zero disagreement on a same-model panel = FAILED run; re-run with sharper adversarial framing.
- [ ] **No recommendation contradicts live-verified ground truth** (live-truth file / findings-register) without explicitly flagging and justifying it.
- [ ] Every proposed fix is tagged **amendment (y/n)**; no contract-touching fix is asserted without an amendment proposal.
- [ ] The **Fable evidence is treated critically** — its load-bearing claims (476/500, dead `AUTHORIZER_DISABLED`, blue/green P-26) are verified/challenged, not adopted wholesale.
- [ ] A domain marked **SOUND** is backed by evidence it *closes* its risk — not merely "the plan mentions it." Absence of a spec for a named risk = NOT-SOUND for that risk, not SOUND.

---

## Setup & run notes (do these BEFORE running — they are the quality + token levers)

- **Save the Fable plan locally first** — blind subagents can't fetch the GitHub URL. Write it to
  `redesign/evidence/fable-infra-mitigation-plan.md`. (Source:
  `github.com/ymeirovich/careervp/blob/main/docs/db-redesign/claude-council-db-redesign-infra-mitigation-plan.md`.)
- **Pre-resolve the live contradictions.** Run `recon.py --env dev` + targeted read-only CLI and
  paste the answers into the evidence *before* the council: (a) actual parent-stack resource count
  (415 vs 476); (b) is Cognito auth enforced in the deployed dev stack; (c) does `AUTHORIZER_DISABLED`
  have any readers. Reasoning from resolved fact (not speculation) is the single biggest quality lever
  and stops six subagents hedging over the same unknowns.
- **Model / effort (TOKEN-OPTIMIZED — Team Premium):** run **`--local` (NOT `--agents`) on Fable at
  effort `high`**, in ONE session (set Fable + `high` once — local subagents inherit session effort).
  Fable gives genuine distance from the Opus/Sonnet-authored corpus (it didn't write it); the
  Fable-authored *evidence* is quarantined as a claim to verify. Rationale for the cheap config:
  dropping `--agents` (~2× fewer turns) and `high` vs `xhigh` roughly halve the run with no
  meaningful loss for a soundness review; the 8 KB Fable digest (vs 62 KB) cuts the input. **6
  soundness lenses** (2 weighted ×2) with per-lens Hard-question banks — the question banks *focus*
  each subagent, which keeps output tight despite the extra depth. **Est. ~350–450k tokens** (< ~1%
  of a Team Premium week). **Dial up only if a domain comes back `SOUND-WITH-CONDITIONS`/inconclusive:**
  re-run just the Architecture or Correctness (×2) lens at `xhigh` — cheap on your plan, and those are
  the two that dominate the go/no-go.
- **Token discipline:** subagents read the plan corpus (A) in full — it is the subject, never
  distill it — plus the **8 KB Fable digest** (not the 62 KB verbatim), the 5 KB live-truth file,
  register Live-verification section, and coverage-matrix §2. Do NOT hand them the whole careervp
  repo; use `file:line` snippets for any cited code.
- **Command (optimized):**
  `/claude-council:ask "$(cat /Users/yitzchak.meirovich/Documents/code/code-analysis/project/eval-council-prompt.md)" --local`
- **After the run:** the Synthesis's bucket (2b) feeds the scope-lock amendment process (§0.3); bucket
  (2a) edits the plan/specs/test-strategy directly. Save the output to
  `project/eval-council-output.md`.
