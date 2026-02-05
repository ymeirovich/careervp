# Task 9.4: CV Tailoring - Infrastructure

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Task 9.3 (Handler)

## Overview

Integrate the CV tailoring Lambda function into the existing CDK infrastructure. This includes adding constants, creating the Lambda function with appropriate configuration, setting up API Gateway integration, and configuring monitoring.

## Todo

### Constants Updates

- [ ] Add `CV_TAILOR_LAMBDA` constant to `infra/careervp/constants.py`
- [ ] Add `CV_TAILOR_FEATURE` constant for naming
- [ ] Add `GW_RESOURCE_TAILOR` constant for API Gateway resource

### API Construct Updates

- [ ] Add `_add_cv_tailor_lambda_integration()` method to `api_construct.py`
- [ ] Create Lambda function with 512 MB memory, 60s timeout
- [ ] Add API Gateway resource `/api/tailor-cv` with POST method
- [ ] Configure Lambda environment variables
- [ ] Add Lambda to monitoring construct

### IAM Permissions

- [ ] Ensure Lambda role has DynamoDB read/write permissions
- [ ] Ensure Lambda role has Bedrock invoke permissions for Haiku 4.5

### Validation

- [ ] Run `python src/backend/scripts/validate_naming.py --path infra --strict`
- [ ] Run `uv run ruff format infra/`
- [ ] Run `uv run ruff check --fix infra/`
- [ ] Run `uv run mypy infra/ --strict`

### Commit

- [ ] Commit with message: `feat(infra): add CV tailoring Lambda and API Gateway integration`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `infra/careervp/constants.py` | Add new constants |
| `infra/careervp/api_construct.py` | Add Lambda and API Gateway integration |
| `infra/careervp/naming_utils.py` | Naming utility (existing, no changes needed) |

### Key Implementation Details

#### constants.py Updates

```python
# Add to existing constants.py

# CV Tailoring Lambda
CV_TAILOR_LAMBDA = "CVTailor"
CV_TAILOR_FEATURE = "cv-tailor"

# API Gateway Resource for CV Tailoring
GW_RESOURCE_TAILOR = "tailor-cv"

# Lambda Configuration
CV_TAILOR_MEMORY_MB = 512
CV_TAILOR_TIMEOUT_SECONDS = 60
```

#### api_construct.py Updates

Add the following method and integrate into `__init__`:

```python
from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_apigateway,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
)
from constructs import Construct

from infra.careervp import constants


class ApiConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        appconfig_app_name: str,
        is_production_env: bool,
        naming: NamingUtils,
    ) -> None:
        super().__init__(scope, id_)

        # ... existing setup code ...

        # Add CV Tailor Lambda integration
        self.cv_tailor_func = self._add_cv_tailor_lambda_integration(
            api_resource=tailor_resource,  # /api/tailor-cv
            role=self.lambda_role,
            db=self.api_db.db,
            appconfig_app_name=appconfig_app_name,
        )

        # Add to monitoring
        self.monitoring.add_lambda_to_dashboard(
            function=self.cv_tailor_func,
            function_name=constants.CV_TAILOR_LAMBDA,
        )

    def _add_cv_tailor_lambda_integration(
        self,
        api_resource: aws_apigateway.Resource,
        role: iam.Role,
        db: dynamodb.Table,
        appconfig_app_name: str,
    ) -> _lambda.Function:
        """
        Create CV Tailor Lambda function and integrate with API Gateway.

        Per docs/specs/04-cv-tailoring.md:
        - Endpoint: POST /api/tailor-cv
        - Memory: 512 MB
        - Timeout: 60 seconds
        - Uses Haiku 4.5 for cost-efficient processing
        """
        function_name = self.naming.lambda_name(constants.CV_TAILOR_FEATURE)

        # Create CloudWatch Log Group
        log_group = logs.LogGroup(
            self,
            f"{constants.CV_TAILOR_LAMBDA}LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Create Lambda function
        lambda_function = _lambda.Function(
            self,
            constants.CV_TAILOR_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler="careervp.handlers.cv_tailor_handler.lambda_handler",
            function_name=function_name,
            memory_size=constants.CV_TAILOR_MEMORY_MB,
            timeout=Duration.seconds(constants.CV_TAILOR_TIMEOUT_SECONDS),
            role=role,
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,
                "CONFIGURATION_APP": appconfig_app_name,
                "DYNAMODB_TABLE_NAME": db.table_name,
                "LOG_LEVEL": "INFO",
            },
            tracing=_lambda.Tracing.ACTIVE,
            log_group=log_group,
        )

        # Create API Gateway resource and method
        tailor_resource = api_resource.add_resource(constants.GW_RESOURCE_TAILOR)
        tailor_resource.add_method(
            http_method="POST",
            integration=aws_apigateway.LambdaIntegration(
                handler=lambda_function,
                proxy=True,
            ),
            authorization_type=aws_apigateway.AuthorizationType.IAM,
        )

        # Add CORS if needed
        tailor_resource.add_cors_preflight(
            allow_origins=["*"],
            allow_methods=["POST", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
        )

        return lambda_function

    def _build_lambda_role(
        self,
        db: dynamodb.Table,
        idempotency_table: dynamodb.Table,
        cv_bucket: s3.Bucket,
    ) -> iam.Role:
        """Build Lambda execution role with required permissions."""
        role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # DynamoDB permissions
        db.grant_read_write_data(role)
        idempotency_table.grant_read_write_data(role)

        # S3 permissions
        cv_bucket.grant_read(role)

        # Bedrock permissions for Haiku 4.5
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    # Haiku 4.5 model ARN pattern
                    f"arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-haiku-*",
                    # Include Sonnet for potential fallback
                    f"arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-*",
                ],
            )
        )

        # X-Ray tracing permissions
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                ],
                resources=["*"],
            )
        )

        return role
```

### Resource Naming Convention

Per `naming_utils.py`, resources follow this pattern:

| Resource Type | Pattern | Example |
| ------------- | ------- | ------- |
| Lambda | `{prefix}-{feature}-lambda-{env}` | `careervp-cv-tailor-lambda-dev` |
| Log Group | `/aws/lambda/{lambda-name}` | `/aws/lambda/careervp-cv-tailor-lambda-dev` |
| API Resource | `/api/{resource}` | `/api/tailor-cv` |

### Lambda Configuration

| Setting | Value | Rationale |
| ------- | ----- | --------- |
| Memory | 512 MB | Sufficient for Pydantic validation and prompt construction |
| Timeout | 60 seconds | Allows for 3 retries with exponential backoff |
| Runtime | Python 3.12 | Match existing Lambdas |
| Tracing | Active | X-Ray integration for observability |

### IAM Permissions Summary

The Lambda role requires:

1. **DynamoDB**: Read/write to main table (UserCV, JobPosting, CompanyResearch, TailoredCV)
2. **Bedrock**: InvokeModel for Claude Haiku 4.5 and Sonnet 4.5 (fallback)
3. **X-Ray**: PutTraceSegments for distributed tracing
4. **CloudWatch**: Basic execution role (logs)

### API Gateway Configuration

```yaml
Resource: /api/tailor-cv
Method: POST
Authorization: IAM
Integration: Lambda Proxy
CORS:
  AllowOrigins: ["*"]
  AllowMethods: ["POST", "OPTIONS"]
  AllowHeaders: ["Content-Type", "Authorization"]
```

### Monitoring Integration

Add to existing `CrudMonitoring` construct:

```python
# Alarms for CV Tailoring
self.monitoring.add_lambda_alarm(
    function=self.cv_tailor_func,
    metric_name="Errors",
    threshold=5,
    evaluation_periods=1,
    alarm_name=f"{constants.CV_TAILOR_FEATURE}-errors",
)

self.monitoring.add_lambda_alarm(
    function=self.cv_tailor_func,
    metric_name="Duration",
    threshold=55000,  # 55 seconds (near timeout)
    evaluation_periods=2,
    alarm_name=f"{constants.CV_TAILOR_FEATURE}-duration",
)
```

### Zero-Hallucination Checklist

- [ ] Lambda handler path matches: `careervp.handlers.cv_tailor_handler.lambda_handler`
- [ ] Constants use kebab-case for AWS resources: `cv-tailor`
- [ ] Memory and timeout match spec: 512 MB, 60 seconds
- [ ] Bedrock permissions include Haiku 4.5 model pattern
- [ ] Log group retention set to ONE_WEEK (matches other Lambdas)

### Acceptance Criteria

- [ ] `cdk synth` completes without errors
- [ ] Lambda function created with correct name pattern
- [ ] API Gateway resource `/api/tailor-cv` with POST method
- [ ] IAM role has DynamoDB and Bedrock permissions
- [ ] X-Ray tracing enabled
- [ ] CloudWatch alarms configured for errors and duration

---

### Verification & Compliance

1. Run `python src/backend/scripts/validate_naming.py --path infra --strict`
2. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
3. If any path or class signature is missing, report a **BLOCKING ISSUE** and exit.
