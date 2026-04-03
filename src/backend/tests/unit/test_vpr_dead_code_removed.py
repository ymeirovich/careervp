"""Guard tests confirming dead VPR prompt symbols are removed (spec 09).

Tests assert that the four deleted symbols no longer exist in vpr_prompt.py
or in prompts/__init__.py. Live symbols that vpr_generator.py depends on
are verified to still be present.

Expected state: RED until spec 09 is implemented (symbols still exist).
After spec 09: GREEN.
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestDeadSymbolsRemovedFromVprPrompt:
    """Dead symbols must not exist in careervp.logic.prompts.vpr_prompt."""

    def test_vpr_generation_prompt_removed(self) -> None:
        """VPR_GENERATION_PROMPT is superseded by PHASE2_PROMPT_2_1_TEMPLATE (spec 02)."""
        import careervp.logic.prompts.vpr_prompt as m

        assert not hasattr(m, 'VPR_GENERATION_PROMPT'), (
            'VPR_GENERATION_PROMPT is dead code — superseded by PHASE2_PROMPT_2_1_TEMPLATE. Remove it from vpr_prompt.py per spec 09.'
        )

    def test_build_vpr_prompt_removed(self) -> None:
        """build_vpr_prompt() is the builder for VPR_GENERATION_PROMPT — also dead."""
        import careervp.logic.prompts.vpr_prompt as m

        assert not hasattr(m, 'build_vpr_prompt'), (
            'build_vpr_prompt is dead code — its only caller is VPR_GENERATION_PROMPT. Remove it from vpr_prompt.py per spec 09.'
        )

    def test_phase2_validation_system_prompt_removed(self) -> None:
        """PHASE2_VALIDATION_SYSTEM_PROMPT was for the Stage 4 LLM call removed in spec 07."""
        import careervp.logic.prompts.vpr_prompt as m

        assert not hasattr(m, 'PHASE2_VALIDATION_SYSTEM_PROMPT'), (
            'PHASE2_VALIDATION_SYSTEM_PROMPT is dead code — Stage 4 LLM call was removed in spec 07. Remove it from vpr_prompt.py per spec 09.'
        )

    def test_build_phase2_validation_prompt_removed(self) -> None:
        """build_phase2_validation_prompt() was the Stage 4 builder — also dead since spec 07."""
        import careervp.logic.prompts.vpr_prompt as m

        assert not hasattr(m, 'build_phase2_validation_prompt'), (
            'build_phase2_validation_prompt is dead code — Stage 4 LLM call was removed in spec 07. Remove it from vpr_prompt.py per spec 09.'
        )


@pytest.mark.unit
class TestDeadSymbolsRemovedFromPromptsInit:
    """Dead symbols must not be exported from careervp.logic.prompts."""

    def test_vpr_generation_prompt_not_in_init_exports(self) -> None:
        import careervp.logic.prompts as m

        assert not hasattr(m, 'VPR_GENERATION_PROMPT'), 'VPR_GENERATION_PROMPT must be removed from prompts/__init__.py exports.'

    def test_build_vpr_prompt_not_in_init_exports(self) -> None:
        import careervp.logic.prompts as m

        assert not hasattr(m, 'build_vpr_prompt'), 'build_vpr_prompt must be removed from prompts/__init__.py exports.'


@pytest.mark.unit
class TestLiveSymbolsStillPresent:
    """Removing dead code must not affect live symbols imported by vpr_generator.py."""

    def test_phase2_system_prompt_present(self) -> None:
        """PHASE2_SYSTEM_PROMPT is imported by vpr_generator.py — must survive removal."""
        from careervp.logic.prompts.vpr_prompt import PHASE2_SYSTEM_PROMPT

        assert isinstance(PHASE2_SYSTEM_PROMPT, str)
        assert len(PHASE2_SYSTEM_PROMPT) > 50

    def test_build_phase2_prompt_present(self) -> None:
        """build_phase2_prompt() is imported by vpr_generator.py — must survive removal."""
        from careervp.logic.prompts.vpr_prompt import build_phase2_prompt

        assert callable(build_phase2_prompt)

    def test_banned_words_present(self) -> None:
        from careervp.logic.prompts.vpr_prompt import BANNED_WORDS

        assert isinstance(BANNED_WORDS, list)
        assert len(BANNED_WORDS) >= 10

    def test_check_anti_ai_patterns_present(self) -> None:
        from careervp.logic.prompts.vpr_prompt import check_anti_ai_patterns

        assert callable(check_anti_ai_patterns)

    def test_phase2_prompt_2_1_template_present(self) -> None:
        from careervp.logic.prompts.vpr_prompt import PHASE2_PROMPT_2_1_TEMPLATE

        assert isinstance(PHASE2_PROMPT_2_1_TEMPLATE, str)
        assert len(PHASE2_PROMPT_2_1_TEMPLATE) > 500
