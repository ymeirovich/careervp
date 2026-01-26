"""
Fact Verification System (FVS) Validator.
Per CLAUDE.md: Validates that IMMUTABLE facts are never modified.

FVS Tiers:
- IMMUTABLE: Dates, company names, job titles, contact info - NEVER modify
- VERIFIABLE: Skills in source CV - reframe only if source exists
- FLEXIBLE: Professional summaries - full creative liberty
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Iterable

from careervp.handlers.utils.observability import logger
from careervp.models.cv import UserCV
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import VPR


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


def validate_immutable_facts(baseline: dict[str, Any], generated: UserCV) -> FVSValidationResult:  # noqa: C901 - explicit comparisons aid readability
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


def validate_verifiable_skills(baseline: dict[str, Any], generated: UserCV) -> FVSValidationResult:
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


def validate_cv_against_baseline(baseline: dict[str, Any], generated: UserCV) -> Result[FVSValidationResult]:
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


YEAR_PATTERN = re.compile(r'((?:19|20)\d{2})')
COMPANY_PATTERN = re.compile(r'\b(?:at|with|for)\s+([A-Z][A-Za-z0-9&.\-]*(?:\s+[A-Z][A-Za-z0-9&.\-]*)*)')
TITLE_PATTERN = re.compile(
    r'\b(?:as|serving as|served as|working as|worked as|functioning as|functioned as)\s+([A-Za-z][A-Za-z0-9&/ \-]+)',
    flags=re.IGNORECASE,
)


def validate_vpr_against_cv(vpr: VPR, user_cv: UserCV) -> Result[FVSValidationResult]:
    """
    Validate VPR IMMUTABLE facts against source CV.

    Per docs/specs/03-vpr-generator.md FVS Rules:
    - IMMUTABLE: Dates, company names, job titles cannot be fabricated
    - VERIFIABLE: Skills/achievements must exist in CV or gap_responses
    """

    company_lookup = {exp.company.lower() for exp in user_cv.experience}
    role_lookup = {exp.role.lower() for exp in user_cv.experience}
    year_lookup = _collect_years(user_cv)

    sections: list[str] = []
    sections.extend(item.evidence for item in vpr.evidence_matrix if item.evidence)
    sections.extend(vpr.differentiators)
    sections.extend(vpr.talking_points)
    sections = [section for section in sections if section]

    violations: list[FVSViolation] = []

    for section in sections:
        for company in _extract_company_mentions(section):
            if company.lower() not in company_lookup:
                violations.append(
                    FVSViolation(
                        field='vpr.company',
                        expected=f'Company from CV: {sorted(company_lookup)}',
                        actual=company,
                        severity='CRITICAL',
                    )
                )

        for year in YEAR_PATTERN.findall(section):
            if year not in year_lookup:
                violations.append(
                    FVSViolation(
                        field='vpr.dates',
                        expected=f'Dates from CV: {sorted(year_lookup)}',
                        actual=year,
                        severity='CRITICAL',
                    )
                )

        for title in _extract_title_mentions(section):
            if not _matches_known_role(title, role_lookup):
                violations.append(
                    FVSViolation(
                        field='vpr.role',
                        expected=f'Role from CV: {sorted(role_lookup)}',
                        actual=title,
                        severity='CRITICAL',
                    )
                )

    validation_result = FVSValidationResult(is_valid=len(violations) == 0, violations=violations)

    if violations:
        logger.warning(
            'FVS VPR validation failed',
            violation_count=len(violations),
            violations=[{'field': v.field, 'actual': v.actual} for v in violations],
        )
        return Result(
            success=False,
            data=validation_result,
            error='VPR references facts not present in source CV',
            code=ResultCode.FVS_HALLUCINATION_DETECTED,
        )

    return Result(success=True, data=validation_result, code=ResultCode.SUCCESS)


def _collect_years(user_cv: UserCV) -> set[str]:
    years: set[str] = set()
    for experience in user_cv.experience:
        years.update(YEAR_PATTERN.findall(experience.dates))
    for education in user_cv.education:
        if education.graduation_date:
            years.update(YEAR_PATTERN.findall(education.graduation_date))
    return years


def _extract_company_mentions(text: str) -> list[str]:
    return COMPANY_PATTERN.findall(text)


def _extract_title_mentions(text: str) -> list[str]:
    return [match.strip() for match in TITLE_PATTERN.findall(text)]


def _normalize(value: str) -> str:
    return re.sub(r'[^a-z0-9 ]', '', value.lower()).strip()


def _matches_known_role(candidate: str, known_roles: Iterable[str]) -> bool:
    normalized_candidate = _normalize(candidate)
    if not normalized_candidate:
        return True
    for role in known_roles:
        normalized_role = _normalize(role)
        if normalized_candidate == normalized_role:
            return True
        if SequenceMatcher(None, normalized_candidate, normalized_role).ratio() >= 0.82:
            return True
    return False
