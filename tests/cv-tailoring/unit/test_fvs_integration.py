"""
Unit tests for FVS (Factual Verification System) integration with CV Tailoring.

Tests the creation of FVS baselines from master CVs and validation of tailored CVs
against those baselines to detect hallucinations and factual violations.
"""

from careervp.logic.fvs_validator import create_fvs_baseline, validate_tailored_cv
from careervp.models.cv import Skill
from careervp.models.fvs import ViolationSeverity
from careervp.models.result import ResultCode


def test_create_fvs_baseline_from_cv(sample_master_cv):
    """Test extracting immutable facts from master CV to create FVS baseline."""
    # Act
    baseline = create_fvs_baseline(sample_master_cv)

    # Assert
    assert baseline is not None
    assert len(baseline.immutable_facts) > 0
    assert baseline.email == sample_master_cv.contact_info.email
    assert baseline.phone == sample_master_cv.contact_info.phone


def test_validate_tailored_cv_success(sample_master_cv, sample_tailored_cv):
    """Test FVS validation passes when no violations exist."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is True
    assert result.code == ResultCode.SUCCESS
    assert len(result.data.violations) == 0


def test_validate_tailored_cv_date_modified(sample_master_cv, sample_tailored_cv):
    """Test FVS detects CRITICAL violation when dates are modified."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.experience[0].dates = "2020-2025"  # Changed from 2020-2024

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert len(result.data.violations) == 1
    assert result.data.violations[0].severity == ViolationSeverity.CRITICAL
    assert "dates" in result.data.violations[0].field.lower()


def test_validate_tailored_cv_company_modified(sample_master_cv, sample_tailored_cv):
    """Test FVS detects CRITICAL violation when company name is modified."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.experience[0].company = "Fake Corp"  # Changed company name

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert len(result.data.violations) == 1
    assert result.data.violations[0].severity == ViolationSeverity.CRITICAL
    assert "company" in result.data.violations[0].field.lower()


def test_validate_tailored_cv_role_modified(sample_master_cv, sample_tailored_cv):
    """Test FVS detects CRITICAL violation when job role/title is modified."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.experience[0].role = "CTO"  # Changed from Senior Engineer

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert len(result.data.violations) == 1
    assert result.data.violations[0].severity == ViolationSeverity.CRITICAL
    assert "role" in result.data.violations[0].field.lower()


def test_validate_tailored_cv_email_modified(sample_master_cv, sample_tailored_cv):
    """Test FVS detects CRITICAL violation when email is modified."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.contact_info.email = "fake@example.com"  # Changed email

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert len(result.data.violations) == 1
    assert result.data.violations[0].severity == ViolationSeverity.CRITICAL
    assert "email" in result.data.violations[0].field.lower()


def test_validate_tailored_cv_phone_modified(sample_master_cv, sample_tailored_cv):
    """Test FVS detects CRITICAL violation when phone number is modified."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.contact_info.phone = "+1-999-999-9999"  # Changed phone

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert len(result.data.violations) == 1
    assert result.data.violations[0].severity == ViolationSeverity.CRITICAL
    assert "phone" in result.data.violations[0].field.lower()


def test_validate_tailored_cv_skill_not_in_source(sample_master_cv, sample_tailored_cv):
    """Test FVS detects WARNING violation when skill not in master CV is added."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.skills.append("Quantum Computing")  # Not in master CV

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert len(result.data.violations) == 1
    assert result.data.violations[0].severity == ViolationSeverity.WARNING
    assert "skill" in result.data.violations[0].field.lower()


def test_validate_tailored_cv_multiple_violations(sample_master_cv, sample_tailored_cv):
    """Test FVS detects multiple CRITICAL violations in single validation."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.experience[0].dates = "2020-2025"
    sample_tailored_cv.experience[0].company = "Fake Corp"
    sample_tailored_cv.contact_info.email = "fake@example.com"

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert len(result.data.violations) == 3
    assert all(v.severity == ViolationSeverity.CRITICAL for v in result.data.violations)


def test_validate_tailored_cv_education_dates_modified(
    sample_master_cv, sample_tailored_cv
):
    """Test FVS detects CRITICAL violation when education dates are modified."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.education[0].dates = "2010-2015"  # Changed graduation date

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert any(v.severity == ViolationSeverity.CRITICAL for v in result.data.violations)


def test_validate_tailored_cv_degree_modified(sample_master_cv, sample_tailored_cv):
    """Test FVS detects CRITICAL violation when degree type is modified."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.education[0].degree = "Ph.D."  # Changed from B.S.

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert any("degree" in v.field.lower() for v in result.data.violations)


def test_validate_tailored_cv_university_modified(sample_master_cv, sample_tailored_cv):
    """Test FVS detects CRITICAL violation when university name is modified."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.education[0].institution = "Fake University"

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert any("institution" in v.field.lower() for v in result.data.violations)


def test_validate_tailored_cv_certification_added(sample_master_cv, sample_tailored_cv):
    """Test FVS detects WARNING when fake certification is added."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    from careervp.models.cv import Certification

    fake_cert = Certification(
        name="Fake Cloud Architect Certification",
        issuer="Fake Cloud",
        date="2023",
    )
    sample_tailored_cv.certifications.append(fake_cert)

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert any(v.severity == ViolationSeverity.WARNING for v in result.data.violations)


def test_validate_tailored_cv_empty_experience(sample_master_cv, sample_tailored_cv):
    """Test FVS validation with empty experience list."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    # Create a tailored CV with empty experience
    from careervp.models.cv_tailoring_models import TailoredCV

    tailored_cv = TailoredCV(
        cv_id=sample_tailored_cv.cv_id,
        user_id=sample_master_cv.user_id,
        full_name=sample_master_cv.full_name,
        email=sample_master_cv.email,
        phone=sample_master_cv.phone,
        location=sample_master_cv.location,
        professional_summary=sample_master_cv.professional_summary,
        work_experience=[],  # Empty experience - should be caught
        education=sample_master_cv.education,
        skills=[s.name if isinstance(s, Skill) else s for s in sample_master_cv.skills],
        certifications=[],
    )

    # Act
    result = validate_tailored_cv(baseline, tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED


def test_validate_tailored_cv_achievement_exaggerated(
    sample_master_cv, sample_tailored_cv
):
    """Test FVS detects WARNING when achievement metrics are exaggerated."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    # Change "20% performance improvement" to "500% performance improvement"
    sample_tailored_cv.experience[0].achievements[0] = (
        "Improved system performance by 500%"
    )

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert any(v.severity == ViolationSeverity.WARNING for v in result.data.violations)


def test_validate_tailored_cv_technology_hallucinated(
    sample_master_cv, sample_tailored_cv
):
    """Test FVS detects WARNING when technology not in master CV is mentioned."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.experience[0].technologies.append("QuantumDB")

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert any("technology" in v.field.lower() for v in result.data.violations)


def test_create_fvs_baseline_extracts_all_dates(sample_master_cv):
    """Test FVS baseline extraction captures all date fields."""
    # Act
    baseline = create_fvs_baseline(sample_master_cv)

    # Assert
    assert len(baseline.experience_dates) == len(sample_master_cv.experience)
    assert len(baseline.education_dates) == len(sample_master_cv.education)


def test_create_fvs_baseline_extracts_all_companies(sample_master_cv):
    """Test FVS baseline extraction captures all company names."""
    # Act
    baseline = create_fvs_baseline(sample_master_cv)

    # Assert
    assert len(baseline.companies) == len(sample_master_cv.experience)
    assert all(exp.company in baseline.companies for exp in sample_master_cv.experience)


def test_create_fvs_baseline_extracts_all_skills(sample_master_cv):
    """Test FVS baseline extraction captures all skills."""
    # Act
    baseline = create_fvs_baseline(sample_master_cv)

    # Assert
    assert len(baseline.skills) == len(sample_master_cv.skills)
    assert set(baseline.skills) == set(sample_master_cv.skills)


def test_validate_tailored_cv_name_modified(sample_master_cv, sample_tailored_cv):
    """Test FVS detects CRITICAL violation when name is modified."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.contact_info.name = "Fake Name"

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert any(v.severity == ViolationSeverity.CRITICAL for v in result.data.violations)
    assert any("name" in v.field.lower() for v in result.data.violations)


def test_validate_tailored_cv_location_modified(sample_master_cv, sample_tailored_cv):
    """Test FVS detects WARNING when location is modified."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.contact_info.location = "Fake City, XX"

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    # Location might be WARNING instead of CRITICAL
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED


def test_validate_tailored_cv_mixed_severity_violations(
    sample_master_cv, sample_tailored_cv
):
    """Test FVS handles mix of CRITICAL and WARNING violations."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.experience[0].dates = "2020-2025"  # CRITICAL
    sample_tailored_cv.skills.append("Quantum Computing")  # WARNING

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
    assert len(result.data.violations) == 2
    critical_violations = [
        v for v in result.data.violations if v.severity == ViolationSeverity.CRITICAL
    ]
    warning_violations = [
        v for v in result.data.violations if v.severity == ViolationSeverity.WARNING
    ]
    assert len(critical_violations) == 1
    assert len(warning_violations) == 1


def test_validate_tailored_cv_experience_order_changed(
    sample_master_cv, sample_tailored_cv
):
    """Test FVS allows reordering of experience (not a violation)."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    sample_tailored_cv.experience = sample_tailored_cv.experience[::-1]  # Reverse order

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    # Reordering should be allowed
    assert result.success is True or len(result.data.violations) == 0


def test_validate_tailored_cv_bullet_rewording_allowed(
    sample_master_cv, sample_tailored_cv
):
    """Test FVS allows rewording of achievement bullets (not a violation)."""
    # Arrange
    baseline = create_fvs_baseline(sample_master_cv)
    # Reword but keep same meaning
    _original = sample_tailored_cv.experience[0].achievements[0]
    sample_tailored_cv.experience[0].achievements[0] = (
        "Enhanced system performance through optimization"
    )

    # Act
    result = validate_tailored_cv(baseline, sample_tailored_cv)

    # Assert
    # Rewording should be allowed
    assert result.success is True or all(
        v.severity != ViolationSeverity.CRITICAL for v in result.data.violations
    )
