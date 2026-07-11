# CareerVP — Council Prompt B: Parallel Rebuild

You are one member of a multi-lens architecture council. The question is a
**strategic fork**: instead of fixing CareerVP in place, should the owner build a
**corrected duplicate** of the platform side-by-side and cut over — and if so, how?

Read BOTH evidence files in full before answering, in order:
1. `/Users/yitzchak.meirovich/Documents/code/code-analysis/redesign/context-pack.md`
   (current state: defects, DAL, infra, constraints)
2. `/Users/yitzchak.meirovich/Documents/code/code-analysis/redesign/context-pack-rebuild-addendum.md`
   (capability surface, MVP→parity carve, coexistence contention)

Reason **only** from those files. Do not explore the repo.

---

## Re-council scope (this is a re-run — a same-model panel)

The prior rebuild-vs-in-place council already reached a verdict. **Concentrate on what the
§0 deltas change about that verdict:** the `core` target is now concretely specified (so both
rebuild and in-place have the same clean end-state), and live volume is confirmed tiny (users 908 /
artifacts 221 / rest <150 — so "avoid a risky large-data migration," a core rebuild argument, is
weak). Do NOT re-derive the full capability surface. Give a decisive verdict and only surface
findings where a delta changes the rebuild scorecard or a high-stakes assumption (identity keying,
knowledge keep/drop). Because this is a same-model panel, agreement is a weak signal — find where
the rebuild case is stronger (or weaker) than the prior council concluded.

## The decided parameters (do not re-litigate these)
- Parity model: **corrected MVP walking skeleton first → waves to full parity.**
- Topology: **side-by-side in the SAME AWS account**, gradual traffic routing,
  shared or copied data.
- All current-state constraints still bind (context-pack §7): **keep DynamoDB**,
  **solo developer**, **>70% margin**, security-conscious but **no GDPR gold-plating**,
  **backend + API-contract only**, **< 10k concurrent**.

## Your two-part job

**PART A — The decision.** Through your lens, argue **parallel rebuild vs. in-place
strangler-fig redesign** (the strangler-fig plan is documented in context-pack §6).
Be decisive, not balanced-for-its-own-sake. Weigh specifically for a **solo dev**:
- Rebuild upside: escape the frozen half-migration / 3-schema defect / god-class;
  build correctness in from day one; no risky in-place migration of live data.
- Rebuild cost/risk: reproducing the **entire** capability surface (§1) solo is a
  huge LOE; running **two platforms** doubles infra + risks double AI spend against
  the >70% margin; the 500-resource CFN ceiling makes same-account side-by-side hard;
  coexistence singletons (payment webhook, Cognito, EventBridge, shared SSM/data).
- State your lens's **verdict** (Rebuild / In-place / Hybrid) with the one or two
  reasons that dominate it.

**PART B — The how-to (assume rebuild proceeds).** Design the rebuild through your
lens: target design, sequencing across the MVP→Wave carve (§2), coexistence
mechanics (§3), and the specific risks/gates.

## Hard constraints
- Keep DynamoDB and improve it — the rebuild's data layer is a **clean** design, not
  a datastore change. Do NOT propose relational/other stores.
- Solo dev → every wave must be independently shippable and reversible; ruthlessly
  minimize what's in the MVP.
- Same-account side-by-side must not corrupt prod: the rebuild uses a **distinct env
  suffix** (§3) — call out anything that violates isolation.
- >70% margin must survive the coexistence period (two running systems).

---

## The lenses (6; Data-architect ×2 weight)

Assign one blind subagent per lens.

1. **Data architect (×2)** — the clean target model built from scratch (single-table
   `core` from day one, `CoreRepository` as sole key-builder, right GSI projections,
   transactions, connection reuse); AND the **old↔new data strategy** during
   coexistence (shared tables vs. own copy synced via Streams CDC — addendum §4 Q1).
2. **Security** — clean-slate least-privilege (per-function roles, no plaintext
   secrets, JWT-only identity from the start, tenant isolation by key design);
   **isolation between old and new** (own Cognito pool? own SSM paths? shared-data IDOR
   risk); personal-data export/delete built in. No GDPR gold-plating.
3. **Reliability / SRE** — building correctness in from day one (idempotency on money +
   at-least-once paths, DLQs wired, partial-batch failures, visibility timeout ≥6×,
   transactions, `max_concurrency` on AI workers) and **parity/shadow verification**
   (addendum §4 Q3) so the rebuild provably matches prod before cutover.
4. **Cost / margin** — the sharp lens: does running **two platforms** during
   coexistence survive **>70% margin**? Duplicate infra cost, double-AI-spend risk on
   shared traffic, on-demand DDB ×2, and how MVP→wave scoping and routing minimize the
   overlap window. Remember the dominant lever is LLM tokens.
5. **Delivery / effort (solo)** — anchors Part A. Realistically size the LOE of
   full-parity rebuild (§1 surface) for one person; is it feasible, or does it become a
   permanent two-system maintenance tax? What's the smallest MVP that proves value;
   where does the rebuild risk never reaching parity (the "80% rewrite" trap)?
6. **Coexistence & cutover** — the same-account crux: the 500-resource CFN ceiling,
   nested-stack budgeting, the **payment-webhook singleton**, env-suffix isolation,
   EventBridge rules kept disabled, traffic-routing mechanism (addendum §4 Q2), cohort
   cutover, rollback, and retiring the old platform.

---

## Output format (each lens)

### Lens: <name>

**Part A — verdict:** Rebuild / In-place / Hybrid + the 1–2 dominant reasons (from
this lens). Note the single biggest risk your lens sees in the rebuild path.

**Part B — findings** (only if rebuild proceeds) — for each:
- **Title**
- **Evidence** — cite the pack/addendum (e.g. "addendum §3", "context-pack §4 HIGH").
- **Recommendation** — concrete, DynamoDB-clean, solo-friendly.
- **Wave** — MVP / W2 / W3 / W4 / W5 (from addendum §2), or "cross-cutting".
- **Scores** — Importance (Critical/High/Med/Low) · LOE (S/M/L/XL) · Difficulty (Low/Med/High).
- **Coexistence risk** — does it touch a shared singleton / risk prod? (y/n + note).

**Blind spots** — what the MVP carve (§2) or coexistence notes (§3) miss from this lens.

**Dissent** — where you disagree with other lenses or with the MVP-first assumption.

---

## Synthesis (combined deliverable)

1. **The recommendation (Part A).** A single clear verdict — **rebuild, in-place, or
   a specific hybrid** — with the decisive reasoning, honest about solo LOE and the
   margin cost of coexistence. State the conditions under which the verdict flips.
2. **If rebuild (or hybrid): the how-to.**
   - **Target architecture** — the clean design in one paragraph + a diagram-in-words.
   - **MVP definition** — confirm or revise the §2 walking skeleton; state the exact
     smallest end-to-end slice.
   - **Wave sequencing** — ordered, each wave independently shippable, with scores.
   - **Coexistence plan** — data strategy (shared vs. synced copy), traffic routing,
     env/isolation, the payment-webhook + EventBridge handling, and cutover + rollback.
   - **Parity verification** — how the solo dev proves the rebuild matches prod per wave.
3. **Risk register** — top risks of the rebuild path, ranked, each with a mitigation
   (esp. the "never reaches parity" trap, double AI spend, prod-data corruption via
   shared naming, CFN ceiling).
4. **Rebuild vs. in-place — the honest scorecard** — a short side-by-side on effort,
   risk, time-to-value, and margin impact, so the owner can see why the verdict fell
   where it did.
5. **Open questions** (addendum §4) — which must be answered before starting, and the
   default you'd assume for each if forced to choose now.

---

## Success criteria (the run is DONE + trustworthy only when ALL hold)

- [ ] Every lens returned its Part-A verdict + (if applicable) Part-B findings, Blind spots, Dissent.
- [ ] Every finding cites the pack/addendum (§ / E#); uncited claims dropped.
- [ ] Part A ends in **one decisive verdict** (rebuild / in-place / specific hybrid) with the
  conditions under which it flips — not a fence-sit.
- [ ] The Synthesis contains all 5 parts, incl. the honest rebuild-vs-in-place scorecard.
- [ ] **Genuine dissent is surfaced** — zero disagreement on a same-model panel = FAILED run.
- [ ] **No recommendation contradicts the live-verified ground truth** (context-pack §7 /
  `findings-register.md` Live-verification) without flagging + justifying it.
- [ ] Coexistence singletons (payment webhook, Cognito, EventBridge) and the prod-corruption
  isolation guard are each addressed — a "how-to" that ignores them is incomplete.
- [ ] *(re-council only)* Every delta from the two updated docs is explicitly assessed.

Keep it concrete and evidence-linked. This seeds a rebuild implementation plan and a
test/parity strategy, so every item must be actionable and independently scoped.
