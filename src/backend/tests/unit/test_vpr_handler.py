import json
import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from careervp.handlers.vpr_handler import lambda_handler
from careervp.models.cv import ContactInfo, UserCV
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import (
    VPR,
    TokenUsage,
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
    VPRResponse,
    VPRResponsibility,
    VPRRoleAlignment,
    VPRSecondaryValue,
    VPRSkillsAnalysis,
    VPRStrength,
    VPRUniqueStrength,
    VPRValueProposition,
)


@pytest.fixture(autouse=True)
def env_vars():
    os.environ['DYNAMODB_TABLE_NAME'] = 'test-table'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'careervp-test'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    yield
    os.environ.pop('DYNAMODB_TABLE_NAME', None)
    os.environ.pop('POWERTOOLS_SERVICE_NAME', None)
    os.environ.pop('LOG_LEVEL', None)


@pytest.fixture
def lambda_context():
    return MagicMock()


@pytest.fixture
def user_cv():
    return UserCV(
        user_id='user-123',
        full_name='Test User',
        language='en',
        contact_info=ContactInfo(email='user@example.com'),
        experience=[],
        education=[],
        certifications=[],
        skills=['python'],
        top_achievements=['Built things'],
        languages=[],
        professional_summary='summary',
        is_parsed=True,
        source_file_key='key',
    )


def _sample_request_body() -> dict[str, Any]:
    return {
        'application_id': 'app-123',
        'user_id': 'user-123',
        'job_posting': {
            'company_name': 'Acme Corp',
            'role_title': 'Senior Engineer',
            'description': 'Job desc',
            'responsibilities': ['Build systems'],
            'requirements': ['5+ years experience'],
            'nice_to_have': ['AWS'],
            'language': 'en',
            'source_url': 'https://example.com/job',
        },
        'gap_responses': [],
    }


def test_vpr_request_accepts_common_job_posting_aliases():
    payload = {
        'application_id': 'test-123',
        'user_id': 'user-456',
        'job_posting': {
            'title': 'Senior Engineer',
            'company': 'Acme Corp',
            'requirements': ['Python', 'AWS'],
        },
    }

    request = VPRRequest.model_validate(payload)

    assert request.job_posting.company_name == 'Acme Corp'
    assert request.job_posting.role_title == 'Senior Engineer'
    assert request.job_posting.requirements == ['Python', 'AWS']


def _generate_event(body: dict[str, Any]) -> dict[str, Any]:
    return {
        'httpMethod': 'POST',
        'path': '/api/vpr',
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body),
    }


def _build_minimal_vpr(application_id: str = 'app-123', user_id: str = 'user-123') -> VPR:
    """Build a minimal valid VPR for handler tests."""
    return VPR(
        application_id=application_id,
        user_id=user_id,
        metadata=VPRMetadata(
            report_date='2024-01-15',
            candidate_name='Test User',
            target_role='Senior Engineer',
            target_company='Acme Corp',
        ),
        executive_summary=VPRExecutiveSummary(
            overall_fit_score=75,
            fit_rationale=(
                'Strong technical match with demonstrated delivery track record. Python and AWS expertise directly align with core role requirements.'
            ),
            top_three_strengths=[
                VPRStrength(strength='Python expertise', evidence='5 years production Python', relevance_to_role='Core stack'),
                VPRStrength(strength='AWS architecture', evidence='Designed 3 production systems', relevance_to_role='Infrastructure'),
                VPRStrength(strength='Team leadership', evidence='Led teams of 5+', relevance_to_role='Management'),
            ],
            top_three_concerns=[
                VPRConcern(concern='Limited ML experience', severity='medium', mitigation='Show adjacent work'),
                VPRConcern(concern='No fintech background', severity='low', mitigation='Transfer skills'),
                VPRConcern(concern='Remote work history', severity='low', mitigation='Highlight async delivery'),
            ],
            recommended_approach='apply_with_customization',
        ),
        role_alignment=VPRRoleAlignment(
            core_responsibilities=[
                VPRResponsibility(
                    responsibility='Lead backend development',
                    alignment_score=85,
                    candidate_evidence=['Led Python backend at Apex Labs'],
                    evidence_quality='direct',
                )
            ],
            requirement_breakdown=VPRRequirementBreakdown(
                must_have=[],
                nice_to_have=[],
                assumed_prerequisites=[],
            ),
        ),
        experience_mapping=VPRExperienceMapping(
            relevant_experiences=[
                VPRRelevantExperience(
                    role='Senior Engineer',
                    organization='Apex Labs',
                    duration='3 years',
                    key_achievements=[VPRKeyAchievement(achievement='Scaled API', metric='50% faster', impact='Cost reduction')],
                    relevance_to_target_role='Direct match',
                )
            ],
            experience_gaps=[],
        ),
        skills_analysis=VPRSkillsAnalysis(
            technical_skills=[],
            soft_skills=[],
            tool_proficiency=[],
        ),
        evidence_gaps=VPREvidenceGaps(
            identified_gaps=[
                VPRIdentifiedGap(
                    requirement='ML experience',
                    current_evidence='Adjacent data work only',
                    gap_severity='medium',
                    suggested_evidence=['ML side projects'],
                )
            ],
            priority_gaps_to_address=[VPRPriorityGap(gap='ML experience', priority=1, action_item='Complete ML course', deadline='before_interview')],
        ),
        differentiators=VPRDifferentiators(
            unique_strengths=[
                VPRUniqueStrength(
                    strength='Full-stack delivery ownership',
                    rarity='uncommon',
                    relevance='End-to-end product delivery',
                    proof='Shipped 3 products independently',
                )
            ],
            competitive_advantages=[],
            positioning_statement=(
                'Proven engineer with full-stack delivery expertise and measurable track record '
                'of improving system reliability and team velocity across complex initiatives.'
            ),
        ),
        concerns_and_mitigations=VPRConcernsAndMitigations(
            likely_objections=[
                VPRObjection(
                    objection='Limited ML experience',
                    likelihood='possible',
                    mitigation=VPRMitigation(
                        strategy='show_analogous_experience',
                        messaging='Data pipeline work demonstrates ML adjacency.',
                    ),
                    where_to_address=['interview'],
                )
            ],
            preemptive_responses=[],
        ),
        value_proposition=VPRValueProposition(
            primary_value=VPRPrimaryValue(
                statement='Ship reliable systems faster',
                evidence='40% delivery improvement at Apex Labs',
                outcome_for_company='Reduced time-to-market',
            ),
            secondary_values=[
                VPRSecondaryValue(value='Cost efficiency', proof='30% infra cost reduction'),
                VPRSecondaryValue(value='Team alignment', proof='Cross-functional delivery track record'),
            ],
            quantified_impact=[],
            elevator_pitch=(
                'Proven engineer delivering scalable systems with measurable business impact across cloud-native and distributed environments.'
            ),
        ),
        application_strategy=VPRApplicationStrategy(
            messaging_approach='Lead with delivery track record and measurable outcomes.',
            ats_keywords=VPRKeywordGroup(primary=['Python', 'AWS'], secondary=['Leadership']),
            cv_lead_differentiator='Backend specialist with end-to-end delivery experience.',
            sections_to_compress=[],
        ),
        version=1,
        language='en',
        created_at=datetime.now(timezone.utc),
        word_count=250,
    )


def _successful_vpr_response() -> VPRResponse:
    vpr = _build_minimal_vpr()
    token_usage = TokenUsage(input_tokens=100, output_tokens=200, cost_usd=1.25, model='sonnet')
    return VPRResponse(success=True, vpr=vpr, token_usage=token_usage, generation_time_ms=321)


def test_successful_vpr_generation(mocker, user_cv, lambda_context):
    dal_cls = mocker.patch('careervp.handlers.vpr_handler.DynamoDalHandler')
    dal_instance = dal_cls.return_value
    dal_instance.get_cv.return_value = user_cv
    generate_vpr_mock = mocker.patch(
        'careervp.handlers.vpr_handler.generate_vpr',
        return_value=Result(success=True, data=_successful_vpr_response(), code=ResultCode.VPR_GENERATED),
    )
    metrics_mock = mocker.patch('careervp.handlers.vpr_handler.metrics.add_metric')

    response = lambda_handler(_generate_event(_sample_request_body()), lambda_context)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['success'] is True
    assert generate_vpr_mock.call_args[0][1] == user_cv
    assert metrics_mock.call_count == 3


def test_missing_cv_returns_404(mocker, user_cv, lambda_context):
    dal_cls = mocker.patch('careervp.handlers.vpr_handler.DynamoDalHandler')
    dal_instance = dal_cls.return_value
    dal_instance.get_cv.return_value = None
    generate_vpr_mock = mocker.patch('careervp.handlers.vpr_handler.generate_vpr')

    response = lambda_handler(_generate_event(_sample_request_body()), lambda_context)

    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert body['success'] is False
    assert 'CV not found' in body['error']
    generate_vpr_mock.assert_not_called()


def test_invalid_request_body_returns_400(mocker, lambda_context):
    dal_cls = mocker.patch('careervp.handlers.vpr_handler.DynamoDalHandler')
    generate_vpr_mock = mocker.patch('careervp.handlers.vpr_handler.generate_vpr')
    event = {'body': '{invalid-json'}

    response = lambda_handler(event, lambda_context)

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['success'] is False
    dal_cls.assert_not_called()
    generate_vpr_mock.assert_not_called()


def test_fvs_validation_failure_returns_422(mocker, user_cv, lambda_context):
    dal_cls = mocker.patch('careervp.handlers.vpr_handler.DynamoDalHandler')
    dal_instance = dal_cls.return_value
    dal_instance.get_cv.return_value = user_cv

    error_response = VPRResponse(success=False, vpr=None, token_usage=None, generation_time_ms=0, error='Hallucination detected')
    mocker.patch(
        'careervp.handlers.vpr_handler.generate_vpr',
        return_value=Result(
            success=False,
            data=error_response,
            error='Hallucination detected',
            code=ResultCode.FVS_HALLUCINATION_DETECTED,
        ),
    )
    metrics_mock = mocker.patch('careervp.handlers.vpr_handler.metrics.add_metric')

    response = lambda_handler(_generate_event(_sample_request_body()), lambda_context)

    assert response['statusCode'] == 422
    body = json.loads(response['body'])
    assert body['success'] is False
    assert body['error'] == 'Hallucination detected'
    metrics_mock.assert_not_called()


def test_llm_error_returns_502(mocker, user_cv, lambda_context):
    dal_cls = mocker.patch('careervp.handlers.vpr_handler.DynamoDalHandler')
    dal_instance = dal_cls.return_value
    dal_instance.get_cv.return_value = user_cv
    mocker.patch(
        'careervp.handlers.vpr_handler.generate_vpr',
        return_value=Result(
            success=False,
            data=None,
            error='LLM crashed',
            code=ResultCode.LLM_API_ERROR,
        ),
    )

    response = lambda_handler(_generate_event(_sample_request_body()), lambda_context)

    assert response['statusCode'] == 502
    body = json.loads(response['body'])
    assert body['success'] is False
    assert body['error'] == 'LLM crashed'


def test_metrics_emitted_on_success(mocker, user_cv, lambda_context):
    dal_cls = mocker.patch('careervp.handlers.vpr_handler.DynamoDalHandler')
    dal_instance = dal_cls.return_value
    dal_instance.get_cv.return_value = user_cv
    mocker.patch(
        'careervp.handlers.vpr_handler.generate_vpr',
        return_value=Result(success=True, data=_successful_vpr_response(), code=ResultCode.VPR_GENERATED),
    )
    metrics_mock = mocker.patch('careervp.handlers.vpr_handler.metrics.add_metric')

    lambda_handler(_generate_event(_sample_request_body()), lambda_context)

    assert metrics_mock.call_count == 3
    assert metrics_mock.call_args_list[0].kwargs == {'name': 'VPRGenerated', 'unit': 'Count', 'value': 1}
    assert metrics_mock.call_args_list[1].kwargs == {
        'name': 'VPRGenerationTimeMs',
        'unit': 'Milliseconds',
        'value': 321,
    }
    assert metrics_mock.call_args_list[2].kwargs == {
        'name': 'VPRCostUSD',
        'unit': 'None',
        'value': 1.25,
    }
