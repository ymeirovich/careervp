"""
Pydantic models for user profile management.
"""

from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    """User profile model used by /users/me endpoints."""

    user_id: Annotated[str, Field(description='Unique user identifier')]
    email: Annotated[EmailStr, Field(description='Primary email address')]
    name: Annotated[str, Field(description='Display name')]
    preferences: Annotated[dict[str, Any], Field(default_factory=dict, description='User preferences payload')]
    created_at: Annotated[datetime, Field(default_factory=lambda: datetime.now(timezone.utc))]
    updated_at: Annotated[datetime, Field(default_factory=lambda: datetime.now(timezone.utc))]

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize the user profile in API response shape."""
        return {
            'id': self.user_id,
            'user_id': self.user_id,
            'email': self.email,
            'name': self.name,
            'preferences': self.preferences,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
