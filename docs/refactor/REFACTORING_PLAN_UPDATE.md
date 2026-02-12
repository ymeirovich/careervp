# Refactoring Plan Update: Additional Considerations

**Document Version:** 1.0
**Date:** 2026-02-10
**Purpose:** Address gaps in refactoring plan with practical guidance

---

## Table of Contents

1. [Frontend Preparation Strategy](#1-frontend-preparation-strategy)
2. [Data Strategy for Dev-to-Production](#2-data-strategy-for-dev-to-production)
3. [Cost & LLM Economics Monitoring](#3-cost--llm-economics-monitoring)
4. [Environment Configuration Remediation](#4-environment-configuration-remediation)
5. [Monitoring & Observability Gaps](#5-monitoring--observability-gaps)
6. [Compliance & Legal Considerations](#6-compliance--legal-considerations)
7. [External Dependencies Strategy](#7-external-dependencies-strategy)
8. [Testing Strategy Recommendations](#8-testing-strategy-recommendations)
9. [Documentation Gap Analysis](#9-documentation-gap-analysis)
10. [Governance Options](#10-governance-options)
11. [Critical Questions Remediation](#11-critical-questions-remediation)

---

## 1. Frontend Preparation Strategy

### 1.1 The Problem

You don't have UI/UX design yet, but backend refactoring changes API contracts. Frontend will need to adapt.

### 1.2 Preparation Strategy: API-First Design

**Goal:** Design APIs that are frontend-agnostic and flexible enough to accommodate any future design.

#### API Design Principles

```
┌─────────────────────────────────────────────────────────────────┐
│                  API-FIRST DESIGN PRINCIPLES                      │
└─────────────────────────────────────────────────────────────────┘

1. RESPONSE WRAPPERS
   - Standard envelope for all responses
   - Frontend knows what to expect

2. HYPERMEDIA LINKS (HATEOAS)
   - Include next possible actions in responses
   - Decouples frontend from routing logic

3. VERSIONED ENDPOINTS
   - /api/v1/... for current version
   - /api/v2/... for breaking changes

4. BACKWARD COMPATIBILITY
   - Never remove fields, just deprecate
   - Add new fields, never remove old ones
```

#### Standard Response Wrapper

```python
# Standard API response format
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

T = TypeVar('T')

class Status(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    PROCESSING = "processing"

class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    status: Status
    data: Optional[T] = None
    meta: Dict[str, Any] = {}  # Pagination, timing, etc.
    links: Dict[str, str] = {}  # HATEOAS links
    error: Optional[Dict[str, Any]] = None

    @classmethod
    def success(cls, data: T, meta: Dict = None, links: Dict = None) -> ApiResponse:
        return cls(
            status=Status.SUCCESS,
            data=data,
            meta=meta or {},
            links=links or {}
        )

    @classmethod
    def error(cls, code: str, message: str, details: Dict = None) -> ApiResponse:
        return cls(
            status=Status.ERROR,
            error={
                "code": code,
                "message": message,
                "details": details or {}
            }
        )

    @classmethod
    def pending(cls, job_id: str, links: Dict = None) -> ApiResponse:
        return cls(
            status=Status.PENDING,
            data={"job_id": job_id},
            links=links or {}
        )
```

#### Async Response Pattern

```python
# For async operations (VPR, etc.)
class AsyncJobResponse(BaseModel):
    """Response for async job submission."""
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    estimated_completion_seconds: int
    progress_url: str  # Polling endpoint
    result_url: Optional[str] = None  # Available when completed
    error: Optional[str] = None

# Frontend polling flow
# 1. POST /api/v1/vpr/submit → {job_id, status, progress_url}
# 2. GET /api/v1/vpr/jobs/{job_id} → {status, progress_url, result_url}
# 3. When result_url present → GET /api/v1/vpr/results/{job_id}
```

### 1.3 Frontend-Agnostic API Specification

**Create now:** `docs/specs/API_SPEC.md`

```yaml
openapi: 3.0.3
info:
  title: CareerVP API
  version: 1.0.0
  description: API specification for CareerVP - frontend agnostic

servers:
  - url: https://api.careervp.com/api/v1
    description: Production
  - url: https://api.dev.careervp.com/api/v1
    description: Development

paths:
  /vpr/submit:
    post:
      summary: Submit VPR generation job
      responses:
        '202':
          description: Job accepted
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AsyncJobResponse'
        '400':
          $ref: '#/components/responses/ValidationError'
        '401':
          $ref: '#/components/responses/Unauthorized'

components:
  schemas:
    AsyncJobResponse:
      type: object
      properties:
        job_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [pending, processing, completed, failed]
        progress_url:
          type: string
          format: uri
        result_url:
          type: string
          format: uri
        estimated_completion_seconds:
          type: integer
```

### 1.4 Frontend Integration Tasks

| Task | Effort | Purpose |
|------|--------|---------|
| Create OpenAPI spec | 4h | Frontend can generate types/clients |
| Define response wrappers | 2h | Standardize API format |
| Create TypeScript types | 4h | Share with frontend team |
| Document polling contract | 2h | Async operation flow |

---

## 2. Data Strategy for Dev-to-Production

### 2.1 Current State: Dev Environment

- Data can be destroyed/recreated
- No production data constraints
- Freedom to change schemas

### 2.2 Preparation Strategy: Data-Agnostic Architecture

**Goal:** Design systems that work regardless of data volume, with migration paths for production.

#### Schema Versioning Pattern

```python
# models/cv.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserCV(BaseModel):
    """User CV with schema versioning."""

    # Schema versioning
    schema_version: str = "1.0.0"

    # Core fields (never remove)
    cv_id: str
    user_email: str

    # Flexible fields for future expansion
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Soft delete support
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    class Config:
        # Preserve unknown fields during deserialization
        extra = "allow"

    def migrate(self, from_version: str) -> "UserCV":
        """Migrate from older schema version."""
        if from_version == "0.9.0":
            # Migration logic for 0.9.0 → 1.0.0
            self.schema_version = "1.0.0"
            # Map old fields to new structure
        return self
```

#### Seed Data Strategy

```python
# scripts/seed_data.py

"""
Development seed data generator.

Run with: python scripts/seed_data.py --env dev --size 100
"""

import argparse
import uuid
from datetime import datetime, timedelta

class SeedDataGenerator:
    """Generate realistic test data for development."""

    PROFILES = [
        {"role": "Software Engineer", "experience": 5, "skills": ["Python", "AWS", "Docker"]},
        {"role": "Product Manager", "experience": 8, "skills": ["Agile", "JIRA", "Roadmapping"]},
        {"role": "Data Scientist", "experience": 3, "skills": ["Python", "SQL", "ML"]},
        # Add more...
    ]

    def generate_cv(self, profile: dict) -> dict:
        """Generate a realistic CV."""
        return {
            "cv_id": str(uuid.uuid4()),
            "user_email": f"test{uuid.uuid4().hex[:8]}@example.com",
            "schema_version": "1.0.0",
            "personal_info": {
                "name": "Test User",
                "email": "test@example.com",
            },
            "work_experience": [
                {
                    "company": f"Company {i}",
                    "title": profile["role"],
                    "start_date": (datetime.now() - timedelta(days=365 * profile["experience"])).isoformat(),
                    "responsibilities": [
                        f"Responsibility {j} for {profile['role']}"
                        for j in range(5)
                    ]
                }
                for i in range(profile["experience"])
            ],
            "skills": profile["skills"],
        }

    def generate_gap_responses(self, cv_id: str, count: int = 10) -> list:
        """Generate gap responses for CV."""
        questions = [
            "Describe a time you led a team through a difficult project.",
            "Tell me about a failure and what you learned.",
            "How do you handle conflicting priorities?",
        ]
        return [
            {
                "response_id": str(uuid.uuid4()),
                "cv_id": cv_id,
                "question_id": f"q-{i}",
                "question_text": questions[i % len(questions)],
                "response_text": f"Test response {i}",
                "evidence_type": "INTERVIEW_MVP",
            }
            for i in range(count)
        ]
```

### 2.3 Production Readiness Checklist

| Checklist Item | Status | Migration Strategy |
|---------------|--------|-------------------|
| Schema versioning | ☐ Required | Auto-migration on read |
| Soft delete support | ☐ Required | Add `deleted_at` field |
| Audit logging | ☐ Required | Log all writes |
| Backup/restore | ☐ Required | AWS Backup or native |
| Data validation | ☐ Required | Pydantic on all inputs |
| Seed data scripts | ☐ Required | For testing |

### 2.4 Data Migration Tasks

| Task | Effort | When |
|------|--------|------|
| Add schema versioning to models | 2h | Phase 1 |
| Create seed data generator | 4h | Phase 1 |
| Add soft delete support | 2h | Phase 2 |
| Create backup/restore script | 4h | Before prod |
| Document data lifecycle | 2h | Before prod |

---

## 3. Cost & LLM Economics Monitoring

### 3.1 The Challenge

6-stage prompts = 6x LLM calls per operation = **6x cost increase**

### 3.2 Monitoring Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              LLM COST MONITORING ARCHITECTURE                    │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   LLM Call   │───▶│  Cost Tracker│───▶│ CloudWatch   │
│   (Claude)   │    │  (Middleware)│    │   Metrics    │
└──────────────┘    └──────────────┘    └──────────────┘
                                               │
                                               ▼
                                      ┌──────────────┐
                                      │    Alarm     │
                                      │   (SNS/SQS)  │
                                      └──────────────┘
                                               │
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                       ┌──────────┐  ┌──────────┐  ┌──────────┐
                       │  Slack   │  │  Email   │  │  Pause   │
                       │  Alert   │  │  Alert   │  │  Service  │
                       └──────────┘  └──────────┘  └──────────┘
```

### 3.3 Cost Tracking Middleware

```python
# logic/middleware/cost_tracker.py

"""
LLM Cost Tracking Middleware.

Tracks:
- Token usage per request
- Cost per request
- Cumulative daily/monthly costs
- Cost by feature (VPR, CV, Cover Letter)
- Cost by user
"""

from functools import wraps
from typing import Callable, Any, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
import boto3

from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit

import anthropic

logger = Logger()
metrics = Metrics()

# Claude pricing (Haiku 4.5 - subject to change)
CLAUDE_PRICING = {
    "claude-haiku-4-5-20251001": {
        "input_cost_per_million": 0.80,  # $0.80 per million tokens
        "output_cost_per_million": 4.00,  # $4.00 per million tokens
    },
    "claude-sonnet-4-5-20250522": {
        "input_cost_per_million": 3.00,
        "output_cost_per_million": 15.00,
    },
}

@dataclass
class CostMetrics:
    """Metrics for a single LLM call."""
    feature: str  # "vpr", "cv_tailoring", etc.
    user_id: str
    model_id: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    request_id: str

class CostTracker:
    """Track and report LLM costs."""

    def __init__(self, table_name: str = "careervp-cost-tracker"):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)
        self.cloudwatch = boto3.client("cloudwatch")

    def record_call(self, metrics: CostMetrics) -> Dict[str, float]:
        """Record a single LLM call and emit metrics."""
        # Calculate cost
        pricing = CLAUDET_PRICING.get(metrics.model_id, {})
        input_cost = (metrics.input_tokens / 1_000_000) * pricing.get("input_cost_per_million", 0)
        output_cost = (metrics.output_tokens / 1_000_000) * pricing.get("output_cost_per_million", 0)
        total_cost = input_cost + output_cost

        # Emit CloudWatch metrics
        self._emit_metrics(metrics, total_cost)

        # Store for analysis
        self._store_cost(metrics, total_cost)

        return {
            "input_tokens": metrics.input_tokens,
            "output_tokens": metrics.output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
        }

    def _emit_metrics(self, metrics: CostMetrics, cost: float) -> None:
        """Emit CloudWatch metrics."""
        dimensions = [
            {"Name": "Feature", "Value": metrics.feature},
            {"Name": "Model", "Value": metrics.model_id},
        ]

        metrics.add_metric(name="LLMInputTokens", unit=MetricUnit.Count, value=metrics.input_tokens, dimensions=dimensions)
        metrics.add_metric(name="LLMOutputTokens", unit=MetricUnit.Count, value=metrics.output_tokens, dimensions=dimensions)
        metrics.add_metric(name="LLMCost", unit=MetricUnit.Count, value=cost * 1_000_000, dimensions=dimensions)  # Store as cents
        metrics.add_metric(name="LLMLatency", unit=MetricUnit.Milliseconds, value=metrics.latency_ms, dimensions=dimensions)

    def _store_cost(self, metrics: CostMetrics, cost: float) -> None:
        """Store cost data for analysis."""
        self.table.put_item(Item={
            "pk": f"USER#{metrics.user_id}",
            "sk": f"CALL#{metrics.request_id}",
            "feature": metrics.feature,
            "model_id": metrics.model_id,
            "input_tokens": metrics.input_tokens,
            "output_tokens": metrics.output_tokens,
            "cost": cost,
            "timestamp": datetime.utcnow().isoformat(),
            "gsi1pk": f"DATE#{datetime.utcnow().strftime('%Y-%m-%d')}",
        })


def track_cost(feature: str) -> Callable:
    """Decorator to track LLM costs for a function."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracker = CostTracker()
            start_time = datetime.utcnow()

            result = func(*args, **kwargs)

            # Extract metrics from result
            # (Assumes function returns dict with metrics)
            if isinstance(result, dict):
                metrics_data = CostMetrics(
                    feature=feature,
                    user_id=result.get("user_id", "unknown"),
                    model_id=result.get("model_id", "unknown"),
                    input_tokens=result.get("input_tokens", 0),
                    output_tokens=result.get("output_tokens", 0),
                    latency_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    request_id=result.get("request_id", "unknown"),
                )
                tracker.record_call(metrics_data)

            return result
        return wrapper
    return decorator
```

### 3.4 CloudWatch Dashboard

```yaml
# infrastructure/monitoring/cost-dashboard.yaml

AWSTemplateFormatVersion: '2010-09-09'
Description: Cost monitoring dashboard

Resources:
  CostDashboard:
    Type: AWS::CloudWatch::Dashboard
    Properties:
      DashboardName: careervp-cost-monitoring
      DashboardBody:
        {
          "widgets": [
            {
              "type": "metric",
              "x": 0, "y": 0,
              "width": 12, "height": 6,
              "properties": {
                "title": "Daily LLM Cost",
                "metrics": [["CareerVP", "LLMCost", "Feature", "vpr", "Model", "*"]],
                "period": 86400,
                "stat": "Sum",
                "region": "us-east-1"
              }
            },
            {
              "type": "metric",
              "x": 12, "y": 0,
              "width": 12, "height": 6,
              "properties": {
                "title": "Token Usage by Feature",
                "metrics": [["CareerVP", "LLMInputTokens", "Feature", "vpr"], ["CareerVP", "LLMInputTokens", "Feature", "cv_tailoring"]],
                "period": 300,
                "stat": "Sum",
                "region": "us-east-1"
              }
            }
          ]
        }
```

### 3.5 Cost Alerts

```python
# infrastructure/monitoring/cost-alarms.py

from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cw,
    aws_sns as sns,
)
from constructs import Construct

class CostAlarms(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Create SNS topic for alerts
        alert_topic = sns.Topic(self, "CostAlertsTopic")

        # Daily cost alarm
        cw.Alarm(
            self, "DailyCostAlarm",
            metric=cw.Metric(
                namespace="CareerVP",
                metric_name="LLMCost",
                statistic="Sum",
                period=Duration.hours(24),
            ),
            threshold=10.00,  # $10 per day warning
            evaluation_periods=1,
            alarm_description="Daily LLM cost exceeds $10",
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        ).add_alarm_action(cw_actions.SnsAction(alert_topic))

        # Monthly cost alarm
        cw.Alarm(
            self, "MonthlyCostAlarm",
            metric=cw.Metric(
                namespace="CareerVP",
                metric_name="LLMCost",
                statistic="Sum",
                period=Duration.hours(24 * 30),
            ),
            threshold=200.00,  # $200 per month
            evaluation_periods=1,
            alarm_description="Monthly LLM cost exceeds $200",
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        ).add_alarm_action(cw_actions.SnsAction(alert_topic))
```

### 3.6 Cost Monitoring Tasks

| Task | Effort | Priority |
|------|--------|----------|
| Create CostTracker middleware | 4h | P1 |
| Add cost tracking to LLM calls | 2h | P1 |
| Create CloudWatch dashboard | 2h | P2 |
| Configure cost alerts | 2h | P2 |
| Implement usage limits per user | 4h | P2 |

---

## 4. Environment Configuration Remediation

### 4.1 Current State Issues (from AGENTS.md)

- Secrets in plain environment variables
- No centralized config
- Environment-specific settings scattered

### 4.2 Remediation: Centralized Configuration

```python
# config/settings.py

"""
Centralized configuration management.

Supports:
- Environment-specific settings
- Secrets from AWS Secrets Manager
- Feature flags
- Validation
"""

from __future__ import annotations
from functools import lru_cache
from typing import Any, Dict, Optional
import os
import json

import boto3
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class LLMSettings(BaseModel):
    """LLM configuration."""
    default_model: str = "claude-haiku-4-5-20251001"
    sonnet_model: str = "claude-sonnet-4-5-20250522"
    haiku_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: int = 60


class DatabaseSettings(BaseModel):
    """Database configuration."""
    users_table: str = "careervp-users-table-dev"
    jobs_table: str = "careervp-jobs-table-dev"
    cv_table: str = "careervp-cv-table-dev"
    knowledge_table: str = "careervp-knowledge-table-dev"
    region: str = "us-east-1"


class SecuritySettings(BaseModel):
    """Security configuration."""
    jwt_secret_arn: str
    jwt_expiration_hours: int = 24
    api_authorizer_enabled: bool = True


class FeatureFlags(BaseModel):
    """Feature flags for gradual rollout."""
    vpr_6stage: bool = False
    cv_3step: bool = False
    gap_analysis: bool = False
    cover_letter: bool = False
    quality_validator: bool = False
    knowledge_base: bool = False


class Settings(BaseModel):
    """Application settings."""
    env: str = "dev"
    debug: bool = False

    llm: LLMSettings = Field(default_factory=LLMSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    security: SecuritySettings
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    @validator("env")
    def validate_env(cls, v):
        if v not in ["dev", "staging", "prod"]:
            raise ValueError(f"Invalid environment: {v}")
        return v


def get_secrets(secret_arn: str) -> Dict[str, Any]:
    """Retrieve secrets from AWS Secrets Manager."""
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    return json.loads(response["SecretString"])


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)."""
    env = os.environ.get("APP_ENV", "dev")

    # Load secrets from AWS Secrets Manager
    secrets_arn = os.environ.get("SECRETS_ARN")
    secrets = get_secrets(secrets_arn) if secrets_arn else {}

    # Build settings
    return Settings(
        env=env,
        debug=os.environ.get("DEBUG", "").lower() == "true",
        security=SecuritySettings(
            jwt_secret_arn=secrets.get("jwt_secret_arn", os.environ.get("JWT_SECRET_ARN")),
        ),
        features=FeatureFlags(
            vpr_6stage=os.environ.get("FEATURE_VPR_6STAGE", "").lower() == "true",
            cv_3step=os.environ.get("FEATURE_CV_3STEP", "").lower() == "true",
        ),
    )


# Usage
settings = get_settings()
print(f"Environment: {settings.env}")
print(f"VPR 6-Stage enabled: {settings.features.vpr_6stage}")
```

### 4.3 Configuration File Structure

```
config/
├── settings.py              # Settings class definition
├── defaults.yaml            # Default settings for all environments
├── .env.example            # Example environment file
├── schemas/
│   ├── settings.schema.json # JSON Schema for validation
│   └── feature-flags.schema.json
├── secrets/
│   └── README.md           # Secrets management guide
└── templates/
    └── cdk-config.yaml     # CDK configuration template
```

### 4.4 Configuration Tasks

| Task | Effort | Priority |
|------|--------|----------|
| Create Settings class | 4h | P1 |
| Implement AWS Secrets Manager | 4h | P2 |
| Create config validation | 2h | P2 |
| Document configuration | 2h | P2 |

---

## 5. Monitoring & Observability Gaps

### 5.1 What's Missing from plan.md

The plan mentions monitoring but doesn't specify:
- CloudWatch dashboard definitions
- Alert thresholds and escalation
- Distributed tracing
- Error budgets and SLOs
- On-call runbooks

### 5.2 Observability Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                  OBSERVABILITY STACK                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ CloudWatch  │  │    X-Ray   │  │    CloudWatch Logs     │  │
│  │  Metrics    │  │  Tracing   │  │    (Structured JSON)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Dash-     │  │   Alarms    │  │     Grafana (optional) │  │
│  │   boards   │  │  + SNS      │  │     for visualization │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 SLO Definitions

```python
# infrastructure/monitoring/slos.py

"""
Service Level Objectives (SLOs) for CareerVP.

Based on: https://aws.amazon.com/builders-library/fiaws-for-architecting/
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SLO:
    """Service Level Objective."""
    name: str
    description: str
    service: str
    metric: str
    target: float  # percentage (e.g., 99.9)
    window: str  # "daily", "monthly"
    error_budget: float  # allowed failure percentage


CAREERVP_SLOS = [
    # API Availability
    SLO(
        name="api_availability",
        description="API endpoints are reachable",
        service="API Gateway",
        metric="5xxError",
        target=99.9,
        window="monthly",
        error_budget=0.1,  # ~43 minutes downtime allowed
    ),

    # VPR Generation Latency
    SLO(
        name="vpr_generation_latency",
        description="VPR job completes within threshold",
        service="VPR Worker",
        metric="Latency",
        target=95.0,  # 95% of requests
        window="daily",
        error_budget=5.0,  # 5% can be slow
        # Note: VPR is async, so this measures p95 latency
    ),

    # CV Tailoring Latency (sync)
    SLO(
        name="cv_tailoring_latency",
        description="CV tailoring completes within 30 seconds",
        service="CV Tailoring",
        metric="Latency",
        target=99.0,
        window="daily",
        error_budget=1.0,
    ),

    # LLM API Availability
    SLO(
        name="llm_api_availability",
        description="Claude API calls succeed",
        service="Anthropic",
        metric="LLMError",
        target=99.5,
        window="daily",
        error_budget=0.5,
    ),

    # Data Consistency
    SLO(
        name="data_consistency",
        description="Reads reflect latest writes",
        service="DynamoDB",
        metric="EventualConsistency",
        target=100.0,  # Always eventual
        window="daily",
        error_budget=0.0,  # N/A for eventual consistency
    ),
]


def calculate_error_budget_status(slo: SLO, actual_percentage: float) -> dict:
    """Calculate error budget remaining."""
    remaining = slo.target - actual_percentage
    if remaining < 0:
        return {
            "status": "exhausted",
            "remaining_percentage": remaining,
            "severity": "critical" if abs(remaining) > slo.error_budget * 0.8 else "warning",
        }
    return {
        "status": "healthy",
        "remaining_percentage": remaining,
        "severity": "ok",
    }
```

### 5.4 Monitoring Dashboard

```python
# infrastructure/monitoring/operational-dashboard.py

from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cw,
)
from constructs import Construct


class OperationalDashboard(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        dashboard = cw.Dashboard(
            self, "CareerVPOperationalDashboard",
            dashboard_name="careervp-operational",
        )

        # API Gateway metrics
        api_widget = cw.GraphWidget(
            title="API Gateway - Requests & Errors",
            left=[
                cw.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="Count",
                    dimensions_map={"ApiName": "careervp-api"},
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                cw.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="4XXError",
                    dimensions_map={"ApiName": "careervp-api"},
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                cw.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="5XXError",
                    dimensions_map={"ApiName": "careervp-api"},
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
            ],
            width=24,
            height=8,
        )

        # Lambda metrics
        lambda_widget = cw.GraphWidget(
            title="Lambda - Invocations & Errors",
            left=[
                cw.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Invocations",
                    dimensions_map={"FunctionName": "careervp-vpr-worker"},
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                cw.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    dimensions_map={"FunctionName": "careervp-vpr-worker"},
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                cw.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Duration",
                    dimensions_map={"FunctionName": "careervp-vpr-worker"},
                    statistic="p95",
                    period=Duration.minutes(5),
                ),
            ],
            width=24,
            height=8,
        )

        # LLM Cost widget
        cost_widget = cw.GraphWidget(
            title="LLM Costs (Cents)",
            left=[
                cw.Metric(
                    namespace="CareerVP",
                    metric_name="LLMCost",
                    statistic="Sum",
                    period=Duration.hours(24),
                ),
            ],
            width=12,
            height=6,
        )

        dashboard.add_widgets(api_widget)
        dashboard.add_widgets(lambda_widget)
        dashboard.add_widgets(cost_widget)
```

### 5.5 Alerting Rules

```python
# infrastructure/monitoring/alarms.py

from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
)
from constructs import Construct


class MonitoringAlarms(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # SNS topic for all alerts
        alert_topic = sns.Topic(self, "CareerVPAlertTopic")

        # Email subscription for non-critical alerts
        alert_topic.add_subscription(
            sns.EmailSubscription("alerts@careervp.com")
        )

        # PagerDuty for critical alerts (optional)
        # alert_topic.add_subscription(sns.UrlSubscription("https://events.pagerduty.com/v2/enqueue"))

        # 1. API Gateway - 5XX Errors
        cw.Alarm(
            self, "ApiGateway5XXAlarm",
            metric=cw.Metric(
                namespace="AWS/ApiGateway",
                metric_name="5XXError",
                dimensions_map={"ApiName": "careervp-api"},
                statistic="Sum",
                period=Duration.minutes(5),
            ),
            threshold=10,
            evaluation_periods=2,
            alarm_description="High 5XX error rate on API Gateway",
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        ).add_alarm_action(cw_actions.SnsAction(alert_topic))

        # 2. Lambda - Errors
        for function in ["careervp-vpr-worker", "careervp-cv-tailoring"]:
            cw.Alarm(
                self, f"LambdaErrors_{function}",
                metric=cw.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    dimensions_map={"FunctionName": function},
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                threshold=5,
                evaluation_periods=2,
                alarm_description=f"Errors in {function}",
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
            ).add_alarm_action(cw_actions.SnsAction(alert_topic))

        # 3. DynamoDB - Throttled Requests
        cw.Alarm(
            self, "DynamoDBThrottledAlarm",
            metric=cw.Metric(
                namespace="AWS/DynamoDB",
                metric_name="ThrottledRequests",
                dimensions_map={"TableName": "careervp-users-table-dev"},
                statistic="Sum",
                period=Duration.minutes(5),
            ),
            threshold=10,
            evaluation_periods=2,
            alarm_description="DynamoDB throttling detected",
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        ).add_alarm_action(cw_actions.SnsAction(alert_topic))

        # 4. VPR Job Failures
        cw.Alarm(
            self, "VPRJobFailuresAlarm",
            metric=cw.Metric(
                namespace="CareerVP",
                metric_name="VPRJobFailed",
                statistic="Sum",
                period=Duration.hours(1),
            ),
            threshold=5,
            evaluation_periods=1,
            alarm_description="VPR job failure rate exceeds threshold",
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        ).add_alarm_action(cw_actions.SnsAction(alert_topic))
```

### 5.6 Monitoring Tasks

| Task | Effort | Priority |
|------|--------|----------|
| Create CloudWatch dashboard | 4h | P1 |
| Configure SLOs and error budgets | 4h | P1 |
| Set up alerting rules | 4h | P1 |
| Implement distributed tracing (X-Ray) | 4h | P2 |
| Create runbooks | 8h | P2 |

---

## 6. Compliance & Legal Considerations

### 6.1 Compliance Requirements by Phase

| Phase | Requirement | Effort | Priority |
|-------|-------------|--------|----------|
| V1 | PII Detection & Masking | 8h | P1 |
| V1 | GDPR Data Retention | 4h | P2 |
| V2 | User Consent Tracking | 8h | P2 |
| V2 | Audit Log Retention | 4h | P2 |
| V2 | Data Export (GDPR) | 8h | P2 |

### 6.2 PII Detection & Masking

```python
# logic/security/pii_detector.py

"""
PII Detection and Masking.

Detects and masks:
- Email addresses
- Phone numbers
- Social Security Numbers
- Credit card numbers
- Bank account numbers
- Addresses
- Names
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class PIIType(Enum):
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    ADDRESS = "address"
    NAME = "name"
    IP_ADDRESS = "ip_address"


@dataclass
class PIIDetection:
    """Result of PII detection."""
    pii_type: PIIType
    value: str
    start_index: int
    end_index: int
    confidence: float  # 0.0 to 1.0


@dataclass
class MaskedContent:
    """Content with PII masked."""
    text: str
    detections: List[PIIDetection]
    masked_text: str


class PIIDetector:
    """Detect and mask PII in text."""

    # Regex patterns for PII detection
    PATTERNS = {
        PIIType.EMAIL: re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        ),
        PIIType.PHONE: re.compile(
            r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b'
        ),
        PIIType.SSN: re.compile(
            r'\b\d{3}-\d{2}-\d{4}\b'
        ),
        PIIType.CREDIT_CARD: re.compile(
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
        ),
        PIIType.IP_ADDRESS: re.compile(
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ),
    }

    # Higher confidence patterns
    HIGH_CONFIDENCE = [PIIType.EMAIL, PIIType.SSN, PIIType.CREDIT_CARD]

    def detect(self, text: str) -> List[PIIDetection]:
        """Detect PII in text."""
        detections = []

        for pii_type, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                detections.append(PIIDetection(
                    pii_type=pii_type,
                    value=match.group(),
                    start_index=match.start(),
                    end_index=match.end(),
                    confidence=1.0 if pii_type in self.HIGH_CONFIDENCE else 0.8,
                ))

        return detections

    def mask(self, text: str) -> MaskedContent:
        """Detect and mask PII in text."""
        detections = self.detect(text)

        # Sort by start position (reverse order for replacement)
        sorted_detections = sorted(detections, key=lambda d: d.start_index, reverse=True)

        masked_text = text
        for detection in sorted_detections:
            mask_char = "*"
            if detection.pii_type == PIIType.EMAIL:
                mask = f"[{detection.pii_type.value}]"
            elif detection.pii_type == PIIType.CREDIT_CARD:
                mask = "[credit_card]"
            else:
                mask = f"[{detection.pii_type.value}]"

            masked_text = (
                masked_text[:detection.start_index] +
                mask +
                masked_text[detection.end_index:]
            )

        return MaskedContent(
            text=text,
            detections=detections,
            masked_text=masked_text,
        )


class PIIMaskingMiddleware:
    """Middleware to mask PII in logs."""

    def __init__(self):
        self.detector = PIIDetector()

    def process_log(self, log_message: str) -> str:
        """Mask PII in log message."""
        masked = self.detector.mask(log_message)
        if masked.detections:
            return masked.masked_text + f" [PII detected: {[d.pii_type.value for d in masked.detections]}]"
        return log_message
```

### 6.3 Data Retention Policy

```python
# logic/compliance/data_retention.py

"""
Data retention policies for GDPR compliance.

Policies:
- CV data: 2 years after last login
- Gap responses: 2 years after last login
- VPR outputs: 1 year after creation
- Audit logs: 7 years (legal requirement)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class DataCategory(Enum):
    CV_DATA = "cv_data"
    GAP_RESPONSES = "gap_responses"
    VPR_OUTPUT = "vpr_output"
    AUDIT_LOG = "audit_log"


@dataclass
class RetentionPolicy:
    """Data retention policy."""
    category: DataCategory
    retention_days: int
    action_on_expiry: str  # "delete", "anonymize", "archive"


RETENTION_POLICIES = {
    DataCategory.CV_DATA: RetentionPolicy(
        category=DataCategory.CV_DATA,
        retention_days=730,  # 2 years
        action_on_expiry="anonymize",
    ),
    DataCategory.GAP_RESPONSES: RetentionPolicy(
        category=DataCategory.GAP_RESPONSES,
        retention_days=730,  # 2 years
        action_on_expiry="delete",
    ),
    DataCategory.VPR_OUTPUT: RetentionPolicy(
        category=DataCategory.VPR_OUTPUT,
        retention_days=365,  # 1 year
        action_on_expiry="delete",
    ),
    DataCategory.AUDIT_LOG: RetentionPolicy(
        category=DataCategory.AUDIT_LOG,
        retention_days=2555,  # 7 years
        action_on_expiry="archive",  # Move to S3 Glacier
    ),
}


class DataRetentionService:
    """Enforce data retention policies."""

    def __init__(self, dynamodb_table, s3_bucket):
        self.table = dynamodb_table
        self.archive_bucket = s3_bucket

    def check_retention(self, item_category: DataCategory, created_at: datetime) -> dict:
        """Check if item should be deleted/anonymized."""
        policy = RETENTION_POLICIES[item_category]
        expiry_date = created_at + timedelta(days=policy.retention_days)

        if datetime.utcnow() >= expiry_date:
            return {
                "action_required": policy.action_on_expiry,
                "should_delete": True,
                "expiry_date": expiry_date.isoformat(),
            }

        return {
            "action_required": "none",
            "should_delete": False,
            "expiry_date": expiry_date.isoformat(),
        }

    def delete_expired_data(self, category: DataCategory) -> int:
        """Delete or archive expired data."""
        policy = RETENTION_POLICIES[category]
        cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)

        # Query expired items
        response = self.table.query(
            IndexName="created_at-index",
            KeyConditionExpression="created_at < :cutoff",
            ExpressionAttributeValues={
                ":cutoff": cutoff_date.isoformat(),
            },
        )

        deleted_count = 0
        for item in response.get("Items", []):
            if policy.action_on_expiry == "delete":
                self.table.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
                deleted_count += 1
            elif policy.action_on_expiry == "anonymize":
                # Anonymize instead of delete
                self.table.update_item(
                    Key={"pk": item["pk"], "sk": item["sk"]},
                    UpdateExpression="SET personal_info = :anon, #deleted = :true",
                    ExpressionAttributeNames={"#deleted": "is_deleted"},
                    ExpressionAttributeValues={
                        ":anon": {"anonymized": True, "date": datetime.utcnow().isoformat()},
                        ":true": True,
                    },
                )

        return deleted_count
```

### 6.4 Compliance Tasks

| Task | Effort | Priority |
|------|--------|----------|
| Implement PII detector | 4h | P1 |
| Add PII masking to logs | 2h | P1 |
| Create data retention policies | 4h | P2 |
| Implement retention enforcement | 8h | P2 |
| Create GDPR data export | 8h | P2 |
| Document compliance procedures | 4h | P2 |

---

## 7. External Dependencies Strategy

### 7.1 External Dependencies Overview

| Dependency | Purpose | Risk Level | Fallback |
|------------|---------|------------|----------|
| Anthropic Claude | LLM generation | HIGH | None (core feature) |
| LinkedIn | Company research | MEDIUM | Web scraping backup |
| Web Search | Company info | MEDIUM | Multiple providers |
| DynamoDB | Data storage | LOW | Multi-region failover |
| S3 | File storage | LOW | Cross-region replication |

### 7.2 Circuit Breaker Pattern

```python
# logic/resilience/circuit_breaker.py

"""
Circuit Breaker Pattern for External Service Resilience.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Failure threshold exceeded, requests fail immediately
- HALF_OPEN: Testing if service recovered
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Any, Optional
from functools import wraps
import time


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5  # Open after N failures
    success_threshold: int = 2   # Close after N successes (half-open)
    timeout_seconds: int = 60    # Time before attempting half-open
    monitoring_window_seconds: int = 300  # Window for failure counting


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    next_attempt_time: datetime = field(default_factory=datetime.utcnow)


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self._is_blocked():
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Retry after {self.stats.next_attempt_time.isoformat()}"
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _is_blocked(self) -> bool:
        """Check if requests should be blocked."""
        if self.stats.state == CircuitState.CLOSED:
            return False

        if self.stats.state == CircuitState.OPEN:
            if datetime.utcnow() >= self.stats.next_attempt_time:
                self.stats.state = CircuitState.HALF_OPEN
                self.stats.success_count = 0
                self.stats.failure_count = 0
                return False
            return True

        # HALF_OPEN - allow limited requests
        return False

    def _on_success(self) -> None:
        """Handle successful call."""
        if self.stats.state == CircuitState.HALF_OPEN:
            self.stats.success_count += 1
            if self.stats.success_count >= self.config.success_threshold:
                self.stats.state = CircuitState.CLOSED
                self.stats.failure_count = 0
        self.stats.last_success_time = datetime.utcnow()

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.stats.failure_count += 1
        self.stats.last_failure_time = datetime.utcnow()

        if self.stats.state == CircuitState.HALF_OPEN:
            self.stats.state = CircuitState.OPEN
            self.stats.next_attempt_time = datetime.utcnow() + timedelta(
                seconds=self.config.timeout_seconds
            )
        elif self.stats.failure_count >= self.config.failure_threshold:
            self.stats.state = CircuitState.OPEN
            self.stats.next_attempt_time = datetime.utcnow() + timedelta(
                seconds=self.config.timeout_seconds
            )

    def get_status(self) -> dict:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "next_attempt": self.stats.next_attempt_time.isoformat() if self.stats.state == CircuitState.OPEN else None,
        }


# Usage
anthropic_breaker = CircuitBreaker(
    name="anthropic",
    config=CircuitBreakerConfig(
        failure_threshold=3,
        timeout_seconds=120,  # Longer timeout for LLM
    )
)

@anthropic_breaker.call
def call_claude(prompt: str) -> str:
    """Call Claude API with circuit breaker."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-5-20250522",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
```

### 7.3 Fallback Strategies

```python
# logic/resilience/fallbacks.py

"""
Fallback strategies for external service failures.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum


class FallbackStrategy(Enum):
    CACHE = "cache"
    DEGRADED = "degraded"
    QUEUE = "queue"
    FAIL = "fail"


class FallbackHandler(ABC):
    """Base class for fallback handlers."""

    @abstractmethod
    def get_fallback(self, original_call: str, error: Exception) -> Any:
        """Return fallback value or raise."""
        pass


class CacheFallback(FallbackHandler):
    """Fallback to cached value."""

    def __init__(self, cache_ttl_seconds: int = 3600):
        self.cache = {}  # Use Redis/DynamoDB in production
        self.ttl = cache_ttl_seconds

    def get_fallback(self, original_call: str, error: Exception) -> Any:
        """Return cached value if available."""
        if original_call in self.cache:
            cached = self.cache[original_call]
            if cached["expires_at"] > datetime.utcnow():
                return {
                    "source": "cache",
                    "data": cached["data"],
                }
        raise error  # No cache hit


class DegradedFallback(FallbackHandler):
    """Return degraded service response."""

    def get_fallback(self, original_call: str, error: Exception) -> Dict[str, Any]:
        """Return degraded response."""
        return {
            "source": "degraded",
            "message": "Service temporarily unavailable",
            "original_call": original_call,
            "error_type": type(error).__name__,
        }


class QueueFallback(FallbackHandler):
    """Queue request for retry."""

    def __init__(self, sqs_queue_url: str):
        self.queue_url = sqs_queue_url

    def get_fallback(self, original_call: str, error: Exception) -> Dict[str, Any]:
        """Queue request for later processing."""
        # Add to SQS queue for retry
        return {
            "source": "queued",
            "message": "Request queued for processing",
            "queue_position": "TBD",
        }


class CompositeFallback:
    """Compose multiple fallback strategies."""

    def __init__(self):
        self.fallbacks: Dict[FallbackStrategy, FallbackHandler] = {}

    def add_fallback(self, strategy: FallbackStrategy, handler: FallbackHandler):
        self.fallbacks[strategy] = handler

    def execute_with_fallback(
        self,
        original_call: str,
        error: Exception,
        strategies: list = None
    ) -> Any:
        """Try fallbacks in order."""
        strategies = strategies or list(FallbackStrategy)

        for strategy in strategies:
            if strategy in self.fallbacks:
                try:
                    return self.fallbacks[strategy].get_fallback(original_call, error)
                except Exception:
                    continue

        # No fallback succeeded, re-raise original error
        raise error
```

### 7.4 Web Scraping Safeguards

```python
# logic/external/web_scraping.py

"""
Web scraping safeguards for company research.

Guidelines:
- Respect robots.txt
- Rate limiting
- User-Agent disclosure
- Cache responses
"""

import time
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScrapingConfig:
    """Web scraping configuration."""
    rate_limit_requests_per_second: float = 0.5  # 1 request every 2 seconds
    timeout_seconds: int = 30
    max_retries: int = 3
    user_agent: str = "CareerVP/1.0 (research purpose)"
    cache_ttl_hours: int = 24


class WebScraper:
    """Respectful web scraper with safeguards."""

    def __init__(self, config: ScrapingConfig = None):
        self.config = config or ScrapingConfig()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.config.user_agent})
        self.last_request_time = datetime.utcnow()

    def fetch(self, url: str, cache_key: str = None) -> Dict[str, Any]:
        """Fetch URL with rate limiting and safeguards."""
        # Check rate limit
        self._enforce_rate_limit()

        # Check cache
        if cache_key:
            cached = self._get_cache(cache_key)
            if cached:
                return {"source": "cache", "data": cached}

        # Make request with retries
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(
                    url,
                    timeout=self.config.timeout_seconds,
                )
                response.raise_for_status()

                # Cache result
                if cache_key:
                    self._set_cache(cache_key, response.text)

                return {
                    "source": "web",
                    "data": response.text,
                    "url": url,
                    "cached": False,
                }

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting."""
        min_interval = 1.0 / self.config.rate_limit_requests_per_second
        time_since_last = (datetime.utcnow() - self.last_request_time).total_seconds()

        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)

        self.last_request_time = datetime.utcnow()

    def _get_cache(self, key: str) -> Optional[str]:
        """Get cached response (use DynamoDB in production)."""
        # Simplified - use Redis/DynamoDB in production
        return None

    def _set_cache(self, key: str, value: str) -> None:
        """Cache response (use DynamoDB in production)."""
        # Simplified - use Redis/DynamoDB in production
        pass


# Usage for LinkedIn/company research
def research_company(company_name: str) -> Dict[str, Any]:
    """Research company with fallback strategies."""
    # 1. Try official API (LinkedIn)
    try:
        linkedin_data = linkedin_api.get_company(company_name)
        return {"source": "linkedin", "data": linkedin_data}
    except Exception as e:
        logger.warning(f"LinkedIn API failed: {e}")

    # 2. Fall back to web scraping
    try:
        scraper = WebScraper()
        website_content = scraper.fetch(
            f"https://www.linkedin.com/company/{company_name}",
            cache_key=f"company:{company_name}",
        )
        return {"source": "web", "data": website_content}
    except Exception as e:
        logger.warning(f"Web scraping failed: {e}")

    # 3. Return error
    return {"error": "Unable to research company"}
```

### 7.5 Resilience Tasks

| Task | Effort | Priority |
|------|--------|----------|
| Implement CircuitBreaker | 4h | P1 |
| Add fallback handlers | 4h | P2 |
| Implement web scraper safeguards | 4h | P2 |
| Add rate limiting | 2h | P2 |
| Create chaos engineering tests | 8h | P3 |

---

## 8. Testing Strategy Recommendations

### 8.1 Testing Pyramid for CareerVP

```
                    ┌─────────────────────┐
                    │      E2E Tests       │  (5%)
                    │  Critical User Flows │
                    └─────────────────────┘
              ┌───────────────────────────────┐
              │    Integration Tests (15%)     │
              │   Service Interactions         │
              └───────────────────────────────┘
        ┌───────────────────────────────────────────┐
        │           Unit Tests (80%)                │
        │  Functions, Classes, Logic Isolation      │
        └───────────────────────────────────────────┘
```

### 8.2 Test Categories

| Category | Coverage Target | Tools | Purpose |
|----------|-----------------|-------|---------|
| Unit Tests | 80% | pytest, moto, unittest.mock | Logic validation |
| Integration | 60% | pytest, moto | Service interaction |
| Contract | 100% | pytest, schemathesis | API compliance |
| Performance | N/A | locust | Load testing |
| Chaos | N/A | AWS Fault Injection Simulator | Resilience |

### 8.3 Performance Testing

```python
# tests/performance/locustfile.py

"""
Load testing for CareerVP API endpoints.

Run with: locust -f tests/performance/locustfile.py
"""

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


class CareerVPUser(HttpUser):
    """Simulate CareerVP user behavior."""
    wait_time = between(1, 5)

    def on_start(self):
        """User login simulation."""
        response = self.client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "test123",
        })
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task(10)
    def submit_vpr(self):
        """VPR submission - async flow."""
        response = self.client.post("/api/v1/vpr/submit", json={
            "cv_id": "test-cv-123",
            "job_url": "https://example.com/job/123",
        })
        if response.status_code == 202:
            self.job_id = response.json()["job_id"]

    @task(5)
    def poll_vpr_status(self):
        """Poll VPR job status."""
        if hasattr(self, "job_id"):
            self.client.get(f"/api/v1/vpr/jobs/{self.job_id}")

    @task(8)
    def submit_cv_tailoring(self):
        """CV tailoring - sync flow."""
        self.client.post("/api/v1/cv/tailor", json={
            "cv_id": "test-cv-123",
            "job_description": "Software Engineer...",
        })


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize custom metrics."""
    if isinstance(environment.runner, MasterRunner):
        environment.runner.register_message(
            "custom_metrics",
            lambda msg: print(f"Custom metric: {msg.data}"),
        )
```

### 8.4 Chaos Engineering Tests

```python
# tests/chaos/test_resilience.py

"""
Chaos engineering tests for external dependencies.

Tests what happens when:
- LLM API fails
- DynamoDB is throttled
- Network latency increases
"""

import pytest
from unittest.mock import patch, Mock
from moto import mock_aws
import boto3


class TestLLMFailure:
    """Test behavior when LLM API fails."""

    def test_circuit_breaker_opens_after_failures(self):
        """Circuit breaker should open after N failures."""
        from logic.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerError

        breaker = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=3)
        )

        def failing_call():
            raise ConnectionError("LLM API failed")

        # 3 failures should open circuit
        for _ in range(3):
            with pytest.raises(ConnectionError):
                breaker.call(failing_call)

        assert breaker.stats.state.value == "open"

        # Next call should fail with circuit breaker error
        with pytest.raises(CircuitBreakerError):
            breaker.call(failing_call)

    def test_fallback_on_circuit_open(self):
        """Should return fallback when circuit is open."""
        from logic.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

        breaker = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=1)
        )

        def failing_call():
            raise ConnectionError("LLM API failed")

        # Open circuit
        with pytest.raises(ConnectionError):
            breaker.call(failing_call)

        # Should be able to get fallback status
        status = breaker.get_status()
        assert status["state"] == "open"


class TestDynamoDBThrottling:
    """Test behavior under DynamoDB throttling."""

    @pytest.fixture
    def dynamodb(self):
        with mock_aws():
            yield boto3.resource("dynamodb", region_name="us-east-1")

    def test_retry_on_throttling(self, dynamodb):
        """Should retry when DynamoDB throttles."""
        from logic.dal.dynamo_repository import DynamoRepository

        table = dynamodb.create_table(
            TableName="test-table",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )

        repo = DynamoRepository(table_name="test-table")

        # Simulate throttling
        with patch.object(
            repo._table,
            "put_item",
            side_effect=[Exception("ProvisionedThroughputExceededException")] * 2 + [None]
        ):
            # Should succeed after retries
            result = repo.put({"pk": "test", "data": "value"})
            assert result.is_ok()
```

### 8.5 Testing Tasks

| Task | Effort | Priority |
|------|--------|----------|
| Expand unit test coverage to 80% | 16h | P1 |
| Add integration tests for all APIs | 12h | P1 |
| Create contract tests (Schemathesis) | 8h | P2 |
| Implement performance tests (Locust) | 8h | P2 |
| Add chaos engineering tests | 12h | P3 |
| Set up test data factories | 4h | P2 |

---

## 9. Documentation Gap Analysis

### 9.1 Missing Documentation

| Documentation Type | Status | Effort |
|-------------------|--------|--------|
| API Reference (OpenAPI/Swagger) | Missing | 8h |
| On-Call Runbooks | Missing | 8h |
| Architecture Decision Records (ADRs) | Partial | 4h |
| User Guide | Missing | 16h |
| Developer Onboarding | Partial | 4h |
| Deployment Procedures | Partial | 4h |

### 9.2 API Documentation Task

```markdown
<!-- docs/tasks/16-api-documentation/task-01-openapi-spec.md -->

# Task: Create OpenAPI Specification

**Phase:** 2
**Effort:** 8 hours
**Priority:** P2

## Objective

Create comprehensive OpenAPI 3.0 specification for all CareerVP API endpoints.

## Deliverables

1. `docs/api/openapi.yaml` - Complete API specification
2. `docs/api/README.md` - API usage guide
3. Generated HTML documentation (via Redoc or Swagger UI)

## Scope

### Authentication
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/logout

### CV Management
- GET /api/v1/cv/{cv_id}
- POST /api/v1/cv
- PUT /api/v1/cv/{cv_id}
- DELETE /api/v1/cv/{cv_id}

### VPR
- POST /api/v1/vpr/submit
- GET /api/v1/vpr/jobs/{job_id}
- GET /api/v1/vpr/results/{job_id}

### CV Tailoring
- POST /api/v1/cv/tailor

### Gap Analysis
- GET /api/v1/gap/questions
- POST /api/v1/gap/respond

## Validation

- Validate OpenAPI spec with `speccy validate docs/api/openapi.yaml`
- Generate client SDKs to verify compatibility
```

### 9.3 On-Call Runbook Template

```markdown
<!-- docs/runbooks/on_call_template.md -->

# On-Call Runbook: [Incident Type]

**Last Updated:** YYYY-MM-DD
**Owner:** Platform Team

---

## Overview

Brief description of this incident type.

## Severity Levels

| Severity | Description | Response Time |
|----------|-------------|---------------|
| SEV1 | Complete outage | 15 minutes |
| SEV2 | Degraded service | 1 hour |
| SEV3 | Minor impact | 4 hours |

## Symptoms

- List of observable symptoms
- Example log patterns
- Monitoring alerts

## Diagnosis Steps

1. **Check Service Health**
   ```bash
   aws lambda list-functions --query "Functions[?starts_with(Name, 'careervp')]"
   ```

2. **Check CloudWatch Metrics**
   - Navigate to CloudWatch Dashboard
   - Look for elevated error rates
   - Check latency percentiles (p95, p99)

3. **Check Recent Deployments**
   ```bash
   aws codepipeline list-pipeline-executions --name careervp-pipeline
   ```

## Remediation Steps

### Step 1: Immediate Action
```bash
# If SEV1, consider rollback
aws codepipeline start-pipeline-execution --name careervp-pipeline --pipeline-execution-id [PREVIOUS_EXECUTION]
```

### Step 2: Scale Resources
```bash
# Increase Lambda concurrency if throttled
aws lambda put-function-concurrency --function-name careervp-vpr-worker --reserved-concurrent-executions 100
```

### Step 3: Notify Stakeholders
- Post to #careervp-incidents
- Notify on-call lead

## Escalation

| Level | Contact | When |
|-------|---------|------|
| L1 | On-call engineer | Always |
| L2 | Platform lead | SEV1 > 30 min |
| L3 | CTO | SEV1 > 2 hours |

## Post-Incident

- [ ] Create incident report
- [ ] Schedule blameless retro
- [ ] Update this runbook
- [ ] Add monitoring if gap identified

## Related Documents

- [Architecture Diagram](../architecture/system-diagram.png)
- [Runbook Index](../runbooks/README.md)
```

### 9.4 Documentation Tasks

| Task | Effort | Priority |
|------|--------|----------|
| Create OpenAPI specification | 8h | P2 |
| Generate API documentation | 4h | P2 |
| Create on-call runbooks | 8h | P2 |
| Document architecture decisions (ADRs) | 4h | P2 |
| Create developer onboarding guide | 4h | P3 |
| Write user documentation | 16h | P3 |

---

## 10. Governance Options

### 10.1 Governance Models

| Model | Description | Best For |
|-------|-------------|----------|
| **Lightweight** | PR reviews + tests | Small team (<5) |
| **Moderate** | PR reviews + tests + security scan | Growing team (5-15) |
| **Enterprise** | All above + compliance audits | Large team (15+) |

### 10.2 Recommended: Moderate Governance

#### PR Requirements

```yaml
# .github/pull_request_template.md

## Checklist

- [ ] Code follows style guidelines (ruff format/check)
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Documentation updated
- [ ] Security scan passed (trivy)
- [ ] Cost impact assessed (if LLM changes)
- [ ] Breaking changes documented

## Required Reviewers

- 1 code reviewer (any team member)
- 1 domain expert (for feature area)
- Security review (for auth/permission changes)

## Branch Protection

```yaml
# .github/branch-protection.yaml
rules:
  - pattern: main
    required_status_checks:
      - "lint"
      - "test"
      - "security-scan"
    enforce_admins: true
    restrictions:
      required_reviewers: 1
```

#### Change Approval Process

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHANGE APPROVAL PROCESS                        │
└─────────────────────────────────────────────────────────────────┘

1. Developer creates PR
           │
           ▼
2. Automated checks:
   - Linting ✓
   - Unit tests ✓
   - Security scan ✓
           │
           ▼
3. Code Review (1-2 reviewers)
           │
           ▼
4. For breaking changes:
   - Create ADR (Architecture Decision Record)
   - Get approval from Tech Lead
           │
           ▼
5. Merge to main
           │
           ▼
6. Deploy to staging
           │
           ▼
7. Automated E2E tests
           │
           ▼
8. Deploy to production (with approval)
```

#### Architecture Decision Records (ADRs)

```markdown
<!-- docs/adrs/YYYY-MM-DD-decision-title.md -->

# ADR: [Title]

**Status:** [Proposed | Accepted | Deprecated | Superseded by [N]]
**Date:** YYYY-MM-DD

## Context

[Description of the situation that prompted this decision]

## Decision

[What was decided]

## Consequences

### Positive
- [List of positive outcomes]

### Negative
- [List of negative outcomes]

### Neutral
- [List of neutral outcomes]

## Alternatives Considered

- [Option 1] - [Reason for rejection]
- [Option 2] - [Reason for rejection]

## Implementation Notes

[Technical details for implementation]

## Related Documents

- [Links to related ADRs, specs, etc.]
```

### 10.3 Versioning Strategy

```
Version Strategy:

MAJOR.MINOR.PATCH

MAJOR - Breaking changes to API or architecture
MINOR - New features (backward compatible)
PATCH - Bug fixes only

Examples:
- v1.0.0 - Initial release
- v1.1.0 - Added Cover Letter feature
- v1.1.1 - Fixed bug in CV Tailoring
- v2.0.0 - VPR 6-Stage (breaking API changes)
```

### 10.4 Deprecation Strategy

```markdown
## Deprecation Policy

### Timeline

1. **Announce** (Version X.N.0)
   - Add deprecation warning to docs
   - Include deprecation header in code
   - Notify users via blog/email

2. **Support** (Version X.N.0 to X.N+1.0)
   - Feature still works
   - No new development
   - Security fixes only

3. **Remove** (Version X.N+1.0)
   - Remove deprecated code
   - Update migration guide

### Example

```python
# v1.2.0
@deprecated(
    "Use submit_vpr_async() instead. "
    "This method will be removed in v2.0.0"
)
def submit_vpr_sync(self, cv_id: str, job_id: str) -> VPRResponse:
    """Submit VPR synchronously (DEPRECATED)."""
    pass
```
```

### 10.5 Governance Tasks

| Task | Effort | Priority |
|------|--------|----------|
| Create PR template with checklist | 2h | P2 |
| Set up branch protection rules | 2h | P2 |
| Create ADR template and log | 4h | P2 |
| Document deprecation policy | 2h | P3 |
| Set up security scanning | 4h | P2 |

---

## 11. Critical Questions Remediation

### 11.1 Original Questions & Answers

| Question | Remediation |
|----------|-------------|
| What happens to existing CVs? | Schema versioning + auto-migration on read |
| How to test without spending $10,000? | Mock LLM responses for dev; staged rollout for prod |
| What if Claude API is down? | Circuit breaker + fallback (cache/degraded) |
| How do users recover from failed jobs? | Explicit status endpoints + retry UI |
| What are latency SLAs? | Define SLOs (see Section 5) |
| How to handle 100 gap responses? | Pagination + context window management |

### 11.2 Token Overflow Strategy

```python
# logic/context_window_manager.py

"""
Manage context window to prevent token overflow.

Strategies:
1. Truncate least relevant content
2. Summarize older content
3. Priority-based filtering
4. Chunking for very long contexts
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import tiktoken


@dataclass
class TokenBudget:
    """Token budget allocation."""
    system_prompt: int = 2000
    cv_content: int = 8000
    job_description: int = 2000
    gap_responses: int = 4000
    company_research: int = 3000
    output_reserve: int = 2000
    # Total: 21,000 (Claude Haiku 4.5 context: 200K)


@dataclass
class ContextItem:
    """Item for context window."""
    content: str
    priority: int  # Lower = more important
    category: str
    token_count: int


class ContextWindowManager:
    """Manage context window to fit within token limits."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        self.encoding = tiktoken.encoding_for_model(model)
        self.max_tokens = 200000  # Claude Haiku 4.5
        self.budget = TokenBudget()

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))

    def prioritize_and_truncate(
        self,
        items: List[ContextItem],
        target_category: str,
    ) -> List[ContextItem]:
        """Select highest priority items for category, truncate if needed."""
        # Filter to category
        category_items = [i for i in items if i.category == target_category]
        sorted_items = sorted(category_items, key=lambda x: x.priority)

        # Calculate available tokens
        available = getattr(self.budget, target_category)

        # Select items until budget exhausted
        selected = []
        current_tokens = 0

        for item in sorted_items:
            if current_tokens + item.token_count <= available:
                selected.append(item)
                current_tokens += item.token_count
            else:
                # Truncate last item
                remaining = available - current_tokens
                if remaining > 100:  # Minimum meaningful content
                    item.content = self._truncate(item.content, remaining)
                    selected.append(item)
                break

        return selected

    def _truncate(self, text: str, max_tokens: int) -> str:
        """Truncate text to max tokens."""
        tokens = self.encoding.encode(text)
        truncated = tokens[:max_tokens]
        return self.encoding.decode(truncated)

    def build_prompt(
        self,
        system_prompt: str,
        items: List[ContextItem],
    ) -> str:
        """Build complete prompt within token limits."""
        context_parts = []
        total_tokens = self.count_tokens(system_prompt)

        # Add system prompt first
        context_parts.append(system_prompt)

        # Add items by priority across categories
        categories = set(i.category for i in items)
        for category in sorted(categories):
            selected = self.prioritize_and_truncate(items, category)
            for item in selected:
                if total_tokens + item.token_count < self.max_tokens - 2000:
                    context_parts.append(f"\n[{item.category.upper()}]\n{item.content}")
                    total_tokens += item.token_count

        return "\n".join(context_parts)
```

### 11.3 Recovery from Failed Jobs

```python
# logic/jobs/job_recovery.py

"""
Recovery mechanisms for failed async jobs.

Features:
- Automatic retry with exponential backoff
- Manual retry via API
- Job state snapshots for debugging
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
import uuid


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class JobSnapshot:
    """Snapshot of job state for debugging."""
    snapshot_id: str
    job_id: str
    step_name: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any] = None
    error_data: Dict[str, Any] = None
    created_at: datetime


class JobRecoveryService:
    """Handle job recovery and retries."""

    MAX_RETRIES = 3
    RETRY_DELAYS = [60, 300, 900]  # 1 min, 5 min, 15 min

    def __init__(self, jobs_repository, snapshots_repository):
        self.jobs = jobs_repository
        self.snapshots = snapshots_repository

    def schedule_retry(self, job_id: str) -> Dict[str, Any]:
        """Schedule a job for retry."""
        job = self.jobs.get(job_id)

        if job["retry_count"] >= self.MAX_RETRIES:
            return {"error": "Max retries exceeded"}

        retry_delay = self.RETRY_DELAYS[job["retry_count"]]
        job["status"] = JobStatus.RETRYING.value
        job["next_retry_at"] = (datetime.utcnow() + timedelta(seconds=retry_delay)).isoformat()
        job["retry_count"] += 1

        self.jobs.update(job)

        return {
            "job_id": job_id,
            "status": "scheduled",
            "retry_at": job["next_retry_at"],
            "attempts_remaining": self.MAX_RETRIES - job["retry_count"],
        }

    def create_snapshot(self, job_id: str, step_name: str, state: Dict) -> str:
        """Create snapshot for debugging."""
        snapshot = JobSnapshot(
            snapshot_id=str(uuid.uuid4()),
            job_id=job_id,
            step_name=step_name,
            input_data=state.get("input", {}),
            output_data=state.get("output", {}),
            error_data=state.get("error", {}),
            created_at=datetime.utcnow(),
        )

        self.snapshots.put(snapshot)
        return snapshot.snapshot_id

    def get_job_diagnostics(self, job_id: str) -> Dict[str, Any]:
        """Get full diagnostics for failed job."""
        job = self.jobs.get(job_id)
        snapshots = self.snapshots.query(f"JOB#{job_id}")

        return {
            "job": job,
            "snapshots": [
                {
                    "id": s.snapshot_id,
                    "step": s.step_name,
                    "error": s.error_data.get("message") if s.error_data else None,
                    "created_at": s.created_at.isoformat(),
                }
                for s in snapshots
            ],
            "retry_available": job["retry_count"] < self.MAX_RETRIES,
        }
```

### 11.4 Additional Critical Questions

| Question | Answer |
|----------|--------|
| How to roll back a bad deployment? | CDK rollback + database migration rollback scripts |
| How to handle hotfixes? | Fast-track PR (1 reviewer) for SEV1 only |
| How to measure feature adoption? | Analytics events on feature usage |
| How to handle A/B testing? | Feature flags with gradual rollout |

---

## Summary: Additional Tasks Required

| Category | Tasks | Total Effort |
|----------|-------|--------------|
| Frontend Preparation | API spec, TypeScript types | 16h |
| Data Strategy | Schema versioning, seed data | 14h |
| Cost Monitoring | CostTracker, alerts, dashboard | 20h |
| Configuration | Settings class, secrets | 16h |
| Monitoring | Dashboard, alarms, SLOs | 28h |
| Compliance | PII detector, retention | 36h |
| Resilience | Circuit breaker, fallbacks | 20h |
| Testing | Performance, chaos tests | 60h |
| Documentation | API docs, runbooks | 44h |
| Governance | PR template, ADRs, policies | 16h |
| **TOTAL** | | **270h (6-7 weeks)** |

---

**Document Version:** 1.0
**Last Updated:** 2026-02-10

---

**END OF UPDATE**
