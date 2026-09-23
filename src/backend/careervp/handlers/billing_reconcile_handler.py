"""
Lambda handler for nightly subscription reconciliation.

Triggered by EventBridge scheduled rule with:
  { "detail": { "action": "reconcile_subscriptions" } }

Any other event shape returns {"status": "ignored"} immediately.
"""

from __future__ import annotations

from typing import Any

from careervp.dal.subscription_repository import SubscriptionRepository
from careervp.handlers.utils.observability import logger, tracer
from careervp.logic.reconciliation_service import ReconciliationService
from careervp.payment_providers.factory import get_payment_provider

_reconciliation_service: ReconciliationService | None = None


def _get_reconciliation_service() -> ReconciliationService:
    global _reconciliation_service
    if _reconciliation_service is None:
        _reconciliation_service = ReconciliationService(
            subscription_repo=SubscriptionRepository(),
            provider_factory=get_payment_provider,
        )
    return _reconciliation_service


@logger.inject_lambda_context(log_event=False)
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ARG001
    """Route EventBridge reconciliation events to ReconciliationService."""
    action = event.get('detail', {}).get('action')
    if action != 'reconcile_subscriptions':
        logger.info('billing_reconcile_ignored', action=action)
        return {'status': 'ignored'}

    svc = _get_reconciliation_service()
    result = svc.reconcile_all()

    logger.info(f'reconcile_complete {result}')
    return {'status': 'ok', **result}
