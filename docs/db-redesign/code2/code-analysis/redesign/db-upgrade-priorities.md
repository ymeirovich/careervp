# CareerVP — DB Upgrade Priorities (High → Low)

Priority **H/M/L** · Effort **Lo/Md/Hi** · all DB/data-layer scope. Live-verified against
dev (2026-07-04). Target = best-practice-compliant, done once (single-table `core`), with
the frontend contract preserved (external `application_id==job_id` + resolvable `artifact_id`;
internal PK is free). Track D of `findings-register.md`.

> **⚡ Quick wins — Lo effort, do first regardless of priority tier:** DB-Q1 surface
> ValidationException · DB-Q2 connection reuse · DB-Q3 pagination fixes · DB-Q4 delete dead
> `knowledge` table (0 items) + dead `DynamoDBStack`/`S3Stack` + stale spec · DB-Q5
> schema-enforced TTL fix · DB-Q6 PITR 7d→35d on PII tables. All Lo, low-risk, high-relief.

---

## `core` table design (target for DB-H8)

**One table, artifacts as items (NOT one table per artifact type):**
```
PK = USER#{cognito_sub}
  SK = PROFILE                                    user account
  SK = CV#{cvId}                                  user-level, shared across ALL apps — referenced by cv_id, never copied
  SK = APP#{appId}                                application root/state (the hub)
  SK = APP#{appId}#GAPRESP#{qId}
  SK = APP#{appId}#ARTIFACT#COMPANY_RESEARCH
  SK = APP#{appId}#ARTIFACT#VPR#v{n}
  SK = APP#{appId}#ARTIFACT#CV_TAILORED#v{n}
  SK = APP#{appId}#ARTIFACT#COVER_LETTER#v{n}
  SK = APP#{appId}#ARTIFACT#INTERVIEW_PREP#v{n}
```
- "One full artifact set per application" = `Query(PK=USER#{sub}, SK begins_with "APP#{appId}#")` — one round-trip, no fan-out. Gives `GET /me/bootstrap` for free.
- **AI Assist turn** = single-item `UpdateItem` on the exact artifact SK, `ConditionExpression` on a `version` attribute (= the frontend's existing 409 optimistic-concurrency contract). Large regen: write body to S3 first, then one conditional `UpdateItem` swapping the pointer + bumping `version`. Rare multi-item edits (artifact + app-root together) = `TransactWriteItems` — cheap because both share one `PK`.
- **Stays out of `core` (genuinely independent, keep as focused tables):** `idempotency`, `llm-cache`, `company-research-cache`.

**DRY without relational normalization:** DynamoDB denormalizes on purpose; DRY is enforced at the code layer, not the storage layer.
1. `CoreRepository` is the **sole key-builder** for every access pattern — no handler assembles a key or names a table. This is the DRY that matters and what's broken today (env-var precedence chain, 1,128-LOC god-class, 3 copies of read-fallback logic).
2. Shared entities are **referenced by key, not copied** (CV by `cv_id`; company research by `CRCACHE#{company}`).
3. Where denormalization is intentional (e.g. stamping `company_name` on the app root for the hub), a **single write-owner** (the repository write path, or a Streams consumer) keeps copies consistent — never hand-maintained in N handlers.

**Hot-partition guardrails (B2C interactive workload, safe at <10k users):**
- `PK=USER#{sub}` has excellent cardinality (UUID-like, one partition per user); a single partition's ~3,000 RCU/1,000 WCU ceiling is far above any real per-user edit rate.
- **The actual risk is a low-cardinality GSI partition key** (e.g. `GSI1PK=STATUS#{status}` — few distinct values, concentrates all "completed" items on one GSI partition). **Rule: every GSI partition key must be user- or high-cardinality-scoped** (`GSI1PK=USER#{sub}`, `GSI1SK=STATUS#...`), or made **sparse** (index only in-flight items) — mirrors the existing `status-index` pattern.
- Avoid LSIs (10 GB/partition cap, constrains splitting) — use GSIs.
- Keep items small; large bodies in S3 with a pointer (well under 400 KB) → more items/partition, faster queries.
- On-demand billing (already in use) + adaptive capacity auto-isolates any residual hot key; if one cache key (e.g. a viral company) goes hot, write-shard it (`CRCACHE#{company}#{0..N}`) — unlikely at this scale.

---

## HIGH priority

| ID | Upgrade | Why | Effort | Depends | Contract |
|---|---|---|---|---|---|
| DB-H1 | **`RETAIN` + `deletion_protection` on all 10 tables** (+ wire the dead RETAIN stacks / add to live construct) | Live: deletion protection = FALSE on every table → a stack replace/`cdk destroy` wipes user data. Prerequisite for any migration. | Lo | — | n |
| DB-H2 | **TableRegistry: single table-name + connection authority** (ends the `ARTIFACTS_TABLE_NAME→DYNAMODB_TABLE_NAME→TABLE_NAME` precedence chain; folds connection reuse E1) | Root of the reader/writer-disagreement defect (#1); reader & writer can resolve different tables today. | Md | — | n |
| DB-H3 | **Surface `ValidationException`** (log+metric+raise) instead of swallowing into false "not found" | The silent failure that hides the routing defect from users *and* CI. Cheapest drift signal. | Lo | DB-H2 | n |
| DB-H4 | **Stored canonical `artifact_id` + pass-resolved-upstreams forward** (stop re-fetching VPR by an artifact-status label) | Fixes the broken cover-letter/interview-prep chain (#1); satisfies the FE `artifact_id` round-trip contract. | Md | DB-H2 | **y** (preserve `artifact_id`) |
| DB-H5 | **Idempotency actually wired** (`@idempotent` on billing + workers, keyed on stable business id) | Live: idempotency table is EMPTY. Money-path double-charge + duplicate AI spend. | Md | — | n |
| DB-H6 | **`TransactWriteItems` for multi-item invariants** (create-app + consume-quota; fix E7 non-atomic status write) | Prevents partial state + quota/revenue leakage; §5.3. | Md | DB-H2 | n |
| DB-H7 | **Eliminate request-path Scans** (billing `get_subscription_by_customer_id`→GSI; CR 6-round-trip E5; cover-letter legacy scan) | §5.1 no-Scan; billing scan is on the money path. | Md | GSI work | n |
| DB-H8 | **Single-table `core` migration** — `PK=USER#{sub}`, `SK=APP#{app}#…` item collection; `CoreRepository` sole key-builder; overloaded/minimized GSIs; via expand→dual-write→backfill→dual-read→contract, **reusing the proven CR (FE-UI-044) pattern**, CV-first | The "do it once" best-practice target; kills the 3-schema class structurally; enables one-Query hub (`GET /me/bootstrap`). | Hi (but volume tiny → low end) | DB-H1,H2,H4 | y (keep response shapes; version if needed) |

## MEDIUM priority

| ID | Upgrade | Why | Effort | Contract |
|---|---|---|---|---|
| DB-M1 | **Split the 1,128-LOC god-class** by entity onto TableRegistry (one PR each) | Maintainability + the per-entity surface the migration needs. | Hi | n |
| DB-M2 | **Stop dual-key CV write (E2/E3)** once legacy read cold for a TTL window | Live: cvs carry both `userId/cvId` + `pk/sk`; permanent write amplification. | Md | n |
| DB-M3 | **Minimized GSI projections** (`ALL`→`KEYS_ONLY`/`INCLUDE`) during GSI rebuild | Write/storage amplification (margin); all GSIs currently `ALL`. | Md | n |
| DB-M4 | **VPR version read E4** (version in SK, `Query Limit=1 desc`) | Fires on every VPR write (74% spend path); avoids paginating all versions. | Md | n |
| DB-M5 | **Retire `userEmail` PII partition key** on `knowledge` (or drop the table — see DB-Q4) | Low-cardinality PII PK; §5.3 hot-partition/IDOR. Live: table empty → cheap. | Md→Lo | n |
| DB-M6 | **Access-pattern inventory doc** as the schema contract (§5.1) | The foundation the `core` model is derived from; makes the migration reviewable. | Lo–Md | n |
| DB-M7 | **Error taxonomy** (`NotFound`/`SchemaDrift`/`Conflict`) mapped once at the edge | Divergent error styles across DAL; makes migration observable. | Md | n (preserve status codes) |

## LOW priority (includes Lo-effort quick wins — do opportunistically)

| ID | Upgrade | Why | Effort |
|---|---|---|---|
| DB-L1 ⚡ | Delete dead `knowledge` table (0 items) + dead `DynamoDBStack`/`S3Stack` + stale `dynamodb_spec.yaml` | Removes a live "second source of truth" that misleads migration authors; stops paying for unused table. | Lo |
| DB-L2 ⚡ | Pagination fixes on list/query paths that silently truncate at one page | Correctness — users not seeing their own artifacts. | Lo |
| DB-L3 ⚡ | PITR 7d→35d on PII tables | Live: PITR is ON (good); extend window cheaply. | Lo |
| DB-L4 ⚡ | Schema-enforced TTL; fix TTL-never-expires (tailored-CV/cover-letter grow unbounded) | Cost/hygiene. | Lo |
| DB-L5 | Remove `_SingletonMeta` hidden global state | Testability (flaky cross-test contamination). | Lo |
| DB-L6 | Collapse `api_storage_adapter` into the single key authority | One key-builder promise (§5.2) contradicted by a 2nd translation layer. | Md |
| DB-L7 | `BatchGetItem` audit for remaining fan-out reads | Round-trip reduction. | Md |

---

## Sequencing note
`RETAIN` (DB-H1) is the non-negotiable first step. Then the seams (DB-H2/H3/H4) + the
Lo-effort quick wins, which are also the on-ramp and prerequisites for the `core` migration
(DB-H8). Idempotency + transactions + Scan-elimination (H5–H7) can proceed in parallel with
the seams. The god-class split (DB-M1) precedes DB-H8. The flagship migration (DB-H8) lands
last, reusing the already-proven CR pattern — and because live volume is tiny (users 908 /
artifacts 221 / everything else <150), its backfill is hours, not weeks.
