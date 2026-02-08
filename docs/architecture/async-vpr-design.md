# Async VPR Generation Architecture Design

**Date:** 2026-02-03
**Status:** Design Complete - Awaiting Implementation Approval
**Architect:** Claude Sonnet 4.5

---

## Executive Summary

**Problem:** VPR generation via Claude Sonnet 4.5 takes 30-60 seconds, causing API Gateway timeout (29s limit).

**Solution:** SQS + Polling pattern with job tracking via DynamoDB.

**Cost:** ~$0.0013 per VPR (77x under $0.10 budget)

**Complexity:** LOW (battle-tested AWS serverless pattern)

---

## Architecture Pattern: SQS + Polling

### Sequence Flow

```
CLIENT → POST /api/vpr → Submit Lambda → SQS Queue
                              ↓
                         DynamoDB (job_id, status: PENDING)
                              ↓
                         202 Accepted {job_id}

CLIENT ← 202 Accepted {job_id}

SQS Queue → Worker Lambda (triggered)
                 ↓
           Update status: PROCESSING
                 ↓
           Call Claude API (30-60s)
                 ↓
           FVS Validation
                 ↓
           Store result in S3
                 ↓
           Update status: COMPLETED

CLIENT → GET /api/vpr/status/{job_id} (poll every 5s)
              ↓
         Status Lambda → DynamoDB
              ↓
         200 OK {status: COMPLETED, result_url: presigned_s3_url}
```

---

## New AWS Resources Required

| Resource | Name | Purpose |
|----------|------|---------|
| SQS Queue | `careervp-vpr-jobs-queue-dev` | Job queue (11-min visibility) |
| SQS DLQ | `careervp-vpr-jobs-dlq-dev` | Dead letter queue |
| DynamoDB Table | `careervp-jobs-table-dev` | Job status tracking (10-min TTL) |
| DynamoDB GSI | `idempotency-key-index` | Duplicate request detection |
| S3 Bucket | `careervp-dev-vpr-results-use1-{hash}` | VPR results (7-day lifecycle) |
| Lambda | `careervp-vpr-submit-lambda-dev` | Submit job (10s timeout) |
| Lambda | `careervp-vpr-worker-lambda-dev` | Process VPR (5min timeout) |
| Lambda | `careervp-vpr-status-lambda-dev` | Status check (10s timeout) |
| API Route | `POST /api/vpr` | Submit endpoint |
| API Route | `GET /api/vpr/status/{job_id}` | Status endpoint |
| CloudWatch Alarm | `careervp-vpr-dlq-alarm-dev` | DLQ messages alert |
| CloudWatch Alarm | `careervp-vpr-worker-errors-alarm-dev` | Worker failures alert |

---

## DynamoDB Jobs Table Schema

**Table:** `careervp-jobs-table-dev`

| Attribute | Type | Purpose |
|-----------|------|---------|
| `job_id` (PK) | String | UUID |
| `idempotency_key` | String | `vpr#{user_id}#{application_id}` |
| `user_id` | String | User identifier |
| `application_id` | String | Application context |
| `status` | String | PENDING/PROCESSING/COMPLETED/FAILED |
| `created_at` | String | ISO timestamp |
| `started_at` | String | ISO timestamp |
| `completed_at` | String | ISO timestamp |
| `input_data` | Map | VPRRequest payload |
| `result_key` | String | S3 object key |
| `error` | String | Error message if failed |
| `token_usage` | Map | Claude API metrics |
| `ttl` | Number | Unix timestamp (10-min auto-cleanup) |

**GSI:** `idempotency-key-index` (PK: `idempotency_key`)

**State Machine:**
```
PENDING → PROCESSING → COMPLETED
                    ↘ FAILED
```

---

## Migration Strategy

### Phase 1: Deploy New Infrastructure (Week 1)
- Deploy SQS queue + DLQ
- Deploy jobs table + GSI
- Deploy S3 results bucket
- Deploy worker Lambda (SQS trigger)
- Deploy status Lambda
- Add status API route

**Risk:** LOW (new resources, no impact on existing)

### Phase 2: Refactor Submit Handler (Week 2)
- Rename: `vpr_handler.py` → `vpr_submit_handler.py`
- Add idempotency check
- Queue job to SQS
- Return 202 Accepted with job_id

**Risk:** MEDIUM (changes existing endpoint)

### Phase 3: Update Frontend (Week 2)
- Implement polling component
- Poll `/api/vpr/status/{job_id}` every 5s
- Show spinner: "Generating your VPR..."
- Timeout after 5 minutes

**Risk:** MEDIUM (UX change)

### Phase 4: Gradual Rollout (Week 3)
- Route 10% traffic → async
- Monitor metrics
- Route 50% traffic → async
- Route 100% traffic → async
- Deprecate synchronous code

**Risk:** LOW (gradual with rollback)

---

## Idempotency Strategy

**Key Format:** `vpr#{user_id}#{application_id}`

**TTL:** 24 hours

**Behavior:**

| Scenario | Response |
|----------|----------|
| New request | Create job, return 202 with job_id |
| Duplicate (PENDING) | Return 200 with existing job_id |
| Duplicate (PROCESSING) | Return 200 with existing job_id |
| Duplicate (COMPLETED) | Return 200 with job_id + result_url |
| Duplicate (after TTL) | Create new job (data expired) |

---

## Security Considerations

### Attack Mitigation

| Attack Vector | Mitigation |
|---------------|------------|
| Job ID enumeration | UUIDv4 (128-bit random) + ownership validation |
| DDoS via submissions | API Gateway throttling (2 req/s, 10 burst) |
| Malicious input | Pydantic validation + input escaping |
| Presigned URL abuse | 1-hour expiry + ownership check |
| Replay attacks | Idempotency key (24h window) |

### Data Protection

| Data | Encryption | Retention |
|------|------------|-----------|
| Jobs table | DynamoDB default (AWS-owned key) | 10 minutes (TTL) |
| VPR results (S3) | S3-Managed (SSE-S3) | 7 days (lifecycle) |
| SQS messages | SQS default | 4 hours |

### IAM Policies (Least Privilege)

**Submit Lambda:**
- `dynamodb:PutItem` on jobs table
- `dynamodb:Query` on GSI (idempotency check)
- `sqs:SendMessage` on queue

**Worker Lambda:**
- `dynamodb:GetItem` on users table (read-only)
- `dynamodb:UpdateItem` on jobs table
- `s3:PutObject` on results bucket
- `ssm:GetParameter` (Anthropic API key)

**Status Lambda:**
- `dynamodb:GetItem` on jobs table (read-only)
- `s3:GetObject` on results bucket (presigned URL generation)

---

## Performance Optimization

### Concurrency Management

| Lambda | Reserved Concurrency | Justification |
|--------|---------------------|---------------|
| Submit | Unreserved | Fast, scales with traffic |
| Worker | **5** | Controls Claude API cost + rate limits |
| Status | Unreserved | Fast, read-only |

### Monitoring Metrics

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| VPR generation time | <60s | >90s (p95) |
| Queue depth | <10 | >50 |
| DLQ messages | 0 | ≥1 |
| Lambda errors | <1% | >5% |
| Cost per VPR | <$0.01 | >$0.05 |

---

## Impact on Downstream Phases

### Phases 9-12 Analysis

**Key Finding:** Only Phase 7 (VPR) needs async pattern.

| Phase | LLM Timeout | Pattern | Reason |
|-------|------------|---------|--------|
| 7 (VPR) | 30-60s | **ASYNC** | Exceeds 29s API Gateway limit |
| 9 (CV Tailor) | <20s | SYNC | Fits within budget |
| 10 (Cover Letter) | <20s | SYNC | Fits within budget |
| 11 (Gap Analysis) | <20s | SYNC | Fits within budget |
| 12 (Interview Prep) | <20s | SYNC | Fits within budget |

### Integration Flow Update

```
BEFORE: CV Upload → VPR (sync, 30-60s) → Gap Analysis

AFTER:  CV Upload → VPR (async, submit 202)
                    ↓
                  Poll status (5s intervals)
                    ↓
                  VPR Complete (200 OK)
                    ↓
                  Gap Analysis (sync)
```

**Frontend UX:** Show "Generating VPR..." spinner before enabling Gap Analysis form.

---

## Cost Analysis

### Per-VPR Cost Breakdown

| Component | Cost |
|-----------|------|
| API Gateway (submit + 10 polls) | $0.000038 |
| SQS (send + receive) | $0.0000008 |
| Lambda (submit, 100ms, 128MB) | $0.000003 |
| Lambda (worker, 5min, 1024MB) | $0.00125 |
| Lambda (status, 10×50ms, 128MB) | $0.00001 |
| DynamoDB (1 write + 10 reads) | $0.000002 |
| S3 (storage + GET) | $0.000001 |
| **Total** | **~$0.0013** |

**Budget Headroom:** 77x under $0.10 target

---

## Alternative Patterns Evaluated

### Step Functions (NOT RECOMMENDED)
- **Cost:** ~$0.0063/VPR (5x higher)
- **Complexity:** MEDIUM (state machine language)
- **Verdict:** Overkill for single-step workflow

### WebSocket (NOT RECOMMENDED for MVP)
- **Cost:** ~$0.0013/VPR (same as SQS)
- **Complexity:** HIGH (client reconnection, state management)
- **Verdict:** Better UX, but not worth complexity for MVP

---

## Implementation Checklist

### CDK Changes
- [ ] Add SQS queue + DLQ to `api_construct.py`
- [ ] Add jobs table + GSI to `api_construct.py`
- [ ] Add S3 results bucket to `api_construct.py`
- [ ] Add worker Lambda with SQS event source
- [ ] Add status Lambda
- [ ] Update API Gateway routes
- [ ] Add CloudWatch alarms (DLQ + errors)

### Backend Code
- [ ] Create `vpr_submit_handler.py` (refactor from `vpr_handler.py`)
- [ ] Create `vpr_worker_handler.py` (move VPR generation logic)
- [ ] Create `vpr_status_handler.py` (new status endpoint)
- [ ] Create `dal/jobs_repository.py` (job CRUD operations)
- [ ] Update `models/vpr.py` (add job_id field to response)

### Tests
- [ ] Unit tests: idempotency logic
- [ ] Unit tests: job CRUD operations
- [ ] Unit tests: status transitions
- [ ] Integration tests: submit → worker → status flow
- [ ] Load tests: 100 concurrent submissions
- [ ] Failure tests: worker crashes, SQS retries, DLQ

### Frontend
- [ ] Create `VPRStatusPoller.tsx` component
- [ ] Update VPR submission flow (handle 202 response)
- [ ] Add polling logic (5s intervals, 5min timeout)
- [ ] Update UX: show spinner "Generating VPR..."
- [ ] Add error handling: timeout, failed status

### Deployment
- [ ] Deploy to dev environment
- [ ] Smoke tests
- [ ] Gradual rollout (10% → 50% → 100%)
- [ ] Monitor metrics
- [ ] Deprecate synchronous code

### Documentation
- [ ] Update `plan.md` (Phase 7 tasks)
- [ ] Update `PROGRESS.md`
- [ ] Create migration guide for team

---

## Questions & Considerations

### Operational
1. **Q: What if Claude API is down >10 minutes?**
   - **A:** Jobs fail after 3 retries → DLQ → CloudWatch alarm → Manual reprocessing

2. **Q: How prevent hundreds of duplicate requests?**
   - **A:** Idempotency key + API Gateway rate limiting per user_id

3. **Q: What if S3 result deleted before client polls?**
   - **A:** Return 410 Gone "Result expired, please regenerate"

### Design
4. **Q: Should we batch VPR jobs?**
   - **A:** NO. Each takes 30-60s, batching would hit 15-min Lambda limit

5. **Q: Should we use Lambda Powertools Idempotency?**
   - **A:** YES for Submit Lambda. NO for Worker (SQS handles it)

---

## Next Steps

1. **Stakeholder Approval** - Review this design
2. **Spike** - Deploy infrastructure to dev (1 day)
3. **Implementation** - 2 weeks (backend + frontend)
4. **Testing** - 1 week (load + failure tests)
5. **Rollout** - 1 week (gradual traffic shift)

---

## Research Sources

This architecture was designed using parallel research orchestration with 5 concurrent scientist agents:
- Stage 1 (Haiku): Extracted Phases 9-12 dependencies from plan.md
- Stage 2 (Haiku): Analyzed project constraints (CLAUDE.md, .clauderules)
- Stage 3 (Sonnet): Inventoried existing infrastructure (DynamoDB, Lambda, S3)
- Stage 4 (Sonnet): Analyzed current synchronous VPR implementation
- Stage 5 (Opus): Compared async patterns (SQS vs Step Functions vs WebSocket)

---

## Approval Status

- [ ] Architecture approved by stakeholder
- [ ] Ready for implementation
- [ ] Assigned to: _____________
- [ ] Target completion: _____________

---

**Document Version:** 1.0
**Last Updated:** 2026-02-03
**Author:** Claude Sonnet 4.5 (Architect)
