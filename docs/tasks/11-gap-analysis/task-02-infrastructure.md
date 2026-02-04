# Task 02: Infrastructure - API Gateway & Lambda (Synchronous)

## Overview

**IMPORTANT:** Phase 11 uses **SYNCHRONOUS** implementation (no SQS, no async workers).
Update CDK to add gap analysis endpoint with direct Lambda invocation.

**Files to modify:**
- `infra/api_construct.py` - Add gap analysis route
- `infra/careervp/constants.py` - Add naming constants (if needed)

**Dependencies:** None
**Estimated time:** 1 hour

---

## What NOT to Create

❌ SQS Queue (not needed for synchronous implementation)
❌ Dead Letter Queue (not needed)
❌ Worker Lambda (not needed)
❌ Status polling endpoint (not needed)
❌ DynamoDB jobs table GSI (not needed - no job tracking)

---

## What to Create

✅ Single Lambda function for gap analysis
✅ API Gateway POST route: `/api/gap-analysis`
✅ Lambda environment variables
✅ IAM permissions

---

## Implementation

### Update: `infra/api_construct.py`

Add gap analysis Lambda and API Gateway route following existing VPR pattern.

**Pattern to follow:** Look at existing VPR Lambda configuration in `api_construct.py`.

```python
# Add Gap Analysis Lambda Function
gap_analysis_fn = lambda_.Function(
    self,
    "GapAnalysisHandler",
    function_name=NamingUtils.lambda_name("gap-analysis", environment),
    runtime=lambda_.Runtime.PYTHON_3_12,
    handler="careervp.handlers.gap_handler.lambda_handler",
    code=lambda_.Code.from_asset("../src/backend"),
    timeout=Duration.seconds(120),  # 2 minutes (synchronous)
    memory_size=512,
    environment={
        "DYNAMODB_TABLE_NAME": dynamodb_table.table_name,
        "ANTHROPIC_API_KEY": anthropic_api_key,
        "POWERTOOLS_SERVICE_NAME": "careervp-gap-analysis",
        "LOG_LEVEL": "INFO"
    },
    layers=[powertools_layer],
)

# Grant permissions
dynamodb_table.grant_read_write_data(gap_analysis_fn)

# Add API Gateway route: POST /api/gap-analysis
gap_analysis_resource = api.root.add_resource("gap-analysis")
gap_analysis_resource.add_method(
    "POST",
    apigw.LambdaIntegration(gap_analysis_fn),
    authorization_type=apigw.AuthorizationType.COGNITO,
    authorizer=cognito_authorizer
)
```

---

## Infrastructure Tests

**File:** `tests/gap-analysis/infrastructure/test_gap_analysis_stack.py`

Tests verify:
- Lambda function exists with correct name
- Lambda has 120s timeout (synchronous)
- API Gateway POST route exists
- Cognito authorization configured
- DynamoDB permissions granted

---

## Verification Commands

```bash
cd infra

# Install dependencies
uv sync

# Synthesize CDK
npx cdk synth

# Expected: No errors, gap-analysis Lambda in output

# Run infrastructure tests
cd ..
uv run pytest tests/gap-analysis/infrastructure/ -v

# Expected: All infrastructure tests pass
```

---

## Acceptance Criteria

- [ ] Gap analysis Lambda created (`careervp-gap-analysis-{env}`)
- [ ] Lambda timeout = 120 seconds (synchronous processing)
- [ ] Lambda memory = 512 MB
- [ ] Lambda has DynamoDB read/write permissions
- [ ] API Gateway route: POST `/api/gap-analysis`
- [ ] Cognito authorization enabled
- [ ] Environment variables set correctly
- [ ] CDK synth succeeds
- [ ] Infrastructure tests pass

---

## Commit Message

```bash
git add infra/api_construct.py
git commit -m "feat(gap-analysis): add synchronous Lambda and API route

- Add gap_analysis_fn Lambda (120s timeout, 512MB)
- Add POST /api/gap-analysis API Gateway route
- Configure Cognito authorization
- Grant DynamoDB permissions

Synchronous implementation (no SQS for Phase 11).

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```
