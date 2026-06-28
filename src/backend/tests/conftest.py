"""Shared pytest configuration for CareerVP backend tests."""

import json
import os
from typing import Any
from unittest.mock import MagicMock

import pytest

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.models.cv import Education, Skill, SkillLevel, UserCV, WorkExperience
from careervp.models.job import GapResponse, JobPosting
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import (
    VPR,
    VPRApplicationStrategy,
    VPRCompetitiveAdvantage,
    VPRConcern,
    VPRConcernsAndMitigations,
    VPRDifferentiators,
    VPREvidenceGaps,
    VPRExecutiveSummary,
    VPRExperienceGap,
    VPRExperienceMapping,
    VPRIdentifiedGap,
    VPRKeyAchievement,
    VPRKeywordGroup,
    VPRMetadata,
    VPRMitigation,
    VPRMustHave,
    VPRNiceToHave,
    VPRObjection,
    VPRPreemptiveResponse,
    VPRPrerequisite,
    VPRPrimaryValue,
    VPRPriorityGap,
    VPRQuantifiedImpact,
    VPRRelevantExperience,
    VPRRequest,
    VPRRequirementBreakdown,
    VPRResponsibility,
    VPRRoleAlignment,
    VPRSecondaryValue,
    VPRSkillsAnalysis,
    VPRSoftSkill,
    VPRStrength,
    VPRTechnicalSkill,
    VPRToolProficiency,
    VPRUniqueStrength,
    VPRValueProposition,
)

# Ensure aws-lambda-env-modeler re-reads environment variables between tests.
os.environ['LAMBDA_ENV_MODELER_DISABLE_CACHE'] = 'true'

# Baseline AWS/moto configuration so tests never reach real AWS.
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['AWS_REGION'] = 'us-east-1'

# Default application env vars used across handlers.
os.environ['POWERTOOLS_SERVICE_NAME'] = 'careervp-test'
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
os.environ['TABLE_NAME'] = 'test-users-table'
os.environ['CV_BUCKET_NAME'] = 'test-cv-bucket'
os.environ['IDEMPOTENCY_TABLE_NAME'] = 'test-idempotency-table'


@pytest.fixture(autouse=True)
def reset_dynamo_dal_singleton():
    """Ensure each test gets a fresh DAL instance with its requested table."""
    DynamoDalHandler.reset_instance()
    yield
    DynamoDalHandler.reset_instance()


@pytest.fixture(autouse=True)
def mock_company_research_load(mocker):
    """Mock company research loading to prevent AWS calls in tests."""
    mocker.patch(
        'careervp.handlers.artifact_dependency_utils.load_confident_company_research_artifact',
        return_value=None,
    )


@pytest.fixture(autouse=True)
def mock_artifact_dependency_resolver(mocker):
    """Bypass upstream VPR/CR dependency checks in unit tests.

    Handlers call resolve_handler_dependencies() before doing any real work.
    Without a valid VPR in DynamoDB, the resolver returns 409 and the handler
    exits early — breaking every test that doesn't set up the full artifact
    chain. Patching the inner resolve_dependencies() to return 'ready' lets
    each test focus on its own behaviour instead of upstream DAL setup.
    """
    from careervp.logic.artifact_dependency_resolver import DependencyResolution

    mocker.patch(
        'careervp.handlers.artifact_dependency_utils.resolve_dependencies',
        return_value=DependencyResolution(status='ready'),
    )


@pytest.fixture(scope='session', autouse=True)
def ensure_lambda_build_dir():
    """Create placeholder lambda asset directory expected by CDK tests."""
    from pathlib import Path

    backend_root = Path(__file__).resolve().parent.parent
    lambdas_dir = backend_root / '.build' / 'lambdas'
    lambdas_dir.mkdir(parents=True, exist_ok=True)
    (lambdas_dir / '.placeholder').touch()


# ---------------------------------------------------------------------------
# VPR model fixtures — visible to all test tiers (unit, integration, e2e)
# ---------------------------------------------------------------------------


def mock_llm_result(payload: dict[str, Any]) -> Result[dict[str, Any]]:
    """Wrap a dict payload as a successful LLM Result."""
    return Result(
        success=True,
        data={
            'text': json.dumps(payload),
            'input_tokens': 100,
            'output_tokens': 200,
            'cost': 0.003,
            'model': 'claude-sonnet-4-6',
        },
        code=ResultCode.SUCCESS,
    )


def mock_llm_failure(error: str = 'LLM timeout') -> Result[None]:
    """Return a failed LLM Result."""
    return Result(success=False, data=None, code=ResultCode.LLM_TIMEOUT, error=error)


@pytest.fixture
def minimal_user_cv() -> UserCV:
    """UserCV with 2 experiences, education, skills — sufficient for all VPR tests."""
    return UserCV(
        user_id='user-123',
        full_name='Jane Smith',
        email='jane@example.com',
        experience=[
            WorkExperience(
                company='Acme Corp',
                role='Senior Engineer',
                start_date='2020-01',
                end_date='2023-12',
                achievements=[
                    'Led team of 8 engineers',
                    'Delivered $2M AWS migration on time',
                ],
            ),
            WorkExperience(
                company='StartupCo',
                role='Engineer',
                start_date='2018-01',
                end_date='2020-01',
                achievements=['Built core API from scratch'],
            ),
        ],
        education=[Education(institution='MIT', degree='B.Sc. Computer Science', graduation_date='2018')],
        skills=[
            Skill(name='Python', level=SkillLevel.EXPERT),
            Skill(name='AWS', level=SkillLevel.ADVANCED),
        ],
        top_achievements=['Delivered $2M AWS migration on time'],
    )


@pytest.fixture
def minimal_vpr_request() -> VPRRequest:
    """VPRRequest with job_posting and gap_responses for SysAid Staff Engineer."""
    return VPRRequest(
        application_id='app-001',
        user_id='user-123',
        job_posting=JobPosting(
            company_name='SysAid',
            role_title='Staff Engineer',
            description='Lead platform engineering team for enterprise SaaS.',
            requirements=['Python', 'AWS', 'Team leadership'],
            language='en',
        ),
        gap_responses=[
            GapResponse(
                question_id='q1',
                question='Describe your leadership experience.',
                answer='Led 8 engineers at Acme Corp for 3 years.',
            ),
        ],
    )


@pytest.fixture
def minimal_vpr() -> VPR:
    """Valid 10-section VPR with all required fields populated."""
    return VPR(
        application_id='app-001',
        user_id='user-123',
        version=1,
        language='en',
        word_count=350,
        metadata=VPRMetadata(
            report_date='2025-01-01',
            candidate_name='Jane Smith',
            target_role='Staff Engineer',
            target_company='SysAid',
            report_version='1.0',
            analysis_scope='full',
        ),
        executive_summary=VPRExecutiveSummary(
            overall_fit_score=82,
            fit_rationale=(
                "Jane's 5 years at Acme Corp maps directly to SysAid's platform engineering needs. "
                'Her experience leading large-scale AWS infrastructure migrations demonstrates the '
                'technical depth and team leadership required for this Staff Engineer role.'
            ),
            top_three_strengths=[
                VPRStrength(
                    strength='Cloud infrastructure expertise',
                    evidence='Led $2M AWS migration at Acme Corp',
                    relevance_to_role='Direct match for platform engineering scope',
                ),
                VPRStrength(
                    strength='Team leadership',
                    evidence='Led 8-person team at Acme',
                    relevance_to_role="Matches SysAid's scale",
                ),
                VPRStrength(
                    strength='Python expertise',
                    evidence='5 years production experience',
                    relevance_to_role='Core requirement for role',
                ),
            ],
            top_three_concerns=[
                VPRConcern(
                    concern='No enterprise SaaS background',
                    severity='medium',
                    mitigation="Acme's scale is comparable to enterprise SaaS complexity",
                ),
                VPRConcern(
                    concern='Limited ITIL certification',
                    severity='low',
                    mitigation='Can pursue certification during onboarding',
                ),
                VPRConcern(
                    concern='Different tech stack experience',
                    severity='low',
                    mitigation='AWS fundamentals transfer across platforms',
                ),
            ],
            recommended_approach='apply_with_customization',
        ),
        role_alignment=VPRRoleAlignment(
            core_responsibilities=[
                VPRResponsibility(
                    responsibility='Lead platform engineering team',
                    alignment_score=85,
                    candidate_evidence=['Led 8-person team at Acme for 3 years'],
                    evidence_quality='direct',
                )
            ],
            requirement_breakdown=VPRRequirementBreakdown(
                must_have=[
                    VPRMustHave(
                        requirement='Python expertise',
                        candidate_meets_requirement=True,
                        evidence='Expert level, 5 years in production',
                        strength_of_evidence='strong',
                    )
                ],
                nice_to_have=[
                    VPRNiceToHave(
                        preference='ITIL certification',
                        candidate_has_this=False,
                        evidence='',
                    )
                ],
                assumed_prerequisites=[
                    VPRPrerequisite(
                        assumption='B.Sc. Computer Science or equivalent',
                        candidate_meets_this=True,
                        reasoning='MIT CS degree confirmed in CV',
                    )
                ],
            ),
        ),
        experience_mapping=VPRExperienceMapping(
            relevant_experiences=[
                VPRRelevantExperience(
                    role='Senior Engineer',
                    organization='Acme Corp',
                    duration='4 years',
                    key_achievements=[
                        VPRKeyAchievement(
                            achievement='Delivered $2M AWS migration on time',
                            metric='$2M budget, zero downtime',
                            impact='High — platform stability improved 40%',
                        )
                    ],
                    relevance_to_target_role='Direct platform engineering experience at scale',
                    relevance_score=85,
                )
            ],
            experience_gaps=[
                VPRExperienceGap(
                    missing_experience='Enterprise SaaS product background',
                    impact_on_candidacy='moderate',
                    compensating_factors=['Large-scale AWS work at Acme'],
                    mitigation_strategy='Highlight infrastructure scale as proxy for SaaS complexity',
                )
            ],
        ),
        skills_analysis=VPRSkillsAnalysis(
            technical_skills=[
                VPRTechnicalSkill(
                    skill='Python',
                    required_level='expert',
                    candidate_level='expert',
                    evidence='5 years daily production use',
                    gap=False,
                )
            ],
            soft_skills=[
                VPRSoftSkill(
                    skill='Team leadership',
                    candidate_demonstrates=True,
                    evidence='Led 8-person engineering team at Acme',
                    strength_level='strong',
                )
            ],
            tool_proficiency=[
                VPRToolProficiency(
                    tool='AWS',
                    required_for_role=True,
                    candidate_proficiency='expert',
                    evidence='Led $2M AWS migration project',
                    needs_upskilling=False,
                )
            ],
        ),
        evidence_gaps=VPREvidenceGaps(
            identified_gaps=[
                VPRIdentifiedGap(
                    requirement='Enterprise SaaS experience',
                    current_evidence='Startup and mid-market background only',
                    gap_severity='medium',
                    suggested_evidence=['Case study highlighting Acme scale'],
                    can_be_created_quickly=True,
                )
            ],
            priority_gaps_to_address=[
                VPRPriorityGap(
                    gap='Enterprise SaaS case study',
                    priority=1,
                    action_item='Write 1-page case study before applying',
                    deadline='before_application',
                )
            ],
        ),
        differentiators=VPRDifferentiators(
            unique_strengths=[
                VPRUniqueStrength(
                    strength='AWS migration at $2M scale with zero downtime',
                    rarity='uncommon',
                    relevance=(
                        'Direct fit for SysAid infrastructure scope. Demonstrates ability to '
                        'operate at commercial scale while maintaining reliability standards.'
                    ),
                    proof='$2M project delivered on schedule at Acme Corp',
                )
            ],
            competitive_advantages=[
                VPRCompetitiveAdvantage(
                    advantage='Full-stack cloud expertise combined with team leadership',
                    vs_typical_candidate='Most candidates have one, not both',
                )
            ],
            positioning_statement=(
                'Platform engineer with proven ability to lead large infrastructure '
                'migrations at commercial scale. Combines deep technical expertise in cloud '
                'infrastructure with demonstrated team leadership on high-stakes projects.'
            ),
        ),
        concerns_and_mitigations=VPRConcernsAndMitigations(
            likely_objections=[
                VPRObjection(
                    objection='No direct enterprise SaaS product background',
                    likelihood='likely',
                    mitigation=VPRMitigation(
                        strategy='provide_evidence',
                        messaging=(
                            "Acme's 500-node cluster matches enterprise SaaS complexity. "
                            'The $2M migration scope is evidence of operating at that scale. '
                            'Infrastructure reliability at Acme Corp was mission-critical.'
                        ),
                    ),
                    where_to_address=['cover_letter', 'interview'],
                )
            ],
            preemptive_responses=[
                VPRPreemptiveResponse(
                    concern="Team size smaller than SysAid's engineering org",
                    preemptive_action='Open CV with concrete team leadership metrics',
                )
            ],
        ),
        value_proposition=VPRValueProposition(
            primary_value=VPRPrimaryValue(
                statement="Reduce infrastructure risk while scaling SysAid's platform.",
                evidence='Delivered $2M migration with zero downtime at Acme Corp',
                outcome_for_company='Faster feature delivery on a reliable, scalable platform',
            ),
            secondary_values=[
                VPRSecondaryValue(
                    value='Python depth reduces team onboarding friction',
                    proof='Expert-level Python across 5 production systems at Acme',
                ),
                VPRSecondaryValue(
                    value='Proven ability to manage large-scale infrastructure projects',
                    proof='Led $2M migration with zero downtime',
                ),
            ],
            quantified_impact=[
                VPRQuantifiedImpact(
                    metric='Infrastructure delivery time',
                    expected_range='20-30% faster',
                    basis_for_projection='Based on Acme migration velocity benchmark',
                )
            ],
            elevator_pitch=(
                "Platform engineer with a $2M AWS migration track record, ready to scale SysAid's infrastructure without disrupting product delivery."
            ),
        ),
        application_strategy=VPRApplicationStrategy(
            messaging_approach=(
                "Lead with infrastructure migration outcomes; connect AWS expertise to SysAid's current growth phase and platform reliability goals."
            ),
            ats_keywords=VPRKeywordGroup(
                primary=['platform engineering', 'AWS', 'Python', 'cloud infrastructure'],
                secondary=['cloud migration', 'infrastructure', 'team leadership', 'SRE'],
            ),
            cv_lead_differentiator='$2M AWS migration with zero downtime',
            sections_to_compress=['Education', 'Early-career roles at StartupCo'],
        ),
    )


@pytest.fixture
def llm_phase2_response() -> dict[str, Any]:
    """Valid 10-section VPR as raw JSON dict (snake_case keys)."""
    return {
        'metadata': {
            'report_date': '2025-01-01',
            'candidate_name': 'Jane Smith',
            'target_role': 'Staff Engineer',
            'target_company': 'SysAid',
            'report_version': '1.0',
            'analysis_scope': 'full',
        },
        'executive_summary': {
            'overall_fit_score': 82,
            'fit_rationale': (
                "Jane's 5 years at Acme Corp maps directly to SysAid's platform engineering needs. "
                'Her experience leading large-scale AWS infrastructure migrations demonstrates the '
                'technical depth and team leadership required for this Staff Engineer role.'
            ),
            'top_three_strengths': [
                {
                    'strength': 'Cloud infrastructure expertise',
                    'evidence': 'Led $2M AWS migration at Acme Corp',
                    'relevance_to_role': 'Direct match for platform engineering scope',
                }
            ]
            * 3,
            'top_three_concerns': [
                {
                    'concern': 'No enterprise SaaS background',
                    'severity': 'medium',
                    'mitigation': "Acme's scale is comparable to enterprise complexity",
                }
            ]
            * 3,
            'recommended_approach': 'apply_with_customization',
        },
        'role_alignment': {
            'core_responsibilities': [
                {
                    'responsibility': 'Lead platform engineering team',
                    'alignment_score': 85,
                    'candidate_evidence': ['Led 8-person team at Acme for 3 years'],
                    'evidence_quality': 'direct',
                }
            ],
            'requirement_breakdown': {
                'must_have': [
                    {
                        'requirement': 'Python expertise',
                        'candidate_meets_requirement': True,
                        'evidence': 'Expert level, 5 years',
                        'strength_of_evidence': 'strong',
                    }
                ],
                'nice_to_have': [{'preference': 'ITIL certification', 'candidate_has_this': False, 'evidence': ''}],
                'assumed_prerequisites': [
                    {
                        'assumption': 'B.Sc. Computer Science',
                        'candidate_meets_this': True,
                        'reasoning': 'MIT CS degree confirmed',
                    }
                ],
            },
        },
        'experience_mapping': {
            'relevant_experiences': [
                {
                    'role': 'Senior Engineer',
                    'organization': 'Acme Corp',
                    'duration': '4 years',
                    'key_achievements': [
                        {
                            'achievement': 'Delivered $2M project on time',
                            'metric': '$2M budget',
                            'impact': 'High',
                        }
                    ],
                    'relevance_to_target_role': 'Direct platform engineering experience',
                    'relevance_score': 85,
                }
            ],
            'experience_gaps': [
                {
                    'missing_experience': 'Enterprise SaaS background',
                    'impact_on_candidacy': 'moderate',
                    'compensating_factors': ['Large-scale AWS work'],
                    'mitigation_strategy': 'Highlight cloud scale achievements',
                }
            ],
        },
        'skills_analysis': {
            'technical_skills': [
                {
                    'skill': 'Python',
                    'required_level': 'expert',
                    'candidate_level': 'expert',
                    'evidence': '5 years daily use',
                    'gap': False,
                }
            ],
            'soft_skills': [
                {
                    'skill': 'Leadership',
                    'candidate_demonstrates': True,
                    'evidence': 'Led 8-person team',
                    'strength_level': 'strong',
                }
            ],
            'tool_proficiency': [
                {
                    'tool': 'AWS',
                    'required_for_role': True,
                    'candidate_proficiency': 'expert',
                    'evidence': 'AWS migration project',
                    'needs_upskilling': False,
                }
            ],
        },
        'evidence_gaps': {
            'identified_gaps': [
                {
                    'requirement': 'Enterprise SaaS experience',
                    'current_evidence': 'Startup + mid-market only',
                    'gap_severity': 'medium',
                    'suggested_evidence': ['Case study from Acme scale'],
                    'can_be_created_quickly': True,
                }
            ],
            'priority_gaps_to_address': [
                {
                    'gap': 'Enterprise SaaS case study',
                    'priority': 1,
                    'action_item': 'Write 1-page case study',
                    'deadline': 'before_application',
                }
            ],
        },
        'differentiators': {
            'unique_strengths': [
                {
                    'strength': 'AWS migration at $2M scale',
                    'rarity': 'uncommon',
                    'relevance': (
                        'Direct fit for SysAid infra scope. Demonstrates ability to operate '
                        'at commercial scale while maintaining reliability standards required.'
                    ),
                    'proof': '$2M project delivered on time at Acme',
                }
            ],
            'competitive_advantages': [
                {
                    'advantage': 'Full-stack cloud + leadership combo',
                    'vs_typical_candidate': 'Most candidates have one, not both',
                }
            ],
            'positioning_statement': ('Platform engineer with proven ability to lead large infrastructure migrations at commercial scale.'),
        },
        'concerns_and_mitigations': {
            'likely_objections': [
                {
                    'objection': 'No enterprise SaaS background',
                    'likelihood': 'likely',
                    'mitigation': {
                        'strategy': 'provide_evidence',
                        'messaging': (
                            "Acme's 500-node cluster matches enterprise complexity. "
                            'The $2M migration scope is evidence of operating at that scale. '
                            'Infrastructure reliability at Acme Corp was mission-critical.'
                        ),
                    },
                    'where_to_address': ['cover_letter', 'interview'],
                }
            ],
            'preemptive_responses': [
                {
                    'concern': 'Team size gap',
                    'preemptive_action': 'Open CV with team leadership metrics',
                }
            ],
        },
        'value_proposition': {
            'primary_value': {
                'statement': 'Reduce infrastructure risk while scaling SysAid platform.',
                'evidence': 'Delivered $2M migration with zero downtime',
                'outcome_for_company': 'Faster feature delivery with reliable platform',
            },
            'secondary_values': [
                {
                    'value': 'Python depth reduces onboarding time',
                    'proof': 'Expert-level Python across 5 production systems',
                },
                {
                    'value': 'Infrastructure project leadership',
                    'proof': '$2M migration delivered',
                },
            ],
            'quantified_impact': [
                {
                    'metric': 'Infrastructure delivery time',
                    'expected_range': '20-30% faster',
                    'basis_for_projection': 'Based on Acme migration benchmark',
                }
            ],
            'elevator_pitch': (
                'Platform engineer with $2M AWS migration track record, ready to scale SysAid infrastructure without disrupting product delivery.'
            ),
        },
        'application_strategy': {
            'messaging_approach': 'Lead with infrastructure migration outcomes.',
            'ats_keywords': {
                'primary': ['platform engineering', 'AWS', 'Python'],
                'secondary': ['cloud migration', 'infrastructure'],
            },
            'cv_lead_differentiator': '$2M AWS migration with zero downtime',
            'sections_to_compress': ['Education'],
        },
    }


# P2: Three-stage pipeline test fixtures
@pytest.fixture
def sample_parsed_facts() -> 'UserCV':
    """UserCV with work experience for pipeline tests."""
    from careervp.models.cv_models import Skill, SkillLevel, UserCV, WorkExperience

    return UserCV(
        user_id='user-123',
        full_name='Alex Candidate',
        email='alex@example.com',
        phone='+1-555-0100',
        location='New York, NY',
        professional_summary='Engineering leader with platform and cloud expertise.',
        work_experience=[
            WorkExperience(
                company='Nimbus Labs',
                role='Senior Software Engineer',
                start_date='2021-01',
                end_date='Present',
                is_current=True,
                responsibilities=['Led Kubernetes migration for 12 production services'],
                achievements=[
                    'Increased deployment reliability by 35%',
                    'Reduced pipeline duration by 22%',
                ],
                technologies=['Kubernetes', 'AWS', 'Python'],
            ),
        ],
        education=[],
        skills=[
            Skill(name='Python', level=SkillLevel.EXPERT),
            Skill(name='AWS', level=SkillLevel.ADVANCED),
            Skill(name='Kubernetes', level=SkillLevel.EXPERT),
            Skill(name='Leadership', level=SkillLevel.INTERMEDIATE),
        ],
        certifications=[],
        languages=['English'],
    )


@pytest.fixture
def mock_llm_stage1() -> MagicMock:
    """LLM client that returns a valid Stage1 JSON for mocking."""
    mock = MagicMock()
    mock.complete.return_value = MagicMock(
        text=json.dumps(
            {
                'uvp_statement': 'Platform engineer with cloud expertise and 35% reliability improvement track record',
                'key_differentiators': ['Kubernetes automation', 'Python tooling', 'SRE mindset'],
                'primary_keywords': [
                    {
                        'keyword': 'Kubernetes',
                        'category': 'technical_skill',
                        'priority': 1,
                        'supporting_evidence': 'work_experience[0].achievements[0]',
                    },
                    {'keyword': 'Python', 'category': 'technical_skill', 'priority': 2, 'supporting_evidence': 'work_experience[0].skills'},
                    {'keyword': 'AWS', 'category': 'technical_skill', 'priority': 3, 'supporting_evidence': 'work_experience[0].skills'},
                ],
                'keywords_to_emphasize': ['Kubernetes', 'Python', 'AWS'],
                'keywords_missing_from_cv': [],
                'experience_items_to_include': [],
                'summary_focus': 'Platform engineer with cloud expertise',
            }
        )
    )
    return mock
