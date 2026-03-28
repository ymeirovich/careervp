"""
FVS Validator Tests.
Validates that the Fact Verification System correctly detects hallucinations.

Per .clauderules: Never mark a task as complete until its unit test passes.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, cast

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
from careervp.models.vpr import (
    VPR,
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
    VPRRequirementBreakdown,
    VPRResponsibility,
    VPRRoleAlignment,
    VPRSecondaryValue,
    VPRSkillsAnalysis,
    VPRStrength,
    VPRUniqueStrength,
    VPRValueProposition,
)

# Path to fixtures (repo root/tests/fixtures)
FIXTURES_DIR = Path(__file__).resolve().parents[4] / 'tests' / 'fixtures'


@pytest.fixture
def fvs_baseline() -> Dict[str, Any]:
    """Load FVS baseline fixture."""
    baseline_path = FIXTURES_DIR / 'fvs_baseline_cv.json'
    with open(baseline_path) as f:
        data = json.load(f)
        return cast(Dict[str, Any], data)


@pytest.fixture
def fvs_hallucination() -> Dict[str, Any]:
    """Load FVS hallucination example fixture."""
    hallucination_path = FIXTURES_DIR / 'fvs_test_hallucination.json'
    with open(hallucination_path) as f:
        data = json.load(f)
        return cast(Dict[str, Any], data)


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
                technologies=[],
            ),
            WorkExperience(
                company='Israel Ministry of Finance',
                role='AWS Solutions Architect',
                dates='2009 – 2021',
                achievements=['Architected cloud solutions'],
                technologies=[],
            ),
        ],
        education=[
            Education(
                institution='University of Maryland',
                degree='B.A. Political Science',
                honors=[],
            ),
        ],
        certifications=[
            Certification(name='AWS Solutions Architect Associate'),
            Certification(name='AWS Certified Developer Associate'),
        ],
        skills=['AWS Solutions Architect Associate', 'Python', 'JavaScript'],
        top_achievements=['Implemented LMS system'],
        languages=[],
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
                technologies=[],
            ),
        ],
        education=[
            Education(
                institution='Unknown',
                degree='M.S. Computer Science',  # HALLUCINATED: Should be "B.A. Political Science"
                honors=[],
            ),
        ],
        certifications=[],
        top_achievements=[],
        skills=['Rust Expert'],  # HALLUCINATED: Not in verifiable skills
        languages=[],
        is_parsed=True,
    )


class TestFVSImmutableFactsValidation:
    """Test validation of immutable facts."""

    def test_valid_cv_passes_immutable_check(self, fvs_baseline: Dict[str, Any], valid_user_cv: UserCV) -> None:
        """A CV with correct immutable facts should pass validation."""
        result = validate_immutable_facts(fvs_baseline, valid_user_cv)

        assert result.is_valid is True
        assert len(result.violations) == 0
        assert result.has_critical_violations is False

    def test_hallucinated_role_fails(self, fvs_baseline: Dict[str, Any], hallucinated_user_cv: UserCV) -> None:
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

    def test_hallucinated_dates_fails(self, fvs_baseline: Dict[str, Any], hallucinated_user_cv: UserCV) -> None:
        """A CV with hallucinated dates should fail validation."""
        result = validate_immutable_facts(fvs_baseline, hallucinated_user_cv)

        # Find the dates violation
        dates_violations = [v for v in result.violations if 'dates' in v.field]
        assert len(dates_violations) >= 1

        dates_violation = dates_violations[0]
        assert dates_violation.expected == '2021 – Present'
        assert dates_violation.actual == '2018 – Present'
        assert dates_violation.severity == 'CRITICAL'

    def test_contact_info_change_fails(self, fvs_baseline: Dict[str, Any], valid_user_cv: UserCV) -> None:
        """Changing contact info should fail validation."""
        # Modify email
        assert valid_user_cv.contact_info is not None
        valid_user_cv.contact_info.email = 'wrong@email.com'

        result = validate_immutable_facts(fvs_baseline, valid_user_cv)

        assert result.is_valid is False
        email_violations = [v for v in result.violations if 'email' in v.field]
        assert len(email_violations) == 1


class TestFVSVerifiableSkillsValidation:
    """Test validation of verifiable skills."""

    def test_valid_skills_pass(self, fvs_baseline: Dict[str, Any], valid_user_cv: UserCV) -> None:
        """Skills from the verifiable list should pass."""
        result = validate_verifiable_skills(fvs_baseline, valid_user_cv)

        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_hallucinated_skill_fails(self, fvs_baseline: Dict[str, Any], hallucinated_user_cv: UserCV) -> None:
        """Skills not in verifiable list should be flagged."""
        result = validate_verifiable_skills(fvs_baseline, hallucinated_user_cv)

        assert result.is_valid is False
        skill_violations = [v for v in result.violations if v.actual == 'Rust Expert']
        assert len(skill_violations) == 1
        assert skill_violations[0].severity == 'WARNING'


class TestFullFVSValidation:
    """Test complete FVS validation flow."""

    def test_valid_cv_returns_success(self, fvs_baseline: Dict[str, Any], valid_user_cv: UserCV) -> None:
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
        """Build a VPR aligned with the user's CV facts (new 10-section schema)."""
        return VPR(
            application_id='app-123',
            user_id=valid_user_cv.user_id,
            metadata=VPRMetadata(
                report_date='2024-01-15',
                candidate_name='Test Candidate',
                target_role='Learning Experience Specialist',
                target_company='SysAid',
            ),
            executive_summary=VPRExecutiveSummary(
                overall_fit_score=78,
                fit_rationale=(
                    'Led enablement at SysAid during 2021 delivering measurable results. '
                    'Trusted partner across cross-functional initiatives with direct role alignment.'
                ),
                top_three_strengths=[
                    VPRStrength(
                        strength='SysAid enablement leadership', evidence='Led enablement at SysAid 2021', relevance_to_role='Direct experience'
                    ),
                    VPRStrength(strength='Cross-functional delivery', evidence='Trusted partner 2021 initiatives', relevance_to_role='Collaboration'),
                    VPRStrength(strength='Values-first approach', evidence='Documented values alignment', relevance_to_role='Cultural fit'),
                ],
                top_three_concerns=[
                    VPRConcern(concern='Scope of past role unknown', severity='low', mitigation='Clarify in interview'),
                    VPRConcern(concern='Limited quantified metrics', severity='medium', mitigation='Prepare examples'),
                    VPRConcern(concern='Recency of experience unclear', severity='low', mitigation='Reference 2021 work'),
                ],
                recommended_approach='apply_with_customization',
            ),
            role_alignment=VPRRoleAlignment(
                core_responsibilities=[
                    VPRResponsibility(
                        responsibility='Lead enablement initiatives',
                        alignment_score=85,
                        candidate_evidence=['Led enablement at SysAid during 2021'],
                        evidence_quality='direct',
                    )
                ],
                requirement_breakdown=VPRRequirementBreakdown(must_have=[], nice_to_have=[], assumed_prerequisites=[]),
            ),
            experience_mapping=VPRExperienceMapping(
                relevant_experiences=[
                    VPRRelevantExperience(
                        role='Learning Experience Specialist',
                        organization='SysAid',
                        duration='1 year',
                        key_achievements=[
                            VPRKeyAchievement(
                                achievement='Led enablement program',
                                metric='Delivered 2021',
                                impact='Immediate readiness for teams',
                            )
                        ],
                        relevance_to_target_role='Trusted partner at SysAid across 2021 initiatives.',
                    )
                ],
                experience_gaps=[],
            ),
            skills_analysis=VPRSkillsAnalysis(technical_skills=[], soft_skills=[], tool_proficiency=[]),
            evidence_gaps=VPREvidenceGaps(
                identified_gaps=[
                    VPRIdentifiedGap(
                        requirement='Quantified metrics',
                        current_evidence='Qualitative evidence only',
                        gap_severity='medium',
                        suggested_evidence=['Add metrics to achievements'],
                    )
                ],
                priority_gaps_to_address=[
                    VPRPriorityGap(
                        gap='Quantified metrics',
                        priority=1,
                        action_item='Prepare 2-3 quantified examples',
                        deadline='before_interview',
                    )
                ],
            ),
            differentiators=VPRDifferentiators(
                unique_strengths=[
                    VPRUniqueStrength(
                        strength='Trusted SysAid enablement partner',
                        rarity='somewhat_rare',
                        relevance='Direct domain experience',
                        proof='Trusted partner at SysAid across 2021 initiatives.',
                    )
                ],
                competitive_advantages=[],
                positioning_statement=(
                    'Experienced enablement professional with direct SysAid track record '
                    'and values-first approach to learning experience design and delivery.'
                ),
            ),
            concerns_and_mitigations=VPRConcernsAndMitigations(
                likely_objections=[
                    VPRObjection(
                        objection='Limited quantified metrics',
                        likelihood='possible',
                        mitigation=VPRMitigation(
                            strategy='provide_evidence',
                            messaging='Discuss leadership as Learning Experience Specialist with specific outcomes.',
                        ),
                        where_to_address=['interview'],
                    )
                ],
                preemptive_responses=[],
            ),
            value_proposition=VPRValueProposition(
                primary_value=VPRPrimaryValue(
                    statement='Drive enablement outcomes at SysAid',
                    evidence='Led enablement at SysAid 2021',
                    outcome_for_company='Immediate readiness',
                ),
                secondary_values=[
                    VPRSecondaryValue(value='Values alignment', proof='Consistent values-first approach'),
                    VPRSecondaryValue(value='Cross-functional trust', proof='Trusted partner across 2021 initiatives'),
                ],
                quantified_impact=[],
                elevator_pitch=(
                    'Enablement professional with direct SysAid experience and proven track record '
                    'of building trusted cross-functional partnerships that deliver immediate readiness.'
                ),
            ),
            application_strategy=VPRApplicationStrategy(
                messaging_approach='Lead with direct SysAid experience and values alignment.',
                ats_keywords=VPRKeywordGroup(primary=['Enablement'], secondary=['Leadership', 'SysAid']),
                cv_lead_differentiator='Enablement specialist with direct SysAid track record.',
                sections_to_compress=[],
            ),
            version=1,
            language='en',
            created_at=datetime.now(timezone.utc),
            word_count=0,
        )

    @pytest.mark.xfail(reason='Pending spec-04: fvs_validator.py accesses old VPR fields (evidence_matrix, differentiators, talking_points)')
    def test_vpr_validation_passes_when_facts_align(self, aligned_vpr: VPR, valid_user_cv: UserCV) -> None:
        """VPR referencing only CV facts should pass."""
        result = validate_vpr_against_cv(aligned_vpr, valid_user_cv)

        assert result.success is True
        assert result.code == 'SUCCESS'
        assert result.data is not None
        assert result.data.is_valid is True

    @pytest.mark.xfail(reason='Pending spec-04: fvs_validator.py accesses old VPR fields (evidence_matrix, differentiators, talking_points)')
    def test_vpr_validation_detects_unknown_company(self, aligned_vpr: VPR, valid_user_cv: UserCV) -> None:
        """Referencing a company not in the CV should fail."""
        result = validate_vpr_against_cv(aligned_vpr, valid_user_cv)

        assert result.success is False
        assert result.code == 'FVS_HALLUCINATION_DETECTED'
        assert result.data is not None
        assert any(v.actual == 'Fictional Labs' for v in result.data.violations)

    @pytest.mark.xfail(reason='Pending spec-04: fvs_validator.py accesses old VPR fields (evidence_matrix, differentiators, talking_points)')
    def test_vpr_validation_detects_unknown_dates(self, aligned_vpr: VPR, valid_user_cv: UserCV) -> None:
        """Referencing dates not present in CV should fail."""
        result = validate_vpr_against_cv(aligned_vpr, valid_user_cv)

        assert result.success is False
        assert result.code == 'FVS_HALLUCINATION_DETECTED'
        assert result.data is not None
        assert any(v.field == 'vpr.dates' for v in result.data.violations)

    @pytest.mark.xfail(reason='Pending spec-04: fvs_validator.py accesses old VPR fields (evidence_matrix, differentiators, talking_points)')
    def test_vpr_validation_detects_unknown_title(self, aligned_vpr: VPR, valid_user_cv: UserCV) -> None:
        """Referencing a job title not in CV should fail."""
        result = validate_vpr_against_cv(aligned_vpr, valid_user_cv)

        assert result.success is False
        assert result.code == 'FVS_HALLUCINATION_DETECTED'
        assert result.data is not None
        assert any('Chief Visionary Officer' in v.actual for v in result.data.violations)

    def test_hallucinated_cv_returns_failure(self, fvs_baseline: Dict[str, Any], hallucinated_user_cv: UserCV) -> None:
        """A CV with hallucinations should return failure Result."""
        result = validate_cv_against_baseline(fvs_baseline, hallucinated_user_cv)

        assert result.success is False
        assert result.code == 'FVS_HALLUCINATION_DETECTED'
        assert result.error is not None
        assert 'immutable fact violations' in result.error.lower()


class TestFVSFixtureIntegrity:
    """Test that fixtures are properly structured."""

    def test_baseline_fixture_has_required_fields(self, fvs_baseline: Dict[str, Any]) -> None:
        """Baseline fixture should have all required FVS fields."""
        assert 'full_name' in fvs_baseline
        assert 'immutable_facts' in fvs_baseline
        assert 'verifiable_skills' in fvs_baseline

        immutable = fvs_baseline['immutable_facts']
        assert 'contact_info' in immutable
        assert 'work_history' in immutable
        assert 'education' in immutable

    def test_hallucination_fixture_has_violations(self, fvs_hallucination: Dict[str, Any]) -> None:
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
