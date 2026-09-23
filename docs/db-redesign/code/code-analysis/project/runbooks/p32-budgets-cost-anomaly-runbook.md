# P-32 — Budgets + Cost Anomaly Detection Runbook (post-deploy verification, HUMAN-APPLIED)

**Amendment (2026-07-12, human decision):** the Wave 0 slice of P-32 moved from
console-only to CDK. `specs/P-32-cost-obs-edge-spec.md` Fix Plan item 4
("Do not store console-only configuration as fake CDK code unless AWS
ownership is moved into IaC by explicit decision") is now satisfied by that
explicit decision. The AWS Budget and Cost Anomaly Detection monitor/
subscription are defined in `infra/careervp/monitoring.py`
(`MonitoringNestedStack._build_cost_observability`) and synth-tested in
`infra/tests/infrastructure/test_p32_budgets_cost_anomaly.py`. See
`project-scope-lock.yaml`/`.md` for the recorded amendment.

What's still human-only: **an agent session can prove the CDK template is
correct (synth passing), but cannot prove a real deploy happened or that the
live account actually has these resources** — the same "code existing isn't
evidence" rule P-27/P-28 already established. That's the only remaining step
here.

## 1. Deploy

Go through the normal P-28 human-gated deploy flow (`create-change-set` →
review the Replacement report → `execute-change-set`). No new console
clicking is required for this step — the Budget, AnomalyMonitor, and
AnomalySubscription resources are created by the change-set like any other
resource in `MonitoringNestedStack`.

## 2. Confirm the resources exist in the account and record evidence

After the deploy completes, pull the real ARNs and populate an evidence
document matching the shape `validate_budget_evidence` /
`validate_cost_anomaly_evidence` (`src/backend/scripts/deploy_evidence.py`)
expect:

```bash
aws budgets describe-budgets --account-id <account-id> --region us-east-1
aws ce get-anomaly-monitors --region us-east-1
aws ce get-anomaly-subscriptions --region us-east-1
```

```json
{
  "aws_budget": {
    "budget_name": "careervp-cost-obs-monthly-budget-dev",
    "threshold_amount": 100,
    "subscriber": "arn:aws:sns:us-east-1:<account-id>:careervp-monitoring-alarms-dev",
    "captured_at": "<ISO-8601 timestamp of when you captured this>"
  },
  "cost_anomaly_detection": {
    "monitor_arn": "arn:aws:ce::<account-id>:anomalymonitor/<id-from-describe>",
    "subscription_arn": "arn:aws:ce::<account-id>:anomalysubscription/<id-from-describe>",
    "captured_at": "<ISO-8601 timestamp of when you captured this>"
  }
}
```

Store this file wherever this repo's other deploy-gate evidence lives (see
`src/backend/scripts/evidence_pack.py` / P-29's evidence pack for the sibling
pattern) and pass it through `validate_budget_evidence` +
`validate_cost_anomaly_evidence` before treating 0.56 as fully done. An agent
session cannot fabricate these ARNs or confirm a real deploy occurred —
pasting real post-deploy values back is the human's part of this step.

## NOT part of this runbook
- Tags, correlation-ID propagation, log retention/alarms, and API request
  validators/models are the **P-32 remainder**, homed in Wave 5
  (`project-scope-lock.yaml:179`), not this Wave 0 slice.
