# Task 8.7: CDK Integration

**Status:** Not Started
**Spec Reference:** [[docs/specs/02-company-research.md]]
**Priority:** P0

## Overview

Add the company research Lambda function and API Gateway route to the CDK infrastructure stack.

## Todo

### Constants Update (`infra/careervp/constants.py`)

- [ ] Add `COMPANY_RESEARCH_LAMBDA = "CompanyResearch"`
- [ ] Add `GW_RESOURCE_COMPANY_RESEARCH = "company-research"`

### API Construct Update (`infra/careervp/api_construct.py`)

- [ ] Add company-research API Gateway resource
- [ ] Add `_add_company_research_lambda_integration()` method
- [ ] Configure Lambda with:
    - Memory: 512 MB
    - Timeout: 60 seconds
    - Runtime: Python 3.14
- [ ] Add Lambda to monitoring construct
- [ ] Grant outbound HTTP permissions (for web scraping)

### Lambda IAM Permissions

The company research Lambda needs:
- Standard Lambda execution role
- DynamoDB read/write (for caching results)
- Outbound internet access (for web scraping/search)

### Validation

- [ ] Run `cd infra && cdk synth` - verify no errors
- [ ] Run `cd infra && uv run pytest tests/infrastructure/ -v`

### Commit

- [ ] Commit with message: `infra(company-research): add Lambda and API Gateway route`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `infra/careervp/constants.py` | Add COMPANY_RESEARCH constants |
| `infra/careervp/api_construct.py` | Add Lambda and API route |

### Constants Addition

```python
# In constants.py, add:

# Lambda Functions
COMPANY_RESEARCH_LAMBDA = "CompanyResearch"

# API Gateway Resources
GW_RESOURCE_COMPANY_RESEARCH = "company-research"
```

### API Construct Addition

```python
# In api_construct.py __init__ method, add after vpr_resource:

company_research_resource = api_resource.add_resource(constants.GW_RESOURCE_COMPANY_RESEARCH)
self.company_research_func = self._add_company_research_lambda_integration(
    company_research_resource,
    self.lambda_role,
    self.api_db.db,
    appconfig_app_name,
)

# Update monitoring to include new function:
self.monitoring = CrudMonitoring(
    self,
    id_,
    self.rest_api,
    self.api_db.db,
    self.api_db.idempotency_db,
    [self.cv_upload_func, self.vpr_generator_func, self.company_research_func],
)
```

### Lambda Integration Method

```python
def _add_company_research_lambda_integration(
    self,
    api_resource: aws_apigateway.Resource,
    role: iam.Role,
    db: dynamodb.TableV2,
    appconfig_app_name: str,
) -> _lambda.Function:
    """Add company research Lambda with API Gateway integration."""
    log_group = logs.LogGroup(
        self,
        f"{constants.COMPANY_RESEARCH_LAMBDA}LogGroup",
        retention=logs.RetentionDays.ONE_DAY,
        removal_policy=RemovalPolicy.DESTROY,
    )

    lambda_function = _lambda.Function(
        self,
        constants.COMPANY_RESEARCH_LAMBDA,
        runtime=_lambda.Runtime.PYTHON_3_14,
        code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
        handler="careervp.handlers.company_research_handler.lambda_handler",
        environment={
            "DYNAMODB_TABLE_NAME": db.table_name,
            constants.POWERTOOLS_SERVICE_NAME: "careervp-company-research",
            constants.POWER_TOOLS_LOG_LEVEL: "INFO",
            "CONFIGURATION_APP": appconfig_app_name,
            "CONFIGURATION_ENV": constants.ENVIRONMENT,
        },
        tracing=_lambda.Tracing.ACTIVE,
        retry_attempts=0,
        timeout=Duration.seconds(60),  # 60s for web scraping
        memory_size=512,
        role=role,
        log_group=log_group,
        logging_format=_lambda.LoggingFormat.JSON,
        system_log_level_v2=_lambda.SystemLogLevel.INFO,
        architecture=_lambda.Architecture.X86_64,
    )

    # POST /api/company-research
    api_resource.add_method(
        http_method="POST",
        integration=aws_apigateway.LambdaIntegration(handler=lambda_function),
    )

    return lambda_function
```

### API Route Structure

After this change, the API will have:
```
/api
  /cv              POST - CV upload
  /vpr             POST - VPR generation
  /company-research POST - Company research (NEW)
```

### Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/infra

# Synthesize CloudFormation template
cdk synth

# Run infrastructure tests
uv run pytest tests/infrastructure/ -v

# Diff against deployed stack (if deployed)
cdk diff
```

### Commit Instructions

```bash
cd /Users/yitzchak/Documents/dev/careervp
git add infra/careervp/constants.py infra/careervp/api_construct.py
git commit -m "infra(company-research): add Lambda and API Gateway route

- Add COMPANY_RESEARCH_LAMBDA constant
- Add GW_RESOURCE_COMPANY_RESEARCH constant
- Add _add_company_research_lambda_integration() method
- Configure Lambda: 512MB memory, 60s timeout
- Add POST /api/company-research route
- Include in monitoring construct

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Acceptance Criteria

- [ ] `cdk synth` succeeds without errors
- [ ] Lambda configured with 60s timeout (for web scraping)
- [ ] Lambda configured with 512MB memory
- [ ] POST /api/company-research route accessible
- [ ] Lambda included in monitoring dashboard
- [ ] Infrastructure tests pass
