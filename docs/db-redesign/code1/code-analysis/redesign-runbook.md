<!--
  CareerVP — Redesign Runbook (executable migration). Companion to careervp-architecture-v2.md.
  Governing rule: additive-first / expand-contract. Every step independently reversible.
  Reconciled against `main` @ HEAD 4f7c294 (2026-06-29).
-->

# CareerVP — Redesign Runbook

**Companion to:** [`careervp-architecture-v2.md`](./careervp-architecture-v2.md) (the as-built record + target). This doc is the **executable migration** — ordered, reversible steps with success metrics and rollback.

**Governing rule:** *additive-first / expand-contract.* Never mutate or delete a live resource in place — add the new alongside the old, shift traffic gradually, verify, retire the old. Every step is independently reversible without data surgery.

---

## 0. Golden rules
- **Never edit a live stateful resource destructively.** No renaming/removing a table, GSI, or bucket, and **no PK/SK change** in a single deploy — CloudFormation replaces → data loss. This is doubly dangerous today because stateful resources are `RemovalPolicy.DESTROY` (fixed in Phase 0).
- **Decouple deploy from release.** Ship dark behind feature flags (AppConfig — already wired); release = flip a flag, not a deploy.
- **One reversible change at a time**, each with a success metric and a rollback that needs no data surgery.
- **Back up before every risky step.** On-demand DynamoDB backup + confirm PITR; S3 versioning on.
- **Test the migration itself** in staging with prod-shaped data volume — not just the new code.
- **Same-account isolation.** All envs share one account, isolated by `{env}` naming + IAM ARN scoping. Verify every role's ARNs carry the `{env}` suffix before running migration work.

---

## Phase 0 — Guardrails & headroom (NO user-facing change)

> Pure refactor of stack composition + removal policies. This phase **unblocks** the data migration; until it lands, expand-contract is unsafe.

### 0.1 Flip stateful resources to safe policies
- [ ] Set `RemovalPolicy.RETAIN` + `deletion_protection=True` on **all** DynamoDB tables and S3 buckets in `api_db_construct.py`.
- [ ] Remove `auto_delete_objects=True` on the CV bucket (`api_db_construct.py:165`); enable versioning on the CV bucket.
- **Success metric:** `cdk diff` shows only metadata/policy changes, zero resource replacements.
- **Rollback:** revert the construct change (policy-only, no data impact).

### 0.2 Move stateful resources to a top-level stack
- [ ] Wire the dead `DynamoDBStack`/`S3Stack` (or one `StatefulStack`) into `app.py` as **top-level** stacks; pass table/bucket refs into `ServiceStack` via **constructor props** (never `Fn::ImportValue`).
- [ ] Migrate ownership of existing tables/buckets without replacement — use **`cdk import`** / logical-id retention so CloudFormation adopts the live resources rather than recreating them. Verify each retained logical id.
- **Success metric:** tables/buckets now in the stateful stack; `cdk diff` on `ServiceStack` shows them removed-from-template but **retained** (not deleted); data intact.
- **Rollback:** stateful stack and parent both reference the same physical names; revert app.py wiring.
- ⚠ **This is the single highest-risk Phase-0 step** — rehearse in staging with prod-shaped data and an on-demand backup first.

### 0.3 Decompose the parent stack
- [ ] Carve high-churn feature Lambda groups into additional nested stacks so **no template exceeds ~400 resources** (5 resources/function headroom). Pass shared refs as props.
- [ ] Add a **CI resource-count gate**: synth each template, fail if any `Resources` count > 400.
- **Success metric:** every synthesized template < 400 resources; CI gate green.
- **Rollback:** nested stacks are additive; collapse back if needed.

### 0.4 Safety net
- [ ] Confirm PITR on all tables; take on-demand backups; confirm S3 versioning.
- [ ] Stand up staging with prod-shaped data volume; `cdk diff` in CI against deployed state.

---

## Phase 1 — CRITICAL security (additive + canary)

Each fix ships behind a flag/alias, canaried, reversible.

- [ ] **Remove the `x-user-id` identity fallback** (`auth_utils.py:44-47`). Identity from validated JWT claims only. *Pre-check:* grep logs to confirm no live client relies on the header. **Metric:** zero 401 spike on canary; auth-enforcement test passes. **Rollback:** flag.
- [ ] **`@idempotent` on billing + AI-cost handlers** (idempotency table already exists), keyed by Stripe event id. **Metric:** duplicate-webhook test produces one charge. **Rollback:** flag.
- [ ] **Scope wildcard IAM**: KMS → queue key ARNs; AppConfig → application ARN (`api_construct.py:778,516`). **Begin splitting the shared role** per artifact domain (one role per Lambda is the target). **Metric:** `cdk diff` shows narrowed policies; no `AccessDenied` on canary. **Rollback:** revert policy.
- [ ] **Enforce the partition key in `get_job`** (kill IDOR, `jobs_repository.py:196-223`). **Metric:** cross-user fetch returns not-found.
- [ ] **Lock CV bucket CORS** to app origins; keep versioning (from 0.1).
- [ ] **WAF in all environments** (or document the dev trade-off in `.checkov.yaml`).
- [ ] **Add secret scanning** (gitleaks) to CI.

---

## Phase 2 — Reliability hardening (additive)

- [ ] **`ReportBatchItemFailures` on all SQS workers** — fix `vpr_worker_handler.py:619`, `cover_letter_handler.py:487`, `interview_prep_handler.py:151` to return partial-batch failures (CR worker is the reference). **Metric:** an injected poison message reaches the DLQ instead of being deleted.
- [ ] **Visibility timeout ≥ 6× Lambda timeout** on every AI queue (today they're 1×: vpr 600s/600s, cover-letter 300s/300s, interview-prep 300s/300s). **Metric:** no duplicate delivery while a worker is mid-flight under load test.
- [ ] **`max_concurrency` (3–5) on AI worker event sources** to protect the Anthropic rate limit. **Metric:** sustained burst does not trip provider 429s.
- [ ] **DLQ-depth alarms + worker coverage** in monitoring (add the ~24 worker Lambdas + `ApproximateNumberOfMessagesVisible` on DLQs to `service_stack.py:72-80`). **Metric:** a stuck DLQ pages on-call.
- [ ] **Canary/alias traffic shifting** (CodeDeploy linear/canary) with auto-rollback on error/p99 alarms; fix the frontend rollback job to restore the prior build.
- [ ] Fix the likely-inverted `_build_dashboard_factory` (`monitoring.py:214-217`); raise log retention to 30–90d.

---

## Phase 3 — DynamoDB → single-table `core` (expand → dual-write → backfill → dual-read → contract)

> The hardest, most valuable phase. Target schema and the typed storage contract are in architecture-v2 §5.2. **Bypass the autouse resolver mock** (`tests/conftest.py`) — add tests that drive real `get_artifact`/worker resolution against moto tables with the actual key schemas, or this whole defect class stays invisible.

### 3.1 Expand (additive, no behavior change)
- [ ] Create the new `core` table (`PK`/`SK` generic, `GSI1` for status) in the stateful stack. Adding a table is non-destructive.
- [ ] Implement `CoreRepository` as the **only** key-builder, importing the typed `artifact_type → (table, key)` contract. No env-var precedence.
- [ ] Streams already on `artifacts`/`jobs`; confirm CDC capture.
- **Rollback:** delete the new table (no reads yet).

### 3.2 Dual-write
- [ ] Behind flag `core_dual_write`, writers emit to **both** the legacy location and `core`. Reads still legacy.
- [ ] Converge the `TABLE_NAME`/`DYNAMODB_TABLE_NAME`/`USERS_TABLE_NAME` aliases to one binding per logical store as part of this.
- **Metric:** every new artifact appears correctly shaped in `core`; stream reconciliation shows zero drift.
- **Rollback:** flag off (legacy unaffected).

### 3.3 Backfill
- [ ] Throttled, idempotent batch job (Step Functions + paginated export, or S3-export→Glue for the ~906-item users table) copies history into `core`. Run against on-demand capacity.
- [ ] Stream-driven reconciliation emits a **drift metric**; resolve the 3-id problem by deriving the canonical stored key per dossier §9.2.
- **Metric:** drift metric → 0; counts match per artifact type.

### 3.4 Dual-read / shift reads
- [ ] Behind flag `core_read`, flip reads to `core`, **canary by user cohort** (internal → small % → all). Shadow-compare against legacy.
- [ ] **Validate the whole chain to a persisted result**, not just the gate's HTTP status (dossier §6.4 — fixing the gate unmasks worker defects). Confirm cover-letter/interview-prep workers consume the gate-resolved upstream (or re-resolve by `application_id`), never by `*_artifact_id`.
- **Metric:** shadow-read parity ≥ threshold; zero `ValidationException`; downstream artifacts persist end-to-end.
- **Rollback:** flag back to legacy reads.

### 3.5 Contract (retire old)
- [ ] After `core` serves 100% with zero drift for a full validation window, **stop dual-writing**, then **retire legacy artifact locations in a later, separate deploy**.
- [ ] Fold in the data-correctness fixes now that there's one home: **TTL** (write the table's actual TTL attr), remove the **interview-prep orphan `prep_id` row**, drop the **`userEmail` PII key** (knowledge data → `core` under `USER#{user_id}`).
- [ ] Make staleness an explicit tested contract or remove `_is_stale`; model the chain lock as first-class state.
- [ ] Keep a final on-demand backup of each retired table before deletion.
- **Metric:** legacy reads = 0 for the full retention window before deletion.
- ⚠ Never remove a read path and the underlying table in the same deploy.

---

## Phase 4 — API / compute modernization
- [ ] Additive schema changes preferred; breaking changes → new `/v2` route, both served in parallel, old deprecated after usage → 0.
- [ ] Complete the `{proxy+}` route collapse deferred earlier (frees API-GW resources; respects the 500 limit).
- [ ] Retire old compute after a bake window at 100% with no regression.

---

## Phase 5 — Cost & observability tuning
- [ ] Switch Lambdas to **ARM64/Graviton** (validate Powertools/boto3 compatibility).
- [ ] **Prompt-cache migration:** Gap/Cover-Letter/Interview-Prep → `complete(use_system_cache=True)` (pad system prompts to the 1,024-token cache minimum).
- [ ] **Truncate Company Research** raw Tavily content (the measured 15k-token input) or set `include_raw_content: false`.
- [ ] Verify VPR stages 4–6 `max_tokens` aren't truncating; confirm `AI_ASSIST_MODEL` isn't Sonnet in prod.
- [ ] Define **SLOs** (latency/availability) with error budgets; per-feature dashboards; cost anomaly alarms; AI-spend metric (Sonnet vs Haiku).

---

## Verification & rollback discipline (every phase)
- **Pre-cutover:** on-demand backups, confirmed PITR, S3 versioning, a written rollback runbook naming the exact flag/alias to revert.
- **During:** canary alarms (error rate, p99, DLQ depth, DynamoDB throttles) → **auto-rollback**; correlation IDs trace the new path; shadow-comparison metrics.
- **Post-cutover:** bake at 100% before retiring old resources; cost/latency dashboards confirm no regression.
- **Rollback test:** exercise the rollback path **in staging**, never assume it.
- **Blast-radius limit:** migrate per-cohort (internal → small % → all).

## Block these in any redesign PR
- A single deploy that renames/removes a live table, GSI, or bucket, or changes a PK/SK → **CRITICAL**.
- Read path switched to `core` before backfill + reconciliation complete.
- A "big bang" cutover with no canary, no flag, no rollback.
- `removal_policy=DESTROY` (re)introduced on a stateful resource.
- Migration batch job running unthrottled against live table capacity.
- New feature resources added to an already-near-full stack (>400 resources) instead of a new nested stack.
- An IAM role/policy scoped to ARNs spanning environments (no `{env}` suffix).
