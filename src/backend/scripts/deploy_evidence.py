#!/usr/bin/env python3
"""Shared deploy-gate evidence validators (P-21, P-29).

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
