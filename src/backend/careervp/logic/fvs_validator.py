"""
Fact Verification System (FVS) Validator.
Per CLAUDE.md: Validates that IMMUTABLE facts are never modified.

FVS Tiers:
- IMMUTABLE: Dates, company names, job titles, contact info - NEVER modify
- VERIFIABLE: Skills in source CV - reframe only if source exists
- FLEXIBLE: Professional summaries - full creative liberty
"""

from dataclasses import dataclass

from careervp.handlers.utils.observability import logger
from careervp.models.cv import UserCV
from careervp.models.result import Result, ResultCode


@dataclass
class FVSViolation:
    """Represents a single FVS rule violation."""

    field: str
    expected: str
    actual: str
    severity: str  # 'CRITICAL' for immutable, 'WARNING' for verifiable


@dataclass
class FVSValidationResult:
    """Result of FVS validation."""

    is_valid: bool
    violations: list[FVSViolation]

    @property
    def has_critical_violations(self) -> bool:
        return any(v.severity == 'CRITICAL' for v in self.violations)


def validate_immutable_facts(baseline: dict, generated: UserCV) -> FVSValidationResult:  # noqa: C901 - explicit comparisons aid readability
    """
    Validate that generated CV does not modify immutable facts from baseline.

    Per tests/fixtures/fvs_baseline_cv.json structure:
    - full_name: IMMUTABLE
    - immutable_facts.contact_info: IMMUTABLE
    - immutable_facts.work_history[].company: IMMUTABLE
    - immutable_facts.work_history[].role: IMMUTABLE
    - immutable_facts.work_history[].dates: IMMUTABLE
    - immutable_facts.education[].institution: IMMUTABLE
    - immutable_facts.education[].degree: IMMUTABLE

    Args:
        baseline: FVS baseline dict from fvs_baseline_cv.json
        generated: Generated/tailored UserCV

    Returns:
        FVSValidationResult with any violations found
    """
    violations = []

    # Validate full name
    expected_name = baseline.get('full_name', '').upper()
    actual_name = generated.full_name.upper() if generated.full_name else ''
    if expected_name and actual_name and expected_name != actual_name:
        violations.append(
            FVSViolation(
                field='full_name',
                expected=baseline.get('full_name', ''),
                actual=generated.full_name,
                severity='CRITICAL',
            )
        )

    immutable = baseline.get('immutable_facts', {})

    # Validate contact info
    baseline_contact = immutable.get('contact_info', {})
    if baseline_contact:
        gen_contact = generated.contact_info

        if baseline_contact.get('email') and gen_contact.email:
            if baseline_contact['email'].lower() != gen_contact.email.lower():
                violations.append(
                    FVSViolation(
                        field='contact_info.email',
                        expected=baseline_contact['email'],
                        actual=gen_contact.email,
                        severity='CRITICAL',
                    )
                )

        if baseline_contact.get('phone') and gen_contact.phone:
            # Normalize phone for comparison (remove spaces, dashes)
            expected_phone = ''.join(c for c in baseline_contact['phone'] if c.isdigit())
            actual_phone = ''.join(c for c in gen_contact.phone if c.isdigit())
            if expected_phone != actual_phone:
                violations.append(
                    FVSViolation(
                        field='contact_info.phone',
                        expected=baseline_contact['phone'],
                        actual=gen_contact.phone,
                        severity='CRITICAL',
                    )
                )

    # Validate work history
    baseline_work = immutable.get('work_history', [])
    for baseline_job in baseline_work:
        baseline_company = baseline_job.get('company', '').lower()
        baseline_role = baseline_job.get('role', '')
        baseline_dates = baseline_job.get('dates', '')

        # Find matching job in generated CV
        matching_job = None
        for gen_job in generated.experience:
            if gen_job.company.lower() == baseline_company:
                matching_job = gen_job
                break

        if matching_job:
            # Validate role hasn't changed
            if baseline_role and matching_job.role != baseline_role:
                violations.append(
                    FVSViolation(
                        field=f'work_history.{baseline_company}.role',
                        expected=baseline_role,
                        actual=matching_job.role,
                        severity='CRITICAL',
                    )
                )

            # Validate dates haven't changed
            if baseline_dates and matching_job.dates != baseline_dates:
                violations.append(
                    FVSViolation(
                        field=f'work_history.{baseline_company}.dates',
                        expected=baseline_dates,
                        actual=matching_job.dates,
                        severity='CRITICAL',
                    )
                )

    # Validate education
    baseline_edu = immutable.get('education', [])
    for baseline_school in baseline_edu:
        baseline_institution = baseline_school.get('institution', '').lower()
        baseline_degree = baseline_school.get('degree', '')

        # Find matching education in generated CV
        matching_edu = None
        for gen_edu in generated.education:
            if gen_edu.institution.lower() == baseline_institution:
                matching_edu = gen_edu
                break

        if matching_edu:
            # Validate degree hasn't changed
            if baseline_degree and matching_edu.degree != baseline_degree:
                violations.append(
                    FVSViolation(
                        field=f'education.{baseline_institution}.degree',
                        expected=baseline_degree,
                        actual=matching_edu.degree,
                        severity='CRITICAL',
                    )
                )

    # Log violations
    if violations:
        logger.warning(
            'FVS violations detected',
            violation_count=len(violations),
            critical_count=sum(1 for v in violations if v.severity == 'CRITICAL'),
            violations=[{'field': v.field, 'expected': v.expected, 'actual': v.actual} for v in violations],
        )

    return FVSValidationResult(is_valid=len(violations) == 0, violations=violations)


def validate_verifiable_skills(baseline: dict, generated: UserCV) -> FVSValidationResult:
    """
    Validate that generated skills exist in the baseline verifiable skills list.

    Skills can be reframed but must have a source in the original CV.
    """
    violations = []
    verifiable_skills = [s.lower() for s in baseline.get('verifiable_skills', [])]

    for skill in generated.skills:
        skill_lower = skill.lower()
        # Check if skill or a variation exists in baseline
        found = False
        for baseline_skill in verifiable_skills:
            if skill_lower in baseline_skill or baseline_skill in skill_lower:
                found = True
                break

        if not found:
            violations.append(
                FVSViolation(
                    field='skills',
                    expected=f'Skill from verifiable list: {verifiable_skills}',
                    actual=skill,
                    severity='WARNING',
                )
            )

    return FVSValidationResult(is_valid=len(violations) == 0, violations=violations)


def validate_cv_against_baseline(baseline: dict, generated: UserCV) -> Result[FVSValidationResult]:
    """
    Full FVS validation of generated CV against baseline.

    Returns Result with CRITICAL failure if immutable facts are violated.
    """
    # Check immutable facts (CRITICAL)
    immutable_result = validate_immutable_facts(baseline, generated)

    if immutable_result.has_critical_violations:
        return Result(
            success=False,
            data=immutable_result,
            error=f'FVS CRITICAL: {len(immutable_result.violations)} immutable fact violations detected',
            code=ResultCode.FVS_HALLUCINATION_DETECTED,
        )

    # Check verifiable skills (WARNING only)
    skills_result = validate_verifiable_skills(baseline, generated)

    # Combine results
    all_violations = immutable_result.violations + skills_result.violations
    combined_result = FVSValidationResult(is_valid=len(all_violations) == 0, violations=all_violations)

    return Result(success=True, data=combined_result, code=ResultCode.SUCCESS)
