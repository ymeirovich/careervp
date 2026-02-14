from __future__ import annotations

import pytest
from pydantic import ValidationError

from careervp.models import cv as cv_models_primary
from careervp.models import cv_models as cv_models_compat


def test_cv_section_enum_contains_expected_sections() -> None:
    expected = {
        'professional_summary',
        'work_experience',
        'education',
        'skills',
        'certifications',
        'languages',
    }
    assert {section.value for section in cv_models_primary.CVSection} == expected


def test_skill_is_frozen() -> None:
    skill = cv_models_primary.Skill(name='Python')
    with pytest.raises(ValidationError):
        skill.name = 'Go'  # type: ignore[misc]


def test_work_experience_populates_dates_from_start_and_end() -> None:
    model = cv_models_primary.WorkExperience(
        company='Acme',
        role='Engineer',
        start_date='2022-01',
        end_date='2024-01',
    )
    assert model.dates == '2022-01-2024-01'


def test_education_populates_dates_from_end_only() -> None:
    model = cv_models_primary.Education(institution='Uni', degree='BSc', end_date='2020')
    assert model.dates == '2020'


def test_certification_syncs_issuer_aliases() -> None:
    cert = cv_models_primary.Certification(name='AWS SA', issuing_organization='AWS', date='2024-01')
    assert cert.issuer == 'AWS'
    assert cert.issue_date == '2024-01'


def test_user_cv_syncs_contact_info_to_top_level() -> None:
    user_cv = cv_models_primary.UserCV(
        user_id='u1',
        full_name='Jane Doe',
        contact_info=cv_models_primary.ContactInfo(email='jane@example.com', phone='123'),
    )
    assert str(user_cv.email) == 'jane@example.com'
    assert user_cv.phone == '123'


def test_user_cv_serializes_skill_objects_as_names() -> None:
    user_cv = cv_models_primary.UserCV(
        user_id='u1',
        full_name='Jane Doe',
        skills=[cv_models_primary.Skill(name='Python'), 'AWS'],
    )
    dumped = user_cv.model_dump(mode='json')
    assert dumped['skills'] == ['Python', 'AWS']


def test_user_cv_accepts_work_experience_alias_field() -> None:
    user_cv = cv_models_primary.UserCV(
        user_id='u1',
        full_name='Jane Doe',
        work_experience=[{'company': 'Acme', 'role': 'Engineer'}],
    )
    assert len(user_cv.work_experience) == 1
    assert user_cv.work_experience[0].company == 'Acme'


def test_cv_models_module_reexports_primary_cv_models() -> None:
    assert cv_models_compat.UserCV is cv_models_primary.UserCV
    assert cv_models_compat.WorkExperience is cv_models_primary.WorkExperience
    assert cv_models_compat.Certification is cv_models_primary.Certification
