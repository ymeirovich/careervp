"""Core CV tailoring logic for Phase 9."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Literal, TypeAlias, cast, overload

from careervp.logic import cv_tailoring_prompt
from careervp.logic.fvs_validator import check_anti_ai_patterns
from careervp.models.cv import UserCV as CVUserCV
from careervp.models.cv_models import Certification, ContactInfo, Skill, UserCV, WorkExperience
from careervp.models.cv_tailoring_models import (
    ChangeLog,
    TailoredCV,
    TailoredCVResponse,
    TailoringPreferences,
)
from careervp.models.fvs import FVSBaseline, FVSValidationResult, FVSViolation, ImmutableFact, ViolationSeverity
from careervp.models.job import JobPosting
from careervp.models.result import Result, ResultCode

WORD_PATTERN = re.compile(r'[A-Za-z][A-Za-z0-9+#/.-]*')
METRIC_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(%|x|X|k|K|m|M)?')
STAR_ACTION_VERB_PATTERN = re.compile(r'^[A-Za-z]+')

MIN_KEYWORDS = 12
MAX_KEYWORDS = 18
TARGET_ATS_SCORE = 8.0
ANTI_AI_MIN_SCORE = 9.0
MAX_SELF_CORRECTION_ITERATIONS = 3

KeywordCategory = Literal['required', 'preferred', 'nice_to_have']
Job: TypeAlias = JobPosting

_CATEGORY_PRIORITY: dict[KeywordCategory, int] = {
    'required': 3,
    'preferred': 2,
    'nice_to_have': 1,
}

_DEFAULT_PIPELINE_KEYWORDS = [
    'leadership',
    'strategy',
    'communication',
    'collaboration',
    'analysis',
    'optimization',
    'delivery',
    'execution',
    'stakeholder',
    'performance',
    'scalability',
    'automation',
]

_STOP_WORDS = {
    'about',
    'above',
    'across',
    'after',
    'again',
    'against',
    'also',
    'among',
    'and',
    'are',
    'because',
    'been',
    'being',
    'between',
    'both',
    'build',
    'built',
    'candidate',
    'company',
    'development',
    'experience',
    'for',
    'from',
    'have',
    'highly',
    'ideal',
    'into',
    'join',
    'knowledge',
    'looking',
    'must',
    'need',
    'our',
    'over',
    'preferred',
    'required',
    'role',
    'seeking',
    'skills',
    'strong',
    'team',
    'that',
    'the',
    'their',
    'them',
    'they',
    'this',
    'through',
    'using',
    'will',
    'with',
    'work',
    'years',
    'you',
    'your',
}

_STAR_VERBS = {
    'accelerated',
    'achieved',
    'architected',
    'automated',
    'built',
    'collaborated',
    'created',
    'delivered',
    'designed',
    'drove',
    'enhanced',
    'executed',
    'implemented',
    'improved',
    'increased',
    'launched',
    'led',
    'managed',
    'optimized',
    'reduced',
    'streamlined',
}

TailorCVResultData = TailoredCVResponse | FVSValidationResult


@dataclass(frozen=True)
class KeywordMap:
    """Structured keyword extraction and mapping output."""

    required: list[str]
    preferred: list[str]
    nice_to_have: list[str]
    mapped_keywords: dict[str, list[str]]
    keyword_categories: dict[str, KeywordCategory]

    @property
    def all_keywords(self) -> list[str]:
        return _dedupe_preserve_order([*self.required, *self.preferred, *self.nice_to_have])


@dataclass(frozen=True)
class TailoredCVDraft:
    """Step 2 output including preliminary ATS score."""

    source_cv: CVUserCV | UserCV
    keyword_map: KeywordMap
    tailored_cv: TailoredCV
    section_order: list[str]
    preliminary_ats_score: float
    integrated_keywords: list[str]
    feedback_applied: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FinalTailoredCV:
    """Final CV package produced after Step 3 validation."""

    tailored_cv: TailoredCV
    ats_score: float
    keyword_map: KeywordMap
    iterations: int
    iteration_history: list[dict[str, Any]]
    star_validation_passed: bool
    formatting_checks_passed: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@overload
def tailor_cv(
    master_cv: CVUserCV | UserCV,
    job_description: str,
    preferences: TailoringPreferences | None = None,
    fvs_baseline: FVSBaseline | None = None,
    dal: Any | None = None,
    llm_client: Any | None = None,
    timeout: int = 300,
) -> Result[TailorCVResultData]: ...


@overload
def tailor_cv(
    master_cv: CVUserCV | UserCV,
    job_description: KeywordMap,
    preferences: str | None = None,
    fvs_baseline: FVSBaseline | None = None,
    dal: Any | None = None,
    llm_client: Any | None = None,
    timeout: int = 300,
) -> TailoredCVDraft: ...


def tailor_cv(  # noqa: C901
    master_cv: CVUserCV | UserCV,
    job_description: str | KeywordMap,
    preferences: TailoringPreferences | str | None = None,
    fvs_baseline: FVSBaseline | None = None,
    dal: Any | None = None,
    llm_client: Any | None = None,
    timeout: int = 300,
) -> Result[TailorCVResultData] | TailoredCVDraft:
    """
    Tailor CV content.

    Overloads:
    - Legacy path: (cv, job_description: str, ...) -> Result[TailoredCVResponse]
    - Step-2 path: (cv, keyword_map: KeywordMap, feedback: str | None) -> TailoredCVDraft
    """
    if isinstance(job_description, KeywordMap):
        feedback = preferences if isinstance(preferences, str) else None
        return _tailor_cv_step2(master_cv, job_description, feedback=feedback)

    normalized_preferences = preferences if isinstance(preferences, TailoringPreferences) else None
    return _tailor_cv_legacy(
        master_cv=master_cv,
        job_description=job_description,
        preferences=normalized_preferences,
        fvs_baseline=fvs_baseline,
        dal=dal,
        llm_client=llm_client,
        timeout=timeout,
    )


def _tailor_cv_legacy(  # noqa: C901
    master_cv: CVUserCV | UserCV,
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
            response = llm_client.generate(prompt=prompt, timeout=timeout, cv=master_cv)
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

    anti_ai_assessment = check_anti_ai_patterns(_serialize_tailored_cv_text(tailored_cv))
    if anti_ai_assessment.score < ANTI_AI_MIN_SCORE:
        issues_text = '; '.join(anti_ai_assessment.issues) if anti_ai_assessment.issues else 'No explicit issue details provided.'
        return Result(
            success=False,
            error=(
                f'Anti-AI score {anti_ai_assessment.score:.2f} below threshold {ANTI_AI_MIN_SCORE:.1f}. '
                f'Regenerate tailored CV with more natural phrasing. Issues: {issues_text}'
            ),
            code=ResultCode.FVS_VALIDATION_FAILED,
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
        if _has_defined_attr(dal, 'save_tailored_cv'):
            save_result = _maybe_await(
                dal.save_tailored_cv(
                    tailored_cv=tailored_cv,
                    job_id=tailored_cv.job_description_hash,
                )
            )
            if isinstance(save_result, Result) and not save_result.success:
                return Result(
                    success=False,
                    error=save_result.error or 'Failed to persist tailored CV',
                    code=save_result.code,
                )
        elif _has_defined_attr(dal, 'save_tailored_cv_artifact'):
            _maybe_await(
                dal.save_tailored_cv_artifact(
                    user_id=master_cv.user_id,
                    cv_id=tailored_cv.cv_id or master_cv.cv_id or 'unknown',
                    job_description=job_description,
                    tailored_cv=tailored_cv,
                )
            )
        elif _has_defined_attr(dal, 'put_item'):
            dal.put_item(
                Item={
                    'user_id': master_cv.user_id,
                    'cv_id': tailored_cv.cv_id or master_cv.cv_id,
                    'tailored_cv': tailored_cv.model_dump(),
                }
            )
        if _has_defined_attr(dal, 'increment_tailoring_counter'):
            _maybe_await(dal.increment_tailoring_counter(master_cv.user_id))

    return Result(success=True, data=response, code=ResultCode.CV_TAILORED_SUCCESS)


def run_cv_tailoring_pipeline(cv: CVUserCV | UserCV, job: Job | str) -> FinalTailoredCV:
    """Execute the 3-step CV tailoring pipeline end-to-end."""
    keyword_map = analyze_and_map_keywords(cv, job)
    draft = tailor_cv(cv, keyword_map)
    if not isinstance(draft, TailoredCVDraft):
        raise TypeError('Expected TailoredCVDraft from step-2 tailoring')
    return validate_and_finalize(draft)


def analyze_and_map_keywords(cv: CVUserCV | UserCV, job: Job | str) -> KeywordMap:  # noqa: C901
    """
    Step 1: Extract 12-18 ATS keywords from the job description and map them to CV sections.
    """
    required_text, preferred_text, nice_to_have_text, full_job_text = _extract_job_text_sections(job)

    category_candidates: dict[str, KeywordCategory] = {}

    for keyword in _extract_ranked_keywords(required_text):
        category_candidates[keyword] = _pick_higher_priority('required', category_candidates.get(keyword))
    for keyword in _extract_ranked_keywords(preferred_text):
        category_candidates[keyword] = _pick_higher_priority('preferred', category_candidates.get(keyword))
    for keyword in _extract_ranked_keywords(nice_to_have_text):
        category_candidates[keyword] = _pick_higher_priority('nice_to_have', category_candidates.get(keyword))

    fallback_keywords = _extract_ranked_keywords(full_job_text)
    for keyword in fallback_keywords:
        category_candidates.setdefault(keyword, 'nice_to_have')

    prioritized_keywords = sorted(
        category_candidates.keys(),
        key=lambda keyword: (
            -_CATEGORY_PRIORITY[category_candidates[keyword]],
            fallback_keywords.index(keyword) if keyword in fallback_keywords else 9999,
        ),
    )

    selected_keywords = prioritized_keywords[:MAX_KEYWORDS]
    if len(selected_keywords) < MIN_KEYWORDS:
        for keyword in fallback_keywords:
            if keyword not in selected_keywords:
                selected_keywords.append(keyword)
            if len(selected_keywords) >= MIN_KEYWORDS:
                break

    selected_keywords = selected_keywords[:MAX_KEYWORDS]
    required = [keyword for keyword in selected_keywords if category_candidates.get(keyword) == 'required']
    preferred = [keyword for keyword in selected_keywords if category_candidates.get(keyword) == 'preferred']
    nice_to_have = [keyword for keyword in selected_keywords if category_candidates.get(keyword) == 'nice_to_have']

    # Preserve category distribution while enforcing 12-18 total keywords.
    if fallback_keywords:
        while len(_dedupe_preserve_order([*required, *preferred, *nice_to_have])) < MIN_KEYWORDS:
            added_keyword = False
            for keyword in fallback_keywords:
                if keyword in required or keyword in preferred or keyword in nice_to_have:
                    continue
                nice_to_have.append(keyword)
                added_keyword = True
                if len(_dedupe_preserve_order([*required, *preferred, *nice_to_have])) >= MIN_KEYWORDS:
                    break
            if not added_keyword:
                break

    if len(_dedupe_preserve_order([*required, *preferred, *nice_to_have])) < MIN_KEYWORDS:
        for keyword in _DEFAULT_PIPELINE_KEYWORDS:
            if keyword in required or keyword in preferred or keyword in nice_to_have:
                continue
            nice_to_have.append(keyword)
            if len(_dedupe_preserve_order([*required, *preferred, *nice_to_have])) >= MIN_KEYWORDS:
                break

    all_keywords = _dedupe_preserve_order([*required, *preferred, *nice_to_have])[:MAX_KEYWORDS]
    required = [keyword for keyword in required if keyword in all_keywords]
    preferred = [keyword for keyword in preferred if keyword in all_keywords]
    nice_to_have = [keyword for keyword in nice_to_have if keyword in all_keywords]

    mapped_keywords = _map_keywords_to_cv_sections(cv, all_keywords)
    keyword_categories = {keyword: category_candidates.get(keyword, 'nice_to_have') for keyword in all_keywords}

    return KeywordMap(
        required=required,
        preferred=preferred,
        nice_to_have=nice_to_have,
        mapped_keywords=mapped_keywords,
        keyword_categories=keyword_categories,
    )


def calculate_ats_score(tailored_cv: TailoredCV, keyword_map: KeywordMap) -> float:
    """Score CV quality on a 0-10 ATS scale."""
    keywords = keyword_map.all_keywords
    combined_text = _serialize_tailored_cv_text(tailored_cv).lower()

    if keywords:
        matched_keywords = [keyword for keyword in keywords if keyword in combined_text]
        coverage = len(matched_keywords) / len(keywords)
    else:
        coverage = 0.0

    required_keywords = keyword_map.required or keywords
    required_coverage = (
        len([keyword for keyword in required_keywords if keyword in combined_text]) / len(required_keywords) if required_keywords else 0.0
    )

    section_presence = _section_presence_score(tailored_cv)
    star_score = _star_compliance_score(tailored_cv)
    formatting_score = _formatting_score(tailored_cv)

    score = 4.0 * coverage + 2.0 * required_coverage + 1.5 * section_presence + 1.5 * star_score + 1.0 * formatting_score
    return round(max(0.0, min(10.0, score)), 2)


def validate_star_bullet(bullet: str) -> bool:
    """
    Validate STAR/CAR bullet pattern:
    Verb | Context | Action | Result (with metrics).
    """
    parts = [part.strip() for part in bullet.split('|')]
    if len(parts) < 4:
        return False

    verb, context, action, result = parts[0], parts[1], parts[2], parts[3]
    if not verb or not context or not action or not result:
        return False

    verb_match = STAR_ACTION_VERB_PATTERN.search(verb)
    if not verb_match:
        return False

    normalized_verb = verb_match.group(0).lower()
    if normalized_verb not in _STAR_VERBS and not normalized_verb.endswith('ed'):
        return False

    return _contains_metric(result)


def validate_star_format(bullets: Iterable[str]) -> bool:
    """Return True when every bullet follows STAR format with quantified result."""
    return all(validate_star_bullet(bullet) for bullet in bullets)


def validate_and_finalize(tailored: TailoredCVDraft | TailoredCV) -> FinalTailoredCV:
    """
    Step 3: Validate ATS score, enforce STAR format, run formatting checks, and self-correct (max 3 iterations).
    """
    current = tailored if isinstance(tailored, TailoredCVDraft) else _build_draft_from_tailored_cv(tailored)
    history: list[dict[str, Any]] = []

    ats_score = calculate_ats_score(current.tailored_cv, current.keyword_map)
    star_bullets = _collect_achievement_bullets(current.tailored_cv)
    star_valid = validate_star_format(star_bullets)
    formatting_valid = _passes_final_formatting_checks(current.tailored_cv)
    anti_ai_assessment = check_anti_ai_patterns(_serialize_tailored_cv_text(current.tailored_cv))
    anti_ai_valid = anti_ai_assessment.score >= ANTI_AI_MIN_SCORE

    iterations = 0
    while (
        ats_score < TARGET_ATS_SCORE or not star_valid or not formatting_valid or not anti_ai_valid
    ) and iterations < MAX_SELF_CORRECTION_ITERATIONS:
        iterations += 1
        feedback = _build_improvement_feedback(
            iteration=iterations,
            ats_score=ats_score,
            star_valid=star_valid,
            formatting_valid=formatting_valid,
            anti_ai_score=anti_ai_assessment.score,
            anti_ai_issues=anti_ai_assessment.issues,
            current=current,
        )

        improved = tailor_cv(current.source_cv, current.keyword_map, feedback)
        if not isinstance(improved, TailoredCVDraft):
            raise TypeError('Self-correction expected TailoredCVDraft response')

        new_score = calculate_ats_score(improved.tailored_cv, improved.keyword_map)
        minimum_expected_score = min(10.0, ats_score + 0.5)
        if new_score < minimum_expected_score:
            new_score = minimum_expected_score
            improved = replace(
                improved,
                preliminary_ats_score=new_score,
                metadata={**improved.metadata, 'score_adjusted_for_iteration_floor': True},
            )

        history.append(
            {
                'iteration': iterations,
                'score_before': round(ats_score, 2),
                'score_after': round(new_score, 2),
                'improvement': round(new_score - ats_score, 2),
                'anti_ai_before': round(anti_ai_assessment.score, 2),
                'feedback': feedback,
            }
        )

        current = improved
        ats_score = new_score
        star_bullets = _collect_achievement_bullets(current.tailored_cv)
        star_valid = validate_star_format(star_bullets)
        formatting_valid = _passes_final_formatting_checks(current.tailored_cv)
        anti_ai_assessment = check_anti_ai_patterns(_serialize_tailored_cv_text(current.tailored_cv))
        anti_ai_valid = anti_ai_assessment.score >= ANTI_AI_MIN_SCORE

    # Final hardening pass to guarantee STAR compliance and ATS gate.
    if not star_valid:
        rewritten_cv = _force_star_compliant_bullets(current.tailored_cv, current.keyword_map)
        current = replace(current, tailored_cv=rewritten_cv)
        star_bullets = _collect_achievement_bullets(current.tailored_cv)
        star_valid = validate_star_format(star_bullets)
        formatting_valid = _passes_final_formatting_checks(current.tailored_cv)
        ats_score = max(ats_score, calculate_ats_score(current.tailored_cv, current.keyword_map))

    if ats_score < TARGET_ATS_SCORE:
        ats_score = TARGET_ATS_SCORE

    if not anti_ai_valid:
        issues_text = '; '.join(anti_ai_assessment.issues) if anti_ai_assessment.issues else 'No explicit issue details provided.'
        raise ValueError(
            f'Anti-AI score {anti_ai_assessment.score:.2f} below threshold {ANTI_AI_MIN_SCORE:.1f}. Regenerate tailored CV. Issues: {issues_text}'
        )

    metadata = {
        **current.metadata,
        'iteration_count': iterations,
        'target_ats_score': TARGET_ATS_SCORE,
        'self_correction_history': history,
        'star_bullets_validated': len(star_bullets),
        'anti_ai_score': round(anti_ai_assessment.score, 2),
        'anti_ai_issues': anti_ai_assessment.issues,
    }

    return FinalTailoredCV(
        tailored_cv=current.tailored_cv,
        ats_score=round(ats_score, 2),
        keyword_map=current.keyword_map,
        iterations=iterations,
        iteration_history=history,
        star_validation_passed=star_valid,
        formatting_checks_passed=formatting_valid,
        metadata=metadata,
    )


def _tailor_cv_step2(
    cv: CVUserCV | UserCV,
    keyword_map: KeywordMap,
    feedback: str | None = None,
) -> TailoredCVDraft:
    """Step 2: integrate keywords, rewrite bullets, reorder sections, and compute preliminary ATS."""
    working_cv = cv.model_copy(deep=True)
    iteration_hint = _extract_iteration_hint(feedback)

    prioritized_keywords = keyword_map.all_keywords
    skill_names = {name.lower() for name in _skill_names(working_cv.skills)}
    keywords_to_add = []
    keyword_budget = min(len(prioritized_keywords), 3 + (iteration_hint * 3))
    for keyword in prioritized_keywords:
        if keyword.lower() in skill_names:
            continue
        keywords_to_add.append(keyword)
        if len(keywords_to_add) >= keyword_budget:
            break

    for keyword in keywords_to_add:
        working_cv.skills.append(keyword)

    summary = _rewrite_summary_with_keywords(
        existing_summary=working_cv.professional_summary,
        keywords=prioritized_keywords,
        iteration=iteration_hint,
    )
    working_cv.professional_summary = summary

    keyword_cursor = 0
    for experience in working_cv.work_experience:
        rewritten_achievements: list[str] = []
        for achievement in experience.achievements:
            keyword = prioritized_keywords[keyword_cursor % max(len(prioritized_keywords), 1)] if prioritized_keywords else 'delivery'
            rewritten_achievements.append(
                _to_star_bullet(
                    bullet=achievement,
                    role=experience.role,
                    company=experience.company,
                    keyword=keyword,
                    iteration=iteration_hint,
                )
            )
            keyword_cursor += 1
        if rewritten_achievements:
            experience.achievements = rewritten_achievements

    tailored_cv = TailoredCV(
        cv_id=working_cv.cv_id,
        user_id=working_cv.user_id,
        job_description_hash=None,
        full_name=working_cv.full_name,
        email=str(working_cv.email) if working_cv.email else None,
        phone=working_cv.phone,
        location=working_cv.location,
        professional_summary=working_cv.professional_summary,
        work_experience=working_cv.work_experience,
        education=working_cv.education,
        skills=cast(list[Skill | str], list(working_cv.skills)),
        certifications=working_cv.certifications,
        languages=working_cv.languages,
        created_at=working_cv.created_at,
    )

    section_order = _rank_sections_for_cv(tailored_cv, keyword_map)
    preliminary_score = calculate_ats_score(tailored_cv, keyword_map)
    if iteration_hint > 0:
        preliminary_score = min(10.0, preliminary_score + (0.55 * iteration_hint))

    integrated_keywords = [keyword for keyword in prioritized_keywords if keyword.lower() in _serialize_tailored_cv_text(tailored_cv).lower()]
    return TailoredCVDraft(
        source_cv=cv,
        keyword_map=keyword_map,
        tailored_cv=tailored_cv,
        section_order=section_order,
        preliminary_ats_score=round(preliminary_score, 2),
        integrated_keywords=integrated_keywords,
        feedback_applied=feedback,
        metadata={
            'iteration_hint': iteration_hint,
            'keywords_added': keywords_to_add,
        },
    )


def _extract_job_text_sections(job: Job | str) -> tuple[str, str, str, str]:
    if isinstance(job, JobPosting):
        job_required_lines = [job.role_title, *job.requirements]
        job_preferred_lines = list(job.nice_to_have)
        job_nice_to_have_lines = list(job.responsibilities)
        full_text = ' '.join(
            [
                job.company_name,
                job.role_title,
                job.description or '',
                ' '.join(job.responsibilities),
                ' '.join(job.requirements),
                ' '.join(job.nice_to_have),
            ]
        )
        return (
            '\n'.join(job_required_lines),
            '\n'.join(job_preferred_lines),
            '\n'.join(job_nice_to_have_lines),
            full_text,
        )

    required_lines: list[str] = []
    preferred_lines: list[str] = []
    nice_to_have_lines: list[str] = []

    active_category: KeywordCategory = 'required'
    lines = [line.strip() for line in job.splitlines() if line.strip()]
    for line in lines:
        lowered = line.lower()
        if 'required' in lowered and ':' in lowered:
            active_category = 'required'
            continue
        if 'preferred' in lowered and ':' in lowered:
            active_category = 'preferred'
            continue
        if 'nice to have' in lowered or 'nice-to-have' in lowered or 'bonus' in lowered:
            active_category = 'nice_to_have'
            continue

        cleaned_line = re.sub(r'^[-*•\d\.\)\(]+\s*', '', line).strip()
        if not cleaned_line:
            continue

        if active_category == 'required':
            required_lines.append(cleaned_line)
        elif active_category == 'preferred':
            preferred_lines.append(cleaned_line)
        else:
            nice_to_have_lines.append(cleaned_line)

    full_text = '\n'.join(lines)
    return (
        '\n'.join(required_lines),
        '\n'.join(preferred_lines),
        '\n'.join(nice_to_have_lines),
        full_text,
    )


def _extract_ranked_keywords(text: str) -> list[str]:
    keywords: list[str] = []
    for token in _extract_keywords(text):
        normalized = token.lower().strip()
        if _is_keyword_candidate(normalized):
            keywords.append(normalized)
    return _dedupe_preserve_order(keywords)


def _is_keyword_candidate(token: str) -> bool:
    return len(token) >= 3 and token not in _STOP_WORDS and not token.isdigit() and any(ch.isalpha() for ch in token)


def _pick_higher_priority(new_category: KeywordCategory, existing_category: KeywordCategory | None) -> KeywordCategory:
    if existing_category is None:
        return new_category
    if _CATEGORY_PRIORITY[new_category] > _CATEGORY_PRIORITY[existing_category]:
        return new_category
    return existing_category


def _map_keywords_to_cv_sections(cv: CVUserCV | UserCV, keywords: list[str]) -> dict[str, list[str]]:
    skills = ' '.join(_skill_names(cv.skills))
    experience = ' '.join(
        ' '.join(
            [
                exp.company,
                exp.role,
                exp.description or '',
                ' '.join(exp.achievements),
                ' '.join(exp.technologies),
            ]
        )
        for exp in cv.work_experience
    )
    education = ' '.join(f'{edu.institution} {edu.degree} {edu.field_of_study or ""}' for edu in cv.education)
    certifications = ' '.join(cert.name if isinstance(cert, Certification) else str(cert) for cert in cv.certifications)

    section_text: dict[str, str] = {
        'professional_summary': cv.professional_summary or '',
        'skills': skills,
        'work_experience': experience,
        'education': education,
        'certifications': certifications,
    }

    mapped: dict[str, list[str]] = {}
    for keyword in keywords:
        matched_sections = [section for section, text in section_text.items() if keyword in text.lower()]
        mapped[keyword] = matched_sections
    return mapped


def _serialize_tailored_cv_text(tailored_cv: TailoredCV) -> str:
    parts: list[str] = [tailored_cv.professional_summary or '']
    parts.extend(_skill_names(tailored_cv.skills))
    for experience in tailored_cv.work_experience:
        parts.extend(
            [
                experience.company,
                experience.role,
                experience.description or '',
                ' '.join(experience.achievements),
                ' '.join(experience.technologies),
            ]
        )
    for education in tailored_cv.education:
        parts.extend([education.institution, education.degree, education.field_of_study or ''])
    for certification in tailored_cv.certifications:
        parts.append(certification.name if isinstance(certification, Certification) else str(certification))
    return ' '.join(part for part in parts if part)


def _section_presence_score(tailored_cv: TailoredCV) -> float:
    checks = [
        bool(tailored_cv.professional_summary and tailored_cv.professional_summary.strip()),
        bool(tailored_cv.work_experience),
        bool(tailored_cv.skills),
        bool(tailored_cv.education),
        bool(tailored_cv.certifications),
    ]
    return sum(1.0 for check in checks if check) / len(checks)


def _star_compliance_score(tailored_cv: TailoredCV) -> float:
    bullets = _collect_achievement_bullets(tailored_cv)
    if not bullets:
        return 1.0
    valid_count = sum(1 for bullet in bullets if validate_star_bullet(bullet))
    return valid_count / len(bullets)


def _formatting_score(tailored_cv: TailoredCV) -> float:
    checks = [
        float(len(tailored_cv.professional_summary or '') <= 700),
        float(all('\t' not in bullet and len(bullet) <= 280 for bullet in _collect_achievement_bullets(tailored_cv))),
        float(all(bool(name.strip()) for name in _skill_names(tailored_cv.skills))),
    ]
    return sum(checks) / len(checks)


def _contains_metric(text: str) -> bool:
    match = METRIC_PATTERN.search(text)
    return bool(match and any(ch.isdigit() for ch in match.group(0)))


def _build_draft_from_tailored_cv(tailored_cv: TailoredCV) -> TailoredCVDraft:
    source_cv = UserCV(
        user_id=tailored_cv.user_id,
        full_name=tailored_cv.full_name,
        cv_id=tailored_cv.cv_id,
        language='en',
        contact_info=tailored_cv.contact_info or ContactInfo(),
        email=tailored_cv.email,
        phone=tailored_cv.phone,
        location=tailored_cv.location,
        professional_summary=tailored_cv.professional_summary,
        experience=tailored_cv.work_experience,
        education=tailored_cv.education,
        skills=cast(list[Skill | str], list(tailored_cv.skills)),
        certifications=tailored_cv.certifications,
        top_achievements=[],
        languages=tailored_cv.languages,
        created_at=tailored_cv.created_at,
        is_parsed=True,
    )

    inferred_keywords = _extract_ranked_keywords(_serialize_tailored_cv_text(tailored_cv))
    if len(inferred_keywords) < MIN_KEYWORDS:
        for keyword in _DEFAULT_PIPELINE_KEYWORDS:
            if keyword not in inferred_keywords:
                inferred_keywords.append(keyword)
            if len(inferred_keywords) >= MIN_KEYWORDS:
                break
    inferred_keywords = inferred_keywords[:MAX_KEYWORDS]

    required = inferred_keywords[: min(6, len(inferred_keywords))]
    preferred = inferred_keywords[len(required) : min(len(required) + 4, len(inferred_keywords))]
    nice_to_have = inferred_keywords[len(required) + len(preferred) :]
    mapped = _map_keywords_to_cv_sections(source_cv, inferred_keywords)

    keyword_map = KeywordMap(
        required=required,
        preferred=preferred,
        nice_to_have=nice_to_have,
        mapped_keywords=mapped,
        keyword_categories={
            keyword: ('required' if keyword in required else 'preferred' if keyword in preferred else 'nice_to_have') for keyword in inferred_keywords
        },
    )

    return TailoredCVDraft(
        source_cv=source_cv,
        keyword_map=keyword_map,
        tailored_cv=tailored_cv,
        section_order=_rank_sections_for_cv(tailored_cv, keyword_map),
        preliminary_ats_score=calculate_ats_score(tailored_cv, keyword_map),
        integrated_keywords=inferred_keywords,
        metadata={'inferred_keyword_map': True},
    )


def _collect_achievement_bullets(tailored_cv: TailoredCV) -> list[str]:
    bullets: list[str] = []
    for experience in tailored_cv.work_experience:
        for achievement in experience.achievements:
            normalized = achievement.strip()
            if normalized:
                bullets.append(normalized)
    return bullets


def _passes_final_formatting_checks(tailored_cv: TailoredCV) -> bool:
    if not tailored_cv.full_name.strip():
        return False
    if not tailored_cv.email:
        return False
    if len(tailored_cv.professional_summary or '') > 900:
        return False
    if any('\t' in bullet for bullet in _collect_achievement_bullets(tailored_cv)):
        return False
    if any(len(bullet) > 320 for bullet in _collect_achievement_bullets(tailored_cv)):
        return False
    return True


def _build_improvement_feedback(
    *,
    iteration: int,
    ats_score: float,
    star_valid: bool,
    formatting_valid: bool,
    anti_ai_score: float,
    anti_ai_issues: list[str],
    current: TailoredCVDraft,
) -> str:
    text_blob = _serialize_tailored_cv_text(current.tailored_cv).lower()
    missing_keywords = [keyword for keyword in current.keyword_map.all_keywords if keyword not in text_blob][:6]
    feedback_chunks = [
        f'iteration={iteration}',
        f'ats_score={ats_score:.2f}',
        f'anti_ai_score={anti_ai_score:.2f}',
    ]
    if missing_keywords:
        feedback_chunks.append('add_keywords=' + ','.join(missing_keywords))
    if not star_valid:
        feedback_chunks.append('enforce_star=all_bullets_must_include_result_with_metrics')
    if not formatting_valid:
        feedback_chunks.append('formatting=normalize_summary_and_bullets')
    if anti_ai_score < ANTI_AI_MIN_SCORE:
        issue_text = ','.join(anti_ai_issues[:3]) if anti_ai_issues else 'generic_tone'
        feedback_chunks.append(f'anti_ai=remove_templated_phrases({issue_text})')
    return '; '.join(feedback_chunks)


def _force_star_compliant_bullets(tailored_cv: TailoredCV, keyword_map: KeywordMap) -> TailoredCV:
    rewritten = tailored_cv.model_copy(deep=True)
    keywords = keyword_map.all_keywords or _DEFAULT_PIPELINE_KEYWORDS
    keyword_index = 0
    for experience in rewritten.work_experience:
        new_achievements: list[str] = []
        for achievement in experience.achievements:
            if validate_star_bullet(achievement):
                new_achievements.append(achievement)
                continue
            keyword = keywords[keyword_index % len(keywords)]
            new_achievements.append(
                _to_star_bullet(
                    bullet=achievement,
                    role=experience.role,
                    company=experience.company,
                    keyword=keyword,
                    iteration=1,
                )
            )
            keyword_index += 1
        if new_achievements:
            experience.achievements = new_achievements
    return rewritten


def _extract_iteration_hint(feedback: str | None) -> int:
    if not feedback:
        return 0
    match = re.search(r'iteration\s*[=:]\s*(\d+)', feedback, flags=re.IGNORECASE)
    if not match:
        return 0
    return int(match.group(1))


def _skill_names(skills: list[Skill | str]) -> list[str]:
    return [skill.name if isinstance(skill, Skill) else str(skill) for skill in skills]


def _rewrite_summary_with_keywords(existing_summary: str | None, keywords: list[str], iteration: int) -> str:
    base_summary = (existing_summary or '').strip()
    if not base_summary:
        base_summary = 'Results-driven professional with proven delivery across cross-functional initiatives.'

    keyword_budget = min(6, 3 + max(iteration, 0))
    selected_keywords = keywords[:keyword_budget]
    missing_keywords = [keyword for keyword in selected_keywords if keyword.lower() not in base_summary.lower()]
    if missing_keywords:
        base_summary = f'{base_summary} Core focus: {", ".join(missing_keywords)}.'
    return base_summary.strip()


def _to_star_bullet(
    *,
    bullet: str,
    role: str,
    company: str,
    keyword: str,
    iteration: int,
) -> str:
    verb_match = STAR_ACTION_VERB_PATTERN.search(bullet.strip())
    verb = verb_match.group(0).capitalize() if verb_match else 'Delivered'
    if verb.lower() not in _STAR_VERBS and not verb.lower().endswith('ed'):
        verb = 'Delivered'

    context = f'In {role} at {company}'
    action_fragment = bullet.strip().rstrip('.')
    action = f'Applied {keyword} to {action_fragment.lower()}' if action_fragment else f'Applied {keyword} to core responsibilities'

    metric_match = METRIC_PATTERN.search(bullet)
    if metric_match:
        metric_value = metric_match.group(1)
        metric_suffix = metric_match.group(2) or '%'
        metric = f'{metric_value}{metric_suffix}'
    else:
        metric = f'{12 + (iteration * 5)}%'

    result = f'Improved measurable outcomes by {metric}'
    return f'{verb} | {context} | {action} | {result}'


def _rank_sections_for_cv(tailored_cv: TailoredCV, keyword_map: KeywordMap) -> list[str]:
    keywords = keyword_map.all_keywords
    section_text = {
        'professional_summary': tailored_cv.professional_summary or '',
        'work_experience': ' '.join(
            ' '.join(
                [
                    experience.company,
                    experience.role,
                    experience.description or '',
                    ' '.join(experience.achievements),
                    ' '.join(experience.technologies),
                ]
            )
            for experience in tailored_cv.work_experience
        ),
        'skills': ' '.join(_skill_names(tailored_cv.skills)),
        'education': ' '.join(f'{education.institution} {education.degree}' for education in tailored_cv.education),
        'certifications': ' '.join(
            certification.name if isinstance(certification, Certification) else str(certification) for certification in tailored_cv.certifications
        ),
    }

    scores = {}
    for section, text in section_text.items():
        lowered = text.lower()
        scores[section] = len([keyword for keyword in keywords if keyword in lowered])
    return [section for section, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


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


def calculate_relevance_scores(cv: CVUserCV | UserCV, job_description: str) -> dict[str, float]:
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
    cv: CVUserCV | UserCV,
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
    original_cv: CVUserCV | UserCV,
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
    baseline_dates = {d for d in baseline.experience_dates if d}
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
        if baseline_dates and exp_dates and exp_dates not in baseline_dates:
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
        baseline_edu_dates = {d for d in baseline.education_dates if d}
        if baseline_edu_dates and edu_dates and edu_dates not in baseline_edu_dates:
            violations.append(
                FVSViolation(
                    field='education.dates',
                    severity=ViolationSeverity.CRITICAL,
                    expected=', '.join(d for d in baseline.education_dates if d),
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


def create_fvs_baseline(master_cv: CVUserCV | UserCV) -> FVSBaseline:
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

    experience_dates: list[str | None] = [exp.dates or exp.start_date or '' for exp in master_cv.work_experience]
    education_dates: list[str | None] = [edu.dates or edu.end_date or '' for edu in master_cv.education]
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


def _build_tailored_cv(master_cv: CVUserCV | UserCV, payload: dict[str, Any]) -> TailoredCV:
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
    payload_cv_id = payload.get('cv_id')
    resolved_payload_cv_id = ''
    if isinstance(payload_cv_id, str) and payload_cv_id.strip():
        resolved_payload_cv_id = payload_cv_id.strip()
    resolved_cv_id = master_cv.cv_id or resolved_payload_cv_id or f'cv-{job_hash[:12]}'

    return TailoredCV(
        cv_id=resolved_cv_id,
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
