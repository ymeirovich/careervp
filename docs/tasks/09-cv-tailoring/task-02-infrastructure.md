# Task 9.2: CV Tailoring - CDK Infrastructure

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Task 9.1 (Validation)
**Blocking:** Task 9.6 (Handler)

## Overview

Implement CDK infrastructure for the CV tailoring feature, including Lambda function, API Gateway route, DynamoDB table for artifacts, and monitoring configuration. Lambda is configured with 60-second timeout and 3GB memory to handle complex LLM calls.

## Todo

### Infrastructure Implementation

- [ ] Create `infra/careervp/constructs/cv_tailoring_construct.py`
- [ ] Add Lambda function with 60s timeout, 3GB memory
- [ ] Add `/api/cv-tailoring` POST endpoint to API Gateway
- [ ] Add DynamoDB table for tailored CV artifacts
- [ ] Add IAM permissions for Lambda to access S3, DynamoDB, Secrets Manager
- [ ] Add CloudWatch Logs and X-Ray tracing
- [ ] Update `infra/careervp/careervp_stack.py` to include CV Tailoring construct
- [ ] Define stack constants (memory, timeout, table capacity)

### Test Implementation

- [ ] Create `tests/infra/test_cv_tailoring_stack.py`
- [ ] Implement 10-15 CDK assertions testing construct structure
- [ ] Test Lambda configuration (memory, timeout, environment)
- [ ] Test API Gateway route creation
- [ ] Test DynamoDB table configuration
- [ ] Test IAM role permissions
- [ ] Test resource naming and tagging

### Validation & Formatting

- [ ] Run `uv run ruff format infra/`
- [ ] Run `uv run ruff check --fix infra/`
- [ ] Run `uv run mypy infra/ --strict`
- [ ] Run `uv run pytest tests/infra/test_cv_tailoring_stack.py -v`

### Commit

- [ ] Commit with message: `infra(cdk): add CV tailoring Lambda and API Gateway infrastructure`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `infra/careervp/constructs/cv_tailoring_construct.py` | CV Tailoring CDK construct |
| `infra/careervp/constants.py` | Update with CV tailoring constants |
| `infra/careervp/careervp_stack.py` | Add CV Tailoring construct to main stack |
| `tests/infra/test_cv_tailoring_stack.py` | CDK assertion tests |

### Constants Definition

```python
"""
Infrastructure constants for CV tailoring.
Per docs/specs/04-cv-tailoring.md Deployment section.
"""

# Lambda configuration
CV_TAILORING_LAMBDA_MEMORY_MB = 3072  # 3 GB for complex LLM processing
CV_TAILORING_LAMBDA_TIMEOUT_SECONDS = 60
CV_TAILORING_LAMBDA_EPHEMERAL_STORAGE_MB = 10240  # 10 GB

# API Gateway
CV_TAILORING_API_PATH = "cv-tailoring"
CV_TAILORING_API_METHOD = "POST"
CV_TAILORING_REQUEST_TIMEOUT_MS = 59000  # Just under Lambda timeout

# DynamoDB
CV_TAILORING_TABLE_NAME = "cv-tailored-artifacts"
CV_TAILORING_TABLE_READ_CAPACITY = 10
CV_TAILORING_TABLE_WRITE_CAPACITY = 10
CV_TAILORING_TABLE_BILLING_MODE = "PAY_PER_REQUEST"  # Or PROVISIONED for prod
CV_TAILORING_TABLE_RETENTION_DAYS = 90  # Lifecycle policy

# Monitoring
CV_TAILORING_LOG_RETENTION_DAYS = 30
CV_TAILORING_ERROR_ALARM_THRESHOLD = 5  # Errors per minute
CV_TAILORING_LATENCY_ALARM_THRESHOLD_MS = 45000  # ms

# Lambda layers and dependencies
CV_TAILORING_LAMBDA_HANDLER = "handlers.cv_tailoring_handler.handler"
CV_TAILORING_LAMBDA_RUNTIME = "python3.11"
```

### Key Implementation Details

#### cv_tailoring_construct.py

```python
"""
CDK Construct for CV Tailoring Infrastructure.
Per docs/specs/04-cv-tailoring.md Deployment section.

Provisions:
- Lambda function (60s timeout, 3GB memory)
- DynamoDB table for artifacts
- API Gateway integration
- CloudWatch monitoring and alarms
- X-Ray tracing
- IAM permissions
"""

from __future__ import annotations

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway,
    aws_dynamodb,
    aws_iam,
    aws_lambda,
    aws_logs,
    aws_s3,
    aws_xray,
)
from constructs import Construct

from infra.careervp.constants import (
    CV_TAILORING_API_METHOD,
    CV_TAILORING_API_PATH,
    CV_TAILORING_LAMBDA_EPHEMERAL_STORAGE_MB,
    CV_TAILORING_LAMBDA_HANDLER,
    CV_TAILORING_LAMBDA_MEMORY_MB,
    CV_TAILORING_LAMBDA_RUNTIME,
    CV_TAILORING_LAMBDA_TIMEOUT_SECONDS,
    CV_TAILORING_LOG_RETENTION_DAYS,
    CV_TAILORING_REQUEST_TIMEOUT_MS,
    CV_TAILORING_TABLE_BILLING_MODE,
    CV_TAILORING_TABLE_NAME,
    CV_TAILORING_TABLE_RETENTION_DAYS,
)


class CVTailoringConstruct(Construct):\n    \"\"\"CDK Construct for CV Tailoring feature.\"\"\"\n\n    def __init__(\n        self,\n        scope: Construct,\n        construct_id: str,\n        *,\n        api_gateway: aws_apigateway.RestApi,\n        cv_artifacts_bucket: aws_s3.Bucket,\n        job_research_table: aws_dynamodb.Table,\n        lambda_security_group,\n        vpc,\n        **kwargs,\n    ) -> None:\n        \"\"\"\n        Initialize CV Tailoring construct.\n\n        Args:\n            scope: CDK stack scope\n            construct_id: Construct identifier\n            api_gateway: Existing API Gateway for integration\n            cv_artifacts_bucket: S3 bucket for storing tailored CVs\n            job_research_table: DynamoDB table for job research (Phase 8)\n            lambda_security_group: VPC security group for Lambda\n            vpc: VPC for Lambda networking\n            **kwargs: Additional construct arguments\n        \"\"\"\n        super().__init__(scope, construct_id, **kwargs)\n\n        self.lambda_function: aws_lambda.Function | None = None\n        self.artifacts_table: aws_dynamodb.Table | None = None\n        self.api_resource: aws_apigateway.Resource | None = None\n\n        self._create_dynamodb_table()\n        self._create_lambda_function(\n            cv_artifacts_bucket,\n            job_research_table,\n            lambda_security_group,\n            vpc,\n        )\n        self._create_api_integration(api_gateway)\n        self._setup_monitoring()\n\n    def _create_dynamodb_table(self) -> None:\n        \"\"\"Create DynamoDB table for tailored CV artifacts.\n\n        Schema:\n            PK: application_id\n            SK: created_at (timestamp)\n            TTL: expiration (90 days)\n        \"\"\"\n        # PSEUDO-CODE:\n        # self.artifacts_table = aws_dynamodb.Table(\n        #     self, \"CVTailoredArtifacts\",\n        #     table_name=CV_TAILORING_TABLE_NAME,\n        #     partition_key=aws_dynamodb.Attribute(\n        #         name=\"application_id\",\n        #         type=aws_dynamodb.AttributeType.STRING,\n        #     ),\n        #     sort_key=aws_dynamodb.Attribute(\n        #         name=\"created_at\",\n        #         type=aws_dynamodb.AttributeType.STRING,\n        #     ),\n        #     billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,\n        #     time_to_live_attribute=\"expiration_timestamp\",\n        #     removal_policy=RemovalPolicy.RETAIN,\n        #     point_in_time_recovery=True,\n        #     encryption=aws_dynamodb.TableEncryption.AWS_MANAGED,\n        # )\n        # Add GSI for querying by user_id\n        # self.artifacts_table.add_global_secondary_index(\n        #     index_name=\"user_id_created_at_gsi\",\n        #     partition_key=aws_dynamodb.Attribute(\n        #         name=\"user_id\",\n        #         type=aws_dynamodb.AttributeType.STRING,\n        #     ),\n        #     sort_key=aws_dynamodb.Attribute(\n        #         name=\"created_at\",\n        #         type=aws_dynamodb.AttributeType.STRING,\n        #     ),\n        #     read_capacity=CV_TAILORING_TABLE_READ_CAPACITY,\n        #     write_capacity=CV_TAILORING_TABLE_WRITE_CAPACITY,\n        # )\n        pass\n\n    def _create_lambda_function(\n        self,\n        cv_artifacts_bucket: aws_s3.Bucket,\n        job_research_table: aws_dynamodb.Table,\n        lambda_security_group,\n        vpc,\n    ) -> None:\n        \"\"\"Create Lambda function for CV tailoring.\n\n        Configuration:\n        - Runtime: Python 3.11\n        - Memory: 3 GB (for LLM processing)\n        - Timeout: 60 seconds\n        - Ephemeral storage: 10 GB\n        - Tracing: X-Ray enabled\n        - Logging: CloudWatch Logs\n        \"\"\"\n        # PSEUDO-CODE:\n        # self.lambda_function = aws_lambda.Function(\n        #     self, \"CVTailoringFunction\",\n        #     function_name=f\"{Stack.of(self).stack_name}-cv-tailoring\",\n        #     runtime=aws_lambda.Runtime.PYTHON_3_11,\n        #     handler=CV_TAILORING_LAMBDA_HANDLER,\n        #     code=aws_lambda.Code.from_asset(\n        #         path=\"../src/backend\",\n        #         exclude=[\"**/.venv\", \"**/.git\", \"**/tests\"],\n        #     ),\n        #     memory_size=CV_TAILORING_LAMBDA_MEMORY_MB,\n        #     timeout=Duration.seconds(CV_TAILORING_LAMBDA_TIMEOUT_SECONDS),\n        #     ephemeral_storage_size=Size.mebibytes(CV_TAILORING_LAMBDA_EPHEMERAL_STORAGE_MB),\n        #     tracing=aws_lambda.Tracing.ACTIVE,\n        #     logs_retention=aws_logs.RetentionDays(CV_TAILORING_LOG_RETENTION_DAYS),\n        #     environment={\n        #         \"CV_TAILORING_TABLE_NAME\": self.artifacts_table.table_name,\n        #         \"CV_ARTIFACTS_BUCKET\": cv_artifacts_bucket.bucket_name,\n        #         \"LOG_LEVEL\": \"INFO\",\n        #     },\n        #     vpc=vpc,\n        #     security_groups=[lambda_security_group],\n        # )\n        #\n        # Grant permissions\n        # self.artifacts_table.grant_read_write_data(self.lambda_function)\n        # cv_artifacts_bucket.grant_read_write(self.lambda_function)\n        # job_research_table.grant_read_data(self.lambda_function)\n        #\n        # Add Secrets Manager permission for Anthropic API key\n        # secrets_policy = aws_iam.PolicyStatement(\n        #     actions=[\"secretsmanager:GetSecretValue\"],\n        #     resources=[f\"arn:aws:secretsmanager:*:*:secret:anthropic-*\"],\n        # )\n        # self.lambda_function.add_to_role_policy(secrets_policy)\n        pass\n\n    def _create_api_integration(self, api_gateway: aws_apigateway.RestApi) -> None:\n        \"\"\"Integrate Lambda with API Gateway.\n\n        Creates:\n        - POST /api/cv-tailoring route\n        - Request/response models\n        - Integration with Lambda\n        - CORS configuration\n        \"\"\"\n        # PSEUDO-CODE:\n        # api_resource = api_gateway.root.get_resource(\"api\").add_resource(\"cv-tailoring\")\n        # self.api_resource = api_resource\n        #\n        # Request validator with body validation\n        # request_validator = api_gateway.add_request_validator(\n        #     \"cv-tailoring-validator\",\n        #     validate_request_body=True,\n        #     validate_request_parameters=True,\n        # )\n        #\n        # Create request/response models\n        # request_model = api_gateway.add_model(\n        #     \"TailorCVRequestModel\",\n        #     schema=...,  # TailorCVRequest schema\n        # )\n        # response_model = api_gateway.add_model(\n        #     \"TailorCVResponseModel\",\n        #     schema=...,  # TailorCVResponse schema\n        # )\n        #\n        # Integration\n        # api_resource.add_method(\n        #     \"POST\",\n        #     integration=aws_apigateway.LambdaIntegration(\n        #         handler=self.lambda_function,\n        #         proxy=False,  # Use integration response for custom handling\n        #     ),\n        #     request_validator=request_validator,\n        #     request_models={\"application/json\": request_model},\n        # )\n        pass\n\n    def _setup_monitoring(self) -> None:\n        \"\"\"Setup CloudWatch alarms and X-Ray tracing.\n\n        Alarms:\n        - Lambda errors >5/min\n        - Lambda duration >45s\n        - DynamoDB throttling\n        \"\"\"\n        # PSEUDO-CODE:\n        # Lambda error rate alarm\n        # error_alarm = aws_cloudwatch.Alarm(\n        #     self, \"CVTailoringErrorAlarm\",\n        #     metric=self.lambda_function.metric_errors(),\n        #     threshold=CV_TAILORING_ERROR_ALARM_THRESHOLD,\n        #     evaluation_periods=1,\n        # )\n        #\n        # Lambda duration alarm\n        # duration_alarm = aws_cloudwatch.Alarm(\n        #     self, \"CVTailoringDurationAlarm\",\n        #     metric=self.lambda_function.metric_duration(),\n        #     threshold=CV_TAILORING_LATENCY_ALARM_THRESHOLD_MS,\n        #     evaluation_periods=5,\n        # )\n        pass
```

#### careervp_stack.py Integration

```python
\"\"\"
Update careervp_stack.py to include CV Tailoring construct.

PSEUDO-CODE for modification:
\"\"\"

# In careervp_stack.py __init__ method:

from infra.careervp.constructs.cv_tailoring_construct import CVTailoringConstruct

# After existing constructs are created:

# CV Tailoring (Phase 9)
cv_tailoring = CVTailoringConstruct(
    self,
    \"CVTailoring\",
    api_gateway=api_gateway,  # From existing API Gateway construct
    cv_artifacts_bucket=cv_bucket,  # From existing S3 construct
    job_research_table=company_research_table,  # From Phase 8
    lambda_security_group=lambda_sg,
    vpc=vpc,
)

# Export outputs
CfnOutput(\n    self,\n    \"CVTailoringTableName\",\n    value=cv_tailoring.artifacts_table.table_name,\n    export_name=f\"{self.stack_name}-cv-tailoring-table\",\n)\n\nCfnOutput(\n    self,\n    \"CVTailoringLambdaArn\",\n    value=cv_tailoring.lambda_function.function_arn,\n    export_name=f\"{self.stack_name}-cv-tailoring-lambda\",\n)
```

### Test Implementation Structure

```python
"""
CDK Tests for CV Tailoring Infrastructure.
Per tests/infra/test_cv_tailoring_stack.py.

Test categories:
- Lambda function configuration (4 tests)
- API Gateway integration (3 tests)
- DynamoDB table (3 tests)
- IAM permissions (3 tests)
- Monitoring and alarms (2 tests)

Total: 10-15 tests
"""

import pytest
from aws_cdk import assertions as cdk_assertions
from aws_cdk import (
    aws_lambda,
    aws_dynamodb,
    aws_apigateway,
)

from infra.careervp.constructs.cv_tailoring_construct import CVTailoringConstruct


class TestCVTailoringInfrastructure:
    """Test CV Tailoring CDK construct."""

    def test_lambda_function_created(self):
        """Lambda function is created with correct name."""
        # PSEUDO-CODE:
        # template = assertions.Template.from_stack(stack)
        # template.resource_count_is("AWS::Lambda::Function", 1)
        # template.has_resource_properties(
        #     "AWS::Lambda::Function",
        #     {
        #         "Handler": "handlers.cv_tailoring_handler.handler",
        #         "Runtime": "python3.11",
        #     },
        # )
        pass

    def test_lambda_memory_configuration(self):
        """Lambda configured with 3GB memory."""
        # PSEUDO-CODE:
        # template = assertions.Template.from_stack(stack)
        # template.has_resource_properties(
        #     "AWS::Lambda::Function",
        #     {
        #         "MemorySize": 3072,
        #     },
        # )
        pass

    def test_lambda_timeout_configuration(self):
        """Lambda configured with 60 second timeout."""
        # PSEUDO-CODE:
        # template = assertions.Template.from_stack(stack)
        # template.has_resource_properties(
        #     "AWS::Lambda::Function",
        #     {
        #         "Timeout": 60,\n        #     },
        # )
        pass

    def test_lambda_ephemeral_storage(self):
        """Lambda configured with 10GB ephemeral storage."""
        # PSEUDO-CODE:
        # template = assertions.Template.from_stack(stack)
        # template.has_resource_properties(
        #     "AWS::Lambda::Function",
        #     {
        #         "EphemeralStorage": {"Size": 10240},
        #     },
        # )
        pass

    def test_dynamodb_table_created(self):
        """DynamoDB table created for artifacts."""
        # PSEUDO-CODE:
        # template = assertions.Template.from_stack(stack)
        # template.resource_count_is("AWS::DynamoDB::Table", 1)
        # template.has_resource_properties(
        #     "AWS::DynamoDB::Table",
        #     {
        #         "TableName": "cv-tailored-artifacts",
        #     },
        # )
        pass

    def test_dynamodb_partition_key(self):
        """DynamoDB table has correct partition key."""
        # PSEUDO-CODE:
        # template = assertions.Template.from_stack(stack)
        # template.has_resource_properties(
        #     "AWS::DynamoDB::Table",
        #     {
        #         "KeySchema": [\n        #             {"AttributeName": "application_id", "KeyType": "HASH"},\n        #         ],\n        #     },\n        # )
        pass

    def test_dynamodb_gsi_created(self):
        """DynamoDB table has GSI for user_id queries."""
        # PSEUDO-CODE:
        # template = assertions.Template.from_stack(stack)
        # template.has_resource_properties(
        #     "AWS::DynamoDB::Table",
        #     {
        #         "GlobalSecondaryIndexes": [\n        #             {\n        #                 "IndexName": "user_id_created_at_gsi",\n        #             },\n        #         ],\n        #     },\n        # )
        pass

    def test_api_gateway_integration(self):
        """API Gateway has /api/cv-tailoring POST endpoint."""
        # PSEUDO-CODE:
        # template = assertions.Template.from_stack(stack)
        # template.resource_count_is("AWS::ApiGateway::Method", 1)
        # template.has_resource_properties(
        #     "AWS::ApiGateway::Method",
        #     {
        #         "HttpMethod": "POST",\n        #         "RequestParameters": {...},\n        #     },\n        # )
        pass

    def test_lambda_iam_permissions(self):
        """Lambda has IAM permissions for DynamoDB."""
        # PSEUDO-CODE:
        # template = assertions.Template.from_stack(stack)
        # template.has_resource_properties(
        #     "AWS::IAM::Policy",\n        #     {\n        #         \"PolicyDocument\": {\n        #             \"Statement\": [\n        #                 Match.object_like({\n        #                     \"Action\": Match.any_value(),\n        #                     \"Effect\": \"Allow\",\n        #                     \"Resource\": Match.any_value(),\n        #                 }),\n        #             ],\n        #         },\n        #     },\n        # )
        pass

    def test_lambda_s3_permissions(self):
        """Lambda has S3 read/write permissions."""
        # PSEUDO-CODE:
        # template = assertions.Template.from_stack(stack)
        # template.match_resources(\"AWS::IAM::Policy\", Match.object_like({...}))
        pass

    def test_cloudwatch_logs_configured(self):
        """CloudWatch Logs retention configured."""
        # PSEUDO-CODE:
        # template = assertions.Template.from_stack(stack)
        # template.resource_count_is(\"AWS::Logs::LogGroup\", 1)
        pass

    def test_xray_tracing_enabled(self):
        """X-Ray tracing enabled for Lambda."""
        # PSEUDO-CODE:
        # template = assertions.Template.from_stack(stack)
        # template.has_resource_properties(
        #     \"AWS::Lambda::Function\",
        #     {\n        #         \"TracingConfig\": {\"Mode\": \"Active\"},\n        #     },\n        # )
        pass

    def test_lambda_environment_variables(self):
        """Lambda environment variables set correctly."""
        # PSEUDO-CODE:
        # template = assertions.Template.from_stack(stack)
        # template.has_resource_properties(
        #     \"AWS::Lambda::Function\",\n        #     {\n        #         \"Environment\": {\n        #             \"Variables\": {\n        #                 \"CV_TAILORING_TABLE_NAME\": Match.any_value(),\n        #                 \"LOG_LEVEL\": \"INFO\",\n        #             },\n        #         },\n        #     },\n        # )
        pass
```

### Verification Commands

Run these commands to verify infrastructure code:

```bash
# Format code
uv run ruff format infra/

# Check for style issues
uv run ruff check --fix infra/

# Type check with strict mode
uv run mypy infra/ --strict

# Validate CDK construct
uv run cdk synth

# Run infrastructure tests
uv run pytest tests/infra/test_cv_tailoring_stack.py -v

# Expected output:
# ===== test session starts =====
# tests/infra/test_cv_tailoring_stack.py::TestCVTailoringInfrastructure::test_lambda_function_created PASSED
# tests/infra/test_cv_tailoring_stack.py::TestCVTailoringInfrastructure::test_lambda_memory_configuration PASSED
# ... [10-15 total tests]
# ===== 10-15 passed in X.XXs =====
```

### Expected Test Results

```
tests/infra/test_cv_tailoring_stack.py::TestCVTailoringInfrastructure PASSED (10-15 tests)

Lambda Configuration Tests: 4 PASSED
- Memory: 3072 MB
- Timeout: 60 seconds
- Ephemeral storage: 10240 MB
- Runtime: Python 3.11

DynamoDB Configuration Tests: 3 PASSED
- Table created with billing mode PAY_PER_REQUEST
- Partition key: application_id (STRING)
- Sort key: created_at (STRING)
- GSI: user_id_created_at_gsi

API Gateway Tests: 3 PASSED
- Route: POST /api/cv-tailoring
- Request validation enabled
- Lambda integration configured

IAM Permission Tests: 3 PASSED
- DynamoDB read/write access
- S3 read/write access
- Secrets Manager access for API keys

Monitoring Tests: 2 PASSED
- CloudWatch Logs configured (30 day retention)
- X-Ray tracing enabled

Total: 10-15 tests passing
Type checking: 0 errors, 0 warnings
CDK synth: Successful
```

### Zero-Hallucination Checklist

- [ ] Lambda memory exactly 3GB (3072 MB)
- [ ] Lambda timeout exactly 60 seconds
- [ ] DynamoDB table name matches constant
- [ ] All IAM permissions explicitly granted
- [ ] No hardcoded resource names (use constants)
- [ ] CloudWatch log retention set to 30 days
- [ ] X-Ray tracing enabled on Lambda
- [ ] API Gateway route path correct (/api/cv-tailoring)
- [ ] Environment variables documented in code
- [ ] Security groups properly configured

### Acceptance Criteria

- [ ] Lambda function provisioned with 60s timeout, 3GB memory
- [ ] DynamoDB table created with TTL for 90-day retention
- [ ] API Gateway route `/api/cv-tailoring` POST configured
- [ ] Lambda has IAM permissions for S3, DynamoDB, Secrets Manager
- [ ] CloudWatch monitoring and alarms set up
- [ ] X-Ray tracing enabled for debugging
- [ ] All infrastructure code uses constants (no magic numbers)
- [ ] 10-15 CDK assertion tests all passing
- [ ] Type checking passes with `mypy --strict`
- [ ] `cdk synth` produces valid CloudFormation template

---

### Verification & Compliance

1. Run `python src/backend/scripts/validate_naming.py --path infra --strict`
2. Run `uv run cdk synth && uv run cdk diff`
3. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
4. Run `uv run pytest tests/infra/test_cv_tailoring_stack.py -v --cov`
5. If any infrastructure is misconfigured, report a **BLOCKING ISSUE** and exit.
