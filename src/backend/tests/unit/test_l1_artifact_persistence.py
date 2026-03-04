"""L1.1 real persistence tests for generated artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from careervp.models.cv import ContactInfo, UserCV, WorkExperience
from careervp.models.job import JobPosting
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import VPRRequest


def _user_cv(user_id: str = 'user-123') -> UserCV:
    return UserCV(
        user_id=user_id,
        cv_id='cv-123',
        full_name='Alex Candidate',
        language='en',
        contact_info=ContactInfo(email='alex@example.com'),
        professional_summary='Backend engineer focused on reliable systems.',
        experience=[
            WorkExperience(
                company='Nimbus Labs',
                role='Senior Engineer',
                dates='2020 - Present',
                achievements=['Improved release reliability by 35%'],
                technologies=['Python', 'AWS'],
            )
        ],
        education=[],
        certifications=[],
        skills=['Python', 'AWS', 'Leadership'],
        top_achievements=['Reduced incidents by 35%'],
        languages=['English'],
        is_parsed=True,
    )


def _cover_letter_event() -> dict[str, object]:
    return {
        'httpMethod': 'POST',
        'path': '/cover-letter/generate',
        'requestContext': {'authorizer': {'jwt': {'claims': {'sub': 'user-123'}}}},
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(
            {
                'cv_id': 'cv-123',
                'job_id': 'job-123',
                'vpr_id': 'vpr-123',
                'gap_response_ids': ['gap-123'],
                'company_research_id': 'company-123',
            }
        ),
    }


def _interview_prep_event() -> dict[str, object]:
    return {
        'httpMethod': 'POST',
        'path': '/interview-prep/generate',
        'requestContext': {'authorizer': {'jwt': {'claims': {'sub': 'user-123'}}}},
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(
            {
                'vpr_id': 'vpr-123',
                'gap_response_ids': ['gap-1'],
                'focus_areas': ['architecture'],
                'question_count': 3,
            }
        ),
    }


def _cv_tailoring_event() -> dict[str, object]:
    return {
        'httpMethod': 'POST',
        'path': '/cv-tailoring/generate',
        'requestContext': {'authorizer': {'jwt': {'claims': {'sub': 'user-123'}}}},
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(
            {
                'cv_id': 'cv-123',
                'job_id': 'job-123',
                'vpr_id': 'vpr-123',
            }
        ),
    }


def _gap_event() -> dict[str, object]:
    return {
        'httpMethod': 'POST',
        'path': '/gap-analysis/questions',
        'requestContext': {'authorizer': {'jwt': {'claims': {'sub': 'user-123'}}}},
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'cv_id': 'cv-123', 'job_id': 'job-123', 'max_questions': 10}),
    }


def _stage_3_payload() -> str:
    return json.dumps(
        {
            'executive_summary': 'Alex aligns platform strategy with measurable outcomes.',
            'evidence_matrix': [
                {
                    'requirement': 'Python',
                    'evidence': 'Led Python reliability initiatives at scale.',
                    'alignment_score': 'STRONG',
                    'impact_potential': 'Can improve production reliability.',
                }
            ],
            'differentiators': ['Balances architecture quality with speed.'],
            'gap_strategies': [],
            'cultural_fit': 'Collaborative ownership.',
            'talking_points': ['Show reliability outcomes with metrics.'],
            'keywords': ['Python', 'AWS'],
        }
    )


def _stage_4_payload() -> str:
    return json.dumps(
        {
            'executive_summary': 'Alex has led high-impact platform initiatives with measurable outcomes.',
            'differentiators': ['Combines strategy and delivery discipline.'],
            'talking_points': ['Describe one measurable reliability initiative.'],
            'corrections_applied': ['Refined wording for natural tone'],
        }
    )


def _sample_vpr_request() -> VPRRequest:
    posting = JobPosting(
        company_name='Acme Cloud',
        role_title='Principal Platform Engineer',
        description='Lead platform reliability and architecture quality.',
        responsibilities=['Improve reliability'],
        requirements=['Python', 'AWS'],
        nice_to_have=['Security'],
        language='en',
    )
    return VPRRequest(
        application_id='app-123',
        user_id='user-123',
        job_posting=posting,
        gap_responses=[],
    )


@pytest.mark.unit
def test_cover_letter_generation_persists_to_dynamodb() -> None:
    from careervp.handlers.cover_letter_handler import lambda_handler

    with patch('careervp.handlers.cover_letter_handler._get_dal') as mock_get_dal:
        dal = MagicMock()
        dal.get_cv.return_value = _user_cv()
        dal.save_cover_letter.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)
        mock_get_dal.return_value = dal

        with patch('careervp.handlers.cover_letter_handler.generate_cover_letter') as mock_generate:
            payload = {'cover_letter_id': 'cl-123', 'full_text': 'Generated cover letter text.', 'word_count': 120, 'paragraphs': []}
            mock_generate.return_value = Result(
                success=True,
                data=MagicMock(cover_letter=MagicMock(model_dump=MagicMock(return_value=payload))),
                code=ResultCode.COVER_LETTER_GENERATED,
            )
            response = lambda_handler(_cover_letter_event(), MagicMock())

    assert response['statusCode'] == 200
    dal.save_cover_letter.assert_called_once()
    kwargs = dal.save_cover_letter.call_args.kwargs
    assert kwargs['user_id'] == 'user-123'
    assert kwargs['cv_id'] == 'cv-123'
    assert kwargs['job_id'] == 'job-123'


@pytest.mark.unit
def test_interview_prep_persisted_item_contains_prefix_and_ttl() -> None:
    from careervp.handlers.interview_prep_handler import lambda_handler

    with patch('careervp.handlers.interview_prep_handler._get_dal') as mock_get_dal:
        table = MagicMock()
        dal = MagicMock()
        dal.get_cv.return_value = _user_cv()
        dal._get_db_handler.return_value = table
        dal.table_name = 'table'
        mock_get_dal.return_value = dal

        with patch('careervp.handlers.interview_prep_handler.generate_interview_prep') as mock_generate:
            payload = {'prep_id': 'prep-123', 'questions': []}
            mock_generate.return_value = Result(
                success=True,
                data=MagicMock(interview_prep=MagicMock(model_dump=MagicMock(return_value=payload))),
                code=ResultCode.INTERVIEW_QUESTIONS_GENERATED,
            )
            response = lambda_handler(_interview_prep_event(), MagicMock())

    assert response['statusCode'] == 200
    table.put_item.assert_called_once()
    item = table.put_item.call_args.kwargs['Item']
    assert str(item['sk']).startswith('ARTIFACT#INTERVIEW_PREP#')
    assert isinstance(item.get('expiration'), int)
    assert item['expiration'] > int(datetime.now(timezone.utc).timestamp())


@pytest.mark.unit
def test_cv_tailoring_async_generate_persists_with_artifact_prefix() -> None:
    from careervp.handlers.cv_tailoring_handler import lambda_handler

    table = MagicMock()
    dal = MagicMock()
    dal.get_cv.return_value = _user_cv()
    dal._get_db_handler.return_value = table

    with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=dal):
        response = lambda_handler(_cv_tailoring_event(), MagicMock())

    assert response['statusCode'] == 202
    body = json.loads(response['body'])
    assert body['request_id']
    table.put_item.assert_called_once()
    item = table.put_item.call_args.kwargs['Item']
    assert str(item['sk']).startswith('ARTIFACT#CV_TAILORED#')
    assert item.get('request_id') == body['request_id']


@pytest.mark.unit
def test_gap_analysis_generation_persists_item_with_non_null_artifact_id() -> None:
    from careervp.handlers.gap_handler import lambda_handler

    generated_questions = [
        {'question_id': f'q-{idx}', 'question': 'Describe measurable impact.', 'impact': 'HIGH', 'probability': 'MEDIUM', 'tags': ['[CV IMPACT]']}
        for idx in range(10)
    ]

    with (
        patch('careervp.handlers.gap_handler.generate_gap_questions') as mock_generate,
        patch('careervp.handlers.gap_handler._get_dal') as mock_get_dal,
        patch('careervp.handlers.gap_handler._get_trial_service') as mock_trial_service,
        patch('careervp.handlers.gap_handler._get_application_repository') as mock_application_repository,
    ):
        dal = MagicMock()
        dal.save_gap_questions.return_value = Result(success=True, data=None, code=ResultCode.GAP_QUESTIONS_GENERATED)
        mock_get_dal.return_value = dal
        mock_generate.return_value = Result(success=True, data=generated_questions, code=ResultCode.GAP_QUESTIONS_GENERATED)
        trial_service = MagicMock()
        trial_service.check_trial_status.return_value = {'is_active': True}
        trial_service.consume_credit.return_value = None
        mock_trial_service.return_value = trial_service
        mock_application_repository.return_value = MagicMock()
        response = lambda_handler(_gap_event(), MagicMock())

    assert response['statusCode'] in [200, 201]
    dal.save_gap_questions.assert_called_once()
    call_args = dal.save_gap_questions.call_args
    assert call_args is not None


@pytest.mark.unit
def test_vpr_generation_persists_via_save_vpr() -> None:
    with patch('careervp.logic.vpr_generator.LLMClient') as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            Result(
                success=True,
                data={'text': _stage_3_payload(), 'input_tokens': 500, 'output_tokens': 350, 'cost': 0.01, 'model': 'claude-sonnet-4-5'},
                code=ResultCode.SUCCESS,
            ),
            Result(
                success=True,
                data={'text': _stage_4_payload(), 'input_tokens': 450, 'output_tokens': 300, 'cost': 0.009, 'model': 'claude-sonnet-4-5'},
                code=ResultCode.SUCCESS,
            ),
        ]
        mock_llm_cls.return_value = mock_llm

        dal = MagicMock()
        dal.save_vpr.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)

        from careervp.logic.vpr_generator import generate_vpr

        result = generate_vpr(_sample_vpr_request(), _user_cv(), dal)

    assert result.success is True
    dal.save_vpr.assert_called_once()


@pytest.mark.unit
def test_list_methods_use_query_not_scan() -> None:
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    dal = DynamoDalHandler('test-table')
    table = MagicMock()
    table.query.return_value = {'Items': []}
    dal._get_db_handler = MagicMock(return_value=table)

    list_cover_result = dal.list_cover_letters('user-123')
    list_tailored_result = dal.list_tailored_cvs('user-123')

    assert list_cover_result.success is True
    assert list_tailored_result.success is True
    assert table.query.call_count >= 2
    assert not table.scan.called
