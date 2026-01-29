"""
FVS Validator Tests.
Validates that the Fact Verification System correctly detects hallucinations.

Per .clauderules: Never mark a task as complete until its unit test passes.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from careervp.logic.fvs_validator import (
    validate_cv_against_baseline,
    validate_immutable_facts,
    validate_verifiable_skills,
    validate_vpr_against_cv,
)
from careervp.models.cv import (
    Certification,
    ContactInfo,
    Education,
    UserCV,
    WorkExperience,
)
from careervp.models.vpr import VPR, EvidenceItem

# Path to fixtures (repo root/tests/fixtures)
FIXTURES_DIR = Path(__file__).resolve().parents[4] / 'tests' / 'fixtures'


@pytest.fixture
def fvs_baseline() -> dict:
    """Load FVS baseline fixture."""
    baseline_path = FIXTURES_DIR / 'fvs_baseline_cv.json'
    with open(baseline_path) as f:
        return json.load(f)


@pytest.fixture
def fvs_hallucination() -> dict:
    """Load FVS hallucination example fixture."""
    hallucination_path = FIXTURES_DIR / 'fvs_test_hallucination.json'
    with open(hallucination_path) as f:
        return json.load(f)


@pytest.fixture
def valid_user_cv() -> UserCV:
    """Create a UserCV that matches the baseline exactly."""
    return UserCV(
        user_id='test-user-123',
        full_name='YITZCHAK MEIROVICH',
        language='en',
        contact_info=ContactInfo(
            phone='052-756-3792',
            email='ymeirovich@presgen.net',
            location='Modiin, Israel',
        ),
        experience=[
            WorkExperience(
                company='SysAid',
                role='Learning Experience Specialist',
                dates='2021 – Present',
                achievements=['Designed training programs'],
            ),
            WorkExperience(
                company='Israel Ministry of Finance',
                role='AWS Solutions Architect',
                dates='2009 – 2021',
                achievements=['Architected cloud solutions'],
            ),
        ],
        education=[
            Education(
                institution='University of Maryland',
                degree='B.A. Political Science',
            ),
        ],
        certifications=[
            Certification(name='AWS Solutions Architect Associate'),
            Certification(name='AWS Certified Developer Associate'),
        ],
        skills=['AWS Solutions Architect Associate', 'Python', 'JavaScript'],
        top_achievements=['Implemented LMS system'],
        is_parsed=True,
    )


@pytest.fixture
def hallucinated_user_cv() -> UserCV:
    """Create a UserCV with hallucinated facts (matches fvs_test_hallucination.json)."""
    return UserCV(
        user_id='test-user-123',
        full_name='YITZCHAK MEIROVICH',
        language='en',
        contact_info=ContactInfo(
            phone='052-756-3792',
            email='ymeirovich@presgen.net',
            location='Modiin, Israel',
        ),
        experience=[
            WorkExperience(
                company='SysAid',
                role='Director of Learning',  # HALLUCINATED: Should be "Learning Experience Specialist"
                dates='2018 – Present',  # HALLUCINATED: Should be "2021 – Present"
                achievements=[],
            ),
        ],
        education=[
            Education(
                institution='Unknown',
                degree='M.S. Computer Science',  # HALLUCINATED: Should be "B.A. Political Science"
            ),
        ],
        certifications=[],
        top_achievements=[],
        skills=['Rust Expert'],  # HALLUCINATED: Not in verifiable skills
        is_parsed=True,
    )


class TestFVSImmutableFactsValidation:
    """Test validation of immutable facts."""

    def test_valid_cv_passes_immutable_check(self, fvs_baseline: dict, valid_user_cv: UserCV):
        """A CV with correct immutable facts should pass validation."""
        result = validate_immutable_facts(fvs_baseline, valid_user_cv)

        assert result.is_valid is True
        assert len(result.violations) == 0
        assert result.has_critical_violations is False

    def test_hallucinated_role_fails(self, fvs_baseline: dict, hallucinated_user_cv: UserCV):
        """A CV with hallucinated job title should fail validation."""
        result = validate_immutable_facts(fvs_baseline, hallucinated_user_cv)

        assert result.is_valid is False
        assert result.has_critical_violations is True

        # Find the role violation
        role_violations = [v for v in result.violations if 'role' in v.field]
        assert len(role_violations) >= 1

        role_violation = role_violations[0]
        assert role_violation.expected == 'Learning Experience Specialist'
        assert role_violation.actual == 'Director of Learning'
        assert role_violation.severity == 'CRITICAL'

    def test_hallucinated_dates_fails(self, fvs_baseline: dict, hallucinated_user_cv: UserCV):
        """A CV with hallucinated dates should fail validation."""
        result = validate_immutable_facts(fvs_baseline, hallucinated_user_cv)

        # Find the dates violation
        dates_violations = [v for v in result.violations if 'dates' in v.field]
        assert len(dates_violations) >= 1

        dates_violation = dates_violations[0]
        assert dates_violation.expected == '2021 – Present'
        assert dates_violation.actual == '2018 – Present'
        assert dates_violation.severity == 'CRITICAL'

    def test_contact_info_change_fails(self, fvs_baseline: dict, valid_user_cv: UserCV):
        """Changing contact info should fail validation."""
        # Modify email
        valid_user_cv.contact_info.email = 'wrong@email.com'

        result = validate_immutable_facts(fvs_baseline, valid_user_cv)

        assert result.is_valid is False
        email_violations = [v for v in result.violations if 'email' in v.field]
        assert len(email_violations) == 1


class TestFVSVerifiableSkillsValidation:
    """Test validation of verifiable skills."""

    def test_valid_skills_pass(self, fvs_baseline: dict, valid_user_cv: UserCV):
        """Skills from the verifiable list should pass."""
        result = validate_verifiable_skills(fvs_baseline, valid_user_cv)

        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_hallucinated_skill_fails(self, fvs_baseline: dict, hallucinated_user_cv: UserCV):
        """Skills not in verifiable list should be flagged."""
        result = validate_verifiable_skills(fvs_baseline, hallucinated_user_cv)

        assert result.is_valid is False
        skill_violations = [v for v in result.violations if v.actual == 'Rust Expert']
        assert len(skill_violations) == 1
        assert skill_violations[0].severity == 'WARNING'


class TestFullFVSValidation:
    """Test complete FVS validation flow."""

    def test_valid_cv_returns_success(self, fvs_baseline: dict, valid_user_cv: UserCV):
        """A fully valid CV should return success Result."""
        result = validate_cv_against_baseline(fvs_baseline, valid_user_cv)

        assert result.success is True
        assert result.code == 'SUCCESS'
        assert result.data is not None
        assert result.data.is_valid is True


class TestVPRValidationAgainstCV:
    """Test VPR-specific IMMUTABLE validation."""

    @pytest.fixture
    def aligned_vpr(self, valid_user_cv: UserCV) -> VPR:
        """Build a VPR aligned with the user's CV facts."""
        return VPR(
            application_id='app-123',
            user_id=valid_user_cv.user_id,
            executive_summary='SysAid impact narrative.',
            evidence_matrix=[
                EvidenceItem(
                    requirement='Leadership',
                    evidence='Led enablement at SysAid during 2021 delivering results.',
                    alignment_score='STRONG',
                    impact_potential='Immediate readiness.',
                )
            ],
            differentiators=['Trusted partner at SysAid across 2021 initiatives.'],
            gap_strategies=[],
            cultural_fit='Values-first.',
            talking_points=['Discuss leadership as Learning Experience Specialist.'],
            keywords=['Enablement'],
            version=1,
            language='en',
            created_at=datetime.utcnow(),
            word_count=0,
        )

    def test_vpr_validation_passes_when_facts_align(self, aligned_vpr: VPR, valid_user_cv: UserCV):
        """VPR referencing only CV facts should pass."""
        result = validate_vpr_against_cv(aligned_vpr, valid_user_cv)

        assert result.success is True
        assert result.code == 'SUCCESS'
        assert result.data is not None
        assert result.data.is_valid is True

    def test_vpr_validation_detects_unknown_company(self, aligned_vpr: VPR, valid_user_cv: UserCV):
        """Referencing a company not in the CV should fail."""
        aligned_vpr.evidence_matrix[0].evidence = 'Led enablement at Fictional Labs between 2021 and 2022.'

        result = validate_vpr_against_cv(aligned_vpr, valid_user_cv)

        assert result.success is False
        assert result.code == 'FVS_HALLUCINATION_DETECTED'
        assert result.data is not None
        assert any(v.actual == 'Fictional Labs' for v in result.data.violations)

    def test_vpr_validation_detects_unknown_dates(self, aligned_vpr: VPR, valid_user_cv: UserCV):
        """Referencing dates not present in CV should fail."""
        aligned_vpr.differentiators[0] = 'Managed programs at SysAid from 2015 to 2016.'

        result = validate_vpr_against_cv(aligned_vpr, valid_user_cv)

        assert result.success is False
        assert result.code == 'FVS_HALLUCINATION_DETECTED'
        assert result.data is not None
        assert any(v.field == 'vpr.dates' for v in result.data.violations)

    def test_vpr_validation_detects_unknown_title(self, aligned_vpr: VPR, valid_user_cv: UserCV):
        """Referencing a job title not in CV should fail."""
        aligned_vpr.talking_points[0] = 'Discuss time serving as Chief Visionary Officer.'

        result = validate_vpr_against_cv(aligned_vpr, valid_user_cv)

        assert result.success is False
        assert result.code == 'FVS_HALLUCINATION_DETECTED'
        assert result.data is not None
        assert any('Chief Visionary Officer' in v.actual for v in result.data.violations)

    def test_hallucinated_cv_returns_failure(self, fvs_baseline: dict, hallucinated_user_cv: UserCV):
        """A CV with hallucinations should return failure Result."""
        result = validate_cv_against_baseline(fvs_baseline, hallucinated_user_cv)

        assert result.success is False
        assert result.code == 'FVS_HALLUCINATION_DETECTED'
        assert result.error is not None
        assert 'immutable fact violations' in result.error.lower()


class TestFVSFixtureIntegrity:
    """Test that fixtures are properly structured."""

    def test_baseline_fixture_has_required_fields(self, fvs_baseline: dict):
        """Baseline fixture should have all required FVS fields."""
        assert 'full_name' in fvs_baseline
        assert 'immutable_facts' in fvs_baseline
        assert 'verifiable_skills' in fvs_baseline

        immutable = fvs_baseline['immutable_facts']
        assert 'contact_info' in immutable
        assert 'work_history' in immutable
        assert 'education' in immutable

    def test_hallucination_fixture_has_violations(self, fvs_hallucination: dict):
        """Hallucination fixture should contain known violations."""
        tailored = fvs_hallucination['tailored_cv_output']

        # Should have wrong role
        assert tailored['experience'][0]['role'] == 'Director of Learning'

        # Should have wrong dates
        assert tailored['experience'][0]['dates'] == '2018 – Present'

        # Should have wrong degree
        assert tailored['education'][0]['degree'] == 'M.S. Computer Science'

        # Should have hallucinated skill
        assert 'Rust Expert' in tailored['skills']
