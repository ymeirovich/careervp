from __future__ import annotations

from careervp.models import fvs as fvs_models_primary
from careervp.models import fvs_models as fvs_models_compat


def test_new_fvs_models_exist() -> None:
    assert fvs_models_primary.FVSResult is not None
    assert fvs_models_primary.QualityScore is not None
    assert fvs_models_primary.GrammarIssue is not None
    assert fvs_models_primary.ToneIssue is not None


def test_quality_score_model_accepts_expected_fields() -> None:
    score = fvs_models_primary.QualityScore(
        grammar_score=9.2,
        tone_score=8.8,
        ai_pattern_score=9.1,
        formatting_score=8.6,
        structure_score=8.4,
    )
    assert score.grammar_score == 9.2
    assert score.tone_score == 8.8
    assert score.ai_pattern_score == 9.1
    assert score.formatting_score == 8.6
    assert score.structure_score == 8.4


def test_fvs_result_references_quality_and_issues() -> None:
    result = fvs_models_primary.FVSResult(
        overall_score=8.7,
        quality_score=fvs_models_primary.QualityScore(
            grammar_score=9.0,
            tone_score=8.5,
            ai_pattern_score=9.4,
            formatting_score=8.1,
            structure_score=8.6,
        ),
        grammar_issues=[fvs_models_primary.GrammarIssue(message='Passive voice', suggestion='Use active voice')],
        tone_issues=[fvs_models_primary.ToneIssue(message='Too informal', recommendation='Use professional phrasing')],
        recommendations=['Tighten structure in summary paragraph'],
    )
    assert result.overall_score == 8.7
    assert result.quality_score is not None
    assert len(result.grammar_issues) == 1
    assert len(result.tone_issues) == 1


def test_legacy_fvs_models_module_reexports_canonical_models() -> None:
    assert fvs_models_compat.ImmutableFact is fvs_models_primary.ImmutableFact
    assert fvs_models_compat.FVSBaseline is fvs_models_primary.FVSBaseline
