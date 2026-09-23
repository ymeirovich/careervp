<!--
  CareerVP — Architecture Deep-Dive (verbose, per-domain).
  Companion to careervp-architecture-v2.md (as-built record) and redesign-runbook.md (migration).
  Reconciled against `main` @ HEAD 4f7c294 (2026-06-29). Evidence cited path:line.
-->

# CareerVP — Architecture Deep-Dive

**Companion to:** [`careervp-architecture-v2.md`](./careervp-architecture-v2.md) (the as-built record + diagrams) and [`redesign-runbook.md`](./redesign-runbook.md) (the executable migration).
**Purpose:** verbose, domain-by-domain architectural analysis — current state, risks, and recommendations — plus a **parallel-environment** delivery strategy and a **greenfield ("if rebuilt") target**.
**Convention:** evidence cited `path:line` against `main` @ `4f7c294`.

**Contents**
1. Security architecture
2. Database architecture
3. Serverless compute architecture
4. Frontend architecture (incl. the repeated-API-call problem)
5. API architecture
6. Async request/response cycle — SQS & Step Functions
7. LLM architecture
8. CloudFormation / stack redesign
9. Artifact processing — the auto-generation chain & reload status model
10. Parallel-environment redesign strategy
11. If we rebuilt CareerVP from scratch

---

## 1. Security architecture

### 1.1 Current posture
Authentication is real and edge-enforced (Cognito User Pool authorizer on every mutating route, `api_construct.py:446`; public allowlist limited to `/health`, `/auth/*`, `/billing/webhook`, `/errors`, `/swagger*`). Secrets are handled correctly — every provider key (Anthropic, Tavily, JWT signing, Stripe) lives in SSM SecureString and is resolved at runtime with `WithDecryption=True`; nothing sensitive is baked into a Lambda env var, the CloudFormation template, the git tree, or the frontend bundle (`NEXT_PUBLIC_*` carries only the API URL, Cognito public client id, region). CI runs Checkov, Bandit, pip-audit and CodeQL. That is a solid floor.

The problem is **everything between the edge and the data**: identity can be spoofed, the blast radius of any one compromised function is the entire data layer, and the data itself can be destroyed by a routine deploy.

### 1.2 Attack surface & data-compromise paths (ranked)

**A. Identity spoofing — CRITICAL.** `extract_user_id()` prefers validated JWT claims but **falls back to a client-supplied `x-user-id` / `X-User-Id` header** when claims are absent (`auth_utils.py:44-47`). Any request that reaches a handler on a path where the authorizer context is missing — a misconfigured route, a future internal invoke, a header-forwarding bug — can assert an arbitrary user identity. This is the single most dangerous line in the backend: it turns every "scoped to the caller" guarantee into "scoped to whatever the caller claims." **Remove the fallback entirely; identity must derive only from the validated token.**

**B. IDOR via id-only reads — HIGH.** `jobs_repository.get_job(job_id)` fetches by primary key with **no `user_id` constraint** (`jobs_repository.py:196-223`). It is safe today only because every caller remembers to check ownership *after* the fetch (`application_handler.py:163`, `vpr_status_handler.py:555`, etc.). One forgotten check anywhere = cross-tenant data disclosure. The fix is structural: **enforce the tenant partition key in the DAL** so an un-owned id cannot be read in the first place. The single-table `core` model (`PK=USER#{user_id}`) makes this automatic — you physically cannot Query another tenant's partition.

**C. Mutable-PII partition key — HIGH.** The `knowledge` table is keyed `PK=userEmail` (`api_db_construct.py:344`). Email is mutable and is PII; using it as a partition key means (a) a tenant's data is keyed on something that can change, and (b) the key value is sensitive. The table is effectively dead in the live read path (the company-research probe was forced to drop it in `4483b3e` because querying it threw `ValidationException`), but the schema is still deployed. **Retire it; relocate any knowledge data into `core` under the immutable `USER#{user_id}`.**

**D. Over-broad IAM / wide blast radius — CRITICAL/HIGH.** A **single shared role** (`careervp-role-lambda-core`) is attached to 13+ Lambdas and can `Put/Get/Update/Delete/Query` nearly every table, send/consume the queues, and read/write the buckets (`api_construct.py:70-87,482-819`). It also carries two wildcards: `kms:Decrypt/GenerateDataKey` on `resources=["*"]` (`:778`) and AppConfig actions on `resources=["*"]` (`:516`). Compromise *any* of those 13 functions (e.g. via a dependency CVE or a prompt-injection-driven SSRF) and the attacker inherits read/write to the whole datastore. The worker Lambdas already show the correct pattern — dedicated roles with `grant_*` helpers scoped to specific ARNs. **Split the shared role per function/domain and scope the two wildcards to specific key/application ARNs.**

**E. WAF disabled outside prod — MEDIUM/HIGH.** WAF (4 AWS managed rule groups + intended rate-based rules) is only attached when `is_production_env` (`api_construct.py:240-248`). Non-prod environments — which hold real user data in the same account — have no L7 protection. Combined with the very low API Gateway throttle (`rate=2/s, burst=10`, `:338`) there is no rate-based abuse protection in dev/staging.

**F. Prompt-injection / LLM-as-confused-deputy — MEDIUM.** User CV text and job postings are sent to the model; company research pulls **raw web content via Tavily** and concatenates it into prompts. The model output is then rendered as rich text in the SPA. Two risks: (1) injected instructions in a job posting or scraped page steering generation, and (2) stored-XSS if model output containing markup is rendered without sanitization in the TipTap editor. **Delimit untrusted content from instructions, and sanitize/encode generated HTML/markdown on render.**

**G. Cognito hardening gaps — MEDIUM.** Password policy permits no-symbol, min-length-8; MFA is not enabled; advanced security (account-takeover protection) is deferred (`cognito_construct.py:22-28`). For a product holding career history and payment linkage, enable MFA (at least optionally, required for any admin), tighten the policy, and turn on advanced security in prod.

**H. No idempotency on the money path — CRITICAL (also a reliability issue, §6).** The Powertools idempotency table exists but `@idempotent` is wired to **zero** handlers; a retried Stripe webhook can double-process (`billing_reconcile_handler.py`).

**I. Data destroyed by a deploy — CRITICAL.** Every table/bucket is `RemovalPolicy.DESTROY` with no deletion protection and the CV bucket has `auto_delete_objects=True` (`api_db_construct.py:101-670,165`). A stack replacement or an errant `cdk destroy` deletes user data. This is a confidentiality/availability/integrity problem all at once and is the #1 reason the redesign's Phase 0 exists.

### 1.3 Hardening roadmap
1. **Identity:** delete the `x-user-id` fallback; derive identity only from validated claims; enforce the tenant key in the DAL (kills B).
2. **Least privilege:** one role per Lambda; scope KMS/AppConfig to ARNs; remove the table-wide `Scan` grant on `artifacts`.
3. **Data safety:** `RETAIN` + `deletion_protection`; remove `auto_delete_objects`; CV bucket versioning + CORS locked to app origins.
4. **Money path:** `@idempotent` keyed on Stripe event id; conditional writes on quota/subscription mutations.
5. **Edge:** WAF in all envs (or a documented, time-boxed dev exception); raise throttles to realistic values; per-user server-side quotas.
6. **LLM:** prompt-injection delimiting; output sanitization; the confidence gate already mitigates weak research — keep it.
7. **Cognito:** MFA, stronger password policy, advanced security in prod.
8. **CI:** add gitleaks/trufflehog secret scanning (currently absent).
9. **Erasure:** implement a GDPR delete path that purges DynamoDB items + S3 objects for a user (relevant for EN/HE EU users).

---

## 2. Database architecture

### 2.1 Where it stands vs serverless best practice
The data layer is the project's deepest structural debt, and the team's own dossier (`docs/db-redesign/01-artifact-table-routing-and-vpr-id-model.md`) already diagnoses it. Restated against the best-practice rubric:

- **Access patterns were not modeled first.** The schema accreted: 9 tables in `api_db_construct.py` + `llm-cache`, with **three mutually-incompatible key schemas** (`pk/sk` on users, `applicationId/artifactId` on artifacts, `job_id` on jobs). A read built for one schema throws `ValidationException` against another — and those exceptions are swallowed and converted into a silent business "not found."
- **Storage location is implicit.** Which table a Lambda touches is decided by **env-var precedence** (`ARTIFACTS_TABLE_NAME → DYNAMODB_TABLE_NAME → TABLE_NAME`), not a typed contract, so a reader and its writer can resolve to different physical tables.
- **No canonical identifier.** One application carries three ids — `application_id` (== `job_id`, the real handle), a `*_artifact_id` status label that is **a key on no table**, and a request `vpr_id`. The VPR row has no `vpr_id` attribute at all; it is addressable only by `pk=application_id`. The system exported a non-key id to the client and trusted it back as a lookup key.
- **Fan-out reads.** Rendering one application, or even one page bootstrap, touches multiple tables across multiple Lambdas (§4, §5). PROFILE and SUBSCRIPTION#CURRENT share the `users` partition, but CVs use a *raw* `pk=user_id` rather than `USER#{user_id}` (`user_handler.py:138` vs `user_repository.py:140`) — even within one table the keys are inconsistent.
- **Correctness bugs riding on the above:** TTL never-expires (CV-tailored writes `ttl` to a table whose attribute is `expiration`; cover letters write no TTL field — `cv_tailoring_handler.py:467,517`, `cover_letter_handler.py:653-691`), and the interview-prep orphan `prep_id` row (`interview_prep_handler.py:968-991`).

What's already right: on-demand billing (correct for spiky load), PITR enabled, streams on `artifacts`/`jobs` (good for CDC-based migration), and the `cv_tailored` path demonstrates the correct pattern — it **consumes the gate-resolved VPR** rather than re-fetching by a fragile id.

### 2.2 The target: single-table `core` (already partly specced in-repo)
The target model exists in `docs/best_practices/yaml/dynamodb_modeling_spec.yaml:26-27` but is **not deployed**. Adopt it:

```
core table
  PK = USER#{user_id}                  user_id = Cognito sub (immutable), NEVER email
  SK = APP#{app_id}#PROFILE
       APP#{app_id}#GAP
       APP#{app_id}#CR
       APP#{app_id}#VPR#v{n}           (body pointer → S3 vpr-results)
       APP#{app_id}#CV_TAILORED        (body pointer → S3)
       APP#{app_id}#COVER
       APP#{app_id}#INTERVIEW
       APP#{app_id}#STATUS             (the workflow state machine, atomic)
       PROFILE                         (account-level)
       SUBSCRIPTION#CURRENT
       CV#{cv_id}                      (CV metadata; file → S3)
  GSI1 (status):  GSI1PK=USER#{user_id}   GSI1SK=STATUS#{state}#{app_id}   (sparse, "find all in state X")
```

**What it buys, mapped to the rubric:**
- **One typed home + one stored key per artifact.** A single `artifact_type → (table, key derivation)` map that both reader and writer import; a `CoreRepository` is the only key-builder. This makes the 3-schema / 3-id class *structurally impossible* — the dossier's §9 requirements.
- **One Query loads an application** (`PK=USER#{uid}` + `SK begins_with APP#{app_id}#`) and **one Query loads the whole user bootstrap** (profile + subscription + CVs + application summaries) — directly killing both the fan-out and the chatty bootstrap (§4, §5).
- **Atomic status transitions** via `TransactWriteItems` on a single partition (also enables atomic "create application + decrement trial quota").
- **Tenant isolation by construction** — leading the PK with the immutable `user_id` means a Query cannot cross tenants (kills the IDOR class).
- **Additive evolution** — new artifact types = new `SK` prefixes, no new infrastructure.

**Keep as focused tables** (genuinely independent, bounded, rarely joined): `idempotency`, `jobs` (async job state only), `company-research-cache` (shared cross-user cache), `llm-cache`. Large bodies stay in **S3** with a pointer — never inline (400 KB item limit, cost).

### 2.3 Recommended changes (in order)
1. **Phase 0 guardrails first** — `RETAIN` + deletion protection (a PK/SK change forces table replacement; under `DESTROY` that is data loss).
2. Build `core` + `GSI1`; implement `CoreRepository` + the typed storage contract; converge the `TABLE_NAME`/`DYNAMODB_TABLE_NAME`/`USERS_TABLE_NAME` aliases.
3. Migrate via **expand → dual-write → backfill → dual-read → contract** (runbook Phase 3), per-cohort canary, drift metric from streams.
4. On contract, fix TTL (write the real attribute), drop the orphan `prep_id` row, retire the `userEmail` key, unify the CV PK to `USER#{user_id}`.
5. Make `_is_stale` an explicit tested contract or remove it (it currently compares fields that are never written — a latent regeneration-loop trap).

---

## 3. Serverless compute architecture

### 3.1 Current shape
~31 Lambda functions: thin-ish API handlers + a clean `*_submit → queue → *_worker` split for expensive AI work, plus a Step Functions chain. Powertools (logger/metrics/tracer) is used across most handlers. Memory is deliberately sized per function (128 MB–1024 MB). This is a reasonable serverless decomposition.

### 3.2 Risks
- **One shared IAM role across 13+ functions** (§1.2.D) — the dominant compute risk: no blast-radius isolation.
- **All functions are x86_64** (`Architecture.X86_64`, 32 occurrences; zero ARM64 in infra) — leaving ~20% price/performance on the table on a cost base dominated elsewhere, but free to capture.
- **No concurrency control anywhere** — neither `reserved_concurrent_executions` (to guarantee capacity for the API path) nor SQS `max_concurrency` (to cap the AI workers). Under a spike, the AI workers can scale to the account default (~1000) and **stampede the Anthropic rate limit**; there is no backpressure beyond per-container retry/circuit-breaker.
- **Cold starts** — no provisioned concurrency or SnapStart; no Lambda layers for shared deps; the heaviest functions (CV parser 1024 MB, VPR worker 1024 MB) cold-start with full dependency trees. The chatty bootstrap (§4/§5) multiplies cold starts because three separate Lambdas serve one page load.
- **Idempotency absent** on at-least-once and money paths (§1, §6).
- **`/tmp`/container-local assumptions** — mostly fine; the per-request Cognito `getSession()` in the frontend (not Lambda) is the analogous hot-path cost.

### 3.3 Recommendations
1. **One role per function** with `grant_*`-scoped ARNs; remove wildcards and the `Scan` grant.
2. **ARM64/Graviton** across the board (validate Powertools/boto3 wheels — they support arm64).
3. **`max_concurrency` (3–5) on AI worker event sources**; **reserved concurrency** on the API-path Lambdas to guarantee headroom.
4. **Right-size with Lambda Power Tuning** rather than guessed memory; consider a shared **Lambda layer** for boto3/Powertools/anthropic to shrink cold starts.
5. **Idempotency** (`@idempotent`) on billing + AI-cost handlers.
6. Keep functions out of a VPC (correct today — avoids NAT cost/cold-start); use Gateway VPC endpoints only if private resources are ever added.

---

## 4. Frontend architecture

This is grounded in a direct read of `src/frontend` and explains the "many repeated API calls even post-load" symptom you reported.

### 4.1 Current shape
Next.js 16 **App Router**, React 19, a single axios client (`api/client.ts`) with a token-injecting request interceptor and a 401-refresh-retry response interceptor. TanStack Query v5 is a dependency. **But three data-fetching paradigms coexist and fight each other:** React Query (some hooks), raw `useEffect`+axios (CV hook, every artifact detail page, generation), and a hand-rolled `setInterval` poller (`hooks/useModuleStatus.ts`).

### 4.2 Root causes of the excessive/repeated calls (ranked, with evidence)

1. **The QueryClient is created with zero configuration** — `app/_providers.tsx:7` does `new QueryClient()`. With v5 defaults that means `staleTime: 0` and `refetchOnWindowFocus: true`, so **every navigation, remount, and tab-focus refetches everything**. This one line causes most of the repeated traffic. Only a single prefetch anywhere sets `staleTime` (`dashboard/jobs/[jobId]/page.tsx:76`).
2. **The status poller runs on already-completed artifacts** — `hooks/useModuleStatus.ts:40-70` starts a 3 s `setInterval` whenever `enabled && taskId`, never checking whether the artifact is already terminal. `resolveTaskId` returns an id for both `processing` and `completed` (`useApplicationHub.ts:43-49`), and the hook is instantiated **4× per hub render** (VPR, cover letter, interview prep, tailored CV — `useApplicationHub.ts:146-149`). So every hub revisit fires a burst of status GETs for finished work before discovering it's done. It *does* clear on terminal status and unmount (good), but it shouldn't start. Worse, the effect deps include the recomputed `taskId`, so when the hub refetches `/applications` (freely, no staleTime) the interval tears down and restarts, re-firing immediate polls.
3. **The same resource is fetched under multiple query keys, or outside Query entirely.** Subscription is fetched by `useUserContext` *and* by three billing cards each with their own `useQuery` (`SubscriptionCard.tsx:185`, `UsageCard.tsx:136`, `BillingInfoCard.tsx:92`). CV is fetched by `useApplicationHub` under `['cv','me']` *and* by the non-Query `useCV.ts:19`. `/jobs` is fetched under three different keys (`useJobs` + inline in `methods.ts:204` and `:280`). Different keys ⇒ no shared cache ⇒ duplicate network calls.
4. **Artifact detail pages bypass the cache** — the VPR / interview-prep / cover-letter / cv-tailored pages re-`useEffect`-fetch `/applications/{id}` + `/jobs/{id}` + the artifact body on every open (`vpr/page.tsx:343-380`, `interview-prep/page.tsx:233-253`, etc.), ignoring what `useApplicationHub` already cached.
5. **`useUserContext` is mounted in five places** (ProtectedLayout, dashboard layout, billing page, settings page, PlansSection) with no `staleTime`, so each remount refetches `me` + `usage` + `subscription`.
6. **No code splitting** (`next/dynamic`/`lazy` used nowhere) — the heavy TipTap/turndown/marked editor deps load up front; and a per-request Cognito `getSession()` in the axios interceptor (`client.ts:71`) makes every duplicated call a little more expensive.

Server-side, this lands on endpoints that **set no cache headers at all** (no `Cache-Control`/`ETag`; API GW has no stage cache), and the status endpoints are individually expensive (primary `get_item` + `begins_with` query fallback + dual canonical/legacy reads; VPR status does an S3 `head_object` **and** a DynamoDB write on every completed poll — `vpr_status_handler.py:94-102,140`). So a chatty frontend meets an uncached, multi-read backend — the worst combination.

### 4.3 Recommendations (ordered by leverage)
1. **Configure the QueryClient once** (`_providers.tsx`): `defaultOptions.queries = { staleTime: 60_000, gcTime: 300_000, refetchOnWindowFocus: false, retry: 1 }`; give slow-changing resources (`me`, `subscription`, `usage`, `cv`) a 5-minute `staleTime`. *This alone removes most of the post-load refetching.*
2. **Convert polling to React Query `refetchInterval` with a terminal guard**, and **don't start polling when the hub already reports `completed`/`failed`** — gate `enabled` on non-terminal status, not merely on `taskId`.
3. **One shared query key per resource.** Make `useCV` a `useQuery` on the shared CV key; have billing cards consume `useUserContext` instead of their own subscription/usage queries; fetch `/jobs` once and pass it down. Centralize keys in `queryKeys.ts` and forbid inline string keys.
4. **Artifact detail pages read the cache** — consume `useApplicationHub`/the shared `applications.detail` key instead of re-fetching `/applications` + `/jobs`; only the artifact body is a new keyed query.
5. **Lift bootstrap data to one provider** (the existing `DashboardContext` is the natural home) so layouts/cards never re-issue `me`/`subscription`/`usage`.
6. **Add a `GET /me/bootstrap` aggregate endpoint** (see §5.4) and call it once on load.
7. **Add HTTP caching** server-side: `Cache-Control: private, max-age` on the read endpoints, `ETag` + `304` on profile/subscription/cv, terminal status responses cacheable (`max-age=300`/`immutable`), in-flight `no-store`.
8. **Coalesce token refresh** (`client.ts:84-98`) into a single in-flight promise so concurrent 401s await one refresh.
9. **Code-split** the editor and artifact pages with `next/dynamic`; turn on Next image optimization.
10. **Pick one paradigm** — standardize on React Query for server state; either adopt `zustand` deliberately for client state or drop it; make server state the single source of truth (the `localStorage` artifact-id reconciliation in `artifactStorage.ts` is what lets stale ids restart pollers).

### 4.4 Frontend architecture risks (systemic)
The deepest risk is not any single bug but the **three competing fetching paradigms with inconsistent keys** — it guarantees cache misses, duplicate traffic, and unreliable invalidation, and it will keep regenerating this symptom as features are added. Standardizing the data layer is the structural fix; the QueryClient config is the immediate one.

---

## 5. API architecture

### 5.1 Current shape
A single API Gateway **REST** API (`careervp-core-api`) with a Cognito authorizer, access logging, tracing, and a default-deny route model (explicit public allowlist). Recent work collapsed several routes to `{proxy+}` to claw back resources against the 500-resource stack limit. CORS preflight is permissive but auth is Bearer-header (no cookies), so wildcard CORS is medium-risk, not critical.

### 5.2 Risks
- **No HTTP caching** (§4.2) — no `Cache-Control`/`ETag`, no API GW stage cache. Read endpoints are recomputed every call.
- **Throttle set very low** (`rate=2/s, burst=10`, `api_construct.py:338`) with **no usage plans / API keys**. This is simultaneously a reliability bottleneck (a legitimate burst is throttled) and weak abuse protection (no per-client rate-based control; WAF rate rules are prod-only).
- **Validation only in Lambda** — no request models/validators at the gateway, so malformed/oversized payloads still spend a Lambda invocation.
- **A self-managed JWT path coexists with Cognito** (`auth_service.py`, `api_gateway_authorizer.py` handler exists but is unattached) — two auth systems is a maintenance and correctness risk; document which is authoritative per route and consolidate.
- **No API versioning** — breaking changes have nowhere to live without disrupting the SPA.
- **The chatty read pattern** (§5.4) is an API-design problem as much as a frontend one: there is no aggregate/bootstrap resource, so the client must orchestrate many calls.

### 5.3 Recommendations
- Add `Cache-Control`/`ETag` + `304` on GETs; reconsider HTTP API (cheaper, JWT authorizers) for routes that don't need REST-only features, or keep REST and lean on client/CloudFront caching.
- Raise throttles to realistic values; add usage plans; ensure WAF rate-based rules run in all envs.
- Add gateway request validators for the high-traffic write routes (reject garbage before Lambda).
- Consolidate on one auth path; attach or delete the unused Lambda authorizer.
- Introduce `/v2` versioning discipline for future breaking changes (run both, deprecate on usage→0).

### 5.4 The bootstrap aggregate
Today a page load fires `GET /users/me` + `/users/me/subscription` + `/users/me/cv` as **three separate Lambdas across two tables** (~4–5 reads, 2–3 cold starts), none sharing a cache header. Introduce **`GET /me/bootstrap`** returning `{profile, subscription, cvs, application_summaries}` in one call. Today that's ~2–3 Queries in one Lambda (PROFILE+SUBSCRIPTION share the `users` partition; CVs are a second query due to the raw-`user_id` PK inconsistency; applications a third). Under the single-table `core` model it collapses to **one `Query(PK=USER#{user_id})`** — the bootstrap becomes a single round trip. Pair it with the QueryClient `staleTime` so the SPA fetches it once and reuses it.

---

## 6. Async request/response cycle — SQS & Step Functions

### 6.1 Current shape
Expensive AI work is correctly offloaded: `*_submit` Lambdas enqueue to per-artifact SQS queues consumed by `*_worker` Lambdas; a **STANDARD Step Functions** chain (`artifact_chain_construct.py`) orchestrates CR → VPR → CV → {cover letter, interview prep} using `sqs:sendMessage.waitForTaskToken` with heartbeats, and the workers signal completion via `SendTaskSuccess/Failure`. Every queue has a DLQ with `maxReceiveCount=3`. Failure handlers use a dedicated least-privilege role (no `states:*`). This is a good backbone.

### 6.2 Risks
- **Silent message loss — CRITICAL.** Three of four SQS workers return `statusCode:200` instead of `batchItemFailures`, so a failed message is deleted rather than retried (`vpr_worker_handler.py:619`, `cover_letter_handler.py:487`, `interview_prep_handler.py:151`). Only the CR worker reports partial failures correctly.
- **Duplicate processing / duplicate AI spend — CRITICAL.** SQS **visibility timeout equals the Lambda timeout (1×)** on every AI queue (e.g. VPR 600 s/600 s; cover-letter and interview-prep 300 s/300 s — `api_construct.py:1039/1286`, `1080/1575`, `1111/1647`). If a worker runs near its timeout, SQS re-delivers while it's still processing → a second expensive Sonnet/Haiku call. Best practice is visibility ≥ 6× the processing time.
- **No backpressure to the model provider — HIGH.** No `max_concurrency` on any event source; AI workers can fan out to the account concurrency limit and trip Anthropic 429s under load.
- **Unmonitored async failures — MEDIUM.** Monitoring covers only 7 API Lambdas; the ~24 workers and **DLQ depth** are not alarmed (`service_stack.py:72-80`) — a stuck DLQ is silent.
- **Stale chain lock — MEDIUM.** `chain_execution_status=RUNNING` can be left set (observed in dev); the lock is mutated from several call sites rather than modeled as first-class state, so it can strand and double-generate.
- **Two VPR workers + DLQ handler** add operational surface; ensure idempotency so a redelivery or DLQ-recovery doesn't double-write.

### 6.3 Recommendations
- **`ReportBatchItemFailures` on all SQS workers** (CR worker is the reference implementation).
- **Visibility timeout ≥ 6× Lambda timeout** on every AI queue.
- **`max_concurrency` (3–5)** on AI worker event sources; reserved concurrency for the API path.
- **DLQ-depth + worker alarms** wired to the SNS topic/on-call; add the workers to monitoring.
- **Idempotent workers** keyed by business id; model the chain lock as explicit state (claim → set → clear-on-terminal) with a timeout that cannot strand.
- Keep payloads small (S3/Dynamo references, not bodies) — already largely true.

---

## 7. LLM architecture

### 7.1 Current shape (from code + `docs/cost-model/cost-model.md`)
Direct Anthropic API (not Bedrock). **Model routing is enforced and measured:** Sonnet for strategic work (VPR, Gap Analysis), Haiku for templated work (CV tailoring, cover letter, interview prep, AI assist, company research, CV parse) — `_resolve_model`, with a per-model cost metric carrying a `Model` dimension. **Prompt caching is partially adopted:** VPR phase-2 (~1,000-token system prompt), CV-tailoring stage 2, and AI-assist preamble use `cache_control: ephemeral`. The "digest" projection pattern exists (`build_vpr_digest`, `build_cv_digest`, `CVSummarizer`) and is applied in 4 of 5 downstream steps.

Two LLM clients coexist: a "router" (`logic/utils/llm_client.py`) with **real token accounting** (`response.usage`), cost calc, a `MAX_COST_PER_APPLICATION=0.25` alert, and caching support — used by VPR/CR/CV-parse; and an older `LLMClient` (`logic/llm_client.py`) that **estimates tokens as `len/4`** and captures no usage — used by Gap/Cover-Letter/Interview-Prep/CV-Tailoring/AI-Assist. So the cheap Haiku paths fly blind on cost.

Economics: **~$0.43/application, VPR ≈ 74%** (Sonnet, 6-stage, **output-token** dominated); ~88% margin flat to 10,000 users. The cost driver is **output tokens on the one Sonnet pipeline**, not input bloat. Hebrew ≈ 2× tokens. Power users (20–30 apps/mo) compress margin to 35–57%.

### 7.2 Risks
- **No rate-limit backpressure** to Anthropic (§6) — the main scaling risk on the LLM path.
- **Visibility==timeout** means a near-timeout VPR can be re-run — the most expensive possible duplicate.
- **Cost blind spots** on the Haiku artifacts (the `len/4` client) — you can't optimize or alert on what you don't measure.
- **`max_tokens` truncation risk** on VPR stages 4–6 and Interview Prep (cost-model.md:199,264) — a quality risk.
- **Prompt-injection** via job postings / scraped research (§1.2.F).

### 7.3 Recommendations (cost & performance)
- **Prompt caching is the highest-leverage cheap win:** migrate Gap/Cover-Letter/Interview-Prep from `generate()` to `complete(use_system_cache=True)` (pad system prompts to the 1,024-token cache minimum). Savings are modest (~$0.002–0.004/app) precisely because input isn't the driver — but it's near-zero-risk.
- **Bound the one real input-bloat case:** Company Research sends ~15 k tokens of raw Tavily content — truncate per result or set `include_raw_content:false` (~$0.007/gen).
- **Attack the actual driver (VPR output):** the 6-stage Sonnet pipeline is 74% of cost. Evaluate whether stages can be merged, whether some stages can drop to Haiku, and confirm stages 4–6 `max_tokens` aren't truncating; this is where real money is.
- **Unify on the cost-aware client** so Haiku artifacts get real token/cost capture and the `MAX_COST_PER_APPLICATION` alert applies everywhere.
- **Apply backpressure** (`max_concurrency`) and **idempotency** so retries/duplicates don't multiply spend.
- **Hebrew:** ensure `json.dumps(..., ensure_ascii=False)` in all prompt builders (escaped Hebrew triples token count); consider Hebrew as a premium tier.
- **Compression / RAG:** the digest pattern is already "store-rich, project-lean"; do **not** fold a compression program into the DB redesign. RAG/vectors stay deferred (additive nested stack only if a curated corpus is authored).

---

## 8. CloudFormation / stack redesign

### 8.1 Two meanings of "stacksets" — pick the right tool
- **AWS CloudFormation StackSets** (the named feature) deploy one template across **many accounts and/or regions** from a management account. CareerVP runs **all environments in one account, one region**, isolated by `{env}` naming. Unless you move to multi-account (a recommended future — see §11), **StackSets are not the tool here**; they'd add org/admin-role complexity for no isolation benefit today.
- **What you actually need is stack *composition* redesign** — decomposing one near-limit stack into a tree of nested/sibling stacks by lifecycle and blast radius. That's the real "stack set" problem.

### 8.2 Current problem
The parent `ServiceStack` (via `ApiConstruct`) is estimated at **~400–550 CloudFormation resources** against the **500 hard limit**, kept viable only by four existing nested stacks (monitoring, ai-assist, error-report, company-research). Critically, the **stateful resources live *inside* this high-churn stack with `RemovalPolicy.DESTROY`**, and the dedicated `DynamoDBStack`/`S3Stack` files that would hold them with `RETAIN` are **dead code never instantiated in `app.py`**.

### 8.3 Target composition
```
app.py
├── StatefulStack            (top-level, RETAIN + deletion_protection)   ← data outlives compute
│     DynamoDB tables (incl. new `core`), S3 buckets, (optionally) Cognito user pool
├── EdgeStack                WAF, custom domain/ACM, (CloudFront if API-fronting)
├── ServiceStack (parent)    REST API + shared wiring; composes per-feature NESTED stacks:
│     ├── AuthNestedStack
│     ├── VprNestedStack            (submit + workers + queue + DLQ)
│     ├── CompanyResearchNestedStack  (exists)
│     ├── CvNestedStack
│     ├── CoverLetterNestedStack
│     ├── InterviewPrepNestedStack
│     ├── BillingNestedStack
│     ├── AiAssistNestedStack       (exists)
│     ├── ChainNestedStack          (Step Functions + failure/cleanup handlers)
│     └── MonitoringNestedStack     (exists)
└── FrontendStack
```
Rules: **stateful resources top-level with `RETAIN`**; **share refs by constructor props, never `Fn::ImportValue`** (exports create deletion deadlocks that block recreation); **no template > ~400 resources**, enforced by a CI synth-and-count gate; each Lambda ≈ 5 resources, so budget accordingly. Migrate ownership of existing tables/buckets via **`cdk import`** / logical-id retention so CloudFormation *adopts* live resources rather than recreating them.

### 8.4 If/when multi-account
For real environment isolation, move dev/staging/prod to **separate accounts** under an Org, deploy via a CDK Pipelines + cross-account roles (or StackSets for org-wide guardrails like WAF baselines and SCPs). That replaces "isolation by naming" with "isolation by account boundary" — the strongest guardrail — and is the recommended long-term direction (§11).

---

## 9. Artifact processing — the auto-generation chain & reload status model

### 9.1 The flow you described
Post-Gap-Analysis submit → auto-generate **Company Research → VPR → Tailored CV** (then cover letter / interview prep on demand), with the UI checking status on page reload. Today this is implemented by the **Step Functions chain** (`artifact_chain_construct.py`): `RouteStartAt` → `StartCompanyResearch` (SQS+task-token) → `StartVPR` (SQS+task-token) → `StartCVTailoring` (synchronous Lambda invoke by ARN) → `GenerateFinalArtifacts` (Parallel: cover letter + interview prep). Failures route to per-stage handlers that set the application's artifact status to failed; an hourly EventBridge cleanup reaps cancelled jobs + their S3 results. Status is recorded in `applications.artifact_statuses` and surfaced by the per-artifact status endpoints.

### 9.2 Risks specific to the chain & reload-status model
- **Status is fragmented across stores.** Per-artifact status lives in `artifact_statuses` on the application item, but the actual artifacts live across `users`/`artifacts`/`jobs`+S3, and the reload-time status endpoints do multi-read/dual-read fallbacks (§5) — so "is this done?" is reconstructed, not read. The single-table `core` `#STATUS` item makes status a **single authoritative read**.
- **The gate-vs-worker identifier split** (the dossier's core bug) meant the gate could report "VPR missing" while the VPR existed, launching a redundant chain; fixing the gate alone unmasks the worker re-fetch-by-`vpr_id` defect. **Validate the whole chain to a persisted result, not just the gate's HTTP status.**
- **Silent message loss + duplicate processing** (§6) directly threaten chain steps — a dropped SQS message strands a `waitForTaskToken` state until its heartbeat/timeout; a re-delivered message double-generates.
- **Stale chain lock** can block or double-run the chain.
- **Reload polling storms** (§4) — the frontend polls completed artifacts on reload, multiplying status calls against expensive endpoints.

### 9.3 Recommendations
- Make `#STATUS` in `core` the **single source of truth**; the reload path becomes one `Query` (the bootstrap, §5.4) that returns every artifact's state — no per-artifact status fan-out.
- Carry the **resolved upstream reference** (`application_id` + version) in the SQS message; workers consume it or re-resolve by `application_id`, never by `*_artifact_id` (dossier §9.4).
- Apply the §6 fixes (batchItemFailures, visibility ≥6×, max_concurrency, DLQ alarms, idempotent workers, first-class chain lock).
- On the frontend, gate status polling on non-terminal state and prefer the bootstrap aggregate for reload (§4.3).

---

## 10. Parallel-environment redesign strategy (your explicit requirement)

You asked to run the redesign **in parallel to the current environment, duplicating resources until the new design is stable**. Here is how to do that safely in this single-account, `{env}`-suffixed setup.

### 10.1 Principle
Stand the redesign up as a **full, isolated duplicate environment** (a new `{env}` suffix, e.g. `redesign` or `v2`) deployed from the same CDK app. Because every resource name carries `{env}` via `NamingUtils`, a second environment is **physically separate** — its own tables, buckets, queues, Lambdas, API, Cognito (or a shared pool, see below). Nothing in the live `dev`/`prod` path is touched. This is the cleanest interpretation of "duplicate resources until stable," and it composes with the strangler-fig cutover.

### 10.2 What to duplicate vs share
- **Duplicate (new `{env}`):** all stateful tables (incl. the new `core`), buckets, all compute, queues, the Step Functions chain, the API Gateway stage. The new `core` model only ever exists in the redesign env first.
- **Share carefully or fork:** the **Cognito user pool** — either share the existing pool (so users don't re-register; the redesign env validates the same JWTs) or stand up a parallel pool seeded from the same source. Sharing the pool is simpler for a cutover; document the trade-off. **SSM secrets** can be shared (read-only) or duplicated per env.
- **Never share:** IAM roles across envs — every role's ARNs must carry the `{env}` suffix so the redesign env can never touch live data (a cross-env-capable role is a HIGH finding).

### 10.3 Keeping the duplicate in sync with live data
Two options, pick by how long the parallel run lasts:
- **One-time + CDC backfill (recommended):** seed the redesign `core` table from a live DynamoDB **export to S3**, then keep it current by consuming the **live tables' DynamoDB Streams** (already enabled on `artifacts`/`jobs`; enable on others) into an idempotent transformer that writes the `core` shape. This is the same expand/backfill machinery the runbook Phase 3 describes — here it crosses environments.
- **Dual-write at the application layer (behind a flag):** the live writers also write the `core` shape into the redesign env. Higher coupling; use only if you need strong freshness during the parallel run.

### 10.4 Cutover
Route a **cohort** (internal users → small %) to the redesign environment via a feature flag / edge routing, **shadow-compare** artifact outputs and status correctness against live, expand the cohort as confidence grows, then flip 100% and retire the old environment after a bake window. Rollback at any point = route the cohort back; the old env never stopped serving. This is the strangler-fig pattern at the *environment* granularity rather than the handler granularity.

### 10.5 Guardrails for the parallel run (same-account)
- **Tag everything** `Environment=redesign` for cost attribution; set **env-scoped reserved concurrency** and on-demand limits so a runaway redesign backfill can't consume live concurrency/throughput headroom.
- **Per-env alarms/budgets**; a separate SNS topic for the redesign env.
- Confirm `RETAIN` + `deletion_protection` on **both** environments before starting (so neither a misfired `cdk destroy --all` nor a replacement wipes data).
- Keep the redesign env's IAM ARNs strictly `*-{redesignenv}` scoped.

> This parallel-environment approach and the in-place expand-contract in the runbook are **complementary**: use the parallel env to prove the `core` model and the new compute end-to-end with real data; use expand-contract for the eventual in-place migration of the surviving environment — or simply promote the redesign env to be the new prod and retire the old.

---

## 11. If we rebuilt CareerVP from scratch

Same business, same AWS-serverless constraint, same ~88% margin target — but architected for *security, reliability, scale, performance, flexibility* from day one. The current system's pain is not its feature set; it's that data layout, identity, async correctness, and the frontend data layer were each decided incrementally and per-Lambda. A rebuild would make the right thing the *default* thing.

**1. Multi-account from day one.** Separate `dev`/`staging`/`prod` AWS accounts under an Organization, with SCP guardrails and a CDK Pipelines CI/CD deploying cross-account via OIDC. Isolation by account boundary, not by naming — the single strongest guardrail, and it removes the entire class of "dev role can touch prod data" risk.

**2. Single-table DynamoDB, access-pattern-first.** Design `core` (`PK=USER#{user_id}`, overloaded `SK`) from the documented access patterns *before* writing code, with a typed `artifact_type → (key)` contract and one `CoreRepository` as the sole key-builder. Generic keys, item collections, a sparse status GSI. Stateful resources in their own stack, `RETAIN` + deletion protection, PITR, streams — from the first commit. Result: one Query per application, one Query per bootstrap, atomic transactions, tenant isolation by construction, additive evolution. *This eliminates ~half the current findings outright.*

**3. Identity that cannot be spoofed.** Identity derives **only** from validated JWT claims — never a header or body field. The DAL enforces the tenant partition key, so IDOR is structurally impossible. One IAM role per function, ARN-scoped, no wildcards, generated by `grant_*`. MFA + advanced security on Cognito.

**4. Async correctness as a default.** Every SQS consumer reports `batchItemFailures`; visibility timeout templated at ≥6× the function timeout; `max_concurrency` on every rate-limited-dependency consumer; `@idempotent` on every at-least-once and money path; DLQ + depth alarm on every queue. The artifact chain is a Step Functions saga with explicit retry/catch/compensation and a first-class, timeout-bounded lock. A shared L3 construct bakes these in so a new async feature *inherits* them.

**5. A frontend with one data layer.** React Query (or RSC + a server cache) as the single server-state mechanism, configured with sane `staleTime`/`gcTime`, a centralized key factory, polling via `refetchInterval` with terminal guards, and a single `GET /me/bootstrap` aggregate fetched once. HTTP caching (`Cache-Control`/`ETag`) on every read endpoint. No raw `useEffect` fetching, no hand-rolled pollers, no duplicate keys. The reported "repeated calls" symptom never arises because the defaults prevent it.

**6. Edge that earns its keep.** HTTP API (cheaper/faster) where REST-only features aren't needed; WAF + rate-based rules in *all* environments; realistic throttles + per-user server-side quotas; request validation at the gateway; CloudFront fronting cacheable GETs; API versioning discipline.

**7. LLM cost-engineered up front.** One cost-aware LLM client with real token accounting and per-application cost ceilings on *every* call; model routing measured; prompt caching wherever the prompt clears the cache threshold; bounded inputs (truncated research); the expensive Sonnet pipeline continuously evaluated for stage-merging and tier-downgrade. Vectors/RAG added later *only* as an additive, derived read path behind a flag.

**8. Observability and safe delivery from commit #1.** Three pillars on every function (workers included), DLQ-depth and DynamoDB-throttle alarms to on-call, SLOs with error budgets, per-feature cost tags + anomaly alarms. Canary/linear traffic shifting with automatic alarm-based rollback on every function; feature flags so release ≠ deploy; secret scanning in CI; tests that drive the *real* DAL against the *real* key schemas (no autouse mock that hides routing bugs).

**9. Store-rich / project-lean, decoupled.** Keep full artifacts at rest (S3 + `core` pointer) and project purpose-built digests to the model — formalized and versioned, not ad hoc. Storage shape and prompt shape stay independent.

**The throughline:** the current architecture is *recoverable* — every finding here has an additive, reversible fix, and the redesign documents lay them out in order. A from-scratch build would simply start where those fixes land: **data, identity, async, and the frontend data layer designed as contracts, with the safe choice as the default** — so correctness, isolation, and cost discipline are properties of the platform rather than the diligence of each handler.

---

*Deep-dive companion to [`careervp-architecture-v2.md`](./careervp-architecture-v2.md) and [`redesign-runbook.md`](./redesign-runbook.md). Reconciled against `main` @ `4f7c294`.*
