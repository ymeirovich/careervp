"""Re-export CV tailoring models for backward compatibility."""

from careervp.models.cv_tailoring_models import (
    ChangeLog,
    TailorCVRequest,
    TailoredCV,
    TailoredCVResponse,
    TailoringPreferences,
)

__all__ = [
    'TailoringPreferences',
    'TailorCVRequest',
    'TailoredCV',
    'TailoredCVResponse',
    'ChangeLog',
]
