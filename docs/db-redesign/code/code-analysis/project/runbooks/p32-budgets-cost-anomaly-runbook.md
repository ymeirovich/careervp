# P-32 — Budgets + Cost Anomaly Detection Runbook (HUMAN-APPLIED, not automated)

The Wave 0 slice of P-32 is a **console-only** AWS Budgets + Cost Anomaly Detection
setup — see `specs/P-32-cost-obs-edge-spec.md` ("Do not store console-only
configuration as fake CDK code unless AWS ownership is moved into IaC by explicit
decision"). Its purpose: a retry-storm or runaway agent chain during Waves 0–4
must trip a dollar-threshold alarm instead of burning unbounded LLM/AWS spend
unmonitored.

The automatable half of this step is the **evidence gate** in
`src/backend/scripts/deploy_evidence.py` (`validate_budget_evidence`,
`validate_cost_anomaly_evidence`), RED-tested in
`src/backend/tests/unit/test_p32_budget_evidence.py`. Those functions fail
closed on a missing/incomplete evidence document — they cannot verify the AWS
account state itself. Only a human with console access can produce that state
and record it.

## 1. Create the AWS Budget
AWS Console → Billing and Cost Management → **Budgets** → Create budget:
- Budget type: **Cost budget**, monthly, recurring.
- Name: `careervp-dev-monthly` (or the account's chosen convention).
- Amount: set a threshold appropriate to the dev account's expected monthly
  spend (e.g. covers normal usage with headroom, but catches a runaway chain
  well before it becomes expensive).
- Alert thresholds: at minimum one **actual spend** alert (e.g. 80%) and one
  **forecasted spend** alert.
- Notification: add an email subscriber (or SNS topic) that a human actually
  monitors — reuse `careervp-monitoring` topic from
  `infra/careervp/monitoring.py:62-90` if appropriate, or a dedicated cost
  alert address.
- Save. Note the **budget name**, **threshold amount**, and **subscriber**
  (email address or SNS topic ARN).

## 2. Create a Cost Anomaly Detection monitor + subscription
AWS Console → Billing and Cost Management → **Cost Anomaly Detection**:
- Create a **Cost Monitor** (type: AWS Services, or Cost Category if one
  exists) scoped to the account/region in use.
- Create a **Subscription** for that monitor: choose an alert threshold
  (e.g. anomalies ≥ $X or ≥ Y% of expected spend), frequency (immediate or
  daily digest), and a notification recipient (email or SNS).
- Save. Note the **monitor ARN** and **subscription ARN** — both are shown on
  the monitor/subscription detail pages.

## 3. Record the evidence document
Capture the values from steps 1–2 into an evidence JSON matching the shape
`validate_budget_evidence` / `validate_cost_anomaly_evidence` expect:

```json
{
  "aws_budget": {
    "budget_name": "careervp-dev-monthly",
    "threshold_amount": 500,
    "subscriber": "careervp-alerts-dev@careervp.com",
    "captured_at": "<ISO-8601 timestamp of when you captured this>"
  },
  "cost_anomaly_detection": {
    "monitor_arn": "arn:aws:ce::<account-id>:anomalymonitor/<id>",
    "subscription_arn": "arn:aws:ce::<account-id>:anomalysubscription/<id>",
    "captured_at": "<ISO-8601 timestamp of when you captured this>"
  }
}
```

Store this file wherever this repo's other deploy-gate evidence lives (see
`src/backend/scripts/evidence_pack.py` / P-29's evidence pack for the sibling
pattern) and pass it through `validate_budget_evidence` +
`validate_cost_anomaly_evidence` before treating 0.56 as done. An agent
session cannot fabricate these ARNs — pasting real values back is the human's
part of this step.

## NOT part of this runbook
- Tags, correlation-ID propagation, log retention/alarms, and API request
  validators/models are the **P-32 remainder**, homed in Wave 5
  (`project-scope-lock.yaml:179`), not this Wave 0 slice.
