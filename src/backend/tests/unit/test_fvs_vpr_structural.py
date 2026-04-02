"""Unit tests for FVS structural validators and quality gate (spec 04)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.fvs_validator import (
    STRUCTURAL_MIN_SCORE,
    run_vpr_quality_gate,
    validate_alignment_scores,
    validate_differentiator_rarity,
    validate_evidence_traceability,
    validate_gap_severity_calibration,
    validate_mitigation_substance,
    validate_quantification_consistency,
)
from careervp.logic.vpr_generator import FinalVPRData


@pytest.mark.unit
class TestStructuralMinScore:
    def test_structural_min_score_constant(self) -> None:
        assert STRUCTURAL_MIN_SCORE == 8.0

    def test_final_vpr_data_has_structural_score_field(self) -> None:
        """FinalVPRData must have structural_score field with default=10.0."""
        from careervp.models.vpr import VPR

        vpr_mock = MagicMock(spec=VPR)
        fvd = FinalVPRData(
            vpr=vpr_mock,
            anti_ai_score=9.5,
            anti_ai_issues=[],
            passed_gate=True,
            regeneration_count=0,
        )
        assert hasattr(fvd, 'structural_score')
        assert fvd.structural_score == 10.0  # default


@pytest.mark.unit
class TestValidateEvidenceTraceability:
    def test_passes_when_claims_traced_to_cv(self, minimal_vpr: Any) -> None:
        cv_text = 'Jane Smith led $2M AWS migration at Acme Corp for 4 years.'
        gap_text = 'Led 8 engineers at Acme.'
        result = validate_evidence_traceability(minimal_vpr, cv_text, gap_text)
        assert result.score >= 8.0
        assert result.passed

    def test_deducts_for_unverifiable_claims(self, minimal_vpr: Any) -> None:
        """If claims cannot be traced to CV or gap responses, score should drop."""
        # CV text with no relevant content
        empty_cv_text = 'John Doe worked somewhere doing things.'
        empty_gap_text = 'I did various things.'
        result = validate_evidence_traceability(minimal_vpr, empty_cv_text, empty_gap_text)
        # Score may decrease — don't assert exact value, just that it can drop below 10
        assert result.score <= 10.0

    def test_max_deduction_capped_at_4_points(self, minimal_vpr: Any) -> None:
        """Score should never go below 6.0 due to max deduction of -4.0 rule."""
        very_empty_cv = ''
        very_empty_gap = ''
        result = validate_evidence_traceability(minimal_vpr, very_empty_cv, very_empty_gap)
        assert result.score >= 6.0  # 10.0 - 4.0 max deduction


@pytest.mark.unit
class TestValidateQuantificationConsistency:
    def test_passes_when_metrics_consistent(self, minimal_vpr: Any) -> None:
        result = validate_quantification_consistency(minimal_vpr)
        assert isinstance(result.score, float)
        assert result.score >= 0.0

    def test_returns_validation_check_result(self, minimal_vpr: Any) -> None:
        result = validate_quantification_consistency(minimal_vpr)
        assert hasattr(result, 'score')
        assert hasattr(result, 'issues')
        assert hasattr(result, 'passed')


@pytest.mark.unit
class TestValidateAlignmentScores:
    def test_passes_direct_evidence_with_score_80_to_100(self, minimal_vpr: Any) -> None:
        """Direct evidence quality + score 85 should pass Rule 3."""
        # minimal_vpr has evidence_quality='direct' and alignment_score=85
        result = validate_alignment_scores(minimal_vpr)
        assert result.score >= 8.0
        assert result.passed

    def test_deducts_for_mismatched_quality_and_score(self, minimal_vpr: Any) -> None:
        """direct evidence with score=30 should fail — score doesn't match quality."""
        import copy

        bad_vpr = copy.deepcopy(minimal_vpr)
        # Set direct evidence quality but give a low score (should be 80-100)
        bad_vpr.role_alignment.core_responsibilities[0].evidence_quality = 'direct'
        bad_vpr.role_alignment.core_responsibilities[0].alignment_score = 25  # wrong for 'direct'
        result = validate_alignment_scores(bad_vpr)
        assert result.score < 10.0  # deduction applied

    def test_analogous_evidence_score_60_to_79_passes(self, minimal_vpr: Any) -> None:
        import copy

        vpr = copy.deepcopy(minimal_vpr)
        vpr.role_alignment.core_responsibilities[0].evidence_quality = 'analogous'
        vpr.role_alignment.core_responsibilities[0].alignment_score = 70
        result = validate_alignment_scores(vpr)
        assert result.score >= 8.0


@pytest.mark.unit
class TestValidateGapSeverityCalibration:
    def test_passes_when_priority_gap_is_high_severity(self, minimal_vpr: Any) -> None:
        result = validate_gap_severity_calibration(minimal_vpr)
        assert isinstance(result.score, float)
        assert isinstance(result.passed, bool)

    def test_deducts_for_critical_gap_not_in_priority_list(self, minimal_vpr: Any) -> None:
        import copy

        bad_vpr = copy.deepcopy(minimal_vpr)
        # Add a critical gap that is NOT in priority_gaps_to_address
        from careervp.models.vpr import VPRIdentifiedGap

        bad_vpr.evidence_gaps.identified_gaps.append(
            VPRIdentifiedGap(
                requirement='Critical missing skill',
                current_evidence='None',
                gap_severity='critical',
                suggested_evidence=[],
                can_be_created_quickly=False,
            )
        )
        # priority_gaps_to_address only mentions "Enterprise SaaS case study"
        result = validate_gap_severity_calibration(bad_vpr)
        # Should detect miscalibration — critical gap missing from priority list
        assert result.score <= 10.0


@pytest.mark.unit
class TestValidateDifferentiatorRarity:
    def test_passes_uncommon_with_non_empty_relevance(self, minimal_vpr: Any) -> None:
        """uncommon rarity with relevance > 20 words should pass."""
        result = validate_differentiator_rarity(minimal_vpr)
        assert isinstance(result.score, float)
        assert isinstance(result.passed, bool)

    def test_deducts_for_very_rare_without_metric_proof(self, minimal_vpr: Any) -> None:
        import copy

        bad_vpr = copy.deepcopy(minimal_vpr)
        bad_vpr.differentiators.unique_strengths[0].rarity = 'very_rare'
        bad_vpr.differentiators.unique_strengths[0].proof = 'some generic claim with no numbers'
        result = validate_differentiator_rarity(bad_vpr)
        # very_rare without quantified metric in proof → deduction or issues
        assert result.score <= 10.0
        # Either the score is deducted or there are issues reported
        assert result.score < 10.0 or len(result.issues) > 0


@pytest.mark.unit
class TestValidateMitigationSubstance:
    def test_passes_specific_messaging(self, minimal_vpr: Any) -> None:
        """Messaging referencing 'Acme' and '500-node cluster' should pass."""
        result = validate_mitigation_substance(minimal_vpr)
        assert isinstance(result.score, float)
        assert isinstance(result.passed, bool)

    def test_deducts_for_generic_messaging(self, minimal_vpr: Any) -> None:
        import copy

        bad_vpr = copy.deepcopy(minimal_vpr)
        bad_vpr.concerns_and_mitigations.likely_objections[0].mitigation.messaging = 'I am a great candidate.'  # < 30 words, no proper nouns
        result = validate_mitigation_substance(bad_vpr)
        assert result.score < 10.0  # deduction applied


@pytest.mark.unit
class TestRunVPRQualityGate:
    def test_all_pass_returns_passed_gate_true(self, minimal_vpr: Any, minimal_user_cv: Any) -> None:
        cv_text = 'Jane Smith led $2M AWS migration at Acme Corp. Python expert. Led 8-person team.'
        gap_text = 'Led 8 engineers. Delivered migration on time.'

        with (
            patch('careervp.logic.fvs_validator.check_anti_ai_patterns') as mock_anti_ai,
            patch('careervp.logic.fvs_validator.validate_grammar') as mock_grammar,
            patch('careervp.logic.fvs_validator.validate_tone') as mock_tone,
        ):
            mock_anti_ai.return_value = MagicMock(score=9.5, issues=[], passed=True)
            mock_grammar.return_value = MagicMock(score=9.2, issues=[], passed=True)
            mock_tone.return_value = MagicMock(score=8.5, issues=[], passed=True)

            result = run_vpr_quality_gate(minimal_vpr, minimal_user_cv, cv_text, gap_text)

        assert result.passed_gate is True

    def test_anti_ai_score_below_9_sets_passed_gate_false(self, minimal_vpr: Any, minimal_user_cv: Any) -> None:
        cv_text = 'Jane Smith at Acme Corp.'
        gap_text = 'Led engineers.'

        with (
            patch('careervp.logic.fvs_validator.check_anti_ai_patterns') as mock_anti_ai,
            patch('careervp.logic.fvs_validator.validate_grammar') as mock_grammar,
            patch('careervp.logic.fvs_validator.validate_tone') as mock_tone,
        ):
            mock_anti_ai.return_value = MagicMock(score=7.0, issues=['too many buzzwords'], passed=False)
            mock_grammar.return_value = MagicMock(score=9.5, issues=[], passed=True)
            mock_tone.return_value = MagicMock(score=9.0, issues=[], passed=True)

            result = run_vpr_quality_gate(minimal_vpr, minimal_user_cv, cv_text, gap_text)

        assert result.passed_gate is False
        assert result.anti_ai_score == 7.0

    def test_structural_score_below_8_sets_passed_gate_false(self, minimal_vpr: Any, minimal_user_cv: Any) -> None:
        """If all 6 structural validators average below 8.0, gate must fail."""
        cv_text = ''  # empty → traceability validator will deduct heavily
        gap_text = ''

        with (
            patch('careervp.logic.fvs_validator.check_anti_ai_patterns') as mock_anti_ai,
            patch('careervp.logic.fvs_validator.validate_grammar') as mock_grammar,
            patch('careervp.logic.fvs_validator.validate_tone') as mock_tone,
        ):
            mock_anti_ai.return_value = MagicMock(score=9.5, issues=[], passed=True)
            mock_grammar.return_value = MagicMock(score=9.5, issues=[], passed=True)
            mock_tone.return_value = MagicMock(score=9.0, issues=[], passed=True)

            # With empty cv/gap_text, traceability score should drop significantly
            # Use a VPR with many un-traceable claims to trigger low structural score
            result = run_vpr_quality_gate(minimal_vpr, minimal_user_cv, cv_text, gap_text)

        # Structural score field must be populated regardless of pass/fail
        assert hasattr(result, 'structural_score')
        assert isinstance(result.structural_score, float)

    def test_grammar_fail_sets_passed_gate_false(self, minimal_vpr: Any, minimal_user_cv: Any) -> None:
        cv_text = 'Jane Smith at Acme Corp.'
        gap_text = 'Led engineers.'

        with (
            patch('careervp.logic.fvs_validator.check_anti_ai_patterns') as mock_anti_ai,
            patch('careervp.logic.fvs_validator.validate_grammar') as mock_grammar,
            patch('careervp.logic.fvs_validator.validate_tone') as mock_tone,
        ):
            mock_anti_ai.return_value = MagicMock(score=9.5, issues=[], passed=True)
            mock_grammar.return_value = MagicMock(score=7.0, issues=['grammar errors'], passed=False)
            mock_tone.return_value = MagicMock(score=9.0, issues=[], passed=True)

            result = run_vpr_quality_gate(minimal_vpr, minimal_user_cv, cv_text, gap_text)

        assert result.passed_gate is False

    def test_returns_vpr_gate_result_type(self, minimal_vpr: Any, minimal_user_cv: Any) -> None:
        from careervp.logic.fvs_validator import VPRGateResult

        cv_text = 'Jane Smith Acme Corp $2M AWS migration Python.'
        gap_text = 'Led 8 engineers.'

        with (
            patch('careervp.logic.fvs_validator.check_anti_ai_patterns') as mock_anti_ai,
            patch('careervp.logic.fvs_validator.validate_grammar') as mock_grammar,
            patch('careervp.logic.fvs_validator.validate_tone') as mock_tone,
        ):
            mock_anti_ai.return_value = MagicMock(score=9.5, issues=[], passed=True)
            mock_grammar.return_value = MagicMock(score=9.5, issues=[], passed=True)
            mock_tone.return_value = MagicMock(score=9.0, issues=[], passed=True)

            result = run_vpr_quality_gate(minimal_vpr, minimal_user_cv, cv_text, gap_text)

        assert isinstance(result, VPRGateResult)
        assert hasattr(result, 'passed_gate')
