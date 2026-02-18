"""Unit tests for the VPR 6-stage pipeline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.vpr_generator import (
    DraftGapStrategy,
    DraftProposition,
    EvidenceMatch,
    VPRData,
    VPRSixStagePipeline,
    generate_vpr,
)
from careervp.models.cv import ContactInfo, UserCV, WorkExperience
from careervp.models.job import JobPosting
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import VPR, VPRRequest


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


def test_stage_4_self_correct_improves_draft(
    sample_request: VPRRequest,
    sample_user_cv: UserCV,
) -> None:
    pipeline = _build_pipeline(sample_request, sample_user_cv)

    draft = DraftProposition(
        executive_summary='I leverage robust synergy to streamline outcomes across teams.',
        evidence_matrix=[
            EvidenceMatch(
                requirement='Product strategy leadership',
                evidence='Led product strategy for a B2B platform with measurable growth.',
                alignment_score='STRONG',
                impact_potential='Can set a clear strategic direction quickly.',
            )
        ],
        differentiators=['Leverages robust methods to facilitate delivery.'],
        gap_strategies=[
            DraftGapStrategy(
                gap='No fintech domain experience',
                mitigation_approach='Use adjacent product leadership examples.',
                transferable_skills=['Product strategy'],
            )
        ],
        cultural_fit='Collaborative and accountable style.',
        talking_points=['Leverage robust prioritization patterns.'],
        keywords=['Product Strategy'],
    )

    corrected = pipeline._self_correct(draft)

    assert corrected.executive_summary != draft.executive_summary
    assert 'leverage' not in corrected.executive_summary.lower()
    assert corrected.corrections_applied


def test_stage_6_rejects_ai_patterns(
    sample_request: VPRRequest,
    sample_user_cv: UserCV,
) -> None:
    pipeline = _build_pipeline(sample_request, sample_user_cv)

    vpr = VPR(
        application_id=sample_request.application_id,
        user_id=sample_request.user_id,
        executive_summary='I leverage robust synergy and streamline best practices at scale.',
        evidence_matrix=[],
        differentiators=['Game-changer paradigm shift for execution.'],
        gap_strategies=[],
        cultural_fit='Industry-leading mindset.',
        talking_points=['Utilize robust frameworks.'],
        keywords=['Strategy'],
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
