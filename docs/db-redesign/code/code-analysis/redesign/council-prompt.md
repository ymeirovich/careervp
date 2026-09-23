# CareerVP Redesign — Council Prompt

You are one member of a multi-lens architecture council reviewing the **CareerVP**
backend. Read the context pack in full before answering:

`/Users/yitzchak.meirovich/Documents/code/code-analysis/redesign/context-pack.md`

Reason **only** from that pack. Do not explore the repository — every lens works
from the same evidence so findings stay comparable.

---

## Re-council scope (this is the 3rd pass — a same-model panel)

The prior two councils already produced a ranked backlog and a wave plan; a blind full
re-derivation would only re-state them (low value). **Concentrate your fire on:**
(a) the **§0 deltas** — the newly-specified `core` design: SK layout, the hot-partition
**GSI-cardinality rule** (no `STATUS#{status}` GSI PK), the artifact-edit `UpdateItem`+`version`
(409) write pattern, DRY-at-the-code-layer, and what stays out of `core`; and
(b) the **four §8 high-stakes decisions** (HS1 identity keying · HS2 is `core` committed or a
hypothesis · HS3 knowledge keep/drop · HS4 cutover/retention).
For the rest of the documented plan, only flag where a delta **moves** a prior finding's
severity/priority/effort — do not re-list unchanged items. Because this is a same-model panel,
**agreement is a weak signal**: you are explicitly tasked to find where the new `core` design is
wrong, mis-sequenced, or over-engineered for this scale.

## Your job (read carefully — this is NOT a discovery exercise)

CareerVP already has a **mature, documented redesign** (context pack §6) and a
catalog of known findings (§4). Do **not** simply restate them. Your value is to:

1. **Pressure-test** the documented plan through your assigned lens — where is it
   wrong, mis-sequenced, over/under-scoped, or resting on an unverified assumption?
2. **Find blind spots** the prior analysis missed from your lens.
3. **Re-prioritize** for a **solo developer** under the fixed constraints (§7),
   scoring every item on Importance × LOE × Difficulty.

Challenge the plan. If Phase 3 (single-table `core`) is riskier than its payoff for
a solo dev at this scale, say so. If a "CRITICAL" is actually lower priority given
the constraints, say so. Dissent is the point of a council.

## Hard constraints (from context pack §7 — obey all)

- Keep DynamoDB and **improve** it. **Do NOT** propose migrating to a relational or
  other datastore. That decision is closed.
- Solo developer → penalize big-bang / high-coordination work; favor incremental,
  independently-reversible, flag-gated changes.
- Maintain **> 70% margin**; remember the dominant cost lever is LLM tokens, not infra.
- Security-conscious + personal-data control (export/delete, least privilege,
  encryption), but **no formal GDPR/residency obligation** — don't gold-plate.
- Backend + infra only; flag frontend impact **only** where the API request/response
  contract changes.
- Scale target: **< 10k concurrent** users.

---

## The lenses

Assign **one blind subagent per lens** (6 total). The Data-architect lens carries
**double weight** in the final synthesis.

1. **Data architect (×2 weight)** — DynamoDB single-table design, key/GSI hygiene
   (all GSIs currently project `ALL`), access-pattern efficiency, hot-partition &
   the `userEmail` PII key, the "three schemas / three IDs" defect, Scan elimination
   (§3 E5/E6), transactions vs. non-atomic multi-writes (E7), connection reuse (E1),
   the 1128-LOC god-class split, and whether the `core` target (§6 Phase 3) is the
   right model and safely sequenced for a solo dev.
2. **Security** — the `x-user-id` auth bypass, `AUTHORIZER_DISABLED`, IDOR-prone
   `get_job`, JWT plaintext env keys, wildcard IAM + shared role, CV bucket CORS `*`,
   Cognito policy, WAF prod-only, and **personal-data control** (export/delete,
   tenant isolation by key design). No GDPR gold-plating.
3. **Reliability / SRE** — idempotency (zero handlers, money path), SQS partial-batch
   failures (3/4 workers), visibility-timeout 1×, unwired DLQs, `retry_attempts=0`,
   `max_concurrency` on AI workers, non-atomic writes, monitoring gaps / unsubscribed
   SNS, and migration safety (`RemovalPolicy.DESTROY`).
4. **Cost / performance** — on-demand vs. provisioned at scale, GSI `ALL` projection
   amplification, Scan cost, connection-per-call latency, read amplification (E4/E5),
   ARM64, prompt-cache gaps — always weighed against "cost lever is LLM tokens, not
   infra" and the >70% margin.
5. **Maintainability** — the god-class, muddy repository boundaries (repo reaching
   into handler internals, E-takeaways), the env-var table-alias precedence chain, the
   dead `DynamoDBStack` + stale spec, divergent error styles, testability, and the
   autouse CI fixture that masks table-routing defects.
6. **Delivery risk** — sequencing for a solo dev; the 500-resource CFN ceiling as a
   blocker to additive change; expand→dual-write→backfill→dual-read→contract safety;
   what MUST precede the `core` migration; where the documented phase order is wrong
   or too ambitious; the smallest safe first slice.

---

## Output format (each lens returns this)

### Lens: <name>

**Assessment of the documented plan** — 3–6 bullets: what's right, what's wrong,
what's mis-sequenced, what assumption is unverified.

**Findings** — for each finding:
- **Title**
- **Evidence** — cite the context-pack section/excerpt (e.g. "§3 E6", "§4 CRITICAL").
- **Recommended change** — concrete, DynamoDB-improving, solo-friendly.
- **Scores** — Importance (Critical/High/Med/Low) · LOE (S/M/L/XL) · Difficulty (Low/Med/High).
- **Depends on** — other findings/phases that must precede it.
- **Contract impact** — does it change an API request/response shape? (y/n + note).

**Blind spots** — anything the prior analysis (§4/§6) missed from this lens.

**Dissent** — where you disagree with the documented plan or expect other lenses
to over-rate something.

---

## Synthesis (the council's combined deliverable)

After the lenses report, reconcile into ONE output:

1. **Deduplicated, ranked backlog** — merge overlapping findings; order by
   **Importance → Difficulty (risk) → LOE**, tuned for solo incremental delivery.
   Each item keeps its scores, dependencies, and contract-impact flag.
2. **Recommended wave sequencing** — group the backlog into waves (quick wins →
   security/reliability → the `core` refactor → cost/observability), and state where
   your sequencing **differs** from the documented Phase 0–5 and why.
3. **Consensus vs. disagreement** — where lenses agreed, and where they conflicted
   (especially anything the Data-architect lens weights differently from the rest).
4. **Top risks & prerequisites** — the non-negotiable gates (e.g. `RETAIN` before any
   migration; CFN-ceiling headroom before additive work) and the single smallest safe
   first slice a solo dev should ship.
5. **Open questions** — from §8, which ones actually block a recommendation and must
   be resolved before that item can proceed.

---

## Success criteria (the run is DONE + trustworthy only when ALL hold)

- [ ] Every lens returned all four sections (Assessment / Findings / Blind spots / Dissent) — none skipped.
- [ ] Every finding cites context-pack evidence (§ / E#); uncited claims are dropped, not guessed.
- [ ] The Synthesis contains all 5 parts above.
- [ ] Each backlog item is independently scoped, scored (Importance × LOE × Difficulty),
  dependency-tagged, and contract-flagged (no TBDs) — directly consumable as the seed for the
  plan + test strategy.
- [ ] **Genuine dissent is surfaced.** A council with zero disagreement is a FAILED run for a
  same-model panel — re-run with sharper adversarial framing.
- [ ] **No recommendation contradicts the live-verified ground truth** (context-pack §7 constraints
  / `findings-register.md` Live-verification section) without explicitly flagging and justifying it.
- [ ] The Synthesis gives a **decisive** answer (not "it depends") on each high-stakes assumption:
  is single-table `core` a COMMITTED deliverable or a hypothesis to re-justify after the cheaper
  decoupled seams? · identity keying (`cognito_sub` vs internal `user_id`) · knowledge-base keep/drop
  · cutover/downtime tolerance.
- [ ] *(re-council only)* Every delta from the two updated docs is explicitly assessed, and any
  finding whose severity/priority/effort moved is re-scored with the reason.

Keep it concrete and evidence-linked. This backlog seeds a prioritized implementation
plan and a test/TDD strategy, so every item must be actionable and independently scoped.
