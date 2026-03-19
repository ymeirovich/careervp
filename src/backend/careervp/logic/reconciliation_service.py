"""
ReconciliationService — nightly subscription sync against the payment provider.

Algorithm:
  1. scan_active_subscriptions() — all rows with sk=SUBSCRIPTION#CURRENT, status=active.
  2. For each item: retrieve_subscription(item["subscription_id"]) from the provider.
  3. Compare provider status to stored status; call upsert_subscription on divergence.
  4. Log each divergence at INFO with user_id, old_status, new_status.
  5. Catch per-user exceptions; increment error counter and continue — one bad user
     must never abort the entire nightly run.
  6. Return {"checked": n, "updated": n, "errors": n}.

Constraints:
  - NEVER call scan_active_subscriptions from any HTTP handler — reconcile only.
  - Never return 500 if a single user fails (catch and continue).
"""

from __future__ import annotations

from typing import Any

from careervp.handlers.utils.observability import logger


class ReconciliationService:
    """Syncs active subscriptions against the payment provider."""

    def __init__(
        self,
        subscription_repo: Any,
        payment_provider: Any,
    ) -> None:
        self._sub_repo = subscription_repo
        self._payment_provider = payment_provider

    def reconcile_all(self) -> dict[str, int]:
        """Scan active subscriptions and reconcile divergences with the provider.

        Returns a summary dict: {"checked": n, "updated": n, "errors": n}.
        Per-user exceptions are caught and counted — they never abort the run.
        """
        items = self._sub_repo.scan_active_subscriptions()
        checked = len(items)
        updated = 0
        errors = 0

        for item in items:
            user_id = item.get('user_id', '')
            subscription_id = item.get('subscription_id', '')
            stored_status = item.get('status', '')

            try:
                provider_sub = self._payment_provider.retrieve_subscription(subscription_id)
                provider_status = provider_sub.get('status', stored_status)

                if provider_status != stored_status:
                    logger.info(
                        'reconciliation_divergence',
                        user_id=user_id,
                        subscription_id=subscription_id,
                        old_status=stored_status,
                        new_status=provider_status,
                    )
                    self._sub_repo.upsert_subscription(
                        user_id,
                        {**item, 'status': provider_status},
                    )
                    updated += 1

            except Exception as exc:
                logger.error(
                    'reconciliation_user_error',
                    user_id=user_id,
                    subscription_id=subscription_id,
                    error=str(exc),
                )
                errors += 1

        logger.info('reconcile_complete', checked=checked, updated=updated, errors=errors)
        return {'checked': checked, 'updated': updated, 'errors': errors}


__all__ = ['ReconciliationService']
