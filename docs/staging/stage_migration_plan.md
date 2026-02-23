# CareerVP Staging Environment Migration Plan

**Document Version:** 1.0
**Date:** 2026-02-23
**Purpose:** Migrate working Dev code/infra to a staging environment for production-like testing

---

## Executive Summary

This document outlines the step-by-step plan to create a staging environment for CareerVP. The staging environment will be a near-production clone used for:
- Pre-production testing of new features
- Integration testing with production-like data
- Safe deployment validation before production

### Current State (Validated)

| Component | Dev Environment | Notes |
|-----------|----------------|-------|
| **Stack Name** | CareerVpCrudDev | CDK stack in us-east-1 |
| **SSM Parameters** | `/careervp/dev/*` | API keys, JWT keys |
| **DynamoDB Tables** | `careervp-*-dev` | Environment-suffix tables |
| **S3 Buckets** | `careervp-*-dev` | Environment-suffix buckets |
| **API Gateway** | Default "prod" stage | URL: `https://{id}.execute-api.us-east-1.amazonaws.com/prod/` |
| **Configuration** | dev_configuration.json | AWS AppConfig |
| **CI/CD** | Auto-deploy on push to main | Via deploy.yml |

### Target State

| Component | Staging Environment | Notes |
|-----------|---------------------|-------|
| **Stack Name** | CareerVpCrudStaging | Separate CDK stack |
| **SSM Parameters** | `/careervp/staging/*` | Separate secrets |
| **DynamoDB Tables** | `careervp-*-staging` | Separate from dev/prod |
| **S3 Buckets** | `careervp-*-staging` | Separate from dev/prod |
| **API Gateway** | Separate stage or stack | Different API endpoint |
| **Configuration** | staging_configuration.json | AWS AppConfig |
| **CI/CD** | Manual or branch-triggered | Via workflow_dispatch |

---

## What You Might Not Be Considering

Before diving into the implementation, here are critical considerations often overlooked:

### 1. Database Isolation Strategy

**Decision Required:** Should staging share DynamoDB tables with dev or have completely separate tables?

| Option | Pros | Cons |
|--------|------|------|
| **Shared tables (prefix)** | Lower cost, simpler | Risk of data pollution |
| **Separate tables** | Complete isolation | ~2x cost, more complex |

**Recommendation:** Separate tables for staging (per ENVIRONMENT suffix pattern already in use)

### 2. API Endpoint Strategy

**Current State:** API Gateway uses default "prod" stage - all environments share one API Gateway but different stacks.

**Options:**
- **Option A:** Separate API Gateway per environment (cleanest isolation)
- **Option B:** Same API Gateway, different stage per environment (requires stage configuration)
- **Option C:** Same API Gateway + same stage, different stack (risky - resource conflicts)

**Recommendation:** Option A or B - separate stack with unique API Gateway

### 3. Secrets Management

**Critical:** Staging needs its own:
- Anthropic API key (for testing - can use same key as dev or production-like)
- JWT key pair (can share with dev for testing, or generate new)
- Any other external service keys

### 4. Cost Implications

Running staging alongside dev/prod approximately doubles infrastructure costs:
- DynamoDB: ~$1-5/month for moderate usage
- Lambda: Pay per invocation
- API Gateway: ~$3.50/million requests
- S3: Minimal

### 5. Data Seeding

**Question:** How will staging get realistic test data?
- Option A: Anonymized production data copy
- Option B: Synthetic test data
- Option C: Manual test data creation

### 6. Monitoring & Alerting

- Should staging have the same alerts as production?
- Where do staging logs go? (dev or staging CloudWatch group)

### 7. Custom Domains (Future)

Currently no custom domains. When added:
- api-staging.careervp.com → API Gateway
- Need SSL certificate in us-east-1

---

# IMPLEMENTATION PLAN

## Implementation Order

1. **Phase 1:** Infrastructure Prerequisites (SSM, Config)
2. **Phase 2:** CDK Stack Configuration
3. **Phase 3:** CI/CD Pipeline Updates
4. **Phase 4:** Deployment & Verification
5. **Phase 5:** Documentation & Runbooks

---

## Phase 1: Infrastructure Prerequisites

**Duration:** 30 minutes | **Effort:** 1 hour
**Status:** PENDING

### Step 1.1: Create Staging SSM Parameters

**Context:** Create separate SSM parameters for staging environment.

**CODE:**
```bash
# Run in AWS CLI (requires AWS credentials with SSM permissions)
# Option A: Use same Anthropic key as dev (for testing)
aws ssm put-parameter \
  --name "/careervp/staging/anthropic-api-key" \
  --value "$ANTHROPIC_API_KEY" \
  --type SecureString \
  --overwrite

# Option B: Generate new JWT keys for staging
TMP_DIR=$(mktemp -d)
openssl genrsa -out "$TMP_DIR/staging-jwt-private.pem" 2048
openssl rsa -in "$TMP_DIR/staging-jwt-private.pem" -pubout -out "$TMP_DIR/staging-jwt-public.pem"

JWT_PRIVATE=$(cat "$TMP_DIR/staging-jwt-private.pem")
JWT_PUBLIC=$(cat "$TMP_DIR/staging-jwt-public.pem")

aws ssm put-parameter \
  --name "/careervp/staging/jwt-private-key" \
  --value "$JWT_PRIVATE" \
  --type String \
  --overwrite

aws ssm put-parameter \
  --name "/careervp/staging/jwt-public-key" \
  --value "$JWT_PUBLIC" \
  --type String \
  --overwrite
```

**VALIDATION CRITERIA:**
- [ ] `/careervp/staging/anthropic-api-key` exists in SSM
- [ ] `/careervp/staging/jwt-private-key` exists in SSM
- [ ] `/careervp/staging/jwt-public-key` exists in SSM
- [ ] Parameters are SecureString/String as appropriate

---

### Step 1.2: Create Staging Configuration File

**Context:** Create AWS AppConfig configuration for staging.

**FILE TO CREATE:**
- `infra/careervp/configuration/json/staging_configuration.json`

**CODE:**
```json
{
  "feature_flags": {
    "new_cv_tailoring": false,
    "beta_features": false,
    "strict_validation": true,
    "enhanced_logging": true
  },
  "limits": {
    "max_applications_per_day": 50,
    "max_questions_per_session": 10,
    "max_gap_analyses_per_day": 20,
    "max_vpr_per_day": 30
  },
  "rate_limits": {
    "api_requests_per_minute": 60,
    "burst_limit": 100
  },
  "third_party": {
    "anthropic": {
      "model": "claude-sonnet-4-5-20250514",
      "max_tokens": 4096,
      "temperature": 0.7
    }
  },
  "storage": {
    "cv_retention_days": 90,
    "vpr_retention_days": 30,
    "session_timeout_minutes": 60
  }
}
```

**VALIDATION CRITERIA:**
- [ ] File created at `infra/careervp/configuration/json/staging_configuration.json`
- [ ] JSON is valid and parseable
- [ ] Feature flags appropriate for staging environment

---

## Phase 2: CDK Stack Configuration

**Duration:** 1 hour | **Effort:** 4 hours
**Status:** PENDING

### Step 2.1: Update Stack Naming for Staging

**Context:** Ensure CDK creates separate resources for staging.

**READ FIRST:**
- `infra/careervp/naming_utils.py`
- `infra/careervp/constants.py`

**ANALYSIS:**
The naming utils already use ENVIRONMENT variable:
```python
# naming_utils.py
def resource_name(self, feature: str, resource: str) -> str:
    return f"careervp-{feature}-{resource}-{self.environment}"
```

This means setting `ENVIRONMENT=staging` will automatically create:
- Table: `careervp-users-staging`
- Bucket: `careervp-cvs-staging`
- Lambda: `careervp-crud-lambda-staging`

**VALIDATION CRITERIA:**
- [ ] Verified naming pattern includes environment suffix
- [ ] No hardcoded "dev" resource names found

---

### Step 2.2: Update API Gateway Configuration

**Context:** Configure separate API Gateway for staging OR ensure stack isolation.

**READ FIRST:**
- `infra/careervp/api_construct.py` (lines 236-273)

**ANALYSIS:**
Current configuration uses default stage. For staging:
- Option A (Preferred): Deploy as separate stack with separate API Gateway
- Option B: Add stage configuration to use environment-specific stage

**RECOMMENDATION:** Deploy as separate stack (CareerVpCrudStaging) - CDK handles API Gateway separation automatically.

**VALIDATION CRITERIA:**
- [ ] Verified CDK stack will create separate API Gateway
- [ ] No resource conflicts with dev stack

---

### Step 2.3: Configure Environment-Specific Throttling

**Context:** Staging may need different rate limits than production.

**CODE:**
```bash
# Update api_construct.py if needed to read from config
# Or update staging_configuration.json with staging-specific limits
```

**VALIDATION CRITERIA:**
- [ ] Staging has appropriate rate limits (can be more permissive than prod)

---

### Step 2.4: Run CDK Synth for Staging

**CODE:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/infra
ENVIRONMENT=staging uv run cdk synth CareerVpCrudStaging
```

**VALIDATION CRITERIA:**
- [ ] CDK synth succeeds without errors
- [ ] Stack name shows "Staging" in output
- [ ] All resources have "-staging" suffix

---

## Phase 3: CI/CD Pipeline Updates

**Duration:** 30 minutes | **Effort:** 2 hours
**Status:** PENDING

### Step 3.1: Update deploy.yml for Staging

**Context:** Ensure deploy.yml can deploy to staging environment.

**READ FIRST:**
- `.github/workflows/deploy.yml`

**ANALYSIS:**
The deploy.yml already supports staging via `workflow_dispatch`:
```yaml
workflow_dispatch:
  inputs:
    environment:
      description: 'Environment to deploy (dev, staging, prod)'
      required: true
      default: dev
```

And calculates stack name dynamically:
```yaml
STACK_NAME: ${{ inputs.environment == 'prod' && 'CareerVpCrudProduction' || inputs.environment == 'staging' && 'CareerVpCrudStaging' || 'CareerVpCrudDev' }}
```

**VALIDATION CRITERIA:**
- [ ] Verified workflow supports staging deployment
- [ ] Stack name correctly maps to CareerVpCrudStaging

---

### Step 3.2: Create Staging Deployment Workflow (Optional Enhancement)

**Context:** Create dedicated staging workflow for easier access.

**FILE TO CREATE:**
- `.github/workflows/deploy-staging.yml`

**CODE:**
```yaml
name: Deploy to Staging

on:
  workflow_dispatch:
  push:
    branches:
      - develop  # Optional: deploy on develop branch push

permissions:
  contents: read
  id-token: write

env:
  ENVIRONMENT: staging
  STACK_NAME: CareerVpCrudStaging
  AWS_REGION: us-east-1

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - name: Install Python
        run: uv python install 3.13
      - name: Install dependencies
        run: make dev
      - name: Build
        run: make build
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE }}
          role-session-name: deploy-staging-${{ github.sha }}
          aws-region: ${{ env.AWS_REGION }}
      - name: Deploy
        run: |
          cd src/backend
          make deploy
```

**VALIDATION CRITERIA:**
- [ ] File created at `.github/workflows/deploy-staging.yml`
- [ ] Workflow is valid YAML
- [ ] Environment variables correctly set

---

### Step 3.3: Verify GitHub Environments

**Context:** Ensure GitHub environments are configured for staging.

**REQUIRED:**
- GitHub repo settings → Environments
- Create "staging" environment (if not exists)
- Configure protection rules (optional):
  - Required reviewers
  - Wait timer
  - Deployment branch

**VALIDATION CRITERIA:**
- [ ] "staging" environment exists in GitHub
- [ ] Environment has appropriate protection rules

---

## Phase 4: Deployment & Verification

**Duration:** 1 hour | **Effort:** 2 hours
**Status:** PENDING

### Step 4.1: Deploy Staging Stack

**CODE:**
```bash
cd /Users/yitzchak/Documents/dev/careervp

# Option A: Via GitHub workflow dispatch
# Go to Actions → Deploy → Run workflow
# Select environment: staging

# Option B: Via CLI
cd src/backend
ENVIRONMENT=staging make deploy
```

**VALIDATION CRITERIA:**
- [ ] Stack "CareerVpCrudStaging" created in CloudFormation
- [ ] All resources have "-staging" suffix
- [ ] No deployment failures

---

### Step 4.2: Verify Staging API Availability

**CODE:**
```bash
# Get API Gateway URL
STACK_NAME="CareerVpCrudStaging"
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
  --output text)

echo "Staging API: $API_URL"

# Test health endpoint
curl -s "${API_URL}health" | jq '.'
```

**VALIDATION CRITERIA:**
- [ ] Health endpoint returns 200 OK
- [ ] Response includes status: "healthy"

---

### Step 4.3: Run Staging Smoke Tests

**CODE:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Set environment
export ENVIRONMENT=staging
export API_BASE="https://$(aws cloudformation describe-stacks \
  --stack-name CareerVpCrudStaging \
  --region us-east-1 \
  --query "Stacks[0].Outputs[0].OutputValue" \
  --output text)prod"

# Run smoke tests
make smoke-test
```

**VALIDATION CRITERIA:**
- [ ] All smoke tests pass
- [ ] No authentication errors
- [ ] Responses match expected schemas

---

### Step 4.4: Verify Staging Resources

**CODE:**
```bash
# Verify DynamoDB tables
aws dynamodb list-tables --region us-east-1 \
  --query "TableNames[?contains(@, 'staging')]"

# Verify S3 buckets
aws s3api list-buckets \
  --query "Buckets[?contains(Name, 'staging')].Name"

# Verify Lambda functions
aws lambda list-functions --region us-east-1 \
  --query "Functions[?contains(FunctionName, 'staging')].FunctionName"
```

**VALIDATION CRITERIA:**
- [ ] DynamoDB tables with "-staging" suffix exist
- [ ] S3 buckets with "-staging" suffix exist
- [ ] Lambda functions with "-staging" suffix exist

---

## Phase 5: Documentation & Runbooks

**Duration:** 30 minutes | **Effort:** 1 hour
**Status:** PENDING

### Step 5.1: Document Staging Access

**CONTEXT:** Create documentation for accessing staging environment.

**FILE TO UPDATE:**
- `docs/staging/README.md` (create)

**CONTENT:**
```markdown
# Staging Environment

## Access

- **API Endpoint:** https://{api-id}.execute-api.us-east-1.amazonaws.com/prod/
- **Stack Name:** CareerVpCrudStaging
- **Region:** us-east-1

## Deployment

### Via GitHub
1. Go to Actions → Deploy to Staging
2. Click "Run workflow"
3. Select/confirm staging environment

### Via CLI
```bash
cd src/backend
ENVIRONMENT=staging make deploy
```

## Testing

```bash
export ENVIRONMENT=staging
export API_BASE="https://{api-id}.execute-api.us-east-1.amazonaws.com/prod/"
make smoke-test
```

## Monitoring

- CloudWatch Log Groups: `/aws/lambda/careervp-*staging*`
- CloudWatch Metrics: Namespace `careervp_kpi` with staging metric

## Rollback

```bash
aws cloudformation rollback-stack \
  --stack-name CareerVpCrudStaging \
  --region us-east-1
```
```

**VALIDATION CRITERIA:**
- [ ] README.md created at docs/staging/README.md
- [ ] All access information documented

---

### Step 5.2: Add Staging to Runbook

**FILE TO UPDATE:**
- `docs/refactor/execution_runbook_2.md` (or create separate)

**CONTENT:**
Add staging deployment verification to the verification commands section:

```bash
# Staging deployment verification
export ENVIRONMENT=staging

# CDK synth
cd infra && ENVIRONMENT=staging uv run cdk synth CareerVpCrudStaging

# Verify stack exists
aws cloudformation describe-stacks \
  --stack-name CareerVpCrudStaging \
  --region us-east-1

# Test health
curl -s "https://$(aws cloudformation describe-stacks \
  --stack-name CareerVpCrudStaging \
  --region us-east-1 \
  --query "Stacks[0].Outputs[0].OutputValue" \
  --output text)prod/health"
```

---

# VALIDATION COMMANDS

## Pre-Deployment Validation

```bash
# 1. Verify SSM parameters exist
aws ssm get-parameter --name "/careervp/staging/anthropic-api-key"
aws ssm get-parameter --name "/careervp/staging/jwt-private-key"
aws ssm get-parameter --name "/careervp/staging/jwt-public-key"

# 2. Verify configuration file exists
cat infra/careervp/configuration/json/staging_configuration.json | jq .

# 3. Run CDK synth for staging
cd infra
ENVIRONMENT=staging uv run cdk synth CareerVpCrudStaging

# 4. Verify no resource conflicts
ENVIRONMENT=staging uv run cdk diff CareerVpCrudStaging 2>&1 | head -50
```

## Post-Deployment Validation

```bash
# 1. Verify stack status
aws cloudformation describe-stacks \
  --stack-name CareerVpCrudStaging \
  --region us-east-1 \
  --query "Stacks[0].StackStatus"

# 2. Get API URL
STACK_NAME="CareerVpCrudStaging"
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" \
  --output text)

echo "API URL: ${API_URL}prod"

# 3. Test health endpoint
curl -s "${API_URL}prod/health" | jq '.'

# 4. Verify resources
echo "=== DynamoDB Tables ==="
aws dynamodb list-tables --region us-east-1 \
  --query "TableNames[?contains(@, 'staging')]"

echo "=== S3 Buckets ==="
aws s3api list-buckets \
  --query "Buckets[?contains(Name, 'staging')].Name"

echo "=== Lambda Functions ==="
aws lambda list-functions --region us-east-1 \
  --query "Functions[?contains(FunctionName, 'staging')].FunctionName"

# 5. Run smoke tests
cd src/backend
ENVIRONMENT=staging make smoke-test
```

---

# COMPLETION CHECKLIST

## Phase 1: Infrastructure Prerequisites
- [ ] Step 1.1: Create staging SSM parameters (anthropic-api-key, jwt-private-key, jwt-public-key)
- [ ] Step 1.2: Create staging_configuration.json

## Phase 2: CDK Stack Configuration
- [ ] Step 2.1: Verified stack naming includes environment suffix
- [ ] Step 2.2: Verified API Gateway configuration
- [ ] Step 2.3: Configured environment-specific throttling
- [ ] Step 2.4: CDK synth succeeds for staging

## Phase 3: CI/CD Pipeline Updates
- [ ] Step 3.1: Verified deploy.yml supports staging
- [ ] Step 3.2: Created deploy-staging.yml (optional)
- [ ] Step 3.3: Verified GitHub environments configured

## Phase 4: Deployment & Verification
- [ ] Step 4.1: Deployed staging stack
- [ ] Step 4.2: Verified staging API availability
- [ ] Step 4.3: Ran staging smoke tests
- [ ] Step 4.4: Verified staging resources exist

## Phase 5: Documentation & Runbooks
- [ ] Step 5.1: Created staging README.md
- [ ] Step 5.2: Added staging to runbook

---

# OPEN QUESTIONS

The following questions require decision before or during implementation:

1. **API Key Strategy:** Should staging use the same Anthropic API key as dev, or a separate key?
   - Same: Simpler, lower cost
   - Separate: Better isolation, can test key rotation

2. **Data Seeding:** How will staging get test data?
   - Option A: Anonymized production data (requires compliance review)
   - Option B: Synthetic data generation
   - Option C: Manual creation via API

3. **Custom Domains:** When implementing custom domains, should staging get api-staging.careervp.com?
   - Requires Route53 + ACM setup
   - Additional cost ~$1/month

4. **Alerting:** Should staging have the same alerts as production?
   - Option A: Same alerts (catches issues earlier)
   - Option B: Reduced alerts (lower noise)
   - Option C: No alerts (only monitor manually)

5. **长期:** What's the long-term strategy for dev vs staging?
   - Option A: Dev = always-latest, Staging = last-tested
   - Option B: Both always latest, separate by feature flags
   - Option C: Dev for development, Staging for QA

---

# APPENDIX A: Environment Comparison

| Component | Dev | Staging | Production |
|-----------|-----|---------|------------|
| **Stack** | CareerVpCrudDev | CareerVpCrudStaging | CareerVpCrudProduction |
| **SSM Path** | /careervp/dev/* | /careervp/staging/* | /careervp/prod/* |
| **DynamoDB** | *-dev | *-staging | *-prod |
| **S3** | *-dev | *-staging | *-prod |
| **Lambda** | *-dev | *-staging | *-prod |
| **API Gateway** | Shared or separate | Separate | Shared or separate |
| **Config** | dev_configuration.json | staging_configuration.json | prod_configuration.json |
| **Throttling** | High (testing) | Medium | Low (production) |
| **PITR** | Optional | Recommended | Required |
| **Alerts** | None/Minimal | Standard | Comprehensive |
| **Data** | Synthetic | Synthetic/Anonymized | Production |

---

# APPENDIX B: Rollback Procedure

If staging deployment fails:

```bash
# Option 1: CloudFormation rollback
aws cloudformation rollback-stack \
  --stack-name CareerVpCrudStaging \
  --region us-east-1

# Option 2: Delete stack entirely
aws cloudformation delete-stack \
  --stack-name CareerVpCrudStaging \
  --region us-east-1

# Option 3: Re-deploy previous version
# (requires previous artifact in S3 or GitHub)
```

---

# APPENDIX C: Cost Estimation

Monthly cost for staging environment (estimated):

| Service | Estimate |
|---------|----------|
| DynamoDB (10 tables, pay-per-request) | $1-5 |
| Lambda (100K invocations) | $0.20 |
| API Gateway (100K requests) | $0.35 |
| S3 (1GB storage) | $0.02 |
| CloudWatch Logs | $0.50 |
| **Total** | **$2-7/month** |

---

**Document Status:** DRAFT - Ready for Review
**Next Steps:** Confirm open questions, begin Phase 1 implementation
