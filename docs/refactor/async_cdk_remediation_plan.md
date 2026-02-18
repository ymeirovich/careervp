# CDK Remediation Plan: Async Architecture & Missing Resources

## Executive Summary

This document outlines the CDK infrastructure changes required to support all 27 API endpoints in the CareerVP OpenAPI specification. The current CDK deployment only supports 5 endpoints (users, auth, jobs, health), leaving 22 endpoints without the required DynamoDB tables, S3 buckets, and async processing resources.

---

## Part 1: Missing Async Resources

### Current State Analysis

| Resource Category | Currently Deployed | Missing |
|-----------------|-------------------|---------|
| DynamoDB Tables | 4 (users, idempotency, jobs, llm-cache) | 8 (cvs, applications, gap-responses, knowledge, artifacts, subscriptions, sessions, company-research-cache) |
| S3 Buckets | 2 (cv-uploads, vpr-results) | 3 (static, backups, logs) |
| Worker Lambdas | 0 | 4+ (per async feature) |
| SQS Queues | 0 | 4+ (per async feature) |
| Event Triggers | Partial | Complete |

### Async Patterns Required

#### Pattern A: DynamoDB Streams → Worker Lambda
Used for: VPR generation, CV tailoring, Cover Letter, Interview Prep
- Job created in jobs-table with status=PENDING
- DynamoDB Streams triggers Worker Lambda
- Worker updates status to PROCESSING → COMPLETED/FAILED

#### Pattern B: SQS Queue → Worker Lambda
Used for: Gap Analysis, CV Upload processing
- Job submitted to SQS queue
- Worker Lambda polls SQS
- Results stored in artifacts-table

#### Pattern C: S3 Event → Worker Lambda
Used for: CV file processing
- File uploaded to S3 bucket
- S3 event triggers Lambda
- Metadata stored in cvs-table

---

## Part 2: Recommended Approach

### Option: Add to ApiDbConstruct (Recommended)

Follow existing pattern in `api_db_construct.py` using TableV2 API with full features:
- PAY_PER_REQUEST billing
- PITR (7 days dev, 35 days prod)
- TTL where applicable
- Contributor Insights
- GSIs where needed

---

## Part 3: Files to Modify

### 1. `infra/careervp/api_db_construct.py`
- Add: cvs_table, applications_table, gap_responses_table, knowledge_table, artifacts_table
- Add S3 buckets: static-{env}, backups-{env}, logs-{env}
- Update Lambda environment variables to reference new tables

### 2. `infra/careervp/constants.py`
- Add missing table name constants

### 3. `infra/careervp/naming_utils.py`
- Verify bucket naming supports all required buckets

### 4. `infra/careervp/api_construct.py`
- Add Worker Lambda functions for async processing
- Add SQS queues for async job processing
- Configure event triggers (DynamoDB Streams, S3 events)

---

## Part 4: Implementation Steps

### Step 1: Add DynamoDB Tables to ApiDbConstruct

Add 5 new tables following existing pattern:

```python
# Add after llm_cache_table definition
self.cvs_table = self._build_cvs_table(id_)
self.applications_table = self._build_applications_table(id_)
self.gap_responses_table = self._build_gap_responses_table(id_)
self.knowledge_table = self._build_knowledge_table(id_)
self.artifacts_table = self._build_artifacts_table(id_)
```

Each table method follows the pattern:
- Use `dynamodb.TableV2`
- PAY_PER_REQUEST billing
- PITR enabled
- TTL field (expiration) for applicable tables
- GSIs where needed

### Step 2: Grant Lambda Access

Update IAM permissions in each Lambda definition:
- Add table ARN to `iam.PolicyStatement` resources
- Update environment variables

### Step 3: Add Missing S3 Buckets

Add 3 missing buckets:
- `static-{env}` - Frontend assets (SPA)
- `backups-{env}` - Database backups
- `logs-{env}` - CloudWatch log archive

### Step 4: Add Worker Lambdas

Create worker Lambda functions:
- `vpr-worker` - Processes VPR generation
- `cv-tailor-worker` - Processes CV tailoring
- `cover-letter-worker` - Processes cover letter generation
- `interview-prep-worker` - Processes interview prep generation

### Step 5: Add SQS Queues

Create SQS queues for async processing:
- `cv-upload-queue` - CV file processing
- `gap-analysis-queue` - Gap analysis processing

### Step 6: Configure Event Triggers

- Enable DynamoDB Streams on job tables
- Configure S3 event notifications on cv-uploads bucket

### Step 7: Verify CDK Synthesis

```bash
cd infra && uv sync && cdk synth
```

### Step 8: Run Tests

```bash
cd infra && uv run pytest tests/infrastructure/test_cdk.py -v
```

---

## Part 5: Critical Files

| File | Purpose |
|------|---------|
| `infra/careervp/api_db_construct.py` | Main file - table/bucket definitions |
| `infra/careervp/constants.py` | Table/bucket name constants |
| `infra/careervp/naming_utils.py` | Naming utilities |
| `infra/careervp/api_construct.py` | Lambda definitions, event triggers |
| `docs/refactor/specs/prompt_optimization_cdk_spec.yaml` | Compliance rules |

---

## Part 6: Endpoint-to-Resource Mapping (27 Endpoints)

### Sync Endpoints (15)

| # | Endpoint | Method | DynamoDB Tables | S3 Buckets | Lambda |
|---|---------|--------|----------------|------------|--------|
| 1 | `/api/auth/register` | POST | users-table, idempotency-table | - | auth-lambda |
| 2 | `/api/auth/login` | POST | users-table | - | auth-lambda |
| 3 | `/api/auth/refresh` | POST | users-table | - | auth-lambda |
| 4 | `/api/users/me` | GET | users-table | - | user-lambda |
| 5 | `/api/users/me` | PUT | users-table | - | user-lambda |
| 6 | `/api/jobs` | POST | jobs-table, idempotency-table | - | job-create-lambda |
| 7 | `/api/jobs` | GET | jobs-table | - | job-list-lambda |
| 8 | `/api/jobs/{id}` | GET | jobs-table | - | job-get-lambda |
| 9 | `/api/cvs` | GET | cvs-table | - | cv-list-lambda |
| 10 | `/api/vpr` | GET | vpr-jobs-table, artifacts-table | - | vpr-list-lambda |
| 11 | `/api/gap-analysis/questions` | GET | gap-responses-table | - | gap-questions-lambda |
| 12 | `/api/cv-tailoring` | GET | artifacts-table | - | cv-tailor-list-lambda |
| 13 | `/api/cover-letter` | GET | artifacts-table | - | cover-letter-list-lambda |
| 14 | `/api/company-research/{id}` | GET | company-research-cache-table | - | company-research-get-lambda |
| 15 | `/api/health` | GET | - | - | - |

### Async Endpoints (12)

| # | Endpoint | Method | Submitter Lambda | Jobs Table | Worker Lambda | Result Table | S3 Bucket |
|---|---------|--------|-----------------|------------|---------------|--------------|-----------|
| 16 | `/api/cvs/upload` | POST | cv-upload-lambda | cvs-table | cv-upload-worker | cvs-table | cv-uploads |
| 17 | `/api/vpr/generate` | POST | vpr-submit-lambda | vpr-jobs-table | vpr-worker | artifacts-table | - |
| 18 | `/api/vpr/{id}` | GET | - | vpr-jobs-table | - | artifacts-table | - |
| 19 | `/api/gap-analysis/generate` | POST | gap-generate-lambda | gap-responses-table | gap-worker | gap-responses-table | - |
| 20 | `/api/gap-analysis/submit` | POST | gap-submit-lambda | gap-responses-table | gap-worker | gap-responses-table | - |
| 21 | `/api/cv-tailoring/generate` | POST | cv-tailor-lambda | artifacts-table | cv-tailor-worker | artifacts-table | - |
| 22 | `/api/cv-tailoring/{id}` | GET | - | artifacts-table | - | artifacts-table | - |
| 23 | `/api/cover-letter/generate` | POST | cover-letter-lambda | artifacts-table | cover-letter-worker | artifacts-table | - |
| 24 | `/api/cover-letter/{id}` | GET | - | artifacts-table | - | artifacts-table | - |
| 25 | `/api/interview-prep/generate` | POST | interview-prep-lambda | artifacts-table | interview-prep-worker | artifacts-table | - |
| 26 | `/api/interview-prep/{id}` | GET | - | artifacts-table | - | artifacts-table | - |
| 27 | `/api/company-research/fetch` | POST | company-research-lambda | company-research-cache-table | - | company-research-cache-table | - |

---

## Part 7: E2E Workflow Diagrams

### Sync Workflow: POST /api/jobs

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────┐
│  Client  │────▶│  API Gateway │────▶│ Job Create   │────▶│  jobs      │
│          │     │              │     │   Lambda     │     │   table    │
└──────────┘     └──────────────┘     └──────────────┘     └─────┬──────┘
                                                                  │
                                                                  ▼
                                                         ┌────────────┐
                                                         │  Response   │
                                                         │  {jobId}    │
                                                         └────────────┘
```

### Async Workflow: POST /api/vpr/generate

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────┐
│  Client  │────▶│  API Gateway │────▶│ VPR Submit   │────▶│  vpr_jobs  │
│          │     │              │     │   Lambda     │     │   table    │
└──────────┘     └──────────────┘     └──────┬───────┘     └─────┬──────┘
                                              │                   │
                                              ▼                   │ DynamoDB
                                     ┌──────────────┐           │   Streams
                                     │  Response    │           │
                                     │  {jobId,     │           ▼
                                     │   status:    │     ┌────────────┐
                                     │   PENDING}   │     │  VPR Worker │
                                     └──────────────┘     │   Lambda   │
                                                           └──────┬─────┘
                                                                  │
                                                                  ▼
                                                         ┌────────────┐
                                                         │  artifacts  │
                                                         │   table    │
                                                         └────────────┘
                                                                  │
                                                                  ▼
                                                         ┌────────────┐
                                                         │  GET /vpr/ │
                                                         │    {id}    │
                                                         │  returns   │
                                                         │  result    │
                                                         └────────────┘
```

### Async Workflow: POST /api/cvs/upload

```
┌──────────┐     ┌──────────┐     ┌────────────┐     ┌──────────┐
│  Client  │────▶│   S3     │────▶│  S3 Event  │────▶│   CV     │
│ (upload) │     │ (bucket) │     │  Bridge    │     │  Worker  │
└──────────┘     └──────────┘     └──────┬─────┘     └────┬─────┘
                                          │                │
                                          ▼                ▼
                                   ┌────────────┐     ┌──────────┐
                                   │  Response  │     │  cvs     │
                                   │  {upload}  │     │  table   │
                                   └────────────┘     └──────────┘
```

---

## Part 8: Resource Relationships Table

### DynamoDB Tables

| Table | PK | SK | GSI | TTL | Used By Endpoints |
|-------|----|----|-----|-----|-------------------|
| users-table | userId | - | email-index | - | 1,2,3,4,5 |
| idempotency-table | idempotencyKey | - | - | 24h | 16,17,19,20,21,23,25 |
| jobs-table | jobId | - | status-index | - | 6,7,8 |
| vpr-jobs-table | jobId | - | status-index | - | 17,18 |
| cvs-table | userId | cvId | - | - | 9,16 |
| gap-responses-table | userId | questionId | - | - | 19,20,21 |
| artifacts-table | applicationId | artifactId | type-index | - | 18,22,24,26 |
| knowledge-table | userEmail | knowledgeType | entity-index | 365d | (future) |
| llm-cache-table | cacheKey | - | - | 30d | (all LLM calls) |
| company-research-cache-table | cacheKey | - | - | 30d | 27 |

### S3 Buckets

| Bucket | Purpose | Versioning | Lifecycle | Used By |
|--------|---------|------------|-----------|---------|
| cv-uploads-{env} | Original CV files | No | 90d → IA, 365d → Glacier | 16 |
| vpr-results-{env} | VPR JSON results | Yes | 7d | 17,18 |
| artifacts-{env} | Generated documents | Yes | 90d → IA, 180d → Glacier | 22,24,26 |
| static-{env} | Frontend SPA | - | None | (frontend) |
| backups-{env} | DB backups | Yes | 30d → IA, 90d → Glacier | (ops) |
| logs-{env} | CloudWatch archives | Yes | 180d → IA, 365d → Glacier | (ops) |

### Lambda Functions

| Lambda | Type | Trigger | Tables Accessed | S3 Accessed |
|--------|------|---------|-----------------|-------------|
| auth-lambda | API | API GW | users-table, idempotency-table | - |
| user-lambda | API | API GW | users-table | - |
| job-create-lambda | API | API GW | jobs-table, idempotency-table | - |
| job-list-lambda | API | API GW | jobs-table | - |
| job-get-lambda | API | API GW | jobs-table | - |
| cv-list-lambda | API | API GW | cvs-table | - |
| cv-upload-lambda | API | API GW | cvs-table, idempotency-table | cv-uploads |
| cv-upload-worker | Worker | S3 Event | cvs-table | cv-uploads |
| vpr-submit-lambda | API | API GW | vpr-jobs-table, idempotency-table | - |
| vpr-worker | Worker | DynamoDB Streams | vpr-jobs-table, artifacts-table | vpr-results |
| vpr-status-lambda | API | API GW | vpr-jobs-table, artifacts-table | - |
| gap-generate-lambda | API | API GW | gap-responses-table, idempotency-table | - |
| gap-submit-lambda | API | API GW | gap-responses-table | - |
| gap-questions-lambda | API | API GW | gap-responses-table | - |
| cv-tailor-lambda | API | API GW | cvs-table, artifacts-table, idempotency-table | - |
| cv-tailor-worker | Worker | DynamoDB Streams | cvs-table, artifacts-table | - |
| cover-letter-lambda | API | API GW | applications-table, artifacts-table, idempotency-table | - |
| cover-letter-worker | Worker | DynamoDB Streams | applications-table, artifacts-table | - |
| interview-prep-lambda | API | API GW | applications-table, artifacts-table, idempotency-table | - |
| interview-prep-worker | Worker | DynamoDB Streams | applications-table, artifacts-table | - |
| company-research-lambda | API | API GW | company-research-cache-table | - |

### API Gateway Routes

| Method | Path | Auth | Integration | Async? |
|--------|------|------|-------------|--------|
| POST | /api/auth/register | None | auth-lambda | No |
| POST | /api/auth/login | None | auth-lambda | No |
| POST | /api/auth/refresh | JWT | auth-lambda | No |
| GET | /api/users/me | JWT | user-lambda | No |
| PUT | /api/users/me | JWT | user-lambda | No |
| POST | /api/jobs | JWT | job-create-lambda | No |
| GET | /api/jobs | JWT | job-list-lambda | No |
| GET | /api/jobs/{id} | JWT | job-get-lambda | No |
| POST | /api/cvs/upload | JWT | cv-upload-lambda | Yes |
| GET | /api/cvs | JWT | cv-list-lambda | No |
| POST | /api/vpr/generate | JWT | vpr-submit-lambda | Yes |
| GET | /api/vpr/{id} | JWT | vpr-status-lambda | Yes |
| GET | /api/vpr | JWT | vpr-list-lambda | No |
| POST | /api/gap-analysis/generate | JWT | gap-generate-lambda | Yes |
| POST | /api/gap-analysis/submit | JWT | gap-submit-lambda | Yes |
| GET | /api/gap-analysis/questions | JWT | gap-questions-lambda | No |
| POST | /api/cv-tailoring/generate | JWT | cv-tailor-lambda | Yes |
| GET | /api/cv-tailoring/{id} | JWT | cv-tailor-status-lambda | Yes |
| GET | /api/cv-tailoring | JWT | cv-tailor-list-lambda | No |
| POST | /api/cover-letter/generate | JWT | cover-letter-lambda | Yes |
| GET | /api/cover-letter/{id} | JWT | cover-letter-status-lambda | Yes |
| GET | /api/cover-letter | JWT | cover-letter-list-lambda | No |
| POST | /api/interview-prep/generate | JWT | interview-prep-lambda | Yes |
| GET | /api/interview-prep/{id} | JWT | interview-prep-status-lambda | Yes |
| POST | /api/company-research/fetch | JWT | company-research-lambda | No |
| GET | /api/company-research/{id} | JWT | company-research-get-lambda | No |
| GET | /api/health | None | - | No |

---

## Part 9: Verification

1. **CDK Synth**: `cdk synth` completes without errors
2. **Table Count**: Test expects 4 tables - update to 9
3. **Bucket Count**: Verify all 6 buckets created
4. **Lambda Count**: Verify all 21 Lambda functions created
5. **Integration Tests**: Run smoke tests for all 27 endpoints

---

## Part 10: Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| Add to ApiDbConstruct | Single stack, simpler, follows existing pattern | Larger stack |
| Activate DynamoDBStack | Decoupled, can update independently | More complex, not currently imported |
| Create new stack | Maximum decoupling | Most complex, more operational overhead |

**Recommendation**: Add to ApiDbConstruct for simplicity - aligns with existing pattern and matches how ServiceStack currently works.
