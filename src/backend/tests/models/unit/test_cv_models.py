from __future__ import annotations

from careervp.models import cv as cv_models_primary
from careervp.models import cv_models as cv_models_compat


def test_cv_section_exists_and_expected_values() -> None:
    expected = {
        'professional_summary',
        'work_experience',
        'education',
        'skills',
        'certifications',
        'languages',
    }
    assert {section.value for section in cv_models_primary.CVSection} == expected


def test_cv_models_module_is_importable() -> None:
    assert cv_models_compat is not None


def test_cv_models_reexport_identity_matches_canonical_module() -> None:
    assert cv_models_compat.UserCV is cv_models_primary.UserCV
    assert cv_models_compat.WorkExperience is cv_models_primary.WorkExperience
    assert cv_models_compat.Education is cv_models_primary.Education
    assert cv_models_compat.Skill is cv_models_primary.Skill
    assert cv_models_compat.SkillLevel is cv_models_primary.SkillLevel


def test_work_experience_populates_dates() -> None:
    model = cv_models_primary.WorkExperience(
        company='Acme',
        role='Engineer',
        start_date='2022-01',
        end_date='2024-01',
    )
    assert model.dates == '2022-01-2024-01'


def test_education_populates_dates() -> None:
    model = cv_models_primary.Education(institution='Uni', degree='BSc', end_date='2020')
    assert model.dates == '2020'


def test_user_cv_accepts_work_experience_alias() -> None:
    model = cv_models_primary.UserCV(
        user_id='u1',
        full_name='Jane Doe',
        work_experience=[{'company': 'Acme', 'role': 'Engineer'}],
    )
    assert len(model.work_experience) == 1
    assert model.work_experience[0].company == 'Acme'


def test_user_cv_serializes_skills_as_names() -> None:
    model = cv_models_primary.UserCV(
        user_id='u1',
        full_name='Jane Doe',
        skills=[cv_models_primary.Skill(name='Python'), 'AWS'],
    )
    assert model.model_dump(mode='json')['skills'] == ['Python', 'AWS']
