"""
VPR Generator with a 6-stage pipeline.

Stages:
1) _analyze_input
2) _extract_evidence
3) _synthesize
4) _self_correct
5) _generate_output
6) _final_meta_evaluation
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal, cast

from careervp.logic.fvs_validator import check_anti_anti_ai_patterns
from careervp.logic.prompts.vpr_prompt import (
    STAGE_3_SYSTEM_PROMPT,
    STAGE_4_SYSTEM_PROMPT,
    build_stage_3_prompt,
    build_stage_4_prompt,
)

if TYPE_CHECKING:
    TaskMode = Any

    def get_llm_router() -> Any: ...  # pragma: no cover
else:
    from careervp.logic.utils.llm_client import TaskMode, get_llm_router
from careervp.models.cv import UserCV
from careervp.models.job import JobPosting
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import (
    VPR,
    EvidenceItem,
    GapStrategy,
    TokenUsage,
    VPRRequest,
    VPRResponse,
)

if TYPE_CHECKING:
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

DEFAULT_SYSTEM_PROMPT = 'You are CareerVP VPR Generator. Follow instructions exactly and return valid JSON.'
ANTI_AI_MIN_SCORE = 9.0
MAX_STAGE6_RETRIES = 3
WORD_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9+#./'-]*")

AlignmentScore = Literal['STRONG', 'MODERATE', 'DEVELOPING']


@dataclass(frozen=True)
class AnalysisResult:
    """Stage 1 output contract."""

    key_skills: list[str]
    experience_level: str
    job_requirements: list[str]
    cv_achievements: list[str]


@dataclass(frozen=True)
class EvidenceMatch:
    """Mapped evidence for a single requirement."""

    requirement: str
    evidence: str
    alignment_score: AlignmentScore
    impact_potential: str


@dataclass(frozen=True)
class EvidenceList:
    """Stage 2 output contract."""

    matches: list[EvidenceMatch]
    uncovered_requirements: list[str]
    key_skills: list[str]
    experience_level: str


@dataclass(frozen=True)
class DraftGapStrategy:
    """Gap strategy draft element used in stages 3 and 4."""

    gap: str
    mitigation_approach: str
    transferable_skills: list[str]


@dataclass(frozen=True)
class DraftProposition:
    """Stage 3 output contract."""

    executive_summary: str
    evidence_matrix: list[EvidenceMatch]
    differentiators: list[str]
    gap_strategies: list[DraftGapStrategy]
    cultural_fit: str | None
    talking_points: list[str]
    keywords: list[str]


@dataclass(frozen=True)
class CorrectedProposition:
    """Stage 4 output contract."""

    executive_summary: str
    evidence_matrix: list[EvidenceMatch]
    differentiators: list[str]
    gap_strategies: list[DraftGapStrategy]
    cultural_fit: str | None
    talking_points: list[str]
    keywords: list[str]
    corrections_applied: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VPRData:
    """Stage 5 output contract."""

    vpr: VPR


@dataclass(frozen=True)
class FinalVPRData:
    """Stage 6 output contract."""

    vpr: VPR
    anti_ai_score: float
    anti_ai_issues: list[str]
    passed_gate: bool
    regeneration_count: int


class LLMClient:
    """Thin wrapper so tests can patch LLM usage."""

    def __init__(self) -> None:
        self._router: Any = get_llm_router()

    def invoke(
        self,
        prompt: str,
        task_mode: TaskMode,
        max_tokens: int,
        temperature: float,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> Result[dict[str, Any]]:
        """Delegate to centralized router."""
        result = self._router.invoke(
            mode=task_mode,
            system_prompt=system_prompt,
            user_prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return cast(Result[dict[str, Any]], result)


class VPRSixStagePipeline:
    """Orchestrates the 6-stage VPR generation flow."""

    def __init__(
        self,
        request: VPRRequest,
        user_cv: UserCV,
        llm_client: LLMClient | None = None,
        max_stage6_retries: int = MAX_STAGE6_RETRIES,
    ) -> None:
        self._request = request
        self._user_cv = user_cv
        self._llm_client = llm_client or LLMClient()
        self._max_stage6_retries = max(1, max_stage6_retries)

        self._input_tokens_total = 0
        self._output_tokens_total = 0
        self._cost_total = 0.0
        self._model_name = 'claude-sonnet-4-5'
        self._regeneration_count = 0

    @property
    def token_usage(self) -> TokenUsage:
        """Aggregate token and cost metrics from stage-level LLM calls."""
        return TokenUsage(
            input_tokens=self._input_tokens_total,
            output_tokens=self._output_tokens_total,
            cost_usd=round(self._cost_total, 6),
            model=self._model_name,
        )

    def run(self) -> Result[FinalVPRData]:
        """Execute all stages with regeneration on Stage 6 failures."""
        analysis = self._analyze_input(self._user_cv, self._request.job_posting)
        evidence = self._extract_evidence(analysis)

        feedback: str | None = None
        last_meta: FinalVPRData | None = None

        for attempt in range(self._max_stage6_retries):
            self._regeneration_count = attempt

            try:
                draft = self._synthesize(evidence, feedback)
            except ValueError as exc:
                return Result(success=False, error=str(exc), code=ResultCode.INVALID_INPUT)
            except RuntimeError as exc:
                return Result(success=False, error=str(exc), code=ResultCode.LLM_API_ERROR)

            corrected = self._self_correct(draft, feedback)
            vpr_data = self._generate_output(corrected)
            last_meta = self._final_meta_evaluation(vpr_data)

            if last_meta.passed_gate:
                return Result(success=True, data=last_meta, code=ResultCode.SUCCESS)

            feedback = _build_regeneration_feedback(last_meta)

        if last_meta is None:
            return Result(
                success=False,
                error='Pipeline ended without producing a VPR candidate',
                code=ResultCode.INTERNAL_ERROR,
            )

        return Result(
            success=False,
            data=last_meta,
            error=(f'Anti-AI score {last_meta.anti_ai_score:.2f} below threshold {ANTI_AI_MIN_SCORE:.1f} after {self._max_stage6_retries} attempts'),
            code=ResultCode.FVS_VALIDATION_FAILED,
        )

    def _analyze_input(self, cv: UserCV, job: JobPosting) -> AnalysisResult:
        """Stage 1: extract key skills, experience level, and role requirements."""
        key_skills = cv.skill_names()
        job_requirements = _dedupe_preserve_order([*job.requirements, *job.responsibilities])

        cv_achievements: list[str] = []
        cv_achievements.extend(cv.top_achievements)
        for experience in cv.experience:
            cv_achievements.extend(experience.achievements)
            if experience.role and experience.company:
                cv_achievements.append(f'{experience.role} at {experience.company}')

        experience_level = _infer_experience_level(cv)

        return AnalysisResult(
            key_skills=key_skills,
            experience_level=experience_level,
            job_requirements=job_requirements,
            cv_achievements=_dedupe_preserve_order([item for item in cv_achievements if item.strip()]),
        )

    def _extract_evidence(self, analysis: AnalysisResult) -> EvidenceList:
        """Stage 2: map CV evidence to each job requirement."""
        matches: list[EvidenceMatch] = []
        uncovered_requirements: list[str] = []

        evidence_pool = analysis.cv_achievements or analysis.key_skills
        for requirement in analysis.job_requirements:
            chosen_evidence, overlap_score = _select_best_evidence(requirement, evidence_pool)
            if chosen_evidence is None:
                uncovered_requirements.append(requirement)
                chosen_evidence = _fallback_evidence_text(analysis.key_skills)

            alignment = _alignment_from_overlap(overlap_score)
            impact_potential = _build_impact_potential(requirement, analysis.experience_level)

            matches.append(
                EvidenceMatch(
                    requirement=requirement,
                    evidence=chosen_evidence,
                    alignment_score=alignment,
                    impact_potential=impact_potential,
                )
            )

        return EvidenceList(
            matches=matches,
            uncovered_requirements=uncovered_requirements,
            key_skills=analysis.key_skills,
            experience_level=analysis.experience_level,
        )

    def _synthesize(self, evidence: EvidenceList, feedback: str | None = None) -> DraftProposition:
        """Stage 3: synthesize initial value proposition draft."""
        prompt_payload = {
            'matches': [
                {
                    'requirement': match.requirement,
                    'evidence': match.evidence,
                    'alignment_score': match.alignment_score,
                    'impact_potential': match.impact_potential,
                }
                for match in evidence.matches
            ],
            'uncovered_requirements': evidence.uncovered_requirements,
            'key_skills': evidence.key_skills,
            'experience_level': evidence.experience_level,
        }

        prompt = build_stage_3_prompt(prompt_payload, feedback=feedback)
        payload = self._invoke_stage_json(
            prompt=prompt,
            system_prompt=STAGE_3_SYSTEM_PROMPT,
            max_tokens=3000,
            temperature=0.65,
        )
        return _parse_draft_proposition(payload, evidence)

    def _self_correct(self, draft: DraftProposition, feedback: str | None = None) -> CorrectedProposition:
        """Stage 4: self-correct draft for quality and anti-AI style."""
        prompt_payload = _draft_to_payload(draft)
        prompt = build_stage_4_prompt(prompt_payload, feedback=feedback)

        try:
            payload = self._invoke_stage_json(
                prompt=prompt,
                system_prompt=STAGE_4_SYSTEM_PROMPT,
                max_tokens=3000,
                temperature=0.35,
            )
            return _parse_corrected_proposition(payload, draft)
        except (RuntimeError, ValueError):
            return _rule_based_self_correction(draft)

    def _generate_output(self, corrected: CorrectedProposition) -> VPRData:
        """Stage 5: format corrected proposition into final VPR model."""
        evidence_matrix = [
            EvidenceItem(
                requirement=item.requirement,
                evidence=item.evidence,
                alignment_score=item.alignment_score,
                impact_potential=item.impact_potential,
            )
            for item in corrected.evidence_matrix
        ]
        gap_strategies = [
            GapStrategy(
                gap=strategy.gap,
                mitigation_approach=strategy.mitigation_approach,
                transferable_skills=strategy.transferable_skills,
            )
            for strategy in corrected.gap_strategies
        ]

        vpr = VPR(
            application_id=self._request.application_id,
            user_id=self._request.user_id,
            executive_summary=corrected.executive_summary,
            evidence_matrix=evidence_matrix,
            differentiators=corrected.differentiators,
            gap_strategies=gap_strategies,
            cultural_fit=corrected.cultural_fit,
            talking_points=corrected.talking_points,
            keywords=corrected.keywords,
            language=self._request.job_posting.language,
            version=1,
            created_at=datetime.now(timezone.utc),
            word_count=0,
        )
        vpr.word_count = _calculate_word_count(vpr)
        return VPRData(vpr=vpr)

    def _final_meta_evaluation(self, vpr: VPRData) -> FinalVPRData:
        """Stage 6: anti-AI gate and final quality check."""
        content = _serialize_vpr_for_quality(vpr.vpr)
        anti_ai_assessment = check_anti_anti_ai_patterns(content)
        return FinalVPRData(
            vpr=vpr.vpr,
            anti_ai_score=anti_ai_assessment.score,
            anti_ai_issues=anti_ai_assessment.issues,
            passed_gate=anti_ai_assessment.score >= ANTI_AI_MIN_SCORE,
            regeneration_count=self._regeneration_count,
        )

    def _invoke_stage_json(
        self,
        *,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        """Invoke LLM for a stage and parse strict JSON response."""
        llm_result = self._llm_client.invoke(
            prompt=prompt,
            task_mode=TaskMode.STRATEGIC,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
        )

        if not llm_result.success or llm_result.data is None:
            raise RuntimeError(llm_result.error or 'LLM invocation failed')

        self._accumulate_usage(llm_result.data)

        raw_text = str(llm_result.data.get('text', '')).strip()
        if not raw_text:
            raise RuntimeError('LLM returned empty response')

        payload = _parse_json_payload(raw_text)
        if not isinstance(payload, dict):
            raise ValueError('LLM response must be a JSON object')
        return payload

    def _accumulate_usage(self, payload: dict[str, Any]) -> None:
        """Collect token/cost metrics across stage calls."""
        self._input_tokens_total += _as_int(payload.get('input_tokens'))
        self._output_tokens_total += _as_int(payload.get('output_tokens'))
        self._cost_total += _as_float(payload.get('cost'))

        model = payload.get('model')
        if model:
            self._model_name = str(model)


def generate_vpr(request: VPRRequest, user_cv: UserCV, dal: DynamoDalHandler) -> Result[VPRResponse]:
    """Generate VPR through the 6-stage pipeline and persist the output."""
    start_time = time.perf_counter()

    pipeline = VPRSixStagePipeline(request=request, user_cv=user_cv)
    pipeline_result = pipeline.run()

    if not pipeline_result.success or pipeline_result.data is None:
        return Result(
            success=False,
            error=pipeline_result.error or 'VPR generation failed',
            code=pipeline_result.code,
        )

    final_data = pipeline_result.data
    save_result = dal.save_vpr(final_data.vpr)
    if not save_result.success:
        return Result(
            success=False,
            error=save_result.error or 'Failed to persist VPR',
            code=save_result.code,
        )

    generation_time_ms = int((time.perf_counter() - start_time) * 1000)

    response = VPRResponse(
        success=True,
        vpr=final_data.vpr,
        token_usage=pipeline.token_usage,
        generation_time_ms=generation_time_ms,
    )

    return Result(success=True, data=response, code=ResultCode.VPR_GENERATED)


def _parse_draft_proposition(payload: dict[str, Any], evidence: EvidenceList) -> DraftProposition:
    """Parse Stage 3 JSON payload into DraftProposition."""
    evidence_matrix = _parse_evidence_matrix(payload.get('evidence_matrix'), evidence.matches)
    gap_strategies = _parse_gap_strategies(payload.get('gap_strategies'))

    executive_summary = str(payload.get('executive_summary', '')).strip()
    if not executive_summary:
        executive_summary = _default_executive_summary(evidence)

    differentiators = _ensure_str_list(payload.get('differentiators'))
    if not differentiators:
        differentiators = _default_differentiators(evidence)

    talking_points = _ensure_str_list(payload.get('talking_points'))
    if not talking_points:
        talking_points = _default_talking_points(evidence)

    keywords = _ensure_str_list(payload.get('keywords'))
    if not keywords:
        keywords = evidence.key_skills[:10]

    cultural_fit_raw = payload.get('cultural_fit')
    cultural_fit = str(cultural_fit_raw).strip() if cultural_fit_raw else None

    return DraftProposition(
        executive_summary=executive_summary,
        evidence_matrix=evidence_matrix,
        differentiators=differentiators,
        gap_strategies=gap_strategies,
        cultural_fit=cultural_fit,
        talking_points=talking_points,
        keywords=keywords,
    )


def _parse_corrected_proposition(payload: dict[str, Any], draft: DraftProposition) -> CorrectedProposition:
    """Parse Stage 4 JSON payload into CorrectedProposition."""
    evidence_matrix = _parse_evidence_matrix(payload.get('evidence_matrix'), draft.evidence_matrix)
    gap_strategies = _parse_gap_strategies(payload.get('gap_strategies')) or draft.gap_strategies

    executive_summary = str(payload.get('executive_summary', draft.executive_summary)).strip() or draft.executive_summary
    differentiators = _ensure_str_list(payload.get('differentiators')) or draft.differentiators
    talking_points = _ensure_str_list(payload.get('talking_points')) or draft.talking_points
    keywords = _ensure_str_list(payload.get('keywords')) or draft.keywords

    cultural_fit_raw = payload.get('cultural_fit', draft.cultural_fit)
    cultural_fit = str(cultural_fit_raw).strip() if cultural_fit_raw else None

    corrections_applied = _ensure_str_list(payload.get('corrections_applied'))

    return CorrectedProposition(
        executive_summary=executive_summary,
        evidence_matrix=evidence_matrix,
        differentiators=differentiators,
        gap_strategies=gap_strategies,
        cultural_fit=cultural_fit,
        talking_points=talking_points,
        keywords=keywords,
        corrections_applied=corrections_applied,
    )


def _rule_based_self_correction(draft: DraftProposition) -> CorrectedProposition:
    """Fallback self-correction when Stage 4 LLM correction is unavailable."""
    corrections_applied: list[str] = []

    corrected_summary = _replace_banned_terms(draft.executive_summary)
    if corrected_summary != draft.executive_summary:
        corrections_applied.append('Removed banned terms from executive summary')

    corrected_differentiators = [_replace_banned_terms(value) for value in draft.differentiators]
    if corrected_differentiators != draft.differentiators:
        corrections_applied.append('Sanitized differentiators for anti-AI patterns')

    corrected_talking_points = [_replace_banned_terms(value) for value in draft.talking_points]
    if corrected_talking_points != draft.talking_points:
        corrections_applied.append('Sanitized talking points for anti-AI patterns')

    return CorrectedProposition(
        executive_summary=corrected_summary,
        evidence_matrix=draft.evidence_matrix,
        differentiators=corrected_differentiators,
        gap_strategies=draft.gap_strategies,
        cultural_fit=draft.cultural_fit,
        talking_points=corrected_talking_points,
        keywords=draft.keywords,
        corrections_applied=corrections_applied,
    )


def _parse_evidence_matrix(raw_value: object, fallback: list[EvidenceMatch]) -> list[EvidenceMatch]:
    if not isinstance(raw_value, list):
        return fallback

    parsed: list[EvidenceMatch] = []
    for entry in raw_value:
        if not isinstance(entry, dict):
            continue
        parsed.append(
            EvidenceMatch(
                requirement=str(entry.get('requirement', '')).strip(),
                evidence=str(entry.get('evidence', '')).strip(),
                alignment_score=_normalize_alignment(entry.get('alignment_score')),
                impact_potential=str(entry.get('impact_potential', '')).strip(),
            )
        )

    return parsed or fallback


def _parse_gap_strategies(raw_value: object) -> list[DraftGapStrategy]:
    if raw_value is None:
        return []

    raw_entries: list[dict[str, Any]]
    if isinstance(raw_value, list):
        raw_entries = [entry for entry in raw_value if isinstance(entry, dict)]
    elif isinstance(raw_value, dict):
        raw_entries = [raw_value]
    else:
        return []

    return [
        DraftGapStrategy(
            gap=str(entry.get('gap', '')).strip(),
            mitigation_approach=str(entry.get('mitigation_approach', '')).strip(),
            transferable_skills=_ensure_str_list(entry.get('transferable_skills')),
        )
        for entry in raw_entries
    ]


def _draft_to_payload(draft: DraftProposition) -> dict[str, Any]:
    return {
        'executive_summary': draft.executive_summary,
        'evidence_matrix': [
            {
                'requirement': match.requirement,
                'evidence': match.evidence,
                'alignment_score': match.alignment_score,
                'impact_potential': match.impact_potential,
            }
            for match in draft.evidence_matrix
        ],
        'differentiators': draft.differentiators,
        'gap_strategies': [
            {
                'gap': strategy.gap,
                'mitigation_approach': strategy.mitigation_approach,
                'transferable_skills': strategy.transferable_skills,
            }
            for strategy in draft.gap_strategies
        ],
        'cultural_fit': draft.cultural_fit,
        'talking_points': draft.talking_points,
        'keywords': draft.keywords,
    }


def _calculate_word_count(vpr: VPR) -> int:
    """Count words across all textual sections."""
    sections: list[str] = [vpr.executive_summary or '', vpr.cultural_fit or '']
    sections.extend(vpr.differentiators)
    sections.extend(vpr.talking_points)
    sections.extend(vpr.keywords)

    for evidence in vpr.evidence_matrix:
        sections.extend([evidence.requirement, evidence.evidence, evidence.impact_potential])

    for strategy in vpr.gap_strategies:
        sections.extend(
            [
                strategy.gap,
                strategy.mitigation_approach,
                ' '.join(strategy.transferable_skills),
            ]
        )

    words = WORD_PATTERN.findall(' '.join(sections))
    return len(words)


def _serialize_vpr_for_quality(vpr: VPR) -> str:
    """Serialize VPR content into plain text for anti-AI checks."""
    sections: list[str] = [vpr.executive_summary]
    if vpr.cultural_fit:
        sections.append(vpr.cultural_fit)
    sections.extend(vpr.differentiators)
    sections.extend(vpr.talking_points)
    sections.extend(vpr.keywords)

    for item in vpr.evidence_matrix:
        sections.append(f'{item.requirement}. {item.evidence}. {item.impact_potential}')

    for strategy in vpr.gap_strategies:
        sections.append(f'{strategy.gap}. {strategy.mitigation_approach}.')
        sections.extend(strategy.transferable_skills)

    return '\n'.join([section for section in sections if section])


def _ensure_str_list(value: object) -> list[str]:
    """Utility to coerce payload entries into simple string lists."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    normalized = str(value).strip()
    return [normalized] if normalized else []


def _parse_json_payload(response_text: str) -> object:
    """Parse JSON payload and strip optional markdown fences."""
    cleaned_text = response_text.strip()
    if cleaned_text.startswith('```'):
        first_newline = cleaned_text.find('\n')
        if first_newline != -1:
            cleaned_text = cleaned_text[first_newline + 1 :]
        if cleaned_text.endswith('```'):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f'LLM response is not valid JSON: {exc}') from exc


def _select_best_evidence(requirement: str, evidence_pool: list[str]) -> tuple[str | None, int]:
    requirement_tokens = _text_tokens(requirement)

    best_text: str | None = None
    best_overlap = 0

    for evidence in evidence_pool:
        overlap = len(requirement_tokens & _text_tokens(evidence))
        if overlap > best_overlap:
            best_overlap = overlap
            best_text = evidence

    if best_text is None:
        return None, 0
    return best_text, best_overlap


def _text_tokens(text: str) -> set[str]:
    return {token.lower() for token in WORD_PATTERN.findall(text) if len(token) > 2}


def _alignment_from_overlap(overlap: int) -> AlignmentScore:
    if overlap >= 3:
        return 'STRONG'
    if overlap >= 1:
        return 'MODERATE'
    return 'DEVELOPING'


def _build_impact_potential(requirement: str, experience_level: str) -> str:
    normalized_requirement = requirement.strip().lower() or 'the role priorities'
    return f'{experience_level} experience suggests strong delivery potential for {normalized_requirement}.'


def _fallback_evidence_text(key_skills: list[str]) -> str:
    if not key_skills:
        return 'CV includes relevant transferable experience for this requirement.'
    return f'Related skills from CV include: {", ".join(key_skills[:4])}.'


def _infer_experience_level(cv: UserCV) -> str:
    roles = ' '.join(experience.role.lower() for experience in cv.experience if experience.role)

    if any(title in roles for title in ('vp', 'vice president', 'director', 'head', 'principal', 'chief')):
        return 'senior'
    if any(title in roles for title in ('senior', 'lead', 'manager')):
        return 'advanced'
    if len(cv.experience) >= 2:
        return 'mid'
    return 'early'


def _default_executive_summary(evidence: EvidenceList) -> str:
    covered = len([match for match in evidence.matches if match.alignment_score != 'DEVELOPING'])
    total = len(evidence.matches)
    return (
        f'Candidate shows {evidence.experience_level} readiness with direct evidence for '
        f'{covered}/{total} priority requirements and clear plans for remaining gaps.'
    )


def _default_differentiators(evidence: EvidenceList) -> list[str]:
    differentiators: list[str] = []
    if evidence.key_skills:
        differentiators.append(f'Breadth across skills: {", ".join(evidence.key_skills[:4])}')
    if evidence.matches:
        differentiators.append(f'Role-aligned evidence across {len(evidence.matches)} requirements')
    return differentiators or ['Consistent track record tied to role requirements']


def _default_talking_points(evidence: EvidenceList) -> list[str]:
    points: list[str] = []
    for match in evidence.matches[:5]:
        points.append(f"Explain {match.evidence} and how it supports '{match.requirement}'.")
    return points


def _build_regeneration_feedback(final_data: FinalVPRData) -> str:
    issues_text = '; '.join(final_data.anti_ai_issues) if final_data.anti_ai_issues else 'No explicit issue details provided.'
    return (
        f'Anti-AI score {final_data.anti_ai_score:.2f} is below {ANTI_AI_MIN_SCORE:.1f}. Regenerate with more natural wording. Issues: {issues_text}'
    )


def _replace_banned_terms(text: str) -> str:
    replacements = {
        'leverage': 'use',
        'delve into': 'explore',
        'landscape': 'space',
        'robust': 'strong',
        'streamline': 'simplify',
        'utilize': 'use',
        'facilitate': 'support',
        'implement': 'build',
        'cutting-edge': 'modern',
        'best practices': 'proven methods',
        'industry-leading': 'well-regarded',
        'game-changer': 'high-impact improvement',
        'paradigm shift': 'major change',
        'synergy': 'collaboration',
    }

    normalized = text
    for source, target in replacements.items():
        normalized = re.sub(rf'\b{re.escape(source)}\b', target, normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def _normalize_alignment(value: object) -> AlignmentScore:
    normalized = str(value).strip().upper()
    if normalized in {'STRONG', 'MODERATE', 'DEVELOPING'}:
        return cast(AlignmentScore, normalized)
    return 'MODERATE'


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return ordered


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


def _as_float(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0
