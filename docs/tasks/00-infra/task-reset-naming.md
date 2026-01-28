# Task: Infrastructure Naming Convention Reset

## Overview

Reset the CareerVP Dev environment to use strict, human-readable naming conventions instead of CDK auto-generated names. This is a destructive migration that will recreate all AWS resources with proper naming.

## Prerequisites

- AWS CLI configured with appropriate credentials
- CDK CLI installed (`npm install -g aws-cdk`)
- All pending changes committed to version control
- Backup of any critical data in existing resources (DynamoDB tables, S3 buckets)

## Naming Convention

**Format:** `careervp-{feature}-{resource_type}-{env}`

| Resource | Pattern | Example |
|----------|---------|---------|
| Lambda | `careervp-{feature}-lambda-{env}` | `careervp-cv-parser-lambda-dev` |
| DynamoDB | `careervp-{feature}-table-{env}` | `careervp-users-table-dev` |
| S3 Bucket | `careervp-{env}-{purpose}-{region}-{hash}` | `careervp-dev-cvs-use1-a1b2` |
| IAM Role | `careervp-role-{service}-{feature}-{env}` | `careervp-role-lambda-cv-parser-dev` |
| API Gateway | `careervp-{feature}-api-{env}` | `careervp-core-api-dev` |

## Migration Steps

### Step 1: Destroy Current Resources

**WARNING:** This will delete all existing resources. Ensure data is backed up.

```bash
cd /path/to/careervp/infra
cdk destroy --all --force
```

**Verification:**
- Confirm all CloudFormation stacks are deleted
- Check AWS Console for any orphaned resources

### Step 2: Implement NamingUtils Class

Create `infra/careervp/naming_utils.py`:

```python
"""
CareerVP Naming Utilities.
Centralized naming logic for all AWS resources.
"""

from infra.careervp.constants import SERVICE_NAME, ENVIRONMENT


class NamingUtils:
    """Utility class for generating consistent resource names."""

    def __init__(self, environment: str = ENVIRONMENT) -> None:
        self.env = environment
        self.prefix = 'careervp'

    def lambda_name(self, feature: str) -> str:
        """Generate Lambda function name."""
        return f'{self.prefix}-{feature}-lambda-{self.env}'

    def table_name(self, feature: str) -> str:
        """Generate DynamoDB table name."""
        return f'{self.prefix}-{feature}-table-{self.env}'

    def bucket_name(self, purpose: str, region_code: str, hash_suffix: str) -> str:
        """Generate S3 bucket name (must be globally unique)."""
        return f'{self.prefix}-{self.env}-{purpose}-{region_code}-{hash_suffix}'

    def role_name(self, service: str, feature: str) -> str:
        """Generate IAM role name."""
        return f'{self.prefix}-role-{service}-{feature}-{self.env}'

    def api_name(self, feature: str) -> str:
        """Generate API Gateway name."""
        return f'{self.prefix}-{feature}-api-{self.env}'

    def stack_id(self, feature: str) -> str:
        """Generate CDK Stack ID (PascalCase)."""
        feature_pascal = ''.join(word.capitalize() for word in feature.split('-'))
        env_pascal = self.env.capitalize()
        return f'CareerVp{feature_pascal}{env_pascal}'
```

### Step 3: Refactor CDK Stacks and Constructs

Update `infra/careervp/constants.py` to use the new naming convention:

```python
# Before
USERS_TABLE_NAME = "users"
CV_BUCKET_NAME = "cvs"

# After
USERS_TABLE_NAME = "careervp-users-table-dev"
CV_BUCKET_NAME = "careervp-dev-cvs-use1"  # Add hash for uniqueness
```

Update all constructs to use explicit `physical_name` parameters:

```python
# In api_db_construct.py
from infra.careervp.naming_utils import NamingUtils

naming = NamingUtils()

# DynamoDB Table
self.users_table = dynamodb.Table(
    self,
    'UsersTable',
    table_name=naming.table_name('users'),  # careervp-users-table-dev
    ...
)

# Lambda Function
self.cv_parser = lambda_.Function(
    self,
    'CVParser',
    function_name=naming.lambda_name('cv-parser'),  # careervp-cv-parser-lambda-dev
    ...
)
```

### Step 4: Implement NamingValidator Script

The validator script has been created at `src/backend/scripts/validate_naming.py`.

Run the validator:

```bash
cd /path/to/careervp
python src/backend/scripts/validate_naming.py --path infra --verbose
```

**Expected output:** Zero violations after refactoring.

### Step 5: Synthesize and Verify

Generate CloudFormation templates and verify naming:

```bash
cd /path/to/careervp/infra
cdk synth
```

**Verification checklist:**
- [ ] Open `cdk.out/*.template.json`
- [ ] Search for `Resources` section
- [ ] Verify all `AWS::Lambda::Function` resources have explicit `FunctionName`
- [ ] Verify all `AWS::DynamoDB::Table` resources have explicit `TableName`
- [ ] Verify all `AWS::S3::Bucket` resources have explicit `BucketName`
- [ ] Confirm no `${Token[...]}` patterns in physical names

### Step 6: Deploy

Deploy the refactored infrastructure:

```bash
cd /path/to/careervp/infra
cdk deploy --all
```

**Post-deployment verification:**
- [ ] All stacks deployed successfully
- [ ] Lambda functions visible in AWS Console with correct names
- [ ] DynamoDB tables created with correct names
- [ ] S3 buckets created with correct names
- [ ] API Gateway endpoints functional

## Rollback Plan

If deployment fails:

1. Run `cdk destroy --all --force`
2. Revert code changes: `git checkout -- infra/`
3. Redeploy original infrastructure: `cdk deploy --all`

## Files to Modify

| File | Changes |
|------|---------|
| `infra/careervp/constants.py` | Update all resource name constants |
| `infra/careervp/naming_utils.py` | Create new (NamingUtils class) |
| `infra/careervp/api_construct.py` | Use NamingUtils for Lambda names |
| `infra/careervp/api_db_construct.py` | Use NamingUtils for Table/Bucket names |
| `infra/careervp/service_stack.py` | Update stack naming |
| `src/backend/careervp/logic/utils/constants.py` | Sync with infra constants |

## Success Criteria

- [ ] `validate_naming.py` reports zero violations
- [ ] `cdk synth` produces templates with explicit physical names
- [ ] `cdk deploy` succeeds without errors
- [ ] All Lambda functions accessible via API Gateway
- [ ] All unit tests pass
- [ ] Pre-commit hooks pass (including naming validation)

## Codex Directive

This task file is designed for Codex execution. Follow these steps in order:

1. **Read** all files in `infra/careervp/` to understand current structure
2. **Create** `naming_utils.py` as specified in Step 2
3. **Update** `constants.py` with new naming convention
4. **Refactor** each construct file to use NamingUtils
5. **Run** `python src/backend/scripts/validate_naming.py --strict`
6. **Run** `cdk synth` and verify output
7. **Report** any blocking issues following the Escalation Protocol
