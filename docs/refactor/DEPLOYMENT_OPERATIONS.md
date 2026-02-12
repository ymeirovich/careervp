# CareerVP Deployment, Hotfix & Experimentation Guide

**Document Version:** 1.0
**Date:** 2026-02-10
**Purpose:** Document rollback procedures, hotfixes, feature adoption, and A/B testing

---

## Table of Contents

1. [Rollback Procedures](#1-rollback-procedures)
2. [Hotfix Handling](#2-hotfix-handling)
3. [Feature Adoption Metrics](#3-feature-adoption-metrics)
4. [A/B Testing Strategy](#4-ab-testing-strategy)

---

## 1. Rollback Procedures

### 1.1 Automatic Rollback Triggers

```python
# infrastructure/cfn/rollback_config.yaml

RollbackConfiguration:
  # CloudWatch Alarms that trigger rollback
  Alarms:
    - Name: CareerVP-HighErrorRate
      Threshold: > 5% errors for 2 consecutive minutes
    - Name: CareerVP-HighLatency
      Threshold: P95 latency > 5000ms
    - Name: CareerVP-LambdaErrors
      Threshold: > 10 errors in 1 minute
    - Name: CareerVP-5XXErrors
      Threshold: > 20 requests in 1 minute
```

### 1.2 Rollback Decision Matrix

| Scenario | Trigger | Action | Recovery |
|----------|---------|--------|----------|
| **Lambda deployment failure** | `AWS::Lambda::Function` resource failed | Auto-rollback | Previous version active |
| **High error rate** | >5% errors for 2min | Auto-rollback | Previous version active |
| **High latency** | P95 > 5s for 3min | Auto-rollback | Previous version active |
| **API schema mismatch** | Frontend build failure | Manual review | Deploy compatible backend |
| **Database incompatibility** | Query failures detected | Manual rollback | Restore backup, revert code |
| **Security vulnerability** | CVE reported | Immediate rollback | Hotfix required |

### 1.3 Manual Rollback Commands

```bash
#!/bin/bash
# scripts/rollback.sh

ENV=${1:-dev}
REGION=${2:-us-east-1}
VERSION=${3:-previous}

echo "Rolling back $ENV to $VERSION..."

# Option 1: Lambda-specific rollback
aws lambda publish-version \
    --function-name careervp-$ENV-vpr-generator \
    --description "Rolled back to $VERSION" \
    --region $REGION

# Option 2: CloudFormation rollback
aws cloudformation rollback-stack \
    --stack-name careervp-$ENV \
    --region $REGION

# Option 3: Sam rollback
sam deploy \
    --config-file samconfig.toml \
    --rollback \
    --profile careervp

# Verify rollback
aws cloudformation describe-stacks \
    --stack-name careervp-$ENV \
    --region $REGION \
    --query 'Stacks[0].StackStatus'
```

### 1.4 Lambda Version Management

```python
# infrastructure/lambda_versioning.py

class LambdaVersionManager:
    """
    Manages Lambda versions for safe rollbacks.

    Strategy:
    - Each deployment creates a new VERSION (immutable)
    - ALIAS points to current version
    - Previous versions retained for 72 hours
    """

    RETENTION_HOURS = 72
    MAX_VERSIONS = 10

    def deploy_new_version(self, function_name: str, code_uri: str) -> str:
        """Deploy new version and update alias."""
        # 1. Update function code
        update_response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=code_uri,
        )
        version = update_response['Version']

        # 2. Publish version (makes it immutable)
        publish_response = lambda_client.publish_version(
            FunctionName=function_name,
            Description=f"Deployment {version}",
        )

        # 3. Update alias to point to new version
        lambda_client.update_alias(
            FunctionName=function_name,
            AliasName='live',
            FunctionVersion=version,
        )

        # 4. Store version metadata
        self._store_version_metadata(function_name, version)

        return version

    def rollback(self, function_name: str, target_version: str = None) -> str:
        """Rollback to previous version."""
        if not target_version:
            # Get previous version
            versions = self._get_versions(function_name)
            if len(versions) < 2:
                raise RollbackError("No previous version available")
            target_version = versions[-2]  # Second to last

        # Update alias to point to previous version
        lambda_client.update_alias(
            FunctionName=function_name,
            AliasName='live',
            FunctionVersion=target_version,
        )

        # Log rollback event
        self._log_rollback_event(function_name, target_version)

        return target_version

    def get_previous_version(self, function_name: str) -> str:
        """Get the version before current live."""
        versions = self._get_versions(function_name)
        current = self._get_current_version(function_name)
        current_index = versions.index(current)

        if current_index == 0:
            raise RollbackError("No previous version")

        return versions[current_index - 1]
```

### 1.5 Database Rollback Considerations

```python
# scripts/database_rollback.py

class DatabaseRollbackManager:
    """
    Handles database state for rollbacks.

    IMPORTANT: DynamoDB doesn't support traditional rollbacks.
    Use:
    1. Point-in-time recovery (PITR)
    2. Item-level backup/restore
    3. Forward-only migration with compatibility
    """

    def pre_deployment_backup(self, table_name: str):
        """Create backup before deployment."""
        # Enable PITR if not already
        if not self._is_pitr_enabled(table_name):
            self._enable_pitr(table_name)

        # Create on-demand backup
        backup_arn = dynamodb.create_backup(
            TableName=table_name,
            BackupName=f"pre-deploy-{timestamp}"
        )

        # Export critical items to S3
        self._export_critical_items(table_name)

        return backup_arn

    def restore_from_backup(self, table_name: str, backup_arn: str):
        """Restore table from backup."""
        # Create new table from backup
        restore_info = dynamodb.restore_table_from_backup(
            TargetTableName=f"{table_name}-restore",
            BackupArn=backup_arn
        )

        # Verify restore
        if not self._verify_restore(table_name, f"{table_name}-restore"):
            raise RestoreError("Restore verification failed")

        return restore_info

    def forward_only_rollback(self, table_name: str, migration: Migration):
        """
        For DynamoDB, often better to do forward-only migration.

        If new code breaks with old data:
        1. Deploy code that handles BOTH old and new data formats
        2. Migrate data in background
        3. Deploy code that requires new data format
        """
        pass
```

### 1.6 Rollback Checklist

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ROLLBACK CHECKLIST                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PRE-ROLLBACK                                                            │
│  ────────────                                                            │
│  [ ] Identify failure reason                                            │
│  [ ] Determine scope (full rollback vs feature rollback)                 │
│  [ ] Notify stakeholders (Slack #eng-alerts)                            │
│  [ ] Document failure in incident report                                │
│                                                                         │
│  DURING ROLLBACK                                                         │
│  ────────────────                                                        │
│  [ ] Execute rollback command                                            │
│  [ ] Verify Lambda versions updated                                      │
│  [ ] Check CloudWatch logs for errors                                   │
│  [ ] Verify API health endpoint returns 200                             │
│  [ ] Check error rate dropped below threshold                            │
│                                                                         │
│  POST-ROLLBACK                                                           │
│  ─────────────                                                           │
│  [ ] Confirm all alarms are clear                                        │
│  [ ] Notify stakeholders rollback complete                               │
│  [ ] Create post-mortem ticket                                          │
│  [ ] Schedule incident review                                           │
│  [ ] Update runbook if needed                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Hotfix Handling

### 2.1 Hotfix Decision Tree

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HOTFIX DECISION TREE                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                    CRITICAL BUG DETECTED?                                │
│                           │                                             │
│              ┌────────────┼────────────┐                               │
│              │            │            │                               │
│             YES          NO           │                                │
│              │            │            │                               │
│              ▼            ▼            │                                │
│      SEVERITY LEVEL?  PATCH Tuesday? │                                │
│        │                  │         │                                │
│   ┌────┴────┐       ┌────┴────┐     │                                │
│   │P1: CRITICAL│    │P2: HIGH │     │                                │
│   │   Immediate│    │ Next    │     │                                │
│   │  hotfix   │    │ release  │     │                                │
│   └────┬─────┘    └────┬─────┘     │                                │
│        │               │            │                                │
│        ▼               ▼            ▼                                │
│   ┌─────────────────────────────────────────────┐                      │
│   │ HOTFIX WORKFLOW                              │                      │
│   └─────────────────────────────────────────────┘                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Hotfix Severity Levels

| Level | Definition | SLA | Example |
|-------|------------|-----|---------|
| **P1-Critical** | Production down, data loss, security breach | 1 hour | Lambda failing all requests |
| **P2-High** | Major feature broken, no workaround | 4 hours | VPR generator returns 500 |
| **P3-Medium** | Minor feature broken, workaround exists | 24 hours | Cover letter missing signature |
| **P4-Low** | Cosmetic issue,不影响核心功能 | Next release | Typo in error message |

### 2.3 Hotfix Workflow

```bash
#!/bin/bash
# scripts/hotfix.sh

set -e

BRANCH_NAME="hotfix/$(date +%Y%m%d)-$1"
echo "Creating hotfix branch: $BRANCH_NAME"

# 1. Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b $BRANCH_NAME

# 2. Make minimal fix
# (Edit only what is absolutely necessary)
$EDITOR src/backend/careervp/handlers/vpr_handler.py

# 3. Run ONLY the tests related to the fix
uv run pytest tests/unit/test_vpr_handler.py -v --tb=short

# 4. Commit with conventional format
git add -A
git commit -m "hotfix($1): $(git diff --stat | head -1)

Severity: $2
Reason: $(cat /tmp/hotfix_reason.txt)

BREAKING CHANGE: NO"

# 5. Create PR for documentation (no review required)
gh pr create \
    --title "HOTFIX: $1" \
    --body "$(cat <<EOF
## Hotfix Details
- **Severity**: $2
- **Branch**: $BRANCH_NAME
- **Fixes**: $(git diff --stat | head -1)

## Testing
- [ ] Unit tests pass
- [ ] Integration tested
- [ ] Rollback verified

## Rollback
\`\`\`bash
./scripts/rollback.sh $3 $4
\`\`\`
EOF
)" \
    --base main \
    --head $BRANCH_NAME \
    --label "hotfix,skip-ci"

# 6. Deploy immediately (bypass CI for hotfixes)
echo "Deploying hotfix to production..."
./scripts/deploy.sh --environment prod --hotfix

# 7. Merge back to main after deployment
git checkout main
git merge $BRANCH_NAME --no-ff
git push origin main
git branch -d $BRANCH_NAME

echo "Hotfix complete and merged to main"
```

### 2.4 Hotfix PR Template

```markdown
## Hotfix PR: [SHORT TITLE]

### Severity
- [ ] P1-Critical (1 hour SLA)
- [ ] P2-High (4 hours SLA)
- [ ] P3-Medium (24 hours SLA)

### Issue Description
<!-- What is broken and how it affects users -->

### Root Cause
<!-- What caused the issue -->

### Fix Applied
<!-- What code was changed -->

### Testing Performed
- [ ] Unit tests pass
- [ ] Manual testing
- [ ] Verified fix in [env]

### Deployment
- [ ] Deployed to [env] at [time]
- [ ] No errors in logs
- [ ] Monitoring confirms fix

### Rollback Plan
```bash
# Command to rollback if needed
./scripts/rollback.sh [env] [version]
```

### Post-Fix Actions
- [ ] Update runbook
- [ ] Add monitoring
- [ ] Schedule post-mortem (if P1/P2)
```

### 2.5 Emergency Hotfix (Skip All Checks)

```python
# scripts/emergency_deploy.py

class EmergencyDeployer:
    """
    For P1-Critical issues only.

    WARNING: This bypasses ALL safety checks.
    Use only when:
    - Production is down
    - Data is being corrupted
    - Security vulnerability is being exploited
    """

    REQUIRED_APPROVALS = 2
    APPROVERS = ["tech-lead@company.com", "cto@company.com"]

    async def emergency_deploy(self, fix_code: str, approvers: list[str]):
        """Deploy emergency fix with minimal approval."""
        # 1. Get emergency approvals
        if len(approvers) < self.REQUIRED_APPROVALS:
            raise PermissionError("Emergency deploy requires 2 approvals")

        for approver in approvers:
            if approver not in self.APPROVERS:
                raise PermissionError(f"{approver} not authorized")

        # 2. Create emergency branch
        branch = f"emergency/{timestamp}"
        await self._create_branch(branch)

        # 3. Apply minimal fix
        await self._apply_fix(branch, fix_code)

        # 4. Deploy directly to production
        deploy_result = await self._deploy_to_prod(branch)

        # 5. Log EVERYTHING for audit
        self._audit_log({
            "action": "emergency_deploy",
            "fix_code": fix_code[:100],  # First 100 chars
            "approvers": approvers,
            "deploy_result": deploy_result,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return deploy_result
```

---

## 3. Feature Adoption Metrics

### 3.1 Key Metrics Framework

```python
# src/backend/careervp/analytics/feature_metrics.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FeatureMetrics:
    """Track feature adoption and usage."""

    # Raw counts
    total_users: int = 0
    active_users: int = 0
    feature_views: int = 0
    feature_uses: int = 0
    feature_completions: int = 0

    # Adoption rates
    adoption_rate: float = 0.0  # users_who_used / total_users
    activation_rate: float = 0.0  # users_completed / users_started

    # Engagement
    avg_session_duration: float = 0.0
    repeat_usage_rate: float = 0.0

    # Business metrics
    conversion_impact: float = 0.0
    revenue_impact: float = 0.0


class FeatureAdoptionTracker:
    """
    Track feature adoption across user lifecycle.

    Metrics collected:
    - Discovery: User sees feature
    - Activation: User attempts feature
    - Retention: User returns to feature
    - Referral: User tells others about feature
    """

    EVENTS_TABLE = "careervp-analytics-events"

    def track_event(
        self,
        user_id: str,
        event_type: str,
        feature_name: str,
        metadata: dict = None,
    ):
        """Track a feature event."""
        item = {
            "pk": f"USER#{user_id}",
            "sk": f"EVENT#{event_type}#{feature_name}#{datetime.utcnow().isoformat()}",
            "event_type": event_type,
            "feature_name": feature_name,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata,
        }

        dynamodb.put_item(TableName=self.EVENTS_TABLE, Item=item)

    def calculate_adoption_metrics(self, feature_name: str, days: int = 30) -> FeatureMetrics:
        """Calculate adoption metrics for a feature."""
        # Query events for timeframe
        events = self._query_feature_events(feature_name, days)

        # Calculate metrics
        total_users = self._count_unique_users(events)
        active_users = self._count_users_with_event(events, "use")
        completions = self._count_users_with_event(events, "complete")

        # Calculate rates
        adoption_rate = active_users / total_users if total_users > 0 else 0
        activation_rate = completions / active_users if active_users > 0 else 0

        return FeatureMetrics(
            total_users=total_users,
            active_users=active_users,
            feature_uses=len([e for e in events if e.type == "use"]),
            feature_completions=completions,
            adoption_rate=adoption_rate,
            activation_rate=activation_rate,
        )
```

### 3.2 Feature Funnel Analytics

```python
# src/backend/careervp/analytics/funnel.py

class FeatureFunnelAnalyzer:
    """
    Analyze feature conversion funnels.

    Example funnel for Cover Letter:
    1. View feature → 10,000 users
    2. Click generate → 5,000 users (50%)
    3. Complete form → 4,500 users (90%)
    4. Generate → 4,000 users (89%)
    5. Download → 3,500 users (88%)

    Overall conversion: 35%
    """

    FUNNEL_STEPS = {
        "cover_letter": [
            {"step": "view", "name": "View feature page"},
            {"step": "click_generate", "name": "Click generate button"},
            {"step": "complete_form", "name": "Complete CV selection"},
            {"step": "submit", "name": "Submit request"},
            {"step": "download", "name": "Download result"},
        ],
        "vpr_generator": [
            {"step": "view", "name": "View VPR page"},
            {"step": "upload_cv", "name": "Upload CV"},
            {"step": "enter_job", "name": "Enter job description"},
            {"step": "generate", "name": "Generate VPR"},
            {"step": "save", "name": "Save to profile"},
        ],
    }

    def calculate_funnel_metrics(
        self,
        feature_name: str,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """Calculate funnel conversion metrics."""
        steps = self.FUNNEL_STEPS.get(feature_name, [])
        funnel_data = []

        for i, step in enumerate(steps):
            count = self._count_step_events(
                feature_name,
                step["step"],
                start_date,
                end_date,
            )

            # Calculate drop-off from previous step
            if i == 0:
                dropoff = 0
            else:
                prev_count = funnel_data[-1]["count"]
                dropoff = (prev_count - count) / prev_count * 100 if prev_count > 0 else 0

            funnel_data.append({
                "step": step["step"],
                "name": step["name"],
                "count": count,
                "dropoff_rate": round(dropoff, 2),
                "conversion_from_start": round(count / funnel_data[0]["count"] * 100, 2) if funnel_data else 100,
            })

        return {
            "feature": feature_name,
            "period": {"start": start_date, "end": end_date},
            "funnel": funnel_data,
            "overall_conversion": funnel_data[-1]["count"] / funnel_data[0]["count"] if funnel_data else 0,
        }
```

### 3.3 Feature Usage Dashboard Query

```sql
-- Athena/Glue query for feature adoption

SELECT
    feature_name,
    DATE_FORMAT(event_time, '%Y-%m-%d') as date,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(*) as total_events,
    COUNT(CASE WHEN event_type = 'complete' THEN 1 END) as completions,
    AVG(CASE WHEN event_type = 'use' THEN session_duration END) as avg_duration
FROM careervp_analytics.events
WHERE event_time >= DATE_SUB('day', 30, CURRENT_DATE)
GROUP BY feature_name, DATE_FORMAT(event_time, '%Y-%m-%d')
ORDER BY date DESC, unique_users DESC
```

### 3.4 Adoption Alerts

```python
# infrastructure/alerts/feature_adoption_alerts.py

FEATURE_ADOPTION_ALERTS = {
    # Alert if adoption drops below threshold
    "low_adoption": {
        "metric": "adoption_rate",
        "threshold": 0.10,  # 10%
        "period": "7d",
        "severity": "warning",
        "message": "Feature {feature} adoption at {value:.1%}, below 10% threshold",
    },

    # Alert if drop-off at specific step is high
    "high_dropoff": {
        "metric": "step_dropoff",
        "step": "complete_form",  # Specific step
        "threshold": 0.30,  # 30% dropoff
        "period": "24h",
        "severity": "warning",
        "message": "Feature {feature} step '{step}' has {value:.1%} dropoff",
    },

    # Alert if feature not used by power users
    "power_user_adoption": {
        "metric": "power_user_rate",
        "threshold": 0.50,  # 50% of power users
        "period": "7d",
        "severity": "info",
        "message": "Feature {feature} adopted by {value:.1%} of power users",
    },
}
```

---

## 4. A/B Testing Strategy

### 4.1 A/B Testing Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    A/B TESTING ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐                                                       │
│  │   User      │                                                       │
│  └──────┬──────┘                                                       │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────┐                                                       │
│  │  Assignment │  ──Hash(user_id + experiment) % 100                    │
│  │  Service    │                                                       │
│  └──────┬──────┘                                                       │
│         │                                                               │
│         ├──────────┬────────────────────┐                              │
│         │          │                    │                              │
│         ▼          ▼                    ▼                              │
│  ┌─────────┐  ┌─────────┐        ┌─────────┐                         │
│  │ Control │  │Variant A│        │ Variant B│                         │
│  │    A   │  │   (B)   │        │   (C)   │                         │
│  └────┬────┘  └────┬────┘        └────┬────┘                         │
│       │            │                   │                                │
│       └────────────┼───────────────────┘                                │
│                    │                                                   │
│                    ▼                                                   │
│         ┌─────────────────────┐                                         │
│         │   Metrics Service  │                                         │
│         │                     │                                         │
│         │ - Conversion rate  │                                         │
│         │ - Engagement time   │                                         │
│         │ - Revenue impact    │                                         │
│         │ - Error rate        │                                         │
│         └─────────────────────┘                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Experiment Configuration

```python
# experiments/cover_letter_prompt_v1.py

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExperimentConfig:
    """A/B test configuration."""

    name: str
    description: str
    variants: dict[str, str]  # variant_id -> description

    # Traffic allocation
    traffic_percentage: float = 0.10  # 10% of users
    minimum_sample_size: int = 1000  # Per variant

    # Duration
    start_date: datetime
    end_date: datetime

    # Success metrics
    primary_metric: str = "completion_rate"
    secondary_metrics: list[str] = None

    # Guardrails (stop if any violated)
    guardrails: dict[str, float] = None


COVER_LETTER_PROMPT_EXPERIMENT = ExperimentConfig(
    name="cover_letter_prompt_v2",
    description="Test new prompt structure for cover letters",
    variants={
        "control": "Current 3-paragraph prompt",
        "variant_a": "4-paragraph with company research integration",
        "variant_b": "Shorter 2-paragraph with link to portfolio",
    },
    traffic_percentage=0.10,
    minimum_sample_size=500,
    start_date=datetime(2026, 2, 15),
    end_date=datetime(2026, 3, 15),
    primary_metric="download_rate",
    secondary_metrics=["generation_time", "user_rating", "edit_count"],
    guardrails={
        "error_rate": 0.05,  # Stop if errors > 5%
        "latency_p95": 10.0,  # Stop if P95 > 10s
    },
)


@dataclass
class ExperimentAssignment:
    """User assignment to experiment variant."""

    experiment_name: str
    user_id: str
    variant_id: str
    assigned_at: datetime
    cohort: str = None  # For analysis (e.g., "new_user", "premium")


class ExperimentService:
    """
    Manage A/B test assignments and analysis.
    """

    def assign_variant(
        self,
        experiment_name: str,
        user_id: str,
        cohort: str = None,
    ) -> ExperimentAssignment:
        """Assign user to experiment variant."""
        # Check if already assigned
        existing = self._get_assignment(experiment_name, user_id)
        if existing:
            return existing

        # Hash user + experiment for consistent assignment
        hash_value = self._hash(f"{user_id}:{experiment_name}")
        variant = self._select_variant(experiment_name, hash_value)

        assignment = ExperimentAssignment(
            experiment_name=experiment_name,
            user_id=user_id,
            variant_id=variant,
            assigned_at=datetime.utcnow(),
            cohort=cohort,
        )

        # Store assignment
        self._store_assignment(assignment)

        return assignment

    def _select_variant(
        self,
        experiment_name: str,
        hash_value: int,
    ) -> str:
        """Select variant based on hash."""
        config = self._get_config(experiment_name)
        variants = list(config.variants.keys())

        # Get weight for each variant
        weights = [1.0 / len(variants)] * len(variants)

        # Apply traffic percentage
        if hash_value % 100 >= config.traffic_percentage * 100:
            return "control"  # User not in experiment

        # Select variant
        cumulative = 0
        for variant, weight in zip(variants, weights):
            cumulative += weight
            if hash_value / 100 < cumulative:
                return variant

        return "control"

    def calculate_results(self, experiment_name: str) -> dict:
        """Calculate experiment results."""
        config = self._get_config(experiment_name)

        results = {}
        for variant in config.variants.keys():
            results[variant] = self._calculate_variant_metrics(
                experiment_name,
                variant,
            )

        # Statistical significance
        results["significance"] = self._calculate_significance(
            results["control"],
            results[config.variants.keys().__next__()],
        )

        return results
```

### 4.3 Experiment Tracking

```python
# src/backend/careervp/analytics/experiment_tracker.py

class ExperimentTracker:
    """Track experiment events and metrics."""

    def track_assignment(self, assignment: ExperimentAssignment):
        """Track when user is assigned to experiment."""
        self._put_event(
            event_type="experiment_assignment",
            user_id=assignment.user_id,
            experiment=assignment.experiment_name,
            variant=assignment.variant_id,
        )

    def track_action(
        self,
        experiment_name: str,
        user_id: str,
        action: str,
        value: float = None,
        metadata: dict = None,
    ):
        """Track user action within experiment."""
        self._put_event(
            event_type="experiment_action",
            user_id=user_id,
            experiment=experiment_name,
            action=action,
            value=value,
            metadata=metadata,
        )

    def get_experiment_metrics(
        self,
        experiment_name: str,
        variant_id: str,
    ) -> dict:
        """Get metrics for experiment variant."""
        # Query all events for this variant
        events = self._query_events(
            experiment=experiment_name,
            variant=variant_id,
        )

        return {
            "users": self._count_unique_users(events),
            "actions": self._count_by_action(events),
            "conversions": self._count_conversions(events),
            "revenue": self._sum_revenue(events),
        }
```

### 4.4 Statistical Analysis

```python
# experiments/statistical_analysis.py

import math
from scipy import stats


class ExperimentAnalyzer:
    """Statistical analysis for A/B tests."""

    def calculate_significance(
        self,
        control_metrics: dict,
        variant_metrics: dict,
        primary_metric: str,
    ) -> dict:
        """
        Calculate statistical significance using z-test for proportions.

        Returns:
        - p_value: Probability results are due to chance
        - confidence: 1 - p_value
        - uplift: Percentage improvement
        - is_significant: Whether p_value < 0.05
        """
        control_rate = control_metrics[primary_metric]
        variant_rate = variant_metrics[primary_metric]
        control_n = control_metrics["sample_size"]
        variant_n = variant_metrics["sample_size"]

        # Pooled proportion
        pooled = (control_rate * control_n + variant_rate * variant_n) / (control_n + variant_n)

        # Standard error
        se = math.sqrt(pooled * (1 - pooled) * (1/control_n + 1/variant_n))

        # Z-score
        if se == 0:
            z_score = 0
        else:
            z_score = (variant_rate - control_rate) / se

        # P-value (two-tailed)
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

        # Confidence level
        confidence = (1 - p_value) * 100

        # Uplift
        if control_rate > 0:
            uplift = (variant_rate - control_rate) / control_rate * 100
        else:
            uplift = float('inf')

        return {
            "p_value": round(p_value, 4),
            "confidence": round(confidence, 2),
            "uplift": round(uplift, 2),
            "is_significant": p_value < 0.05,
            "z_score": round(z_score, 4),
            "recommendation": self._get_recommendation(p_value, uplift),
        }

    def _get_recommendation(self, p_value: float, uplift: float) -> str:
        """Get recommendation based on results."""
        if p_value >= 0.10:
            return "NO_ACTION: Results not statistically significant"
        elif uplift > 5:
            return "PROMOTE: Variant significantly better, deploy to all users"
        elif uplift < -5:
            return "ROLLBACK: Variant significantly worse, keep control"
        else:
            return "CONTINUE: Need more data, difference too small"

    def calculate_sample_size(
        self,
        baseline_rate: float,
        minimum_detectable_effect: float,
        power: float = 0.80,
        alpha: float = 0.05,
    ) -> int:
        """
        Calculate minimum sample size per variant.

        Args:
            baseline_rate: Current conversion rate
            minimum_detectable_effect: Relative effect to detect (e.g., 0.10 for 10%)
            power: Statistical power (usually 0.80)
            alpha: Significance level (usually 0.05)
        """
        # Z-scores for alpha and power
        z_alpha = stats.norm.ppf(1 - alpha/2)
        z_power = stats.norm.ppf(power)

        # Effect size
        effect = baseline_rate * minimum_detectable_effect

        # Sample size formula
        n = (2 * (z_alpha + z_power)**2 * baseline_rate * (1 - baseline_rate)) / (effect**2)

        return int(math.ceil(n))
```

### 4.5 A/B Test Runbook

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    A/B TEST RUNBOOK                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  BEFORE LAUNCH                                                          │
│  ─────────────                                                          │
│  [ ] Define hypothesis                                                 │
│  [ ] Define success metrics                                             │
│  [ ] Define guardrail metrics                                           │
│  [ ] Calculate minimum sample size                                      │
│  [ ] Get sign-off from product and engineering                         │
│  [ ] Configure feature flag                                            │
│  [ ] Set up monitoring dashboards                                       │
│                                                                         │
│  DURING TEST                                                            │
│  ────────────                                                           │
│  [ ] Monitor guardrail metrics daily                                   │
│  [ ] Check for significant results weekly                              │
│  [ ] Document any issues                                                │
│  [ ] Don't make changes mid-test                                       │
│                                                                         │
│  END OF TEST                                                            │
│  ───────────                                                            │
│  [ ] Run statistical analysis                                           │
│  [ ] Document results                                                   │
│  [ ] Get sign-off on decision                                          │
│  [ ] Update feature flag for all users (if promoted)                    │
│  [ ] Clean up experiment code                                          │
│  [ ] Archive experiment data                                            │
│                                                                         │
│  DECISION FRAMEWORK                                                     │
│  ───────────────────                                                   │
│  • p-value < 0.05 AND positive uplift → Promote to all                  │
│  • p-value < 0.05 AND negative uplift → Keep control                    │
│  • p-value > 0.10 → Need more data or inconclusive                     │
│  • Guardrails violated → Stop immediately                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

**Document Version:** 1.0
**Last Updated:** 2026-02-10

---

**END OF DEPLOYMENT & EXPERIMENTATION GUIDE**
