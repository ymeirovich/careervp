"""
VPR prompt builder tests (Task 04).
"""

from careervp.logic.prompts.vpr_prompt import BANNED_WORDS, check_anti_ai_patterns

# build_vpr_prompt removed per spec 09 (replaced by build_phase2_prompt)

# TestBuildVPRPrompt class removed per spec 09


class TestAntiAIPatterns:
    def test_detects_banned_terms(self) -> None:
        content = f'This tries to {BANNED_WORDS[0]} outcomes and embrace synergy.'
        matches = check_anti_ai_patterns(content)

        assert BANNED_WORDS[0] in matches
        assert 'synergy' in matches
