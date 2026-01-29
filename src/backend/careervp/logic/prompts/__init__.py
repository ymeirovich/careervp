"""
Prompt utilities shared across VPR generation flows.
"""

from careervp.logic.prompts.vpr_prompt import (
    BANNED_WORDS,
    VPR_GENERATION_PROMPT,
    build_vpr_prompt,
    check_anti_ai_patterns,
)

__all__ = ['BANNED_WORDS', 'VPR_GENERATION_PROMPT', 'build_vpr_prompt', 'check_anti_ai_patterns']
