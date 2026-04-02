"""Unit tests for the new 10-section VPR Pydantic models (spec 01)."""

from __future__ import annotations

import json

import pytest

from careervp.models.vpr import (
    VPR,
    VPRCompetitiveAdvantage,
    VPRConcern,
    VPRDifferentiators,
    VPRExecutiveSummary,
    VPRExperienceGap,
    VPRIdentifiedGap,
    VPRKeyAchievement,
    VPRMetadata,
    VPRMitigation,
    VPRMustHave,
    VPRNiceToHave,
    VPRObjection,
    VPRPrerequisite,
    VPRPriorityGap,
    VPRRelevantExperience,
    VPRRequirementBreakdown,
    VPRResponsibility,
    VPRStrength,
    VPRUniqueStrength,
)


@pytest.mark.unit
class TestVPRMetadata:
    def test_validates_required_fields(self) -> None:
        meta = VPRMetadata(
            report_date='2025-01-01',
            candidate_name='Jane Smith',
            target_role='Staff Engineer',
            target_company='SysAid',
            report_version='1.0',
            analysis_scope='full',
        )
        assert meta.candidate_name == 'Jane Smith'
        assert meta.target_company == 'SysAid'

    def test_camel_case_alias_report_date(self) -> None:
        meta = VPRMetadata(
            report_date='2025-01-01',
            candidate_name='Jane',
            target_role='Eng',
            target_company='Co',
            report_version='1.0',
            analysis_scope='full',
        )
        dumped = meta.model_dump(by_alias=True, mode='json')
        assert 'reportDate' in dumped
        assert 'report_date' not in dumped

    def test_extra_fields_ignored(self) -> None:
        """Old DynamoDB items may have unknown fields — they must not crash."""
        meta = VPRMetadata.model_validate(
            {
                'report_date': '2025-01-01',
                'candidate_name': 'Jane',
                'target_role': 'Eng',
                'target_company': 'Co',
                'report_version': '1.0',
                'analysis_scope': 'full',
                'unknown_legacy_field': 'ignored',
            }
        )
        assert meta.candidate_name == 'Jane'


@pytest.mark.unit
class TestVPRExecutiveSummary:
    def test_validates_fit_score_and_rationale(self) -> None:
        es = VPRExecutiveSummary(
            overall_fit_score=82,
            fit_rationale="Jane's background maps directly to SysAid's needs. She has proven expertise in cloud infrastructure and team leadership that aligns well with this role.",
            top_three_strengths=[
                VPRStrength(
                    strength='Cloud expertise',
                    evidence='$2M AWS migration',
                    relevance_to_role='Direct',
                ),
                VPRStrength(
                    strength='Team leadership',
                    evidence='Led 8-person team',
                    relevance_to_role='Direct',
                ),
                VPRStrength(
                    strength='Python proficiency',
                    evidence='5 years experience',
                    relevance_to_role='Direct',
                ),
            ],
            top_three_concerns=[
                VPRConcern(concern='No SaaS experience', severity='medium', mitigation='Scale proxy'),
                VPRConcern(concern='Limited DevOps', severity='low', mitigation='Training available'),
                VPRConcern(concern='New to company', severity='low', mitigation='Onboarding plan'),
            ],
            recommended_approach='apply_with_customization',
        )
        assert es.overall_fit_score == 82
        assert es.recommended_approach == 'apply_with_customization'

    def test_camel_case_alias_overall_fit_score(self) -> None:
        es = VPRExecutiveSummary(
            overall_fit_score=70,
            fit_rationale='This candidate presents a solid match for the role. They have relevant experience and can contribute effectively to the team immediately.',
            top_three_strengths=[
                VPRStrength(strength='S1', evidence='E1', relevance_to_role='R1'),
                VPRStrength(strength='S2', evidence='E2', relevance_to_role='R2'),
                VPRStrength(strength='S3', evidence='E3', relevance_to_role='R3'),
            ],
            top_three_concerns=[
                VPRConcern(concern='C1', severity='low', mitigation='M1'),
                VPRConcern(concern='C2', severity='low', mitigation='M2'),
                VPRConcern(concern='C3', severity='low', mitigation='M3'),
            ],
            recommended_approach='apply_after_preparation',
        )
        dumped = es.model_dump(by_alias=True, mode='json')
        assert 'overallFitScore' in dumped
        assert 'topThreeStrengths' in dumped
        assert 'topThreeConcerns' in dumped
        assert 'recommendedApproach' in dumped

    def test_recommended_approach_enum_values(self) -> None:
        valid_approaches = [
            'aggressive_apply',
            'apply_with_customization',
            'apply_after_preparation',
            'do_not_apply',
        ]
        for approach in valid_approaches:
            es = VPRExecutiveSummary(
                overall_fit_score=70,
                fit_rationale='This candidate presents a solid match for the role. They have relevant experience and can contribute effectively.',
                top_three_strengths=[
                    VPRStrength(strength='S1', evidence='E1', relevance_to_role='R1'),
                    VPRStrength(strength='S2', evidence='E2', relevance_to_role='R2'),
                    VPRStrength(strength='S3', evidence='E3', relevance_to_role='R3'),
                ],
                top_three_concerns=[
                    VPRConcern(concern='C1', severity='low', mitigation='M1'),
                    VPRConcern(concern='C2', severity='low', mitigation='M2'),
                    VPRConcern(concern='C3', severity='low', mitigation='M3'),
                ],
                recommended_approach=approach,  # type: ignore[arg-type]
            )
            assert es.recommended_approach == approach


@pytest.mark.unit
class TestVPRRoleAlignment:
    def test_responsibility_alignment_score_in_range(self) -> None:
        resp = VPRResponsibility(
            responsibility='Lead team',
            alignment_score=85,
            candidate_evidence=['Led 8 people'],
            evidence_quality='direct',
        )
        assert 0 <= resp.alignment_score <= 100

    def test_evidence_quality_enum_values(self) -> None:
        for quality in ['direct', 'analogous', 'transferable', 'weak']:
            resp = VPRResponsibility(
                responsibility='Task',
                alignment_score=75,
                candidate_evidence=['Proof'],
                evidence_quality=quality,  # type: ignore[arg-type]
            )
            assert resp.evidence_quality == quality

    def test_requirement_breakdown_camel_case(self) -> None:
        rb = VPRRequirementBreakdown(
            must_have=[
                VPRMustHave(
                    requirement='Python',
                    candidate_meets_requirement=True,
                    evidence='5 years',
                    strength_of_evidence='strong',
                )
            ],
            nice_to_have=[VPRNiceToHave(preference='ITIL', candidate_has_this=False, evidence='')],
            assumed_prerequisites=[
                VPRPrerequisite(
                    assumption='CS degree',
                    candidate_meets_this=True,
                    reasoning='MIT confirmed',
                )
            ],
        )
        dumped = rb.model_dump(by_alias=True, mode='json')
        assert 'mustHave' in dumped
        assert 'niceToHave' in dumped
        assert 'assumedPrerequisites' in dumped


@pytest.mark.unit
class TestVPRExperienceMapping:
    def test_relevant_experience_validates(self) -> None:
        exp = VPRRelevantExperience(
            role='Senior Engineer',
            organization='Acme Corp',
            duration='4 years',
            key_achievements=[VPRKeyAchievement(achievement='$2M migration', metric='$2M', impact='High')],
            relevance_to_target_role='Direct platform experience',
            relevance_score=85,
        )
        assert exp.relevance_score == 85
        dumped = exp.model_dump(by_alias=True, mode='json')
        assert 'keyAchievements' in dumped
        assert 'relevanceToTargetRole' in dumped

    def test_experience_gap_impact_enum(self) -> None:
        for impact in ['critical', 'significant', 'moderate', 'minimal']:
            gap = VPRExperienceGap(
                missing_experience='SaaS',
                impact_on_candidacy=impact,  # type: ignore[arg-type]
                compensating_factors=['AWS scale'],
                mitigation_strategy='Highlight cloud work',
            )
            assert gap.impact_on_candidacy == impact


@pytest.mark.unit
class TestVPREvidenceGaps:
    def test_gap_severity_enum_values(self) -> None:
        for severity in ['critical', 'high', 'medium', 'low']:
            gap = VPRIdentifiedGap(
                requirement='Experience X',
                current_evidence='Some evidence',
                gap_severity=severity,  # type: ignore[arg-type]
                suggested_evidence=['Case study'],
                can_be_created_quickly=True,
            )
            assert gap.gap_severity == severity

    def test_priority_gap_deadline_enum(self) -> None:
        for deadline in ['before_application', 'before_interview', 'nice_to_have']:
            pg = VPRPriorityGap(
                gap='Missing cert',
                priority=1,
                action_item='Get cert',
                deadline=deadline,  # type: ignore[arg-type]
            )
            assert pg.deadline == deadline


@pytest.mark.unit
class TestVPRDifferentiators:
    def test_rarity_enum_values(self) -> None:
        for rarity in ['very_rare', 'uncommon', 'somewhat_rare']:
            strength = VPRUniqueStrength(
                strength='AWS at scale',
                rarity=rarity,  # type: ignore[arg-type]
                relevance='Direct fit',
                proof='$2M project',
            )
            assert strength.rarity == rarity

    def test_positioning_statement_is_string(self) -> None:
        diff = VPRDifferentiators(
            unique_strengths=[
                VPRUniqueStrength(
                    strength='AWS scale',
                    rarity='uncommon',
                    relevance='Fits SysAid',
                    proof='$2M project',
                ),
                VPRUniqueStrength(
                    strength='Team leadership',
                    rarity='uncommon',
                    relevance='Fits role',
                    proof='Led 8 person team',
                ),
            ],
            competitive_advantages=[
                VPRCompetitiveAdvantage(
                    advantage='Cloud + leadership',
                    vs_typical_candidate='Most have one',
                ),
                VPRCompetitiveAdvantage(
                    advantage='Migration experience',
                    vs_typical_candidate='Rare combination',
                ),
            ],
            positioning_statement='Platform engineer with proven migration leadership and cloud infrastructure expertise at scale. Brings unique combination of hands-on technical depth and team leadership experience from managing large infrastructure transformations.',
        )
        assert isinstance(diff.positioning_statement, str)
        assert len(diff.positioning_statement) > 0


@pytest.mark.unit
class TestVPRConcernsAndMitigations:
    def test_objection_likelihood_enum(self) -> None:
        for likelihood in ['very_likely', 'likely', 'possible', 'unlikely']:
            obj = VPRObjection(
                objection='No SaaS exp',
                likelihood=likelihood,  # type: ignore[arg-type]
                mitigation=VPRMitigation(
                    strategy='provide_evidence',
                    messaging="Acme's cluster matches SaaS complexity.",
                ),
                where_to_address=['cover_letter'],
            )
            assert obj.likelihood == likelihood

    def test_mitigation_strategy_enum(self) -> None:
        for strategy in [
            'reframe',
            'acknowledge_and_address',
            'provide_evidence',
            'show_analogous_experience',
        ]:
            mit = VPRMitigation(strategy=strategy, messaging='Specific response here.')  # type: ignore[arg-type]
            assert mit.strategy == strategy


@pytest.mark.unit
class TestVPRFullModel:
    def test_full_vpr_model_dump_camel_case(self, minimal_vpr: VPR) -> None:
        dumped = minimal_vpr.model_dump(by_alias=True, mode='json')
        # Top-level fields
        assert 'applicationId' in dumped
        assert 'executiveSummary' in dumped
        assert 'roleAlignment' in dumped
        assert 'experienceMapping' in dumped
        assert 'skillsAnalysis' in dumped
        assert 'evidenceGaps' in dumped
        assert 'differentiators' in dumped
        assert 'concernsAndMitigations' in dumped
        assert 'valueProposition' in dumped
        assert 'applicationStrategy' in dumped
        # Verify snake_case is gone
        assert 'application_id' not in dumped
        assert 'executive_summary' not in dumped

    def test_full_vpr_model_dump_snake_case_for_dynamo(self, minimal_vpr: VPR) -> None:
        dumped = minimal_vpr.model_dump(mode='json')
        assert 'application_id' in dumped
        assert 'executive_summary' in dumped
        assert 'applicationId' not in dumped

    def test_vpr_model_validate_with_extra_fields_ignored(self, minimal_vpr: VPR) -> None:
        """Extra fields in input data must be ignored without crashing."""
        dumped = minimal_vpr.model_dump(mode='python')
        dumped['legacy_flat_field'] = 'should be ignored'
        dumped['unknown_field'] = 'also ignored'

        # Should not raise — extra='ignore' handles unknown fields
        vpr = VPR.model_validate(dumped)
        assert vpr.application_id == 'app-001'
        # Should still have all the expected sections
        assert vpr.metadata is not None
        assert vpr.executive_summary is not None

    def test_vpr_json_is_parseable(self, minimal_vpr: VPR) -> None:
        """Serialized VPR must be valid JSON parseable by JSON.loads."""
        response_dict = minimal_vpr.model_dump(by_alias=True, mode='json')
        json_str = json.dumps(response_dict)
        parsed = json.loads(json_str)
        assert parsed['applicationId'] == 'app-001'
