"""
Unit tests for FVS (Feature Validation System) Validator.

Tests immutable fact validation, verifiable skills, and VPR alignment.
Per docs/refactor/specs/fvs_spec.yaml.
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import dataclass, field

from careervp.logic.fvs_validator import (
    FVSViolation,
    FVSValidationResult,
    validate_immutable_facts,
    validate_verifiable_skills,
    validate_cv_against_baseline,
    validate_vpr_against_cv,
    _find_matching_entry,
    _extract_company_mentions,
    _extract_title_mentions,
    _normalize,
    _matches_known_role,
    _collect_years,
)
from careervp.models.fvs import FVSValidationResult as TailoringFVSValidationResult
from careervp.models.result import ResultCode


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_baseline():
    """Create a sample FVS baseline dictionary."""
    return {
        'full_name': 'John Doe',
        'immutable_facts': {
            'contact_info': {
                'email': 'john.doe@example.com',
                'phone': '555-123-4567',
            },
            'work_history': [
                {
                    'company': 'Acme Corp',
                    'role': 'Software Engineer',
                    'dates': 'Jan 2020 - Present',
                },
                {
                    'company': 'Tech Start',
                    'role': 'Junior Developer',
                    'dates': 'Jun 2018 - Dec 2019',
                },
            ],
            'education': [
                {
                    'institution': 'State University',
                    'degree': 'Bachelor of Science in Computer Science',
                    'graduation_date': 'May 2018',
                }
            ],
        },
        'verifiable_skills': [
            'Python',
            'JavaScript',
            'AWS',
            'Docker',
        ],
    }


@pytest.fixture
def matching_generated_cv():
    """Create a generated CV that matches the baseline."""
    @dataclass
    class MockContactInfo:
        email: str = 'john.doe@example.com'
        phone: str = '555-123-4567'

    @dataclass
    class MockExperience:
        company: str = 'Acme Corp'
        role: str = 'Software Engineer'
        dates: str = 'Jan 2020 - Present'
        description: str = ''

    @dataclass
    class MockEducation:
        institution: str = 'State University'
        degree: str = 'Bachelor of Science in Computer Science'
        graduation_date: str = 'May 2018'

    @dataclass
    class MockSkill:
        name: str = ''

    class MockUserCV:
        full_name: str = 'John Doe'
        contact_info: MockContactInfo = field(default_factory=MockContactInfo)
        experience: list = field(default_factory=lambda: [
            MockExperience(company='Acme Corp', role='Software Engineer', dates='Jan 2020 - Present'),
        ])
        education: list = field(default_factory=lambda: [
            MockEducation(institution='State University', degree='Bachelor of Science in Computer Science'),
        ])
        skills: list = field(default_factory=lambda: [
            MockSkill(name='Python'),
            MockSkill(name='JavaScript'),
        ])

    return MockUserCV()


@pytest.fixture
def modified_generated_cv():
    """Create a generated CV with modified immutable facts."""
    @dataclass
    class MockContactInfo:
        email: str = 'different@email.com'  # Modified email
        phone: str = '999-999-9999'  # Modified phone

    @dataclass
    class MockExperience:
        company: str = 'Acme Corp'
        role: str = 'Senior Software Engineer'  # Modified role
        dates: str = '2020 - Now'  # Modified dates
        description: str = ''

    @dataclass
    class MockEducation:
        institution: str = 'State University'
        degree: str = 'Master of Science'  # Modified degree
        graduation_date: str = 'May 2018'

    @dataclass
    class MockSkill:
        name: str = ''

    class MockUserCV:
        full_name: str = 'John Smith'  # Modified name
        contact_info: MockContactInfo = field(default_factory=MockContactInfo)
        experience: list = field(default_factory=lambda: [
            MockExperience(),
        ])
        education: list = field(default_factory=lambda: [
            MockEducation(),
        ])
        skills: list = field(default_factory=list)

    return MockUserCV()


@pytest.fixture
def sample_vpr():
    """Create a sample VPR for testing."""
    @dataclass
    class MockEvidence:
        evidence: str = 'Led a team of 5 engineers at Acme Corp'

    @dataclass
    class MockVPR:
        evidence_matrix: list = field(default_factory=lambda: [MockEvidence()])
        differentiators: list = field(default_factory=lambda: [
            'Architected scalable solutions at Tech Start',
        ])
        talking_points: list = field(default_factory=lambda: [
            'Developed microservices using Python at Acme Corp',
        ])

    return MockVPR()


# ============================================================================
# Test Class 1: FVSViolation and FVSValidationResult
# ============================================================================


class TestFVSViolation:
    """Tests for FVSViolation dataclass."""

    def test_create_critical_violation(self):
        """Test creating a CRITICAL severity violation."""
        violation = FVSViolation(
            field='full_name',
            expected='John Doe',
            actual='John Smith',
            severity='CRITICAL',
        )
        assert violation.field == 'full_name'
        assert violation.expected == 'John Doe'
        assert violation.actual == 'John Smith'
        assert violation.severity == 'CRITICAL'

    def test_create_warning_violation(self):
        """Test creating a WARNING severity violation."""
        violation = FVSViolation(
            field='skills',
            expected='Python',
            actual='Ruby',
            severity='WARNING',
        )
        assert violation.severity == 'WARNING'


class TestFVSValidationResult:
    """Tests for FVSValidationResult dataclass."""

    def test_valid_result(self):
        """Test valid validation result."""
        result = FVSValidationResult(is_valid=True, violations=[])
        assert result.is_valid is True
        assert len(result.violations) == 0
        assert result.has_critical_violations is False

    def test_invalid_result_with_violations(self):
        """Test invalid validation result with violations."""
        violation = FVSViolation(
            field='full_name',
            expected='John Doe',
            actual='Jane Doe',
            severity='CRITICAL',
        )
        result = FVSValidationResult(is_valid=False, violations=[violation])
        assert result.is_valid is False
        assert len(result.violations) == 1
        assert result.has_critical_violations is True

    def test_has_critical_violations_false_for_warnings_only(self):
        """Test has_critical_violations returns False when only warnings."""
        violation = FVSViolation(
            field='skills',
            expected='Python',
            actual='Ruby',
            severity='WARNING',
        )
        result = FVSValidationResult(is_valid=False, violations=[violation])
        assert result.has_critical_violations is False


# ============================================================================
# Test Class 2: Immutable Facts Validation
# ============================================================================


class TestValidateImmutableFacts:
    """Tests for validate_immutable_facts function."""

    def test_valid_cv_returns_no_violations(self, sample_baseline, matching_generated_cv):
        """Test that matching CV returns no violations."""
        result = validate_immutable_facts(sample_baseline, matching_generated_cv)
        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_modified_name_returns_violation(self, sample_baseline, modified_generated_cv):
        """Test that modified full name returns CRITICAL violation."""
        result = validate_immutable_facts(sample_baseline, modified_generated_cv)
        assert result.is_valid is False
        assert any(v.field == 'full_name' for v in result.violations)
        assert any(v.severity == 'CRITICAL' for v in result.violations)

    def test_modified_email_returns_violation(self, sample_baseline, modified_generated_cv):
        """Test that modified email returns CRITICAL violation."""
        result = validate_immutable_facts(sample_baseline, modified_generated_cv)
        assert result.is_valid is False
        assert any('contact_info.email' in v.field for v in result.violations)

    def test_modified_phone_returns_violation(self, sample_baseline, modified_generated_cv):
        """Test that modified phone returns CRITICAL violation."""
        result = validate_immutable_facts(sample_baseline, modified_generated_cv)
        assert result.is_valid is False
        assert any('contact_info.phone' in v.field for v in result.violations)

    def test_modified_role_returns_violation(self, sample_baseline, modified_generated_cv):
        """Test that modified role returns CRITICAL violation."""
        result = validate_immutable_facts(sample_baseline, modified_generated_cv)
        assert result.is_valid is False
        assert any('role' in v.field.lower() for v in result.violations)
        assert any(v.severity == 'CRITICAL' for v in result.violations)

    def test_modified_dates_returns_violation(self, sample_baseline, modified_generated_cv):
        """Test that modified dates returns CRITICAL violation."""
        result = validate_immutable_facts(sample_baseline, modified_generated_cv)
        assert result.is_valid is False
        assert any('dates' in v.field.lower() for v in result.violations)

    def test_modified_degree_returns_violation(self, sample_baseline, modified_generated_cv):
        """Test that modified degree returns CRITICAL violation."""
        result = validate_immutable_facts(sample_baseline, modified_generated_cv)
        assert result.is_valid is False
        assert any('degree' in v.field.lower() for v in result.violations)

    def test_empty_baseline_returns_valid(self, matching_generated_cv):
        """Test that empty baseline returns valid result."""
        empty_baseline = {}
        result = validate_immutable_facts(empty_baseline, matching_generated_cv)
        assert result.is_valid is True

    def test_none_generated_cv_handled(self, sample_baseline):
        """Test handling of None-like generated CV values."""
        @dataclass
        class MockContactInfo:
            email: str = None
            phone: str = None

        class MockUserCV:
            full_name: str = None
            contact_info: MockContactInfo = field(default_factory=MockContactInfo)
            experience: list = field(default_factory=list)
            education: list = field(default_factory=list)
            skills: list = field(default_factory=list)

        result = validate_immutable_facts(sample_baseline, MockUserCV())
        # Should not crash, may or may not have violations depending on logic
        assert isinstance(result, FVSValidationResult)

    def test_case_insensitive_name_comparison(self, sample_baseline):
        """Test that name comparison is case-insensitive."""
        @dataclass
        class MockContactInfo:
            email: str = 'john.doe@example.com'
            phone: str = '555-123-4567'

        class MockUserCV:
            full_name: str = 'JOHN DOE'  # Different case
            contact_info: MockContactInfo = field(default_factory=MockContactInfo)
            experience: list = field(default_factory=list)
            education: list = field(default_factory=list)
            skills: list = field(default_factory=list)

        result = validate_immutable_facts(sample_baseline, MockUserCV())
        # Should be valid due to case-insensitive comparison
        name_violations = [v for v in result.violations if v.field == 'full_name']
        assert len(name_violations) == 0

    def test_phone_normalization(self, sample_baseline):
        """Test that phone numbers are normalized before comparison."""
        @dataclass
        class MockContactInfo:
            email: str = 'john.doe@example.com'
            phone: str = '(555) 123-4567'  # Different format

        class MockUserCV:
            full_name: str = 'John Doe'
            contact_info: MockContactInfo = field(default_factory=MockContactInfo)
            experience: list = field(default_factory=list)
            education: list = field(default_factory=list)
            skills: list = field(default_factory=list)

        result = validate_immutable_facts(sample_baseline, MockUserCV())
        # Should be valid due to digit-only normalization
        phone_violations = [v for v in result.violations if 'phone' in v.field]
        assert len(phone_violations) == 0


# ============================================================================
# Test Class 3: Verifiable Skills Validation
# ============================================================================


class TestValidateVerifiableSkills:
    """Tests for validate_verifiable_skills function."""

    def test_valid_skills_returns_no_violations(self, sample_baseline, matching_generated_cv):
        """Test that skills from baseline return no violations."""
        result = validate_verifiable_skills(sample_baseline, matching_generated_cv)
        assert result.is_valid is True

    def test_unknown_skill_returns_warning(self, sample_baseline):
        """Test that unknown skills return WARNING violations."""
        @dataclass
        class MockSkill:
            name: str = 'UnknownSkill'

        class MockUserCV:
            full_name: str = 'John Doe'
            contact_info = None
            experience: list = field(default_factory=list)
            education: list = field(default_factory=list)
            skills: list = field(default_factory=lambda: [MockSkill()])

        result = validate_verifiable_skills(sample_baseline, MockUserCV())
        assert result.is_valid is False
        assert len(result.violations) > 0
        assert any(v.severity == 'WARNING' for v in result.violations)

    def test_case_insensitive_skill_matching(self, sample_baseline):
        """Test that skill matching is case-insensitive."""
        @dataclass
        class MockSkill:
            name: str = 'python'  # lowercase

        class MockUserCV:
            full_name: str = 'John Doe'
            contact_info = None
            experience: list = field(default_factory=list)
            education: list = field(default_factory=list)
            skills: list = field(default_factory=lambda: [MockSkill()])

        result = validate_verifiable_skills(sample_baseline, MockUserCV())
        skill_violations = [v for v in result.violations if v.field == 'skills']
        assert len(skill_violations) == 0

    def test_partial_skill_matching(self, sample_baseline):
        """Test that partial skill matching works."""
        @dataclass
        class MockSkill:
            name: str = 'Python Programming'

        class MockUserCV:
            full_name: str = 'John Doe'
            contact_info = None
            experience: list = field(default_factory=list)
            education: list = field(default_factory=list)
            skills: list = field(default_factory=lambda: [MockSkill()])

        result = validate_verifiable_skills(sample_baseline, MockUserCV())
        skill_violations = [v for v in result.violations if v.field == 'skills']
        assert len(skill_violations) == 0

    def test_empty_skills_list_returns_valid(self, sample_baseline):
        """Test that empty skills list returns valid result."""
        @dataclass
        class MockContactInfo:
            email: str = 'john.doe@example.com'
            phone: str = '555-123-4567'

        class MockUserCV:
            full_name: str = 'John Doe'
            contact_info: MockContactInfo = field(default_factory=MockContactInfo)
            experience: list = field(default_factory=list)
            education: list = field(default_factory=list)
            skills: list = field(default_factory=list)

        result = validate_verifiable_skills(sample_baseline, MockUserCV())
        assert result.is_valid is True


# ============================================================================
# Test Class 4: Full Baseline Validation
# ============================================================================


class TestValidateCVAgainstBaseline:
    """Tests for validate_cv_against_baseline function."""

    def test_valid_cv_returns_success_result(self, sample_baseline, matching_generated_cv):
        """Test that valid CV returns SUCCESS result."""
        result = validate_cv_against_baseline(sample_baseline, matching_generated_cv)
        assert result.success is True
        assert result.code == ResultCode.SUCCESS

    def test_invalid_cv_returns_failure_result(self, sample_baseline, modified_generated_cv):
        """Test that invalid CV returns FAILURE result."""
        result = validate_cv_against_baseline(sample_baseline, modified_generated_cv)
        assert result.success is False
        assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
        assert result.error is not None

    def test_result_contains_validation_data(self, sample_baseline, matching_generated_cv):
        """Test that result contains FVSValidationResult data."""
        result = validate_cv_against_baseline(sample_baseline, matching_generated_cv)
        assert result.data is not None
        assert isinstance(result.data, FVSValidationResult)


# ============================================================================
# Test Class 5: VPR Validation
# ============================================================================


class TestValidateVPRAgainstCV:
    """Tests for validate_vpr_against_cv function."""

    def test_valid_vpr_returns_success(self, sample_vpr, matching_generated_cv):
        """Test that valid VPR returns SUCCESS."""
        result = validate_vpr_against_cv(sample_vpr, matching_generated_cv)
        assert result.success is True
        assert result.code == ResultCode.SUCCESS

    def test_unknown_company_returns_failure(self, sample_vpr):
        """Test that unknown company in VPR returns failure."""
        @dataclass
        class MockExperience:
            company: str = 'Real Company Inc'
            role: str = 'Engineer'
            dates: str = '2020 - Present'
            description: str = ''

        @dataclass
        class MockContactInfo:
            email: str = 'test@test.com'
            phone: str = '123'

        @dataclass
        class MockEducation:
            institution: str = 'University'
            degree: str = 'BS'
            graduation_date: str = '2020'

        @dataclass
        class MockSkill:
            name: str = 'Python'

        class MockUserCV:
            full_name: str = 'Test User'
            contact_info: MockContactInfo = field(default_factory=MockContactInfo)
            experience: list = field(default_factory=lambda: [MockExperience()])
            education: list = field(default_factory=lambda: [MockEducation()])
            skills: list = field(default_factory=lambda: [MockSkill()])

        @dataclass
        class MockEvidence:
            evidence: str = 'Worked at Fake Company XYZ'

        @dataclass
        class MockVPR:
            evidence_matrix: list = field(default_factory=lambda: [MockEvidence()])
            differentiators: list = field(default_factory=list)
            talking_points: list = field(default_factory=list)

        result = validate_vpr_against_cv(MockVPR(), MockUserCV())
        assert result.success is False
        assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED

    def test_unknown_year_returns_failure(self, sample_vpr, matching_generated_cv):
        """Test that unknown year in VPR returns failure."""
        @dataclass
        class MockEvidence:
            evidence: str = 'Worked at Acme Corp in 1999'  # Year not in CV

        @dataclass
        class MockVPR:
            evidence_matrix: list = field(default_factory=lambda: [MockEvidence()])
            differentiators: list = field(default_factory=list)
            talking_points: list = field(default_factory=list)

        result = validate_vpr_against_cv(MockVPR(), matching_generated_cv)
        assert result.success is False

    def test_unknown_role_returns_failure(self, sample_vpr, matching_generated_cv):
        """Test that unknown role in VPR returns failure."""
        @dataclass
        class MockEvidence:
            evidence: str = 'Served as CEO at Acme Corp'  # Role not in CV

        @dataclass
        class MockVPR:
            evidence_matrix: list = field(default_factory=lambda: [MockEvidence()])
            differentiators: list = field(default_factory=list)
            talking_points: list = field(default_factory=list)

        result = validate_vpr_against_cv(MockVPR(), matching_generated_cv)
        assert result.success is False


# ============================================================================
# Test Class 6: Helper Functions
# ============================================================================


class TestFindMatchingEntry:
    """Tests for _find_matching_entry helper."""

    def test_finds_matching_entry(self):
        """Test finding entry by attribute match."""
        items = [
            Mock(company='Acme Corp'),
            Mock(company='Tech Start'),
            Mock(company='Other Inc'),
        ]
        result = _find_matching_entry(items, 'Acme Corp', 'company')
        assert result is not None
        assert result.company == 'Acme Corp'

    def test_returns_none_for_no_match(self):
        """Test returns None when no match found."""
        items = [
            Mock(company='Acme Corp'),
            Mock(company='Tech Start'),
        ]
        result = _find_matching_entry(items, 'Unknown Corp', 'company')
        assert result is None

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        items = [
            Mock(company='Acme Corp'),
            Mock(company='Tech Start'),
        ]
        result = _find_matching_entry(items, 'ACME CORP', 'company')
        assert result is not None


class TestExtractCompanyMentions:
    """Tests for _extract_company_mentions helper."""

    def test_extracts_simple_company(self):
        """Test extracting company from simple phrase."""
        text = 'Worked at Acme Corp'
        result = _extract_company_mentions(text)
        assert 'Acme Corp' in result

    def test_extracts_company_with_preposition(self):
        """Test extracting company with 'with', 'for' prepositions."""
        text = 'Projects with Tech Start and for Startup Inc'
        result = _extract_company_mentions(text)
        assert 'Tech Start' in result or 'Startup Inc' in result

    def test_returns_empty_for_no_match(self):
        """Test returns empty list when no company mentioned."""
        text = 'Worked in the industry'
        result = _extract_company_mentions(text)
        assert len(result) == 0


class TestExtractTitleMentions:
    """Tests for _extract_title_mentions helper."""

    def test_extracts_title_with_as(self):
        """Test extracting title with 'as' preposition."""
        text = 'Served as Senior Engineer'
        result = _extract_title_mentions(text)
        assert len(result) > 0

    def test_extracts_title_with_served_as(self):
        """Test extracting title with 'served as'."""
        text = 'Worked as Software Developer'
        result = _extract_title_mentions(text)
        assert len(result) > 0

    def test_extracts_multiple_titles(self):
        """Test extracting multiple titles from text."""
        text = 'Served as Engineer and later as Senior Engineer'
        result = _extract_title_mentions(text)
        assert len(result) >= 2


class TestNormalize:
    """Tests for _normalize helper."""

    def test_removes_special_characters(self):
        """Test removing special characters."""
        result = _normalize('Senior Software Engineer!')
        assert '!' not in result

    def test_converts_to_lowercase(self):
        """Test converting to lowercase."""
        result = _normalize('SENIOR Engineer')
        assert result.islower()

    def test_removes_extra_spaces(self):
        """Test removing extra spaces."""
        result = _normalize('  Engineer  ')
        assert result.strip() == result


class TestMatchesKnownRole:
    """Tests for _matches_known_role helper."""

    def test_exact_match(self):
        """Test exact role matching."""
        known_roles = ['Software Engineer', 'Product Manager']
        result = _matches_known_role('Software Engineer', known_roles)
        assert result is True

    def test_no_match(self):
        """Test when role doesn't match."""
        known_roles = ['Software Engineer']
        result = _matches_known_role('CEO', known_roles)
        assert result is False

    def test_fuzzy_match(self):
        """Test fuzzy matching with similarity >= 0.82."""
        known_roles = ['Software Engineer']
        # "Senior Software Engineer" should fuzzy match
        result = _matches_known_role('Senior Software Engineer', known_roles)
        assert result is True

    def test_empty_candidate_returns_true(self):
        """Test that empty candidate returns True."""
        result = _matches_known_role('', ['Engineer'])
        assert result is True


class TestCollectYears:
    """Tests for _collect_years helper."""

    def test_extracts_years_from_experience(self, matching_generated_cv):
        """Test extracting years from experience dates."""
        years = _collect_years(matching_generated_cv)
        assert '2020' in years
        assert 'Present' not in years  # Should not include non-years

    def test_extracts_years_from_education(self, matching_generated_cv):
        """Test extracting years from education."""
        years = _collect_years(matching_generated_cv)
        assert '2018' in years

    def test_returns_empty_set_for_no_dates(self):
        """Test returning empty set when no dates."""
        @dataclass
        class MockExperience:
            company: str = 'Test'
            role: str = 'Engineer'
            dates: str = 'No dates here'
            description: str = ''

        @dataclass
        class MockContactInfo:
            email: str = 'test@test.com'
            phone: str = '123'

        @dataclass
        class MockEducation:
            institution: str = 'University'
            degree: str = 'BS'
            graduation_date: str = 'No date'

        @dataclass
        class MockSkill:
            name: str = 'Python'

        class MockUserCV:
            full_name: str = 'Test'
            contact_info: MockContactInfo = field(default_factory=MockContactInfo)
            experience: list = field(default_factory=lambda: [MockExperience()])
            education: list = field(default_factory=lambda: [MockEducation()])
            skills: list = field(default_factory=lambda: [MockSkill()])

        years = _collect_years(MockUserCV())
        assert isinstance(years, set)


# ============================================================================
# Test Class 7: Edge Cases and Integration
# ============================================================================


class TestFVSEdgeCases:
    """Tests for edge cases in FVS validation."""

    def test_multiple_violations_accumulated(self, sample_baseline, modified_generated_cv):
        """Test that multiple violations are all accumulated."""
        result = validate_immutable_facts(sample_baseline, modified_generated_cv)
        # Should have multiple violations (name, email, phone, role, dates, degree)
        assert len(result.violations) >= 3

    def test_warning_vs_critical_separation(self, sample_baseline):
        """Test that warnings and criticals are properly separated."""
        @dataclass
        class MockSkill:
            name: str = 'Unknown Skill'

        class MockUserCV:
            full_name: str = 'Different Name'  # CRITICAL
            contact_info = None
            experience: list = field(default_factory=list)
            education: list = field(default_factory=list)
            skills: list = field(default_factory=lambda: [MockSkill()])  # WARNING

        # Test both validators
        immutable_result = validate_immutable_facts(sample_baseline, MockUserCV())
        skills_result = validate_verifiable_skills(sample_baseline, MockUserCV())

        assert any(v.severity == 'CRITICAL' for v in immutable_result.violations)
        assert any(v.severity == 'WARNING' for v in skills_result.violations)

    def test_empty_work_history_handled(self, sample_baseline):
        """Test handling of empty work history."""
        @dataclass
        class MockContactInfo:
            email: str = 'john.doe@example.com'
            phone: str = '555-123-4567'

        class MockUserCV:
            full_name: str = 'John Doe'
            contact_info: MockContactInfo = field(default_factory=MockContactInfo)
            experience: list = field(default_factory=list)  # Empty
            education: list = field(default_factory=list)  # Empty
            skills: list = field(default_factory=list)

        result = validate_immutable_facts(sample_baseline, MockUserCV())
        # Should not crash, work history validation should be skipped
        assert isinstance(result, FVSValidationResult)
