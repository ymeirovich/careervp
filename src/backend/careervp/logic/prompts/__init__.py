"""
Prompt utilities shared across VPR generation flows.
"""

from careervp.logic.prompts.cover_letter_prompt import build_system_prompt as build_cover_letter_system_prompt
from careervp.logic.prompts.cover_letter_prompt import build_user_prompt as build_cover_letter_user_prompt
from careervp.logic.prompts.gap_analysis_prompt import build_system_prompt as build_gap_analysis_system_prompt
from careervp.logic.prompts.gap_analysis_prompt import build_user_prompt as build_gap_analysis_user_prompt
from careervp.logic.prompts.vpr_prompt import (
    BANNED_WORDS,
    VPR_GENERATION_PROMPT,
    build_vpr_prompt,
    check_anti_ai_patterns,
)

__all__ = [
    'BANNED_WORDS',
    'VPR_GENERATION_PROMPT',
    'build_vpr_prompt',
    'check_anti_ai_patterns',
    'build_cover_letter_system_prompt',
    'build_cover_letter_user_prompt',
    'build_gap_analysis_system_prompt',
    'build_gap_analysis_user_prompt',
]
