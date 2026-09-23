# CareerVP Cost Model

**Date:** 2026-06-29
**Scope:** Per-artifact Anthropic AI costs, AWS infrastructure costs, Tavily API costs, full-application rollup, scaling projections, and optimization gaps.

---

## 1. Data Sources & Confidence

| Source | What it covers | Confidence |
|--------|---------------|------------|
| CloudWatch `/aws/lambda/careervp-company-research-worker-lambda-dev` | Company Research token/cost actuals (2 samples) | **Actual** |
| Source code (prompts, handlers, CDK) | Models, max_tokens, caching status, Lambda sizes | **Confirmed** |
| AWS/Anthropic pricing pages | Unit rates | **Confirmed** |
| Prompt structure analysis | Token count estimates for workers with no CW data | **Estimated** |
| Frontend component analysis | AI Assist turn counts per artifact | **Estimated** |

No CloudWatch token data was found for: VPR, CV Tailor, Gap Analysis, Cover Letter, Interview Prep, AI Assist workers. All figures for those artifacts are estimates derived from prompt structure and model defaults.

---

## 2. Pricing Reference

### Anthropic (as of 2026)

| Model | Input | Output | Cache Write | Cache Read |
|-------|-------|--------|-------------|------------|
| claude-sonnet-4-6 | $3.00/MTok | $15.00/MTok | $3.75/MTok | $0.30/MTok |
| claude-haiku-4-5-20251001 | $0.80/MTok | $4.00/MTok | $1.00/MTok | $0.08/MTok |

### AWS Lambda (us-east-1)

| Tier | Requests | Compute |
|------|----------|---------|
| Free (permanent) | 1M req/month | 400,000 GB-sec/month |
| Beyond free | $0.20/million req | $0.0000166667/GB-sec |

### AWS DynamoDB On-Demand (us-east-1)

| | Rate | Free tier |
|-|------|-----------|
| Write Request Units | $1.25/million WRU | None (on-demand mode) |
| Read Request Units | $0.25/million RRU | None (on-demand mode) |
| Storage | $0.25/GB-month | First 25 GB free (permanent) |

### AWS S3 Standard (us-east-1)

| Item | Rate |
|------|------|
| Storage | $0.023/GB-month |
| PUT/POST | $0.005/1,000 |
| GET | $0.0004/1,000 |
| Data transfer out (internet) | $0.09/GB |

### AWS API Gateway (REST)

| Item | Rate | Notes |
|------|------|-------|
| API calls | $3.50/million | 12-month free tier expired |
| Data transfer out | $0.09/GB | |

### AWS SQS

| Item | Rate |
|------|------|
| Requests | $0.40/million | First 1M/month free (permanent) |

### AWS Cognito

| Users | Rate |
|-------|------|
| 0–50,000 MAU | Free (permanent) |
| 50,001–100,000 MAU | $0.0055/MAU |

### Tavily

| Tier | Searches/month | Cost |
|------|---------------|------|
| Free | 1,000 | $0 |
| Starter (est.) | 5,000 | ~$49/month |
| Per-search beyond free | — | ~$0.01/search |

### AWS Step Functions

| Type | Rate |
|------|------|
| Standard workflow | $0.025/1,000 state transitions |

### AWS WAF

| Item | Rate |
|------|------|
| Web ACL | $5.00/month |
| Rule evaluation | $1.00/million requests |

---

## 3. Model Assignments (Confirmed from `constants.py`)

```
STRATEGIC_MODEL_ID = "claude-sonnet-4-6"     → VPR Generation, Gap Analysis
TEMPLATE_MODEL_ID  = "claude-haiku-4-5-20251001"  → CV Tailoring, Cover Letter, Interview Prep, AI Assist, Company Research, CV Parsing
```

---

## 4. Prompt Caching Status

| Artifact / Stage | Caching | Details |
|-----------------|---------|---------|
| VPR Phase 2 synthesis (Stage 3) | ✅ Active | `PHASE2_SYSTEM_PROMPT` (~1,000 tokens) with `cache_control: ephemeral` |
| CV Tailoring Stage 2 | ✅ Active | `build_tailoring_system_prompt()` (~800 tokens) cached |
| AI Assist system preamble | ✅ Active | Per-artifact role + anti-AI rules (~300–400 tokens) cached |
| Gap Analysis | ❌ NOT cached | Uses `generate()` which concatenates system+user into one string; no `cache_control` applied |
| Cover Letter | ❌ NOT cached | Uses `generate()` — same issue |
| Interview Prep | ❌ NOT cached | Uses `generate()` — same issue |
| Company Research LLM structuring | ❌ NOT cached | `build_structure_system_prompt()` is ~15 tokens; too small to cache anyway (min 1,024 tokens required) |
| VPR Stages 1,2,4,5,6 | ❌ Not cached | System prompts are 15–30 tokens each; below the 1,024-token cache minimum |

**Gap Analysis caching opportunity:** The system prompt is ~350 tokens — too small on its own. Combining the static rules section with a constant instruction preamble could bring it to cache threshold. Worth refactoring `generate()` call to `complete()` with `use_system_cache=True`.

**Cover Letter / Interview Prep caching opportunity:** Same as above. System prompts are ~300–700 tokens. Could be cached if migrated from `generate()` to `complete()`.

---

## 5. Per-Artifact Anthropic Cost Estimates

### 5.1 Base CV Upload & Parse (one-time per user)

| Parameter | Value | Source |
|-----------|-------|--------|
| Model | Haiku | inferred from DEFAULT_MODEL |
| max_tokens | 3,000 | `cv_parser.py:239` |
| Input tokens | ~4,000 (raw CV text extraction) | Estimated |
| Output tokens | ~2,000 (structured JSON) | Estimated |
| Cache | None | — |

**Cost per CV parse:**
- Input: 4,000 × $0.80/M = **$0.0032**
- Output: 2,000 × $4.00/M = **$0.0080**
- **Total: ~$0.011 per user** (amortized across all their applications)

---

### 5.2 Gap Analysis

| Parameter | Value | Source |
|-----------|-------|--------|
| Model | Sonnet 4.6 | `constants.py` STRATEGIC_MODEL_ID |
| Invocations | 1 per application | — |
| System prompt | ~350 tokens | `gap_analysis_prompt.py` analysis |
| User prompt | CV JSON (~3,000) + job posting JSON (~1,000) | Estimated |
| Total input | ~4,350 tokens | — |
| Output | 10 questions JSON | ~1,500 tokens estimated |
| Cache | ❌ None | `generate()` used |

**Cost per Gap Analysis:**
- Input: 4,350 × $3.00/M = **$0.01305**
- Output: 1,500 × $15.00/M = **$0.02250**
- **Total: ~$0.036 per application**

---

### 5.3 Company Research (Haiku + Tavily)

**Actual CloudWatch data (2 samples, 2026-06-28):**

| Sample | Input tokens | Output tokens | Logged cost | model |
|--------|-------------|--------------|-------------|-------|
| 1 | 15,218 | 1,400 | $0.02222 | claude-haiku-4-5-20251001 |
| 2 | 15,219 | 1,164 | $0.02104 | claude-haiku-4-5-20251001 |
| **Avg** | **15,218** | **1,282** | **$0.02163** | — |

**Explanation of high input token count:** Tavily returns raw web content (5 results from 2 searches: 3 profile + 2 news). Each result is ~3,000 tokens of raw text. The `aggregate_search_content()` function concatenates all results before passing to LLM. This drives input to ~15,000 tokens consistently.

**Tavily calls per Company Research:** 2 API calls (1 profile search + 1 news search). Potentially up to 4 if site-scoped search fails and falls back to general search.

**Cost per Company Research:**
- LLM (Haiku): **$0.022 average** (actual)
- Tavily (free tier): $0 for first 1,000 searches/month (≈ 500 CR generations/month)
- Tavily (beyond free): ~$0.01/search × 2 = **$0.020 per CR**

---

### 5.4 VPR Generation (Sonnet, 6-Stage Pipeline)

**Architecture:** 6 sequential LLM calls within a single Lambda invocation. Stage 3 replaced by Phase 2 approach (larger, higher-quality prompt).

| Stage | System tokens | User input tokens | Output tokens | max_tokens | Cache |
|-------|--------------|------------------|--------------|------------|-------|
| 1 – Analysis | ~20 | CV+Job = ~3,500 | ~700 | 2,500 est. | ❌ |
| 2 – Evidence Mapping | ~20 | Stage1 output = ~700 | ~800 | 2,500 est. | ❌ |
| 3 – Phase 2 Synthesis | **~1,000** (cached) | Evidence+CV+Job+CR+Gaps+Schema = **~7,000** | **~5,000** | **16,000** | ✅ write |
| 4 – Self-Correction | ~250 (incl. few-shot) | Draft VPR = ~5,000 | ~5,000 | 2,500 est. | ❌ |
| 5 – Formatting | ~20 | Corrected JSON = ~5,000 | ~4,000 | 2,500 est. | ❌ |
| 6 – Meta-Evaluation | ~20 | VPR JSON = ~4,000 | ~300 | 2,500 est. | ❌ |
| **Totals** | | **~26,000** | **~15,800** | | |

> **Note on Stage 4/5:** Default max_tokens in `complete()` is 2,500. Stage 3 Phase 2 output can be up to 16,000 tokens. If subsequent stages have default max_tokens=2,500, they will truncate the VPR. Verify explicitly what max_tokens is passed to stages 4–6 in `vpr_generator.py`. This is a potential quality issue, not a cost issue.

**Cost per VPR (Stage 3 first invocation — cache write):**
- Stage 1: (20+3,500) × $3/M + 700 × $15/M = $0.0106 + $0.0105 = $0.0211
- Stage 2: (20+700) × $3/M + 800 × $15/M = $0.0022 + $0.0120 = $0.0142
- Stage 3: 1,000 × $3.75/M (cache write) + 7,000 × $3/M + 5,000 × $15/M = $0.0038 + $0.0210 + $0.0750 = **$0.0998**
- Stage 4: (250+5,000) × $3/M + 5,000 × $15/M = $0.0158 + $0.0750 = $0.0908
- Stage 5: (20+5,000) × $3/M + 4,000 × $15/M = $0.0151 + $0.0600 = $0.0751
- Stage 6: (20+4,000) × $3/M + 300 × $15/M = $0.0121 + $0.0045 = $0.0166
- **Total: ~$0.32 per VPR**

**Range:** $0.25–$0.40 depending on CV length and job posting size.

> Stage 3 is the dominant cost driver (~31% of total). The Phase 2 synthesis with max_tokens=16,000 and a large user prompt is expensive but justified by quality.

---

### 5.5 CV Tailoring (Haiku, 2-Stage Pipeline)

| Stage | System tokens | User input tokens | Output tokens | max_tokens | Cache |
|-------|--------------|------------------|--------------|------------|-------|
| 1 – Keyword Mapping | ~350 | CV+Job+VPR = ~4,000 | ~700 | 2,500 | ❌ |
| 2 – CV Generation | **~800** (cached) | CV+Job+FVS+Keywords = ~3,500 | ~2,000 | **2,500** | ✅ write |
| **Totals** | | **~8,650** | **~2,700** | | |

**Cost per CV Tailoring (first run):**
- Stage 1: (350+4,000) × $0.80/M + 700 × $4/M = $0.0035 + $0.0028 = $0.0063
- Stage 2: 800 × $1.00/M (cache write) + 3,500 × $0.80/M + 2,000 × $4/M = $0.0008 + $0.0028 + $0.0080 = $0.0116
- **Total: ~$0.018 per CV Tailoring**

**Range:** $0.015–$0.025 (Haiku keeps this very affordable).

---

### 5.6 Cover Letter (Haiku)

| Parameter | Value | Source |
|-----------|-------|--------|
| Model | Haiku | TEMPLATE_MODEL_ID |
| System prompt | ~300 tokens | `cover_letter_prompt.py` analysis |
| User prompt | Company (~50) + CR (~600) + Job (~750) + CV digest (~600) + VPR summary (~700) + Gap responses (~1,000) = ~3,700 tokens | Estimated |
| Total input | ~4,000 tokens | — |
| Output | 250–350 word cover letter | ~400 tokens |
| max_tokens | 2,500 (`generate()` default) | Confirmed |
| Cache | ❌ None | `generate()` used |

**Cost per Cover Letter:**
- Input: 4,000 × $0.80/M = **$0.0032**
- Output: 400 × $4.00/M = **$0.0016**
- **Total: ~$0.005 per Cover Letter**

---

### 5.7 Interview Prep (Haiku)

| Parameter | Value | Source |
|-----------|-------|--------|
| Model | Haiku | TEMPLATE_MODEL_ID |
| System prompt | ~700 tokens | `interview_prep_prompt.py` analysis |
| User prompt | Role+Company (~100) + CV facts (~700) + Job reqs (~800) + VPR (~2,000) + VPR differentiators (~300) + Gap responses (~1,000) + CR (~600) = ~5,500 tokens | Estimated |
| Total input | ~6,200 tokens | — |
| Output | 10 Q×STAR answers + questions to ask + salary guidance + checklist | ~2,000 tokens |
| max_tokens | 2,500 (`generate()` default) | Confirmed |
| Cache | ❌ None | `generate()` used |

> ⚠️ **max_tokens warning:** Interview prep output at ~2,000 tokens is near the 2,500 cap. 10 full STAR answers (150–300 words each) would be 1,500–3,000 tokens alone, before questions-to-ask and checklist. Output may be truncated. Increasing max_tokens to 4,000–6,000 is advisable (cost impact: +$0.006–$0.014 per generation).

**Cost per Interview Prep (current):**
- Input: 6,200 × $0.80/M = **$0.0050**
- Output: 2,000 × $4.00/M = **$0.0080**
- **Total: ~$0.013 per Interview Prep**

---

### 5.8 AI Assist (Haiku, per turn)

AI Assist is a conversational field-rewrite tool invoked once per Tiptap editable field.

**Editable Tiptap fields per artifact (confirmed from frontend source):**

| Artifact | Editable RichTextEditor fields | AI Assist turns |
|----------|-------------------------------|-----------------|
| Gap Analysis | 10 (one per question answer) | 10 |
| CV Tailored | 1 (main tailored CV field, line 113) | 1 |
| Cover Letter | 2 (two sections, lines 275 + 295) | 2 |
| Interview Prep | 1 (STAR answer field, line 187 — inside question loop) | ~10 (once per question) |
| **Total possible** | | **~23 turns** |

**Realistic usage assumption:** Not all users engage AI Assist on every field. Estimate **30–50% engagement = 7–12 turns per application.**

**Cost per AI Assist turn:**
| Component | Tokens | Cost |
|-----------|--------|------|
| System preamble (cache read after 1st call) | ~350 | 350 × $0.08/M = $0.000028 |
| User message (field + current text + context digests) | ~1,200 | 1,200 × $0.80/M = $0.00096 |
| Output (rewritten field markdown) | ~400 | 400 × $4.00/M = $0.00160 |
| **Per turn** | | **~$0.0026** |

| AI Assist scenario | Turns | Total cost |
|-------------------|-------|-----------|
| Heavy user (all fields) | 23 | $0.060 |
| Average user (50%) | 12 | $0.031 |
| Light user (25%) | 6 | $0.016 |

---

## 6. Per-Application Cost Rollup

**Standard flow per application:** CV parse (amortized) → Gap Analysis → Company Research → VPR → CV Tailoring (mandatory) → Cover Letter (50% of apps) → Interview Prep (25% of apps) → AI Assist (average user, 12 turns)

### Mandatory artifacts (every application):
| Artifact | Cost |
|---------|------|
| Gap Analysis (Sonnet) | $0.036 |
| Company Research (Haiku + Tavily free tier) | $0.022 |
| VPR Generation (Sonnet, 6 stages) | $0.320 |
| CV Tailoring (Haiku, 2 stages) | $0.018 |
| AI Assist — average 12 turns (Haiku) | $0.031 |
| **Mandatory subtotal** | **$0.427** |

### Optional artifacts (blended into per-application average):
| Artifact | Cost | Usage rate | Blended cost |
|---------|------|-----------|-------------|
| Cover Letter | $0.005 | 50% | $0.003 |
| Interview Prep | $0.013 | 25% | $0.003 |
| **Optional subtotal** | | | **$0.006** |

### CV Parse amortization:
| Scenario | Applications per user | Amortized CV parse cost |
|----------|----------------------|------------------------|
| 5 applications | $0.011 / 5 | $0.002 |
| 20 applications | $0.011 / 20 | $0.001 |

### **Total per-application AI cost (Anthropic only): ~$0.43–$0.45**

> **VPR dominates at ~74% of AI cost per application.** The 6-stage Sonnet pipeline is the primary cost driver. Everything else is minor by comparison.

---

## 7. AWS Infrastructure Cost

### Lambda (33 functions)

**Key memory/timeout configurations (from CDK):**

| Lambda group | Memory | Timeout | Worker type |
|-------------|--------|---------|------------|
| Error report | 128 MB | 10s | Utility |
| Auth, health, billing | 128–256 MB | 10–30s | API handler |
| Gap, CV status, export | 256 MB | 30s | API handler |
| AI Assist | 512 MB | 25s | Synchronous LLM |
| API handlers (default) | 512 MB | 60s | Per `API_HANDLER_LAMBDA_MEMORY_SIZE` |
| VPR submit, cover letter status | 256–512 MB | 30s | |
| Company Research worker | 512 MB | 300s | Async worker |
| Cover Letter worker | 512 MB | 300s | Async worker |
| Interview Prep worker | 512 MB | 300s | Async worker |
| CV parser | 1,024 MB | 120s | Document processing |
| VPR worker | 1,024 MB | ~300s | Async LLM worker |
| CV Tailor worker | 1,024 MB | ~300s | Async LLM worker |

**Lambda cost estimate at 100 active users, 5 applications/user/month:**

- Total applications/month: 500
- API requests per application (submit + status polls + AI Assist turns): ~50 calls/application
- Total Lambda invocations/month: 500 × 50 = **25,000 invocations**
- Well within 1M/month permanent free tier → **$0.00 Lambda request cost**

**Compute (GB-seconds) at 100 users:**
- AI Assist turns: 500 apps × 12 turns × 0.5 GB × 25s = 75,000 GB-sec
- VPR worker: 500 × 1 GB × 90s = 45,000 GB-sec (est. 90s total for 6 stages)
- CV Tailor worker: 500 × 1 GB × 30s = 15,000 GB-sec
- Company Research: 500 × 0.5 GB × 15s = 3,750 GB-sec
- Other handlers: ~10,000 GB-sec
- **Total: ~149,000 GB-sec/month**
- Free tier covers 400,000 GB-sec → **$0.00 compute cost at 100 users**

**Lambda compute becomes non-zero at:** ~2,700 active users (≈ 400,000 GB-sec used)

---

### DynamoDB (On-Demand)

**Tables (from CDK):**
- Users, Sessions, Jobs, Idempotency, LLM Cache
- CVs, Applications, Gap Responses, Knowledge, Artifacts
- Company Research Cache
- **11 tables total**

**DynamoDB costs at 100 users, 500 applications/month:**

| Operation | Count/month | WRU/RRU | Cost |
|-----------|------------|---------|------|
| Application lifecycle (create, update status × 6) | 500 × 7 = 3,500 writes | 3,500 WRU | $0.004 |
| Artifact writes (VPR, CV, CR, CL, IP) | 500 × 5 = 2,500 | 2,500 WRU | $0.003 |
| Gap response writes (10/app) | 5,000 | 5,000 WRU | $0.006 |
| Reads (status polls, AI Assist context) | ~50,000 RRU | 50,000 RRU | $0.013 |
| LLM cache writes/reads | ~5,000 ops | mixed | $0.004 |
| **Total DynamoDB/month at 100 users** | | | **~$0.03** |

**At 1,000 users:** ~$0.30/month
**At 10,000 users:** ~$3.00/month

DynamoDB is negligible at this scale.

---

### S3

**Buckets (from CDK):**
- CVs bucket (user CV uploads — original documents)
- Generated bucket (cover letters, tailored CVs)
- VPR results bucket (VPR JSON artifacts)
- Artifacts bucket
- Outputs, Static, Backups, Logs

**Storage per application:**
- Raw CV document: ~200 KB
- VPR JSON: ~30 KB
- Tailored CV JSON: ~20 KB
- Cover Letter: ~5 KB
- Interview Prep JSON: ~15 KB
- **Total per application: ~270 KB**

| Scale | Applications | S3 Storage | S3 Storage cost/month |
|-------|------------|-----------|----------------------|
| 100 users, 5 apps | 500 apps | 135 MB | $0.003 |
| 1,000 users, 5 apps | 5,000 apps | 1.35 GB | $0.031 |
| 10,000 users, 5 apps | 50,000 apps | 13.5 GB | $0.31 |

**S3 request costs** (PUT on upload, GET on read): ~$0.002/application at current scale = negligible.

---

### API Gateway

| Scale | API calls/month | Cost (no free tier) |
|-------|-----------------|---------------------|
| 100 users | ~25,000 | $0.088 |
| 1,000 users | ~250,000 | $0.875 |
| 10,000 users | ~2,500,000 | $8.75 |

---

### SQS (8 queues)

Each artifact generation involves 1 SQS message send + receive + delete = 3 API calls.

| Scale | Artifact generations/month | SQS calls | Cost |
|-------|--------------------------|-----------|------|
| 100 users | ~2,500 | ~7,500 | Free (< 1M) |
| 1,000 users | ~25,000 | ~75,000 | Free (< 1M) |
| 10,000 users | ~250,000 | ~750,000 | Free (< 1M) |

SQS remains free indefinitely at this scale.

---

### Cognito

Free up to 50,000 MAU. Not a cost factor below that threshold.

---

### Step Functions (Artifact Chain)

State machine for artifact chaining (VPR → CV Tailor → Cover Letter → Interview Prep).

- Transitions per application: ~8–12 state transitions (start, check, success, trigger chain steps)
- At 500 applications/month: 500 × 10 = 5,000 transitions
- Cost: 5,000 / 1,000 × $0.025 = **$0.125/month at 100 users**

---

### CloudWatch Logs

33 Lambda log groups. Lambda Powertools logs JSON structured events.

**Estimated log volume:**
- ~5 log lines per Lambda invocation, ~500 bytes/line
- 25,000 invocations × 5 × 500B = ~62.5 MB/month (100 users)
- Cost: 62.5 MB × $0.50/GB = **$0.031/month**

Grows linearly with users. At 10,000 users: ~$3.10/month.

---

### WAF

$5.00/month fixed Web ACL cost + $1.00/million requests.

**WAF is the largest fixed AWS infrastructure cost**: $5.00/month regardless of user count.

---

## 8. Data Transfer Costs

### Where data transfer occurs:

| Transfer type | Volume per application | Notes |
|--------------|----------------------|-------|
| S3 PUT (CV upload) | ~200 KB | User → S3 via presigned URL. No API Gateway charge. |
| S3 GET (artifact download) | ~70 KB (VPR+CV) | Lambda → S3 (in-region: **free**) |
| API Gateway → Lambda | ~10 KB/request | In-region: **free** |
| Lambda → DynamoDB | ~5 KB/request | In-region: **free** |
| Lambda → Anthropic API | ~50 KB/request (outbound) | Internet egress from Lambda |
| Anthropic API → Lambda | ~30 KB/response (inbound) | Inbound: **free** |
| API Gateway → Client (browser) | ~50 KB/application | Billable egress: $0.09/GB |
| S3 → Browser (direct GET) | ~0 (blocked, private) | Buckets are fully private |

**Primary data transfer cost: API Gateway egress to browser**
- 500 applications/month × 50 KB = 25 MB = $0.002/month at 100 users → negligible.

**Lambda → Anthropic (internet egress):**
- 500 applications × ~50 KB outbound per LLM call × 6 LLM calls = 150 MB
- 150 MB × $0.09/GB = **$0.013/month** at 100 users → negligible.

### Mitigation recommendations (priority order):

1. **CloudFront in front of API Gateway (High value, medium complexity)**
   - Caches GET responses for static/shared content (company research results, VPR status)
   - Reduces API Gateway calls and data transfer
   - Cost: CloudFront is cheaper than API Gateway for high-volume traffic ($0.0085/10,000 requests vs $3.50/million)
   - _No security impact — CloudFront supports WAF, HTTPS, signed URLs_

2. **Keep AI Assist synchronous (already correct)**
   - AI Assist returns responses directly via API Gateway (25s timeout). This avoids S3 round-trip for small payloads.

3. **Compress LLM inputs before logging (Low effort)**
   - CV JSON sent to Anthropic includes full structured data. Stripping `raw_text`, `file_content` fields is already done in `_serialize_cv_for_prompt()` ✅

4. **VPC Endpoint for S3/DynamoDB (Low cost, eliminates egress for internal traffic)**
   - All Lambda→S3 and Lambda→DynamoDB traffic currently goes through the public internet.
   - VPC Endpoints (Gateway type for S3/DynamoDB) are **free** and eliminate any potential NAT Gateway charges if you ever add one.
   - Currently not an issue (no NAT Gateway), but relevant if you add VPC-private infrastructure.

5. **Do NOT add NAT Gateway**
   - NAT Gateway costs $0.045/GB + $0.045/hour. At your scale this would add $30+/month for zero user-visible benefit. Keep Lambda functions outside VPC.

---

## 9. Full Monthly Cost Summary

### At 100 active users (500 applications/month)

| Cost Category | Monthly Cost | Assumptions |
|--------------|-------------|-------------|
| **Anthropic — Mandatory AI per app** | $213.50 | $0.427 × 500 apps |
| **Anthropic — Optional AI (blended)** | $3.00 | $0.006 × 500 apps |
| **Anthropic subtotal** | **$216.50** | |
| **Tavily** | $0.00 | Within 1,000 free searches/month |
| **Lambda compute** | $0.00 | Within 400K GB-sec free tier |
| **DynamoDB** | $0.03 | |
| **S3** | $0.01 | |
| **API Gateway** | $0.09 | |
| **SQS** | $0.00 | Within free tier |
| **Step Functions** | $0.13 | |
| **CloudWatch Logs** | $0.03 | |
| **WAF** | $5.00 | Fixed monthly |
| **Cognito** | $0.00 | < 50K MAU |
| **SSM Parameter Store** | $0.00 | Standard tier |
| **AWS subtotal** | **~$5.30** | |
| **TOTAL** | **~$221.80/month** | |

### Revenue at 100 users ($20/month):
- Monthly revenue: $2,000
- Monthly cost: $221.80
- **Gross margin: 88.9%**

---

### At 500 active users (2,500 applications/month)

| Category | Monthly Cost |
|---------|-------------|
| Anthropic | $1,082.50 |
| Tavily | $10.00 (est. ~500 over free tier) |
| AWS (Lambda still within free) | ~$26.00 |
| WAF | $5.00 |
| **TOTAL** | **~$1,123.50** |

- Revenue: $10,000
- **Gross margin: 88.8%**

---

### At 1,000 active users (5,000 applications/month)

| Category | Monthly Cost |
|---------|-------------|
| Anthropic | $2,165.00 |
| Tavily (Starter plan, est.) | $49.00 |
| Lambda (approaching free tier limit) | ~$8.00 |
| DynamoDB | ~$0.30 |
| Other AWS | ~$55.00 |
| WAF | $5.00 |
| **TOTAL** | **~$2,282.30** |

- Revenue: $20,000
- **Gross margin: 88.6%**

---

### At 5,000 active users (25,000 applications/month)

| Category | Monthly Cost |
|---------|-------------|
| Anthropic | $10,825.00 |
| Tavily (estimate 50K searches) | ~$450 |
| Lambda compute (beyond free) | ~$500 |
| DynamoDB | ~$1.50 |
| API Gateway | ~$87.50 |
| CloudWatch Logs | ~$15.00 |
| Other AWS | ~$30.00 |
| WAF | $5.00 |
| **TOTAL** | **~$11,914** |

- Revenue: $100,000
- **Gross margin: 88.1%**

---

### Gross Margin Summary (for projection graphs)

| Users | Revenue | AI Cost | AWS Cost | Total Cost | Gross Margin |
|-------|---------|---------|---------|-----------|-------------|
| 100 | $2,000 | $216.50 | $5.30 | $221.80 | **88.9%** |
| 500 | $10,000 | $1,082.50 | $41.00 | $1,123.50 | **88.8%** |
| 1,000 | $20,000 | $2,165.00 | $117.30 | $2,282.30 | **88.6%** |
| 5,000 | $100,000 | $10,825.00 | $1,089.00 | $11,914.00 | **88.1%** |
| 10,000 | $200,000 | $21,650.00 | $2,550.00 | $24,200.00 | **87.9%** |

**Margin is stable at ~88–89%.** AWS costs are trivial relative to AI costs at this scale. AI costs scale linearly with applications; the subscription model provides strong margins because the cost-per-application ($0.43) is predictable and stable.

> **Assumption for above:** 5 applications per active user per month. If heavy users submit 20+ applications, the per-user AI cost rises to $8–$9/month vs $20 revenue — still profitable but margin compresses. See sensitivity analysis below.

---

## 10. Sensitivity Analysis: Applications per User

| Apps/user/month | AI cost/user | AWS cost/user | Total cost/user | Revenue/user | Margin |
|----------------|-------------|--------------|----------------|-------------|--------|
| 2 | $0.854 | $0.10 | $0.954 | $20 | **95.2%** |
| 5 | $2.135 | $0.11 | $2.245 | $20 | **88.8%** |
| 10 | $4.270 | $0.12 | $4.390 | $20 | **78.1%** |
| 20 | $8.540 | $0.14 | $8.680 | $20 | **56.6%** |
| 30 | $12.810 | $0.16 | $12.970 | $20 | **35.2%** |

**Key risk:** Power users submitting 20–30 applications/month reduce margins to 35–57%. Consider a soft cap or tiered pricing above 15 applications/month.

---

## 11. Free Tier Boundaries (Post 12-Month Expiry)

| Service | Free tier type | Expires | Current status |
|---------|--------------|---------|---------------|
| Lambda — 1M requests/month | Permanent | Never | Active ✅ |
| Lambda — 400K GB-sec/month | Permanent | Never | Active ✅ |
| DynamoDB — 25 GB storage | Permanent | Never | Active ✅ |
| SQS — 1M requests/month | Permanent | Never | Active ✅ |
| Cognito — 50K MAU | Permanent | Never | Active ✅ |
| S3 — 5 GB storage | 12 months | **Expired** | Paying ❌ |
| API Gateway — 1M calls | 12 months | **Expired** | Paying ❌ |
| CloudWatch — 5 GB logs | 12 months | **Expired** | Paying ❌ |
| CloudWatch — 3 dashboards | 12 months | **Expired** | Paying ❌ |

---

## 12. Hebrew Language Cost Impact

### Why Hebrew increases cost

1. **Token inflation:** Hebrew is written right-to-left in UTF-8. Hebrew characters require 2 bytes each; Anthropic's tokenizer produces ~1.8–2.5× more tokens for equivalent Hebrew text vs English.

2. **Bidirectional text in JSON:** JSON prompts with mixed Hebrew/English (job posting in Hebrew, template labels in English) are particularly token-inefficient.

3. **Output verbosity:** Hebrew output tokens also inflate by the same factor.

### Estimated Hebrew token multiplier: **1.8–2.0×**

| Artifact | English cost | Hebrew cost (est.) | Delta |
|---------|-------------|-------------------|-------|
| Gap Analysis | $0.036 | $0.065–$0.072 | +$0.030 |
| VPR Generation | $0.320 | $0.576–$0.640 | +$0.256 |
| CV Tailoring | $0.018 | $0.032–$0.036 | +$0.015 |
| Cover Letter | $0.005 | $0.009–$0.010 | +$0.004 |
| Interview Prep | $0.013 | $0.023–$0.026 | +$0.011 |
| **Full application** | **$0.427** | **$0.77–$0.86** | **+$0.34–$0.43** |

**A Hebrew user costs ~2× an English user in AI spend.** At $20/month and 5 apps:
- English: $2.245 cost → 88.8% margin
- Hebrew: $4.00 cost → 80.0% margin

Still profitable, but worth monitoring. If you offer Hebrew at the same price, margin compresses ~8 percentage points per Hebrew user.

### Mitigation:
- Use `json.dumps(..., ensure_ascii=False)` to avoid Unicode escape sequences like `א` which inflate token count. (Verify this is already the case — escaped Hebrew characters triple token cost.)
- Consider Hebrew as a premium tier feature if Hebrew user volume grows significantly.

---

## 13. Optimization Recommendations

### Priority 1 (High Impact, Low Effort)

**Migrate Gap Analysis, Cover Letter, Interview Prep to `complete()` with `use_system_cache=True`**

These three artifacts currently use `generate()` which concatenates system+user prompts into one string. Migrating to `complete()` enables Anthropic prompt caching.

- Gap Analysis system prompt: ~350 tokens (below 1,024 cache minimum — add static preamble to reach threshold)
- Cover Letter system prompt: ~300 tokens (same — needs padding to threshold)
- Interview Prep system prompt: ~700 tokens (close — add output format spec to reach threshold)

**Benefit per application:**
- After first invocation within 5-minute cache window (warm Lambda), subsequent requests on same Lambda container pay cache read rate (10% of input).
- At Lambda warming patterns typical for SQS workers, this could save 20–30% of input token costs on these artifacts.
- Estimated savings: $0.002–$0.004 per application at current scale.

---

### Priority 2 (Medium Impact, Low Effort)

**Verify and increase `max_tokens` for Interview Prep**

Current default is 2,500 from `generate()`. 10 STAR answers (150–300 words each) = up to 3,000 tokens of answers alone, before questions-to-ask, salary guidance, and checklist. Output is very likely being truncated.

- Increase to 6,000 tokens
- Cost impact: +$0.014/generation (Haiku is cheap)
- Quality impact: significant improvement

---

### Priority 3 (Medium Impact, Medium Effort)

**Reduce Company Research input token count**

Company Research sends 15,000+ tokens of raw Tavily content to the LLM because `aggregate_search_content()` concatenates all search results verbatim. Options:

a) **Truncate per result:** Limit each Tavily result to 2,000 characters before aggregation. Reduces input from 15,000 to ~6,000 tokens. Saves ~$0.007/generation.

b) **Two-stage approach:** Extract key sentences from each result using a quick regex/heuristic filter before sending to LLM.

c) **Use Tavily's `include_raw_content: false`** and rely on snippet summaries (already shorter). Check if `TavilyClient` is setting this option.

---

### Priority 4 (Low Impact, Low Effort)

**Ensure Hebrew JSON uses `ensure_ascii=False`**

Check all `json.dumps()` calls in prompt builders. Using `ensure_ascii=True` (Python default) converts Hebrew to `\uXXXX` escape sequences, multiplying token count 3×.

---

### Priority 5 (Low Impact, High Effort)

**Stage 3 (Phase 2 VPR) output token cap**

Phase 2 uses `max_tokens=16,000`. In practice, a full VPR JSON is 4,000–6,000 tokens. Reducing `max_tokens` to 8,000 would:
- Cost: no direct saving (billed on actual output, not max_tokens)
- Benefit: reduces Lambda timeout risk (shorter max timeout)
- No action needed unless you observe timeout failures.

---

## 14. Questions for Follow-Up

1. **VPR Stage 4/5/6 max_tokens:** Confirm what values are passed in `_invoke_stage_json()` for stages 1, 2, 4, 5, 6. If they're using the function default of 2,500, stages 4–5 may be truncating the 5,000+ token Phase 2 output.

2. **CV Tailoring field count:** The frontend shows 1 editable RichTextEditor at line 113. Is this the full CV or just one section? If it's the full CV, AI Assist can only rewrite the whole thing — which may not be the intended UX.

3. **AI Assist model override:** `os.environ.get('AI_ASSIST_MODEL', DEFAULT_MODEL)` — confirm AI_ASSIST_MODEL is not set to Sonnet in production CDK config. If it is, AI Assist costs jump 10× per turn.

4. **Tavily plan upgrade threshold:** At 500 searches/month free, you'll hit the Tavily free tier limit at approximately 250 active users submitting one application each. Plan to upgrade to Starter tier at ~200 users.

5. **LLM Response Cache hit rate:** The DynamoDB-backed `LLMResponseCache` caches deterministic responses. For company research, the cache key includes the raw prompt (which varies per company). Cache hit rate is probably low. Consider tracking `AIAssistCacheHit` CloudWatch metric to measure AI Assist cache effectiveness.

6. **Hebrew `ensure_ascii` validation:** Needs a code audit of all `json.dumps()` calls in `logic/prompts/` and `logic/handlers/`.
