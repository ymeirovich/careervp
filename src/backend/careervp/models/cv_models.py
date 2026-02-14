"""Backward-compatible CV model imports.

Canonical CV models live in ``careervp.models.cv``.
This module remains for compatibility and re-exports those types.
"""

from careervp.models.cv import (
    CV,
    Certification,
    ContactInfo,
    CVParseRequest,
    CVParseResponse,
    CVSection,
    Education,
    Skill,
    SkillLevel,
    UserCV,
    WorkExperience,
)

__all__ = [
    'CVSection',
    'CV',
    'CVParseRequest',
    'CVParseResponse',
    'Certification',
    'ContactInfo',
    'Education',
    'Skill',
    'SkillLevel',
    'UserCV',
    'WorkExperience',
]
