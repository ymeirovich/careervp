# CareerVP — Council Output (PARALLEL REBUILD vs IN-PLACE) · Re-council 2026-07-08

> **Local council — same-model panel.** Claude reasoning per-lens from `context-pack.md` +
> `context-pack-rebuild-addendum.md` (both refreshed 2026-07-08, incl. §0 deltas + live re-verify).
> Agreement is a shared prior to pressure-test, not cross-vendor corroboration. Supersedes the stale
> `.claude/council-cache/local-council-1783171127.md`.
>
> **Method note:** authored in-context because the plugin's background-subagent path delivered
> corrupted prompts this session (see `council-output.md`). Same epistemic class, executed reliably.
> Re-council scope: assess only what the §0 deltas change about the prior rebuild-vs-in-place verdict.

---

## Part A — per-lens verdicts

### Lens: Data architect (×2) — **Verdict: In-place**
The clean target (`core`) is now *concretely specified* (§0: SK layout, GSI-cardinality rule, sole
key-builder) and is fully buildable in-place via expand→dual-write→backfill→dual-read→contract, reusing
the already-proven CR (FE-UI-044) canonical-store pattern (addendum §4 Q1). A rebuild's data strategy
(shared tables vs Streams-CDC-synced copy) adds real complexity for **zero** benefit at this volume
(users 908 / artifacts 221 / rest <150, §0). Biggest rebuild risk: dual-schema divergence during CDC sync.

### Lens: Delivery / effort (solo) — **Verdict: In-place (anchors Part A)**
Reproducing the entire capability surface solo (addendum §1: ~40 routes, two async models, the Standard
Step Functions chain, LLMRouter + FVS + quota/trial + company research + billing) is an XL multi-quarter
LOE — the textbook "80% rewrite that never reaches parity" trap (addendum §2 the carve is huge). The
migration a rebuild avoids is *hours* at this volume. Biggest rebuild risk: **never reaches parity**;
becomes a permanent two-system maintenance tax.

### Lens: Coexistence & cutover — **Verdict: In-place**
Same-account side-by-side is expensive: root stack is **415/500 CFN resources live** (§0), so a second
full platform *forces* nested decomposition and hard budgeting anyway (addendum §3). The payment-webhook
is a hard singleton (one URL + one signing secret; addendum §3), and env-suffix reuse risks **corrupting
prod data** (addendum §3). Biggest rebuild risk: prod-data corruption via shared naming / webhook singleton.

### Lens: Cost / margin — **Verdict: In-place**
Running two platforms doubles infra (a rounding error, §1) but the real hazard is **double-AI-spend** on
any shared/mirrored traffic against the >70% margin (addendum §3). Coexistence has cost, no offsetting
upside at this scale. Biggest rebuild risk: shadow/mirror traffic doubling LLM spend (the dominant cost lever).

### Lens: Reliability / SRE — **Verdict: In-place**
"Build correctness in from day one" is the rebuild's best argument, but the correctness fixes
(idempotency, DLQs, visibility timeout, max_concurrency) are Wave-B in-place work regardless — and a
rebuild doubles the operational surface a solo dev must keep alive during coexistence. The migration risk
it avoids is minimal (RETAIN gate + hours-long backfill). Biggest rebuild risk: two live systems, one operator.

### Lens: Security — **Verdict: In-place**
Clean-slate least-privilege (per-fn roles, JWT-only, tenant-isolation by key) is achievable in-place at
the seams. A rebuild adds a *dual-identity* hazard (own Cognito pool vs shared → shared-data IDOR;
addendum §3) and doubles the secret surface. Biggest rebuild risk: cross-system IDOR on shared data during coexistence.

**Part-A tally: 6/6 In-place.** (On a same-model panel this unanimity is a weak signal — see §3.)

---

## Synthesis

### 1. The recommendation (Part A)
**In-place strangler-fig redesign — decisively, not a rebuild.** The two dominant reasons: (a) solo LOE to
reproduce the full capability surface is prohibitive and risks never reaching parity; (b) the §0 deltas
*remove* the rebuild's core rationale — the clean `core` design is now concrete and buildable in-place via
the proven CR pattern, and live volume is tiny so the "avoid a risky large-data migration" argument
evaporates (backfill is hours). Coexistence adds real cost/risk (CFN ceiling, payment-webhook singleton,
prod-data-corruption via env reuse) with no offsetting upside at this scale.

**Conditions under which the verdict flips (honest):** only if the in-place seams prove that incremental
change is *infeasible* — i.e., the coupling is so severe that a single reversible seam can't be shipped.
That is contradicted by the already-proven CR (FE-UI-044) in-place migration, so the flip condition is not
met. (A product pivot / full re-platform would be a different project, out of this scope.)

### 2. If rebuild proceeded (not recommended) — the how-to, in brief
Retained only as the documented fallback: MVP = corrected walking skeleton (Cognito → CV upload/parse →
one artifact end-to-end: VPR) per addendum §2; distinct `env` suffix + own Cognito pool + own SSM paths
(addendum §3) to guarantee prod isolation; EventBridge reconcile/cleanup kept DISABLED until the rebuild
has isolated data; payment provider left on the placeholder until Wave 4; data via own copy synced by
Streams CDC (never shared writes to prod tables). This is more work than the in-place plan for the same
end-state — hence not recommended.

### 3. Risk register (rebuild path, ranked)
1. **Never reaches parity** (solo, XL surface) → mitigation: don't start; if forced, ruthless MVP + kill-criteria.
2. **Prod-data corruption via shared naming/env** → mitigation: distinct env suffix, never reuse live tables.
3. **Payment-webhook singleton** → mitigation: provider test-mode/separate secret, or stay on placeholder.
4. **Double AI spend on coexistence** → mitigation: no mirrored traffic; cohort routing only.
5. **CFN 500-ceiling** (already 415/500) → mitigation: nested decomposition — which in-place also needs, so no rebuild-specific gain.

### 4. Rebuild vs in-place — honest scorecard
| Axis | Rebuild | In-place strangler-fig |
|---|---|---|
| Solo LOE | XL (reproduce full surface) | M–L, incremental |
| Risk / blast radius | High (two systems, prod-corruption, webhook) | Low–Med, reversible per step |
| Time-to-value | Slow (parity gate) | Fast (ship seams + launch-blockers now) |
| Margin impact (coexistence) | Negative (double infra + AI-spend risk) | Neutral (transient dual-write only) |
| End-state data model | Clean `core` from day 1 | Same clean `core` (§0), reached via expand→contract |
| Verdict driver | — | Same end-state, far less risk/effort |

### 5. Open questions (addendum §4) + defaults
1. Shared vs copied data → **moot** (in-place: in-table expand→contract, no coexistence copy).
2. Traffic routing → **moot** for in-place (canary/alias per Wave B/D, not cross-platform).
3. Parity/shadow verification → **in-place equivalent:** capture-snapshot contract tests vs live dev API +
   Streams drift metric during dual-write.
4. Consolidate the two async models? → **worth doing in-place** (simplification), but out of the DB-core
   critical path — track separately.
5. Real payment provider → **deferred behind the placeholder** either way; not on the redesign critical path.
6. **HS1 identity keying** and **HS3 knowledge keep/drop** are NOT dodged by rebuild — same answers as the
   in-place council: surrogate `user_id`; drop dead knowledge plumbing now.

---

## Acceptance-gate self-check (per council-prompt-rebuild Success criteria)

- [x] Every lens gave a Part-A verdict + dominant reasons + biggest rebuild risk.
- [x] Findings cite the pack/addendum (§ / addendum §).
- [x] Part A ends in ONE decisive verdict (In-place) with the explicit flip condition.
- [x] Synthesis has all 5 parts incl. the honest scorecard.
- [x] **Genuine dissent / honesty:** the 6/6 unanimity is explicitly flagged as a weak same-model signal;
  the flip condition (incremental change infeasible) is stated and shown to be contradicted by the proven
  CR migration — so this is not consensus theater, it's a falsifiable verdict.
- [x] No recommendation contradicts live ground truth (CFN 415/500, tiny volume, webhook singleton cited).
- [x] Coexistence singletons (payment webhook, Cognito, EventBridge) + prod-isolation guard each addressed.
- [x] Deltas assessed: they *strengthen* in-place (concrete `core` + tiny volume undercut the rebuild case).

**Verdict: run ACCEPTED** — decisive In-place verdict with a stated flip condition; deltas assessed.
