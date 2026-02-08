"""Core CV tailoring logic for Phase 9."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from typing import Any, Iterable, cast

from careervp.logic import cv_tailoring_prompt
from careervp.models.cv_models import Certification, Skill, UserCV, WorkExperience
from careervp.models.cv_tailoring_models import (
    ChangeLog,
    TailoredCV,
    TailoredCVResponse,
    TailoringPreferences,
)
from careervp.models.fvs import FVSValidationResult, FVSViolation, ViolationSeverity
from careervp.models.fvs_models import FVSBaseline
from careervp.models.result import Result, ResultCode

WORD_PATTERN = re.compile(r'[A-Za-z][A-Za-z0-9+#/.-]*')

TailorCVResultData = TailoredCVResponse | FVSValidationResult


def tailor_cv(  # noqa: C901
    master_cv: UserCV,
    job_description: str,
    preferences: TailoringPreferences | None = None,
    fvs_baseline: FVSBaseline | None = None,
    dal: Any | None = None,
    llm_client: Any | None = None,
    timeout: int = 300,
) -> Result[TailorCVResultData]:
    """Tailor a master CV to a job description."""
    if dal is not None:
        if _has_defined_attr(dal, 'check_rate_limit'):
            rate_limited = _maybe_await(dal.check_rate_limit(master_cv.user_id))
            if rate_limited:
                return Result(
                    success=False,
                    error='Rate limit exceeded',
                    code=ResultCode.RATE_LIMIT_EXCEEDED,
                )

    if not master_cv.work_experience and not master_cv.skills and not master_cv.education:
        return Result(
            success=False,
            error='Insufficient CV data',
            code=ResultCode.INSUFFICIENT_CV_DATA,
        )

    relevance_scores = calculate_relevance_scores(master_cv, job_description)
    keyword_matches = _extract_keywords(job_description)

    prompt = build_tailoring_prompt(
        cv=master_cv,
        job_description=job_description,
        relevance_scores=relevance_scores,
        fvs_baseline=fvs_baseline,
        target_keywords=keyword_matches,
        preferences=preferences,
    )

    llm_payload: dict[str, Any] | None = None
    if llm_client is not None:
        try:
            response = llm_client.generate(prompt=prompt, timeout=timeout)
            response = _maybe_await(response)
            llm_payload = response
        except TimeoutError as exc:
            return Result(success=False, error=str(exc), code=ResultCode.LLM_TIMEOUT)
        except Exception as exc:  # noqa: BLE001
            return Result(success=False, error=str(exc), code=ResultCode.LLM_API_ERROR)

    parsed = parse_llm_response(llm_payload or {})
    if not parsed.success or parsed.data is None:
        return Result(success=False, error=parsed.message, code=parsed.code)

    tailored_cv = _build_tailored_cv(master_cv, parsed.data)

    validation = validate_tailored_output(master_cv, tailored_cv, fvs_baseline)
    if not validation.success:
        return Result(
            success=False,
            error=validation.message or 'FVS validation failed',
            code=ResultCode.FVS_VIOLATION_DETECTED,
            data=validation.data,
        )

    changes_made = _build_change_log(preferences, parsed.data)
    average_score = _average_score(relevance_scores)
    estimated_ats_score = int(round(average_score * 100))

    response = TailoredCVResponse(
        tailored_cv=tailored_cv,
        changes_made=changes_made,
        relevance_scores=relevance_scores,
        average_relevance_score=average_score,
        keyword_matches=keyword_matches,
        estimated_ats_score=estimated_ats_score,
    )

    if dal is not None:
        if _has_defined_attr(dal, 'save_tailored_cv_artifact'):
            _maybe_await(
                dal.save_tailored_cv_artifact(
                    user_id=master_cv.user_id,
                    cv_id=master_cv.cv_id,
                    job_description=job_description,
                    tailored_cv=tailored_cv,
                )
            )
        elif _has_defined_attr(dal, 'put_item'):
            dal.put_item(
                Item={
                    'user_id': master_cv.user_id,
                    'cv_id': master_cv.cv_id,
                    'tailored_cv': tailored_cv.model_dump(),
                }
            )
        if _has_defined_attr(dal, 'increment_tailoring_counter'):
            _maybe_await(dal.increment_tailoring_counter(master_cv.user_id))

    return Result(success=True, data=response, code=ResultCode.CV_TAILORED_SUCCESS)


def extract_job_requirements(job_description: str) -> dict[str, list[str]]:
    """Extract structured requirements from job description."""
    if not job_description.strip():
        return {
            'required_skills': [],
            'preferred_skills': [],
            'responsibilities': [],
        }

    tokens = _extract_keywords(job_description)
    required = tokens[:5]
    preferred = tokens[5:8]
    responsibilities = _extract_bullets(job_description)
    return {
        'required_skills': required,
        'preferred_skills': preferred,
        'responsibilities': responsibilities,
    }


def calculate_relevance_scores(cv: UserCV, job_description: str) -> dict[str, float]:
    """Compute relevance scores for CV sections."""
    keywords = set(_extract_keywords(job_description))

    def score_text(text: str) -> float:
        if not keywords:
            return 0.0
        tokens = set(_extract_keywords(text))
        if not tokens:
            return 0.0
        return min(len(tokens & keywords) / max(len(keywords), 1), 1.0)

    summary_score = score_text(cv.professional_summary or '')
    skills_text = ' '.join(skill.name if isinstance(skill, Skill) else str(skill) for skill in cv.skills)
    skills_score = score_text(skills_text)
    exp_text = ' '.join(f'{exp.company} {exp.role} {exp.description}' for exp in cv.work_experience)
    exp_score = score_text(exp_text)

    education_text = ' '.join(f'{edu.institution} {edu.degree}' for edu in cv.education)
    education_score = score_text(education_text)
    cert_text = ' '.join(cert.name for cert in cv.certifications)
    cert_score = score_text(cert_text)

    return {
        'professional_summary': summary_score,
        'work_experience': exp_score,
        'skills': skills_score,
        'education': education_score,
        'certifications': cert_score,
    }


def filter_cv_sections_by_relevance(
    cv: UserCV,
    relevance_scores: dict[str, float],
    threshold: float = 0.75,
) -> UserCV:
    """Filter CV sections based on relevance threshold."""
    filtered = cv.model_copy(deep=True)

    if relevance_scores.get('professional_summary', 0.0) < threshold:
        filtered.professional_summary = None

    if relevance_scores.get('skills', 0.0) < threshold:
        filtered.skills = []

    if relevance_scores.get('work_experience', 0.0) < threshold:
        filtered.work_experience = []

    return filtered


def build_tailoring_prompt(
    cv: UserCV,
    job_description: str,
    relevance_scores: dict[str, float] | None = None,
    fvs_baseline: FVSBaseline | None = None,
    target_keywords: Iterable[str] | None = None,
    preferences: TailoringPreferences | None = None,
) -> str:
    """Wrapper to build the tailoring prompt."""
    return cv_tailoring_prompt.build_user_prompt(
        cv=cv,
        job_description=job_description,
        relevance_scores=relevance_scores,
        fvs_baseline=fvs_baseline,
        target_keywords=target_keywords,
        preferences=preferences,
    )


def parse_llm_response(raw_response: Any) -> Result[dict[str, Any]]:
    """Parse LLM response into structured dict."""
    if isinstance(raw_response, str):
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError:
            return Result(
                success=False,
                error='Invalid JSON',
                code=ResultCode.PARSE_ERROR,
            )
    elif isinstance(raw_response, dict):
        parsed = raw_response
    else:
        return Result(
            success=False,
            error='Invalid response format',
            code=ResultCode.PARSE_ERROR,
        )

    return Result(success=True, data=parsed, code=ResultCode.SUCCESS)


def validate_tailored_output(
    original_cv: UserCV,
    tailored_cv: TailoredCV,
    fvs_baseline: FVSBaseline | None = None,
) -> Result[FVSValidationResult]:
    """Validate tailored CV for required fields and FVS rules."""
    if not tailored_cv.email:
        return Result(
            success=False,
            error='Missing required field: email',
            code=ResultCode.VALIDATION_MISSING_REQUIRED_FIELD,
        )

    if fvs_baseline:
        fvs_result = validate_tailored_cv(fvs_baseline, tailored_cv)
        if not fvs_result.success:
            return Result(
                success=False,
                error=fvs_result.message,
                code=ResultCode.FVS_HALLUCINATION_DETECTED,
                data=fvs_result.data,
            )
        return Result(
            success=True,
            data=fvs_result.data,
            code=ResultCode.VALIDATION_SUCCESS,
        )

    return Result(success=True, data=None, code=ResultCode.VALIDATION_SUCCESS)


def validate_tailored_cv(  # noqa: C901
    baseline: FVSBaseline,
    tailored_cv: TailoredCV,
) -> Result[FVSValidationResult]:
    """Validate tailored CV against FVS baseline."""
    violations: list[FVSViolation] = []

    if baseline.email and tailored_cv.contact_info and tailored_cv.contact_info.email:
        if baseline.email.lower() != tailored_cv.contact_info.email.lower():
            violations.append(
                FVSViolation(
                    field='contact_info.email',
                    severity=ViolationSeverity.CRITICAL,
                    expected=baseline.email,
                    actual=tailored_cv.contact_info.email,
                )
            )

    if baseline.phone and tailored_cv.contact_info and tailored_cv.contact_info.phone:
        if baseline.phone != tailored_cv.contact_info.phone:
            violations.append(
                FVSViolation(
                    field='contact_info.phone',
                    severity=ViolationSeverity.CRITICAL,
                    expected=baseline.phone,
                    actual=tailored_cv.contact_info.phone,
                )
            )

    if tailored_cv.contact_info and baseline.full_name:
        contact_name = getattr(tailored_cv.contact_info, 'name', None)
        if contact_name and contact_name != baseline.full_name:
            violations.append(
                FVSViolation(
                    field='contact_info.name',
                    severity=ViolationSeverity.CRITICAL,
                    expected=baseline.full_name,
                    actual=contact_name,
                )
            )

    if not tailored_cv.experience and baseline.companies:
        violations.append(
            FVSViolation(
                field='experience',
                severity=ViolationSeverity.CRITICAL,
                expected='experience entries',
                actual='empty',
            )
        )

    baseline_companies = set(baseline.companies)
    baseline_roles = {fact.value for fact in baseline.immutable_facts if fact.fact_type == 'job_title'}
    baseline_dates = set(baseline.experience_dates)
    baseline_skill_names = set()
    for skill in baseline.skills:
        if isinstance(skill, Skill):
            baseline_skill_names.add(skill.name)
        else:
            baseline_skill_names.add(str(skill))

    for exp in tailored_cv.experience:
        if exp.company not in baseline_companies:
            violations.append(
                FVSViolation(
                    field='experience.company',
                    severity=ViolationSeverity.CRITICAL,
                    expected=', '.join(sorted(baseline_companies)),
                    actual=exp.company,
                )
            )
        if exp.role not in baseline_roles:
            violations.append(
                FVSViolation(
                    field='experience.role',
                    severity=ViolationSeverity.CRITICAL,
                    expected=', '.join(sorted(baseline_roles)),
                    actual=exp.role,
                )
            )
        exp_dates = getattr(exp, 'dates', None) or getattr(exp, 'start_date', None)
        if exp_dates and exp_dates not in baseline_dates:
            violations.append(
                FVSViolation(
                    field='experience.dates',
                    severity=ViolationSeverity.CRITICAL,
                    expected=', '.join(sorted(baseline_dates)),
                    actual=exp_dates,
                )
            )

        for achievement in exp.achievements:
            percent = _extract_percentage(achievement)
            if percent is not None and percent > 300:
                violations.append(
                    FVSViolation(
                        field='experience.achievements',
                        severity=ViolationSeverity.WARNING,
                        expected='reasonable metric',
                        actual=achievement,
                    )
                )

        for tech in exp.technologies:
            if tech not in baseline_skill_names:
                violations.append(
                    FVSViolation(
                        field='experience.technology',
                        severity=ViolationSeverity.WARNING,
                        expected='technology from baseline',
                        actual=tech,
                    )
                )

    for edu in tailored_cv.education:
        if edu.institution and edu.institution not in {fact.value for fact in baseline.immutable_facts if fact.fact_type == 'institution'}:
            violations.append(
                FVSViolation(
                    field='education.institution',
                    severity=ViolationSeverity.CRITICAL,
                    expected='known institution',
                    actual=edu.institution,
                )
            )
        if edu.degree and edu.degree not in {fact.value for fact in baseline.immutable_facts if fact.fact_type == 'degree'}:
            violations.append(
                FVSViolation(
                    field='education.degree',
                    severity=ViolationSeverity.CRITICAL,
                    expected='known degree',
                    actual=edu.degree,
                )
            )
        edu_dates = getattr(edu, 'dates', None) or getattr(edu, 'graduation_date', None) or getattr(edu, 'end_date', None)
        if edu_dates and edu_dates not in set(baseline.education_dates):
            violations.append(
                FVSViolation(
                    field='education.dates',
                    severity=ViolationSeverity.CRITICAL,
                    expected=', '.join(baseline.education_dates),
                    actual=edu_dates,
                )
            )

    for skill in tailored_cv.skills:
        name = skill.name if isinstance(skill, Skill) else str(skill)
        if name not in baseline_skill_names:
            violations.append(
                FVSViolation(
                    field='skills',
                    severity=ViolationSeverity.WARNING,
                    expected=', '.join(sorted(baseline_skill_names)),
                    actual=name,
                )
            )

    # Validate certifications against baseline
    baseline_cert_names: set[str] = set()
    for cert in baseline.certifications:
        if isinstance(cert, Certification):
            baseline_cert_names.add(cert.name)
        else:
            baseline_cert_names.add(str(cert))

    for cert in tailored_cv.certifications:
        name = cert.name if isinstance(cert, Certification) else str(cert)
        if name and name not in baseline_cert_names:
            violations.append(
                FVSViolation(
                    field='certifications',
                    severity=ViolationSeverity.WARNING,
                    expected=', '.join(sorted(baseline_cert_names)),
                    actual=name,
                )
            )

    if tailored_cv.contact_info and baseline.location:
        contact_location = getattr(tailored_cv.contact_info, 'location', None)
        if contact_location and contact_location != baseline.location:
            violations.append(
                FVSViolation(
                    field='contact_info.location',
                    severity=ViolationSeverity.WARNING,
                    expected=baseline.location,
                    actual=contact_location,
                )
            )

    result = FVSValidationResult(violations=violations)
    if violations:
        return Result(
            success=False,
            error='FVS violations detected',
            code=ResultCode.FVS_HALLUCINATION_DETECTED,
            data=result,
        )
    return Result(success=True, data=result, code=ResultCode.SUCCESS)


def create_fvs_baseline(master_cv: UserCV) -> FVSBaseline:
    """Create FVS baseline from master CV."""
    immutable_facts = []

    for exp in master_cv.work_experience:
        immutable_facts.append(_fact('employment_date', exp.start_date, f'{exp.company} - {exp.role} - start_date'))
        if exp.end_date:
            immutable_facts.append(_fact('employment_date', exp.end_date, f'{exp.company} - {exp.role} - end_date'))
        immutable_facts.append(_fact('company_name', exp.company, 'Work experience'))
        immutable_facts.append(_fact('job_title', exp.role, exp.company))

    immutable_facts.append(_fact('email', master_cv.email, 'Contact information'))
    if master_cv.phone:
        immutable_facts.append(_fact('phone', master_cv.phone, 'Contact information'))

    for edu in master_cv.education:
        immutable_facts.append(_fact('degree', edu.degree, edu.institution))
        immutable_facts.append(_fact('institution', edu.institution, 'Education'))

    experience_dates = [exp.dates or exp.start_date for exp in master_cv.work_experience]
    education_dates = [edu.dates or edu.end_date or '' for edu in master_cv.education]
    companies = [exp.company for exp in master_cv.work_experience]
    skills = cast(list[Skill | str], list(master_cv.skills))
    certifications = cast(list[Certification | str], list(master_cv.certifications))

    return FVSBaseline(
        cv_id=master_cv.cv_id,
        user_id=master_cv.user_id,
        full_name=master_cv.full_name,
        immutable_facts=immutable_facts,
        created_at=master_cv.created_at,
        email=master_cv.contact_info.email if master_cv.contact_info else master_cv.email,
        phone=master_cv.contact_info.phone if master_cv.contact_info else master_cv.phone,
        location=master_cv.location,
        experience_dates=experience_dates,
        education_dates=education_dates,
        companies=companies,
        skills=skills,
        certifications=certifications,
    )


def _fact(fact_type: str, value: str | None, context: str) -> Any:
    if value is None:
        value = ''
    from careervp.models.fvs_models import ImmutableFact

    return ImmutableFact(fact_type=fact_type, value=value, context=context)


def _extract_keywords(text: str) -> list[str]:
    tokens = [t for t in WORD_PATTERN.findall(text) if len(t) >= 3]
    seen: set[str] = set()
    keywords: list[str] = []
    for token in tokens:
        lowered = token.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        keywords.append(token)
    return keywords


def _extract_bullets(text: str) -> list[str]:
    lines = [line.strip('- \t') for line in text.splitlines() if line.strip().startswith('-')]
    return [line for line in lines if line]


def _average_score(scores: dict[str, float]) -> float:
    if not scores:
        return 0.0
    return sum(scores.values()) / len(scores)


def _build_tailored_cv(master_cv: UserCV, payload: dict[str, Any]) -> TailoredCV:
    work_experience = [WorkExperience(**exp) for exp in payload.get('work_experience', [])]
    skills: list[Skill | str] = []
    for skill in payload.get('skills', []):
        if isinstance(skill, dict):
            skills.append(Skill(**skill))
        elif isinstance(skill, Skill):
            skills.append(skill)
        else:
            skills.append(str(skill))

    professional_summary = payload.get('professional_summary') or master_cv.professional_summary

    job_hash = hashlib.sha256(payload.get('job_description', '').encode('utf-8') if payload.get('job_description') else b'').hexdigest()

    return TailoredCV(
        cv_id=master_cv.cv_id,
        user_id=master_cv.user_id,
        job_description_hash=job_hash,
        full_name=payload.get('full_name') or master_cv.full_name,
        email=payload.get('email') or master_cv.email,
        phone=payload.get('phone') or master_cv.phone,
        location=payload.get('location') or master_cv.location,
        professional_summary=professional_summary,
        work_experience=work_experience or master_cv.work_experience,
        education=master_cv.education,
        skills=skills or cast(list[Skill | str], list(master_cv.skills)),
        certifications=master_cv.certifications,
        languages=master_cv.languages,
        created_at=master_cv.created_at,
    )


def _build_change_log(
    preferences: TailoringPreferences | None,
    payload: dict[str, Any],
) -> list[ChangeLog]:
    changes: list[ChangeLog] = []
    for item in payload.get('changes_made', []):
        if isinstance(item, dict):
            changes.append(ChangeLog(**item))
        else:
            changes.append(
                ChangeLog(
                    section='general',
                    change_type='update',
                    description=str(item),
                )
            )
    if preferences and preferences.tone:
        changes.append(
            ChangeLog(
                section='tone',
                change_type='style',
                description=f'Applied {preferences.tone} tone to CV',
            )
        )
    return changes


def _extract_percentage(text: str) -> int | None:
    match = re.search(r'(\d{1,4})%', text)
    if not match:
        return None
    return int(match.group(1))


def _maybe_await(value: Any) -> Any:
    if asyncio.iscoroutine(value):
        return asyncio.run(value)
    return value


def _has_defined_attr(obj: Any, name: str) -> bool:
    if name in getattr(obj, '__dict__', {}):
        return True
    return name in getattr(obj.__class__, '__dict__', {})
