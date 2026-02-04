# Task 7.8: Gradual Deployment & Monitoring

**Status:** Not Started
**Spec Reference:** [[docs/specs/07-vpr-async-architecture.md]]
**Priority:** P0 (BLOCKING - Production VPR generation fails 100%)

## Overview

Deploy VPR async architecture to production using gradual rollout strategy with monitoring. Start with 10% traffic, monitor metrics, increase to 50%, then 100%. Includes rollback plan and success criteria verification.

## Prerequisites

- [ ] Tasks 7.1-7.7 complete (all implementation and tests pass)
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Load tests passing (100 concurrent requests)
- [ ] Dev environment fully tested
- [ ] Rollback plan documented

## Todo

### 1. Pre-Deployment Checklist

- [ ] All tests passing in CI/CD pipeline
- [ ] Code reviewed and approved
- [ ] Infrastructure changes reviewed (CDK diff)
- [ ] Database migration plan (if needed)
- [ ] Rollback plan documented and tested
- [ ] Monitoring dashboards created
- [ ] CloudWatch alarms configured
- [ ] On-call rotation scheduled
- [ ] Deployment announcement sent to team

### 2. Deploy to Dev Environment

- [ ] Run `cdk diff` to review changes
- [ ] Deploy infrastructure: `cdk deploy --all`
- [ ] Verify all resources created:
  - SQS queue + DLQ
  - DynamoDB jobs table + GSI
  - S3 results bucket
  - 3 Lambda functions
  - CloudWatch alarms
- [ ] Run smoke tests on dev environment
- [ ] Verify end-to-end flow works
- [ ] Monitor CloudWatch Logs for errors

### 3. Create CloudWatch Dashboard

**Dashboard Name:** `VPR-Async-Monitoring-{env}`

- [ ] Add widget: SQS queue depth (metric: ApproximateNumberOfMessagesVisible)
- [ ] Add widget: DLQ messages (metric: ApproximateNumberOfMessagesVisible)
- [ ] Add widget: Lambda invocations (all 3 Lambdas)
- [ ] Add widget: Lambda errors (all 3 Lambdas)
- [ ] Add widget: Lambda duration (worker Lambda p50, p95, p99)
- [ ] Add widget: DynamoDB read/write capacity units
- [ ] Add widget: API Gateway 4xx/5xx errors
- [ ] Add widget: API Gateway latency (p50, p95, p99)
- [ ] Save dashboard

### 4. Configure CloudWatch Alarms (Additional)

Beyond Task 7.1 alarms, add:

- [ ] **High Queue Depth Alarm**
  - Metric: SQS ApproximateNumberOfMessagesVisible
  - Threshold: >50 messages
  - Action: SNS notification
- [ ] **API Gateway 5xx Alarm**
  - Metric: API Gateway 5XXError
  - Threshold: >5% over 5 minutes
  - Action: SNS notification + PagerDuty
- [ ] **Lambda Throttling Alarm**
  - Metric: Lambda Throttles (worker Lambda)
  - Threshold: >0 over 5 minutes
  - Action: SNS notification
- [ ] **DynamoDB Throttling Alarm**
  - Metric: SystemErrors (jobs table)
  - Threshold: >0 over 5 minutes
  - Action: SNS notification

### 5. Deploy to Staging/QA Environment

- [ ] Deploy same infrastructure to staging
- [ ] Run full test suite on staging
- [ ] Perform manual QA testing
- [ ] Load test with 100+ concurrent users
- [ ] Verify metrics in CloudWatch dashboard
- [ ] Soak test: Run for 24 hours, monitor stability
- [ ] Get sign-off from QA team

### 6. Production Deployment - Phase 1 (10% Traffic)

**Strategy:** Use API Gateway routing to split traffic

- [ ] Deploy async infrastructure to production (new resources only)
- [ ] **Do NOT modify existing `/api/vpr` endpoint yet**
- [ ] Create new endpoint `/api/vpr-async` (temporary)
- [ ] Configure API Gateway weighted routing:
  - 90% → `/api/vpr` (existing sync endpoint)
  - 10% → `/api/vpr-async` (new async endpoint)
- [ ] Deploy and monitor for 24 hours
- [ ] Verify metrics:
  - Success rate: >99%
  - P95 submit latency: <3s
  - P95 VPR generation time: <90s
  - Queue depth: <10
  - DLQ messages: 0
  - Error rate: <1%

### 7. Production Deployment - Phase 2 (50% Traffic)

- [ ] Review Phase 1 metrics (24-hour soak)
- [ ] Get approval from engineering lead
- [ ] Update API Gateway routing:
  - 50% → `/api/vpr` (sync)
  - 50% → `/api/vpr-async` (async)
- [ ] Deploy and monitor for 24 hours
- [ ] Verify same metrics as Phase 1
- [ ] Compare cost per VPR: async vs sync

### 8. Production Deployment - Phase 3 (100% Traffic)

- [ ] Review Phase 2 metrics (24-hour soak)
- [ ] Get approval from product team
- [ ] **Migrate `/api/vpr` to async handler**:
  - Update Lambda function to point to `vpr_submit_handler`
  - Remove old sync handler from routing
- [ ] Remove temporary `/api/vpr-async` endpoint
- [ ] Deploy and monitor for 48 hours
- [ ] Verify 100% of traffic using async pattern

### 9. Deprecate Synchronous Code

- [ ] Archive old `vpr_handler.py` (sync version)
- [ ] Remove unused environment variables
- [ ] Update API documentation
- [ ] Announce completion to team
- [ ] Celebrate! 🎉

### 10. Post-Deployment Monitoring (Week 1)

Monitor daily for first week:

- [ ] **Day 1:** Check all metrics every 4 hours
- [ ] **Day 2-3:** Check metrics twice per day
- [ ] **Day 4-7:** Check metrics once per day
- [ ] **Week 2+:** Normal monitoring cadence

**Key Metrics to Monitor:**

| Metric | Target | Alert If |
|--------|--------|----------|
| Success Rate | >99% | <98% |
| P95 Submit Latency | <3s | >5s |
| P95 VPR Generation Time | <90s | >120s |
| Queue Depth | <10 | >50 |
| DLQ Messages | 0 | ≥1 |
| Lambda Errors | <1% | >5% |
| Cost per VPR | <$0.01 | >$0.05 |

## Codex Implementation Guide

### API Gateway Weighted Routing (Temporary)

```python
# infra/careervp/api_construct.py

# TEMPORARY: Split traffic between sync and async during rollout

# Create async endpoint (temporary)
self.api.add_routes(
    path="/api/vpr-async",
    methods=[aws_apigatewayv2.HttpMethod.POST],
    integration=aws_apigatewayv2_integrations.HttpLambdaIntegration(
        "VprAsyncIntegration",
        self.vpr_submit_lambda  # New async handler
    )
)

# Keep existing sync endpoint
self.api.add_routes(
    path="/api/vpr",
    methods=[aws_apigatewayv2.HttpMethod.POST],
    integration=aws_apigatewayv2_integrations.HttpLambdaIntegration(
        "VprSyncIntegration",
        self.vpr_generator_lambda  # Old sync handler (keep for rollback)
    )
)

# Frontend: Randomly route 10% to async
# if (Math.random() < 0.1) {
#   endpoint = '/api/vpr-async';
# } else {
#   endpoint = '/api/vpr';
# }
```

### CloudWatch Dashboard Definition

```python
# infra/careervp/monitoring_construct.py

import aws_cdk.aws_cloudwatch as cloudwatch

class MonitoringConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, env: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Create CloudWatch Dashboard
        dashboard = cloudwatch.Dashboard(
            self, "VprAsyncDashboard",
            dashboard_name=f"VPR-Async-Monitoring-{env}"
        )

        # SQS Queue Metrics
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="SQS Queue Depth",
                left=[
                    self.vpr_jobs_queue.metric_approximate_number_of_messages_visible(),
                    self.vpr_jobs_dlq.metric_approximate_number_of_messages_visible()
                ],
                period=Duration.minutes(5)
            )
        )

        # Lambda Metrics
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Lambda Invocations",
                left=[
                    self.vpr_submit_lambda.metric_invocations(),
                    self.vpr_worker_lambda.metric_invocations(),
                    self.vpr_status_lambda.metric_invocations()
                ],
                period=Duration.minutes(5)
            ),
            cloudwatch.GraphWidget(
                title="Lambda Errors",
                left=[
                    self.vpr_submit_lambda.metric_errors(),
                    self.vpr_worker_lambda.metric_errors(),
                    self.vpr_status_lambda.metric_errors()
                ],
                period=Duration.minutes(5),
                statistic="Sum"
            )
        )

        # Worker Lambda Duration
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Worker Lambda Duration",
                left=[self.vpr_worker_lambda.metric_duration()],
                period=Duration.minutes(5),
                statistic="Average"
            )
        )

        # DynamoDB Metrics
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="DynamoDB Operations",
                left=[
                    self.jobs_table.metric_consumed_read_capacity_units(),
                    self.jobs_table.metric_consumed_write_capacity_units()
                ],
                period=Duration.minutes(5)
            )
        )
```

## Rollback Plan

### Scenario 1: Async Endpoint Failing

**Symptoms:** High error rate, DLQ messages, failed VPR generations

**Rollback Steps:**
1. Update API Gateway routing to 0% async, 100% sync
2. Deploy routing change (takes ~30 seconds)
3. Verify sync endpoint working
4. Investigate async failures in CloudWatch Logs
5. Fix issues and redeploy

**Rollback Time:** <5 minutes

### Scenario 2: High Queue Depth (Backlog)

**Symptoms:** Queue depth >100, slow VPR generation

**Mitigation Steps:**
1. Increase worker Lambda concurrency (5 → 10)
2. Monitor Claude API rate limits
3. Consider temporary Step Functions parallel execution
4. If persistent, rollback to sync endpoint

**Rollback Time:** <10 minutes

### Scenario 3: DynamoDB Throttling

**Symptoms:** SystemErrors alarm, failed job updates

**Mitigation Steps:**
1. Switch jobs table to Provisioned billing mode
2. Increase WCU/RCU to 100 each
3. Monitor for 30 minutes
4. If resolved, keep Provisioned mode
5. If not resolved, rollback to sync endpoint

**Rollback Time:** <15 minutes

## Verification Commands

### Pre-Deployment Checks

```bash
# 1. Verify all tests pass
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest tests/ -v --tb=short

# 2. Check code coverage
uv run pytest tests/ --cov=careervp --cov-report=term-missing

# 3. Lint and type check
uv run ruff check careervp/ --fix
uv run mypy careervp/ --strict

# 4. Review CDK changes
cd ../infra
cdk diff

# 5. Validate naming
python ../src/backend/scripts/validate_naming.py --path . --strict
```

### Deployment Commands

```bash
# Deploy to dev
cd infra
cdk deploy --all --context env=dev

# Deploy to staging
cdk deploy --all --context env=staging

# Deploy to production (infrastructure only, no endpoint change)
cdk deploy --all --context env=prod

# Verify deployment
python ../src/backend/scripts/verify_aws_state.py --mode deployed --env prod
```

### Monitoring Commands

```bash
# Check CloudWatch Logs (submit Lambda)
aws logs tail /aws/lambda/careervp-vpr-submit-lambda-prod --follow

# Check CloudWatch Logs (worker Lambda)
aws logs tail /aws/lambda/careervp-vpr-worker-lambda-prod --follow

# Check SQS metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=careervp-vpr-jobs-queue-prod \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# Check DLQ messages
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name careervp-vpr-jobs-dlq-prod --query 'QueueUrl' --output text) \
  --attribute-names ApproximateNumberOfMessages

# Check CloudWatch alarms
aws cloudwatch describe-alarms \
  --alarm-names careervp-vpr-dlq-alarm-prod careervp-vpr-worker-errors-alarm-prod
```

## Acceptance Criteria

- [ ] All tests passing before deployment
- [ ] Dev environment deployed and tested
- [ ] Staging environment deployed and tested
- [ ] CloudWatch dashboard created
- [ ] CloudWatch alarms configured and tested
- [ ] Phase 1 (10% traffic) successful for 24 hours
- [ ] Phase 2 (50% traffic) successful for 24 hours
- [ ] Phase 3 (100% traffic) successful for 48 hours
- [ ] Success rate >99%
- [ ] P95 VPR generation time <90s
- [ ] Queue depth <10 (steady state)
- [ ] DLQ messages = 0
- [ ] Cost per VPR <$0.01
- [ ] Old sync code deprecated and archived
- [ ] Documentation updated
- [ ] Team announcement sent

## Dependencies

**Blocks:**
- None (final task in sequence)

**Blocked By:**
- Tasks 7.1-7.7 (all implementation and tests must pass)

## Estimated Effort

**Time:** 2-3 weeks (including soak periods)
- Week 1: Dev + Staging deployment + testing
- Week 2: Production Phase 1 (10%) + Phase 2 (50%)
- Week 3: Production Phase 3 (100%) + monitoring + deprecation

**Complexity:** HIGH (production deployment with gradual rollout)

## Notes

- **Gradual rollout is critical** - Do NOT go straight to 100%
- Monitor metrics continuously during each phase
- Have rollback plan ready and tested
- Schedule deployment during low-traffic hours
- Keep on-call engineer available during rollout
- Document all issues encountered during deployment
- Celebrate when complete! 🎉
