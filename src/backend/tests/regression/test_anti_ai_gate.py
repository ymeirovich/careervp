"""Regression tests — anti-AI and quality gate thresholds must never weaken."""

from __future__ import annotations

import pytest


@pytest.mark.regression
class TestAntiAIGateThresholds:
    def test_anti_ai_min_score_is_9_0(self) -> None:
        """ANTI_AI_MIN_SCORE must remain exactly 90."""
        from careervp.logic.fvs_validator import ANTI_AI_MIN_SCORE

        assert ANTI_AI_MIN_SCORE == 90, (
            f'ANTI_AI_MIN_SCORE was changed to {ANTI_AI_MIN_SCORE}. This threshold must not be reduced — it guards output quality.'
        )

    def test_grammar_min_score_is_9_0(self) -> None:
        """GRAMMAR_MIN_SCORE must remain exactly 90."""
        from careervp.logic.fvs_validator import GRAMMAR_MIN_SCORE

        assert GRAMMAR_MIN_SCORE == 90, f'GRAMMAR_MIN_SCORE was changed to {GRAMMAR_MIN_SCORE}. Threshold must not be reduced.'

    def test_tone_min_score_is_8_0(self) -> None:
        """TONE_MIN_SCORE must remain exactly 80."""
        from careervp.logic.fvs_validator import TONE_MIN_SCORE

        assert TONE_MIN_SCORE == 80, f'TONE_MIN_SCORE was changed to {TONE_MIN_SCORE}.'

    def test_structural_min_score_is_8_0(self) -> None:
        """STRUCTURE_MIN_SCORE must remain exactly 80."""
        from careervp.logic.fvs_validator import STRUCTURE_MIN_SCORE

        assert STRUCTURE_MIN_SCORE == 80, f'STRUCTURE_MIN_SCORE was changed to {STRUCTURE_MIN_SCORE}.'

    def test_max_stage6_retries_is_3(self) -> None:
        """MAX_STAGE6_RETRIES must remain 1 after the quality-warning fallback change."""
        from careervp.logic.vpr_generator import MAX_STAGE6_RETRIES

        assert MAX_STAGE6_RETRIES == 1, (
            f'MAX_STAGE6_RETRIES was changed to {MAX_STAGE6_RETRIES}. This controls maximum LLM retry cost per VPR generation.'
        )

    def test_banned_words_count_not_reduced(self) -> None:
        """BANNED_WORDS list must not shrink below the baseline of 14 terms."""
        from careervp.logic.prompts.vpr_prompt import BANNED_WORDS

        # Baseline: 14 terms as of spec 02 (leverage, delve into, landscape, robust,
        # streamline, utilize, facilitate, implement, cutting-edge, best practices,
        # industry-leading, game-changer, paradigm shift, synergy)
        BASELINE_BANNED_WORD_COUNT = 14
        actual_count = len(BANNED_WORDS)

        assert actual_count >= BASELINE_BANNED_WORD_COUNT, (
            f'BANNED_WORDS shrank from {BASELINE_BANNED_WORD_COUNT} to {actual_count}. Do not remove banned terms — only add new ones.'
        )
