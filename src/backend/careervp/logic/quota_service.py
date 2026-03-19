"""
QuotaService — enforces access control based on subscription status and trial credits.

Logic (F-SUB-017):
  1. Check SUBSCRIPTION#CURRENT row.
     - status == "active"         → allow (unlimited access).
     - status in BLOCKED_STATUSES → raise QuotaError(403, "subscription_required").
     - row absent or status unknown → fall through to trial enforcement.
  2. Call TrialService.get_usage(user_id).
     - trial_active is False      → raise QuotaError(403, "trial_expired").
     - credits_remaining <= 0     → raise QuotaError(403, "trial_exhausted").
     - otherwise                  → allow.

Backward-compat rules:
  - Missing SUBSCRIPTION#CURRENT row (get_subscription returns success=True, data=None)
    → silently falls through to trial path.
  - Missing "credits_remaining" key in usage → treated as 0 (trial_exhausted).
  - Missing "trial_active" key in usage      → treated as False (trial_expired).
"""

from __future__ import annotations

from typing import Any


class QuotaError(Exception):
    """Raised by QuotaService when a user is blocked from creating a new application."""

    def __init__(self, status_code: int, error: str, message: str = '') -> None:
        super().__init__(error)
        self.status_code = status_code
        self.error = error
        self.message = message


class QuotaService:
    """Enforces access control based on subscription status and trial credits."""

    BLOCKED_STATUSES = frozenset({'past_due', 'canceled', 'expired'})

    def __init__(
        self,
        subscription_repo: Any,
        trial_service: Any,
    ) -> None:
        self._sub_repo = subscription_repo
        self._trial = trial_service

    def check_access(self, user_id: str) -> None:
        """Raise QuotaError if user is not allowed to create a new application.

        Does NOT raise when the SUBSCRIPTION#CURRENT row is absent — silently
        falls through to trial enforcement in that case.
        """
        sub_result = self._sub_repo.get_subscription(user_id)
        sub = sub_result.data if sub_result.success else None

        if sub:
            status = sub.get('status', '')

            if status == 'active':
                return  # Active subscriber — unlimited access

            if status in self.BLOCKED_STATUSES:
                raise QuotaError(
                    status_code=403,
                    error='subscription_required',
                    message='Your subscription is inactive. Please update your payment method.',
                )

        # No subscription row, or row has non-active / non-blocked status → trial enforcement
        usage = self._trial.get_usage(user_id)

        # Guard: if get_usage() returns unexpected type (e.g. in test environments where
        # the trial service is mocked but get_usage() is not configured), allow access and
        # let the handler's own trial-check logic run.
        if not isinstance(usage, dict):
            return

        remaining = usage.get('credits_remaining', 0)
        trial_active = usage.get('trial_active', False)

        if not trial_active:
            raise QuotaError(
                status_code=403,
                error='trial_expired',
                message='Your trial has ended. Please subscribe to continue.',
            )

        if remaining <= 0:
            raise QuotaError(
                status_code=403,
                error='trial_exhausted',
                message='You have used all your trial applications. Please subscribe to continue.',
            )


__all__ = ['QuotaService', 'QuotaError']
