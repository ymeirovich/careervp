# Feature Spec: VPR Async Architecture (F-INFRA-007)

## Objective

Transition VPR generation from synchronous to asynchronous execution to resolve API Gateway 29-second timeout constraint. VPR generation via Claude Sonnet 4.5 takes 30-60 seconds, exceeding the synchronous API Gateway limit.

## Problem Statement

**Current State:**
- Client POSTs to `/api/vpr` → Lambda generates VPR (30-60s) → API Gateway timeout at 29s → Client receives 504 Gateway Timeout

**Root Cause:**
- Claude Sonnet 4.5 VPR generation: 30-60 seconds
- API Gateway timeout limit: 29 seconds (hard limit)
- Lambda timeout: 120 seconds (sufficient, but API Gateway fails first)

**Impact:**
- 100% failure rate for VPR generation in production
- Poor user experience (timeout errors)
- Wasted Lambda execution time + Claude API cost on failed requests

## Solution: SQS + Polling Pattern

### Architecture Pattern

**Asynchronous Job Queue with Status Polling**

```
Client → POST /api/vpr → Submit Lambda → SQS Queue → 202 Accepted {job_id}
                              ↓
                         DynamoDB (status: PENDING)

SQS Queue → Worker Lambda → Claude API (30-60s) → S3 Result
                 ↓
            DynamoDB (status: COMPLETED)

Client → GET /api/vpr/status/{job_id} → Status Lambda → 200 OK {result_url}
```

### Why This Pattern?

**Alternative Patterns Evaluated:**

| Pattern | Cost/VPR | Complexity | Verdict |
|---------|----------|------------|---------|
| **SQS + Polling** | $0.0013 | LOW | ✅ SELECTED |
| Step Functions | $0.0063 | MEDIUM | ❌ 5x cost, overkill |
| WebSocket | $0.0013 | HIGH | ❌ Complex client, not worth MVP |

**Selection Rationale:**
- Lowest operational complexity (battle-tested AWS pattern)
- Most cost-effective ($0.0013/VPR vs $0.10 budget = 77x headroom)
- Perfect fit with existing DynamoDB + S3 stack
- Progressive enhancement path (can add WebSocket later if needed)

## Technical Details

### New AWS Resources

| Resource | Name | Purpose | Cost/VPR |
|----------|------|---------|----------|
| SQS Queue | `careervp-vpr-jobs-queue-dev` | Job queue | $0.0000008 |
| SQS DLQ | `careervp-vpr-jobs-dlq-dev` | Failed job handling | $0 (only on failure) |
| DynamoDB Table | `careervp-jobs-table-dev` | Job status tracking | $0.000002 |
| DynamoDB GSI | `idempotency-key-index` | Duplicate detection | Included above |
| S3 Bucket | `careervp-dev-vpr-results-use1-{hash}` | VPR result storage | $0.000001 |
| Lambda | `careervp-vpr-submit-lambda-dev` | Submit endpoint | $0.000003 |
| Lambda | `careervp-vpr-worker-lambda-dev` | VPR generation worker | $0.00125 |
| Lambda | `careervp-vpr-status-lambda-dev` | Status check endpoint | $0.00001 |
| API Route | `POST /api/vpr` | Submit job | $0.0000035 |
| API Route | `GET /api/vpr/status/{job_id}` | Check status | $0.000035 |

**Total Cost:** ~$0.0013 per VPR (77x under $0.10 budget)

### Infrastructure Configuration

**SQS Queue:**
- Visibility timeout: 660 seconds (11 minutes = 2× worker timeout)
- Receive message wait time: 20 seconds (long polling)
- Retention period: 4 hours
- Dead letter queue: Max 3 retries

**DynamoDB Jobs Table:**
- Partition key: `job_id` (UUID)
- GSI: `idempotency_key` (for duplicate detection)
- TTL: 10 minutes (auto-cleanup completed/failed jobs)
- Billing mode: Pay-per-request

**S3 Results Bucket:**
- Encryption: S3-Managed (SSE-S3)
- Lifecycle: Delete after 7 days
- Block public access: ALL

**Lambda Configuration:**

| Lambda | Timeout | Memory | Concurrency | Purpose |
|--------|---------|--------|-------------|---------|
| Submit | 10s | 256 MB | Unreserved | Fast job creation |
| Worker | 300s (5min) | 1024 MB | **5 (reserved)** | Claude API call + FVS |
| Status | 10s | 256 MB | Unreserved | Read-only status check |

**Worker Concurrency Justification:**
- Reserved concurrency = 5 limits parallel Claude API calls
- Controls cost (max $0.065/minute at peak)
- Respects Claude API rate limits (Tier 2: 4,000 TPM)
- Each VPR consumes ~3,700 tokens → ~1 VPR/minute without queueing

## API Contract

### Submit VPR Job

**Endpoint:** `POST /api/vpr`

**Request:**
```json
{
  "application_id": "app-uuid-123",
  "user_id": "user-uuid-456",
  "job_posting": {
    "company_name": "Natural Intelligence",
    "role_title": "Learning & Development Manager",
    "responsibilities": ["..."],
    "requirements": ["..."]
  },
  "gap_responses": [
    {"question": "...", "answer": "..."}
  ]
}
```

**Response (New Request):**
```json
{
  "statusCode": 202,
  "body": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "PENDING",
    "message": "VPR generation job submitted successfully"
  }
}
```

**Response (Duplicate Request - Idempotent):**
```json
{
  "statusCode": 200,
  "body": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "PROCESSING" | "COMPLETED" | "FAILED",
    "message": "Job already exists"
  }
}
```

**Idempotency Key:** `vpr#{user_id}#{application_id}`
- Prevents duplicate VPR generation for same application
- TTL: 24 hours (allows regeneration after 1 day)

---

### Check Job Status

**Endpoint:** `GET /api/vpr/status/{job_id}`

**Response (PENDING/PROCESSING):**
```json
{
  "statusCode": 202,
  "body": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "PENDING" | "PROCESSING",
    "created_at": "2026-02-03T13:05:32Z",
    "started_at": "2026-02-03T13:05:35Z"
  }
}
```

**Response (COMPLETED):**
```json
{
  "statusCode": 200,
  "body": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "COMPLETED",
    "created_at": "2026-02-03T13:05:32Z",
    "completed_at": "2026-02-03T13:06:12Z",
    "result_url": "https://s3.presigned.url/results/550e8400.json?expires=3600",
    "token_usage": {
      "input_tokens": 7500,
      "output_tokens": 2200
    }
  }
}
```

**Response (FAILED):**
```json
{
  "statusCode": 200,
  "body": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "FAILED",
    "error": "Claude API rate limit exceeded",
    "created_at": "2026-02-03T13:05:32Z",
    "started_at": "2026-02-03T13:05:35Z"
  }
}
```

**Response (NOT FOUND):**
```json
{
  "statusCode": 404,
  "body": {
    "error": "Job not found (may have expired after 10 minutes)"
  }
}
```

---

## Data Schema

### DynamoDB Jobs Table

**Table Name:** `careervp-jobs-table-dev`

**Schema:**

| Attribute | Type | Purpose | Example |
|-----------|------|---------|---------|
| `job_id` (PK) | String | Unique job identifier | `"550e8400-e29b-41d4-a716-446655440000"` |
| `idempotency_key` | String | Deduplication key | `"vpr#user_123#application_456"` |
| `user_id` | String | User who submitted job | `"user_123"` |
| `application_id` | String | Application context | `"application_456"` |
| `status` | String | Job state | `"PENDING"` \| `"PROCESSING"` \| `"COMPLETED"` \| `"FAILED"` |
| `created_at` | String | ISO timestamp | `"2026-02-03T13:05:32Z"` |
| `started_at` | String | ISO timestamp | `"2026-02-03T13:05:35Z"` |
| `completed_at` | String | ISO timestamp | `"2026-02-03T13:06:12Z"` |
| `input_data` | Map | VPRRequest payload | `{job_posting, gap_responses, ...}` |
| `result_key` | String | S3 object key | `"results/550e8400.json"` |
| `error` | String | Error message if failed | `"Claude API rate limit exceeded"` |
| `token_usage` | Map | Claude API metrics | `{input: 2500, output: 1200}` |
| `ttl` | Number | Unix timestamp for auto-deletion | `1738598400` (10 min from creation) |

**GSI:** `idempotency-key-index`
- Partition key: `idempotency_key`
- Projection: ALL
- Purpose: Fast duplicate request detection

**State Machine:**
```
PENDING → PROCESSING → COMPLETED
                    ↘ FAILED
```

---

## Security & Data Protection

### Attack Surface Mitigation

| Attack Vector | Mitigation Strategy |
|---------------|---------------------|
| **Job ID Enumeration** | UUIDv4 (128-bit random). Validate user_id ownership before returning status. |
| **Idempotency Key Collision** | Hash `user_id + application_id + timestamp`. Ownership validation. |
| **DDoS via Job Submission** | API Gateway throttling (2 req/s per user, 10 burst). CloudWatch alarm on queue depth >100. |
| **Malicious Input Injection** | Pydantic validation. Escape user input before Claude API call. |
| **S3 Presigned URL Abuse** | 1-hour expiration. Validate user_id ownership before generating URL. |
| **SQS Message Tampering** | Worker validates message schema. Reject invalid payloads. |
| **Replay Attacks** | Idempotency key prevents duplicate processing within 24h. |

### Data Protection

**Encryption:**
- **In-Transit:** TLS 1.2 for all API calls, DynamoDB access, S3 access
- **At-Rest:**
  - DynamoDB: AWS-owned key (default)
  - S3: S3-Managed encryption (SSE-S3)
  - SQS: AWS-owned key (default)

**Data Retention:**
- Jobs table: 10 minutes (TTL auto-deletion)
- S3 results: 7 days (lifecycle policy)
- SQS messages: 4 hours
- Idempotency records: 24 hours

**Access Control (IAM Least Privilege):**
- Submit Lambda: Write to jobs table + SQS
- Worker Lambda: Read users table, write jobs table + S3
- Status Lambda: Read-only jobs table + S3 (presigned URL generation)

---

## Performance & Monitoring

### Key Metrics

| Metric | Target | Alert Threshold | Purpose |
|--------|--------|----------------|---------|
| VPR Generation Time | <60s | >90s (p95) | Worker performance |
| Queue Depth | <10 | >50 | Backlog detection |
| DLQ Messages | 0 | ≥1 | Failure alert |
| Lambda Errors (Worker) | <1% | >5% | Worker stability |
| API Gateway 4xx | <2% | >10% | Client errors |
| API Gateway 5xx | <0.1% | >1% | Server errors |
| Cost per VPR | <$0.01 | >$0.05 | Budget control |

### CloudWatch Alarms

1. **DLQ Alarm:** Triggers when DLQ has ≥1 message
2. **Worker Errors Alarm:** Triggers when worker error rate >5% over 5 minutes
3. **Queue Depth Alarm:** Triggers when queue depth >50

---

## Frontend Integration

### Polling Pattern

**Client Flow:**

1. Submit VPR job → Receive `202 Accepted` with `job_id`
2. Poll `/api/vpr/status/{job_id}` every 5 seconds
3. Continue polling until status = `COMPLETED` or `FAILED`
4. Max polling duration: 5 minutes (60 polls × 5 seconds)
5. If timeout, show: "VPR generation is taking longer than expected. Please try again."

**UX States:**

| Status | UI Display |
|--------|------------|
| PENDING | 🟡 "VPR generation queued..." |
| PROCESSING | 🔵 "Generating your personalized Value Proposition Report..." |
| COMPLETED | ✅ "VPR complete! Fetching results..." |
| FAILED | ❌ "Unable to generate report. Please try again." |
| TIMEOUT (>5 min) | ⏱️ "Generation is taking longer than expected. Please check back later." |

**React Component Example:**

```typescript
// VPRStatusPoller.tsx
interface VPRPollerProps {
  jobId: string;
  onComplete: (resultUrl: string) => void;
  onError: (error: string) => void;
}

export function VPRStatusPoller({ jobId, onComplete, onError }: VPRPollerProps) {
  const [status, setStatus] = useState<VPRStatus | null>(null);
  const [pollingCount, setPollingCount] = useState(0);

  useEffect(() => {
    const poll = async () => {
      if (pollingCount >= 60) {  // 5 minutes max
        onError('VPR generation timeout. Please try again.');
        return;
      }

      const response = await fetch(`/api/vpr/status/${jobId}`);
      const data = await response.json();
      setStatus(data);

      if (data.status === 'COMPLETED') {
        onComplete(data.result_url);
      } else if (data.status === 'FAILED') {
        onError(data.error);
      } else {
        setPollingCount(prev => prev + 1);
        setTimeout(poll, 5000);  // Poll every 5 seconds
      }
    };

    poll();
  }, [jobId, pollingCount]);

  return <div className="vpr-status">{/* Status UI */}</div>;
}
```

---

## Migration Strategy

### Phase 1: Deploy Infrastructure (Week 1)

**Goal:** Deploy async resources without impacting existing synchronous endpoint.

- [ ] Deploy SQS queue + DLQ
- [ ] Deploy `careervp-jobs-table-dev` with GSI
- [ ] Deploy S3 results bucket
- [ ] Deploy worker Lambda (SQS event source)
- [ ] Deploy status Lambda
- [ ] Add `GET /api/vpr/status/{job_id}` API route
- [ ] Deploy CloudWatch alarms

**Verification:**
```bash
# Verify resources exist
aws sqs get-queue-url --queue-name careervp-vpr-jobs-queue-dev
aws dynamodb describe-table --table-name careervp-jobs-table-dev
aws s3 ls s3://careervp-dev-vpr-results-use1-*
```

**Risk:** LOW (new resources, no impact on existing endpoint)

---

### Phase 2: Refactor Submit Handler (Week 2)

**Goal:** Convert `POST /api/vpr` from synchronous to asynchronous.

- [ ] Rename `vpr_handler.py` → `vpr_submit_handler.py`
- [ ] Implement idempotency check (query GSI by `idempotency_key`)
- [ ] Create job record in `jobs-table-dev` (status: PENDING)
- [ ] Send message to SQS queue
- [ ] Return `202 Accepted` with `job_id`
- [ ] Move VPR generation logic to `vpr_worker_handler.py`

**Verification:**
```bash
# Test submit endpoint
curl -X POST /api/vpr -d '{"application_id": "test", "user_id": "test", ...}'
# Expected: 202 Accepted with job_id

# Test duplicate request
curl -X POST /api/vpr -d '{"application_id": "test", "user_id": "test", ...}'
# Expected: 200 OK with existing job_id
```

**Risk:** MEDIUM (modifies existing endpoint, requires frontend update)

**Rollback Plan:** Keep synchronous handler in separate Lambda, route traffic via API Gateway

---

### Phase 3: Frontend Polling (Week 2)

**Goal:** Update frontend to async polling pattern.

- [ ] Create `VPRStatusPoller.tsx` component
- [ ] Update VPR submission flow to handle `202 Accepted`
- [ ] Implement polling logic (5s intervals, 5min timeout)
- [ ] Update UX: show spinner "Generating VPR..."
- [ ] Add error handling for FAILED and TIMEOUT states

**Verification:**
- Submit VPR job → See PENDING status
- Poll status → See PROCESSING status
- Wait for completion → See COMPLETED status with result URL
- Fetch VPR from presigned URL → Verify VPR content

**Risk:** MEDIUM (UX change, user-facing)

---

### Phase 4: Gradual Rollout (Week 3)

**Goal:** Migrate production traffic with monitoring.

- [ ] Deploy to dev environment
- [ ] Run integration tests (submit → worker → status flow)
- [ ] Run load tests (100 concurrent submissions)
- [ ] Monitor metrics (queue depth, worker errors, DLQ)
- [ ] Route 10% traffic → async endpoint
- [ ] Monitor for 24 hours
- [ ] Route 50% traffic → async endpoint
- [ ] Monitor for 24 hours
- [ ] Route 100% traffic → async endpoint
- [ ] Deprecate synchronous code path

**Verification Metrics:**
- Success rate: >99%
- P95 generation time: <75s
- Queue depth: <10
- DLQ messages: 0
- Cost per VPR: <$0.002

**Risk:** LOW (gradual rollout with monitoring, rollback available)

---

## Success Criteria

### Functional Requirements

- [x] Architecture designed and documented
- [ ] Client receives response within 3 seconds (202 Accepted)
- [ ] VPR result retrievable within 5 minutes
- [ ] Job status visible via API
- [ ] Idempotency prevents duplicate LLM calls
- [ ] Failed jobs move to DLQ after 3 retries
- [ ] Jobs auto-expire after 10 minutes (TTL)

### Non-Functional Requirements

- [ ] Cost: <$0.10 per VPR (target: $0.0013)
- [ ] Availability: Same as synchronous endpoint (99.9%)
- [ ] Max queue time: <10 minutes before job expiry
- [ ] Worker concurrency: 5 (cost control + rate limit compliance)
- [ ] Security: All attack vectors mitigated
- [ ] Monitoring: CloudWatch alarms for DLQ + errors

### Testing Requirements

- [ ] Unit tests: Idempotency logic, job CRUD, status transitions
- [ ] Integration tests: Submit → worker → status flow
- [ ] Load tests: 100 concurrent submissions, verify queue depth
- [ ] Failure tests: Worker crashes, SQS retries, DLQ delivery
- [ ] Frontend tests: Polling component, timeout handling, error states

---

## Impact on Downstream Phases

### Phases 9-12 Analysis

**Key Finding:** Only Phase 7 (VPR) requires async pattern.

| Phase | LLM Model | Timeout | Pattern | Reason |
|-------|-----------|---------|---------|--------|
| 7 (VPR) | Sonnet 4.5 | 30-60s | **ASYNC** | Exceeds API Gateway 29s limit |
| 9 (CV Tailor) | Haiku 4.5 | <20s | SYNC | Fits within budget |
| 10 (Cover Letter) | Haiku 4.5 | <20s | SYNC | Fits within budget |
| 11 (Gap Analysis) | Sonnet 4.5 | <20s | SYNC | Fits within budget |
| 12 (Interview Prep) | Haiku 4.5 | <20s | SYNC | Fits within budget |

**Integration Flow Update:**

```
BEFORE: CV Upload → VPR (sync, 30-60s timeout) → Gap Analysis

AFTER:  CV Upload → VPR (async, submit 202)
                    ↓
                  Poll status (5s intervals)
                    ↓
                  VPR Complete (200 OK)
                    ↓
                  Gap Analysis (sync)
```

**Frontend UX Consideration:** Disable Gap Analysis, CV Tailor, and Cover Letter forms until VPR status = COMPLETED.

---

## References

- **Architecture Design:** [[docs/architecture/async-vpr-design.md]]
- **Task Breakdown:** [[docs/tasks/07-vpr-async/]]
- **Original VPR Spec:** [[docs/specs/03-vpr-generator.md]]
- **AWS SQS Best Practices:** https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-best-practices.html
- **AWS Lambda + SQS:** https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html

---

**Status:** Design Complete - Ready for Implementation
**Priority:** P0 (BLOCKING - Production VPR generation currently fails 100%)
**Estimated Effort:** 3-4 weeks (1 week infra, 2 weeks backend/frontend, 1 week testing/rollout)
