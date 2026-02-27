"""Stub module for TrialService — placeholder for L3 trial enforcement logic."""


class TrialService:
    """Manages trial credits and enforcement for beta users."""

    def check_trial_status(self, user_id: str) -> dict[str, bool | int]:
        raise NotImplementedError

    def consume_credit(self, user_id: str) -> None:
        raise NotImplementedError
