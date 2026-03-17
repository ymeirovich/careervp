"""
Unit tests for QuotaService (access enforcement).

Mirrors TypeScript tests:
  quota-enforcement.test.ts (F-SUB-017)
  trial.test.ts             (F-SUB-001 through F-SUB-003)
  backward-compat-*.test.ts

Spec: docs/best_practices/yaml/testing_spec.yaml
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# ─── Inline QuotaService (implementation lives in logic/quota_service.py)
# These tests define the expected contract. ────────────────────────────────────


class QuotaError(Exception):
    """Raised by QuotaService when a user is blocked."""

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
        subscription_repo: MagicMock,
        trial_service: MagicMock,
    ) -> None:
        self._sub_repo = subscription_repo
        self._trial = trial_service

    def check_access(self, user_id: str) -> None:
        """Raise QuotaError if user is not allowed to create a new application."""
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

        # No subscription or non-blocked non-active status → trial enforcement
        usage = self._trial.get_usage(user_id)

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


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_service(
    *,
    subscription: dict | None = None,
    trial_usage: dict | None = None,
) -> tuple[QuotaService, MagicMock, MagicMock]:
    sub_repo = MagicMock()
    trial_service = MagicMock()

    sub_result = MagicMock()
    sub_result.success = True
    sub_result.data = subscription
    sub_repo.get_subscription.return_value = sub_result

    trial_service.get_usage.return_value = trial_usage or {
        'trial_active': True,
        'days_remaining': 14,
        'credits_remaining': 3,
    }

    return QuotaService(sub_repo, trial_service), sub_repo, trial_service


def _sub(status: str) -> dict:
    return {'subscription_id': f'sub_{status}', 'user_id': 'user-test', 'status': status}


# ─── F-SUB-017: Blocked States ────────────────────────────────────────────────


@pytest.mark.unit
class TestBlockedSubscriptionStates:
    @pytest.mark.parametrize('status', ['past_due', 'canceled', 'expired'])
    def test_blocked_status_raises_quota_error_403(self, status: str) -> None:
        svc, _, _ = _make_service(subscription=_sub(status))

        with pytest.raises(QuotaError) as exc_info:
            svc.check_access('user-017')

        assert exc_info.value.status_code == 403

    @pytest.mark.parametrize('status', ['past_due', 'canceled', 'expired'])
    def test_blocked_status_error_code_is_subscription_required(self, status: str) -> None:
        svc, _, _ = _make_service(subscription=_sub(status))

        with pytest.raises(QuotaError) as exc_info:
            svc.check_access('user-017')

        assert exc_info.value.error == 'subscription_required'

    def test_active_subscription_allows_access(self) -> None:
        svc, _, _ = _make_service(subscription=_sub('active'))

        # Should not raise
        svc.check_access('user-017')

    def test_blocked_status_checked_before_trial(self) -> None:
        """DAL is called first; trial service must NOT be called for active-status check."""
        svc, sub_repo, trial_service = _make_service(subscription=_sub('past_due'))

        with pytest.raises(QuotaError):
            svc.check_access('user-017')

        sub_repo.get_subscription.assert_called_once_with('user-017')
        trial_service.get_usage.assert_not_called()

    def test_active_subscription_does_not_check_trial(self) -> None:
        svc, _, trial_service = _make_service(subscription=_sub('active'))

        svc.check_access('user-active')

        trial_service.get_usage.assert_not_called()


# ─── Trial enforcement (no subscription) ─────────────────────────────────────


@pytest.mark.unit
class TestTrialEnforcement:
    def test_trial_with_credits_allows_access(self) -> None:
        svc, _, _ = _make_service(
            subscription=None,
            trial_usage={'trial_active': True, 'days_remaining': 10, 'credits_remaining': 2},
        )

        svc.check_access('user-trial')  # no raise

    def test_exhausted_trial_raises_trial_exhausted(self) -> None:
        svc, _, _ = _make_service(
            subscription=None,
            trial_usage={'trial_active': True, 'days_remaining': 5, 'credits_remaining': 0},
        )

        with pytest.raises(QuotaError) as exc_info:
            svc.check_access('user-trial')

        assert exc_info.value.error == 'trial_exhausted'
        assert exc_info.value.status_code == 403

    def test_expired_trial_raises_trial_expired(self) -> None:
        svc, _, _ = _make_service(
            subscription=None,
            trial_usage={'trial_active': False, 'days_remaining': 0, 'credits_remaining': 1},
        )

        with pytest.raises(QuotaError) as exc_info:
            svc.check_access('user-trial')

        assert exc_info.value.error == 'trial_expired'
        assert exc_info.value.status_code == 403

    def test_no_subscription_calls_trial_service(self) -> None:
        svc, _, trial_service = _make_service(
            subscription=None,
            trial_usage={'trial_active': True, 'days_remaining': 14, 'credits_remaining': 3},
        )

        svc.check_access('user-trial')

        trial_service.get_usage.assert_called_once_with('user-trial')


# ─── Backward-compat: missing/partial subscription data ──────────────────────


@pytest.mark.unit
class TestBackwardCompatibility:
    def test_missing_subscription_falls_back_to_trial(self) -> None:
        """User with no subscription row must be handled as trial user."""
        svc, sub_repo, trial_service = _make_service(
            subscription=None,
            trial_usage={'trial_active': True, 'days_remaining': 14, 'credits_remaining': 3},
        )

        svc.check_access('user-no-sub')

        # trial service is consulted
        trial_service.get_usage.assert_called_once()

    def test_subscription_with_missing_status_falls_back_to_trial(self) -> None:
        """Partial subscription row with no 'status' key must not crash."""
        svc, _, trial_service = _make_service(
            subscription={'subscription_id': 'sub_partial'},
            trial_usage={'trial_active': True, 'days_remaining': 5, 'credits_remaining': 1},
        )

        svc.check_access('user-partial')

        # No status means non-active, non-blocked → falls to trial path
        trial_service.get_usage.assert_called_once()

    def test_missing_credits_remaining_treated_as_zero(self) -> None:
        svc, _, _ = _make_service(
            subscription=None,
            trial_usage={'trial_active': True},  # no 'credits_remaining' key
        )

        with pytest.raises(QuotaError) as exc_info:
            svc.check_access('user-missing-credits')

        assert exc_info.value.error == 'trial_exhausted'

    def test_missing_trial_active_treated_as_expired(self) -> None:
        svc, _, _ = _make_service(
            subscription=None,
            trial_usage={'credits_remaining': 3},  # no 'trial_active' key
        )

        with pytest.raises(QuotaError) as exc_info:
            svc.check_access('user-missing-trial-flag')

        assert exc_info.value.error == 'trial_expired'
