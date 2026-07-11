# AWS Serverless Best Practices

> **Audience:** Claude Code (automated reviewer/redesigner).
> **Purpose:** A structured evaluation rubric for auditing and redesigning AWS serverless applications into **production-ready, anti-fragile, hardened, high-throughput** systems. Tailored to **CareerVP** (CDK Python IaC, AWS Lambda + Powertools, API Gateway, DynamoDB, S3, SQS, Step Functions, Cognito, WAF, Amplify/Next.js frontend).
> **Mode of use:** Walk a codebase domain by domain. For each check, classify by severity, cite the file/line, and propose the recommended pattern.
> **Prime directive:** Optimize for systems that are *resilient to change and load, non-fragile, easy to evolve, and hardened against attack* — never for cleverness or premature optimization.

---

## 0. How to Use This Document (for Claude Code)

1. **Scope the system first.** Enumerate stacks/constructs (`infra/careervp/*.py`), Lambda handlers (`src/backend/careervp/handlers/`), the DAL (`src/backend/careervp/dal/`), and the logic layer (`src/backend/careervp/logic/`). Map each resource to its access patterns and the IAM principals that touch it.
2. **Evaluate per domain.** Each section is a rubric: **Principle → Check → Red Flags → Recommended Pattern**. Treat every `[ ]` as an auditable assertion (PASS / FAIL / N/A).
3. **Classify every finding by severity** (scale below).
4. **Cite evidence** as `file_path:line_number`, or state the explicit absence of a control.
5. **Propose redesign, don't just flag.** Each FAIL gets a minimal, idiomatic fix matching surrounding code (CDK Python / Powertools).
6. **Respect documented trade-offs** (`.checkov.yaml`). A `dev`-only skip with a prod plan is **INFO**, not a defect.
7. **Never destabilize the running system.** Any change you propose must be deliverable via the safe-migration playbook in **§18** — additive first, reversible always.

### Severity Scale

| Severity | Meaning | Examples |
|----------|---------|----------|
| **CRITICAL** | Exploitable now / data loss / auth bypass | Public S3 with PII, `iam:*` on `*`, unauthenticated mutating endpoint, secrets in code |
| **HIGH** | Likely incident under load or attack | Wildcard IAM on data, no input validation on writes, no encryption at rest, no idempotency on payments, hot partition on a core table |
| **MEDIUM** | Reliability/cost/maintainability risk | No DLQ on async consumer, oversized Lambda memory, no throttling, no PITR |
| **LOW** | Hardening / hygiene | Missing tags, log retention unset, missing alarm |
| **INFO** | Documented trade-off / stylistic note | `dev`-only Checkov skip with prod follow-up |

### Finding Template
```
[SEVERITY] <domain>: <one-line problem>
  Evidence: <file_path:line>
  Why it matters: <impact on resilience / security / cost>
  Recommended: <concrete fix + snippet reference>
  Migration: <how to ship it safely per §18 — additive / expand-contract / canary>
  Effort: S | M | L
```

---

## 1. Production-Readiness & Anti-Fragility Principles (Anchor)

These are the lenses every finding ladders up to. A production system is not "feature-complete code" — it is code plus the operational properties below.

- [ ] **Everything is reproducible from code.** Tear down and rebuild any environment from `infra/` + pipeline alone. No console artifacts, no snowflake state.
- [ ] **Stateful and stateless are separated.** Compute redeploys constantly; data must never be at risk from a code deploy. Different stacks, different removal policies.
- [ ] **Every change is reversible.** Versioned Lambdas/aliases, CloudFormation rollback, expand-contract DB changes, feature flags. You can always go back without data loss.
- [ ] **Failure is designed-for, not exceptional.** Timeouts, retries+backoff+jitter, DLQs, idempotency, circuit breakers, graceful degradation are present on every dependency call.
- [ ] **Load is bounded and shed gracefully.** Throttling, reserved/maximum concurrency, queue buffering, backpressure — the system degrades, it does not collapse.
- [ ] **Identity and least privilege are non-negotiable.** Every request authenticated at the edge; every principal minimally scoped; every datum encrypted.
- [ ] **Observable end to end.** Logs + metrics + traces + alarms-to-on-call answer "is it healthy, why did it fail, what did it cost?" without code spelunking.
- [ ] **Anti-fragile, not just robust.** The system gets *safer* under stress: autoscaling, on-demand capacity, retries that back off, breakers that isolate, alarms that catch regressions before users do.
- [ ] **Easy to evolve.** Thin handlers, logic isolated from I/O, contracts/versioned APIs, tests that gate merges. A new feature is additive, not a rewrite.

**Well-Architected mapping:** Operational Excellence · Security · Reliability · Performance Efficiency · Cost Optimization · Sustainability. Tag each finding with the pillar it serves.

**Master red flag:** Any resource not traceable to a CDK construct, or any change that cannot be rolled back without manual data surgery.

---

## 2. Infrastructure as Code (CDK Python)

**Principle:** Infrastructure is versioned, reviewed, policy-scanned, and decomposed by blast radius.

### Checks
- [ ] All resources in CDK; zero drift (run `cdk diff` in CI against deployed state).
- [ ] **Stacks split by lifecycle & blast radius** (data vs. compute vs. edge), as this repo does (`dynamodb_stack`, `s3_stack`, `service_stack`, `frontend_stack`, nested `ai_assist_nested_stack`). A compute redeploy must not be able to replace a table or bucket.
- [ ] **Cross-stack references are stable.** Prefer importing by stable name/SSM parameter over CloudFormation `Export`/`Fn::ImportValue` for resources you may need to recreate (exports create deletion deadlocks). This directly affects how safely you can redesign (§18).
- [ ] Consistent, environment-aware naming via one helper (`NamingUtils` → `careervp-{feature}-{type}-{env}`); no scattered physical names.
- [ ] `RemovalPolicy.RETAIN` + `deletion_protection` on all stateful resources (tables, buckets, user pools). ✅ Repo retains tables.
- [ ] Environment config externalized (context/SSM), not `if env == "prod"` magic strings.
- [ ] **Tagging strategy** applied app-wide (`Project`, `Environment`, `Feature`, `Owner`, `CostCenter`) via `Tags.of(app)` — enables cost attribution and safe targeted deploys.
- [ ] Static analysis gates synth: **Checkov** ✅ / cdk-nag. `cdk synth` clean; assertion/snapshot tests in `infra/tests`.
- [ ] **Constructs are composable and reusable** (L3 constructs per feature) so new features reuse hardened building blocks instead of copy-paste.

### 2.1 Nested-Stack Decomposition & the 500-Resource Limit (REQUIRED for CareerVP)

**Context:** CloudFormation enforces a **hard limit of 500 resources per stack** (not adjustable via Service Quotas). CareerVP is already approaching it in a single stack, so the architecture **must** decompose into **nested stacks**. This is both a scaling necessity and a resilience win (smaller blast radius, faster targeted deploys).

**How nested stacks help the limit:**
- A nested stack appears in its **parent as a single `AWS::CloudFormation::Stack` resource** — so 10 nested stacks of ~450 resources each = ~4,510 effective resources while each individual stack stays under 500.
- The whole tree (parent + all descendants) may contain at most **500 stacks**, and nesting can go up to **5 levels deep** — ample headroom for a serverless app.
- In CDK, instantiate `NestedStack` (the repo already does this with `ai_assist_nested_stack.py`) and the parent reference is wired automatically; cross-nested-stack values pass as **constructor props / CfnParameters / CfnOutputs**, not brittle `Fn::ImportValue`.

**Checks**
- [ ] **No single stack approaches 500 resources.** Count resources in synthesized templates (`cdk synth` → inspect each template's `Resources`); flag any stack > **~400** as **HIGH** (headroom for the inevitable additions — a Lambda alias + version + log group + permission + role is 5 resources per function).
- [ ] **Decompose by feature/bounded-context AND by lifecycle**, e.g. parent `ServiceStack` with nested stacks: `AuthNestedStack`, `VprNestedStack`, `CvNestedStack`, `CompanyResearchNestedStack`, `BillingNestedStack`, `AiAssistNestedStack` (✅ exists). Keep **stateful resources in their own stacks** (`dynamodb_stack`, `s3_stack`) — those should generally be **top-level**, not nested under churning compute, so a compute redeploy can never replace data.
- [ ] **Stateful vs. nested-compute boundary respected.** Tables/buckets/user pools live in dedicated stacks with `RETAIN`; nested stacks hold the per-feature Lambdas, queues, SFN, API resources that change often.
- [ ] **Pass shared resources in as props** (table, bucket, user-pool references) from a parent or a top-level stateful stack into each nested stack's constructor — avoids `Export`/`ImportValue` deletion deadlocks and keeps nested stacks independently updatable.
- [ ] **Mind nested-stack update semantics:** updating a nested stack updates the parent change set; a failed nested update can roll back the parent. Keep nested stacks cohesive so a deploy touches the smallest necessary tree.
- [ ] **Watch other per-stack limits too:** 200 parameters, 200 mappings, 200 outputs, 1 MB template body (use S3-backed templates / asset bundling — CDK handles this for nested stacks automatically). Outputs proliferate when wiring many nested stacks — prefer passing object references in code over CfnOutput chains.
- [ ] **IAM roles count as resources** — sharing nothing is correct for least privilege, but be aware each function's role/policy/log-group/version/alias add up; this is another reason to split functions across nested stacks.

**Red Flags**
- A monolithic stack synthesizing **> 450 resources** → imminent deploy failure (**HIGH**).
- Nested stacks coupled via `Fn::ImportValue` instead of props → can't update/recreate independently (**MEDIUM**).
- Stateful resources (tables/buckets) nested **under** a high-churn compute stack → a compute change risks data resources (**HIGH**).
- New features bolted onto an existing near-full stack instead of a new nested stack.

**Recommended Pattern**
```python
# Top-level stateful stacks (own lifecycle, RETAIN) — created once, rarely changed.
data = DynamoDBStack(app, naming.stack_name("data"))
storage = S3Stack(app, naming.stack_name("storage"))

# Parent service stack composes per-feature NESTED stacks, passing shared refs as props.
class ServiceStack(Stack):
    def __init__(self, scope, cid, *, core_table, artifacts_bucket, user_pool, **kw):
        super().__init__(scope, cid, **kw)
        VprNestedStack(self, "Vpr", core_table=core_table, artifacts_bucket=artifacts_bucket)
        CvNestedStack(self, "Cv", core_table=core_table, artifacts_bucket=artifacts_bucket)
        BillingNestedStack(self, "Billing", core_table=core_table)
        AiAssistNestedStack(self, "AiAssist", core_table=core_table)   # ✅ already nested
        # each NestedStack stays well under 500 resources; each is one resource here.

ServiceStack(app, naming.stack_name("service"),
             core_table=data.core_table, artifacts_bucket=storage.artifacts_bucket,
             user_pool=auth.user_pool)
```
**Anti-pattern**
```python
# BAD: everything in one Stack — will breach the 500-resource hard limit and fail to deploy.
class MegaStack(Stack):
    def __init__(self, ...):
        # auth + vpr + cv + cover + interview + billing + research + monitoring + waf ...
        # 600+ resources -> CloudFormation rejects the template.
```

### Red Flags
- Stateful resources in the same stack as PR-frequency compute.
- `removal_policy=DESTROY` on anything holding user data outside ephemeral test stacks.
- `Fn::ImportValue` chains that prevent recreating a resource without a multi-stack teardown.
- Any single stack synthesizing more than ~400 resources (500 is the hard ceiling).
- Checkov skips with no justification or no prod remediation plan.

### Recommended Pattern
```python
self.cvs_table = dynamodb.Table(
    self, "CVsTable",
    table_name=naming.table_name(constants.CVS_TABLE_NAME),
    partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
    sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
    billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
    encryption=dynamodb.TableEncryption.AWS_MANAGED,     # CUSTOMER_MANAGED for regulated PII
    point_in_time_recovery=True,
    stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,   # enables CDC / safe migration backfill
    removal_policy=RemovalPolicy.RETAIN,
    deletion_protection=True,
)
```

---

## 3. AWS Lambda

**Principle:** Functions are small, single-purpose, fast to cold-start, observable, idempotent, and concurrency-bounded.

### 3.1 Design
- [ ] One responsibility per function; handler is a thin adapter delegating to the **logic** layer. No business rules in handlers.
- [ ] Heavy clients (boto3, DB handlers, model clients) at **module scope** for warm-container reuse.
- [ ] Expensive/long work offloaded to **SQS/Step Functions** (repo's `*_submit` → queue/SFN → `*_worker` split ✅). No synchronous AI generation on an API-path Lambda.
- [ ] Handlers are **stateless**; no reliance on `/tmp` persistence or container-local caches surviving invocations (except as best-effort warm cache).

### 3.2 Performance & Cost
- [ ] Memory right-sized via **Lambda Power Tuning**, not guessed (CPU scales with memory).
- [ ] Realistic timeouts; API-path Lambdas ≤ API Gateway's 29s limit.
- [ ] **ARM64 (Graviton)** for ~20% better price/performance where compatible.
- [ ] Cold starts controlled: minimal deps, **Lambda Layers** for shared/large deps, tree-shaken packages.
- [ ] Provisioned Concurrency / SnapStart only where latency-critical and cost-justified.
- [ ] No VPC unless a private resource requires it (cold-start + NAT cost — repo documents this).

### 3.3 Reliability & Concurrency Control (high-use hardening)
- [ ] **Idempotency** on all at-least-once and money paths via Powertools `@idempotent` + DynamoDB idempotency table (repo references an `idempotency` table — verify it's wired to billing/AI handlers).
- [ ] **Reserved concurrency** on critical functions to guarantee capacity; **maximum concurrency** on functions that call rate-limited dependencies (AI APIs, payment provider, DBs) to prevent overwhelming them under spikes.
- [ ] Every async source has a **DLQ** / `on_failure` destination (repo: `vpr_dlq_handler`, `*_failure_handler` ✅).
- [ ] Transient vs. permanent errors distinguished; retries use backoff (repo's `RetryableError` + SQS visibility-timeout backoff ✅); poison messages reach a DLQ.
- [ ] SQS **partial-batch failure reporting** (`ReportBatchItemFailures`) so one bad record doesn't reprocess the batch.
- [ ] Account-level concurrency headroom monitored; per-function reservations don't starve others.

### 3.4 Observability (Powertools)
- [ ] Shared `logger, metrics, tracer` (`handlers/utils/observability.py`) used everywhere; `@inject_lambda_context`, `@capture_lambda_handler`, `@log_metrics` applied consistently.
- [ ] Correlation IDs propagated across SQS/SFN hops.
- [ ] No `print()`/unstructured logs; no PII/tokens/full bodies logged.
- [ ] Custom business metrics emitted (`VPRGenerated`, `CRConfidenceBelowThreshold`).

### Recommended Pattern
```python
@idempotent(persistence_store=_persistence)
@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event: dict, context: LambdaContext) -> dict:
    request = MyRequest.model_validate(event)   # validate at the boundary
    result = do_work(request)                    # delegate to logic
    metrics.add_metric(name="WorkCompleted", unit=MetricUnit.Count, value=1)
    return result.model_dump()
```
```python
# CDK: bound concurrency against a rate-limited AI provider; guarantee API capacity.
ai_worker = _lambda.Function(self, "AIWorker", architecture=_lambda.Architecture.ARM_64, ...)
ai_worker.add_event_source(SqsEventSource(ai_queue, batch_size=5, report_batch_item_failures=True,
                                          max_concurrency=10))   # don't stampede the model API
api_fn = _lambda.Function(self, "Api", reserved_concurrent_executions=50, ...)  # guaranteed headroom
```

---

## 4. API Gateway

**Principle:** The edge enforces authentication, validation, and throttling before any compute runs.

### Checks
- [ ] **API type fits need:** HTTP API (cheaper/lower latency, JWT authorizers) unless REST-only features (request validators, usage plans/API keys, stage caching, per-method WAF) are required. Document the choice.
- [ ] **AuthN/Z at edge:** Cognito/Lambda authorizer (repo: `api_gateway_authorizer.py`, `cognito_construct`) on every route except explicitly public ones (`/health` — documented).
- [ ] No mutating endpoint is unauthenticated.
- [ ] **Request validation** at the gateway (models/validators) *and* in handlers (Pydantic). Reject oversized/malformed payloads before Lambda runs.
- [ ] **Throttling**: per-stage and per-route rate/burst limits; usage plans for API keys. Protects Lambda concurrency and cost from a single abusive client (high-use hardening).
- [ ] **WAF** on the API/CloudFront in prod (repo: `waf_construct`): AWS managed rule sets, **rate-based rules**, bot control, geo/IP rules as needed.
- [ ] **CORS** locked to known origins (repo: `cors_utils.py`); no `*` with credentials.
- [ ] Response **caching** for read-heavy idempotent GETs in prod (cost/latency trade-off documented).
- [ ] Access + execution logging to CloudWatch; X-Ray on the stage.
- [ ] Custom domain (`*.careervp.com` ACM) + stage variables for env routing — no hard-coded invoke URLs in the frontend.

### Red Flags
- `authorization_type=NONE` on a mutating route → **CRITICAL**.
- Wildcard CORS with credentials.
- No throttling → one client exhausts concurrency/cost.
- Validation only in Lambda (wastes invocations on garbage).

---

## 5. DynamoDB — Architecture Deep Dive

**Principle:** Model the access patterns first; the schema is *derived* from queries. A well-modeled DynamoDB table scales to any load with constant latency; a poorly-modeled one is the most common fragility point in a serverless system.

### 5.1 Access-Pattern-Driven Design
- [ ] **Enumerate every access pattern before modeling** (entity, operation, key, filter, expected cardinality, RPS). Maintain this list in `docs/` and treat it as the contract the schema satisfies.
- [ ] Each read maps to a `GetItem` or `Query` on a key/GSI. **No `Scan` on any request path** (Scans are O(table) and the #1 cause of throttling/cost blowups under load).
- [ ] **Generic key names** (`PK`/`SK`, `GSI1PK`/`GSI1SK`) when using overloaded/single-table design, so new entity types and patterns are additive — no schema migration to add a new query.

### 5.2 Single-Table vs. Multi-Table (the core architectural decision)
- **Single-table design** stores multiple entity types in one table with overloaded, generic keys and composite sort keys, enabling:
  - Fetching related entities (e.g., a user + their applications + CVs) in **one `Query`** instead of N round-trips → lower latency, fewer Lambda-ms, lower cost.
  - Adding new entities/patterns **additively** (new key prefixes, new GSIs) without new infrastructure.
  - Atomic, single-partition transactions across related items.
- **Multi-table** (CareerVP today: `cvs`, `applications`, `users`, `jobs`, `subscriptions`, …) is acceptable when entities are **independently accessed, bounded, and rarely joined**. It is simpler to reason about and to secure per-table, but it costs extra round-trips and makes cross-entity consistency harder.

**Checks**
- [ ] If the app frequently reads several entities together per request (e.g., render an application = job + company research + CV + cover letter + status), **prefer single-table** or a denormalized item collection to collapse fan-out reads into one `Query`. Flag fan-out read clusters in the DAL as **MEDIUM** (latency/cost) — recommend item-collection modeling under a shared `PK` (e.g., `PK=USER#<email>`, `SK=APP#<id>#CV`, `SK=APP#<id>#COVER`).
- [ ] If entities are genuinely independent (auth/session vs. analytics), multi-table is fine — do **not** force single-table dogmatically.
- [ ] **Item collections** (same `PK`, ranged `SK`) used to model one-to-many and enable "get parent + all children" in one query.
- [ ] **GSI overloading** (one or two well-designed GSIs serving many patterns) over one-GSI-per-attribute. Projection minimized (`KEYS_ONLY`/`INCLUDE` over `ALL`).
- [ ] **Sparse GSIs** for filtered queries (e.g., index only `status=PENDING` items) — efficient "find all in state X" without scanning.

> **CareerVP recommendation:** Keep `users`/`sessions`/`idempotency` as focused tables. For the *application artifact graph* (job → company research → VPR → CV → cover letter → interview prep → status), model an **item collection under a single `core` table** keyed `PK=USER#<email>`, `SK=APP#<app_id>#<ARTIFACT>`. This makes "load everything for an application" a single `Query`, makes adding a new artifact type additive, and gives you atomic status transitions via `TransactWriteItems`. Migrate to it via the expand-contract path in §18 — never in place.

### 5.3 Resilience Under Load (anti-fragile data layer)
- [ ] **`PAY_PER_REQUEST`** for spiky/unpredictable load (repo default ✅) — scales to traffic automatically, no capacity planning, no throttling from under-provisioning. Switch to provisioned + autoscaling only with a proven steady baseline that's cheaper.
- [ ] **Hot-partition avoidance:** high-cardinality `PK`. Flag low-cardinality partition keys (status flags, dates, tenant-less constants) as **HIGH** — they serialize all traffic onto one partition and throttle under load. Use **write sharding** (`PK=METRIC#<n>` with `n` in a suffix range) for unavoidable high-write single logical keys.
- [ ] **Adaptive capacity** understood — it helps, but does not save a fundamentally skewed key design.
- [ ] **Conditional writes** (`ConditionExpression`) on all read-modify-write paths (quotas, trial-application counts, subscription state) to prevent lost updates under concurrency → **HIGH** if absent on money/quota paths.
- [ ] **Transactions** (`TransactWriteItems`) for multi-item invariants (create application + decrement quota atomically). Used sparingly (2× cost, 100-item limit).
- [ ] **Optimistic locking** (version attribute) where transactions are overkill but concurrency exists.
- [ ] **Pagination** always handled (`Limit` + `LastEvaluatedKey`); no unbounded result assembly in memory.
- [ ] Large blobs (CVs, generated artifacts) in **S3** with a pointer in DynamoDB — never inline (400 KB item limit; cost).

### 5.4 Durability, Recovery & Evolution
- [ ] **PITR** enabled in prod (repo notes dev omission) — 35-day continuous backup; recover to any second.
- [ ] **On-demand backups** before any risky migration/deploy (§18).
- [ ] **Encryption at rest** (AWS-managed min; CMK for regulated PII).
- [ ] **TTL** on ephemeral items (sessions, idempotency, transient jobs) — auto-expire, control cost and table size.
- [ ] **DynamoDB Streams** (`NEW_AND_OLD_IMAGES`) for event-driven side effects and **migration backfill/dual-write verification** — not application-level dual-writes. Stream consumers idempotent.
- [ ] **Global Tables** only if multi-region active-active is a real requirement (adds eventual-consistency and cost) — otherwise out of scope for V1.

### Red Flags
- `Scan` in a repository method used for normal reads → **HIGH**.
- Low-cardinality partition key on a high-traffic table → **HIGH** (hot partition).
- A GSI per attribute "just in case."
- Read-modify-write without `ConditionExpression` on billing/quota → **HIGH** (lost updates, revenue leakage).
- Large JSON/base64 blobs as item attributes.
- Cross-table fan-out (3+ `GetItem`s to render one screen) where an item collection would serve one `Query`.

### Recommended Patterns
```python
# Single-table item collection: load an entire application graph in ONE query.
resp = table.query(
    KeyConditionExpression=Key("PK").eq(f"USER#{email}") & Key("SK").begins_with(f"APP#{app_id}#"),
)
# Atomic: create application AND decrement trial quota, or neither.
table.meta.client.transact_write_items(TransactItems=[
    {"Put": {"TableName": T, "Item": app_item,
             "ConditionExpression": "attribute_not_exists(PK)"}},
    {"Update": {"TableName": T, "Key": {"PK": f"USER#{email}", "SK": "PROFILE"},
                "UpdateExpression": "SET apps_remaining = apps_remaining - :one",
                "ConditionExpression": "apps_remaining > :zero",
                "ExpressionAttributeValues": {":one": 1, ":zero": 0}}},
])
```
```python
# Write-sharded hot key (e.g., a global daily counter) to spread load across partitions.
shard = random.randint(0, 9)
table.update_item(Key={"PK": f"COUNTER#{day}#{shard}", "SK": "AGG"},
                  UpdateExpression="ADD n :one", ExpressionAttributeValues={":one": 1})
# Read = sum across the 10 shards.
```
**Anti-pattern**
```python
table.scan(FilterExpression=Attr("status").eq("PENDING"))  # BAD: full-table scan; use a sparse GSI
```

---

## 6. S3

**Principle:** Buckets are private by default, encrypted, TLS-enforced, versioned for important data, and lifecycle-managed.

### Checks
- [ ] **Block Public Access** ON at bucket + account level. Public assets only via CloudFront **OAC**, never a public bucket.
- [ ] **Encryption at rest** (SSE-S3 min; SSE-KMS/CMK for user CVs & artifacts).
- [ ] **TLS enforced** via bucket policy (`aws:SecureTransport=false` → deny).
- [ ] **Versioning** on user-data/important buckets in prod (repo notes dev omission) — recover from overwrite/delete.
- [ ] **Lifecycle rules**: expire/transition intermediate artifacts, old versions, incomplete multipart uploads.
- [ ] **Presigned URLs** for client upload/download — short TTL, scoped to a single key; clients never get bucket-wide creds. Verify `cv_upload_handler`/`export_handler`.
- [ ] **Object Lock** considered for compliance/immutable artifacts.
- [ ] Server access logging / CloudTrail data events in prod for audit (repo notes dev omission).
- [ ] CORS scoped to the app origin.
- [ ] **Key design prevents cross-tenant access** (`{user_hash}/{artifact_id}`); never trust a client-supplied key verbatim (path traversal / IDOR).

### Red Flags
- Public bucket holding user data → **CRITICAL**.
- Long-lived presigns or presigns granting `s3:*`.
- Handler uses client-supplied object key directly.

---

## 7. IAM & Least Privilege

**Principle:** Minimum actions on minimum resources. Wildcards are findings until proven necessary.

### Checks
- [ ] **One execution role per Lambda**; CDK `grant_*` helpers so policy tracks real usage.
- [ ] Actions scoped (`dynamodb:Query`, not `dynamodb:*`); **resources scoped to ARNs** (this table + its indexes, this bucket/prefix — not `*`).
- [ ] No `iam:*`/`*:*`/`Resource:"*"` except where AWS requires it (`kms:GenerateDataKey` for SSE — documented; X-Ray `PutTraceSegments`).
- [ ] Cross-service trust least-privilege (SFN→Lambda, SQS→Lambda) with condition keys (`aws:SourceArn`/`aws:SourceAccount`).
- [ ] No long-lived IAM users/keys; **OIDC roles** for GitHub Actions.
- [ ] Permission boundaries / SCPs for prod guardrails.
- [ ] Resource policies (S3, SQS, KMS) never `Principal:"*"` without a condition.

### Red Flags
- `actions=["*"], resources=["*"]` → **CRITICAL**.
- Hand-written policies broader than the `grant_*` equivalent.
- One role shared across unrelated functions (blast-radius amplifier).

### Recommended Pattern
```python
core_table.grant_read_write_data(app_handler)      # scoped to the table ARN + indexes
artifacts_bucket.grant_put(cv_upload_fn)            # not grant_read_write
cr_queue.grant_send_messages(cr_submit_fn)
cr_queue.grant_consume_messages(cr_worker_fn)
```

---

## 8. Authentication & Authorization (Cognito)

**Principle:** Identity verified at the edge; authorization enforced per-resource against the authenticated subject.

### Checks
- [ ] User Pool: strong password policy, MFA available (required for admin), email verification, account-takeover protection (advanced security).
- [ ] Tokens validated at the edge (`api_gateway_authorizer.py`); handlers derive identity **only** from validated JWT claims (`sub`/email), never from a client-supplied `user_id`.
- [ ] **Tenant isolation:** every data access scoped to the caller's identity. DAL filters by the authenticated subject — **no IDOR** (passing another user's `application_id` must not return their data) → **CRITICAL** if violable.
- [ ] Token expiry/refresh handled; refresh-token rotation; revocation possible.
- [ ] Only **public** client IDs in the frontend; app-client secrets/OAuth config in SSM/Secrets Manager.
- [ ] Authorizer caching tuned (TTL) to cut Lambda-authorizer cost without stale-auth windows.

### Red Flags — **CRITICAL**
- Handler trusts `body["user_id"]` instead of the JWT claim.
- Any object fetched by client-supplied ID without an ownership check.

---

## 9. Security & Hardening (Cross-Cutting)

**Principle:** Defense in depth — validate, encrypt, isolate, log, assume breach.

### Checks
- [ ] **Secrets:** none in code/env-baked/images/git. SSM SecureString / Secrets Manager with rotation. Verify AI-model and payment keys never land in Lambda env or logs.
- [ ] **Input validation everywhere:** Pydantic at every boundary (repo ✅); forbid extra fields, enforce types/limits, sanitize persisted/rendered data.
- [ ] **Injection defense:** prompt-injection (delimit user content from instructions in AI calls), parameterized DynamoDB expressions, XSS encoding in generated HTML/markdown artifacts.
- [ ] **Encryption in transit** (TLS on API, S3, internal calls) and **at rest** (DynamoDB, S3, SQS SSE ✅, CloudWatch Logs KMS for sensitive logs).
- [ ] **Dependency hygiene:** lockfiles committed (`uv.lock`, `package-lock.json` ✅); automated CVE scanning (Dependabot/`pip-audit`/`npm audit`) in CI.
- [ ] **SAST/IaC/secret scanning** in CI: Checkov ✅ + gitleaks + code SAST.
- [ ] **Least-exposure logging:** never log PII, tokens, full CVs, payment data; redact at the logger.
- [ ] **Abuse protection (high-use):** WAF rate-based rules + API throttling + per-user quotas enforced **server-side** (the 14-day/3-app trial — never client-side).
- [ ] **CloudTrail** on; **GuardDuty** considered for prod.
- [ ] **Data retention & erasure:** user-deletion purges DynamoDB items + S3 objects (GDPR; EN/HE EU-relevant users).

### Red Flags
- API/payment secrets in Lambda env or committed files → **CRITICAL**.
- User text concatenated into AI prompts with system instructions → prompt injection (**HIGH**).
- Quota/trial enforced only in the frontend → bypassable (**HIGH**).

---

## 10. Event-Driven & Orchestration (SQS, Step Functions, EventBridge)

**Principle:** Decouple producers from consumers; make every step retryable and idempotent; orchestrate long workflows explicitly. This is the backbone of load resilience.

### Checks
- [ ] Long/expensive work (VPR, company research, AI calls) is **async** behind SQS/SFN (repo ✅). No expensive AI call blocks an API Lambda.
- [ ] **Queues absorb spikes** (buffering) — producers never call consumers synchronously under load.
- [ ] Every queue has a **DLQ** + `maxReceiveCount` + depth alarm + drain/replay handler (repo: `vpr_dlq_handler`, `*_failure_handler` ✅).
- [ ] Consumers **idempotent** (dedupe by business key) — SQS is at-least-once.
- [ ] **Visibility timeout ≥ max processing time** (× retries) — avoids premature redelivery.
- [ ] **`max_concurrency`** on event sources calling rate-limited deps (AI/payment) — backpressure, not stampede.
- [ ] FIFO only where strict ordering/exactly-once needed (throughput/cost trade-off).
- [ ] Step Functions for multi-step sagas (artifact chain): explicit `Retry`/`Catch` per state, compensation on failure, **task-token timeouts** (repo's `task_token` ✅) so a lost worker doesn't hang the execution.
- [ ] EventBridge for fan-out/scheduling (billing reconciliation, artifact cleanup) over cron-in-Lambda.
- [ ] Small payloads; large data by S3/DynamoDB reference.

### Red Flags
- Async Lambda with no DLQ → silent data loss.
- SFN `Task` with no `Retry`/`Catch`; task tokens with no timeout.
- Synchronous chain of Lambdas calling Lambdas (fragile; no buffering).

---

## 11. Amplify & Frontend (Next.js)

**Principle:** Ship only public config; build reproducibly; hold no privileged credentials.

### Checks
- [ ] Reproducible build: `npm ci` ✅, typecheck before build ✅, cache scoped ✅; pipeline fails on typecheck/test/lint (no `|| true`).
- [ ] **Branch-per-environment** (dev/staging/prod); no prod secrets in preview branches.
- [ ] **Only public values** in `NEXT_PUBLIC_*`: Cognito public client ID, API base URL, region. No secret/payment/admin keys → **CRITICAL** if present.
- [ ] Runtime secrets fetched server-side (server components/route handlers), never in the client bundle.
- [ ] Amplify Compute (SSR) IAM role least-privilege.
- [ ] Security headers (CSP, HSTS, X-Content-Type-Options, frame-ancestors) via Amplify/Next config.
- [ ] CloudFront + WAF in prod; cache policy correct for SSR vs. static.
- [ ] No browser-side AWS SDK calls with broad creds — all data via the authenticated API.
- [ ] Frontend never the sole enforcer of auth/quotas — backend re-checks everything.

---

## 12. Observability & Operations

**Principle:** Answer "healthy? why failed? what cost?" from telemetry alone.

### Checks
- [ ] **Three pillars** via Powertools, consistent across handlers (repo ✅).
- [ ] **Log retention** set on every log group (30–90d) — unset = unbounded cost.
- [ ] **Alarms** on: Lambda errors/throttles/duration p99, DLQ depth, API 4xx/5xx, **DynamoDB throttles & per-partition heat**, SFN failures, concurrency near account limit (repo `monitoring.py` — verify coverage).
- [ ] **Dashboards** per service; correlation IDs link API → queue → worker.
- [ ] **Synthetic canaries** on critical endpoints (`health_handler`).
- [ ] Alarms route to **on-call (SNS/pager)**, not just console.
- [ ] **Cost monitoring:** budgets + anomaly detection; per-feature tags; **AI spend tracked** (Sonnet vs. Haiku usage as a metric) for the 91% margin.
- [ ] **SLOs defined** (latency/availability) with error budgets — turns "is it OK?" into a measurable yes/no.

### Red Flags
- Log groups with no retention.
- Errors swallowed (`except: pass`) without metric/log.
- Alarms pointing nowhere.

---

## 13. Cost Optimization (Serverless-Specific)

- [ ] No idle provisioned capacity without measured justification.
- [ ] Lambda memory right-sized (top silent cost); ARM64 where possible.
- [ ] Log/S3/DynamoDB lifecycle + TTL purge transient data.
- [ ] **AI model routing enforced & measured:** Sonnet (strategic: VPR, gap analysis) vs. Haiku (templated: CV tailoring, cover letter, interview prep). Bounded prompt sizes; cache/reuse repeated outputs.
- [ ] HTTP API over REST where features allow; DynamoDB on-demand for spiky traffic ✅.
- [ ] Tags on all resources for allocation.

### Red Flags
- Strategic-tier model on templated tasks (margin erosion).
- Unbounded prompt/context; no caching of repeated AI outputs.
- Untagged resources.

---

## 14. CI/CD & Deployment Safety

- [ ] Pipeline gates merge: `ruff` format/lint, `mypy --strict`, unit+integration tests, `cdk synth`, `cdk diff`, Checkov, secret scan (repo `.pre-commit-config.yaml`, `.github/`, mandated commands ✅).
- [ ] GitHub Actions → AWS via **OIDC role**, not long-lived keys.
- [ ] Promotion dev → staging → prod via pipeline, not laptop `cdk deploy`.
- [ ] **Rollback strategy:** Lambda **aliases + versions**, CloudFormation auto-rollback, **canary/linear traffic shifting** (CodeDeploy) on critical functions.
- [ ] No masking (`|| true`); no skipped mandatory checks.
- [ ] Naming guard (`validate_naming.py`) in CI ✅.

---

## 15. Reliability & Resilience

- [ ] Idempotency on all retryable/money paths (§3.3, §5.3, §10).
- [ ] Timeouts + retries + exponential backoff + **jitter** on every outbound call (AI, payment, research sources).
- [ ] **Circuit breaker / graceful degradation** when a provider is down (queue+retry, partial results, "in progress" state) — repo's confidence-gate + retry is a good base.
- [ ] DLQs + replay for all async paths.
- [ ] **Concurrency limits** protect downstream and cap blast radius/cost.
- [ ] PITR + S3 versioning enable recovery (prod).
- [ ] Health checks distinguish "my service up" vs. "dependencies up."
- [ ] **Load/chaos tested**: known behavior at 10× expected RPS; failure injection (drop a dependency) verifies graceful degradation.

### Red Flags
- Unbounded concurrency hammering a rate-limited dependency.
- No backoff/jitter (thundering herd on recovery).
- One Lambda doing retrieve + AI-generate + persist with no checkpoint (a failure reruns the expensive AI call).

---

## 16. Redesign Triage — Output Format

1. **Executive summary** — system shape, top 5 risks by severity, Well-Architected posture, fragility hotspots.
2. **Findings table** — `Severity | Domain | Location | Issue | Recommendation | Migration path (§18) | Effort`.
3. **Quick wins** — low-effort/high-leverage (log retention, tags, scoped IAM, throttling, alarms).
4. **Structural redesigns** — HIGH/CRITICAL rearchitecture (tenant isolation, async offload, **DynamoDB item-collection model**).
5. **Cost & margin impact** — AI routing, memory, idle capacity.
6. **Sequenced plan** — ordered by risk-reduction-per-effort, dependencies noted, **each step mapped to a safe-migration technique (§18)**.

### Prioritization Heuristic
```
Priority = (Severity weight × Likelihood) / Effort
Severity weight: CRITICAL=16, HIGH=8, MEDIUM=4, LOW=2, INFO=1
```
Fix CRITICAL security/auth/data-loss first regardless of effort.

---

## 17. Master Pre-Flight Checklist (Condensed)

- [ ] All infra in CDK; stateful resources isolated + `RETAIN` + protected; cross-stack refs recreatable.
- [ ] Lambdas: single-purpose, validated input, module-scope clients, Powertools, right-sized, ARM64, concurrency-bounded.
- [ ] Idempotency on all at-least-once / money paths.
- [ ] Every async source: DLQ + alarm + replay + backpressure.
- [ ] API: edge authn, no unauthenticated mutations, throttling, validation, WAF (prod), scoped CORS.
- [ ] DynamoDB: access-pattern-driven, no hot-path Scans, high-cardinality keys, item collections for fan-out, conditional writes/transactions on money paths, PITR (prod), TTL, encryption, streams for safe migration.
- [ ] S3: block public, encrypted, TLS-enforced, scoped/short presigns, versioned (prod), lifecycle, tenant-safe keys.
- [ ] IAM: one role/function, scoped actions + ARNs, zero unexplained wildcards, OIDC for CI.
- [ ] Cognito: identity from validated JWT, tenant isolation, no IDOR.
- [ ] Secrets in SSM/Secrets Manager; none in code/env/frontend/logs.
- [ ] Frontend ships only public config; backend re-enforces auth/quotas.
- [ ] Observability: logs+metrics+traces, retention set, alarms→on-call, SLOs.
- [ ] CI/CD: full gating, OIDC, canary/alias rollback, no masking.
- [ ] Cost: ARM64, right-sized memory, AI routing enforced & measured, tags.
- [ ] Resilience: timeouts+backoff+jitter, circuit breakers, load/chaos tested.

---

## 18. Running the Redesign Without Impacting Live Code & Infrastructure

> The goal: evolve the system continuously with **zero downtime, zero data loss, and instant rollback**. The governing rule is **additive-first / expand-contract**: never mutate or delete a live resource in place — add the new alongside the old, shift traffic gradually, verify, then retire the old. Every step below is independently reversible.

### 18.0 Golden Rules
- [ ] **Never edit a live stateful resource destructively.** No renaming/removing a DynamoDB table, GSI, or bucket that holds data in a single deploy (CloudFormation replaces → data loss). Add new, migrate, retire.
- [ ] **Decouple deploy from release.** Ship code dark behind **feature flags**; release by flipping a flag, not by deploying.
- [ ] **One reversible change at a time.** Each step has a defined success metric and a rollback that needs no data surgery.
- [ ] **Back up before every risky step.** On-demand DynamoDB backup + confirm PITR; S3 versioning on.
- [ ] **Test the migration itself**, not just the new code — in a prod-like staging environment with prod-shaped data volume.

### 18.1 Environment & Stack Isolation — Same Account, Nested Stacks
**This project runs all environments in a single AWS account**, isolated by the `{env}` naming suffix (`NamingUtils` → `careervp-{feature}-{type}-{env}`). Isolation is therefore enforced by **naming + IAM scoping + separate stacks**, not by account boundaries — so naming discipline and least-privilege roles (§7) carry more weight here, and every resource ARN in an IAM policy must be env-scoped so `dev` principals can never touch `prod` resources.

- [ ] **One account, env-suffixed stacks.** Every stack/resource name carries the `{env}` suffix; no shared physical names across environments. Prove the redesign in `dev` → `staging` before `prod`, all in the same account.
- [ ] **IAM enforces the env boundary** the account does not: each function's role is scoped to ARNs matching its own `{env}` (e.g., `careervp-*-dev`), so a dev mistake cannot read/write prod data. Flag any cross-env-capable role as **HIGH**.
- [ ] **Decompose with nested stacks (per §2.1)** — mandatory given the 500-resource limit. The redesign adds **new nested stacks alongside the existing ones** under the same parent; the old nested stacks keep serving live traffic until cutover, then are retired. A nested stack is the natural unit of strangler-fig replacement here.
- [ ] **Ephemeral preview stacks** per branch/PR (`careervp-*-pr123-<env>`) in the same account for isolated end-to-end testing with no shared state; tear down after merge.
- [ ] **Share resources via constructor props, not `Fn::ImportValue`.** Pass top-level stateful refs (core table, buckets, user pool) into new nested stacks so the new path attaches without disturbing the old and stays independently updatable/removable.
- [ ] **Same-account cost & blast-radius hygiene:** because environments share the account, rely on **tags** (`Environment`, `Feature`) for cost attribution and **per-env CloudWatch alarms/budgets**; a runaway dev migration must not consume prod's concurrency/throughput headroom — set env-scoped reserved concurrency and on-demand limits.

> **Same-account caution:** without an account boundary, the strongest guardrails are (1) env-suffixed naming, (2) IAM resource ARNs scoped per env, (3) separate stacks/nested stacks per env+feature, and (4) `deletion_protection`/`RETAIN` on stateful resources so a misfired `cdk destroy --all` can't wipe prod data. Verify all four before running migration work in the shared account.

### 18.2 Strangler Fig — Incremental Replacement
The safest pattern for redesigning a running system: route a slice of functionality to the new implementation while the rest stays on the old, then expand the slice until the old is unused.
- [ ] Put a **routing seam** in front of the component (API Gateway route, a dispatcher in the logic layer, or a feature flag) that can send a request to old or new code.
- [ ] Migrate **one handler / one access pattern at a time**; keep the contract identical.
- [ ] Expand coverage as confidence grows; **delete the old path only after it has served zero traffic for a full retention window**.

### 18.3 Lambda / Compute Cutover (zero-downtime)
- [ ] Deploy new function **versions**; shift traffic with an **alias + CodeDeploy canary/linear** (e.g., 10% for 10 min → 100%) with **automatic rollback on alarm** (errors/p99 latency).
- [ ] For behavioral changes, gate with a **feature flag** (Powertools feature flags / AppConfig) so release is a flag flip, instantly reversible.
- [ ] **Shadow / mirror traffic**: invoke the new implementation in parallel (async, results discarded or compared) to validate correctness under real load before it serves users.
- [ ] Keep request/response **contracts backward-compatible**; version the API (`/v2`) if breaking, run both, deprecate the old after clients migrate.

### 18.4 DynamoDB Migration — Expand / Migrate / Contract (the hardest, most important)
Restructuring data (e.g., multi-table → single-table item collections per §5.2) must be done without downtime or data loss:

1. **Expand (additive, no behavior change).**
   - [ ] Create the **new table / new GSI / new attributes** in a *separate* deploy. Adding a GSI or a table is non-destructive; the live table keeps serving.
   - [ ] Enable **DynamoDB Streams** on source tables for change capture.
2. **Dual-write.**
   - [ ] Application writes to **both** old and new models (behind a flag). New reads still come from the old model. Verify writes land correctly in the new shape.
3. **Backfill.**
   - [ ] Copy historical data into the new model with a **throttled, idempotent batch job** (Step Functions + paginated `Scan`/export, or **S3 export → Glue/EMR** for large tables to avoid impacting live capacity). Run against on-demand capacity or a copy.
   - [ ] Reconcile: stream-driven verification that old and new agree; emit a drift metric.
4. **Dual-read / shift reads.**
   - [ ] Flip reads to the new model behind a flag, **canary by percentage or user cohort**. Compare results (shadow read) before full cutover.
5. **Contract (retire old).**
   - [ ] After new model serves 100% with zero drift for a full validation window, **stop dual-writing**, then **retire the old table/GSI in a later, separate deploy** (never the same deploy that removes the read path).
   - [ ] Keep the final on-demand backup of the old table per retention policy before deletion.
- [ ] **GSI changes:** add the new GSI, let it backfill (it builds online without downtime), shift queries, then remove the old GSI in a separate deploy. Never rename a GSI in place.
- [ ] **Key-schema changes are impossible in place** — they always require a new table + migration as above. Flag any PR attempting to change PK/SK on a live table as **CRITICAL — will cause replacement/data loss**.

### 18.5 API / Contract Evolution
- [ ] **Additive schema changes** (new optional fields) over breaking ones; consumers tolerate unknown fields.
- [ ] Breaking changes → **new versioned route** (`/v2`), both served in parallel, old deprecated with metrics on its usage before removal.
- [ ] Request validators updated additively; never tighten validation on a live route without confirming no client sends the now-rejected shape (check logs first).

### 18.6 Safety Net & Verification
- [ ] **Pre-cutover:** on-demand backups, confirmed PITR, S3 versioning, a written rollback runbook with the exact flag/alias to revert.
- [ ] **During:** canary alarms (error rate, p99, DLQ depth, DynamoDB throttles) wired to **auto-rollback**; correlation IDs to trace the new path; shadow-comparison metrics.
- [ ] **Post-cutover:** bake time (hours–days) at 100% before retiring old resources; cost/latency dashboards confirm no regression.
- [ ] **Rollback test:** the rollback path is *exercised in staging*, not assumed.
- [ ] **Blast-radius limit:** migrate per-cohort (internal users → small % → all) so a defect touches few users.

### 18.7 Sequenced Redesign Plan (template for the report)
```
Phase 0  Baseline & guardrails: backups, PITR, alarms→on-call, feature-flag + alias/canary infra,
         staging with prod-shaped data, cdk diff in CI, and per-stack resource-count check
         (<400). Carve the existing monolith into nested stacks (§2.1) FIRST so there is
         headroom to add the redesign's resources without breaching the 500-resource limit.
         (No user-facing change — pure refactor of stack composition.)
Phase 1  CRITICAL security/auth fixes via additive deploys + canary (tenant isolation, scoped IAM,
         server-side quotas, secrets to SSM). Reversible by flag/alias.
Phase 2  Reliability hardening: DLQs, idempotency, concurrency bounds, retries+jitter — all additive.
Phase 3  DynamoDB re-architecture via Expand→Dual-write→Backfill→Dual-read→Contract (§18.4),
         per-cohort canary, zero downtime.
Phase 4  API/compute modernization behind versioned routes + canary; retire old after bake.
Phase 5  Cost & observability tuning (memory, ARM64, AI routing, SLOs, dashboards).
Each phase: independently shippable, independently reversible, gated by metrics before the next.
```

### Red Flags in a Redesign PR — **block these**
- A single deploy that **renames/removes a live table, GSI, or bucket**, or changes a PK/SK → replacement & data loss (**CRITICAL**).
- Read path switched to a new data model **before** backfill + reconciliation complete.
- A "big bang" cutover with no canary, no flag, no rollback path.
- `removal_policy=DESTROY` introduced on a stateful resource "to make the deploy clean."
- Migration batch job running unthrottled against the live table's capacity.
- New feature resources added to an **already near-full stack** (>400 resources) instead of a new nested stack → risks breaching the 500-resource hard limit and failing the deploy (**HIGH**).
- An IAM role/policy in the shared account scoped to ARNs that span environments (e.g., no `{env}` suffix) → a dev change can touch prod data (**HIGH**).

---

*End of guide. Use it as a rubric, not a wish-list: every assertion resolves to PASS / FAIL / N/A with cited evidence, a concrete idiomatic remediation, and a safe migration path. Build for change and pressure — additive, reversible, observable, least-privileged.*
