# CareerVP — Council Context Pack

**Purpose:** This is the *only* evidence file the redesign council reads. It is a
curated, high-signal snapshot of CareerVP's backend as of `main @ 4f7c294`
(2026-06-29), assembled from the codebase, the CDK infra, 8 prior analysis docs,
and 2 best-practice guides. Do **not** re-explore the repo — reason from this pack.

**Framing for the panel:** the datastore (DynamoDB) is being **kept and improved**,
not replaced. A mature phased redesign is *already* documented (see §6). Your job
is to **independently pressure-test, re-sequence, and find blind spots** in that
plan — and to produce a backlog scored for a **solo developer** under the fixed
constraints in §7 — not to rediscover the runbook.

---

## 0. What changed since the last council (READ FIRST — this is a RE-COUNCIL)

Two source docs were updated after the prior council run, and live AWS was re-verified on
**2026-07-08**. The prior council outputs are now stale. Reason from the *updated* facts below;
they override anything later in this pack they contradict.

**Doc updates (authoritative):**
- **`db-upgrade-priorities.md` now carries a concrete `core` table design** (the material change):
  - **SK layout:** `PK=USER#{sub}`; CV at USER level (`CV#{cvId}`, shared across all apps, referenced
    by `cv_id`, never copied); per-app artifacts `APP#{appId}#ARTIFACT#{TYPE}#v{n}` (version in the SK);
    gap responses `APP#{appId}#GAPRESP#{qId}`; app root/hub `APP#{appId}`. One
    `Query(PK=USER#{sub}, SK begins_with "APP#{appId}#")` returns a full artifact set → `GET /me/bootstrap` free.
  - **Artifact-edit / "AI-Assist turn" WRITE pattern:** single-item `UpdateItem` on the exact artifact SK
    + `ConditionExpression` on a `version` attr = the frontend's **409 optimistic-concurrency contract**.
    Large regen: write body to S3, then one conditional `UpdateItem` swapping the pointer + bumping `version`.
    Rare multi-item edits = `TransactWriteItems` (cheap; shared PK). *(NB: the `/ai/assist` endpoint itself is
    still read-only today — infra §3.4 IAM is GetItem/Query only; this pattern governs edit PERSISTENCE.)*
  - **DRY at the CODE layer, not storage:** `CoreRepository` is the sole key-builder (no handler assembles a
    key/table name); shared entities referenced-by-key not copied; any intentional denormalized copy has a
    single write-owner (repo path or a Streams consumer), never hand-maintained across N handlers.
  - **Hot-partition GSI rule (new hard constraint):** every GSI partition key must be user-/high-cardinality-
    scoped (`GSI1PK=USER#{sub}, GSI1SK=STATUS#…`) **or sparse** (index only in-flight items). A
    `GSI1PK=STATUS#{status}` key is explicitly forbidden (low cardinality → hot GSI partition). Avoid LSIs.
  - **Stays OUT of `core`:** `idempotency`, `llm-cache`, `company-research-cache` remain focused tables;
    applications/jobs/artifacts/gap/cv fold into the `USER#` item collection.
- **`aws-infrastructure-configuration-reference.md`** was reformatted + refined (same 16 critical findings —
  no severity changed). Corrections to this pack's §2a: **idempotency PITR = 35 days** (not 7); **llm-cache
  PITR is prod-only → DISABLED in dev**; users table has Contributor Insights (THROTTLED_KEYS). It is a
  **static-code** read → where it disagrees with live verification, **live wins.**

**Live re-verification (2026-07-08, read-only) — every prior ground-truth claim HOLDS:**
deletion protection FALSE on all 10 tables · volumes unchanged (users 908 / artifacts 221 / jobs 144 /
gap 16 / apps 9 / cvs 6 / CR-cache 2 / idempotency 0 / knowledge 0) — only drift is **llm-cache 11→0**
(TTL expiry) · multi-schema drift still physically present · throttle 2rps/burst10 · **0 regional WAF web ACLs
exist** · SNS 0 subscribers · Cognito MFA OFF · 0/31 reserved concurrency · CFN root 415/500 + 4 nested.

**Decide these (the re-council's job — see §8 for the framing):**
1. **Identity keying** — literal `cognito_sub` vs an internal immutable surrogate `user_id`. The user plans
   to add Google/Facebook social IdP (a human gets a different `sub` per provider/pool → account-linking
   fragility, vendor lock-in). This choice IS the `core` PK. **Not a closed decision.**
2. **Is single-table `core` a COMMITTED deliverable or a hypothesis** to re-justify after the cheaper
   decoupled seams (both prior councils demoted it to Med; volume is tiny)?
3. **Knowledge base** keep vs drop (table empty + unwired; two conflicting designs).
4. **Cutover/downtime tolerance + retention window** (tiny volume → backfill is hours).

---

## 1. System snapshot

CareerVP is an AWS-serverless (CDK/Python 3.13) app that turns a user's CV + a job
posting into a chain of AI-generated career artifacts:

```
Base CV → Gap Analysis → Company Research → VPR (Value Proposition Report)
                                              → {Tailored CV, Cover Letter, Interview Prep}
```
plus a read-only "AI Assist" rewriter.

- **Compute:** API Gateway REST (`careervp-core-api`) → ~35 Lambdas (Powertools),
  split into thin sync handlers + an async `*_submit → SQS → *_worker` pattern,
  orchestrated by a **STANDARD Step Functions** chain using `waitForTaskToken`.
- **Data:** 10 DynamoDB tables (all on-demand, PITR 7d) + 6 S3 buckets (CV files,
  VPR bodies, exports). **No RAG/vector layer exists** — all retrieval is key-based;
  generation is one-shot prompt-stuffing.
- **Payments:** Stripe-style webhook (`billing_lambda`) + daily reconcile.
- **Auth:** Cognito User Pool authorizer alongside a self-managed RS256 JWT path.
- **Economics:** ~88% gross margin, **AI-cost-dominated** (VPR ≈ 74% of per-app AI
  spend, ~$0.43/app). AWS infra cost is a rounding error; the margin lever is LLM
  token spend + cache hit-rate, **not** infra.

---

## 2. Data-layer map

### 2a. Live DynamoDB tables (from `infra/careervp/.../api_db_construct.py`)

All `TableV2`, **on-demand billing**, **AWS-owned encryption key** (no CMK),
**`RemovalPolicy.DESTROY`**, **all GSIs project `ALL`**. **PITR: 7d on the 8 PII tables,
35d on `idempotency`, DISABLED on `llm-cache` (prod-only)** — verified live 2026-07-08.

| Table | PK / SK | GSIs | TTL | Stream |
|---|---|---|---|---|
| users (`db`) | `pk` / `sk` | email-index; user_id-index | – | – |
| idempotency | `id` | – | `expiration` | – |
| jobs | `job_id` | idempotency-key-index; user_id-index | `ttl` (~24h) | NEW_AND_OLD |
| cvs | `userId` / `cvId` | – | `expiration` (90d) | – |
| applications | `userId` / `applicationId` | status-index | **none** | – |
| gap_responses | `userId` / `questionId` | – | `expiration` | – |
| knowledge | **`userEmail`** / `knowledgeType` | entity-index | `expiration` | – |
| artifacts | `applicationId` / `artifactId` | type-index | `expiration` | NEW_AND_OLD |
| company_research_cache | `cacheKey` | – | `expiresAt` (30d) | – |
| llm_cache | `cache_key` | – | `expires_at` (prod) | – |

> **Dead-code trap:** a second definition `dynamodb_stack.py::DynamoDBStack` exists
> with *different keys* and `RETAIN`, but is **never instantiated** in `app.py`. The
> `dynamodb_spec.yaml` still names it as owner → the spec is stale vs. reality.

### 2b. DAL modules (from `src/backend/careervp/dal/`)

| Module | LOC | Responsibility |
|---|---|---|
| `db_handler.py` | 117 | Abstract `DalHandler` base + `_SingletonMeta` (hidden global state). |
| `dynamo_dal_handler.py` | **1128** | **God-class**: CV, VPR, tailored CV, cover letter, gap Q/R, company research. |
| `application_repository.py` | 389 | Application state machine, artifact statuses, chain-execution lock. |
| `jobs_repository.py` | 527 | Jobs + VPR async job state; idempotency-key lookup. |
| `subscription_repository.py` | 466 | Billing/subscription; payment-event dedup; **reconciliation scan**. |
| `user_repository.py` | 170 | User PROFILE CRUD, dual-PK legacy fallback. |
| `cv_repository.py` / `cv_dal.py` / `cv_tailoring_dal.py` | 38/100/96 | CV S3 keying; compat CV table; separate `cv-tailoring` table. |
| `knowledge_repository.py` | 117 | Gap responses + company research. |
| `api_storage_adapter.py` | 229 | Logical-ID ↔ physical-key translation (pure). |

### 2c. The root-cause data defect — "three schemas, three IDs"

There is **no single rule for where an artifact lives**. The same logical entity is
addressed through **4+ incompatible PK/SK conventions** across the `users`/`artifacts`/
`jobs` tables. Which physical table a Lambda hits is chosen by **env-var precedence**
(`ARTIFACTS_TABLE_NAME → DYNAMODB_TABLE_NAME → TABLE_NAME`), not a typed contract —
so a reader and writer can resolve to *different* tables. A query against the wrong
schema throws `ValidationException`, which is caught and **silently converted to a
false "not found."** Half of `dynamo_dal_handler.py` is this schema-drift defense.

---

## 3. Curated code excerpts (cost/correctness-critical paths)

**E1 — New boto3 connection on *every* call (latency tax on all ops)**
`dynamo_dal_handler.py:81`
```python
def _get_db_handler(self, table_name):
    session = boto3.session.Session()
    dynamodb = session.resource('dynamodb')
    return dynamodb.Table(table_name)   # no reuse/caching
```

**E2 — Dual key schema written on every CV save (permanent write amplification)**
`dynamo_dal_handler.py:97`
```python
item['userId'] = user_cv.user_id; item['cvId'] = user_cv.cv_id
item['pk'] = user_cv.user_id; item['sk'] = f'CV#{user_cv.cv_id}'  # legacy alias, always written
table.put_item(Item=item)
```

**E3 — Read fallback across two schemas doubles round-trips on drift**
`dynamo_dal_handler.py:119`
```python
try:
    response = table.query(KeyConditionExpression=Key('userId').eq(user_id), ...)
except ClientError as exc:
    if error_code != 'ValidationException': raise
    response = table.query(KeyConditionExpression=Key('pk').eq(user_id) & Key('sk').begins_with('CV#'), ...)
```

**E4 — `get_latest_vpr` fully paginates + validates ALL versions to pick max**
(called by `get_next_vpr_version` on every VPR write) `dynamo_dal_handler.py:356`
```python
while 'LastEvaluatedKey' in response:
    response = table.query(..., ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response.get('Items', []))
latest_item = max(items, key=_parse_record_version)
```

**E5 — `get_company_research`: up to 6 sequential round-trips + in-partition filter**
`dynamo_dal_handler.py:1101`
```python
for partition_key, prefix in query_candidates:   # 3 gets, then 3 queries
    response = table.query(KeyConditionExpression=Key('pk').eq(partition_key) & Key('sk').begins_with(prefix),
                           FilterExpression=Attr('sk').contains(job_id), Limit=1)
```

**E6 — Full-table Scan on the subscription-reconciliation path**
`subscription_repository.py:388` (also a point-lookup Scan at `:127`, and a
point-read Scan in `legacy_read_cover_letter` at `dynamo_dal_handler.py:784`)
```python
while True:
    response = self._table.scan(**kwargs)      # grows linearly with the whole users table
    results.extend(response.get('Items', []))
    if not response.get('LastEvaluatedKey'): break
```

**E7 — Non-atomic two-step nested-map write (partial-state risk; no transaction)**
`application_repository.py:284`
```python
# Step 1: ensure map exists ... then Step 2: set nested keys — two separate update_item calls.
# No TransactWriteItems anywhere in the codebase; a crash between steps leaves partial state.
```

**E8 — Correct atomic worker claim (GOOD pattern to preserve/replicate)**
`jobs_repository.py:300`
```python
update_kwargs['ConditionExpression'] = '#status = :expected_status'   # conditional write = idempotent claim
```

**E9 — API throttle floor cannot serve target scale** `api_construct.py:338`
```python
throttling_rate_limit=2, throttling_burst_limit=10   # 2 req/s caps the ENTIRE API
```

**E10 — JWT private key injected as plaintext Lambda env var** `api_construct.py:894`
```python
"JWT_PRIVATE_KEY": ssm.StringParameter.value_for_string_parameter(self, f"/careervp/{ENV}/jwt-private-key")
# resolved at synth → lands in Lambda config as plaintext (contrast: ANTHROPIC key passed as SSM *path*)
```

**Data-layer takeaways:** (1) no connection reuse; (2) zero transactions/batching
despite multi-item writes; (3) three Scans (one on a reconciliation path); (4)
pervasive dual-schema read/write fallback = frozen half-migration → permanent write
amplification + doubled read latency; (5) 1128-LOC 6-entity god-class; (6) multiple
independent boto3/table-name resolution points, no single authority.

---

## 4. Known findings catalog (from prior analysis — to be re-prioritized, not re-found)

**CRITICAL**
- `RemovalPolicy.DESTROY` + no deletion protection on all stateful resources → data
  loss on stack replacement; **makes any in-place migration unsafe.** (Blocks Phase 3.)
- **Auth bypass:** `extract_user_id()` falls back to client-supplied `x-user-id`
  header when JWT claims absent (`auth_utils.py:44`). Plus `AUTHORIZER_DISABLED=true`
  on `cv_tailoring_func` in all non-prod envs.
- **No idempotency on money path:** `@idempotent` wired to **zero** handlers → Stripe
  retries can double-charge.
- **Silent SQS loss:** 3 of 4 workers return `200` instead of `batchItemFailures`;
  built DLQs never wired.
- **Duplicate AI spend:** SQS visibility timeout == Lambda timeout (1×) → re-delivery
  mid-flight → duplicate Sonnet/Haiku calls.
- **Wildcard IAM:** `kms:Decrypt`/`GenerateDataKey` + AppConfig on `resources=["*"]`;
  single shared role across 13+ Lambdas. *(Nuance: DynamoDB/S3 grants ARE
  least-privilege — no `dynamodb:*`. The real issues are the shared role + SQS KMS `*`.)*

**HIGH**
- 3-schema / 3-id data model (§2c) — the flagship refactor target.
- `ServiceStack` at the **500-resource CFN ceiling** → blocks further additive change.
- No `max_concurrency` on AI workers → Anthropic rate-limit stampede.
- All GSIs project `ALL` → write/storage amplification (margin).
- API throttle 2 req/s (E9) → cannot serve <10k users.
- `userEmail` PII partition key on `knowledge`; CV bucket CORS `*`, unversioned.
- JWT keys plaintext env (E10); `retry_attempts=0` drops async events.

**MEDIUM / LOW**
- TTL never-expires (Tailored CV / Cover Letter grow unbounded).
- Interview-prep orphan row; `_is_stale` compares never-written fields (latent loop).
- Only 7 of 35 Lambdas monitored; no DLQ-depth alarms; **SNS topics may have no
  subscribers** (alarms notify no one); 1-day log retention.
- x86 not ARM64; prompt-cache gaps; Tavily 15k-token input bloat.
- WAF prod-only, no edge rate-limit; Cognito 8-char no-symbol passwords, MFA off.

---

## 5. Best-practice delta (measuring stick — DB-weighted)

From `AWS_Serverless_Best_Practices.md` + `agentic-development-guide.md`. Mark the
codebase pass/fail against each. (Full list in the guides; DB-critical subset here.)

**DynamoDB / data**
- [ ] Access patterns enumerated *before* modeling; schema derived from queries.
- [ ] Every read is `GetItem`/`Query` on a key/GSI — **no Scan on any request path**. *(FAIL: E5/E6)*
- [ ] Money/quota paths use `ConditionExpression`; multi-item invariants use
  `TransactWriteItems`. *(PARTIAL: conditionals yes, transactions no — E7)*
- [ ] High-cardinality PKs; no low-cardinality/PII PK (hot-partition + IDOR). *(FAIL: `userEmail` key)*
- [ ] Co-read entities modeled as one item collection (shared PK, ranged SK) → one Query. *(FAIL: cross-table fan-out)*
- [ ] Exactly one typed repository per entity; **no env-var table-alias precedence chain**. *(FAIL: §2c)*
- [ ] GSIs overloaded + minimized projection (`KEYS_ONLY`/`INCLUDE`, not `ALL`). *(FAIL: all `ALL`)*
- [ ] On-demand for spiky load; provisioned only with a proven cheaper baseline. *(PASS, revisit at scale)*
- [ ] PITR in prod; backup before risky migration. *(PARTIAL: PITR yes; DESTROY policy negates safety)*
- [ ] TTL on ephemeral items, **schema-enforced**. *(FAIL: app-code TTL, some never expire)*
- [ ] Streams for CDC/backfill; consumers idempotent. *(PARTIAL: 2 tables only)*
- [ ] Pagination always handled; no unbounded in-memory assembly. *(PARTIAL: several truncate silently)*
- [ ] Large blobs in S3 with a DynamoDB pointer. *(PASS: VPR/CV in S3)*
- [ ] PK/SK & GSI changes never in place on a live table — new table/GSI + migration. *(governs Phase 3)*

**Reliability / security (DB-adjacent)**
- [ ] `@idempotent` on all at-least-once + money paths, keyed on a stable business id. *(FAIL: zero handlers)*
- [ ] Every async source has DLQ + maxReceiveCount + depth alarm + replay. *(FAIL: unwired)*
- [ ] SQS consumers report partial-batch failures. *(FAIL: 3/4 return 200)*
- [ ] Visibility timeout ≥ ~6× function timeout. *(FAIL: 1×)*
- [ ] Identity derived only from validated JWT claims; no client-supplied id fallback. *(FAIL: x-user-id)*
- [ ] Every data access scoped to the authenticated subject. *(FAIL: IDOR-prone get_job)*
- [ ] One execution role per Lambda; ARN-scoped actions. *(PARTIAL: scoped grants, shared role)*
- [ ] Secrets never as plaintext env. *(FAIL: JWT keys)*

**Cost (margin)**
- [ ] AI model routing enforced *and measured* (real token usage, not `len/4`). *(FAIL: estimator only)*
- [ ] Prompt caching on cache-eligible prefixes; input context bounded. *(PARTIAL: gaps)*
- [ ] No idle provisioned capacity; ARM64 where possible. *(PARTIAL: on-demand good; x86)*

---

## 6. The already-documented redesign (the plan to pressure-test)

Governing rule across all docs: **expand → dual-write → backfill → dual-read →
contract**; every step independently reversible; never mutate/rename a live
table/GSI/bucket or change PK/SK in one deploy.

- **Phase 0 — Guardrails & headroom (prerequisite):** flip stateful resources to
  `RETAIN` + deletion protection; remove `auto_delete_objects`; adopt live resources
  via `cdk import`; decompose the 500-resource stack into nested stacks (<400 each)
  with a CI resource-count gate.
- **Phase 1 — CRITICAL security (additive + canary):** delete `x-user-id` fallback
  (JWT-only); `@idempotent` on billing keyed by Stripe event id; scope KMS/AppConfig
  wildcards + split shared role; enforce partition key in `get_job`; lock CV bucket
  CORS/versioning; WAF all envs; add gitleaks.
- **Phase 2 — Reliability:** `ReportBatchItemFailures` on all workers; visibility
  timeout ≥ 6×; `max_concurrency` 3–5 on AI workers; DLQ-depth + worker alarms;
  canary/alias traffic shifting with auto-rollback.
- **Phase 3 — Single-table `core` (flagship):** collapse per-app artifacts into one item
  collection — `PK=USER#{sub}` (never email; `sub`-vs-surrogate-`user_id` is open, see §0/§8),
  CV at USER level (`CV#{cvId}`, referenced not copied), per-app artifacts
  `APP#{appId}#ARTIFACT#{TYPE}#v{n}`, gap `APP#{appId}#GAPRESP#{qId}`; large bodies in S3 with a
  pointer. **GSIs must be user-/high-cardinality-scoped or sparse — a `STATUS#{status}` GSI PK is
  forbidden** (hot-partition rule). `idempotency`/`llm-cache`/`company-research-cache` stay OUT of
  `core`. `CoreRepository` = **sole key-builder** (no env-var precedence); edits persist via conditional
  `UpdateItem` on `version` (the 409 contract). Migrate expand→dual-write→backfill→dual-read→contract,
  per-entity CV-first, reusing the proven CR (FE-UI-044) pattern, drift metric from Streams. On contract:
  fix TTL, drop orphan row, retire `userEmail` key, unify CV PK. (Full design in
  `db-upgrade-priorities.md`; earlier YAML spec `docs/best_practices/yaml/dynamodb_modeling_spec.yaml`
  not deployed. Volume tiny → backfill is hours, not weeks.)
- **Phase 4 — API/compute:** versioned routes; `GET /me/bootstrap` aggregate (one
  Query under `core`) to kill the chatty frontend; HTTP caching.
- **Phase 5 — Cost & observability:** ARM64; prompt-cache migration; truncate Tavily;
  SLOs, dashboards, cost-anomaly alarms.

**Explicitly out of the DB-core scope (parallel/deferred tracks):** RAG/vectors
(feature enabler, not architecture; blocked on a bilingual corpus that doesn't exist;
avoid OpenSearch Serverless ~$345/mo), Sonnet-5 migration (pilot on VPR only), and
artifact compression (payoff capped — cost is *output* tokens).

---

## 7. Fixed constraints (every lens must obey; drive all scoring)

- **Scale:** dev today → hundreds → **< 10k concurrent** max. DynamoDB fits; focus on
  access-pattern efficiency & hot-partition avoidance, not raw throughput.
- **Cost / margin:** maintain **> 70% profit margin**. Cost is a real constraint. Note
  the dominant lever is LLM token spend, not infra — weigh DB cost items accordingly.
- **Security:** conscious; **respect personal-data control** (export/delete, least
  privilege, encryption). **No formal GDPR / data-residency obligation** — do not
  gold-plate for compliance not owed.
- **Team:** **solo developer.** Penalize big-bang migrations and high-coordination
  work; favor incremental, independently-reversible, flag-gated changes.
- **Frontend:** **out of scope** except where a change alters the API request/response
  contract (flag those explicitly).
- **Datastore decision is CLOSED:** keep DynamoDB and improve it. Do **not** propose or
  evaluate migrating to a relational/other store.

### Scoring axes (score EVERY backlog item on all three)
- **Importance** — impact on security, reliability, cost/margin, or maintainability.
- **LOE** — solo-dev effort: **S / M / L / XL**.
- **Difficulty** — technical risk / uncertainty / blast radius: **Low / Med / High**.

---

## 8. Open questions (flag if they change a recommendation)

**High-stakes decisions the re-council MUST resolve decisively (see §0):**
- **HS1. Identity keying** — literal `cognito_sub` as the `core` PK, or an internal immutable surrogate
  `user_id` resolved from one-or-many `sub`s at the edge? Driver: planned Google/Facebook social IdP
  (`sub` is per-provider/per-pool). Trade: surrogate adds an indirection layer but survives IdP changes.
- **HS2. Is single-table `core` COMMITTED or a hypothesis?** Both prior councils demoted it to Med and said
  the cheaper decoupled seams (single key-authority, kill 3-schema drift, stop dual-key CV write, retire PII
  PK) capture most of the value. Volume is tiny. Decide: staged-committed (seams now, core-collapse as a later
  go/no-go wave) vs. capture-value-and-stop.
- **HS3. Knowledge base keep vs drop** — table empty + unwired; two conflicting designs (v1 doc-corpus vs KV
  user-memory keyed on PII `userEmail`). Drop dead plumbing now and reintroduce later on a non-PII key?
- **HS4. Cutover/downtime tolerance + retention window** — needed to size Track D (tiny volume → hours).

**Resolved by live verification 2026-07-08 (no longer open):**
- ~~Which schema is deployed vs the dead `DynamoDBStack`?~~ → **Active `api_db_construct` schema is deployed**
  (recon: live keys are `userId/cvId`, `userId/applicationId`, `job_id`, `pk/sk`, etc.); legacy `RETAIN`
  `user_email` stack is dead code. Delete it (DB-L1).
- ~~Should `jobs`/`applications` be unified, or does `core` subsume both?~~ → **`core` subsumes both** as
  `APP#{appId}` items; only the 3 caches stay separate (db-upgrade update).
- ~~Are alarm SNS topics subscribed?~~ → **No** (0 subscribers, dev+staging).

**Still-open technical checks (flag if they change a recommendation):**
- `cv_tailoring` write target — does a `pk/sk` write to a `userId/cvId` table raise `ValidationException` at
  runtime? (recon shows cvs carries BOTH conventions, so the dual-write path masks it.)
- Make `_is_stale` explicit-and-tested or delete it (compares never-written fields).
- Model `chain_execution_status` as first-class state (stale `RUNNING` seen in dev).
- Real VPR economics **unmeasured** (2 cost samples, both Haiku); every Sonnet figure estimated — cost-ranked
  items inherit this uncertainty.
