# CareerVP Redesign — Council Output (IN-PLACE) · Re-council 2026-07-08

> **Local council — same-model panel.** Every lens below is Claude reasoning from one role
> against `context-pack.md` (as refreshed 2026-07-08, incl. §0 deltas + live re-verification).
> **Agreement is a weak signal, not cross-vendor corroboration** — treat convergence as a shared
> prior to pressure-test. The value is angle coverage + decisive answers on the four high-stakes
> decisions. Supersedes the stale `.claude/council-cache/local-council-1783166912.md`.
>
> **Method note (transparency):** the plugin's local-council path spawns background subagents. In
> this session that harness delivered *corrupted/crossed prompts* to ~half the members (some
> received an unrelated ".zshrc" task) and 0-tool-use non-answers, so a subagent panel could not be
> trusted to cite the pack. The panel was therefore convened in-context (Claude adopting each lens
> against the real evidence) — same epistemic class as a same-model subagent panel, executed
> reliably. This is a re-council: per §0, lenses concentrate on the deltas + the four §8 decisions
> and only re-score prior findings where a delta moves them.

---

## Lens: Data architect (×2 weight)

**Assessment of the documented plan**
- The newly-specified `core` SK layout (§0) is *correct DynamoDB modeling*: one item collection per
  user, CV at USER level referenced-by-`cv_id` (not copied), `APP#{appId}#ARTIFACT#{TYPE}#v{n}`, and
  `Query(PK=USER#{sub}, SK begins_with APP#{appId}#)` for a full artifact set in one round-trip. This
  is the right shape and it earns `GET /me/bootstrap` for free (§6 Phase 4).
- The **hot-partition GSI-cardinality rule** (§0) is the single most valuable addition and *corrects*
  a latent bug in the older plan: the old "GSI1 for status" (§6 Phase 3) implied `GSI1PK=STATUS#{status}`,
  which is low-cardinality and would concentrate every "completed" item on one GSI partition. The rule
  (`GSI1PK=USER#{sub}, GSI1SK=STATUS#…` or sparse index of in-flight items) is right and mirrors the
  existing `status-index` (PK `userId`) already live on the applications table.
- **The DRY win is decoupled from the physical collapse.** The plan's real defect is §2c (three
  schemas / three IDs resolved by env-var precedence) + the 1128-LOC god-class (§2b). The fix that
  matters is `CoreRepository` as the *sole key-builder* — and that can be delivered over the EXISTING
  tables (DB-H2 TableRegistry + DB-M1 god-class split) without physically collapsing to one table.
- **Unverified assumption in the plan:** that the physical single-table collapse is worth its blast
  radius at this scale. Live volume is tiny (§0: artifacts 221, users 908, rest <150). The collapse
  buys one-Query bootstrap and structural drift-elimination, but the seams already kill the drift at
  the code layer.

**Findings**
- **Status/in-flight GSI must be user-scoped or sparse (design constraint on the core wave).**
  Evidence: §0 GSI rule; live `status-index` PK=`userId` (recon). Recommended: any new status GSI uses
  `GSI1PK=USER#{sub}` or is sparse (index only non-terminal artifacts). Scores: Importance High · LOE S ·
  Difficulty Low. Depends on: DB-H8 design. Contract impact: n.
- **Make `CoreRepository` the sole key-builder over existing tables FIRST (the DRY that matters).**
  Evidence: §2c env-var precedence; §3 data-layer takeaway (6). Recommended: TableRegistry + one typed
  repo per entity; no handler assembles a key/table name. Scores: Importance High · LOE L · Difficulty
  Med. Depends on: DB-M1 god-class split. Contract impact: n.
- **Version-in-SK kills E4.** Evidence: §3 E4 (get_latest_vpr paginates all versions). Recommended:
  `…#v{n}` SK + `Query(Limit=1, ScanIndexForward=false)`. Scores: Importance Med · LOE S · Difficulty
  Low. Contract impact: n.
- **Retire `userEmail` PII PK on `knowledge` by deletion (table empty).** Evidence: §5 best-practice
  FAIL (low-cardinality/PII PK); live knowledge=0. Scores: Importance Med · LOE S · Difficulty Low.
  Contract impact: n.

**Blind spots** — the plan doesn't state a *trigger* for when the physical collapse becomes worth it
(e.g. a measured bootstrap-latency SLA, or ongoing drift after the seams). Without a trigger, "Phase 3"
risks being done for its own sake. Also: `company-research` appears both as a per-app artifact
(`APP#…#ARTIFACT#COMPANY_RESEARCH`) and a cross-user cache (`CRCACHE#{company}`, stays out of core) —
the plan should state the write-owner that keeps them consistent (§0 single-write-owner rule covers it,
but it's easy to miss).

**Dissent** — I carry double weight and I still will *not* claim the physical single-table collapse is a
launch blocker. The other lenses will likely under-rate the *code-layer* DRY (sole key-builder) because
it's unglamorous; that, not the physical table, is what fixes the correctness defect (§1 broken
cover-letter/interview-prep, `docs/db-redesign/01`). I rate the seams **High/committed** and the physical
collapse **Med/deferred**.

### High-stakes stance
- **HS1 (identity):** surrogate `user_id` as the `core` PK. The PK is set once at backfill and is
  expensive to change; the stated social-IdP intent (§0) makes `sub` fragile. Resolve sub→user_id at the edge.
- **HS2 (core committed?):** **Staged-committed.** Seams (single key-authority, kill 3-schema drift, stop
  dual-key CV write E2, retire PII key) = committed and mostly launch-relevant. Physical collapse =
  deferred wave behind a go/no-go gate tied to a concrete access-pattern need. Not a launch blocker.
- **HS3 (knowledge):** Drop the dead table + plumbing now (empty, `userEmail` PII PK); re-introduce on a
  non-PII key only if the cross-app memory feature is committed.
- **HS4 (cutover):** Zero-downtime by construction (expand→dual-write→backfill→dual-read→contract; both
  schemas live). Backfill is hours at this volume. Gate on RETAIN + deletion-protection + a fresh backup.

---

## Lens: Security

**Assessment**
- The security-relevant part of `core` is the **key design**, not the physical table: retiring the
  `userEmail` PII PK (§4 knowledge) and keying every item under `USER#{principal}` gives tenant isolation
  *by construction* and removes the IDOR-prone ambiguity behind §4 HIGH `get_job`.
- The launch-blocking security defects are independent of the DB redesign and unchanged by the deltas:
  `x-user-id` fallback + `AUTHORIZER_DISABLED` (§4 CRITICAL), JWT plaintext env keys (E10), shared IAM
  role + SQS-KMS `*` (§4 CRITICAL), CV bucket CORS `*` (§4 HIGH), Cognito MFA-off (§4 MED, live-confirmed),
  and **WAF entirely absent regionally** (§0 live — stronger than "prod-only").
- New delta with a security edge: the artifact-edit `UpdateItem`+`version` (409) pattern (§0) means if
  `/ai/assist` ever persists edits it needs `UpdateItem` IAM — today it's read-only GetItem/Query, which
  is the *correct* least-privilege posture. Keep it read-only unless the write path is deliberately added.

**Findings**
- **Delete `x-user-id` fallback; derive identity only from validated JWT claims.** Evidence: §4 CRITICAL,
  §5 FAIL. Scores: Importance Critical · LOE S · Difficulty Low. Contract impact: n (auth header only).
- **Split the shared role + scope SQS-KMS to the 3 key ARNs; move JWT keys out of plaintext env.**
  Evidence: §4 CRITICAL, E10. Scores: Importance Critical · LOE M · Difficulty Med. Contract impact: n.
- **Tenant-filter every `core` query on the partition principal (IDOR guard by key design).** Evidence:
  §4 HIGH get_job; §5 FAIL. Scores: Importance High · LOE M · Difficulty Med. Depends on: CoreRepository.
  Contract impact: n.
- **Attach WAF to dev/staging now (0 web ACLs exist).** Evidence: §0 live; §4 MED. Scores: Importance
  Med · LOE S · Difficulty Low. Contract impact: n.

**Blind spots** — the personal-data **account-delete** ("delete all my data") path isn't in the DB plan;
under `core` it becomes trivial (delete the `USER#{principal}` collection + S3 + Cognito user) — call it
out as a first-class capability, since export already exists. Also: 3 live Cognito pools (§0: 1 dev, 2
staging) — one staging pool may be orphaned; confirm which is authoritative before wiring `core` identity.

**Dissent** — I disagree with treating single-table `core` as a *security* driver. The isolation win comes
from the KEY (retire `userEmail`, principal-scoped PK) and the auth fixes, both achievable at the seams.
The physical collapse is security-neutral; don't let it gate the CRITICAL auth work.

### High-stakes stance
- **HS1:** surrogate `user_id`. `sub` is per-pool/per-provider; with social IdP a human maps to multiple
  `sub`s → either duplicate tenants or fragile account-linking. A stable internal principal is the safer
  isolation boundary. (Edge already resolves `user_id` from `sub`, so the indirection is cheap.)
- **HS2:** Seams (auth + key fixes) are launch-critical and committed; physical collapse deferred.
- **HS3:** Drop now — an empty table with a `userEmail` PII PK is pure latent liability (IDOR + hot
  partition) and misleads migration authors.
- **HS4:** RETAIN + deletion-protection + backup BEFORE any migration step is the non-negotiable security/
  durability gate (§4 CRITICAL DESTROY). Online migration → no downtime.

---

## Lens: Reliability / SRE

**Assessment**
- The migration path itself is the reliability question. expand→dual-write→backfill→dual-read→contract
  (§6) is sound and reversible per step, and reusing the *already-proven CR (FE-UI-044) canonical-store
  pattern* materially de-risks it — but it is only as safe as its prerequisite: **all 10 tables are
  DESTROY + deletion-protection FALSE (§0 live).** Any dual-write/backfill on those tables before the
  RETAIN flip is a data-loss trap.
- The `UpdateItem`+`version` (409) edit pattern (§0) is a genuine reliability *win*: optimistic
  concurrency prevents lost updates and matches the frontend's existing 409 contract. Pair it with a
  Streams-derived drift metric during dual-write.
- Launch-blocking reliability defects are unchanged by the deltas: zero idempotency handlers on the money
  path (§4 CRITICAL; live idempotency table empty), 3/4 workers return 200 not `batchItemFailures`,
  visibility-timeout ≈1× (duplicate AI spend), unwired DLQs, `retry_attempts=0`, no `max_concurrency` on
  AI workers, SNS 0 subscribers (§0 live — alarms notify no one).

**Findings**
- **RETAIN + deletion protection on all 10 tables + adopt via `cdk import` (Phase 0 gate).** Evidence:
  §4 CRITICAL; §0 live. Scores: Importance Critical · LOE S · Difficulty Low. Contract impact: n.
- **`@idempotent` on billing (Stripe event id) + async workers.** Evidence: §4 CRITICAL. Scores:
  Importance Critical · LOE M · Difficulty Med. Contract impact: n.
- **`ReportBatchItemFailures` + visibility timeout ≥6× + `max_concurrency` 3–5 on AI workers.** Evidence:
  §4 CRITICAL/HIGH, §5 FAIL. Scores: Importance High · LOE M · Difficulty Med. Contract impact: n.
- **Streams drift metric during dual-write; subscribe SNS before relying on alarms.** Evidence: §6 Phase
  3; §0 SNS 0 subs. Scores: Importance High · LOE S · Difficulty Low. Contract impact: n.

**Blind spots** — nobody owns *rollback* of a partially-backfilled `core` collection. Define the reverse
(contract→dual-read→stop-dual-write) as an explicit, tested runbook step, not an afterthought. Also: the
VPR Step Functions task has no heartbeat (infra Finding #5) — a stuck migration-era VPR can hang 2h.

**Dissent** — I rate the physical `core` collapse's *incremental* reliability value LOW once the seams +
idempotency + DLQ wiring are done. The collapse adds migration risk without removing a launch-blocking
reliability defect. Commit to it only behind the go/no-go gate.

### High-stakes stance
- **HS1:** surrogate `user_id` — a stable principal survives IdP/pool changes without a second migration
  (re-keying a backfilled table is the exact high-risk operation we want to avoid).
- **HS2:** Staged-committed; seams + reliability fixes first. Physical collapse is a deferred, gated wave.
- **HS3:** Drop now (empty, unwired — zero reliability value, nonzero drift-confusion cost).
- **HS4:** No downtime needed (online expand→contract). Take an on-demand backup + extend PITR 7d→35d on
  PII tables before contract; idempotency is already 35d (§0). RETAIN gate is mandatory first.

---

## Lens: Cost / performance

**Assessment**
- The governing truth (§1, §7): margin is ~88% and **LLM-token-dominated (VPR ≈74% of per-app spend);
  infra is a rounding error.** This reframes the entire DB program: DB changes earn their keep via
  *correctness, latency, and maintainability*, not infra cost.
- Therefore the physical single-table collapse has **near-zero margin payoff**. The cost-relevant DB items
  are: minimized GSI projections (`ALL`→`KEYS_ONLY`/`INCLUDE`; §5 FAIL), and killing read amplification
  E4 (paginate-all-versions), E5 (6-round-trip CR), E6 (reconciliation Scan) — and *all of these can be
  done without the collapse*.
- The deltas don't move the cost picture materially. `#v{n}` version-in-SK (§0) is the clean E4 fix;
  one-Query bootstrap reduces request count but request cost is negligible at this scale.

**Findings**
- **Minimized GSI projections during any GSI rebuild.** Evidence: §5 FAIL (all `ALL`). Scores:
  Importance Med · LOE M · Difficulty Med. Contract impact: n.
- **Eliminate the reconciliation Scan (E6) → GSI; fix E4/E5 read amplification.** Evidence: §3 E4/E5/E6.
  Scores: Importance Med (E6 on money path → High) · LOE M · Difficulty Med. Contract impact: n.
- **The real margin levers are LLM-side, not DB:** prompt-cache breakpoints, bound artifact `max_tokens`,
  retire `len/4` estimator, truncate Tavily input. Evidence: §5 cost FAIL/PARTIAL. Scores: Importance
  High · LOE M · Difficulty Med. Contract impact: n. *(Flagged: VPR economics are UNMEASURED — 2 Haiku
  samples, §8 — so every Sonnet figure is an estimate; instrument real token usage before optimizing.)*

**Blind spots** — the plan optimizes DB cost (negligible) while the measured cost driver (LLM tokens) is
under-instrumented. If any single item should be "committed," it's the AI-spend metric, not `core`.

**Dissent** — strongest dissent on the panel: **the physical single-table collapse is not cost-justified.**
On-demand DDB at 221 artifacts costs cents; the collapse is engineering spend against a rounding-error line
item. Capture the GSI-projection + Scan-elimination wins at the seams and STOP. I explicitly disagree with
any framing that sells `core` on cost/performance grounds at this scale.

### High-stakes stance
- **HS1:** surrogate `user_id` (cost-neutral; decide on durability grounds — defer to Security/Data-arch).
- **HS2:** **Hypothesis, not committed** — from a pure cost/margin lens the collapse fails a cost-benefit
  test at current scale. Do the cheap wins (GSI projections, Scan kill) without it.
- **HS3:** Drop — stops paying for an unused table and a misleading second schema source.
- **HS4:** No downtime; the online migration's only cost is transient dual-write (doubled writes on a
  tiny table — negligible). Backup before contract.

---

## Lens: Maintainability

**Assessment**
- The biggest maintenance tax is the trio: 1128-LOC 6-entity god-class (§2b), the env-var table-alias
  precedence chain (§2c), and the dual-schema read/write fallback (E2/E3) — plus the autouse
  `mock_artifact_dependency_resolver` fixture that *masks* routing defects in CI (§4 MED).
- The new DRY-at-the-code-layer principle (§0) is exactly the right lever: `CoreRepository` as the *sole*
  key-builder, shared entities referenced-by-key, denormalized copies with a single write-owner. **Crucial
  insight: this DRY is achievable over the existing tables** — you don't need the physical single table to
  get it. That decouples the maintainability win (big) from the migration risk (big).
- Live verification resolved a maintainability trap: the dead `DynamoDBStack`/`dynamodb_spec.yaml` is
  confirmed NOT deployed (§0/§8) — it's a "second source of truth" that misleads authors. Delete it (DB-L1).

**Findings**
- **Split the god-class by entity onto a TableRegistry, one PR each (precedes core).** Evidence: §2b, §2c.
  Scores: Importance High · LOE L · Difficulty Med. Contract impact: n.
- **Surface `ValidationException` (log+metric+raise) instead of the false "not found."** Evidence: §2c.
  Scores: Importance High · LOE S · Difficulty Low. Contract impact: n. *(cheapest drift signal.)*
- **Retire the autouse test fixture (make opt-in) + enable branch coverage.** Evidence: §4 MED. Scores:
  Importance Med · LOE S · Difficulty Low. Contract impact: n.
- **Delete dead `DynamoDBStack`/`S3Stack` + stale spec (live-confirmed dead).** Evidence: §0/§8; §4 MED.
  Scores: Importance Med · LOE S · Difficulty Low. Contract impact: n.

**Blind spots** — a single `CoreRepository` risks becoming the *next* god-class if it isn't split by
entity behind one interface. The plan should mandate per-entity modules under one key authority, not a
second 1000-LOC class.

**Dissent** — I'm the lens most sympathetic to `core`, but even I concede the *code-DRY* benefit lands at
the seams (TableRegistry/CoreRepository over existing tables). The physical collapse's marginal
maintainability gain (one table vs several) is real but modest and does not justify launch-blocking it.

### High-stakes stance
- **HS1:** surrogate `user_id` — a stable internal principal is more maintainable across an evolving auth
  surface (social IdP) than threading provider-specific `sub`s through the code.
- **HS2:** Staged-committed. Seams (god-class split, sole key-builder, ValidationException, error
  taxonomy) are the committed maintainability program; physical collapse is a deferred, gated nicety.
- **HS3:** Drop the dead plumbing now — it's a maintenance liability and a migration-author trap.
- **HS4:** No downtime; keep both schemas readable during migration so a bad step is reversible.

---

## Lens: Delivery risk

**Assessment**
- The hard delivery constraint is live and confirmed: root `CareerVpCrudDev` = **415/500 direct
  resources, 4 nested** (§0). Every redesign resource (per-fn roles, idempotency wiring, DLQ reapers,
  alarms, new GSIs) ADDS count — so **nested-stack decomposition of the API stack must precede additive
  work**, and the physical `core` collapse (new table + GSIs during expand) lands squarely into this
  ceiling if sequenced early.
- For a solo dev, the reversible/independent work is the seams + security + reliability fixes. The
  physical collapse is the highest-blast-radius, least-reversible item — even with expand→contract it's a
  multi-week track with a live-data backfill.
- The deltas *help* delivery: the concrete SK layout + reuse of the proven CR (FE-UI-044) pattern turn the
  collapse from "design-and-pray" into "follow a known-good migration" — but they don't shrink the blast
  radius; they de-risk the mechanics.

**Findings**
- **Phase 0 gate: RETAIN + deletion protection, then decompose the API RestApi into a nested stack**
  (collapses ~175 API-GW resources to 1 parent entry) BEFORE adding redesign resources. Evidence: §0 CFN
  415/500; §4 HIGH; findings-register #8 fix. Scores: Importance Critical · LOE M · Difficulty Med.
  Contract impact: **y** (RestApi recreate can change the invoke URL — mitigate via retained logical id or
  custom domain; verify frontend resolves).
- **Smallest safe first slice = the seams, not the table.** Evidence: §6 Phase 0/1; §2c. Order:
  RETAIN → ValidationException surfacing → TableRegistry single key-authority → stop dual-key CV write.
  Scores: Importance High · LOE M · Difficulty Low. Contract impact: n.
- **Gate the physical collapse behind an explicit go/no-go** (trigger = measured need). Scores: Importance
  Med · LOE XL · Difficulty High. Depends on: DB-H1, DB-H2, DB-M1, CFN decomposition. Contract impact: y
  (preserve response shapes; version if needed).

**Blind spots** — the CFN-ceiling interaction with the collapse is under-stated in the plan: adding the
`core` table + overloaded GSIs during the *expand* phase competes for the same 500-resource budget as the
security/reliability additive work. Sequence the decomposition first or the collapse can't even deploy.

**Dissent** — I most strongly resist committing to the physical collapse up front. For a solo dev it's the
classic "flagship refactor that eats the quarter." Ship the reversible seams, get to a safe paid launch,
and only then run the collapse behind a gate — if a measured need survives.

### High-stakes stance
- **HS1:** surrogate `user_id` — decide *now* (before backfill) so we never re-key a populated table; the
  edge already maps sub→user_id so the delivery cost today is ~zero.
- **HS2:** **Staged-committed with a hard go/no-go.** The seams are committed and launch-relevant; the
  physical collapse is explicitly a *later* wave, not a launch blocker. This is the safest solo path.
- **HS3:** Drop now (one-PR cleanup; removes a live migration-author trap).
- **HS4:** No downtime (online expand→contract); the binding gate is RETAIN + backup + CFN headroom, not a
  maintenance window.

---

## Synthesis (the council's combined deliverable)

### 1. Deduplicated, ranked backlog (ordered Importance → Difficulty/risk → LOE, tuned for solo incremental delivery)

| Rank | Item | Imp · LOE · Diff | Track | Contract | Depends |
|---|---|---|---|---|---|
| 1 | RETAIN + deletion protection on all 10 tables (+ adopt via `cdk import`) | Crit · S · Low | D/P (DB-H1) | n | — |
| 2 | Decompose API RestApi → nested stack (CFN headroom) before additive work | Crit · M · Med | P (#8) | **y** (invoke URL) | 1 |
| 3 | Delete `x-user-id` fallback + `AUTHORIZER_DISABLED` (JWT-only identity) | Crit · S · Low | P | n | — |
| 4 | `@idempotent` on billing (Stripe event id) + async workers | Crit · M · Med | P | n | — |
| 5 | Split shared IAM role + scope SQS-KMS + JWT keys out of plaintext env | Crit · M · Med | P | n | — |
| 6 | `ReportBatchItemFailures` + visibility ≥6× + `max_concurrency` on AI workers | High · M · Med | P | n | — |
| 7 | TableRegistry single key-authority + surface `ValidationException` (the seams) | High · M · Low–Med | D (DB-H2/H3) | n | — |
| 8 | Stored canonical `artifact_id` + pass-resolved-upstreams (fix broken CL/interview) | High · M · Med | P/D (DB-H4) | **y** (preserve `artifact_id`) | 7 |
| 9 | Split 1128-LOC god-class by entity (precedes any collapse) | High · L · Med | D (DB-M1) | n | 7 |
| 10 | Tenant-filter every query on principal (IDOR guard) | High · M · Med | P | n | 7 |
| 11 | Stop dual-key CV write (E2/E3) once legacy read cold | Med · M · Med | D (DB-M2) | n | 7 |
| 12 | Eliminate request-path Scans (E6 money path → GSI) + E4/E5 read amplification | Med–High · M · Med | D (DB-H7/M4) | n | 7 |
| 13 | Minimized GSI projections (`ALL`→`KEYS_ONLY`/`INCLUDE`) | Med · M · Med | D (DB-M3) | n | — |
| 14 | AI-spend metric + prompt-cache + bound `max_tokens` + retire `len/4` (real margin lever) | High · M · Med | P | n | — |
| 15 | Attach WAF to dev/staging; subscribe SNS; log retention 30–90d | Med · S · Low | P | n | — |
| 16 | Quick wins: delete dead `knowledge` table + dead stacks + stale spec; PITR 7d→35d PII; TTL fix; pagination | Med · S · Low | D (DB-Q/L) | n | — |
| 17 | **Single-table `core` physical collapse** (SK layout §0, sole key-builder, sparse/user-scoped GSIs) | **Med · XL · High** | D (DB-H8) | y (preserve shapes) | 1,2,7,9 + go/no-go |
| 18 | Personal-data account-delete ("delete all my data") — trivial under `core` | Med · M · Med | P | n | 17 (or seams) |

### 2. Recommended wave sequencing (and where it differs from the documented Phase 0–5)

- **Wave A — Guardrails & headroom (Phase 0):** items 1–2. *Unchanged from the plan; non-negotiable first.*
- **Wave B — Launch-blocking security + reliability + money path (Phase 1–2):** items 3–6, 8, 14. *This is
  the paid-launch gate.*
- **Wave C — The seams (Track D on-ramp):** items 7, 9, 10, 12, 13, 15, 16. *These are the DRY + drift-kill
  + cost wins and they are prerequisites to any collapse.*
- **Wave D — Physical `core` collapse (Phase 3), GATED:** item 17, then 18. **This is where the council
  differs from the documented plan:** the plan presents Phase 3 as the flagship deliverable; the panel
  (5 of 6 lenses, incl. the double-weight Data-architect conceding) demotes the *physical collapse* to a
  **deferred, go/no-go-gated wave** — because the correctness/DRY/isolation value it was sold on is
  captured in Wave C at the code layer, and infra cost is a rounding error.
- **Wave E — Cost/observability polish (Phase 5):** ARM64, dashboards, cost-anomaly alarms.

### 3. Consensus vs. disagreement (same-model panel — agreement is a shared prior, not corroboration)

- **Convergence (stress-test, don't trust):** all six lenses agree the *seams* (single key-authority,
  ValidationException, god-class split, retire PII key, tenant-filter) capture most of the value and are
  committed; and that RETAIN + CFN-decomposition gate everything. *Shared blind spot to probe:* every lens
  is a DynamoDB-keep prior (the datastore decision is closed, §7) — none re-questions whether the artifact
  workload wants a different store; that's deliberately out of scope but worth naming.
- **Genuine disagreement (the real signal):**
  - **Data-architect (×2)** rates the physical collapse's *eventual* value higher (structural drift-kill,
    one-Query bootstrap) than **Cost** and **Delivery-risk**, which argue it is not cost-justified and is a
    solo big-bang trap. Net (even at double weight): the Data-architect concedes it is **not a launch
    blocker** and is decoupled from the DRY win — so the panel lands on *staged-committed / gated*, not
    *committed-now*.
  - **HS1 residual tension:** surrogate `user_id` is the panel recommendation, but a defensible minority
    view (YAGNI) is "ship on `sub`, swap at the edge later." Resolved toward surrogate *because the `core`
    PK is set once and re-keying a backfilled table is the exact risk to avoid* — and the edge cost today
    is ~zero.

### 4. Top risks & prerequisites (non-negotiable gates + smallest safe first slice)

- **Gate 1:** RETAIN + deletion protection on all 10 tables (live: DESTROY + protection FALSE) before ANY
  dual-write/backfill. Take a fresh on-demand backup + extend PITR 7d→35d on PII tables.
- **Gate 2:** Decompose the API RestApi into a nested stack (415/500 live) before adding redesign
  resources — otherwise the security/reliability additions and the `core` expand can't deploy.
- **Gate 3 (for Wave D only):** an explicit go/no-go with a *measured* trigger (bootstrap-latency SLA or
  post-seams drift) — do not run the physical collapse on principle.
- **Smallest safe first slice a solo dev should ship:** RETAIN flip (item 1) → surface `ValidationException`
  (item 7a) → delete `x-user-id` fallback (item 3). All reversible, all high-relief, none touches the
  frontend contract.

### 5. Open questions that actually block a recommendation (from §8)

- **HS1 identity keying** — **blocks the `core` PK.** Recommendation: surrogate `user_id`; confirm the
  social-IdP intent is real (if definitively dropped, `sub` becomes acceptable).
- **HS2 core committed?** — **resolved: staged-committed / gated** (does not block launch).
- **HS3 knowledge keep/drop** — **resolved: drop now**, re-introduce later on a non-PII key if the feature
  is committed.
- **HS4 cutover/retention** — **resolved: no downtime** (online expand→contract); gate on RETAIN + backup +
  35d PITR. Confirm the retention window the owner wants beyond 35d PITR (default: 35d PITR + pre-contract backup).
- Non-blocking checks retained: `cv_tailoring` `ValidationException` at runtime (masked by dual-write),
  `_is_stale` delete-or-test, `chain_execution_status` as first-class state, VPR economics unmeasured.

---

## Acceptance-gate self-check (per council-prompt Success criteria)

- [x] Every lens returned Assessment / Findings / Blind spots / Dissent (+ High-stakes stance).
- [x] Findings cite context-pack evidence (§ / E#); no uncited claims carried.
- [x] Synthesis contains all 5 parts.
- [x] Backlog items are scoped, scored (Imp·LOE·Diff), dependency-tagged, contract-flagged.
- [x] **Genuine dissent surfaced** — Cost & Delivery-risk vs. the double-weight Data-architect on the
  physical collapse; a real HS1 minority (sub-now-swap-later). Not consensus theater.
- [x] **No recommendation contradicts live-verified ground truth** (RETAIN gate, tiny-volume backfill,
  CFN 415/500, WAF absent, SNS 0 subs all honored and cited).
- [x] **Decisive answer on each high-stakes assumption:** HS1 = surrogate `user_id`; HS2 = staged-committed/
  gated (not a launch blocker); HS3 = drop now; HS4 = no downtime, RETAIN+backup+35d PITR gate.
- [x] Every delta from the updated docs assessed; no prior finding's severity moved (deltas enrich the
  `core` spec + resolve open questions, they don't re-tier launch-blockers).

**Verdict: run ACCEPTED** — meets the gate; genuine dissent present; decisive on all four decisions.
