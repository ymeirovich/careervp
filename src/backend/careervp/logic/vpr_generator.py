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
from datetime import date
from typing import TYPE_CHECKING, Any, Literal, cast

from pydantic import ValidationError

from careervp.logic.fvs_validator import run_vpr_quality_gate
from careervp.logic.prompts.vpr_prompt import (
    PHASE2_SYSTEM_PROMPT,
    build_phase2_prompt,
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
    TokenUsage,
    VPRApplicationStrategy,
    VPRCompanyInsight,
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
    VPRMustHave,
    VPRNiceToHave,
    VPRObjection,
    VPRPrerequisite,
    VPRPrimaryValue,
    VPRPriorityGap,
    VPRRelevantExperience,
    VPRRequest,
    VPRRequirementBreakdown,
    VPRResponse,
    VPRResponsibility,
    VPRRoleAlignment,
    VPRSecondaryValue,
    VPRSkillsAnalysis,
    VPRStrength,
    VPRUniqueStrength,
    VPRValueProposition,
    VPRVerificationSummary,
)

if TYPE_CHECKING:
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

DEFAULT_SYSTEM_PROMPT = 'You are CareerVP VPR Generator. Follow instructions exactly and return valid JSON.'
ANTI_AI_MIN_SCORE = 90  # 0-100 scale (P4)
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
class Phase2Draft:
    """Stage 3 output contract for new 10-section schema."""

    raw_payload: dict[str, Any]
    evidence_context: EvidenceList


@dataclass(frozen=True)
class ValidatedDraft:
    """Stage 4 output contract for new 10-section schema."""

    raw_payload: dict[str, Any]
    validation_notes: list[str]
    evidence_context: EvidenceList


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
    structural_score: float = field(default=10.0)


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

    def _synthesize(self, evidence: EvidenceList, feedback: str | None = None) -> Phase2Draft:
        """Stage 3: synthesize initial value proposition draft using Phase 2 prompt."""
        evidence_payload = {
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

        prompt = build_phase2_prompt(evidence_payload, self._user_cv, self._request, feedback)
        payload = self._invoke_stage_json(
            prompt=prompt,
            system_prompt=PHASE2_SYSTEM_PROMPT,
            max_tokens=16000,
            temperature=0.65,
        )
        return Phase2Draft(raw_payload=payload, evidence_context=evidence)

    def _self_correct(self, draft: Phase2Draft, feedback: str | None = None) -> ValidatedDraft:
        """Stage 4: rule-based structural validation only (LLM merged into Stage 3)."""
        return _rule_based_validation_fallback(draft)

    def _generate_output(self, validated: ValidatedDraft) -> VPRData:
        """Stage 5: parse validated payload into new 10-section VPR model."""
        vpr = _parse_full_vpr_model(validated.raw_payload, self._request, validated.evidence_context)
        vpr.word_count = _calculate_word_count(vpr)
        return VPRData(vpr=vpr)

    def _final_meta_evaluation(self, vpr: VPRData) -> FinalVPRData:
        """Stage 6: structural + anti-AI + grammar + tone quality gate."""
        cv_text = _serialize_cv_for_quality(self._user_cv)
        gap_text = ' '.join(gr.answer for gr in self._request.gap_responses if gr.answer)
        gate = run_vpr_quality_gate(vpr.vpr, self._user_cv, cv_text, gap_text)
        return FinalVPRData(
            vpr=vpr.vpr,
            anti_ai_score=gate.anti_ai_score,
            anti_ai_issues=gate.issues,
            structural_score=gate.structural_score,
            passed_gate=gate.passed_gate,
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


def _parse_full_vpr_model(  # noqa: C901 - complex but well-structured
    payload: dict[str, Any],
    request: VPRRequest,
    evidence_context: EvidenceList,
) -> VPR:
    """Parse a validated Phase 2 payload into the 10-section VPR model.

    Each section is parsed individually; a ValidationError falls back to a
    minimal valid default so a single bad section never aborts the whole VPR.
    """
    try:
        metadata = VPRMetadata.model_validate(payload.get('metadata', {}))
    except ValidationError:
        metadata = _build_minimal_metadata(request)

    try:
        executive_summary = VPRExecutiveSummary.model_validate(payload.get('executive_summary', {}))
    except ValidationError:
        executive_summary = _build_minimal_executive_summary()

    try:
        role_alignment = VPRRoleAlignment.model_validate(payload.get('role_alignment', {}))
    except ValidationError:
        role_alignment = _build_minimal_role_alignment()

    try:
        experience_mapping = VPRExperienceMapping.model_validate(payload.get('experience_mapping', {}))
    except ValidationError:
        experience_mapping = _build_minimal_experience_mapping()

    try:
        skills_analysis = VPRSkillsAnalysis.model_validate(payload.get('skills_analysis', {}))
    except ValidationError:
        skills_analysis = _build_minimal_skills_analysis()

    try:
        evidence_gaps = VPREvidenceGaps.model_validate(payload.get('evidence_gaps', {}))
    except ValidationError:
        evidence_gaps = _build_minimal_evidence_gaps(evidence_context)

    try:
        differentiators = VPRDifferentiators.model_validate(payload.get('differentiators', {}))
    except ValidationError:
        differentiators = _build_minimal_differentiators(evidence_context)

    try:
        concerns_and_mitigations = VPRConcernsAndMitigations.model_validate(payload.get('concerns_and_mitigations', {}))
    except ValidationError:
        concerns_and_mitigations = _build_minimal_concerns_and_mitigations()

    try:
        value_proposition = VPRValueProposition.model_validate(payload.get('value_proposition', {}))
    except ValidationError:
        value_proposition = _build_minimal_value_proposition()

    try:
        application_strategy = VPRApplicationStrategy.model_validate(payload.get('application_strategy', {}))
    except ValidationError:
        application_strategy = _build_minimal_application_strategy()

    company_insights: VPRCompanyInsight | None = None
    if 'company_insights' in payload:
        try:
            company_insights = VPRCompanyInsight.model_validate(payload['company_insights'])
        except ValidationError:
            pass

    verification_summary: VPRVerificationSummary | None = None
    if 'verification_summary' in payload:
        try:
            verification_summary = VPRVerificationSummary.model_validate(payload['verification_summary'])
        except ValidationError:
            pass

    return VPR(
        application_id=request.application_id,
        user_id=request.user_id,
        metadata=metadata,
        executive_summary=executive_summary,
        role_alignment=role_alignment,
        experience_mapping=experience_mapping,
        skills_analysis=skills_analysis,
        evidence_gaps=evidence_gaps,
        differentiators=differentiators,
        concerns_and_mitigations=concerns_and_mitigations,
        value_proposition=value_proposition,
        application_strategy=application_strategy,
        company_insights=company_insights,
        verification_summary=verification_summary,
        language=request.job_posting.language,
        version=request.target_version,
    )


def _rule_based_validation_fallback(draft: Phase2Draft) -> ValidatedDraft:
    """Fallback when Stage 4 LLM fails: clean banned terms from text-heavy fields."""
    payload = dict(draft.raw_payload)

    def _clean_nested(d: dict[str, Any], *keys: str) -> None:
        """Replace banned terms in a nested string field in-place."""
        node: Any = d
        for key in keys[:-1]:
            if not isinstance(node, dict):
                return
            node = node.get(key)
        if isinstance(node, dict):
            last_key = keys[-1]
            raw = node.get(last_key)
            if isinstance(raw, str):
                node[last_key] = _replace_banned_terms(raw)

    _clean_nested(payload, 'executive_summary', 'fit_rationale')
    _clean_nested(payload, 'differentiators', 'positioning_statement')
    _clean_nested(payload, 'value_proposition', 'elevator_pitch')
    _clean_nested(payload, 'value_proposition', 'primary_value', 'statement')

    return ValidatedDraft(
        raw_payload=payload,
        validation_notes=['Fallback: banned terms removed from text fields'],
        evidence_context=draft.evidence_context,
    )


# ---------------------------------------------------------------------------
# Minimal section builders — used when model_validate() raises ValidationError
# ---------------------------------------------------------------------------


def _build_minimal_metadata(request: VPRRequest) -> VPRMetadata:
    job_data = request.job_posting.model_dump(mode='json')
    return VPRMetadata(
        report_date=date.today().isoformat(),
        candidate_name='Candidate',
        target_role=str(job_data.get('title', 'Target Role')),
        target_company=str(job_data.get('company', 'Target Company')),
        report_version='1.0',
        job_posting_url=None,
        analysis_scope='full',
    )


def _build_minimal_executive_summary() -> VPRExecutiveSummary:
    fit_rationale = (
        'Candidate demonstrates relevant background for this role based on available evidence. '
        'CV analysis indicates alignment with core requirements. '
        'Application materials should highlight key experience areas.'
    )
    strengths = [
        VPRStrength(
            strength='Relevant professional experience in the field',
            evidence='Detailed in CV work history',
            relevance_to_role='Directly applicable to target role',
        ),
        VPRStrength(
            strength='Transferable skills from prior positions',
            evidence='Documented across CV experience sections',
            relevance_to_role='Supports core role requirements',
        ),
        VPRStrength(
            strength='Background aligned with job description needs',
            evidence='CV facts corroborate this assessment',
            relevance_to_role='Contributes to role success',
        ),
    ]
    concerns = [
        VPRConcern(
            concern='Evidence parsing encountered a validation issue',
            severity='low',
            mitigation='Review original CV and job posting for full context',
        ),
        VPRConcern(
            concern='Full assessment may require supplementary review',
            severity='low',
            mitigation='Verify alignment manually before applying',
        ),
        VPRConcern(
            concern='Some sections may benefit from additional detail',
            severity='low',
            mitigation='Address any gaps in cover letter',
        ),
    ]
    return VPRExecutiveSummary(
        overall_fit_score=50,
        fit_rationale=fit_rationale,
        top_three_strengths=strengths,
        top_three_concerns=concerns,
        recommended_approach='apply_with_customization',
    )


def _build_minimal_role_alignment() -> VPRRoleAlignment:
    return VPRRoleAlignment(
        core_responsibilities=[
            VPRResponsibility(
                responsibility='Core role responsibility',
                alignment_score=50,
                candidate_evidence=['Evidence from CV work history'],
                evidence_quality='transferable',
            )
        ],
        requirement_breakdown=VPRRequirementBreakdown(
            must_have=[
                VPRMustHave(
                    requirement='Core requirement',
                    candidate_meets_requirement=True,
                    evidence='CV experience supports this',
                )
            ],
            nice_to_have=[
                VPRNiceToHave(
                    preference='Preferred skill',
                    candidate_has_this=False,
                )
            ],
            assumed_prerequisites=[
                VPRPrerequisite(
                    assumption='Basic professional qualification',
                    candidate_meets_this=True,
                    reasoning='Implied by overall experience level',
                )
            ],
        ),
    )


def _build_minimal_experience_mapping() -> VPRExperienceMapping:
    return VPRExperienceMapping(
        relevant_experiences=[
            VPRRelevantExperience(
                role='Professional Role',
                organization='Organization',
                duration='1 year',
                key_achievements=[
                    VPRKeyAchievement(
                        achievement='Delivered measurable results',
                        metric='Outcome documented in CV',
                        impact='Positive business contribution',
                    )
                ],
                relevance_to_target_role='Experience is applicable to target role requirements',
            )
        ],
        experience_gaps=[],
    )


def _build_minimal_skills_analysis() -> VPRSkillsAnalysis:
    return VPRSkillsAnalysis(
        technical_skills=[],
        soft_skills=[],
        tool_proficiency=[],
    )


def _build_minimal_evidence_gaps(evidence_context: EvidenceList) -> VPREvidenceGaps:
    uncovered = evidence_context.uncovered_requirements[:1]
    gap_requirement = uncovered[0] if uncovered else 'Core requirement area'
    return VPREvidenceGaps(
        identified_gaps=[
            VPRIdentifiedGap(
                requirement=gap_requirement,
                current_evidence='Evidence from CV reviewed but parsing failed',
                gap_severity='low',
                suggested_evidence=['Provide supporting documentation in application'],
            )
        ],
        priority_gaps_to_address=[
            VPRPriorityGap(
                gap=gap_requirement,
                priority=1,
                action_item='Review and address before submitting application',
                deadline='before_application',
            )
        ],
    )


def _build_minimal_differentiators(evidence_context: EvidenceList) -> VPRDifferentiators:
    skills_snippet = ', '.join(evidence_context.key_skills[:3]) if evidence_context.key_skills else 'relevant domain'
    positioning = (
        f'Candidate brings a distinct combination of {skills_snippet} expertise '
        'that aligns with target role requirements and offers tangible value to the organization.'
    )
    # Ensure positioning_statement is within 100-300 chars
    if len(positioning) < 100:
        positioning = positioning + ' Professional background supports immediate contribution and long-term growth.'
    positioning = positioning[:300]
    return VPRDifferentiators(
        unique_strengths=[
            VPRUniqueStrength(
                strength=f'Professional background in {skills_snippet}',
                rarity='somewhat_rare',
                relevance='Applicable to target role requirements',
                proof='CV experience record',
            )
        ],
        competitive_advantages=[],
        positioning_statement=positioning,
    )


def _build_minimal_concerns_and_mitigations() -> VPRConcernsAndMitigations:
    return VPRConcernsAndMitigations(
        likely_objections=[
            VPRObjection(
                objection='Candidate background may not fully match all listed requirements',
                likelihood='possible',
                mitigation=VPRMitigation(
                    strategy='acknowledge_and_address',
                    messaging=('Candidate addresses gaps through transferable experience and a demonstrated capacity for rapid skill development.'),
                ),
                where_to_address=['cover_letter'],
            )
        ],
        preemptive_responses=[],
    )


def _build_minimal_value_proposition() -> VPRValueProposition:
    elevator_pitch = (
        'Experienced professional with a strong track record, ready to deliver results and contribute effectively from day one in this role.'
    )
    return VPRValueProposition(
        primary_value=VPRPrimaryValue(
            statement='Delivers measurable results through applied expertise and a focused work style',
            evidence='CV work history demonstrates consistent achievement across roles',
            outcome_for_company='Contributes directly to team goals and organizational priorities',
        ),
        secondary_values=[
            VPRSecondaryValue(
                value='Technical depth in relevant domain',
                proof='CV skills and project history',
            ),
            VPRSecondaryValue(
                value='Collaborative cross-functional approach',
                proof='Multi-stakeholder experience documented in CV',
            ),
        ],
        quantified_impact=[],
        elevator_pitch=elevator_pitch,
    )


def _build_minimal_application_strategy() -> VPRApplicationStrategy:
    return VPRApplicationStrategy(
        messaging_approach=('Focus on relevant experience and transferable skills to demonstrate fit for the core role requirements.'),
        ats_keywords=VPRKeywordGroup(primary=[], secondary=[]),
        cv_lead_differentiator='Lead with most relevant experience matching core role requirements',
        sections_to_compress=[],
    )


# ---------------------------------------------------------------------------
# Word count and quality serialization — updated for new 10-section schema
# ---------------------------------------------------------------------------


def _calculate_word_count(vpr: VPR) -> int:  # noqa: C901
    """Count words across all textual sections of the new 10-section VPR."""
    sections: list[str] = []

    # Section 2 — Executive Summary
    if vpr.executive_summary:
        sections.append(vpr.executive_summary.fit_rationale)
        for strength in vpr.executive_summary.top_three_strengths:
            sections.extend([strength.strength, strength.evidence, strength.relevance_to_role])
        for concern in vpr.executive_summary.top_three_concerns:
            sections.extend([concern.concern, concern.mitigation])

    # Section 3 — Role Alignment
    if vpr.role_alignment:
        for resp in vpr.role_alignment.core_responsibilities:
            sections.append(resp.responsibility)

    # Section 4 — Experience Mapping
    if vpr.experience_mapping:
        for exp in vpr.experience_mapping.relevant_experiences:
            sections.append(exp.relevance_to_target_role)
        for gap in vpr.experience_mapping.experience_gaps:
            sections.append(gap.missing_experience)
            if gap.mitigation_strategy:
                sections.append(gap.mitigation_strategy)

    # Section 5 — Skills Analysis
    if vpr.skills_analysis:
        for skill in vpr.skills_analysis.technical_skills:
            sections.append(skill.evidence)

    # Section 6 — Evidence Gaps
    if vpr.evidence_gaps:
        for identified in vpr.evidence_gaps.identified_gaps:
            sections.append(identified.current_evidence)

    # Section 7 — Differentiators
    if vpr.differentiators:
        sections.append(vpr.differentiators.positioning_statement)

    # Section 8 — Concerns & Mitigations
    if vpr.concerns_and_mitigations:
        for objection in vpr.concerns_and_mitigations.likely_objections:
            sections.extend([objection.objection, objection.mitigation.messaging])

    # Section 9 — Value Proposition
    if vpr.value_proposition:
        sections.extend(
            [
                vpr.value_proposition.elevator_pitch,
                vpr.value_proposition.primary_value.statement,
                vpr.value_proposition.primary_value.evidence,
            ]
        )

    # Section 10 — Application Strategy
    if vpr.application_strategy:
        sections.append(vpr.application_strategy.messaging_approach)

    # Additional — Company Insights (optional)
    if vpr.company_insights:
        sections.append(vpr.company_insights.mission_and_position)

    words = WORD_PATTERN.findall(' '.join(s for s in sections if s))
    return len(words)


def _serialize_vpr_for_quality(vpr: VPR) -> str:
    """Serialize VPR content into plain text for anti-AI pattern checks."""
    sections: list[str] = []

    # Section 2 — Executive Summary
    if vpr.executive_summary:
        sections.append(vpr.executive_summary.fit_rationale)

    # Section 7 — Differentiators
    if vpr.differentiators:
        sections.append(vpr.differentiators.positioning_statement)
        for strength in vpr.differentiators.unique_strengths:
            sections.extend([strength.strength, strength.relevance])

    # Section 9 — Value Proposition
    if vpr.value_proposition:
        sections.append(vpr.value_proposition.elevator_pitch)

    # Section 8 — Concerns & Mitigations
    if vpr.concerns_and_mitigations:
        for objection in vpr.concerns_and_mitigations.likely_objections:
            sections.append(objection.mitigation.messaging)

    # Section 10 — Application Strategy
    if vpr.application_strategy:
        sections.append(vpr.application_strategy.messaging_approach)

    return '\n'.join(s for s in sections if s)


def _serialize_cv_for_quality(user_cv: UserCV) -> str:
    """Flatten all relevant UserCV text for traceability checks (excludes contact info)."""
    parts: list[str] = []
    if user_cv.full_name:
        parts.append(user_cv.full_name)
    for exp in user_cv.experience:
        if exp.company:
            parts.append(exp.company)
        if exp.role:
            parts.append(exp.role)
        parts.extend(exp.achievements)
    for edu in user_cv.education:
        if edu.institution:
            parts.append(edu.institution)
    parts.extend(user_cv.top_achievements)
    for skill in user_cv.skills:
        parts.append(skill.name if hasattr(skill, 'name') else str(skill))
    return ' '.join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Preserved utility functions
# ---------------------------------------------------------------------------


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
