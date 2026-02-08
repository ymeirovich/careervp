"""FVS (Fact Verification System) models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel


class ViolationSeverity(str, Enum):
    """Severity levels for FVS violations."""

    CRITICAL = 'CRITICAL'
    WARNING = 'WARNING'
    INFO = 'INFO'


class FVSViolation(BaseModel):
    """Represents a single FVS violation."""

    field: str
    severity: ViolationSeverity
    expected: Any | None = None
    actual: Any | None = None


class FVSValidationResult(BaseModel):
    """Result of FVS validation."""

    violations: list[FVSViolation]

    @property
    def has_critical_violations(self) -> bool:
        return any(v.severity == ViolationSeverity.CRITICAL for v in self.violations)
