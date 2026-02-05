# Task 7.1: VPR Async Infrastructure Deployment

**Status:** Not Started
**Spec Reference:** [[docs/specs/07-vpr-async-architecture.md]]
**Priority:** P0 (BLOCKING - Production VPR generation fails 100%)

## Overview

Deploy async infrastructure for VPR generation: SQS queue, DynamoDB jobs table, S3 results bucket, and CloudWatch alarms. This task creates NEW resources without modifying existing synchronous VPR endpoint.

## Prerequisites

- [ ] Phase 0 infrastructure reset complete (kebab-case naming enforced)
- [ ] Existing `careervp-users-table-dev` deployed
- [ ] Existing `careervp-idempotency-table-dev` deployed
- [ ] AWS CDK v2 installed (`npm install -g aws-cdk`)

## Todo

### 1. SQS Queue + DLQ

**File:** `infra/careervp/api_construct.py`

- [ ] Add SQS queue import: `from aws_cdk import aws_sqs`
- [ ] Create Dead Letter Queue (DLQ)
  - Queue name: `careervp-vpr-jobs-dlq-dev`
  - Retention period: 14 days
- [ ] Create VPR Jobs Queue
  - Queue name: `careervp-vpr-jobs-queue-dev`
  - Visibility timeout: 660 seconds (11 minutes)
  - Receive message wait time: 20 seconds (long polling)
  - Retention period: 4 hours
  - Dead letter queue: Max 3 retries
- [ ] Export queue URL as stack output

### 2. DynamoDB Jobs Table

**File:** `infra/careervp/api_db_construct.py` or `api_construct.py`

- [ ] Create `careervp-jobs-table-dev` table
  - Partition key: `job_id` (String)
  - Billing mode: PAY_PER_REQUEST
  - TTL attribute: `ttl`
  - Removal policy: DESTROY (dev), RETAIN (prod)
- [ ] Add Global Secondary Index (GSI)
  - Index name: `idempotency-key-index`
  - Partition key: `idempotency_key` (String)
  - Projection type: ALL
- [ ] Export table name as stack output

### 3. S3 Results Bucket

**File:** `infra/careervp/api_construct.py`

- [ ] Create S3 bucket with unique suffix
  - Bucket name: `careervp-dev-vpr-results-{region}-{id_suffix}`
  - Encryption: S3_MANAGED
  - Block public access: BLOCK_ALL
  - Versioned: False
- [ ] Add lifecycle rule
  - ID: `DeleteOldResults`
  - Expiration: 7 days
- [ ] Set removal policy: DESTROY (dev), RETAIN (prod)
- [ ] Enable auto-delete objects for dev environment
- [ ] Export bucket name as stack output

### 4. CloudWatch Alarms

**File:** `infra/careervp/api_construct.py`

- [ ] Create DLQ Alarm
  - Alarm name: `careervp-vpr-dlq-alarm-dev`
  - Metric: `ApproximateNumberOfMessagesVisible` on DLQ
  - Threshold: ≥1 message
  - Evaluation periods: 1
  - Treat missing data: NOT_BREACHING
- [ ] Create Worker Errors Alarm (placeholder for now, will add after worker Lambda)
  - Alarm name: `careervp-vpr-worker-errors-alarm-dev`
  - Metric: Worker Lambda errors
  - Threshold: >5% error rate over 5 minutes

### 5. CDK Synth & Validation

- [ ] Run naming validator: `python src/backend/scripts/validate_naming.py --path infra --strict`
- [ ] Fix any naming violations
- [ ] Run `cdk synth` and verify CloudFormation template
- [ ] Verify resource names in `cdk.out/CareervpServiceStack-dev.template.json`
- [ ] Check for CDK tokens: `grep -r "Token\[" infra/cdk.out/`

### 6. Deployment

- [ ] Deploy infrastructure: `cd infra && cdk deploy --all --require-approval never`
- [ ] Verify deployment in AWS Console:
  - SQS: Queue + DLQ exist with correct configuration
  - DynamoDB: Jobs table exists with GSI
  - S3: Results bucket exists with lifecycle rule
  - CloudWatch: Alarms exist
- [ ] Run AWS state verifier: `python src/backend/scripts/verify_aws_state.py --mode deployed`

## Codex Implementation Guide

### CDK Code Example: SQS Queue

```python
# infra/careervp/api_construct.py

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_sqs,
    aws_dynamodb,
    aws_s3,
    aws_cloudwatch,
)

class ApiConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, env: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # 1. CREATE DLQ
        self.vpr_jobs_dlq = aws_sqs.Queue(
            self, "VprJobsDLQ",
            queue_name=f"careervp-vpr-jobs-dlq-{env}",
            retention_period=Duration.days(14)
        )

        # 2. CREATE VPR JOBS QUEUE
        self.vpr_jobs_queue = aws_sqs.Queue(
            self, "VprJobsQueue",
            queue_name=f"careervp-vpr-jobs-queue-{env}",
            visibility_timeout=Duration.seconds(660),  # 11 minutes
            receive_message_wait_time=Duration.seconds(20),  # Long polling
            retention_period=Duration.hours(4),
            dead_letter_queue=aws_sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=self.vpr_jobs_dlq
            )
        )
```

### CDK Code Example: DynamoDB Jobs Table

```python
# infra/careervp/api_db_construct.py or api_construct.py

# 3. CREATE JOBS TABLE
self.jobs_table = aws_dynamodb.Table(
    self, "JobsTable",
    table_name=f"careervp-jobs-table-{env}",
    partition_key=aws_dynamodb.Attribute(
        name="job_id",
        type=aws_dynamodb.AttributeType.STRING
    ),
    billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
    time_to_live_attribute="ttl",
    removal_policy=RemovalPolicy.DESTROY if env == "dev" else RemovalPolicy.RETAIN
)

# Add GSI for idempotency key lookup
self.jobs_table.add_global_secondary_index(
    index_name="idempotency-key-index",
    partition_key=aws_dynamodb.Attribute(
        name="idempotency_key",
        type=aws_dynamodb.AttributeType.STRING
    ),
    projection_type=aws_dynamodb.ProjectionType.ALL
)
```

### CDK Code Example: S3 Results Bucket

```python
# 4. CREATE S3 RESULTS BUCKET
# Generate unique suffix for bucket name
id_suffix = Stack.of(self).stack_id.split("/")[-1][:6].lower()

self.vpr_results_bucket = aws_s3.Bucket(
    self, "VprResultsBucket",
    bucket_name=f"careervp-{env}-vpr-results-{Stack.of(self).region}-{id_suffix}",
    encryption=aws_s3.BucketEncryption.S3_MANAGED,
    block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
    versioned=False,
    lifecycle_rules=[
        aws_s3.LifecycleRule(
            id="DeleteOldResults",
            enabled=True,
            expiration=Duration.days(7)
        )
    ],
    removal_policy=RemovalPolicy.DESTROY if env == "dev" else RemovalPolicy.RETAIN,
    auto_delete_objects=True if env == "dev" else False
)
```

### CDK Code Example: CloudWatch Alarms

```python
# 5. CREATE CLOUDWATCH ALARMS
aws_cloudwatch.Alarm(
    self, "VprJobsDLQAlarm",
    alarm_name=f"careervp-vpr-dlq-alarm-{env}",
    metric=self.vpr_jobs_dlq.metric_approximate_number_of_messages_visible(),
    threshold=1,
    evaluation_periods=1,
    datapoints_to_alarm=1,
    comparison_operator=aws_cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
    treat_missing_data=aws_cloudwatch.TreatMissingData.NOT_BREACHING
)

# Worker errors alarm (will be updated in task-03 after worker Lambda exists)
# Placeholder for now
```

## Verification Commands

### Local Validation

```bash
# 1. Naming validation
cd /Users/yitzchak/Documents/dev/careervp
python src/backend/scripts/validate_naming.py --path infra --strict

# 2. CDK synth
cd infra
cdk synth

# 3. Check for CDK tokens
grep -r "Token\[" cdk.out/

# 4. Verify resource names in template
cat cdk.out/CareervpServiceStack-dev.template.json | jq '.Resources | to_entries[] | select(.value.Properties.QueueName or .value.Properties.TableName or .value.Properties.BucketName) | {key: .key, name: (.value.Properties.QueueName // .value.Properties.TableName // .value.Properties.BucketName)}'
```

### Post-Deployment Verification

```bash
# 5. Verify SQS queue
aws sqs get-queue-url --queue-name careervp-vpr-jobs-queue-dev
aws sqs get-queue-attributes --queue-url $(aws sqs get-queue-url --queue-name careervp-vpr-jobs-queue-dev --query 'QueueUrl' --output text) --attribute-names All

# 6. Verify DLQ
aws sqs get-queue-url --queue-name careervp-vpr-jobs-dlq-dev

# 7. Verify DynamoDB table
aws dynamodb describe-table --table-name careervp-jobs-table-dev
aws dynamodb describe-table --table-name careervp-jobs-table-dev | jq '.Table.GlobalSecondaryIndexes[] | select(.IndexName == "idempotency-key-index")'

# 8. Verify S3 bucket
aws s3 ls | grep careervp.*vpr-results
aws s3api get-bucket-lifecycle-configuration --bucket $(aws s3 ls | grep careervp.*vpr-results | awk '{print $3}')

# 9. Verify CloudWatch alarms
aws cloudwatch describe-alarms --alarm-names careervp-vpr-dlq-alarm-dev

# 10. Run state verifier script
cd /Users/yitzchak/Documents/dev/careervp
python src/backend/scripts/verify_aws_state.py --mode deployed
```

## Acceptance Criteria

- [ ] All resource names follow `careervp-{feature}-{type}-{env}` pattern
- [ ] No CDK tokens in resource names (checked via naming validator)
- [ ] SQS queue deployed with correct visibility timeout (660s)
- [ ] DLQ configured with max 3 retries
- [ ] DynamoDB jobs table deployed with GSI
- [ ] S3 bucket deployed with 7-day lifecycle rule
- [ ] CloudWatch DLQ alarm deployed
- [ ] `cdk synth` completes without errors
- [ ] `cdk deploy` completes successfully
- [ ] All resources verified in AWS Console
- [ ] State verifier script passes

## Dependencies

**Blocks:**
- Task 7.2 (Submit Handler) - needs jobs table + SQS queue
- Task 7.3 (Worker Handler) - needs SQS queue + jobs table + S3 bucket
- Task 7.4 (Status Handler) - needs jobs table + S3 bucket

**Blocked By:**
- Phase 0 infrastructure reset (kebab-case naming)

## Estimated Effort

**Time:** 4-6 hours
**Complexity:** LOW-MEDIUM (standard CDK resource creation)

## Notes

- This task creates NEW resources and does NOT modify existing VPR endpoint
- Zero risk to production (new resources only)
- Can be deployed independently and tested in isolation
- Existing synchronous VPR endpoint remains functional during deployment
