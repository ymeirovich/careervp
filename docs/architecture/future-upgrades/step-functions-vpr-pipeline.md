# Future Upgrade: Step Functions VPR Pipeline

**Status:** Deferred — implement after spec 07 stabilizes  
**Prerequisite:** spec 07-pipeline-timeout-fix deployed and validated in prod  
**Estimated LOE:** 3–5 days (backend) + 1 day (CDK) + 1 day (testing)

---

## Why Defer

Spec 07 (merge Stage 4, raise timeout to 10 min, add DLQ Lambda) resolves the immediate
timeout failure at a fraction of the cost. Step Functions becomes worth the investment when
one or more of these triggers is true:

- VPR generation is still timing out after spec 07 (output token growth)
- You add a third LLM stage (e.g. Hebrew translation, extended research)
- You need per-stage cost breakdown in CloudWatch for billing instrumentation
- You want to add human-in-the-loop review before final VPR delivery
- Debugging prod failures requires execution-level visibility beyond log tailing

---

## Problem It Solves

The current pipeline runs 2–4 LLM calls sequentially inside a single Lambda invocation.
Each call takes 2–3 minutes. The Lambda has a hard 15-minute ceiling. As input richness
grows (more gap responses, longer CVs) this ceiling will be hit again.

Step Functions eliminates the cumulative timeout problem: each stage is its own Lambda
with its own independent 15-minute budget.

---

## Proposed State Machine

```
                    ┌─────────────────────────────────────┐
                    │     VPR Generation State Machine     │
                    └─────────────────────────────────────┘
                                      │
                              [Task] PrepareEvidence
                              Lambda: vpr-stage-prepare
                              (Stages 1+2 — pure Python, fast)
                              Timeout: 30s
                                      │
                              [Task] SynthesizeVPR
                              Lambda: vpr-stage-synthesize
                              (Stage 3 — single LLM call, 16K tokens)
                              Timeout: 10 min
                              Retry: 2x, backoff 30s
                                      │
                              [Task] EvaluateQuality
                              Lambda: vpr-stage-evaluate
                              (Stage 5+6 — parse + quality gate)
                              Timeout: 60s
                                      │
                              [Choice] passed_gate?
                             /                       \
                           Yes                       No
                            │                         │
                    [Task] PersistVPR           [Task] RegenerateFeedback
                    Lambda: vpr-stage-persist    Lambda: vpr-stage-feedback
                    Timeout: 30s                 Timeout: 10s
                                                  │
                                            [Choice] retry_count < 3?
                                           /                         \
                                         Yes                         No
                                          │                           │
                                  (back to Synthesize)        [Task] PersistBestEffort
                                                              (persist with passed_gate=false)
```

### State Details

| State | Lambda | Input | Output | Timeout |
|---|---|---|---|---|
| PrepareEvidence | vpr-stage-prepare | job_id, user_id | evidence_payload (JSON) | 30s |
| SynthesizeVPR | vpr-stage-synthesize | evidence_payload, feedback? | raw_vpr_payload (JSON) | 10 min |
| EvaluateQuality | vpr-stage-evaluate | raw_vpr_payload | vpr_object, passed_gate, score, issues | 60s |
| PersistVPR | vpr-stage-persist | vpr_object, job_id | artifact_id | 30s |
| RegenerateFeedback | vpr-stage-feedback | issues, score | feedback string, retry_count++ | 10s |
| PersistBestEffort | vpr-stage-persist | vpr_object, job_id, best_effort=true | artifact_id | 30s |

---

## State Payload Design

**Critical constraint:** Step Functions Standard Workflows allow 256KB max state size.
The full VPR JSON is ~35–40KB. Serialized with the full input context it may approach
100KB. Two strategies:

### Option A: Pass full state in-band (simpler, risky)
Each Lambda receives and returns the full accumulated state. Works while payloads stay
well under 256KB. Fails silently if a stage returns >256KB (SF throws `States.DataLimitExceeded`).

### Option B: S3-backed state (recommended)
Each Lambda writes its output to S3 (`s3://vpr-results/{execution_id}/{stage}.json`)
and passes only the S3 key in the state payload. The next Lambda reads from S3.

```json
{
  "job_id": "4e43dbb4-...",
  "execution_id": "arn:aws:states:...",
  "stage_outputs": {
    "prepare": "s3://careervp-vpr-results-dev/executions/4e43dbb4/prepare.json",
    "synthesize": "s3://careervp-vpr-results-dev/executions/4e43dbb4/synthesize.json"
  },
  "retry_count": 0,
  "feedback": null
}
```

This approach has no size limit risk and also gives you a free audit trail of intermediate
outputs per execution.

---

## Job Status Bridging

The frontend polls `GET /vpr/{job_id}/status` against the DynamoDB jobs table.
The jobs table must stay as the source of truth for the frontend — do not replace it
with Step Functions execution status API calls.

Each stage Lambda updates the jobs table:

| Stage completes | DynamoDB status |
|---|---|
| PrepareEvidence | PROCESSING (already set by submit) |
| SynthesizeVPR | PROCESSING (no change needed) |
| EvaluateQuality passes | COMPLETING (optional intermediate) |
| PersistVPR | COMPLETED |
| Any stage fails after retries | FAILED |

The submit Lambda changes: instead of enqueuing to SQS, it starts a Step Functions
execution and stores the execution ARN in the jobs table for debugging.

```python
# vpr_submit_handler.py change
sf_client.start_execution(
    stateMachineArn=os.environ['VPR_STATE_MACHINE_ARN'],
    name=job_id,  # execution name = job_id for easy lookup
    input=json.dumps({'job_id': job_id, 'user_id': user_id, ...}),
)
```

---

## CDK Changes

### New constructs needed

```python
# New file: infra/careervp/vpr_stepfunctions_construct.py

from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks

# 1. One Lambda per stage (5 total)
# 2. Task states wrapping each Lambda
# 3. Choice states for quality gate and retry logic
# 4. Standard Workflow (not Express — need execution history)
# 5. IAM: SF execution role needs Lambda:InvokeFunction for each stage Lambda
# 6. IAM: submit Lambda needs states:StartExecution
```

### Workflow type: Standard (not Express)
- Standard: $0.025 per 1K state transitions. A typical VPR run = ~15 transitions = $0.000375.
  Negligible at any realistic volume.
- Express: cheaper but no execution history, 5-min max duration, no `getExecutionHistory`.
  Not suitable — VPR runs can exceed 5 min and you need debugging history.

### Remove or repurpose
- SQS queue: can be removed from VPR path (SF handles orchestration)
- SQS worker Lambda: replaced by stage Lambdas
- DLQ: replace with SF error handling (`Catch` on each task → update job to FAILED)
- DLQ Lambda from spec 07: no longer needed (SF handles failure states natively)

---

## What You're Not Considering

### 1. Lambda cold start amplification
A 5-stage SF pipeline invokes 5 separate Lambdas. In the worst case (all cold starts),
you add 5 × ~500ms = 2.5 seconds of cold start overhead. Mitigate with provisioned
concurrency on SynthesizeVPR (the most-hit stage) or keep the PrepareEvidence and
EvaluateQuality stages combined in one Lambda since they're fast.

### 2. Cost increase
Current: ~$0.15 per VPR generation (one LLM call, no SF)
With SF: ~$0.15 (LLM) + $0.000375 (SF transitions) + ~$0.001 (5 Lambda invocations) ≈ $0.151
Effectively identical. SF overhead is negligible compared to LLM cost.

### 3. X-Ray tracing across stages
The current `xray_trace_id` flows through a single Lambda invocation. With SF, you get
a new trace per stage Lambda. Wire `_X_AMZN_TRACE_ID` explicitly via SF context object
(`$$`) into each task input, or use SF's native X-Ray integration (`tracing: sfn.Tracing.ENABLED`).
Without this, your Powertools tracer will show disconnected sub-segments.

### 4. Idempotency in stage Lambdas
Currently the submit handler uses an idempotency key to deduplicate. With SF, if the
user clicks "Generate" twice, you start two SF executions. The execution `name` parameter
(set to `job_id`) is idempotent per SF — a second `start_execution` with the same name
returns the existing execution ARN. This is free idempotency at the SF level.
**But:** the jobs table still needs the idempotency key for the `status=FAILED` bypass
added in the submit handler (spec idempotency fix). Keep that logic.

### 5. Local development
The current setup runs locally via `sam local` or direct Lambda invocation. Step Functions
can be tested locally with `aws-stepfunctions-local` (Docker image). Add this to the
local dev setup documentation — it's not obvious and is often skipped, making SF harder
to develop locally.

### 6. Hebrew / multi-language VPRs
If a Hebrew translation stage is added in V2, it fits naturally as a parallel branch in
the state machine running concurrently with the English quality gate. This is a key
architectural advantage of SF: parallel branches with `Parallel` state at no extra latency cost.

---

## Migration Path from Spec 07

Spec 07 and Step Functions are designed to coexist during migration:

1. **Phase 1 (spec 07, now):** Merge Stage 4, raise timeout, add DLQ Lambda.
   SQS-based pipeline with 10-min Lambda.

2. **Phase 2 (SF pilot):** Add SF state machine alongside SQS pipeline.
   Feature-flag `USE_STEP_FUNCTIONS=true` in submit handler routes new jobs to SF.
   Old jobs still processed by SQS worker. Run both in parallel for 2 weeks.

3. **Phase 3 (SF GA):** Remove SQS queue, SQS worker Lambda, DLQ Lambda.
   All VPR jobs go through SF. Clean up CDK constructs.

---

## Acceptance Criteria (for spec authoring)

- Each stage Lambda completes independently within its timeout budget
- SF execution history visible in AWS console for every VPR job
- Job status in DynamoDB transitions correctly through the execution lifecycle
- Failed stage → job status = FAILED within 60 seconds
- User can regenerate after failure (idempotency bypass still works)
- Total wall-clock time for a typical VPR generation ≤ 5 minutes end-to-end
- X-Ray trace spans visible per stage in AWS X-Ray console
- `cdk synth` produces valid CloudFormation with no nag suppressions added
- All existing VPR unit tests pass unchanged
- Cost per VPR generation ≤ $0.20 (LLM + infrastructure)
