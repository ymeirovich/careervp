# CareerVP Redesign — Council Engagement Scope

**Date:** 2026-07-04
**Owner:** solo (yitzchak.meirovich)
**Status:** scope approved, not yet executed
**This doc plans the scope only. No implementation.**

---

## 0. Goal

Use `claude-council` (local Claude panel) to review the CareerVP backend against
the existing analysis and best-practice guides, and emit a **prioritized,
security-conscious, reliable redesign plan** — DB-first, whole-platform. The
data layer (DynamoDB) is kept and *improved*; the datastore choice is **not**
re-litigated.

Two phases:

- **Phase 1 — Analysis.** A grounded local council produces a scored redesign backlog.
- **Phase 2 — Planning.** From the council output, generate two docs — a
  **prioritized plan** (with per-task reasoning-effort annotations) and a
  **test/TDD strategy** — which later seed per-component specs.

### Inputs

| Source | Path |
|---|---|
| Code (backend) | `.../careervp/src/backend/careervp/` (DAL, handlers, logic, models) |
| Infra | `.../careervp/infra/` (CDK) |
| Prior analysis (8 docs) | `~/Documents/code/code-analysis/*.md` |
| Best-practice guides | `~/Documents/code/best-practice/` (AWS serverless, agentic dev) |
| Output | `~/Documents/code/code-analysis/redesign/` |

### Fixed constraints (drive scoring)

- **Scale:** dev today → hundreds of users → **< 10k concurrent** max. Moderate; Dynamo fits.
- **Cost:** maintain **> 70% profit margin** — cost is a real constraint.
- **Security:** conscious; **respect personal-data control** (export/delete, least
  privilege, encryption). **No formal GDPR / residency** obligation — do not gold-plate.
- **Team:** **solo** — penalize big-bang migrations; favor incremental, low-coordination work.
- **Frontend:** **out of scope** except where it changes the API request/response contract.

### Scoring axes (every backlog item scored on all three)

- **Importance** — impact on security, reliability, cost/margin, or maintainability.
- **LOE** — effort for a solo dev (S / M / L / XL).
- **Difficulty** — technical risk / uncertainty / blast radius (Low / Med / High).

---

## 1. Approach (chosen: B — Grounded two-stage council)

Blind local Claude subagents degrade under huge context, so we **do not** point
six subagents at 3,400 lines of DAL + 8 analysis docs + 3 guides. Instead:

```
Stage 0  Context pack        (me, high effort, no council)
Stage 1  Council lenses  ┐
                         ├─  single /claude-council:ask --local --agents run (xhigh)
Stage 2  Synthesis       ┘
Stage 3  Phase-2 docs        (me, high effort, from council output)
```

Stages 1 and 2 are **one** council invocation — claude-council fans out the lenses
and synthesizes automatically.

### Model & effort

| Step | Runs where | Model | Effort |
|---|---|---|---|
| 0. Context pack | main loop (here) | Opus 4.8 | high |
| 1+2. Council + synthesis | your terminal | Opus 4.8 | **xhigh** |
| 3. Phase-2 docs | main loop (here) | Opus 4.8 | high |

**Effort switching:** you flip session effort to **xhigh** once, before the
council run, and back to **high** after. claude-council's local subagents inherit
the session effort — it can't be set per-lens from the prompt.

---

## 2. Phase 1 — Stage 0: Context Pack

**Deliverable:** `~/Documents/code/code-analysis/redesign/context-pack.md` — the
single file the council reads. Built by me. Sections:

1. **System snapshot** — one-paragraph what-CareerVP-is + the AWS serverless
   topology (Lambda handlers → logic → DAL → DynamoDB; CDK infra), distilled from
   the architecture deep-dive and v2 docs. No re-derivation; cite the source docs.
2. **Data-layer map** — table of every DAL module with line count and one-line
   responsibility; flag `dynamo_dal_handler.py` (1,128 LOC) as the hotspot. Include
   the current DynamoDB table/index design and the known access patterns.
3. **Curated code excerpts** — the read/write paths most relevant to cost &
   correctness (scans, query patterns, batch ops, transaction use), not whole files.
4. **Best-practice delta checklist** — extracted from the two guides: the specific
   AWS-serverless and agentic-dev rules CareerVP should be measured against
   (idempotency, least-privilege IAM, single-table design, GSI hygiene, error
   handling, observability, cost controls). Each as a checkable line.
5. **Constraints block** — the fixed constraints and scoring axes above, verbatim,
   so every lens shares them.
6. **Open questions** — anything the analysis docs leave ambiguous.

**Budget:** aim for a tight, high-signal pack (target ≈ 2–4k lines max), because
six subagents each read it.

---

## 3. Phase 1 — Stage 1+2: The Council Run

### Command (run in terminal, session effort = xhigh)

```
/claude-council:ask "$(cat ~/Documents/code/code-analysis/redesign/council-prompt.md)" --local --agents
```

I'll also write `council-prompt.md`. Its content:

### The six lenses (one blind subagent each)

| # | Lens | Weight | Mandate |
|---|---|---|---|
| 1 | **Data architect** | ×2 | DynamoDB single-table design, GSI/LSI hygiene, access-pattern efficiency, hot-partition avoidance, `dynamo_dal_handler` refactor, read amplification. |
| 2 | **Security** | ×1 | Least-privilege IAM, encryption at rest/in transit, secrets, personal-data export/delete, authz on handlers. No GDPR gold-plating. |
| 3 | **Reliability / SRE** | ×1 | Idempotency, retries/DLQs, consistency, failure handlers, transactional integrity, observability. |
| 4 | **Cost / performance** | ×1 | On-demand vs provisioned, scan elimination, Lambda sizing, anything threatening the >70% margin. |
| 5 | **Maintainability** | ×1 | DAL/repository boundaries, the 1,128-LOC hotspot, testability, coupling, models. |
| 6 | **Delivery risk** | ×1 | Sequencing for a solo dev; flag big-bang risk; identify the safe incremental path. |

### Prompt contract (what council-prompt.md instructs the panel)

- Read only the context pack; do not re-explore the repo (keeps lenses comparable).
- Each lens returns **findings**, each with: title, current-state evidence (cite pack
  section), recommended change, **Importance / LOE / Difficulty** scores, and
  dependencies on other findings.
- Explicitly stay within constraints: keep DynamoDB, respect margin, solo-friendly,
  no GDPR gold-plating, backend + contract only.
- **Synthesis** (auto): reconcile the six views into **one deduplicated, ranked
  backlog**; note consensus vs. disagreement; call out where DB-first ordering
  conflicts with a higher-severity cross-cutting item.

### Deliverable

`~/Documents/code/code-analysis/redesign/council-output.md` — the raw panel
responses + synthesized ranked backlog. (Save the terminal output here.)

---

## 4. Phase 2 — Planning Docs (from council output)

Two separate docs; these later seed per-component specs (specs are **not** produced now).

### 4a. Prioritized plan — `redesign-plan.md`

- Ranked task list from the synthesized backlog, ordered by
  **Importance → Difficulty (risk) → LOE**, tuned for solo incremental delivery.
- Grouped into waves (e.g. Wave 1 = high-importance / low-risk quick wins;
  later waves = the DAL/hotspot refactor and structural DB work).
- **Each task annotated with:**
  - Target tool: **Claude Code** vs **Codex**.
  - **Reasoning effort**: low / medium / high / xhigh — mechanical edits = low;
    schema/access-pattern or security changes = high/xhigh.
  - Dependencies, rough LOE, and "spec needed? y/n" (flags future per-component specs).
- Explicit **DB-first track** called out as the spine, with cross-cutting security/
  reliability items interleaved where severity demands.

### 4b. Test / TDD strategy — `test-strategy.md`

- Maps to the plan's tasks: for each redesign unit, **what tests to write first**.
- Layers: unit (DAL/repositories with mocked Dynamo), integration
  (local Dynamo / moto), contract tests for any changed request/response shape.
- Regression guardrails for the `dynamo_dal_handler` refactor (characterization
  tests before touching it).
- Coverage targets and the red-green-refactor loop each per-component spec will follow.

---

## 5. Execution checklist

- [ ] Stage 0 — I build `context-pack.md` (high effort).
- [ ] I write `council-prompt.md`.
- [ ] You review the pack + prompt.
- [ ] **Set session effort → xhigh.**
- [ ] You run the `/claude-council:ask ... --local --agents` command in terminal.
- [ ] Save output to `council-output.md`.
- [ ] **Set session effort → high.**
- [ ] Stage 3 — I generate `redesign-plan.md` + `test-strategy.md`.
- [ ] You review; per-component specs authored later, one at a time.
