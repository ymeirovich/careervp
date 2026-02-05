# Task 10.2: Cover Letter - CDK Infrastructure

**Status:** Pending
**Spec Reference:** [docs/specs/cover-letter/COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md)
**Depends On:** Task 10.1 (Validation)
**Blocking:** Task 10.6 (Handler)

## Overview

Implement CDK infrastructure for the cover letter generation feature, including Lambda function, API Gateway route, DynamoDB table for artifacts, and monitoring configuration. Lambda is configured with 300-second timeout and 2GB memory to handle LLM calls with Claude Haiku 4.5.

## Todo

### Infrastructure Implementation

- [ ] Create `infra/careervp/constructs/cover_letter_construct.py`
- [ ] Add Lambda function with 300s timeout, 2GB memory
- [ ] Add `/api/cover-letter` POST endpoint to API Gateway
- [ ] Add DynamoDB GSI for cover letter artifacts (if needed)
- [ ] Add IAM permissions for Lambda to access S3, DynamoDB, Bedrock
- [ ] Add CloudWatch Logs and X-Ray tracing
- [ ] Update `infra/careervp/careervp_stack.py` to include Cover Letter construct
- [ ] Define stack constants (memory, timeout, table capacity)

### Test Implementation

- [ ] Create `tests/cover-letter/infrastructure/test_cover_letter_stack.py`
- [ ] Implement 10-15 CDK assertions testing construct structure
- [ ] Test Lambda configuration (memory, timeout, environment)
- [ ] Test API Gateway route creation
- [ ] Test DynamoDB table/GSI configuration
- [ ] Test IAM role permissions
- [ ] Test resource naming and tagging

### Validation & Formatting

- [ ] Run `uv run ruff format infra/`
- [ ] Run `uv run ruff check --fix infra/`
- [ ] Run `uv run mypy infra/ --strict`
- [ ] Run `uv run pytest tests/cover-letter/infrastructure/ -v`

### Commit

- [ ] Commit with message: `infra(cdk): add cover letter Lambda and API Gateway infrastructure`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `infra/careervp/constructs/cover_letter_construct.py` | Cover Letter CDK construct |
| `infra/careervp/constants.py` | Update with cover letter constants |
| `infra/careervp/careervp_stack.py` | Add Cover Letter construct to main stack |
| `tests/cover-letter/infrastructure/test_cover_letter_stack.py` | CDK assertion tests |

### Constants Definition

```python
"""
Infrastructure constants for cover letter generation.
Per docs/specs/cover-letter/COVER_LETTER_SPEC.md Deployment section.
"""

# Lambda configuration
COVER_LETTER_LAMBDA_MEMORY_MB = 2048  # 2 GB for LLM processing
COVER_LETTER_LAMBDA_TIMEOUT_SECONDS = 300  # 5 minutes for Haiku generation
COVER_LETTER_LAMBDA_EPHEMERAL_STORAGE_MB = 512  # Minimal storage needed

# API Gateway
COVER_LETTER_API_PATH = "cover-letter"
COVER_LETTER_API_METHOD = "POST"
COVER_LETTER_REQUEST_TIMEOUT_MS = 299000  # Just under Lambda timeout

# DynamoDB (using existing artifacts table with GSI)
COVER_LETTER_ARTIFACT_PREFIX = "ARTIFACT#COVER_LETTER"
COVER_LETTER_TTL_DAYS = 90  # 90-day retention

# Monitoring
COVER_LETTER_LOG_RETENTION_DAYS = 30
COVER_LETTER_ERROR_ALARM_THRESHOLD = 5  # Errors per minute
COVER_LETTER_LATENCY_ALARM_THRESHOLD_MS = 20000  # 20s p95 target

# Lambda handler
COVER_LETTER_LAMBDA_HANDLER = "handlers.cover_letter_handler.lambda_handler"
COVER_LETTER_LAMBDA_RUNTIME = "python3.11"
```

### Key Implementation Details

#### cover_letter_construct.py

```python
"""
CDK Construct for Cover Letter Generation Infrastructure.

Creates:
- Lambda function for cover letter generation
- API Gateway POST /api/cover-letter route
- IAM roles and permissions
- CloudWatch alarms and dashboards
"""

from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct

from .constants import (
    COVER_LETTER_LAMBDA_MEMORY_MB,
    COVER_LETTER_LAMBDA_TIMEOUT_SECONDS,
    COVER_LETTER_LAMBDA_HANDLER,
    COVER_LETTER_API_PATH,
    COVER_LETTER_LOG_RETENTION_DAYS,
)


class CoverLetterConstruct(Construct):
    """CDK construct for cover letter generation infrastructure."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        api: apigw.RestApi,
        artifacts_table: dynamodb.Table,
        user_pool: cognito.UserPool,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda function
        self.lambda_function = self._create_lambda(artifacts_table)

        # Add API Gateway route
        self._add_api_route(api, user_pool)

        # Add CloudWatch alarms
        self._add_monitoring()

    def _create_lambda(self, artifacts_table: dynamodb.Table) -> lambda_.Function:
        """Create Lambda function for cover letter generation."""
        fn = lambda_.Function(
            self,
            "CoverLetterFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler=COVER_LETTER_LAMBDA_HANDLER,
            code=lambda_.Code.from_asset("src/backend"),
            memory_size=COVER_LETTER_LAMBDA_MEMORY_MB,
            timeout=Duration.seconds(COVER_LETTER_LAMBDA_TIMEOUT_SECONDS),
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                "ARTIFACTS_TABLE_NAME": artifacts_table.table_name,
                "POWERTOOLS_SERVICE_NAME": "cover-letter",
                "POWERTOOLS_METRICS_NAMESPACE": "CareerVP",
                "LOG_LEVEL": "INFO",
            },
        )

        # Grant permissions
        artifacts_table.grant_read_write_data(fn)

        # Add Bedrock permissions for Claude Haiku
        fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["arn:aws:bedrock:*::foundation-model/anthropic.*"],
            )
        )

        return fn

    def _add_api_route(
        self,
        api: apigw.RestApi,
        user_pool: cognito.UserPool,
    ) -> None:
        """Add POST /api/cover-letter route."""
        cover_letter_resource = api.root.add_resource(COVER_LETTER_API_PATH)

        # Cognito authorizer
        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "CoverLetterAuthorizer",
            cognito_user_pools=[user_pool],
        )

        cover_letter_resource.add_method(
            "POST",
            apigw.LambdaIntegration(
                self.lambda_function,
                timeout=Duration.milliseconds(299000),
            ),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

    def _add_monitoring(self) -> None:
        """Add CloudWatch alarms and dashboard."""
        # Error alarm
        self.lambda_function.metric_errors().create_alarm(
            self,
            "CoverLetterErrorAlarm",
            threshold=5,
            evaluation_periods=1,
            alarm_description="Cover letter generation errors exceeded threshold",
        )

        # Latency alarm (p95 > 20s)
        self.lambda_function.metric_duration().create_alarm(
            self,
            "CoverLetterLatencyAlarm",
            threshold=20000,
            evaluation_periods=3,
            alarm_description="Cover letter generation latency exceeded 20s p95",
        )
```

### Test Implementation

#### test_cover_letter_stack.py

```python
"""
CDK assertion tests for Cover Letter infrastructure.
Tests Lambda configuration, API Gateway routes, and IAM permissions.
"""

import pytest
from aws_cdk import App, Stack
from aws_cdk.assertions import Template, Match

from infra.careervp.constructs.cover_letter_construct import CoverLetterConstruct


class TestCoverLetterStack:
    """Test suite for Cover Letter CDK construct."""

    @pytest.fixture
    def template(self) -> Template:
        """Create CDK template for testing."""
        app = App()
        stack = Stack(app, "TestStack")
        # Create construct with mocked dependencies
        # ... setup code
        return Template.from_stack(stack)

    def test_lambda_memory_configuration(self, template: Template) -> None:
        """Test Lambda has 2GB memory."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"MemorySize": 2048},
        )

    def test_lambda_timeout_configuration(self, template: Template) -> None:
        """Test Lambda has 300s timeout."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"Timeout": 300},
        )

    def test_lambda_runtime(self, template: Template) -> None:
        """Test Lambda uses Python 3.11."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"Runtime": "python3.11"},
        )

    def test_lambda_tracing_enabled(self, template: Template) -> None:
        """Test X-Ray tracing is enabled."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"TracingConfig": {"Mode": "Active"}},
        )

    def test_lambda_environment_variables(self, template: Template) -> None:
        """Test Lambda has required environment variables."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "Environment": {
                    "Variables": Match.object_like({
                        "POWERTOOLS_SERVICE_NAME": "cover-letter",
                    })
                }
            },
        )

    def test_api_gateway_post_route(self, template: Template) -> None:
        """Test API Gateway has POST /cover-letter route."""
        template.has_resource_properties(
            "AWS::ApiGateway::Method",
            {"HttpMethod": "POST"},
        )

    def test_api_gateway_cognito_authorizer(self, template: Template) -> None:
        """Test API Gateway uses Cognito authorizer."""
        template.has_resource_properties(
            "AWS::ApiGateway::Authorizer",
            {"Type": "COGNITO_USER_POOLS"},
        )

    def test_lambda_bedrock_permissions(self, template: Template) -> None:
        """Test Lambda has Bedrock invoke permissions."""
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": Match.array_with(["bedrock:InvokeModel"]),
                        })
                    ])
                }
            },
        )

    def test_lambda_dynamodb_permissions(self, template: Template) -> None:
        """Test Lambda has DynamoDB read/write permissions."""
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": Match.array_with([
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                            ]),
                        })
                    ])
                }
            },
        )

    def test_cloudwatch_error_alarm(self, template: Template) -> None:
        """Test CloudWatch error alarm is configured."""
        template.has_resource_properties(
            "AWS::CloudWatch::Alarm",
            {"Threshold": 5},
        )

    def test_cloudwatch_latency_alarm(self, template: Template) -> None:
        """Test CloudWatch latency alarm is configured."""
        template.has_resource_properties(
            "AWS::CloudWatch::Alarm",
            {"Threshold": 20000},
        )

    def test_resource_count(self, template: Template) -> None:
        """Test expected number of resources created."""
        template.resource_count_is("AWS::Lambda::Function", 1)
        template.resource_count_is("AWS::ApiGateway::Method", 1)
        template.resource_count_is("AWS::CloudWatch::Alarm", 2)
```

---

## Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp

# Format infrastructure code
uv run ruff format infra/careervp/constructs/cover_letter_construct.py

# Lint infrastructure code
uv run ruff check --fix infra/careervp/constructs/

# Type check
uv run mypy infra/careervp/constructs/cover_letter_construct.py --strict

# Run CDK tests
uv run pytest tests/cover-letter/infrastructure/test_cover_letter_stack.py -v

# Expected output:
# tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_lambda_memory_configuration PASSED
# tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_lambda_timeout_configuration PASSED
# ... (12 more tests)
# Total: 14 tests PASSED

# Synthesize CDK stack to verify
cdk synth --app "python infra/app.py" CareervpStack
```

---

## Expected Test Results

```
==================== test session starts ====================
platform darwin -- Python 3.11.x, pytest-8.x.x
collected 14 items

tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_lambda_memory_configuration PASSED
tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_lambda_timeout_configuration PASSED
tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_lambda_runtime PASSED
tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_lambda_tracing_enabled PASSED
tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_lambda_environment_variables PASSED
tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_api_gateway_post_route PASSED
tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_api_gateway_cognito_authorizer PASSED
tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_lambda_bedrock_permissions PASSED
tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_lambda_dynamodb_permissions PASSED
tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_cloudwatch_error_alarm PASSED
tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_cloudwatch_latency_alarm PASSED
tests/cover-letter/infrastructure/test_cover_letter_stack.py::TestCoverLetterStack::test_resource_count PASSED

==================== 14 passed in 3.45s ====================
```

---

## Completion Criteria

- [ ] `cover_letter_construct.py` created with Lambda, API Gateway, monitoring
- [ ] Constants added to `constants.py`
- [ ] Main stack updated to include CoverLetterConstruct
- [ ] 14 CDK assertion tests passing
- [ ] `ruff format` passes (no changes)
- [ ] `ruff check` passes (no errors)
- [ ] `mypy --strict` passes (no errors)
- [ ] `cdk synth` succeeds without errors

---

## Common Pitfalls

### Pitfall 1: Wrong Timeout Configuration
**Problem:** Setting timeout too low causes LLM calls to fail.
**Solution:** Use 300 seconds (5 minutes) for cover letter generation.

### Pitfall 2: Missing Bedrock Permissions
**Problem:** Lambda can't invoke Claude Haiku without Bedrock permissions.
**Solution:** Add `bedrock:InvokeModel` IAM policy statement.

### Pitfall 3: API Gateway Timeout Mismatch
**Problem:** API Gateway timeout exceeds Lambda timeout, causing confusing errors.
**Solution:** Set API Gateway timeout to 299000ms (just under Lambda's 300s).

### Pitfall 4: Missing Environment Variables
**Problem:** Lambda fails to find table names or service configuration.
**Solution:** Pass all required env vars: ARTIFACTS_TABLE_NAME, POWERTOOLS_SERVICE_NAME, etc.

---

## Success Checklist

- [ ] Infrastructure construct created
- [ ] Lambda configured with 2GB memory, 300s timeout
- [ ] API Gateway POST /api/cover-letter route added
- [ ] Cognito authorizer configured
- [ ] Bedrock permissions granted
- [ ] DynamoDB permissions granted
- [ ] CloudWatch alarms configured
- [ ] All 14 tests pass
- [ ] CDK synth succeeds
- [ ] Code formatted and type-checked

---

## References

- [COVER_LETTER_DESIGN.md](../../architecture/COVER_LETTER_DESIGN.md) - Architecture decisions
- [COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md) - API specification
- [Phase 9 Task 02](../09-cv-tailoring/task-02-infrastructure.md) - Pattern reference
- [cv_tailoring_construct.py](../../../infra/careervp/constructs/) - Existing pattern
