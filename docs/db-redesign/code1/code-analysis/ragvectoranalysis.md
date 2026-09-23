# RAG / Vector-DB Feasibility Analysis for CareerVP

> **Type:** Architecture decision analysis (no code change).
> **Scope:** Should CareerVP adopt embeddings + a vector store (Amazon S3 Vectors, DynamoDB-as-vector, OpenSearch Serverless, or Bedrock Knowledge Bases)? Where does it pay off, where does it not, and how would it change the architecture under the §18 expand-contract safety rules.
> **Constraint:** AWS-native / serverless only. Preserve the 91%+ margin target and the Sonnet/Haiku routing strategy.
> **Date:** 2026-06-23 · **Author model:** opus-4.8/high

---

## 0. TL;DR — The honest answer

**Yes, but narrowly and additively. Vectors are a feature enabler, not an architecture replacement.**

The single most important insight from auditing the codebase: **CareerVP today does one-shot prompting — it stuffs the *entire* CV + job posting + company research + prior gap responses into the prompt** (`vpr_prompt.py:596`, `interview_prep.py:42`, `gap_analysis_prompt.py:30`). There is **no embedding or vector usage anywhere** in the repo. Retrieval is 100% key-based (`user_id`, `job_id`, `company_name`).

That fact cuts both ways and is the crux of the whole decision:

- **RAG helps when the source is large and only *partially* relevant** — a curated career-methodology corpus, a long company-research body, web-search results, or a power user's history across dozens of applications. Here, retrieving the top-k relevant chunks instead of dumping everything is a real win for cost, quality, and token budget.
- **RAG *hurts* when the source is small and *wholly* relevant** — a single user's CV or a single job posting. A VPR must reason over the *whole* CV; chunking it and retrieving "the relevant parts" will silently drop evidence and degrade the artifact. **Do not RAG over a user's own CV/job for generation.**

So the recommendation is **targeted adoption**, ranked by value-per-effort:

| Rank | Use case | Vector store | Value | Effort | Verdict |
|---|---|---|---|---|---|
| 1 | **Knowledge Base grounding** (curated career/VPR methodology corpus) | S3 Vectors (or Bedrock KB on S3 Vectors) | **High** — enables richer/more accurate artifacts that are *impossible* to achieve by prompt-stuffing | M–L | **Adopt** (build the corpus first) |
| 2 | **Company-research semantic reuse/dedup** (shared cache) | S3 Vectors | Medium — fewer redundant web-scrape+LLM runs across users; lower cost | M | **Adopt after #1** |
| 3 | **User's own artifact recall** (best prior bullets/answers across their apps) | **DynamoDB brute-force** (no new infra) | Medium for power users only | S | **Cheap experiment** |
| 4 | **Job ↔ profile matching/ranking** | S3 Vectors or OpenSearch | Medium, but **V2** (job tracking is deferred) | L | **Defer to V2** |

**What this is *not*:** It is not a reason to switch off DynamoDB/S3, not a reason to adopt OpenSearch Serverless (its ~$345/mo idle baseline would shred the margin), and not a replacement for the §18 single-table re-architecture. Vectors are a **new additive read path**, deployed as a new nested stack, behind a flag — exactly the strangler-fig shape the runbook already prescribes.

---

## Q1. How would CareerVP use S3 Vectors and/or DynamoDB-as-vector?

### 1a. Amazon S3 Vectors (the AWS-native default as of Dec 2025 GA)

S3 Vectors is a new bucket type (`vector bucket` → `vector index`) that stores embeddings as durable S3 objects and serves approximate-nearest-neighbour (ANN) queries directly, with no servers to run. It went GA in December 2025: up to **2 billion vectors per index**, 10,000 indexes per bucket, 14 regions, and sub-second query latency (practically ~100–800 ms, optimized for *hundreds* of QPS — not thousands).

**Pricing (us-east-1, verify before prod):**
- **Storage:** **$0.06 / GB-month** (vector + filterable/non-filterable metadata + keys).
- **Upload (PUT):** **$0.20 / GB** ingested.
- **Query:** **$2.50 / million queries** + a small data-processed charge (tiered, $0.004 → $0.0004 / TB) + **$0.01 / GB returned** (first 512 KB/query free).
- AWS positions it at **~90% cheaper than specialized vector DBs / OpenSearch Serverless**.

**How it slots into CareerVP — the canonical RAG read path:**

```
                       ┌─────────── write/index time (async, Streams or batch) ───────────┐
  source text ─────► chunk ─────► Bedrock embedding (Titan v2 / Cohere) ─────► S3 Vectors index
  (KB doc, company                                                              (vector + metadata:
   research body)                                                                tenant, doc_id, lang)

                       ┌──────────────── query time (in a *_worker Lambda) ────────────────┐
  generation request ─► embed the query ─► S3 Vectors query (top-k, metadata filter) ─► inject
                                                                                       k chunks
                                                                                       into prompt ─► LLM
```

Concretely, two indexes to start:

1. **`careervp-kb-vectors-{env}`** — chunks of the curated career/VPR methodology corpus (see Q1 caveat: this corpus does not exist yet and must be authored). Metadata: `{lang: en|he, topic, doc_id, chunk_id}`. Queried during VPR / gap / interview-prep generation to inject 3–5 relevant methodology chunks instead of nothing (or instead of an impossible full-corpus dump).
2. **`careervp-company-research-vectors-{env}`** — one (or few) vectors per cached company-research body, keyed off the existing `careervp-company-research-cache-{env}` table (`api_db_construct.py:409`). Lets a new request find a *semantically equivalent* prior research result ("Google" ≈ "Google LLC" ≈ "Alphabet") before paying for a fresh scrape + Haiku synthesis (`company_research.py:29`).

S3 Vectors' latency profile (100–800 ms, hundreds of QPS) is a **perfect fit** here: all of CareerVP's AI work is already **async behind SQS/Step Functions** (`*_submit` → queue → `*_worker`), so an extra ~300 ms in a worker is invisible to the user. This is the key reason S3 Vectors — not OpenSearch — is the right tool for this app.

### 1b. DynamoDB as a vector store (brute-force, zero new infra)

DynamoDB has **no native vector type and no ANN index**. You can still do useful vector search by storing the embedding as a number-list/binary attribute and computing cosine similarity **in the Lambda** after a key-based prefilter. This is only viable when the candidate set is *small* — but for **use case #3 (a user's own artifact history)** it is, because you first narrow to `PK=USER#{uid}` and a single user rarely has more than a few dozen artifacts.

```python
# Per-user recall with NO new infrastructure — fits the existing single-table direction (§5.2).
items = table.query(KeyConditionExpression=Key("PK").eq(f"USER#{uid}")
                    & Key("SK").begins_with("EMB#"))          # tens of items, not millions
ranked = sorted(items, key=lambda i: cosine(q_vec, i["vec"]), reverse=True)[:k]
```

**When DynamoDB-as-vector is right:** small per-tenant corpora (≤ ~1–2k vectors), no new stack, naturally inherits the tenant isolation you already enforce (`PK=USER#{uid}`), and it composes with the planned `core` single-table model (store `SK=APP#{app_id}#EMB#{artifact}` alongside the artifact).
**When it's wrong:** any cross-user / corpus-wide search (KB, company dedup) — brute force over all tenants is an O(table) Scan in disguise, which the best-practices guide flags **HIGH** (§5.1). Use S3 Vectors there.

### 1c. The two AWS-native options you should *not* reach for first

- **OpenSearch Serverless (the old Bedrock-KB default):** real-time, high-QPS, low-latency k-NN — but a **~$345/month minimum idle baseline (2 OCU × $0.24/OCU-hr)**. For a pre-scale product guarding a 91% margin, that fixed cost is disqualifying. Only revisit if you ever need thousands of QPS at <50 ms (you don't, because generation is async).
- **Bedrock Knowledge Bases (managed RAG):** orchestrates chunking → embedding → sync → retrieve → optional rerank, and **can now use S3 Vectors as its backend**, plus parsing ($0.01/page) and Amazon Rerank ($1.00 / 1,000 queries). It removes a lot of build effort for use case #1. **Caveat:** CareerVP currently calls the **Anthropic API directly** (`llm_client.py`), not Bedrock — adopting Bedrock KB introduces a Bedrock dependency and a second model-access path. Reasonable, but it's an architecture decision in its own right (see Q3).

---

## Q2. How would this change the architecture?

The change is **purely additive** and maps cleanly onto the runbook's existing phase model. Nothing in the current data path is removed or mutated.

### New components
- **One new nested stack** `VectorNestedStack` under the parent `ServiceStack` (per §2.1) — keeps you inside the 500-resource limit and gives the vector path its own blast radius. It composes: the S3 Vectors bucket/indexes, an **embedding/indexing worker** (SQS-fed), and IAM grants.
- **Embedding generation** via Bedrock (`Titan Text Embeddings v2` or `Cohere Embed v4`), called from a worker — **not** on any API-path Lambda. Embedding cost is negligible (≈ $0.02–$0.10 per **million** input tokens — verify current Bedrock pricing; it rounds to nothing next to generation cost).
- **Index-time pipeline:** reuse **DynamoDB Streams** (already enabled `NEW_AND_OLD_IMAGES` on artifacts/jobs) → a stream consumer enqueues an embed job → worker embeds → writes to S3 Vectors. This is the same CDC pattern the runbook recommends for migration backfill (§5.4, §18.4), so it's idempotent and replayable by construction.
- **Query-time seam:** a `RetrievalService` in the **logic layer** (the only module that talks to the vector store, mirroring the "`CoreRepository` is the only key-builder" discipline). Handlers stay thin.

### What changes in the generation flow

| Today | With targeted RAG |
|---|---|
| Handler fetches CV+Job+Company+Gap, dumps **all** as JSON into prompt (`vpr_prompt.py:596`) | Same for CV/Job (kept whole). **Augmenting** context (KB methodology, long company research) is **retrieved top-k** and only relevant chunks injected |
| KB methodology grounding is **not possible** (can't stuff a 200-page corpus per call) | 3–5 relevant chunks (~1–2k tokens) injected → grounded, on-brand, anti-AI-detection-aligned output |
| Company research = exact-name cache hit or full re-scrape+LLM | Semantic cache hit reuses near-duplicate research → fewer Haiku calls + web fetches |

### What does *not* change
- DynamoDB and S3 remain the **system of record**. Vectors are a **derived, rebuildable index** — never authoritative. (If the index is lost, re-embed from source; no data loss. This is also why vectors **do not** "increase DB resilience" — see Q3 issues.)
- Sonnet/Haiku routing, idempotency, DLQs, tenant isolation — all unchanged and inherited.
- Tenant isolation extends naturally: **every vector carries a `tenant`/`user_id` metadata field and every query passes a metadata filter** — the same IDOR discipline as the DAL (§8). Cross-tenant retrieval = a CRITICAL bug, gated the same way.

### Migration shape (§18 expand-contract — vectors are easy because they're additive)
```
Expand:   deploy VectorNestedStack + indexes (no reads).      flag rag_retrieval = OFF
Backfill: Stream/batch embed existing KB + company-research.  (idempotent, throttled)
Dual:     generation optionally retrieves; shadow-compare artifact quality on a cohort.
Cutover:  flip rag_retrieval ON per artifact, per cohort.     rollback = flip flag (index stays warm)
```
There is **no "contract" risk** — because the vector store is derived, you can delete it any time and fall back to today's behavior by flipping the flag. That makes this one of the **lowest-risk** changes in the whole redesign backlog.

---

## Q3. Is there value in switching to a vector approach?

Scored against **your stated goals**:

| Your goal | Verdict | Why |
|---|---|---|
| **Richer artifact content** | ✅ **Strong** | KB grounding (use case #1) lets artifacts cite real frameworks/methodology instead of generic LLM prose. This is the headline win and is *impossible* without retrieval. |
| **More accurate** | ✅ **Strong** | Grounding in a curated corpus reduces hallucination and drift; semantic company-research reuse avoids regenerating weak results. |
| **Send less data to the LLM** | ⚠️ **Mixed → net positive** | True **for augmenting context** (KB, long research, history): inject top-k instead of everything. **False for CV/job** — those must stay whole, so don't expect to shrink the core prompt. Net token reduction is real but modest on existing calls; the bigger effect is *enabling* KB grounding *without* a token blowup. |
| **Cheaper to store** | ➖ **Neutral** | You already store cheaply in DynamoDB/S3. S3 Vectors at $0.06/GB-mo is cheap, but it's *additional* storage, not a replacement. Net storage cost goes slightly **up**, not down. |
| **Cheaper to retrieve** | ⚠️ **Mixed** | Vector query adds a per-query fee + ~300 ms. It's cheaper than re-running web-scrape+LLM for company research (real saving), but more expensive than today's free `GetItem` for cases that don't need semantics. |
| **Improve performance** | ⚠️ **Mixed** | Retrieval adds latency in the worker (hidden by async), but smaller/*grounded* prompts can reduce generation time and retries. Net roughly flat for the user; slightly better artifact-per-attempt success. |
| **Increase DB resilience** | ❌ **No** | Vectors are a *derived* index, not a resilience mechanism. Resilience comes from PITR, on-demand backups, single-table conditional writes, DLQs — the §5/§15 items. **Do not adopt vectors expecting resilience; pursue the §18 data re-architecture for that.** |
| **Token optimization** | ✅ **Good** | Real on augmenting context and on the company-research path (skip redundant synthesis). Directly supports the 91% margin **if** you also enforce bounded top-k and reuse (don't let retrieval *add* tokens). |

### Bottom line
Adopt vectors for **#1 (KB grounding)** as the flagship — it's the only item that unlocks a capability you simply cannot get by prompt-stuffing, and it directly serves "richer + more accurate." Pair it with **#2 (company-research semantic reuse)** for the clearest cost saving, and run **#3 (DynamoDB brute-force per-user recall)** as a cheap, no-new-infra experiment. **Defer #4 (job↔profile matching)** to V2 with job tracking. **Avoid OpenSearch Serverless** outright on margin grounds. **Skip vectors entirely for CV→VPR core context** — that would degrade quality.

The prerequisite that gates everything: **#1 requires authoring a curated corpus that does not exist today.** The repo's "Knowledge Base" feature (`knowledge_base.py`, `careervp-knowledge-{env}`) is a per-user key-value store of gap responses + company research — *not* a document corpus. No corpus, no KB RAG. Budget for content authoring, not just code.

---

## Issues you should be considering (raised by this review)

1. **No corpus exists yet.** The biggest-value use case (#1) is blocked on authoring/licensing a career-methodology corpus in **English *and* Hebrew** (V1 is bilingual). This is a content cost, not an engineering one — scope it explicitly.
2. **Don't RAG the CV.** Chunking a user's own CV/job for generation will drop evidence and *lower* quality. Keep whole-document inputs whole; reserve retrieval for large external/aggregate sources. Treat "RAG over everything" as an anti-pattern.
3. **Tenant isolation moves into metadata filters.** Every vector needs a `tenant`/`user_id` tag and every query a matching filter — a missing filter is a cross-tenant **IDOR/CRITICAL** leak (§8). Make `RetrievalService` the sole query path and unit-test the filter on every call, same discipline as the planned `CoreRepository`.
4. **Embeddings are PII-derived.** Vectors of a user's CV are personal data. They must inherit encryption-at-rest, the GDPR **erasure** path (delete vectors on user deletion, §9), and `{env}`-scoped IAM ARNs (§18.1) so dev can't read prod vectors.
5. **The vector index is derived, never authoritative.** Source of truth stays in DynamoDB/S3. Build the index from **Streams** so it's rebuildable and you never have a dual-write consistency problem on the hot path. A stale/lost index degrades gracefully (flag off → today's behavior).
6. **Re-embedding cost on model change.** Switching embedding models (or re-chunking) means re-embedding the whole corpus. Version the index (`...-vectors-v2`), backfill, shadow-compare, cut over — same expand-contract as a GSI change (§18.4). Pin the embedding model + dimension in the spec.
7. **Confidence-gate interaction with a *shared* semantic cache.** The 0.85 company-research confidence gate matters more once semantic matching serves one company's research to *near-duplicate* companies — a single weak result can now reach many users (also flagged in the runbook's open confirms). Gate retrieval on confidence + similarity threshold, and decide the min cosine score for a "reuse" vs "regenerate".
8. **Latency/QPS ceiling of S3 Vectors.** ~100–800 ms, hundreds of QPS/bucket. Fine inside async workers; **not** for a synchronous "type-ahead job search" UX. If a real-time search feature ever appears, that's the (rare) case for OpenSearch — re-evaluate then.
9. **500-resource limit (§2.1) is a hard prerequisite.** The vector path must land as a **new nested stack**, and Phase 0.3's nested-stack carve-up must be done first — otherwise there's no headroom to deploy it. Don't bolt indexes onto a near-full stack.
10. **Bedrock dependency decision.** Embeddings (and optional Bedrock KB/rerank) introduce Bedrock alongside the current direct Anthropic API. Decide deliberately: Bedrock KB buys managed chunking/sync at the cost of a second model-access surface, new IAM, and Bedrock pricing to track in the margin model.
11. **Measure before generalizing.** Gate each use case behind a flag and a shadow-comparison metric (artifact-quality parity, token delta, cost delta). Ship #1 to a cohort, prove richer/cheaper, *then* expand — never big-bang.

---

## Recommended sequencing (fits the runbook's phase model)

This is an additive **Phase 5+ / parallel track**, not a blocker for the Phase 3 data re-architecture. It depends only on Phase 0.3 (nested-stack headroom).

```
V-0  Spec specs/redesign/p5.rag_vectors.yaml: indexes, embedding model+dim (pinned),
     chunking, metadata schema (incl. tenant), top-k bounds, similarity thresholds,
     flags (rag_retrieval, company_semantic_reuse), rollback. opus-4.8/high. Review-gated (§18).
V-1  Author the KB corpus (EN+HE) — content workstream, parallel to engineering.
V-2  Expand: VectorNestedStack + S3 Vectors indexes + embedding worker (SQS).
     Additive deploy, no reads. Resource-count gate <400.
V-3  Backfill via Streams/batch: embed KB corpus + company-research cache (idempotent, throttled).
V-4  Dual/shadow: generation optionally retrieves; shadow-compare artifact quality + token/cost
     deltas on an internal cohort. Flags default OFF.
V-5  Canary cutover per artifact, per cohort. Rollback = flag off (index stays warm).
V-6  Cheap parallel experiment: DynamoDB brute-force per-user recall (#3), no new infra.
(V2) Job↔profile matching (#4) with job-tracking feature.
```

**Merge gates (unchanged):** unit + integration green (including the tenant-filter IDOR test on every retrieval), regression golden (`p0.behavior_inventory`) parity, e2e at the V-5 cutover. A red regression = no merge.

---

## Illustrative cost sketch (verify before committing)

Assume 1,000 active users, a 300-page methodology corpus, and ~20k generation calls/month.

- **Corpus storage:** 300 pages ≈ ~3 MB text → ~a few thousand 1024-dim chunks (4 KB each) ≈ < 50 MB with metadata → **< $0.01/month** storage; one-time upload **< $0.01**.
- **Embedding (index-time):** corpus + company-research bodies, a few million tokens → **cents, one-time** (plus deltas).
- **Query (gen-time):** ~20k–60k vector queries/month (1–3 indexes/call) → **< $0.20/month** in query fees.
- **vs. avoided cost:** semantic company-research reuse skips redundant web-scrape + Haiku synthesis on near-duplicate companies — likely the **largest single saving**, easily > the entire vector bill.

Net: the vector infrastructure itself is **rounding error** against the LLM bill. The economic question is **content authoring (V-1)** and **engineering time**, not AWS spend. The margin risk is OpenSearch Serverless's idle baseline — which this design deliberately avoids.

---

## Sources
- [Amazon S3 Vectors now generally available (AWS News Blog)](https://aws.amazon.com/blogs/aws/amazon-s3-vectors-now-generally-available-with-increased-scale-and-performance/)
- [Amazon S3 Vectors — feature page](https://aws.amazon.com/s3/features/vectors/)
- [S3 Vectors GA — What's New](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-s3-vectors-generally-available/)
- [S3 Vectors reaches GA — "storage-first" RAG (InfoQ)](https://www.infoq.com/news/2026/01/aws-s3-vectors-ga/)
- [AWS claims 90% vector cost savings (VentureBeat)](https://venturebeat.com/data-infrastructure/aws-claims-90-vector-cost-savings-with-s3-vectors-ga-calls-it-complementary)
- [Real cost of vector storage: S3 vs OpenSearch vs pgvector vs Pinecone](https://darryl-ruggles.cloud/the-real-cost-of-vector-storage-s3-vectors-vs-opensearch-vs-pgvector-vs-pinecone/)
- [Hybrid vector storage nuances (Caylent)](https://caylent.com/blog/architecting-gen-ai-at-scale-lessons-from-aws-s-3-vector-store-and-the-nuances-of-hybrid-vector-storage)
- [Amazon Bedrock Knowledge Bases](https://aws.amazon.com/bedrock/knowledge-bases/)
- [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
- [Bedrock pricing explained 2026 (Cloudchipr)](https://cloudchipr.com/blog/amazon-bedrock-pricing)
