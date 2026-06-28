# CareerVpCrudDev Stack Refactor Runbook: Monitoring Phase 1

Date prepared: 2026-06-12
Region: `us-east-1`
Source stack: `CareerVpCrudDev`
Destination stack: `MonitoringNestedStack`
Scope: create and review a CloudFormation Stack Refactoring plan only. Do not execute until the review criteria pass.

## Verified Inputs

Synthesized templates:

- Parent: `infra/cdk.out/CareerVpCrudDev.template.json`
- Nested monitoring: `infra/cdk.out/CareerVpCrudDevMonitoringNestedStack03847172.nested.template.json`

Template staging URLs to use:

- Parent: `https://s3.us-east-1.amazonaws.com/cdk-hnb659fds-assets-788159322332-us-east-1/41df37fde03261928e2967aea11a858a8cd1c808e56b1c3e92529660a676261c.json`
- Nested: `https://s3.us-east-1.amazonaws.com/cdk-hnb659fds-assets-788159322332-us-east-1/48d27795fbd803f07814761052597d42aebf7600d6e6f3208b8fef236fc0936d.json`

Current validation findings:

- `CareerVpCrudDev` status: `UPDATE_COMPLETE`.
- `MonitoringNestedStack` does not currently exist; `--enable-stack-creation` is required.
- `CareerVpCrudDev` has no stack policy returned by `get-stack-policy`.
- Live deployed resource count: `497`.
- Refactored parent template resource count: `476`, including the new nested stack resource.
- Nested monitoring template resource count: `23`.
- Move mapping count: `22`.
- Moved resource types: `AWS::CloudWatch::Alarm`, `AWS::Logs::MetricFilter`.
- Both moved resource types are `FULLY_MUTABLE`.
- Latest drift detection: `DRIFTED`, `DriftedStackResourceCount=4`, detection completed at `2026-06-12T17:45:09.582000+00:00`.
- `describe-stack-resource-drifts` currently returns these drifted logical IDs outside the move set: `CareerVpCrudDevCognitoUserPoolUserPoolClientFD4D0C15`, `CareerVpCrudDevCrudCareerVpCrudDevCrudHighFacadeCareerVpCrudDevCrudHighFacadeDashboardsDashboard0F3C27FB`, and `CareerVpCrudDevCrudCareerVpCrudDevCrudLowFacadeCareerVpCrudDevCrudLowFacadeDashboardsDashboard7F960C0B`. The dashboards are intentionally excluded from this phase.

AWS references:

- Stack refactoring flow and review: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stack-refactoring.html
- `create-stack-refactor`: https://docs.aws.amazon.com/cli/latest/reference/cloudformation/create-stack-refactor.html

## Preflight

Run from `/Users/yitzchak/Documents/dev/careervp`.

```bash
cd /Users/yitzchak/Documents/dev/careervp

uv run python src/backend/scripts/verify_aws_state.py --mode deployed

aws cloudformation describe-stacks \
  --stack-name CareerVpCrudDev \
  --region us-east-1 \
  --query 'Stacks[0].{StackName:StackName,StackStatus:StackStatus,Drift:DriftInformation,StackId:StackId}' \
  --output json

aws cloudformation get-stack-policy \
  --stack-name CareerVpCrudDev \
  --region us-east-1 \
  --output json

aws cloudformation describe-stack-resource-drifts \
  --stack-name CareerVpCrudDev \
  --region us-east-1 \
  --query 'StackResourceDrifts[?StackResourceDriftStatus!=`IN_SYNC`].{LogicalResourceId:LogicalResourceId,ResourceType:ResourceType,PhysicalResourceId:PhysicalResourceId,DriftStatus:StackResourceDriftStatus}' \
  --output json
```

Abort if:

- `CareerVpCrudDev` is not `CREATE_COMPLETE`, `UPDATE_COMPLETE`, or another steady complete status accepted by CloudFormation for refactoring.
- `get-stack-policy` returns an actual stack policy.
- Any of the 22 mapped resources appears in drift output.
- Any new drift appears on stateful resources, API Gateway, IAM, Lambda config, S3, DynamoDB, Cognito resources being touched, or monitoring resources in the move set.

## Stage Templates

The local parent template is about 671 KB, so use `TemplateURL` rather than inline `TemplateBody`.

```bash
aws s3 cp \
  infra/cdk.out/CareerVpCrudDev.template.json \
  s3://cdk-hnb659fds-assets-788159322332-us-east-1/41df37fde03261928e2967aea11a858a8cd1c808e56b1c3e92529660a676261c.json \
  --region us-east-1

aws s3 cp \
  infra/cdk.out/CareerVpCrudDevMonitoringNestedStack03847172.nested.template.json \
  s3://cdk-hnb659fds-assets-788159322332-us-east-1/48d27795fbd803f07814761052597d42aebf7600d6e6f3208b8fef236fc0936d.json \
  --region us-east-1

aws s3api head-object \
  --bucket cdk-hnb659fds-assets-788159322332-us-east-1 \
  --key 41df37fde03261928e2967aea11a858a8cd1c808e56b1c3e92529660a676261c.json \
  --region us-east-1 \
  --query '{ContentLength:ContentLength,ETag:ETag,LastModified:LastModified}' \
  --output json

aws s3api head-object \
  --bucket cdk-hnb659fds-assets-788159322332-us-east-1 \
  --key 48d27795fbd803f07814761052597d42aebf7600d6e6f3208b8fef236fc0936d.json \
  --region us-east-1 \
  --query '{ContentLength:ContentLength,ETag:ETag,LastModified:LastModified}' \
  --output json
```

Expected content lengths:

- Parent: `671496`
- Nested: `29083`

## Build AWS Resource Mapping

```bash
jq -n \
  --slurpfile map docs/upgrade/stack-refactor-resource-mapping-monitoring-phase1.json \
  '$map[0].mappings | map({
    Source: {
      StackName: "CareerVpCrudDev",
      LogicalResourceId: .source_logical_id
    },
    Destination: {
      StackName: "MonitoringNestedStack",
      LogicalResourceId: .destination_logical_id
    }
  })' \
  > /tmp/careervp-monitoring-phase1-resource-mappings.aws.json

jq 'length' /tmp/careervp-monitoring-phase1-resource-mappings.aws.json
```

Expected mapping length: `22`.

Abort if the generated mapping count is not `22`.

## Create Stack Refactor Preview

This creates the CloudFormation refactor preview. It does not execute the movement.

```bash
aws cloudformation create-stack-refactor \
  --region us-east-1 \
  --description 'CareerVpCrudDev dev us-east-1 phase-1 monitoring nested-stack refactor 2026-06-12' \
  --enable-stack-creation \
  --stack-definitions \
    StackName=CareerVpCrudDev,TemplateURL=https://s3.us-east-1.amazonaws.com/cdk-hnb659fds-assets-788159322332-us-east-1/41df37fde03261928e2967aea11a858a8cd1c808e56b1c3e92529660a676261c.json \
    StackName=MonitoringNestedStack,TemplateURL=https://s3.us-east-1.amazonaws.com/cdk-hnb659fds-assets-788159322332-us-east-1/48d27795fbd803f07814761052597d42aebf7600d6e6f3208b8fef236fc0936d.json \
  --resource-mappings file:///tmp/careervp-monitoring-phase1-resource-mappings.aws.json \
  --output json
```

Capture the returned `StackRefactorId`:

```bash
export STACK_REFACTOR_ID='<returned-stack-refactor-id>'
```

## Review Refactor Status

```bash
aws cloudformation describe-stack-refactor \
  --region us-east-1 \
  --stack-refactor-id "$STACK_REFACTOR_ID" \
  --output json
```

Expected:

- `Status`: `CREATE_COMPLETE`
- `ExecutionStatus`: `AVAILABLE`

Abort if:

- `Status` is not `CREATE_COMPLETE`.
- `ExecutionStatus` is not `AVAILABLE`.
- `StatusReason` reports unsupported resources, validation errors, drift conflicts, template body size problems, dependency errors, or config changes.

## List And Review Actions

```bash
aws cloudformation list-stack-refactor-actions \
  --region us-east-1 \
  --stack-refactor-id "$STACK_REFACTOR_ID" \
  --output json \
  | tee /tmp/careervp-monitoring-phase1-stack-refactor-actions.json
```

Review helpers:

```bash
jq -r '.StackRefactorActions[] | [.Action, .Entity, (.ResourceMapping.Source.LogicalResourceId // "-"), (.ResourceMapping.Destination.LogicalResourceId // "-"), (.PhysicalResourceId // "-"), (.Description // "-")] | @tsv' \
  /tmp/careervp-monitoring-phase1-stack-refactor-actions.json

jq '[.StackRefactorActions[] | select(.Entity=="RESOURCE" and .Action=="MOVE")] | length' \
  /tmp/careervp-monitoring-phase1-stack-refactor-actions.json

jq '[.StackRefactorActions[] | select(.Action=="DELETE" or .Action=="REPLACE")] | length' \
  /tmp/careervp-monitoring-phase1-stack-refactor-actions.json
```

Expected actions:

- `MOVE` for the 22 migrated monitoring resources.
- A stack `CREATE` for `MonitoringNestedStack` is acceptable.
- No `DELETE`.
- No `REPLACE`.
- No stateful resource actions.
- No action for the two excluded dashboards.
- No action for Cognito, API Gateway, Lambda functions, S3, DynamoDB, KMS, SQS, IAM, AppConfig, or Step Functions.
- Action descriptions should indicate no bundled resource configuration changes. Any "configuration changes will be validated during refactor execution" message must be manually reconciled to tag-only CloudFormation ownership changes before proceeding.

Abort if:

- Any migrated resource action is not `MOVE`.
- Any `DELETE` or `REPLACE` appears.
- Any stateful resource appears in the action list.
- Any excluded dashboard appears in the action list.
- Any unsupported type appears in the action list.
- Any action indicates real configuration change beyond CloudFormation ownership/tag metadata movement.
- The total `RESOURCE` `MOVE` count is not `22`.

## Execute Command

Do not run this until all review criteria pass.

```bash
aws cloudformation execute-stack-refactor \
  --region us-east-1 \
  --stack-refactor-id "$STACK_REFACTOR_ID"
```

## Post-Execute Monitoring

Only after an approved execution:

```bash
aws cloudformation describe-stack-refactor \
  --region us-east-1 \
  --stack-refactor-id "$STACK_REFACTOR_ID" \
  --output json

aws cloudformation describe-stacks \
  --stack-name CareerVpCrudDev \
  --region us-east-1 \
  --query 'Stacks[0].{StackName:StackName,StackStatus:StackStatus,Drift:DriftInformation}' \
  --output json

aws cloudformation describe-stacks \
  --stack-name MonitoringNestedStack \
  --region us-east-1 \
  --query 'Stacks[0].{StackName:StackName,StackStatus:StackStatus,Drift:DriftInformation}' \
  --output json
```

Expected final refactor status:

- `Status`: `COMPLETE`
- `ExecutionStatus`: `SUCCEEDED`

## Abort And Rollback Notes

Before `execute-stack-refactor`, abort is simple:

1. Do not run `execute-stack-refactor`.
2. Treat the `StackRefactorId` as discarded.
3. Fix the templates or mapping.
4. Run `create-stack-refactor` again to get a new preview.

There is no `cancel-stack-refactor` AWS CLI command. The available commands are `create-stack-refactor`, `describe-stack-refactor`, `list-stack-refactors`, `list-stack-refactor-actions`, and `execute-stack-refactor`.

If `create-stack-refactor` creates a `MonitoringNestedStack` shell in `REVIEW_IN_PROGRESS` and the preview is rejected, verify it has no moved resources, then remove only that unexecuted shell:

```bash
aws cloudformation describe-stacks \
  --stack-name MonitoringNestedStack \
  --region us-east-1 \
  --query 'Stacks[0].{StackName:StackName,StackStatus:StackStatus,StackId:StackId}' \
  --output json

aws cloudformation delete-stack \
  --stack-name MonitoringNestedStack \
  --region us-east-1
```

After `execute-stack-refactor`, rely on CloudFormation's refactor execution and rollback status. If execution fails, monitor:

```bash
aws cloudformation describe-stack-refactor \
  --region us-east-1 \
  --stack-refactor-id "$STACK_REFACTOR_ID" \
  --output json
```

Escalate immediately if status becomes `EXECUTE_FAILED`, `ROLLBACK_FAILED`, or either stack enters a non-terminal failure status.
