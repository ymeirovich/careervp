"""Stub module for ApplicationRepository — placeholder for L3 application state logic."""


class ApplicationRepository:
    """Manages application state persistence in DynamoDB."""

    def update_state(self, application_id: str, state: str) -> None:
        raise NotImplementedError
