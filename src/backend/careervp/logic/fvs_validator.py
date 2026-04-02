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
from logging import getLogger
from typing import Any, Iterable, cast

from careervp.models.cv import Skill, UserCV
from careervp.models.fvs import FVSBaseline as TailoringFVSBaseline
from careervp.models.fvs import FVSValidationResult as TailoringFVSValidationResult
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import VPR

try:
    from careervp.handlers.utils.observability import logger
except Exception:  # noqa: BLE001
    logger = cast(Any, getLogger(__name__))


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


@dataclass(frozen=True)
class AntiAIPatternResult:
    """Structured anti-AI pattern assessment output."""

    score: float
    issues: list[str]


@dataclass(frozen=True)
class ValidationCheckResult:
    """Result object for a single quality check."""

    score: float
    issues: list[str]
    min_score: float

    @property
    def passed(self) -> bool:
        return self.score >= self.min_score


@dataclass(frozen=True)
class CrossDocumentConsistencyResult:
    """Cross-document factual consistency score and issue list."""

    score: float
    contradictions: list[str]

    @property
    def passed(self) -> bool:
        return self.score >= 9.0 and not self.contradictions


@dataclass(frozen=True)
class FVSQualityReport:
    """Aggregate FVS quality output per specification checks."""

    overall_score: float
    grammar_score: float
    tone_score: float
    ai_pattern_score: float
    formatting_score: float
    structure_score: float
    ats_score: float | None
    consistency_score: float | None
    issues: list[str]
    recommendations: list[str]

    @property
    def passes_quality_gate(self) -> bool:
        base_pass = (
            self.grammar_score >= GRAMMAR_MIN_SCORE
            and self.tone_score >= TONE_MIN_SCORE
            and self.ai_pattern_score >= ANTI_AI_MIN_SCORE
            and self.formatting_score >= FORMATTING_MIN_SCORE
            and self.structure_score >= STRUCTURE_MIN_SCORE
        )
        ats_pass = self.ats_score is None or self.ats_score >= ATS_MIN_SCORE
        consistency_pass = self.consistency_score is None or self.consistency_score >= 9.0
        return base_pass and ats_pass and consistency_pass


GRAMMAR_MIN_SCORE = 9.0
TONE_MIN_SCORE = 8.0
ANTI_AI_MIN_SCORE = 9.0
FORMATTING_MIN_SCORE = 8.0
STRUCTURE_MIN_SCORE = 8.0
ATS_MIN_SCORE = 8.0


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
    violations: list[FVSViolation] = []
    immutable = baseline.get('immutable_facts', {})

    violations.extend(_validate_full_name(baseline, generated))
    violations.extend(_validate_contact_info(immutable, generated))
    violations.extend(_validate_work_history(immutable, generated))
    violations.extend(_validate_education(immutable, generated))

    # Log violations
    if violations:
        logger.warning(
            'FVS violations detected',
            violation_count=len(violations),
            critical_count=sum(1 for v in violations if v.severity == 'CRITICAL'),
            violations=[{'field': v.field, 'expected': v.expected, 'actual': v.actual} for v in violations],
        )

    return FVSValidationResult(is_valid=len(violations) == 0, violations=violations)


def _validate_full_name(baseline: dict[str, Any], generated: UserCV) -> list[FVSViolation]:
    expected_name = baseline.get('full_name', '').upper()
    actual_name = generated.full_name.upper() if generated.full_name else ''
    if expected_name and actual_name and expected_name != actual_name:
        return [
            FVSViolation(
                field='full_name',
                expected=baseline.get('full_name', ''),
                actual=generated.full_name,
                severity='CRITICAL',
            )
        ]
    return []


def _validate_contact_info(immutable: dict[str, Any], generated: UserCV) -> list[FVSViolation]:
    violations: list[FVSViolation] = []
    baseline_contact = immutable.get('contact_info', {})
    if not baseline_contact:
        return violations

    gen_contact = generated.contact_info
    if gen_contact is None:
        return violations
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
    return violations


def _find_matching_entry(collection: Iterable[Any], target: str, attr: str) -> Any | None:
    target_normalized = target.lower()
    for item in collection:
        value = getattr(item, attr, '')
        if value.lower() == target_normalized:
            return item
    return None


def _validate_work_history(immutable: dict[str, Any], generated: UserCV) -> list[FVSViolation]:
    violations: list[FVSViolation] = []
    baseline_work = immutable.get('work_history', [])
    for baseline_job in baseline_work:
        baseline_company = baseline_job.get('company', '')
        baseline_role = baseline_job.get('role', '')
        baseline_dates = baseline_job.get('dates', '')

        matching_job = _find_matching_entry(generated.experience, baseline_company, 'company')
        if not matching_job:
            continue

        if baseline_role and matching_job.role != baseline_role:
            violations.append(
                FVSViolation(
                    field=f'work_history.{baseline_company.lower()}.role',
                    expected=baseline_role,
                    actual=matching_job.role,
                    severity='CRITICAL',
                )
            )

        if baseline_dates and matching_job.dates != baseline_dates:
            violations.append(
                FVSViolation(
                    field=f'work_history.{baseline_company.lower()}.dates',
                    expected=baseline_dates,
                    actual=matching_job.dates,
                    severity='CRITICAL',
                )
            )
    return violations


def _validate_education(immutable: dict[str, Any], generated: UserCV) -> list[FVSViolation]:
    violations: list[FVSViolation] = []
    baseline_edu = immutable.get('education', [])
    for baseline_school in baseline_edu:
        baseline_institution = baseline_school.get('institution', '')
        baseline_degree = baseline_school.get('degree', '')

        matching_edu = _find_matching_entry(generated.education, baseline_institution, 'institution')
        if not matching_edu:
            continue

        if baseline_degree and matching_edu.degree != baseline_degree:
            violations.append(
                FVSViolation(
                    field=f'education.{baseline_institution.lower()}.degree',
                    expected=baseline_degree,
                    actual=matching_edu.degree,
                    severity='CRITICAL',
                )
            )
    return violations


def validate_verifiable_skills(baseline: dict[str, Any], generated: UserCV) -> FVSValidationResult:
    """
    Validate that generated skills exist in the baseline verifiable skills list.

    Skills can be reframed but must have a source in the original CV.
    """
    violations = []
    verifiable_skills = [s.lower() for s in baseline.get('verifiable_skills', [])]

    for skill in generated.skills:
        skill_value = skill.name if isinstance(skill, Skill) else str(skill)
        skill_lower = skill_value.lower()
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
                    actual=skill_value,
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
ANTI_AI_BANNED_TERMS = (
    'leverage',
    'delve into',
    'landscape',
    'robust',
    'streamline',
    'utilize',
    'facilitate',
    'implement',
    'cutting-edge',
    'best practices',
    'industry-leading',
    'game-changer',
    'paradigm shift',
    'synergy',
)
TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9'/-]*")
DOUBLE_SPACE_PATTERN = re.compile(r' {2,}')
SENTENCE_SPLIT_PATTERN = re.compile(r'[.!?]+')
NOISY_PUNCTUATION_PATTERN = re.compile(r'[!?]{2,}|\.{4,}')
SPACE_BEFORE_PUNCT_PATTERN = re.compile(r'\s+[,.!?;:]')
NUMBER_PATTERN = re.compile(r'\b\d+(?:\.\d+)?%?\b')

ROBOTIC_TRANSITIONS = (
    'furthermore',
    'moreover',
    'additionally',
    'in conclusion',
    'in summary',
)
ROBOTIC_FILLER_PHRASES = (
    "in today's fast-paced",
    'across the organization',
    'in order to',
    'at the end of the day',
    'from a strategic perspective',
)
CASUAL_TONE_TERMS = (
    'awesome',
    'super',
    'kinda',
    'sorta',
    'gonna',
    'cool',
)
HEDGING_TERMS = (
    'maybe',
    'might',
    'perhaps',
    'i think',
    'kind of',
    'sort of',
)
CLOSING_MARKERS = (
    'thank you',
    'i would welcome',
    'i look forward',
    'in closing',
    'sincerely',
)
ATS_ACTION_VERBS = (
    'led',
    'built',
    'delivered',
    'improved',
    'reduced',
    'launched',
    'designed',
    'implemented',
    'managed',
    'optimized',
)
ATS_DEFAULT_KEYWORDS = (
    'python',
    'aws',
    'leadership',
    'collaboration',
    'strategy',
    'delivery',
)
COMMON_TYPOS = (
    'teh',
    'recieve',
    'definately',
    'seperate',
    'occurence',
    'adress',
    'enviroment',
    'resposibility',
)


@dataclass(frozen=True)
class _DocumentFacts:
    years: set[str]
    companies: set[str]
    roles: set[str]


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

    # TODO spec-04: update to traverse new 10-section VPR structure
    sections: list[str] = []
    sections.extend(item.evidence for item in vpr.evidence_matrix if item.evidence)  # type: ignore[attr-defined]
    sections.extend(vpr.differentiators)  # type: ignore[arg-type]
    sections.extend(vpr.talking_points)  # type: ignore[attr-defined]
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
        if experience.dates:
            years.update(YEAR_PATTERN.findall(experience.dates))
    for education in user_cv.education:
        if education.graduation_date:
            years.update(YEAR_PATTERN.findall(education.graduation_date))
    return years


def _extract_company_mentions(text: str) -> list[str]:
    return COMPANY_PATTERN.findall(text)


def _extract_title_mentions(text: str) -> list[str]:
    cleaned_titles: list[str] = []
    for match in TITLE_PATTERN.findall(text):
        raw_title = match.strip()
        title = re.split(r'\b(?:at|with|for|in|on)\b', raw_title, maxsplit=1, flags=re.IGNORECASE)[0].strip(' ,.-')
        if title:
            cleaned_titles.append(title)
    return cleaned_titles


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


def _bounded_score(score: float) -> float:
    return max(0.0, min(10.0, round(score, 2)))


def _split_sentences(content: str) -> list[str]:
    return [sentence.strip() for sentence in SENTENCE_SPLIT_PATTERN.split(content) if sentence.strip()]


def _count_phrase_hits(content: str, phrases: Iterable[str]) -> int:
    return sum(content.count(phrase) for phrase in phrases)


def validate_grammar(content: str) -> ValidationCheckResult:
    """
    Validate grammar using heuristic checks.

    Acts as a LanguageTool-equivalent guard when external grammar tooling is unavailable.
    """
    normalized = content.strip()
    if not normalized:
        return ValidationCheckResult(score=0.0, issues=['Content is empty'], min_score=GRAMMAR_MIN_SCORE)

    score = 10.0
    issues: list[str] = []
    sentences = _split_sentences(normalized)

    typo_hits = [typo for typo in COMMON_TYPOS if re.search(rf'\b{re.escape(typo)}\b', normalized, flags=re.IGNORECASE)]
    if typo_hits:
        score -= min(0.45 * len(typo_hits), 1.8)
        issues.append(f'Potential spelling mistakes: {", ".join(sorted(typo_hits))}')

    noisy_punctuation_hits = len(NOISY_PUNCTUATION_PATTERN.findall(normalized))
    if noisy_punctuation_hits:
        score -= min(0.35 * noisy_punctuation_hits, 1.2)
        issues.append('Noisy punctuation detected (e.g. repeated ! or ?)')

    spacing_errors = len(SPACE_BEFORE_PUNCT_PATTERN.findall(normalized))
    if spacing_errors:
        score -= min(0.25 * spacing_errors, 1.0)
        issues.append('Spacing before punctuation needs normalization')

    double_spaces = len(DOUBLE_SPACE_PATTERN.findall(normalized))
    if double_spaces:
        score -= min(0.2 * double_spaces, 0.8)
        issues.append('Repeated spaces reduce readability')

    sentence_start_errors = sum(1 for sentence in sentences if sentence and sentence[0].isalpha() and sentence[0].islower())
    if sentence_start_errors:
        score -= min(0.3 * sentence_start_errors, 1.2)
        issues.append('Some sentences do not start with capital letters')

    short_sentences = sum(1 for sentence in sentences if len(sentence.split()) <= 2)
    if short_sentences >= 2:
        score -= 0.4
        issues.append('Multiple sentence fragments detected')

    return ValidationCheckResult(score=_bounded_score(score), issues=issues, min_score=GRAMMAR_MIN_SCORE)


def validate_tone(content: str) -> ValidationCheckResult:
    """Validate professional, confident, non-robotic tone."""
    normalized = content.strip()
    if not normalized:
        return ValidationCheckResult(score=0.0, issues=['Content is empty'], min_score=TONE_MIN_SCORE)

    lowered = normalized.lower()
    score = 10.0
    issues: list[str] = []
    sentences = _split_sentences(normalized)

    casual_hits = _count_phrase_hits(lowered, CASUAL_TONE_TERMS)
    if casual_hits:
        score -= min(0.6 * casual_hits, 1.8)
        issues.append('Casual language lowers professional tone')

    hedging_hits = _count_phrase_hits(lowered, HEDGING_TERMS)
    if hedging_hits >= 2:
        score -= min(0.45 * hedging_hits, 1.5)
        issues.append('Excessive hedging weakens confidence')

    exclamation_count = normalized.count('!')
    if exclamation_count > 1:
        score -= min(0.2 * exclamation_count, 0.8)
        issues.append('Excessive exclamation marks sound informal')

    weak_confidence_markers = _count_phrase_hits(lowered, ('i hope', 'i would like', 'i will try'))
    if weak_confidence_markers >= 2:
        score -= 0.6
        issues.append('Tone reads tentative rather than confident')

    if len(sentences) >= 4:
        sentence_lengths = [len(sentence.split()) for sentence in sentences]
        longest = max(sentence_lengths)
        shortest = min(sentence_lengths)
        if longest - shortest <= 4:
            score -= 0.5
            issues.append('Uniform sentence rhythm sounds robotic')

    anti_ai_assessment = check_anti_ai_patterns(normalized)
    if anti_ai_assessment.score < ANTI_AI_MIN_SCORE:
        score -= min(1.4, (ANTI_AI_MIN_SCORE - anti_ai_assessment.score))
        issues.append('Robotic phrasing patterns detected')

    return ValidationCheckResult(score=_bounded_score(score), issues=issues, min_score=TONE_MIN_SCORE)


def validate_formatting(content: str) -> ValidationCheckResult:
    """Validate layout, spacing, and bullet consistency."""
    normalized = content.strip()
    if not normalized:
        return ValidationCheckResult(score=0.0, issues=['Content is empty'], min_score=FORMATTING_MIN_SCORE)

    score = 10.0
    issues: list[str] = []
    lines = [line.rstrip() for line in normalized.splitlines()]
    bullet_lines = [line.lstrip() for line in lines if line.lstrip().startswith(('-', '*', '•'))]

    if bullet_lines:
        bullet_markers = {line[0] for line in bullet_lines if line}
        if len(bullet_markers) > 1:
            score -= 0.7
            issues.append('Mixed bullet styles detected')
        malformed_bullets = [line for line in bullet_lines if len(line) < 2 or line[1] != ' ']
        if malformed_bullets:
            score -= 0.5
            issues.append('Bullets should include a space after the marker')

    long_lines = [line for line in lines if len(line) > 180]
    if long_lines:
        score -= min(0.2 * len(long_lines), 1.0)
        issues.append('Some lines are too long and hurt readability')

    if re.search(r'\n{3,}', normalized):
        score -= 0.4
        issues.append('Large blank-line gaps break visual flow')

    paragraph_count = len([paragraph for paragraph in re.split(r'\n\s*\n', normalized) if paragraph.strip()])
    if paragraph_count < 2 and len(normalized.split()) > 120:
        score -= 0.6
        issues.append('Long text should be split into clearer paragraphs')

    return ValidationCheckResult(score=_bounded_score(score), issues=issues, min_score=FORMATTING_MIN_SCORE)


def validate_content_structure(content: str) -> ValidationCheckResult:
    """Validate intro/body/conclusion presence and logical flow."""
    normalized = content.strip()
    if not normalized:
        return ValidationCheckResult(score=0.0, issues=['Content is empty'], min_score=STRUCTURE_MIN_SCORE)

    issues: list[str] = []
    paragraphs = [paragraph.strip() for paragraph in re.split(r'\n\s*\n', normalized) if paragraph.strip()]
    sentences = _split_sentences(normalized)
    score = 0.0

    if paragraphs and len(paragraphs[0].split()) >= 12:
        score += 2.5
    else:
        issues.append('Missing or weak introduction')

    body_paragraphs = paragraphs[1:-1] if len(paragraphs) >= 3 else paragraphs[1:]
    body_text = ' '.join(body_paragraphs).lower()
    has_body_evidence = bool(NUMBER_PATTERN.search(body_text)) or any(verb in body_text for verb in ATS_ACTION_VERBS)
    if has_body_evidence:
        score += 2.5
    else:
        issues.append('Body section lacks concrete evidence')

    conclusion_text = paragraphs[-1].lower() if paragraphs else normalized.lower()
    if any(marker in conclusion_text for marker in CLOSING_MARKERS):
        score += 2.5
    elif len(paragraphs) >= 3 and len(paragraphs[-1].split()) >= 8:
        score += 1.8
        issues.append('Conclusion exists but could be more explicit')
    else:
        issues.append('Missing clear conclusion')

    has_transitions = any(term in normalized.lower() for term in ('first', 'next', 'then', 'finally', 'therefore', 'because'))
    if has_transitions or len(sentences) >= 4:
        score += 2.5
    else:
        issues.append('Logical flow markers are weak')

    return ValidationCheckResult(score=_bounded_score(score), issues=issues, min_score=STRUCTURE_MIN_SCORE)


def score_ats_content(
    content: str,
    keywords: Iterable[str] | None = None,
    *,
    document_type: str = 'generic',
) -> float:
    """Estimate ATS readiness on a 0-10 scale for CV/cover-letter content."""
    normalized = content.strip().lower()
    if not normalized:
        return 0.0

    normalized_keywords = [keyword.strip().lower() for keyword in (keywords or ATS_DEFAULT_KEYWORDS) if keyword and keyword.strip()]
    if normalized_keywords:
        matched_keyword_count = sum(1 for keyword in normalized_keywords if keyword in normalized)
        keyword_coverage = matched_keyword_count / len(normalized_keywords)
    else:
        keyword_coverage = 0.75

    metric_count = len(NUMBER_PATTERN.findall(normalized))
    metric_score = min(1.0, metric_count / 4.0)

    action_verb_count = sum(1 for verb in ATS_ACTION_VERBS if re.search(rf'\b{re.escape(verb)}\b', normalized))
    action_score = min(1.0, action_verb_count / 4.0)

    if document_type == 'cv':
        structure_markers = ('experience', 'skills', 'education')
        structure_score = sum(1.0 for marker in structure_markers if marker in normalized) / len(structure_markers)
    elif document_type == 'cover_letter':
        paragraph_count = len([paragraph for paragraph in re.split(r'\n\s*\n', content) if paragraph.strip()])
        structure_score = 1.0 if paragraph_count >= 3 else 0.7 if paragraph_count == 2 else 0.5
    else:
        structure_score = 0.8

    score = 4.0 * keyword_coverage + 2.2 * metric_score + 2.0 * action_score + 1.8 * structure_score
    return _bounded_score(score)


def _extract_document_facts(content: str) -> _DocumentFacts:
    years = set(YEAR_PATTERN.findall(content))
    companies = {company.lower().strip() for company in _extract_company_mentions(content) if company.strip()}
    roles = {_normalize(role) for role in _extract_title_mentions(content) if _normalize(role)}
    return _DocumentFacts(years=years, companies=companies, roles=roles)


def check_cross_document_consistency(vpr_content: str, cv_content: str, cover_letter_content: str) -> CrossDocumentConsistencyResult:
    """Compare VPR/CV/Cover Letter content for factual contradictions."""
    cv_facts = _extract_document_facts(cv_content)
    if not cv_facts.years and not cv_facts.companies and not cv_facts.roles:
        return CrossDocumentConsistencyResult(score=0.0, contradictions=['CV baseline facts are missing; cannot validate consistency'])

    contradictions: list[str] = []
    for label, content in (('VPR', vpr_content), ('Cover Letter', cover_letter_content)):
        doc_facts = _extract_document_facts(content)

        for company in sorted(doc_facts.companies - cv_facts.companies):
            contradictions.append(f'{label} references company not present in CV: {company}')

        for year in sorted(doc_facts.years - cv_facts.years):
            contradictions.append(f'{label} references year not present in CV: {year}')

        for role in sorted(doc_facts.roles):
            if not _matches_known_role(role, cv_facts.roles):
                contradictions.append(f'{label} references role not present in CV: {role}')

    score = _bounded_score(10.0 - (0.8 * len(contradictions)))
    return CrossDocumentConsistencyResult(score=score, contradictions=contradictions)


def _build_quality_recommendations(
    grammar: ValidationCheckResult,
    tone: ValidationCheckResult,
    anti_ai: AntiAIPatternResult,
    formatting: ValidationCheckResult,
    structure: ValidationCheckResult,
    ats_score: float | None,
    consistency: CrossDocumentConsistencyResult | None,
) -> list[str]:
    recommendations: list[str] = []
    if not grammar.passed:
        recommendations.append('Correct spacing, punctuation, and spelling before finalizing output.')
    if not tone.passed:
        recommendations.append('Use confident, direct wording and reduce hedging or casual language.')
    if anti_ai.score < ANTI_AI_MIN_SCORE:
        recommendations.append('Rewrite templated phrases with concrete, specific wording.')
    if not formatting.passed:
        recommendations.append('Normalize paragraph spacing and bullet formatting for readability.')
    if not structure.passed:
        recommendations.append('Ensure clear intro, evidence-focused body, and explicit conclusion.')
    if ats_score is not None and ats_score < ATS_MIN_SCORE:
        recommendations.append('Increase keyword alignment and quantified outcomes for ATS strength.')
    if consistency is not None and not consistency.passed:
        recommendations.append('Resolve factual mismatches across VPR, CV, and cover letter.')
    return recommendations


def run_quality_validation(
    content: str,
    *,
    document_type: str,
    ats_keywords: Iterable[str] | None = None,
    vpr_content: str | None = None,
    cv_content: str | None = None,
    cover_letter_content: str | None = None,
) -> FVSQualityReport:
    """Run full FVS quality checks and return per-dimension scores."""
    grammar = validate_grammar(content)
    tone = validate_tone(content)
    anti_ai = check_anti_ai_patterns(content)
    formatting = validate_formatting(content)
    structure = validate_content_structure(content)

    ats_score: float | None = None
    if document_type in {'cv', 'cover_letter'}:
        ats_score = score_ats_content(content, ats_keywords, document_type=document_type)

    consistency_result: CrossDocumentConsistencyResult | None = None
    if vpr_content is not None and cv_content is not None and cover_letter_content is not None:
        consistency_result = check_cross_document_consistency(vpr_content, cv_content, cover_letter_content)

    issues = [
        *grammar.issues,
        *tone.issues,
        *anti_ai.issues,
        *formatting.issues,
        *structure.issues,
    ]
    if ats_score is not None and ats_score < ATS_MIN_SCORE:
        issues.append(f'ATS score {ats_score:.2f} is below {ATS_MIN_SCORE:.1f}')
    if consistency_result is not None:
        issues.extend(consistency_result.contradictions)

    recommendations = _build_quality_recommendations(
        grammar=grammar,
        tone=tone,
        anti_ai=anti_ai,
        formatting=formatting,
        structure=structure,
        ats_score=ats_score,
        consistency=consistency_result,
    )

    overall_score = _bounded_score((grammar.score + tone.score + anti_ai.score + formatting.score + structure.score) / 5.0)
    consistency_score = consistency_result.score if consistency_result is not None else None
    return FVSQualityReport(
        overall_score=overall_score,
        grammar_score=grammar.score,
        tone_score=tone.score,
        ai_pattern_score=anti_ai.score,
        formatting_score=formatting.score,
        structure_score=structure.score,
        ats_score=ats_score,
        consistency_score=consistency_score,
        issues=issues,
        recommendations=recommendations,
    )


def check_anti_ai_patterns(content: str) -> AntiAIPatternResult:  # noqa: C901
    """
    Score content on anti-AI writing patterns.

    Uses an 8-pattern detection framework.
    The score is 0.0-10.0 where >=9.0 passes the quality gate.
    """
    normalized = content.strip()
    if not normalized:
        return AntiAIPatternResult(score=0.0, issues=['Content is empty'])

    lowered = normalized.lower()
    issues: list[str] = []
    score = 10.0

    # Pattern 1: banned buzzwords.
    matched_banned = [term for term in ANTI_AI_BANNED_TERMS if term in lowered]
    if matched_banned:
        score -= min(len(matched_banned) * 0.6, 4.0)
        issues.append(f'Pattern 1 - banned terms detected: {", ".join(sorted(matched_banned))}')

    # Pattern 2: too-short shape.
    sentences = [part.strip() for part in re.split(r'[.!?]+', normalized) if part.strip()]
    if len(sentences) < 2:
        score -= 0.4
        issues.append('Pattern 2 - very short response shape; expand with more natural variation')

    if sentences:
        lengths = [len(sentence.split()) for sentence in sentences]
        avg_sentence_len = sum(lengths) / len(lengths)
        # Pattern 3: heavy sentence length.
        if avg_sentence_len > 26:
            score -= 0.4
            issues.append('Pattern 3 - average sentence length is too high and sounds formulaic')

        starters: list[str] = []
        for sentence in sentences:
            words = sentence.lower().split()
            starters.append(' '.join(words[:2]) if len(words) >= 2 else words[0])
        # Pattern 4: repeated openings.
        if starters:
            repeated_start_count = max(starters.count(starter) for starter in set(starters))
            if repeated_start_count >= 3:
                score -= 0.4
                issues.append('Pattern 4 - repeated sentence openings suggest templated writing')

        # Pattern 5: unusually uniform sentence lengths.
        if len(lengths) >= 4:
            length_spread = max(lengths) - min(lengths)
            if length_spread <= 4:
                score -= 0.5
                issues.append('Pattern 5 - sentence lengths are overly uniform')

    # Pattern 6: low lexical diversity.
    tokens = TOKEN_PATTERN.findall(lowered)
    if tokens:
        diversity = len(set(tokens)) / len(tokens)
        if diversity < 0.42:
            score -= 0.4
            issues.append('Pattern 6 - low lexical diversity suggests repetitive AI-like phrasing')

    # Pattern 7: formulaic transitions and fillers.
    transition_hits = _count_phrase_hits(lowered, ROBOTIC_TRANSITIONS)
    filler_hits = _count_phrase_hits(lowered, ROBOTIC_FILLER_PHRASES)
    if transition_hits + filler_hits >= 3:
        score -= 0.6
        issues.append('Pattern 7 - formulaic transition/filler phrases detected')

    # Pattern 8: overuse of nominalized vocabulary.
    if tokens:
        nominalized_count = sum(1 for token in tokens if token.endswith(('tion', 'ment', 'ness')))
        nominalized_ratio = nominalized_count / len(tokens)
        if nominalized_ratio > 0.18:
            score -= 0.5
            issues.append('Pattern 8 - heavy nominalization can sound robotic')

    return AntiAIPatternResult(score=_bounded_score(score), issues=issues)


def check_anti_anti_ai_patterns(content: str) -> AntiAIPatternResult:
    """Backward-compatible alias for older call sites."""
    return check_anti_ai_patterns(content)


STRUCTURAL_MIN_SCORE = 8.0


@dataclass(frozen=True)
class VPRGateResult:
    """Quality gate output for VPR — consumed by VPRSixStagePipeline._final_meta_evaluation."""

    anti_ai_score: float
    structural_score: float
    grammar_score: float
    tone_score: float
    passed_gate: bool
    issues: list[str]


def validate_evidence_traceability(vpr: VPR, cv_text: str, gap_response_text: str) -> ValidationCheckResult:
    """Rule 1 (structural): Verify top-level quantified claims appear in cv_text or gap_response_text."""
    if vpr.executive_summary is None or vpr.value_proposition is None:
        return ValidationCheckResult(score=10.0, issues=[], min_score=STRUCTURAL_MIN_SCORE)
    source_text = (cv_text + ' ' + gap_response_text).lower()
    score = 10.0
    issues: list[str] = []
    deduction = 0.0

    claims = [
        vpr.executive_summary.fit_rationale,
        vpr.value_proposition.primary_value.evidence,
        vpr.value_proposition.elevator_pitch,
    ]

    for claim in claims:
        if not claim:
            continue
        numbers = NUMBER_PATTERN.findall(claim)
        proper_nouns = re.findall(r'\b[A-Z][a-zA-Z0-9]{2,}\b', claim)
        tokens = numbers + proper_nouns
        if not tokens:
            continue
        verified = any(token.lower() in source_text for token in tokens)
        if not verified:
            deduction += 0.8
            issues.append(f'Unverifiable claim (no token found in source): "{claim[:60]}..."')

    score -= min(deduction, 4.0)
    return ValidationCheckResult(score=_bounded_score(score), issues=issues, min_score=STRUCTURAL_MIN_SCORE)


def validate_quantification_consistency(vpr: VPR) -> ValidationCheckResult:
    """Rule 2 (structural): Detect metric paraphrasing across sections."""
    if vpr.executive_summary is None or vpr.value_proposition is None or vpr.differentiators is None or vpr.concerns_and_mitigations is None:
        return ValidationCheckResult(score=10.0, issues=[], min_score=STRUCTURAL_MIN_SCORE)
    all_text_fields: list[str] = [
        vpr.executive_summary.fit_rationale,
        vpr.value_proposition.elevator_pitch,
        vpr.value_proposition.primary_value.statement,
        vpr.value_proposition.primary_value.evidence,
        vpr.differentiators.positioning_statement,
        *[sv.value for sv in vpr.value_proposition.secondary_values],
        *[sv.proof for sv in vpr.value_proposition.secondary_values],
        *[s.strength for s in vpr.differentiators.unique_strengths],
        *[s.proof for s in vpr.differentiators.unique_strengths],
        *[s.relevance for s in vpr.differentiators.unique_strengths],
        *[o.mitigation.messaging for o in vpr.concerns_and_mitigations.likely_objections],
    ]

    score = 10.0
    issues: list[str] = []
    deduction = 0.0

    value_contexts: dict[str, list[str]] = {}
    for field_text in all_text_fields:
        if not field_text:
            continue
        for match in NUMBER_PATTERN.finditer(field_text):
            num_val = match.group()
            start = max(0, match.start() - 8)
            end = min(len(field_text), match.end() + 8)
            context = field_text[start:end]
            if num_val not in value_contexts:
                value_contexts[num_val] = []
            value_contexts[num_val].append(context)

    for num_val, contexts in value_contexts.items():
        if len(contexts) < 2:
            continue
        normalized = {re.sub(r'[^\w%$]', '', c).lower() for c in contexts}
        if len(normalized) > 1:
            deduction += 0.5
            issues.append(f'Metric "{num_val}" appears with inconsistent context across sections')

    score -= min(deduction, 3.0)
    return ValidationCheckResult(score=_bounded_score(score), issues=issues, min_score=STRUCTURAL_MIN_SCORE)


def validate_alignment_scores(vpr: VPR) -> ValidationCheckResult:
    """Rule 3 (structural): alignment_score must match evidence_quality in core_responsibilities."""
    if vpr.role_alignment is None:
        return ValidationCheckResult(score=10.0, issues=[], min_score=STRUCTURAL_MIN_SCORE)
    quality_ranges: dict[str, tuple[int, int]] = {
        'direct': (80, 100),
        'analogous': (60, 79),
        'transferable': (40, 59),
        'weak': (0, 39),
    }
    score = 10.0
    issues: list[str] = []
    deduction = 0.0

    for resp in vpr.role_alignment.core_responsibilities:
        expected_range = quality_ranges.get(resp.evidence_quality)
        if expected_range is None:
            continue
        low, high = expected_range
        if not (low <= resp.alignment_score <= high):
            deduction += 1.0
            issues.append(
                f'Responsibility "{resp.responsibility[:50]}" has evidence_quality="{resp.evidence_quality}" '
                f'but alignment_score={resp.alignment_score} (expected {low}-{high})'
            )

    score -= min(deduction, 4.0)
    return ValidationCheckResult(score=_bounded_score(score), issues=issues, min_score=STRUCTURAL_MIN_SCORE)


def validate_gap_severity_calibration(vpr: VPR) -> ValidationCheckResult:
    """Rule 4 (structural): priority_gaps with before_application should be critical/high; critical gaps must be prioritized."""
    if vpr.evidence_gaps is None:
        return ValidationCheckResult(score=10.0, issues=[], min_score=STRUCTURAL_MIN_SCORE)
    score = 10.0
    issues: list[str] = []
    deduction = 0.0

    gap_severity_map: dict[str, str] = {g.requirement.lower(): g.gap_severity for g in vpr.evidence_gaps.identified_gaps}

    for priority_gap in vpr.evidence_gaps.priority_gaps_to_address:
        if priority_gap.deadline == 'before_application':
            severity = gap_severity_map.get(priority_gap.gap.lower())
            if severity in ('medium', 'low'):
                deduction += 1.5
                issues.append(
                    f'Priority gap "{priority_gap.gap[:50]}" has deadline=before_application but severity="{severity}" (should be critical/high)'
                )

    priority_gap_texts = {pg.gap.lower() for pg in vpr.evidence_gaps.priority_gaps_to_address if pg.priority <= 2}
    for identified_gap in vpr.evidence_gaps.identified_gaps:
        if identified_gap.gap_severity == 'critical':
            if identified_gap.requirement.lower() not in priority_gap_texts:
                deduction += 1.0
                issues.append(f'Critical gap "{identified_gap.requirement[:50]}" not found in priority_gaps_to_address (priority 1-2)')

    score -= deduction
    return ValidationCheckResult(score=_bounded_score(score), issues=issues, min_score=STRUCTURAL_MIN_SCORE)


def validate_differentiator_rarity(vpr: VPR) -> ValidationCheckResult:
    """Rule 5 (structural): rarity claims must be supported by proof/relevance evidence."""
    if vpr.differentiators is None:
        return ValidationCheckResult(score=10.0, issues=[], min_score=STRUCTURAL_MIN_SCORE)
    score = 10.0
    issues: list[str] = []
    deduction = 0.0

    for strength in vpr.differentiators.unique_strengths:
        if strength.rarity == 'very_rare':
            if not NUMBER_PATTERN.search(strength.proof):
                deduction += 1.0
                issues.append(f'Strength "{strength.strength[:50]}" claimed very_rare but proof lacks quantified metric')
        elif strength.rarity == 'uncommon':
            relevance_words = len(strength.relevance.split()) if strength.relevance else 0
            if relevance_words <= 20:
                deduction += 1.0
                issues.append(f'Strength "{strength.strength[:50]}" claimed uncommon but relevance is too short (<= 20 words)')

    return ValidationCheckResult(score=_bounded_score(score), issues=issues, min_score=STRUCTURAL_MIN_SCORE)


def validate_mitigation_substance(vpr: VPR) -> ValidationCheckResult:
    """Rule 6 (structural): mitigation messaging must be specific, not generic."""
    if vpr.concerns_and_mitigations is None:
        return ValidationCheckResult(score=10.0, issues=[], min_score=STRUCTURAL_MIN_SCORE)
    score = 10.0
    issues: list[str] = []
    deduction = 0.0

    for objection in vpr.concerns_and_mitigations.likely_objections:
        messaging = objection.mitigation.messaging or ''
        word_count = len(messaging.split())
        proper_nouns = re.findall(r'\b[A-Z][a-zA-Z0-9]{2,}\b', messaging)
        if word_count < 30 or not proper_nouns:
            deduction += 1.2
            issues.append(
                f'Objection "{objection.objection[:50]}" has weak/generic mitigation (words={word_count}, proper_nouns={len(proper_nouns)})'
            )

    score -= min(deduction, 4.8)
    return ValidationCheckResult(score=_bounded_score(score), issues=issues, min_score=STRUCTURAL_MIN_SCORE)


def run_vpr_quality_gate(vpr: VPR, user_cv: UserCV, cv_text: str, gap_response_text: str) -> VPRGateResult:
    """Aggregate gate: run all 7 quality checks and return structured result."""
    if (
        vpr.executive_summary is None
        or vpr.differentiators is None
        or vpr.value_proposition is None
        or vpr.application_strategy is None
        or vpr.concerns_and_mitigations is None
    ):
        return VPRGateResult(
            anti_ai_score=10.0,
            structural_score=10.0,
            grammar_score=10.0,
            tone_score=10.0,
            passed_gate=True,
            issues=[],
        )
    content = '\n'.join(
        s
        for s in [
            vpr.executive_summary.fit_rationale,
            vpr.differentiators.positioning_statement,
            vpr.value_proposition.elevator_pitch,
            vpr.application_strategy.messaging_approach,
            *[o.mitigation.messaging for o in vpr.concerns_and_mitigations.likely_objections],
            *[s.relevance for s in vpr.differentiators.unique_strengths],
        ]
        if s
    )

    anti_ai = check_anti_ai_patterns(content)

    structural_results = [
        validate_evidence_traceability(vpr, cv_text, gap_response_text),
        validate_quantification_consistency(vpr),
        validate_alignment_scores(vpr),
        validate_gap_severity_calibration(vpr),
        validate_differentiator_rarity(vpr),
        validate_mitigation_substance(vpr),
    ]
    structural_score = _bounded_score(sum(r.score for r in structural_results) / len(structural_results))

    grammar = validate_grammar(content)
    tone = validate_tone(content)

    passed_gate = (
        anti_ai.score >= ANTI_AI_MIN_SCORE
        and structural_score >= STRUCTURAL_MIN_SCORE
        and grammar.score >= GRAMMAR_MIN_SCORE
        and tone.score >= TONE_MIN_SCORE
    )

    all_issues: list[str] = [*anti_ai.issues]
    for r in structural_results:
        all_issues.extend(r.issues)
    all_issues.extend(grammar.issues)
    all_issues.extend(tone.issues)

    return VPRGateResult(
        anti_ai_score=anti_ai.score,
        structural_score=structural_score,
        grammar_score=grammar.score,
        tone_score=tone.score,
        passed_gate=passed_gate,
        issues=all_issues,
    )


# Phase 9 CV Tailoring helpers (delegates to cv_tailoring implementation)
def create_fvs_baseline(master_cv: Any) -> TailoringFVSBaseline:
    """Create FVS baseline for CV tailoring flow."""
    from careervp.logic.cv_tailoring import create_fvs_baseline as _create_baseline

    return _create_baseline(master_cv)


def validate_tailored_cv(
    baseline: TailoringFVSBaseline,
    tailored_cv: Any,
) -> Result[TailoringFVSValidationResult]:
    """Validate tailored CV against FVS baseline for CV tailoring flow."""
    from careervp.logic.cv_tailoring import validate_tailored_cv as _validate

    return _validate(baseline, tailored_cv)
