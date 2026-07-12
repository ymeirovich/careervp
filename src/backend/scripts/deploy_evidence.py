#!/usr/bin/env python3
"""Shared deploy-gate evidence validators (P-21, P-29, P-32).

These functions turn a captured evidence document into a list of gate errors.
An empty list means the gate passes; a non-empty list means the deploy gate
must stay *blocked*. The validators fail **closed**: missing or malformed
evidence is treated as a failure, never as an implicit pass, so a human never
assumes delivery/backup happened when the record does not prove it.
"""

from __future__ import annotations

from typing import Mapping, Sequence

SENSITIVE_MARKERS: tuple[str, ...] = (
    'secret',
    'token',
    'password',
    'api_key',
    'apikey',
    'private',
    'credential',
)

REDACTED = '***REDACTED***'


def validate_sns_subscription_confirmed(evidence: Mapping[str, object]) -> list[str]:
    """P-21 gate: require a Confirmed SNS subscription with an ARN.

    Fails closed when the ``sns_subscriptions`` section is absent, empty, or
    contains no entry whose status is ``Confirmed`` and which carries a
    subscription ARN. A ``PendingConfirmation`` subscription does not satisfy
    the gate — delivery is not proven until the human confirms the inbox.
    """
    subscriptions = evidence.get('sns_subscriptions')
    if not isinstance(subscriptions, Sequence) or isinstance(subscriptions, (str, bytes)):
        return ['sns_subscriptions evidence is missing (gate fails closed)']
    if not subscriptions:
        return ['sns_subscriptions evidence is empty (gate fails closed)']

    confirmed = [
        entry
        for entry in subscriptions
        if isinstance(entry, Mapping)
        and str(entry.get('status', '')).strip().lower() == 'confirmed'
        and str(entry.get('subscription_arn', '')).strip()
    ]
    if not confirmed:
        return ['no Confirmed SNS subscription with an ARN found (gate fails closed)']
    return []


def validate_budget_evidence(evidence: Mapping[str, object]) -> list[str]:
    """P-32 Wave 0 gate: require a human-created AWS Budget record.

    AWS Budgets and Cost Anomaly Detection are console-only for this slice
    (per specs/P-32-cost-obs-edge-spec.md) — there is no CDK resource to
    synth, so the only proof available is a human-captured evidence document.
    Fails closed when the ``aws_budget`` section is absent or missing any of
    the budget name, a numeric threshold, a subscriber (email/SNS endpoint),
    or a capture timestamp.
    """
    budget = evidence.get('aws_budget')
    if not isinstance(budget, Mapping):
        return ['aws_budget evidence is missing (gate fails closed)']

    errors: list[str] = []
    name = str(budget.get('budget_name', '')).strip()
    if not name:
        errors.append('aws_budget.budget_name is missing')

    threshold = budget.get('threshold_amount')
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or threshold <= 0:
        errors.append('aws_budget.threshold_amount is missing or not a positive number')

    subscriber = str(budget.get('subscriber', '')).strip()
    if not subscriber:
        errors.append('aws_budget.subscriber is missing')

    timestamp = str(budget.get('captured_at', '')).strip()
    if not timestamp:
        errors.append('aws_budget.captured_at is missing')

    return errors


def validate_cost_anomaly_evidence(evidence: Mapping[str, object]) -> list[str]:
    """P-32 Wave 0 gate: require a human-created Cost Anomaly Detection monitor + subscription.

    Fails closed when the ``cost_anomaly_detection`` section is absent or
    missing the monitor ARN, the subscription ARN, or a capture timestamp.
    """
    anomaly = evidence.get('cost_anomaly_detection')
    if not isinstance(anomaly, Mapping):
        return ['cost_anomaly_detection evidence is missing (gate fails closed)']

    errors: list[str] = []
    monitor_arn = str(anomaly.get('monitor_arn', '')).strip()
    if not monitor_arn:
        errors.append('cost_anomaly_detection.monitor_arn is missing')

    subscription_arn = str(anomaly.get('subscription_arn', '')).strip()
    if not subscription_arn:
        errors.append('cost_anomaly_detection.subscription_arn is missing')

    timestamp = str(anomaly.get('captured_at', '')).strip()
    if not timestamp:
        errors.append('cost_anomaly_detection.captured_at is missing')

    return errors


def validate_dynamodb_backups(evidence: Mapping[str, object]) -> list[str]:
    """P-29 gate: require at least one recorded on-demand DynamoDB backup ARN."""
    backups = evidence.get('dynamodb_backups')
    if not isinstance(backups, Sequence) or isinstance(backups, (str, bytes)):
        return ['dynamodb_backups evidence is missing (gate fails closed)']
    arns = [entry for entry in backups if isinstance(entry, Mapping) and str(entry.get('backup_arn', '')).strip()]
    if not arns:
        return ['no DynamoDB backup ARNs recorded (gate fails closed)']
    return []


def redact_secrets(env: Mapping[str, object]) -> dict[str, object]:
    """Return a copy of a Lambda env mapping with sensitive *values* redacted.

    Key names are preserved so the shape of the config is auditable; only the
    values of keys whose name looks sensitive are replaced.
    """
    redacted: dict[str, object] = {}
    for key, value in env.items():
        lowered = key.lower()
        if any(marker in lowered for marker in SENSITIVE_MARKERS):
            redacted[key] = REDACTED
        else:
            redacted[key] = value
    return redacted


def require(errors: Sequence[str]) -> None:
    """Raise if any gate errors are present."""
    if errors:
        raise DeployGateBlocked('; '.join(errors))


class DeployGateBlocked(RuntimeError):
    """Raised when a deploy-gate evidence check fails closed."""
