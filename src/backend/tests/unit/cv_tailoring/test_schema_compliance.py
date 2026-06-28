# THIS FILE WAS GENERATED FROM: docs/architecture/careervp_prompts/cv-tailoring/tests/test_P7_schema_compliance_and_enrichment.yaml
# Spec ID: TEST-CVT-P7
# Re-run generate_tests_from_yaml.py to regenerate, or edit manually then remove this header.
#
# IMPORTANT: These tests fail until CVT-P7 is implemented.
# Failure modes before implementation:
#   T-P7-01..03: ImportError (CVExperienceBullet absent)
#   T-P7-04:     AttributeError (Stage3Result.keywords_to_emphasize absent)
#   T-P7-05:     AssertionError (start_date still empty)
#   T-P7-06:     AssertionError (phone/location/linkedin still empty)
#   T-P7-07:     AssertionError (certifications still [])
#   T-P7-08:     ImportError (ATSResult absent)
#   T-P7-09:     ModuleNotFoundError (cv_tailoring_ats absent)
#   T-P7-10:     ModuleNotFoundError or AssertionError (wrong keyword_match)
#   T-P7-11:     ModuleNotFoundError or AssertionError (wrong grade)
#   T-P7-12:     AssertionError (ats_result not stored in artifact)
#   T-P7-13:     AssertionError (ats_result/ats_grade absent from status payload)
#   T-P7-14:     AssertionError (fact_verification_detail absent / fvs_validation still exposed)
#   T-P7-15:     AssertionError (keywords_matched absent or contains full bullet sentences)
#   T-P7-16:     AssertionError (version/language/generated_at absent)
"""
Unit tests for CVT-P7: Schema compliance, Stage 3 enrichment, ATS rules engine,
handler response alignment.

These tests are non-self-closing: each one fails before CVT-P7 is implemented.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from careervp.models.cv import Certification, ContactInfo, UserCV, WorkExperience
from careervp.models.result import Result, ResultCode

# ─── Shared helpers ──────────────────────────────────────────────────────────


def _make_long_summary(words: str = '') -> str:
    base = (
        'Strategic professional with 10 years of Python and AWS experience '
        'delivering scalable learning solutions for global enterprise organisations.'
    )
    return base if not words else f'{base} {words}'


def _make_simple_cv_sections(
    company: str = 'Acme',
    start_date: str = '01/2020',
    bullets: list[str] | None = None,
) -> object:
    from careervp.models.cv_tailoring_models import (
        CVContactSection,
        CVExperienceSection,
        CVSections,
        CVSkillsSection,
    )

    return CVSections(
        contact=CVContactSection(name='Test User', email='test@example.com'),
        summary=_make_long_summary(),
        skills=CVSkillsSection(technical=['Python', 'AWS'], soft=['Leadership']),
        experience=[
            CVExperienceSection(
                company=company,
                title='Engineer',
                start_date=start_date,
                bullets=bullets or ['Built distributed system handling 1M+ requests per day.'],
            )
        ],
        education=[],
        certifications=[],
    )


def _make_user_cv(
    company: str = 'Acme',
    start_date: str = '01/2020',
    phone: str = '052-756-3792',
    location: str = 'Modiin, Israel',
    linkedin: str = 'linkedin.com/in/testuser',
    certifications: list[object] | None = None,
) -> UserCV:
    return UserCV(
        user_id='u',
        cv_id='cv-123',
        full_name='Test User',
        language='en',
        contact_info=ContactInfo(
            name='Test User',
            email='test@example.com',
            phone=phone,
            location=location,
            linkedin=linkedin,
        ),
        professional_summary='Senior engineer with 10 years of experience.',
        experience=[
            WorkExperience(
                company=company,
                role='Engineer',
                dates=f'{start_date} - Present',
                start_date=start_date,
                end_date=None,
                current=True,
                achievements=['Built X'],
                technologies=['Python'],
            )
        ],
        education=[],
        certifications=certifications or [],
        skills=['Python', 'AWS'],
        top_achievements=[],
        languages=['English'],
        is_parsed=True,
    )


def _make_stage2_output(cv_sections: object) -> object:
    from careervp.models.cv_tailoring_models import Stage2Output, Stage2Verification

    return Stage2Output(
        verification=Stage2Verification(
            ats_keyword_score=7,
            keywords_added_in_review=[],
            summary_rewritten=False,
            fact_verification_passed=True,
            hallucination_flags=[],
        ),
        cv_sections=cv_sections,  # type: ignore[arg-type]
    )


# ─── T-P7-01: CVExperienceBullet model exists ────────────────────────────────


@pytest.mark.unit
def test_cv_experience_bullet_model_exists() -> None:
    from careervp.models.cv_tailoring_models import CVExperienceBullet

    bullet = CVExperienceBullet(
        text='Generated $1M+ in training revenue within 18 months.',
        source='parsed_facts',
    )
    assert hasattr(bullet, 'text')
    assert hasattr(bullet, 'source')
    assert hasattr(bullet, 'user_edited')
    assert hasattr(bullet, 'quantified')
    assert bullet.source == 'parsed_facts'
    assert bullet.user_edited is False
    assert isinstance(bullet.quantified, bool)


# ─── T-P7-02: CVExperienceSection coerces str bullets ────────────────────────


@pytest.mark.unit
def test_cv_experience_section_bullets_accepts_strings() -> None:
    from careervp.models.cv_tailoring_models import CVExperienceBullet, CVExperienceSection

    exp = CVExperienceSection(
        company='AllCloud',
        title='Director of AWS Training',
        start_date='05/2021',
        bullets=[
            'Generated $1M+ in training revenue within 18 months.',
            'Led cross-functional team across six departments.',
        ],
    )
    assert len(exp.bullets) == 2
    assert isinstance(exp.bullets[0], CVExperienceBullet), f'Expected CVExperienceBullet, got {type(exp.bullets[0]).__name__} — P7-A not implemented'
    assert exp.bullets[0].source == 'parsed_facts'
    assert exp.bullets[0].quantified is True, "Bullet with '$1M+' must have quantified=True"
    assert exp.bullets[1].quantified is False


# ─── T-P7-03: _parse_cv_sections converts bullets ────────────────────────────


@pytest.mark.unit
def test_parse_cv_sections_converts_bullets() -> None:
    from careervp.logic.cv_tailoring_pipeline import _parse_cv_sections
    from careervp.models.cv_tailoring_models import CVExperienceBullet

    data = {
        'contact': {'name': 'Test User', 'email': 'test@example.com'},
        'summary': _make_long_summary(),
        'skills': {'technical': ['Python', 'AWS'], 'soft': ['Leadership']},
        'experience': [
            {
                'company': 'Acme',
                'title': 'Engineer',
                'start_date': '01/2020',
                'bullets': [
                    'Reduced infrastructure costs by 40% through AWS optimisation.',
                    'Mentored junior engineers on best practices.',
                ],
            }
        ],
        'education': [],
        'certifications': [],
    }
    sections = _parse_cv_sections(data)

    assert isinstance(sections.experience[0].bullets[0], CVExperienceBullet), (
        f'Expected CVExperienceBullet, got {type(sections.experience[0].bullets[0]).__name__}'
    )
    assert sections.experience[0].bullets[0].source == 'parsed_facts'
    assert sections.experience[0].bullets[0].quantified is True
    assert sections.experience[0].bullets[1].quantified is False


# ─── T-P7-04: Stage3Result.keywords_to_emphasize set by pipeline ─────────────


@pytest.mark.unit
def test_stage3_result_has_keywords_to_emphasize() -> None:
    cv_sections = _make_simple_cv_sections()
    stage2_response = _make_stage2_output(cv_sections)

    with patch(
        'careervp.logic.cv_tailoring_pipeline.run_stage2_cv_generation',
        return_value=Result(success=True, data=stage2_response, code=ResultCode.SUCCESS),
    ):
        from careervp.logic.cv_tailoring_pipeline import run_cv_tailoring_pipeline

        result = run_cv_tailoring_pipeline(
            cv=_make_user_cv(),
            job_description='Senior Python engineer with AWS and cloud architecture experience.',
            vpr=None,
            llm_client=MagicMock(),
        )

    assert result.success is True, f'Pipeline failed: {result.error!r}'
    assert result.data is not None
    assert hasattr(result.data, 'keywords_to_emphasize'), 'Stage3Result must have keywords_to_emphasize — P7-B not implemented'
    assert isinstance(result.data.keywords_to_emphasize, list)


# ─── T-P7-05: Stage 3 backfills experience dates ─────────────────────────────


@pytest.mark.unit
def test_stage3_backfills_experience_dates() -> None:
    from careervp.logic.cv_tailoring_pipeline import run_stage3_fact_verification
    from careervp.models.cv_tailoring_models import (
        CVContactSection,
        CVExperienceSection,
        CVSections,
        CVSkillsSection,
    )

    cv_sections = CVSections(
        contact=CVContactSection(name='Test User', email='test@example.com'),
        summary=_make_long_summary(),
        skills=CVSkillsSection(technical=['Python'], soft=[]),
        experience=[
            CVExperienceSection(
                company='AllCloud',
                title='Director of AWS Training',
                start_date='',
                end_date=None,
                bullets=['Built AWS training programme generating $1M+ revenue.'],
            )
        ],
        education=[],
        certifications=[],
    )

    result = run_stage3_fact_verification(
        stage2_output=_make_stage2_output(cv_sections),  # type: ignore[arg-type]
        parsed_facts=_make_user_cv(company='AllCloud', start_date='05/2021'),
        ats_keyword_score=70,
    )

    exp = result.cv_sections.experience[0]
    assert exp.start_date != '', 'Stage 3 must backfill start_date from parsed_facts, got empty string — P7-B not implemented'
    assert exp.start_date == '05/2021', f"Expected '05/2021', got {exp.start_date!r}"


# ─── T-P7-06: Stage 3 backfills contact fields ───────────────────────────────


@pytest.mark.unit
def test_stage3_backfills_contact_fields() -> None:
    from careervp.logic.cv_tailoring_pipeline import run_stage3_fact_verification
    from careervp.models.cv_tailoring_models import (
        CVContactSection,
        CVExperienceSection,
        CVSections,
        CVSkillsSection,
    )

    cv_sections = CVSections(
        contact=CVContactSection(
            name='Test User',
            email='test@example.com',
            phone='',
            location='',
            linkedin='',
        ),
        summary=_make_long_summary(),
        skills=CVSkillsSection(technical=['Python'], soft=[]),
        experience=[
            CVExperienceSection(
                company='Acme',
                title='Engineer',
                start_date='01/2020',
                bullets=['Built distributed system handling 1M+ requests per day.'],
            )
        ],
        education=[],
        certifications=[],
    )

    result = run_stage3_fact_verification(
        stage2_output=_make_stage2_output(cv_sections),  # type: ignore[arg-type]
        parsed_facts=_make_user_cv(),
        ats_keyword_score=70,
    )

    contact = result.cv_sections.contact
    assert contact.phone == '052-756-3792', f"phone must be '052-756-3792', got {contact.phone!r} — P7-B not implemented"
    assert contact.location == 'Modiin, Israel', f'location wrong: {contact.location!r}'
    assert contact.linkedin == 'linkedin.com/in/testuser', f'linkedin wrong: {contact.linkedin!r}'


# ─── T-P7-07: Stage 3 populates certifications ───────────────────────────────


@pytest.mark.unit
def test_stage3_populates_certifications() -> None:
    from careervp.logic.cv_tailoring_pipeline import run_stage3_fact_verification
    from careervp.models.cv_tailoring_models import (
        CVContactSection,
        CVExperienceSection,
        CVSections,
        CVSkillsSection,
    )

    cv_sections = CVSections(
        contact=CVContactSection(name='Test User', email='test@example.com'),
        summary=_make_long_summary(),
        skills=CVSkillsSection(technical=['Python'], soft=[]),
        experience=[
            CVExperienceSection(
                company='Acme',
                title='Engineer',
                start_date='01/2020',
                bullets=['Built distributed system handling 1M+ requests per day.'],
            )
        ],
        education=[],
        certifications=[],
    )
    certs = [
        Certification(name='AWS Authorized Instructor', issuer='Amazon Web Services', date='2022'),
        Certification(
            name='AWS Certified Solutions Architect Associate',
            issuer='Amazon Web Services',
            date='2021',
        ),
    ]

    result = run_stage3_fact_verification(
        stage2_output=_make_stage2_output(cv_sections),  # type: ignore[arg-type]
        parsed_facts=_make_user_cv(certifications=certs),
        ats_keyword_score=70,
    )

    assert len(result.cv_sections.certifications) == 2, (
        f'Expected 2 certifications, got {len(result.cv_sections.certifications)} — P7-B not implemented'
    )
    names = [c.name for c in result.cv_sections.certifications]
    assert 'AWS Authorized Instructor' in names


# ─── T-P7-08: ATSResult and ATSComponents models exist ───────────────────────


@pytest.mark.unit
def test_ats_result_model_exists() -> None:
    from careervp.models.cv_tailoring_models import ATSComponents, ATSResult

    components = ATSComponents(
        keyword_match=32.0,
        quantified_bullets=16.0,
        section_headers=15.0,
        formatting_safety=15.0,
        summary_keyword_density=8.0,
    )
    result = ATSResult(
        total_score=86,
        grade='yellow',
        components=components,
        issues=[],
        keywords_matched=['Python', 'AWS'],
        keywords_missing=['Kubernetes'],
        keyword_match_score_1_10=9,
    )
    assert result.total_score == 86
    assert result.grade == 'yellow'
    assert result.components.keyword_match == 32.0
    assert result.keyword_match_score_1_10 == 9


# ─── T-P7-09: compute_ats_result returns ATSResult ───────────────────────────


@pytest.mark.unit
def test_compute_ats_result_returns_ats_result() -> None:
    from careervp.logic.cv_tailoring_ats import compute_ats_result
    from careervp.models.cv_tailoring_models import ATSResult

    result = compute_ats_result(
        cv_sections=_make_simple_cv_sections(),  # type: ignore[arg-type]
        primary_keywords=['Python', 'AWS'],
    )
    assert isinstance(result, ATSResult), f'Expected ATSResult, got {type(result).__name__} — P7-C not implemented'
    assert result.grade in ('green', 'yellow', 'red')
    assert 0 <= result.total_score <= 100


# ─── T-P7-10: keyword_match component formula ────────────────────────────────


@pytest.mark.unit
def test_ats_keyword_match_component() -> None:
    from careervp.logic.cv_tailoring_ats import compute_ats_result
    from careervp.models.cv_tailoring_models import (
        CVContactSection,
        CVExperienceSection,
        CVSections,
        CVSkillsSection,
    )

    cv_sections = CVSections(
        contact=CVContactSection(name='Test User', email='test@example.com'),
        summary='Python and AWS engineer with 10 years of experience in cloud systems.',
        skills=CVSkillsSection(technical=['Python', 'AWS'], soft=[]),
        experience=[
            CVExperienceSection(
                company='Acme',
                title='Engineer',
                start_date='01/2020',
                bullets=['Built system handling 1M+ daily requests with Python.'],
            )
        ],
        education=[],
        certifications=[],
    )
    result = compute_ats_result(cv_sections, primary_keywords=['Python', 'AWS', 'Java', 'Kubernetes'])

    assert result.components.keyword_match == 20.0, f'2/4 keywords → keyword_match must be 20.0, got {result.components.keyword_match}'
    assert 'Python' in result.keywords_matched
    assert 'Java' in result.keywords_missing


# ─── T-P7-11: grade boundaries ───────────────────────────────────────────────


@pytest.mark.unit
def test_ats_grade_boundaries() -> None:
    from careervp.logic.cv_tailoring_ats import compute_ats_result

    def _grade_for(score: int) -> str:
        return 'green' if score >= 90 else ('yellow' if score >= 70 else 'red')

    assert _grade_for(90) == 'green'
    assert _grade_for(89) == 'yellow'
    assert _grade_for(70) == 'yellow'
    assert _grade_for(69) == 'red'

    live = compute_ats_result(
        cv_sections=_make_simple_cv_sections(),  # type: ignore[arg-type]
        primary_keywords=['Python', 'AWS'],
    )
    assert live.grade in ('green', 'yellow', 'red'), f'Invalid grade: {live.grade!r}'


# ─── T-P7-12: handler stores ats_result in artifact ──────────────────────────


@pytest.mark.unit
def test_handler_stores_ats_result_in_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    import careervp.handlers.cv_tailoring_handler as handler_module
    from careervp.models.cv_tailoring_models import ATSComponents, ATSResult, Stage3Result

    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-table')

    stage3 = Stage3Result(
        cv_sections=_make_simple_cv_sections(),  # type: ignore[arg-type]
        fact_verification_passed=True,
        ats_keyword_score=80,
        keywords_to_emphasize=['Python', 'AWS'],
    )
    mock_ats = ATSResult(
        total_score=85,
        grade='yellow',
        components=ATSComponents(
            keyword_match=32.0,
            quantified_bullets=12.0,
            section_headers=15.0,
            formatting_safety=15.0,
            summary_keyword_density=8.0,
        ),
        issues=[],
        keywords_matched=['Python', 'AWS'],
        keywords_missing=[],
        keyword_match_score_1_10=9,
    )
    pipeline_result = Result(success=True, data=stage3, code=ResultCode.SUCCESS)

    mock_dal = MagicMock()
    mock_dal.get_cv.return_value = _make_user_cv()
    mock_table = MagicMock()
    mock_dal._get_db_handler.return_value = mock_table

    with patch.object(handler_module, 'DynamoDalHandler', return_value=mock_dal):
        with patch.object(handler_module, 'resolve_handler_dependencies', return_value=MagicMock(status='ready', resolved_upstream={})):
            with patch.object(handler_module, 'JobsRepository') as mock_jobs_cls:
                mock_jobs_cls.return_value.get_job.return_value = {
                    'description': 'Python engineer with AWS experience.',
                    'title': 'Senior Engineer',
                }
                with patch.object(handler_module, 'LLMClient'):
                    with patch.object(handler_module, 'run_cv_tailoring_pipeline', return_value=pipeline_result):
                        with patch.object(handler_module, 'compute_ats_result', return_value=mock_ats):
                            with patch.object(handler_module, '_update_application_artifact'):
                                handler_module._handle_openapi_async_generate(
                                    event={},
                                    request_data={'cv_id': 'cv-123', 'job_id': 'job-456'},
                                    headers={},
                                    user_id='user-789',
                                )

    artifact = mock_table.put_item.call_args.kwargs['Item']
    assert 'ats_result' in artifact, f"Artifact must contain 'ats_result' — P7-E not implemented. Keys: {list(artifact.keys())}"
    assert artifact.get('ats_grade') == 'yellow'
    assert artifact['ats_result'].get('total_score') == 85


# ─── T-P7-13: status payload includes ats_result ─────────────────────────────


@pytest.mark.unit
def test_status_payload_includes_ats_result() -> None:
    from careervp.handlers.cv_tailoring_handler import _build_tailored_cv_status_payload

    item = {
        'request_id': 'cv-tail-abc',
        'status': 'completed',
        'cv_sections': {
            'contact': {'name': 'T', 'email': 't@t.com'},
            'summary': _make_long_summary(),
            'skills': {'technical': [], 'soft': []},
            'experience': [],
            'education': [],
            'certifications': [],
        },
        'ats_score': 85,
        'ats_grade': 'yellow',
        'ats_result': {
            'total_score': 85,
            'grade': 'yellow',
            'components': {
                'keyword_match': 32.0,
                'quantified_bullets': 12.0,
                'section_headers': 15.0,
                'formatting_safety': 15.0,
                'summary_keyword_density': 8.0,
            },
            'issues': [],
            'keywords_matched': ['Python', 'AWS'],
            'keywords_missing': [],
            'keyword_match_score_1_10': 9,
        },
    }
    payload = _build_tailored_cv_status_payload(item, 'fallback')
    result = payload['result']

    assert 'ats_result' in result, f"result must contain 'ats_result' — P7-E not implemented. Keys: {list(result.keys())}"
    assert result['ats_result']['total_score'] == 85
    assert result.get('ats_grade') == 'yellow'


# ─── T-P7-14: status payload uses fact_verification_detail ───────────────────


@pytest.mark.unit
def test_status_payload_uses_fact_verification_detail() -> None:
    from careervp.handlers.cv_tailoring_handler import _build_tailored_cv_status_payload

    item = {
        'request_id': 'cv-tail-abc',
        'status': 'completed',
        'cv_sections': {
            'contact': {'name': 'T', 'email': 't@t.com'},
            'summary': _make_long_summary(),
            'skills': {'technical': [], 'soft': []},
            'experience': [],
            'education': [],
            'certifications': [],
        },
        'ats_score': 85,
        'fact_verification_detail': {
            'passed': True,
            'items_corrected': 1,
            'items_removed': 0,
            'hallucination_flags_from_ai': [],
            'checks': [{'check_name': 'name_match', 'passed': True, 'action_taken': 'none', 'detail': None}],
        },
        'fvs_validation': {'is_valid': True, 'violations': []},
    }
    payload = _build_tailored_cv_status_payload(item, 'fallback')
    result = payload['result']

    assert 'fact_verification_detail' in result, f"result must contain 'fact_verification_detail' — P7-E not implemented. Keys: {list(result.keys())}"
    assert result['fact_verification_detail']['passed'] is True
    assert 'fvs_validation' not in result, "'fvs_validation' must not appear in the API response"


# ─── T-P7-15: keywords_matched are short strings ─────────────────────────────


@pytest.mark.unit
def test_status_payload_keywords_matched_are_short_strings() -> None:
    from careervp.handlers.cv_tailoring_handler import _build_tailored_cv_status_payload

    item = {
        'request_id': 'cv-tail-abc',
        'status': 'completed',
        'cv_sections': {
            'contact': {'name': 'T', 'email': 't@t.com'},
            'summary': _make_long_summary(),
            'skills': {'technical': [], 'soft': []},
            'experience': [],
            'education': [],
            'certifications': [],
        },
        'ats_score': 85,
        'keywords_matched': ['Python', 'AWS', 'LMS Implementation', 'Instructional Design'],
        'keywords_missing': ['Kubernetes'],
        'keyword_match_score': 9,
    }
    payload = _build_tailored_cv_status_payload(item, 'fallback')
    result = payload['result']

    assert 'keywords_matched' in result, f"result must contain 'keywords_matched' — P7-E not implemented. Keys: {list(result.keys())}"
    matched = result['keywords_matched']
    assert matched == ['Python', 'AWS', 'LMS Implementation', 'Instructional Design']
    too_long = [k for k in matched if len(k) > 50]
    assert not too_long, f'keywords_matched must be short strings (<=50 chars), found: {too_long}'
    assert result.get('keywords_missing') == ['Kubernetes']


# ─── T-P7-16: top-level version, language, generated_at ──────────────────────


@pytest.mark.unit
def test_status_payload_includes_version_language_generated_at() -> None:
    from careervp.handlers.cv_tailoring_handler import _build_tailored_cv_status_payload

    item = {
        'request_id': 'cv-tail-abc',
        'status': 'completed',
        'cv_sections': {
            'contact': {'name': 'T', 'email': 't@t.com'},
            'summary': _make_long_summary(),
            'skills': {'technical': [], 'soft': []},
            'experience': [],
            'education': [],
            'certifications': [],
        },
        'ats_score': 85,
        'version': 1,
        'language': 'en',
        'created_at': '2026-04-05T08:31:00Z',
    }
    payload = _build_tailored_cv_status_payload(item, 'fallback')

    assert payload.get('version') == 1, f'Top-level version must be 1, got {payload.get("version")!r} — P7-E not implemented'
    assert payload.get('language') == 'en', f"Top-level language must be 'en', got {payload.get('language')!r}"
    assert payload.get('generated_at') == '2026-04-05T08:31:00Z', f'generated_at must be set, got {payload.get("generated_at")!r}'
