# CareerVP Staging Environment Execution Runbook

**Document Version:** 1.0
**Date:** 2026-02-24
**Purpose:** Deploy the CURRENT, WORKING Dev environment to Staging for testing

---

## PRIMARY GOAL STATEMENT

This runbook's purpose is to deploy the **CURRENT, WORKING Dev environment to Staging for testing**. Every Phase, Step, and Test validates this goal.

---

## Executive Summary

This runbook provides a comprehensive, spec-based, test-driven approach to implementing a staging environment for the CareerVP application. The staging environment serves as a near-production clone for pre-production testing.

### Current State (Dev Environment -Validated)

| Component | Dev Environment | Notes |
|-----------|----------------|-------|
| **Stack Name** | CareerVpCrudDev | CDK stack in us-east-1 |
| **SSM Parameters** | `/careervp/dev/*` | API keys, JWT keys |
| **DynamoDB Tables** | `careervp-*-dev` | Environment-suffix tables |
| **S3 Buckets** | `careervp-*-dev` | Environment-suffix buckets |
| **API Gateway** | Default "prod" stage | URL: `https://{id}.execute-api.us-east-1.amazonaws.com/prod/` |
| **Configuration** | dev_configuration.json | AWS AppConfig |
| **CI/CD** | Auto-deploy on push to main | Via deploy.yml |

### Target State (Staging)

| Component | Staging Environment | Notes |
|-----------|---------------------|-------|
| **Stack Name** | CareerVpCrudStaging | Separate CDK stack |
| **SSM Parameters** | `/careervp/staging/*` | Separate secrets |
| **DynamoDB Tables** | `careervp-*-staging` | Separate from dev/prod |
| **S3 Buckets** | `careervp-*-staging` | Separate from dev/prod |
| **API Gateway** | Separate API Gateway | Different API endpoint |
| **Configuration** | staging_configuration.json | AWS AppConfig |
| **CI/CD** | develop branch push | Via deploy.yml |

---

## Architecture Decisions

1. **Database Isolation**: Separate tables for staging (per ENVIRONMENT suffix pattern already in use)
2. **API Gateway Strategy**: Separate API Gateway per environment (cleanest isolation)
3. **Secrets Management**: Staging needs its own:
   - Separate Anthropic API key: `/careervp/staging/anthropic-api-key`
   - Separate JWT key pair: `/careervp/staging/jwt-private-key`, `/careervp/staging/jwt-public-key`
4. **Data Seeding**: Synthetic test data (create data generator)
5. **Monitoring**: Staging has the same alerts as production, logs go to CloudWatch groups with `-staging` suffix
6. **Git Branch Strategy**: Branch-Based approach
   - `develop` branch pushes -> auto-deploy to staging
   - `main` branch pushes -> auto-deploy to dev

---

# PHASE 1: Git Branch Setup

**Goal Validation:** Create branch that will trigger Staging deployment of Dev code

## Step 1.1: Create develop branch from main

**Context:** Create a develop branch that carries Dev code and will trigger staging deployments.

**CODE:**
```bash
# Ensure you're on main with latest changes
cd /Users/yitzchak/Documents/dev/careervp
git checkout main
git pull origin main

# Create develop branch
git checkout -b develop

# Push develop branch to origin
git push -u origin develop
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **NO** - This phase sets up the branch that will trigger Staging deployment
- [ ] `develop` branch exists locally
- [ ] `develop` branch exists on remote (origin)
- [ ] Branch contains same commits as main

---

## Step 1.2: Update Branch Protection Rules

**Context:** Configure branch protection rules for develop and staging environment.

**CODE:**
```bash
# GitHub CLI to protect develop branch
gh api repos/{owner}/{repo}/protection/branches/develop \
  -X PUT \
  -f required_status_checks='{"strict":true,"contexts":["Deploy/dev"]}' \
  -f required_pull_request_reviews='{"required_approving_review_count":1}' \
  -f allow_force_pushes=false \
  -f allow_deletions=false
```
//correction: repos/{owner}/{repo}/branches/develop/protection

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **NO** - This phase configures branch protection
- [ ] develop branch has protection rules configured

---

## Step 1.3: Create GitHub "staging" Environment

**Context:** Create GitHub environment for staging deployments.

**CODE:**
```bash
# Create staging environment via GitHub CLI
gh api repos/{owner}/{repo}/environments/staging \
  -X PUT \
  -H "Accept: application/vnd.github+json" \
  -f wait_timer=0 \
  -f review_workers=0
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **NO** - This phase creates the GitHub environment
- [ ] "staging" environment exists in GitHub
- [ ] Environment has no required reviewers (for automated deploys)

---

# PHASE 2: Infrastructure Prerequisites

**Goal Validation:** Prepare AWS for Dev code to run in Staging

## Step 2.1: Create Staging SSM Parameters

**Context:** Create separate SSM parameters for staging environment.

**CODE:**
```bash
# Run in AWS CLI (requires AWS credentials with SSM permissions)
# Option A: Use same Anthropic key as dev (for testing)
aws ssm put-parameter \
  --name "/careervp/staging/anthropic-api-key" \
  --value "$ANTHROPIC_API_KEY_STAGING" \
  --type SecureString \
  --overwrite \
  --region us-east-1

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
  --overwrite \
  --region us-east-1

aws ssm put-parameter \
  --name "/careervp/staging/jwt-public-key" \
  --value "$JWT_PUBLIC" \
  --type String \
  --overwrite \
  --region us-east-1
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **NO** - This phase prepares infrastructure
- [ ] `/careervp/staging/anthropic-api-key` exists in SSM
- [ ] `/careervp/staging/jwt-private-key` exists in SSM
- [ ] `/careervp/staging/jwt-public-key` exists in SSM
- [ ] Parameters are SecureString/String as appropriate

---

## Step 2.2: Create Staging Configuration File

**Context:** Create AWS AppConfig configuration for staging.

**FILE:** `infra/careervp/configuration/json/staging_configuration.json`

**CODE:**
```json
{
    "features": {
        "premium_features": {
            "default": false,
            "rules": {
                "enable premium features for this specific customer name": {
                    "when_match": true,
                    "conditions": [
                        {
                            "action": "EQUALS",
                            "key": "customer_name",
                            "value": "RanTheBuilder"
                        }
                    ]
                }
            }
        },
        "ten_percent_off_campaign": {
            "default": true
        }
    },
    "countries": [
        "ISRAEL",
        "USA"
    ]
}
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **NO** - This phase creates config file
- [ ] File created at `infra/careervp/configuration/json/staging_configuration.json`
- [ ] JSON is valid and parseable
- [ ] Feature flags appropriate for staging environment

---

# PHASE 3: GitHub Workflows

**Goal Validation:** Enable CI/CD to deploy Dev code to Staging

## Step 3.1: Create deploy-staging.yml Workflow

**Context:** Create dedicated staging deployment workflow.

**FILE:** `.github/workflows/deploy-staging.yml`

**CODE:**
```yaml
name: Deploy to Staging

on:
  push:
    branches:
      - develop
  workflow_dispatch:

permissions:
  contents: read
  deployments: write
  id-token: write

env:
  PYTHON_VERSION: '3.13'
  NODE_VERSION: '22'
  AWS_REGION: 'us-east-1'
  UV_VERSION: '0.5.21'
  ENVIRONMENT: 'staging'
  STACK_NAME: 'CareerVpCrudStaging'

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
        with:
          ref: develop

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: npm
          cache-dependency-path: package-lock.json

      - name: Install Node dependencies
        run: npm ci

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          version: ${{ env.UV_VERSION }}
          enable-cache: true
          cache-dependency-glob: '**/uv.lock'

      - name: Install Python
        run: uv python install ${{ env.PYTHON_VERSION }}

      - name: Install backend dependencies
        working-directory: src/backend
        run: uv sync

      - name: Build Lambda artifacts
        working-directory: src/backend
        run: make build

      - name: Run CDK Nag Security Scan
        working-directory: infra
        run: |
          uv sync
          echo "=== Running CDK Nag Security Scan ==="
          npx cdk synth --quiet || { echo "CDK synth failed"; exit 1; }
          echo "=== CDK Nag Security Scan passed ==="

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE }}
          role-session-name: deploy-staging-${{ github.sha }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Ensure SSM Parameter exists
        env:
          ANTHROPIC_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          if [ -n "$ANTHROPIC_KEY" ]; then
            aws ssm put-parameter \
              --name "/careervp/staging/anthropic-api-key" \
              --value "$ANTHROPIC_KEY" \
              --type SecureString \
              --overwrite
          else
            echo "::warning::ANTHROPIC_API_KEY secret not set."
          fi

      - name: Ensure JWT SSM Parameters exist
        env:
          JWT_PRIVATE_KEY_SECRET: ${{ secrets.JWT_PRIVATE_KEY }}
          JWT_PUBLIC_KEY_SECRET: ${{ secrets.JWT_PUBLIC_KEY }}
        run: |
          set -euo pipefail
          ensure_string_parameter() {
            local param_name="$1"
            local param_value="$2"
            aws ssm put-parameter \
              --name "$param_name" \
              --value "$param_value" \
              --type String \
              --overwrite
          }
          JWT_PRIVATE_KEY="${JWT_PRIVATE_KEY_SECRET:-}"
          JWT_PUBLIC_KEY="${JWT_PUBLIC_KEY_SECRET:-}"
          if [ -z "$JWT_PRIVATE_KEY" ] || [ -z "$JWT_PUBLIC_KEY" ]; then
            TMP_DIR="$(mktemp -d)"
            openssl genrsa -out "$TMP_DIR/jwt-private.pem" 2048 >/dev/null 2>&1
            openssl rsa -in "$TMP_DIR/jwt-private.pem" -pubout -out "$TMP_DIR/jwt-public.pem" >/dev/null 2>&1
            JWT_PRIVATE_KEY="$(cat "$TMP_DIR/jwt-private.pem")"
            JWT_PUBLIC_KEY="$(cat "$TMP_DIR/jwt-public.pem")"
            echo "::warning::JWT keys not set. Generated ephemeral keys."
          fi
          ensure_string_parameter "/careervp/staging/jwt-private-key" "$JWT_PRIVATE_KEY"
          ensure_string_parameter "/careervp/staging/jwt-public-key" "$JWT_PUBLIC_KEY"

      - name: CFN State Guard
        run: |
          .github/scripts/cfn-guard.sh "${{ env.STACK_NAME }}" "${{ env.AWS_REGION }}"

      - name: Build and Deploy
        working-directory: src/backend
        run: |
          set -o pipefail
          make deploy 2>&1 | tee /tmp/deploy.log || {
            if grep -Eq "(_IN_PROGRESS state and can not be updated|UPDATE_COMPLETE_CLEANUP_IN_PROGRESS)" /tmp/deploy.log; then
              echo "::warning::Stack update lock detected. Re-running CFN guard and retrying deploy..."
              .github/scripts/cfn-guard.sh "${{ env.STACK_NAME }}" "${{ env.AWS_REGION }}"
              make deploy
            else
              exit 1
            fi
          }

      - name: Wait for Stack Stability
        run: |
          echo "Waiting for CloudFormation stack to stabilize..."
          aws cloudformation wait stack-create-complete \
            --stack-name ${{ env.STACK_NAME }} \
            --region ${{ env.AWS_REGION }} 2>/dev/null || \
          aws cloudformation wait stack-update-complete \
            --stack-name ${{ env.STACK_NAME }} \
            --region ${{ env.AWS_REGION }} 2>/dev/null || true

      - name: Wait for API Availability
        run: |
          .github/scripts/wait-for-api.sh "${{ env.AWS_REGION }}" "${{ env.STACK_NAME }}"

      - name: Smoke test
        working-directory: src/backend
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          AUTO_SET_LAMBDA_ENV: '1'
          AWS_REGION: us-east-1
        run: |
          echo "=== IAM PROPAGATION WAIT (15s) ==="
          sleep 15
          export PATH="${PWD}/.venv/bin:${PATH}"
          bash tests/aws_cli_smoke.sh staging
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **YES** - This workflow enables CI/CD to deploy
- [ ] File created at `.github/workflows/deploy-staging.yml`
- [ ] Workflow is valid YAML
- [ ] Environment variables correctly set to staging

---

# PHASE 4: Synthetic Data Generator

**Goal Validation:** Provide test data so Dev features can be tested in Staging

## Step 4.1: Create Synthetic Data Generator Script

**Context:** Create script to generate synthetic test data for staging.

**FILE:** `docs/staging/scripts/generate_synthetic_data.py`

**CODE:**
```python
#!/usr/bin/env python3
"""
Synthetic Data Generator for Staging Environment

Generates realistic test data for the CareerVP staging environment including:
- Test users (job seekers with various profiles)
- Test jobs (various positions and companies)
- Test CVs (sample resumes in different formats)
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Constants
NUM_TEST_USERS = 10
NUM_TEST_JOBS = 20


def generate_test_users() -> list[dict[str, Any]]:
    """Generate synthetic test users."""
    first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa", "William", "Jennifer"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    countries = ["ISRAEL", "USA"]
    subscription_tiers = ["free", "premium", "trial"]

    users = []
    for i in range(NUM_TEST_USERS):
        user = {
            "user_id": str(uuid.uuid4()),
            "email": f"test.user{i+1}@staging.careervp.com",
            "first_name": random.choice(first_names),
            "last_name": random.choice(last_names),
            "country": random.choice(countries),
            "subscription_tier": random.choice(subscription_tiers),
            "is_active": True,
            "created_at": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        users.append(user)

    return users


def generate_test_jobs() -> list[dict[str, Any]]:
    """Generate synthetic test jobs."""
    job_titles = [
        "Software Engineer",
        "Senior Software Engineer",
        "Full Stack Developer",
        "Backend Developer",
        "Frontend Developer",
        "DevOps Engineer",
        "Data Scientist",
        "Product Manager",
        "UX Designer",
        "QA Engineer",
        "Machine Learning Engineer",
        "Security Engineer",
        "Cloud Architect",
        "Technical Lead",
        "Engineering Manager",
    ]

    companies = [
        "TechCorp",
        "InnovateTech",
        "CloudSystems",
        "DataDriven Inc",
        "SecureNet",
        "AIVentures",
        "DigitalFirst",
        "FutureSoft",
        "NextGen Labs",
        "QuantumCode",
    ]

    countries = ["ISRAEL", "USA"]
    job_types = ["FULL_TIME", "PART_TIME", "CONTRACT", "INTERNSHIP"]
    experience_levels = ["ENTRY", "MID", "SENIOR", "LEAD", "EXECUTIVE"]

    jobs = []
    for i in range(NUM_TEST_JOBS):
        job = {
            "job_id": str(uuid.uuid4()),
            "title": random.choice(job_titles),
            "company": random.choice(companies),
            "country": random.choice(countries),
            "job_type": random.choice(job_types),
            "experience_level": random.choice(experience_levels),
            "description": f"Looking for a talented {random.choice(job_titles)} to join our team.",
            "requirements": [
                "3+ years of experience",
                "Bachelor's degree or equivalent",
                "Strong communication skills",
            ],
            "is_active": True,
            "created_at": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        jobs.append(job)

    return jobs


def generate_test_cvs() -> list[dict[str, Any]]:
    """Generate synthetic test CVs."""
    cvs = []

    # Sample CV 1 - Software Engineer
    cvs.append({
        "cv_id": str(uuid.uuid4()),
        "user_id": "{{USER_ID_1}}",
        "file_name": "software_engineer_resume.pdf",
        "file_type": "application/pdf",
        "summary": "Experienced software engineer with 5 years of experience in full-stack development.",
        "experience": [
            {
                "title": "Software Engineer",
                "company": "TechCorp",
                "start_date": "2020-01",
                "end_date": "Present",
                "description": "Developed microservices using Python and React."
            },
            {
                "title": "Junior Developer",
                "company": "StartupXYZ",
                "start_date": "2018-06",
                "end_date": "2019-12",
                "description": "Built REST APIs and front-end components."
            }
        ],
        "skills": ["Python", "JavaScript", "React", "AWS", "Docker", "Kubernetes", "SQL", "NoSQL"],
        "education": [
            {
                "degree": "B.Sc. Computer Science",
                "institution": "Technion",
                "year": 2018
            }
        ],
        "created_at": datetime.now().isoformat(),
    })

    # Sample CV 2 - Data Scientist
    cvs.append({
        "cv_id": str(uuid.uuid4()),
        "user_id": "{{USER_ID_2}}",
        "file_name": "data_scientist_resume.pdf",
        "file_type": "application/pdf",
        "summary": "Data scientist with expertise in machine learning and statistical analysis.",
        "experience": [
            {
                "title": "Data Scientist",
                "company": "DataDriven Inc",
                "start_date": "2021-03",
                "end_date": "Present",
                "description": "Built ML models for predictive analytics."
            }
        ],
        "skills": ["Python", "R", "TensorFlow", "PyTorch", "SQL", "Tableau", "Statistics"],
        "education": [
            {
                "degree": "M.Sc. Data Science",
                "institution": "Tel Aviv University",
                "year": 2021
            }
        ],
        "created_at": datetime.now().isoformat(),
    })

    return cvs


def main() -> None:
    """Main entry point for data generation."""
    output_dir = Path(__file__).parent.parent / "payloads"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate and save test users
    users = generate_test_users()
    users_file = output_dir / "staging_test_users.json"
    with open(users_file, "w") as f:
        json.dump(users, f, indent=2)
    print(f"Generated {len(users)} test users -> {users_file}")

    # Generate and save test jobs
    jobs = generate_test_jobs()
    jobs_file = output_dir / "staging_test_jobs.json"
    with open(jobs_file, "w") as f:
        json.dump(jobs, f, indent=2)
    print(f"Generated {len(jobs)} test jobs -> {jobs_file}")

    # Generate and save test CVs
    cvs = generate_test_cvs()
    cvs_file = output_dir / "staging_test_cvs.json"
    with open(cvs_file, "w") as f:
        json.dump(cvs, f, indent=2)
    print(f"Generated {len(cvs)} test CVs -> {cvs_file}")

    print("\nSynthetic data generation complete!")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **NO** - This phase creates test data
- [ ] Script created at `docs/staging/scripts/generate_synthetic_data.py`
- [ ] Script is executable
- [ ] Script generates valid JSON files

---

## Step 4.2: Generate Test Data

**CODE:**
```bash
python3 docs/staging/scripts/generate_synthetic_data.py
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **NO** - This generates test data
- [ ] `staging_test_users.json` created
- [ ] `staging_test_jobs.json` created
- [ ] `staging_test_cvs.json` created

---

# PHASE 5: CDK Validation

**Goal Validation:** Verify CDK can deploy Dev code as Staging stack

## Step 5.1: Run CDK Synth for Staging

**CODE:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/infra
ENVIRONMENT=staging uv run cdk synth CareerVpCrudStaging
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **YES** - This validates the CDK can deploy to staging
- [ ] CDK synth succeeds without errors
- [ ] Stack name shows "Staging" in output
- [ ] All resources have "-staging" suffix

---

## Step 5.2: Verify Resource Naming

**CODE:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/infra
ENVIRONMENT=staging uv run cdk list
```

Expected output should include: `CareerVpCrudStaging`

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **YES** - This verifies stack naming
- [ ] Stack name is `CareerVpCrudStaging`
- [ ] All resources include `-staging` suffix

---

# PHASE 6: Deployment

**Goal Validation:** DEPLOY Dev code to Staging

## Step 6.1: Deploy Staging Stack

**CODE:**
```bash
# Option A: Via GitHub workflow
# Go to Actions -> Deploy to Staging -> Run workflow
# Select/confirm staging environment

# Option B: Via CLI
cd /Users/yitzchak/Documents/dev/careervp/src/backend
ENVIRONMENT=staging make deploy
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **YES** - This actually deploys
- [ ] Stack "CareerVpCrudStaging" created in CloudFormation
- [ ] All resources have "-staging" suffix
- [ ] No deployment failures

---

## Step 6.2: Verify Staging API Availability

**CODE:**
```bash
# Get API Gateway URL
STACK_NAME="CareerVpCrudStaging"
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='Apigateway'].OutputValue" \
  --output text)

echo "Staging API: ${API_URL}"

# Test health endpoint
curl -s "${API_URL}health" | jq '.'
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **YES** - This verifies deployment
- [ ] Health endpoint returns 200 OK
- [ ] Response includes status: "healthy"

---

# PHASE 7: E2E Live Tests

**Goal Validation:** Verify Dev code works correctly in Staging

## Step 7.1: Test Health Endpoint

**CODE:**
```bash
API_URL=$(aws cloudformation describe-stacks \
  --stack-name CareerVpCrudStaging \
  --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='Apigateway'].OutputValue" \
  --output text)

curl -s "${API_URL}health" | jq '.'
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **YES** - This verifies the code works
- [ ] Health endpoint returns 200 OK

---

## Step 7.2: Test Auth Flow

**CODE:**
```bash
API_URL=$(aws cloudformation describe-stacks \
  --stack-name CareerVpCrudStaging \
  --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='Apigateway'].OutputValue" \
  --output text)

# Register a new user
curl -s -X POST "${API_URL}auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@staging.careervp.com",
    "password": "TestPassword123!",
    "name": "Test User"
  }' | jq '.'

# Login
curl -s -X POST "${API_URL}auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@staging.careervp.com",
    "password": "TestPassword123!"
  }' | jq '.'
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **YES** - This verifies auth works
- [ ] Register returns 201 Created
- [ ] Login returns access token

---

## Step 7.3: Test CRUD Operations

**CODE:**
```bash
API_URL=$(aws cloudformation describe-stacks \
  --stack-name CareerVpCrudStaging \
  --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='Apigateway'].OutputValue" \
  --output text)

# Get auth token first (see Step 7.2)
TOKEN="YOUR_ACCESS_TOKEN"

# Test user profile
curl -s "${API_URL}users/me" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Test jobs list
curl -s "${API_URL}jobs" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **YES** - This verifies CRUD works
- [ ] User profile returns user data
- [ ] Jobs list returns job data

---

## Step 7.4: Test Async Flows (VPR, CV Tailoring)

**CODE:**
```bash
API_URL=$(aws cloudformation describe-stacks \
  --stack-name CareerVpCrudStaging \
  --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='Apigateway'].OutputValue" \
  --output text)

TOKEN="YOUR_ACCESS_TOKEN"

# Test VPR generation
curl -s -X POST "${API_URL}vpr/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cv_text": "Experienced software engineer...",
    "target_role": "Senior Software Engineer",
    "country": "USA"
  }' | jq '.'

# Note: VPR is async, poll for status
# Test CV Tailoring
curl -s -X POST "${API_URL}cv-tailoring/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cv_id": "YOUR_CV_ID",
    "job_id": "YOUR_JOB_ID"
  }' | jq '.'
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **YES** - This verifies async flows work
- [ ] VPR endpoint accepts request and returns job ID
- [ ] CV Tailoring endpoint accepts request and returns job ID

---

# PHASE 8: Monitoring & Alerts

**Goal Validation:** Ensure Dev-equivalent observability in Staging

## Step 8.1: Verify CloudWatch Log Groups

**CODE:**
```bash
# Verify Lambda log groups
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/lambda/careervp" \
  --region us-east-1 \
  --query "logGroups[?contains(logGroupName, 'staging')].logGroupName"
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **NO** - This sets up monitoring
- [ ] Log groups with "-staging" suffix exist

---

## Step 8.2: Configure Staging Alerts

**Context:** Configure alerts for staging (may reuse dev alerts).

**CODE:**
```bash
# List existing CloudWatch alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix "careervp" \
  --region us-east-1 \
  --query "MetricAlarms[].AlarmName"
```

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **NO** - This configures monitoring
- [ ] Alarms can be created or reused from dev

---

# PHASE 9: Custom Domain (Optional)

**Goal Validation:** Provide human-readable URL to access Dev code in Staging

## Step 9.1: Document DNS Configuration

**Context:** Note for user to create subdomain in Cloudflare.

**VALIDATION CRITERIA:**
- [ ] PRIMARY GOAL: Does this phase deploy Dev code to Staging? **NO** - This is optional
- [ ] DNS target documented for staging subdomain

---

# VALIDATION COMMANDS

## Pre-Deployment Validation

```bash
# 1. Verify SSM parameters exist
aws ssm get-parameter --name "/careervp/staging/anthropic-api-key" --region us-east-1
aws ssm get-parameter --name "/careervp/staging/jwt-private-key" --region us-east-1
aws ssm get-parameter --name "/careervp/staging/jwt-public-key" --region us-east-1

# 2. Verify configuration file exists
cat infra/careervp/configuration/json/staging_configuration.json | jq .

# 3. Run CDK synth for staging
cd infra
ENVIRONMENT=staging uv run cdk synth CareerVpCrudStaging

# 4. Verify no resource conflicts
ENVIRONMENT=staging uv run cdk diff CareerVpCrudStaging 2>&1 | head -50

# 5. Code quality checks (per best_practices/yaml/code_quality_security_spec.yaml)
cd src/backend
uv run ruff check .                    # Lint check
uv run ruff format --check .            # Format check
uv run mypy careervp --strict          # Type check
uv run bandit -r careervp/ -ll         # Security scan

# 6. Required test cases validation (per spec Section 9)
# Validate auth test coverage
grep -r "test_.*_returns_401" tests/ || echo "WARNING: Missing 401 tests"
grep -r "test_handler_returns_401" tests/ || echo "WARNING: Missing auth 401 tests"
grep -r "test_handler_extracts_user_id_from_jwt" tests/ || echo "WARNING: Missing JWT extraction tests"

# Validate null safety test coverage
grep -r "test_.*_handles_none" tests/ || echo "WARNING: Missing null safety tests"
grep -r "test_handler_handles_empty_list" tests/ || echo "WARNING: Missing empty list tests"

# Run unit tests
uv run pytest tests/unit -v
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
  --query "Stacks[0].Outputs[?OutputKey=='Apigateway'].OutputValue" \
  --output text)

echo "API URL: ${API_URL}"

# 3. Test health endpoint
curl -s "${API_URL}health" | jq '.'

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

# ROLLBACK PROCEDURES

## Rollback via CloudFormation

```bash
# Option 1: CloudFormation rollback
aws cloudformation rollback-stack \
  --stack-name CareerVpCrudStaging \
  --region us-east-1

# Option 2: Delete stack entirely
aws cloudformation delete-stack \
  --stack-name CareerVpCrudStaging \
  --region us-east-1

# Option 3: Re-deploy previous version (requires previous artifact)
# Use GitHub to redeploy a previous commit
```

## Rollback via Git

```bash
# Revert the develop branch to previous commit
git checkout develop
git revert HEAD
git push origin develop

# This will trigger a new deployment with the reverted code
```

---

---

## CODE REVIEW CHECKLIST (per best_practices/yaml/code_quality_security_spec.yaml Section 11)

Before marking a phase as complete, verify:

### Authentication & Authorization
- [ ] user_id comes only from extract_user_id(), never from payload
- [ ] No AUTHORIZER_DISABLED or similar bypasses
- [ ] All handlers use @require_auth or equivalent

### Ownership & Access Control
- [ ] Resources checked for user ownership before access

### Null Safety
- [ ] All result.data access null-checked
- [ ] All optional parameters handled explicitly

### Error Handling
- [ ] No bare `except:` statements
- [ ] All exceptions logged with logger.exception or logger.error

### Security
- [ ] No `Access-Control-Allow-Origin: *` wildcard
- [ ] log_event=False on Lambda decorators
- [ ] No sensitive data in logs

### Type Safety
- [ ] All functions have type hints
- [ ] No `Any` types without justification

### Testing
- [ ] Auth/authorization paths tested
- [ ] Null handling paths tested

---

# COMPLETION CHECKLIST

## Phase 1: Git Branch Setup
- [ ] Step 1.1: Created develop branch from main
- [ ] Step 1.2: Updated branch protection rules
- [ ] Step 1.3: Created GitHub "staging" environment

## Phase 2: Infrastructure Prerequisites
- [ ] Step 2.1: Created staging SSM parameters
- [ ] Step 2.2: Created staging_configuration.json

## Phase 3: GitHub Workflows
- [ ] Step 3.1: Created deploy-staging.yml workflow

## Phase 4: Synthetic Data Generator
- [ ] Step 4.1: Created synthetic data generator script
- [ ] Step 4.2: Generated test data files

## Phase 5: CDK Validation
- [ ] Step 5.1: Ran CDK synth for staging
- [ ] Step 5.2: Verified resource naming

## Phase 6: Deployment
- [ ] Step 6.1: Deployed staging stack
- [ ] Step 6.2: Verified staging API availability

## Phase 7: E2E Live Tests
- [ ] Step 7.1: Tested health endpoint
- [ ] Step 7.2: Tested auth flow
- [ ] Step 7.3: Tested CRUD operations
- [ ] Step 7.4: Tested async flows

## Phase 8: Monitoring & Alerts
- [ ] Step 8.1: Verified CloudWatch log groups
- [ ] Step 8.2: Configured staging alerts

## Phase 9: Custom Domain (Optional)
- [ ] Step 9.1: Documented DNS configuration

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
| **Data** | Synthetic | Synthetic | Production |

---

# APPENDIX B: Cost Estimation

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
**Next Steps:** Begin Phase 1 implementation
