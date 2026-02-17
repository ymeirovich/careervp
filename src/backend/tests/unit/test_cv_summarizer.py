"""Unit tests for CV prompt-compression summarizer."""

from __future__ import annotations

import json
import math

from careervp.logic.cv_summarizer import CVSummarizer
from careervp.models.cv import Education, Skill, SkillLevel, UserCV, WorkExperience


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _build_large_cv() -> UserCV:
    long_summary = 'Senior engineer with deep backend expertise. ' * 220
    long_description = 'Designed distributed systems, delivered cloud migrations, and optimized platform costs. ' * 120

    experiences = [
        WorkExperience(
            company='Northwind Systems',
            role='Principal Engineer',
            dates='2022-Present',
            description=long_description,
            achievements=['Cut platform spend by 37%', 'Led modernization for 12 services'],
        ),
        WorkExperience(
            company='Skyline Data',
            role='Senior Engineer',
            dates='2019-2022',
            description=long_description,
            achievements=['Built analytics pipeline', 'Improved SLA to 99.95%'],
        ),
        WorkExperience(
            company='Global Commerce',
            role='Software Engineer',
            dates='2016-2019',
            description=long_description,
            achievements=['Scaled checkout stack', 'Reduced error rate by 80%'],
        ),
        WorkExperience(
            company='Legacy Labs',
            role='Developer',
            dates='2014-2016',
            description=long_description,
        ),
    ]

    skills = [
        Skill(name='Python', level=SkillLevel.EXPERT, years_of_experience=10),
        Skill(name='AWS', level=SkillLevel.ADVANCED, years_of_experience=8),
        Skill(name='Distributed Systems', level=SkillLevel.ADVANCED, years_of_experience=7),
    ]
    skills.extend(f'Skill-{index:02d}' for index in range(1, 48))

    education = [
        Education(
            institution='Massachusetts Institute of Technology and Advanced Applied Research Programs',
            degree='Master of Science in Computer Engineering and Large Scale Systems Design',
            field_of_study='Cloud Architecture and Enterprise Platform Reliability',
            graduation_date='2014',
        ),
        Education(
            institution='University of Technology and Systems Innovation',
            degree='Bachelor of Engineering in Computer Science and Information Systems',
            field_of_study='Software Engineering and Distributed Computing',
            graduation_date='2012',
        ),
    ]

    return UserCV(
        user_id='user-large',
        full_name='Alex Cost Saver',
        language='en',
        email='alex@example.com',
        experience=experiences,
        education=education,
        certifications=[],
        skills=skills,
        top_achievements=['Cut platform spend by 37%'],
        professional_summary=long_summary,
        languages=[],
    )


def test_summarize_truncates_long_sections() -> None:
    summarizer = CVSummarizer()
    cv = _build_large_cv()

    summarized = summarizer.summarize(cv)

    assert len(summarized['summary']) <= 200
    assert len(summarized['experience']) <= 3
    assert all(len(job) <= 500 for job in summarized['experience'])
    assert len(summarized['skills_extracted']) <= 50
    assert len(summarized['education']) <= 300
    assert summarized['was_truncated'] is True

    original_tokens = _estimate_tokens(json.dumps(cv.model_dump(mode='json'), ensure_ascii=False))
    assert summarized['token_count'] <= int(original_tokens * 0.6)


def test_summarize_preserves_key_information() -> None:
    summarizer = CVSummarizer()
    cv = UserCV(
        user_id='user-preserve',
        full_name='Jamie Candidate',
        language='en',
        email='jamie@example.com',
        experience=[
            WorkExperience(
                company='Acme Corp',
                role='Lead Platform Engineer',
                dates='2021-Present',
                description='Owns platform reliability and developer tooling.',
            ),
            WorkExperience(
                company='Example Inc',
                role='Software Engineer',
                dates='2018-2021',
            ),
        ],
        education=[],
        certifications=[],
        skills=[
            Skill(name='Python', level=SkillLevel.EXPERT, years_of_experience=9),
            Skill(name='AWS', level=SkillLevel.ADVANCED, years_of_experience=7),
            'Leadership',
        ],
        top_achievements=[],
        professional_summary='Backend engineer focused on cloud cost and reliability.',
        languages=[],
    )

    summarized = summarizer.summarize(cv)

    assert 'Jamie Candidate' in summarized['summary']
    assert 'Python' in summarized['skills_extracted'][:3]
    assert any('Acme Corp' in job and 'Lead Platform Engineer' in job for job in summarized['experience'])


def test_summarize_calculates_token_count() -> None:
    summarizer = CVSummarizer()
    cv = _build_large_cv()

    summarized = summarizer.summarize(cv)
    payload_without_metadata = {
        'summary': summarized['summary'],
        'experience': summarized['experience'],
        'skills_extracted': summarized['skills_extracted'],
        'education': summarized['education'],
    }
    expected_tokens = _estimate_tokens(json.dumps(payload_without_metadata, ensure_ascii=False))

    assert summarized['token_count'] == expected_tokens
    assert isinstance(summarized['token_count'], int)
    assert summarized['token_count'] > 0


def test_summarize_handles_edge_cases() -> None:
    summarizer = CVSummarizer()
    empty_cv = UserCV(
        user_id='user-empty',
        full_name='Pat Empty',
        language='en',
        experience=[],
        education=[],
        certifications=[],
        skills=[],
        top_achievements=[],
        professional_summary=None,
        languages=[],
    )

    summarized = summarizer.summarize(empty_cv)

    assert summarized['summary'] == 'Pat Empty'
    assert summarized['experience'] == []
    assert summarized['skills_extracted'] == []
    assert summarized['education'] == ''
    assert summarized['token_count'] > 0
    assert summarized['was_truncated'] is False
