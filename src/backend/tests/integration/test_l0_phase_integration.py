"""Phase 1 integration: run all generators and write I1 audit evidence."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Callable
from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.cover_letter import generate_cover_letter
from careervp.logic.cv_tailoring import tailor_cv
from careervp.logic.gap_analysis import generate_gap_questions
from careervp.logic.interview_prep import generate_interview_prep
from careervp.logic.vpr_generator import generate_vpr
from careervp.models.cover_letter import CoverLetterRequest
from careervp.models.cv import ContactInfo, UserCV, WorkExperience
from careervp.models.interview_prep import InterviewPrepRequest
from careervp.models.job import JobPosting
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import VPRRequest

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-key')

RUNS_PER_GENERATOR = 50
GENERATORS = ('cover_letter', 'interview_prep', 'gap_analysis', 'cv_tailoring', 'vpr')
TEMPLATE_PATTERNS = (
    'Generated cover letter for request',
    'What quantifiable examples show your impact in core competency',
    'Situation for question',
    'describe a relevant STAR example',
    '{cv_content}',
    '{job_description}',
    '{{',
    '<placeholder>',
    'TODO:',
)

REPO_ROOT = Path(__file__).resolve().parents[4]
EVIDENCE_PATH = REPO_ROOT / 'docs/beta/evidence/I1_generators/generator-output-audit.json'


def _sample_user_cv() -> UserCV:
    return UserCV(
        user_id='user-l0-integration',
        cv_id='cv-l0-integration',
        full_name='Alex Candidate',
        language='en',
        contact_info=ContactInfo(email='alex@example.com'),
        professional_summary='Backend engineer with distributed systems and platform leadership experience.',
        experience=[
            WorkExperience(
                company='Nimbus Labs',
                role='Senior Software Engineer',
                dates='2021 - Present',
                achievements=[
                    'Led platform modernization for distributed services with measurable reliability gains.',
                    'Implemented automation that improved release confidence.',
                ],
                technologies=['Python', 'AWS', 'Kubernetes'],
            )
        ],
        education=[],
        certifications=[],
        skills=['Python', 'AWS', 'Kubernetes', 'Leadership', 'Architecture'],
        top_achievements=['Reduced incident volume by 35%'],
        languages=['English'],
        is_parsed=True,
    )


def _sample_job_posting() -> JobPosting:
    return JobPosting(
        company_name='Acme Cloud',
        role_title='Principal Platform Engineer',
        description='Lead platform reliability and mentor senior engineers.',
        responsibilities=['Improve reliability', 'Drive architecture quality'],
        requirements=['Python', 'AWS', 'Distributed systems leadership'],
        nice_to_have=['Security mindset'],
        language='en',
    )


def _run_cover_letter(run_number: int) -> str:
    request = CoverLetterRequest(
        user_id='user-l0-integration',
        cv_id='cv-l0-integration',
        job_id=f'job-cover-{run_number}',
        vpr_id=f'vpr-cover-{run_number}',
        company_name='Acme Cloud',
        job_title='Principal Platform Engineer',
        job_description='Own platform reliability, observability, and architecture quality.',
        gap_response_ids=[],
    )
    vpr = MagicMock()
    vpr.model_dump.return_value = {'summary': 'Evidence-backed platform leadership.'}

    with (
        patch('careervp.logic.cover_letter.LLMClient') as mock_llm_cls,
        patch(
            'careervp.logic.cover_letter.check_anti_ai_patterns',
            return_value=SimpleNamespace(score=96, issues=[]),
        ),
    ):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = {
            'text': (
                f'Dear Hiring Team, I led reliability work at scale for run {run_number}, '
                'improving release stability and service performance through measurable execution.'
            )
        }
        mock_llm_cls.return_value = mock_llm
        result = asyncio.run(generate_cover_letter(request=request, user_cv=_sample_user_cv(), vpr=vpr))

    assert result.success is True
    assert result.data is not None
    assert result.data.cover_letter is not None
    mock_llm.generate.assert_called_once()
    return result.data.cover_letter.full_text


def _run_interview_prep(run_number: int) -> str:
    request = InterviewPrepRequest(
        user_id='user-l0-integration',
        vpr_id=f'vpr-prep-{run_number}',
        job_id=f'job-prep-{run_number}',
        gap_response_ids=[],
        focus_areas=['architecture', 'leadership'],
        question_count=3,
    )
    with patch('careervp.logic.interview_prep.LLMClient') as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = {
            'text': json.dumps(
                {
                    'questions': [
                        {
                            'question_id': f'q-{run_number}',
                            'question': f'Describe a real architecture tradeoff you led in run {run_number}.',
                            'question_type': 'behavioral',
                            'difficulty': 'medium',
                            'suggested_answer': {
                                'situation': 'Reliability issues impacted delivery confidence.',
                                'task': 'Stabilize the platform while maintaining roadmap progress.',
                                'action': 'Introduced release guardrails and observability standards.',
                                'result': 'Improved deploy success and reduced incidents.',
                                'full_text': 'Improved deploy success and reduced incidents with clear guardrails.',
                            },
                        }
                    ],
                    'questions_to_ask': [],
                }
            )
        }
        mock_llm_cls.return_value = mock_llm
        result = asyncio.run(
            generate_interview_prep(
                request=request,
                vpr_data={'summary': 'Platform impact'},
                gap_responses=[],
                job_title='Principal Platform Engineer',
                company_name='Acme Cloud',
            )
        )

    assert result.success is True
    assert result.data is not None
    assert result.data.interview_prep is not None
    mock_llm.generate.assert_called_once()
    question_text = result.data.interview_prep.questions[0].question
    return question_text


def _run_gap_analysis(run_number: int) -> str:
    questions = [
        {
            'question_id': f'q-{run_number}-{idx}',
            'question': f'Describe measurable platform outcome {idx} from run {run_number}.',
            'impact': 'HIGH' if idx < 4 else 'MEDIUM',
            'probability': 'MEDIUM',
            'tags': ['[CV IMPACT]'],
        }
        for idx in range(10)
    ]

    with patch('careervp.logic.gap_analysis.LLMClient') as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = {'text': json.dumps({'questions': questions})}
        mock_llm_cls.return_value = mock_llm
        result = asyncio.run(
            generate_gap_questions(
                user_cv={'full_name': 'Alex Candidate', 'skills': ['Python', 'AWS']},
                job_posting={'role_title': 'Principal Platform Engineer', 'requirements': ['Reliability']},
                dal=None,
            )
        )

    assert result.success is True
    assert result.data is not None
    mock_llm.generate.assert_called_once()
    return ' '.join(item['question'] for item in result.data)


def _run_cv_tailoring(run_number: int) -> str:
    mock_llm = MagicMock()
    mock_llm.generate.return_value = {
        'summary': f'Platform-focused engineer delivering measurable reliability outcomes in run {run_number} across cloud systems and platform engineering.',
        'experience': [
            {
                'company': 'Nimbus Labs',
                'title': 'Senior Software Engineer',
                'start_date': '01/2021',
                'end_date': 'Present',
                'bullets': ['Led platform engineering improvements that increased release reliability by 35% across cloud services.'],
            }
        ],
        'skills': {'technical': ['Python', 'AWS', 'Kubernetes', 'Leadership'], 'soft': ['Communication']},
        'job_description': 'Required: python aws kubernetes leadership reliability architecture security',
    }

    with patch(
        'careervp.logic.cv_tailoring.check_anti_ai_patterns',
        return_value=SimpleNamespace(score=95, issues=[]),
    ):
        result = tailor_cv(
            master_cv=_sample_user_cv(),
            job_description=('Required: Python AWS Kubernetes reliability architecture leadership security observability.'),
            dal=None,
            llm_client=mock_llm,
        )

    assert result.success is True
    assert result.data is not None
    mock_llm.generate.assert_called_once()
    from careervp.models.cv_tailoring_models import TailoredCVResponse

    assert isinstance(result.data, TailoredCVResponse)
    cv_sections = result.data.cv_sections
    assert cv_sections is not None
    return f'{cv_sections.summary} {" ".join(cv_sections.skills.technical)}'


def _stage_3_payload() -> str:
    return json.dumps(
        {
            'executive_summary': 'Alex aligns platform strategy with measurable reliability outcomes.',
            'evidence_matrix': [
                {
                    'requirement': 'Python',
                    'evidence': 'Led automation initiatives in Python-backed services.',
                    'alignment_score': 'STRONG',
                    'impact_potential': 'Can improve reliability under growth.',
                }
            ],
            'differentiators': ['Balances architecture rigor with delivery speed.'],
            'gap_strategies': [],
            'cultural_fit': 'Collaborative ownership mindset.',
            'talking_points': ['Describe how guardrails improved release confidence.'],
            'keywords': ['Python', 'AWS', 'Reliability'],
        }
    )


def _stage_4_payload() -> str:
    return json.dumps(
        {
            'executive_summary': 'Alex has led platform initiatives requiring high ownership and pragmatic execution.',
            'differentiators': ['Combines strategy with hands-on delivery discipline.'],
            'talking_points': ['Share one measurable reliability initiative with outcomes.'],
            'corrections_applied': ['Refined tone for clarity'],
        }
    )


def _run_vpr(run_number: int) -> str:
    request = VPRRequest(
        application_id=f'app-{run_number}',
        user_id='user-l0-integration',
        job_posting=_sample_job_posting(),
        gap_responses=[],
    )
    mock_dal = MagicMock()
    mock_dal.save_vpr.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)

    with (
        patch('careervp.logic.vpr_generator.LLMClient') as mock_llm_cls,
        patch(
            'careervp.logic.vpr_generator.run_vpr_quality_gate',
            return_value=SimpleNamespace(
                anti_ai_score=94,
                grammar_score=95,
                tone_score=90,
                structural_score=90,
                issues=[],
                passed_gate=True,
            ),
        ),
    ):
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.side_effect = [
            Result(
                success=True,
                data={
                    'text': _stage_3_payload(),
                    'input_tokens': 500,
                    'output_tokens': 350,
                    'cost': 0.01,
                    'model': 'claude-sonnet-4-5',
                },
                code=ResultCode.SUCCESS,
            ),
            Result(
                success=True,
                data={
                    'text': _stage_4_payload(),
                    'input_tokens': 450,
                    'output_tokens': 300,
                    'cost': 0.009,
                    'model': 'claude-sonnet-4-5',
                },
                code=ResultCode.SUCCESS,
            ),
        ]
        mock_llm_cls.return_value = mock_llm_instance
        result = generate_vpr(request=request, user_cv=_sample_user_cv(), dal=mock_dal)

    assert result.success is True
    assert result.data is not None
    assert result.data.vpr is not None
    mock_dal.save_vpr.assert_called_once()
    assert mock_llm_instance.invoke.call_count == 1
    return json.dumps(result.data.vpr.model_dump(mode='json'))


def _find_template_match(text: str) -> str | None:
    lowered = text.lower()
    for pattern in TEMPLATE_PATTERNS:
        if pattern.lower() in lowered:
            return pattern
    return None


def _write_evidence(records: list[dict[str, object]]) -> None:
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(records, indent=2), encoding='utf-8')


def _run_generator(generator: str, run_number: int) -> str:
    runners: dict[str, Callable[[int], str]] = {
        'cover_letter': _run_cover_letter,
        'interview_prep': _run_interview_prep,
        'gap_analysis': _run_gap_analysis,
        'cv_tailoring': _run_cv_tailoring,
        'vpr': _run_vpr,
    }
    return runners[generator](run_number)


@pytest.mark.integration
def test_l0_phase_integration_generates_i1_audit_with_zero_template_matches() -> None:
    records: list[dict[str, object]] = []

    for generator in GENERATORS:
        for run_number in range(1, RUNS_PER_GENERATOR + 1):
            output_text = _run_generator(generator, run_number)
            template_match = _find_template_match(output_text)
            records.append(
                {
                    'generator': generator,
                    'run_id': f'l0-phase-{generator}-{run_number:03d}',
                    'is_template': template_match is not None,
                    'template_match': template_match,
                    'response_excerpt': output_text[:220],
                    'environment': 'local-integration-test',
                }
            )

    _write_evidence(records)

    assert len(records) == RUNS_PER_GENERATOR * len(GENERATORS)
    assert all(record['is_template'] is False for record in records)
    assert EVIDENCE_PATH.exists()
