"""Unit tests for the VPR 6-stage pipeline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.vpr_generator import (
    EvidenceList,
    Phase2Draft,
    VPRData,
    VPRSixStagePipeline,
    generate_vpr,
)
from careervp.models.cv import ContactInfo, UserCV, WorkExperience
from careervp.models.job import JobPosting
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import (
    VPR,
    VPRApplicationStrategy,
    VPRConcern,
    VPRConcernsAndMitigations,
    VPRDifferentiators,
    VPREvidenceGaps,
    VPRExecutiveSummary,
    VPRExperienceMapping,
    VPRIdentifiedGap,
    VPRKeyAchievement,
    VPRKeywordGroup,
    VPRMetadata,
    VPRMitigation,
    VPRObjection,
    VPRPrimaryValue,
    VPRPriorityGap,
    VPRRelevantExperience,
    VPRRequest,
    VPRRequirementBreakdown,
    VPRResponsibility,
    VPRRoleAlignment,
    VPRSecondaryValue,
    VPRSkillsAnalysis,
    VPRStrength,
    VPRUniqueStrength,
    VPRValueProposition,
)


@pytest.fixture
def sample_user_cv() -> UserCV:
    return UserCV(
        user_id='user-123',
        full_name='Alex Rivers',
        language='en',
        contact_info=ContactInfo(email='alex@example.com'),
        experience=[
            WorkExperience(
                company='Apex Labs',
                role='Product Lead',
                dates='2019 – Present',
                achievements=[
                    'Led product strategy for a B2B platform with measurable growth.',
                    'Managed cross-functional collaboration across engineering, design, and sales.',
                ],
                technologies=['Python', 'SQL'],
            )
        ],
        education=[],
        certifications=[],
        skills=['Product Strategy', 'Cross-functional Leadership', 'Roadmapping'],
        top_achievements=['Improved activation by 28% within two quarters.'],
        languages=[],
        is_parsed=True,
    )


@pytest.fixture
def sample_request() -> VPRRequest:
    posting = JobPosting(
        company_name='Bright Future',
        role_title='Director of Product',
        description='Lead product strategy and execution.',
        responsibilities=['Guide product roadmap execution'],
        requirements=['Product strategy leadership', 'Cross-functional collaboration'],
        nice_to_have=['Analytics depth'],
        language='en',
    )
    return VPRRequest(
        application_id='app-789',
        user_id='user-123',
        job_posting=posting,
        gap_responses=[],
    )


def _stage_3_payload() -> str:
    return json.dumps(
        {
            'executive_summary': (
                'Alex combines product strategy leadership with strong delivery discipline and cross-functional execution across complex initiatives.'
            ),
            'evidence_matrix': [
                {
                    'requirement': 'Product strategy leadership',
                    'evidence': 'Led product strategy for a B2B platform with measurable growth.',
                    'alignment_score': 'STRONG',
                    'impact_potential': 'Can align roadmap decisions with business outcomes.',
                },
                {
                    'requirement': 'Cross-functional collaboration',
                    'evidence': 'Managed cross-functional collaboration across engineering, design, and sales.',
                    'alignment_score': 'STRONG',
                    'impact_potential': 'Can drive alignment across teams to ship faster.',
                },
            ],
            'differentiators': ['Connects strategy with execution cadence.'],
            'gap_strategies': [],
            'cultural_fit': 'Operates with transparent communication and ownership.',
            'talking_points': ['Explain how roadmap priorities were translated into measurable outcomes.'],
            'keywords': ['Product Strategy', 'Cross-functional Collaboration', 'Roadmapping'],
        }
    )


def _stage_4_payload() -> str:
    return json.dumps(
        {
            'executive_summary': (
                'Alex has led product strategy in operating environments that required strong tradeoff '
                'decisions, clear communication, and rapid execution.'
            ),
            'differentiators': ['Balances strategy, speed, and stakeholder alignment.'],
            'talking_points': ['Share one launch where cross-team planning improved delivery confidence.'],
            'corrections_applied': ['Tightened wording for natural tone'],
        }
    )


def _build_pipeline(sample_request: VPRRequest, sample_user_cv: UserCV) -> VPRSixStagePipeline:
    llm_client = MagicMock()
    llm_client.invoke.return_value = Result(
        success=False,
        error='Not used in this test',
        code=ResultCode.LLM_API_ERROR,
    )
    return VPRSixStagePipeline(sample_request, sample_user_cv, llm_client=llm_client)


def test_stage_1_analyze_input_returns_analysis_result(
    sample_request: VPRRequest,
    sample_user_cv: UserCV,
) -> None:
    pipeline = _build_pipeline(sample_request, sample_user_cv)

    analysis = pipeline._analyze_input(sample_user_cv, sample_request.job_posting)

    assert analysis.key_skills
    assert 'Product Strategy' in analysis.key_skills
    assert analysis.experience_level in {'early', 'mid', 'advanced', 'senior'}
    assert 'Product strategy leadership' in analysis.job_requirements


def test_stage_2_extract_evidence_maps_correctly(
    sample_request: VPRRequest,
    sample_user_cv: UserCV,
) -> None:
    pipeline = _build_pipeline(sample_request, sample_user_cv)
    analysis = pipeline._analyze_input(sample_user_cv, sample_request.job_posting)

    evidence = pipeline._extract_evidence(analysis)

    assert len(evidence.matches) == len(analysis.job_requirements)
    assert any('product strategy' in item.evidence.lower() for item in evidence.matches)
    assert any('cross-functional' in item.evidence.lower() for item in evidence.matches)


def test_stage_4_self_correct_falls_back_to_rule_based_when_llm_fails(
    sample_request: VPRRequest,
    sample_user_cv: UserCV,
) -> None:
    # LLM is mocked to always fail (from _build_pipeline), so fallback must run.
    pipeline = _build_pipeline(sample_request, sample_user_cv)
    evidence = EvidenceList(matches=[], uncovered_requirements=[], key_skills=[], experience_level='mid')
    raw_payload = {
        'executive_summary': {
            'fit_rationale': 'I leverage robust synergy to streamline outcomes across teams.',
        },
        'differentiators': {
            'positioning_statement': 'Utilize robust methods to leverage game-changing paradigm shifts.',
        },
        'value_proposition': {
            'elevator_pitch': 'Leverage robust synergy to streamline outcomes.',
            'primary_value': {
                'statement': 'Facilitate best practices to utilize robust frameworks.',
            },
        },
    }
    draft = Phase2Draft(raw_payload=raw_payload, evidence_context=evidence)

    corrected = pipeline._self_correct(draft)

    fit_rationale = corrected.raw_payload.get('executive_summary', {}).get('fit_rationale', '')
    positioning = corrected.raw_payload.get('differentiators', {}).get('positioning_statement', '')
    elevator_pitch = corrected.raw_payload.get('value_proposition', {}).get('elevator_pitch', '')

    assert 'leverage' not in fit_rationale.lower()
    assert 'robust' not in fit_rationale.lower()
    assert 'streamline' not in fit_rationale.lower()
    assert 'leverage' not in positioning.lower()
    assert 'leverage' not in elevator_pitch.lower()
    assert corrected.validation_notes == ['Fallback: banned terms removed from text fields']


def test_stage_6_rejects_ai_patterns(
    sample_request: VPRRequest,
    sample_user_cv: UserCV,
) -> None:
    pipeline = _build_pipeline(sample_request, sample_user_cv)

    vpr = VPR(
        application_id=sample_request.application_id,
        user_id=sample_request.user_id,
        metadata=VPRMetadata(
            report_date='2024-01-15',
            candidate_name='Alex Rivers',
            target_role='Director of Product',
            target_company='Bright Future',
        ),
        executive_summary=VPRExecutiveSummary(
            overall_fit_score=60,
            fit_rationale=(
                'I leverage robust synergy and streamline best practices at scale across all paradigms. '
                'Game-changer mindset with industry-leading frameworks for execution excellence.'
            ),
            top_three_strengths=[
                VPRStrength(strength='Robust synergy leveraging', evidence='Streamlined best practices', relevance_to_role='Leadership'),
                VPRStrength(strength='Paradigm shift expertise', evidence='Game-changer execution', relevance_to_role='Innovation'),
                VPRStrength(strength='Industry-leading mindset', evidence='Utilized robust frameworks', relevance_to_role='Strategy'),
            ],
            top_three_concerns=[
                VPRConcern(concern='Overuse of AI language patterns', severity='high', mitigation='Reframe with specifics'),
                VPRConcern(concern='Lack of quantified evidence', severity='medium', mitigation='Add metrics'),
                VPRConcern(concern='Generic positioning', severity='medium', mitigation='Differentiate clearly'),
            ],
            recommended_approach='apply_after_preparation',
        ),
        role_alignment=VPRRoleAlignment(
            core_responsibilities=[
                VPRResponsibility(
                    responsibility='Lead product strategy',
                    alignment_score=60,
                    candidate_evidence=['Utilize robust frameworks'],
                    evidence_quality='weak',
                )
            ],
            requirement_breakdown=VPRRequirementBreakdown(must_have=[], nice_to_have=[], assumed_prerequisites=[]),
        ),
        experience_mapping=VPRExperienceMapping(
            relevant_experiences=[
                VPRRelevantExperience(
                    role='Product Lead',
                    organization='Apex Labs',
                    duration='3 years',
                    key_achievements=[
                        VPRKeyAchievement(achievement='Game-changer paradigm shift', metric='Leverage synergy', impact='Streamlined outcomes')
                    ],
                    relevance_to_target_role='Adjacent product leadership',
                )
            ],
            experience_gaps=[],
        ),
        skills_analysis=VPRSkillsAnalysis(technical_skills=[], soft_skills=[], tool_proficiency=[]),
        evidence_gaps=VPREvidenceGaps(
            identified_gaps=[
                VPRIdentifiedGap(
                    requirement='Quantified outcomes',
                    current_evidence='Generic statements only',
                    gap_severity='high',
                    suggested_evidence=['Specific metrics'],
                )
            ],
            priority_gaps_to_address=[
                VPRPriorityGap(gap='Quantified outcomes', priority=1, action_item='Add metrics', deadline='before_application')
            ],
        ),
        differentiators=VPRDifferentiators(
            unique_strengths=[
                VPRUniqueStrength(
                    strength='Game-changer paradigm shift for execution',
                    rarity='uncommon',
                    relevance='Strategic leadership',
                    proof='Industry-leading mindset demonstrated',
                )
            ],
            competitive_advantages=[],
            positioning_statement=(
                'I leverage robust synergy and streamline best practices to deliver game-changer paradigm shifts '
                'across all industry-leading frameworks and utilize innovative execution methodologies.'
            ),
        ),
        concerns_and_mitigations=VPRConcernsAndMitigations(
            likely_objections=[
                VPRObjection(
                    objection='AI-generated language patterns detected',
                    likelihood='very_likely',
                    mitigation=VPRMitigation(
                        strategy='reframe',
                        messaging='Replace with specific, quantified examples.',
                    ),
                    where_to_address=['cv', 'cover_letter'],
                )
            ],
            preemptive_responses=[],
        ),
        value_proposition=VPRValueProposition(
            primary_value=VPRPrimaryValue(
                statement='Utilize robust frameworks',
                evidence='Industry-leading mindset',
                outcome_for_company='Streamlined best practices',
            ),
            secondary_values=[
                VPRSecondaryValue(value='Synergy leveraging', proof='Game-changer execution'),
                VPRSecondaryValue(value='Paradigm shift', proof='Robust frameworks utilized'),
            ],
            quantified_impact=[],
            elevator_pitch=(
                'I leverage robust synergy and streamline best practices at scale to deliver game-changer '
                'paradigm shifts using industry-leading frameworks and innovative execution methodologies.'
            ),
        ),
        application_strategy=VPRApplicationStrategy(
            messaging_approach='Utilize robust frameworks to leverage synergy.',
            ats_keywords=VPRKeywordGroup(primary=['Strategy'], secondary=['Leadership']),
            cv_lead_differentiator='Game-changer paradigm shift for execution.',
            sections_to_compress=[],
        ),
        language='en',
        version=1,
        created_at=datetime.now(timezone.utc),
        word_count=0,
    )

    final_data = pipeline._final_meta_evaluation(VPRData(vpr=vpr))

    assert final_data.passed_gate is False
    assert final_data.anti_ai_score < 9.0
    assert final_data.anti_ai_issues


@patch('careervp.logic.vpr_generator.LLMClient')
def test_full_pipeline_produces_valid_vpr(
    mock_llm_client_cls: MagicMock,
    sample_request: VPRRequest,
    sample_user_cv: UserCV,
) -> None:
    mock_llm_instance = MagicMock()
    mock_llm_instance.invoke.side_effect = [
        Result(
            success=True,
            data={
                'text': _stage_3_payload(),
                'input_tokens': 600,
                'output_tokens': 400,
                'cost': 0.01,
                'model': 'claude-sonnet-4-5',
            },
            code=ResultCode.SUCCESS,
        ),
        Result(
            success=True,
            data={
                'text': _stage_4_payload(),
                'input_tokens': 550,
                'output_tokens': 350,
                'cost': 0.009,
                'model': 'claude-sonnet-4-5',
            },
            code=ResultCode.SUCCESS,
        ),
    ]
    mock_llm_client_cls.return_value = mock_llm_instance

    mock_dal = MagicMock()
    mock_dal.save_vpr.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)

    result = generate_vpr(sample_request, sample_user_cv, mock_dal)

    assert result.success is True
    assert result.data is not None
    assert result.data.vpr is not None
    assert result.data.vpr.application_id == sample_request.application_id
    assert result.data.vpr.user_id == sample_request.user_id
    assert result.data.vpr.word_count > 0
    assert result.data.token_usage is not None
    assert result.data.token_usage.input_tokens == 1150
    assert result.data.token_usage.output_tokens == 750
    mock_dal.save_vpr.assert_called_once()
