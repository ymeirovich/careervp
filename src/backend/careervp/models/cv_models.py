"""Backward-compatible CV model imports.

This module is retained for compatibility while canonical CV models live in
careervp.models.cv.
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
