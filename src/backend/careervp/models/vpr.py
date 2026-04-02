"""
Pydantic models for Value Proposition Report (VPR) generation.
10-section schema per docs/architecture/careervp_prompts/vpr/specs/01-pydantic-schema.yaml.

VPR is the strategic foundation document generated using Sonnet 4.5
that provides alignment mapping between CV facts and job requirements.

Field names are snake_case for DynamoDB storage.
Use .model_dump(by_alias=True) to produce camelCase for API/frontend consumers.
"""

from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from careervp.models.job import CompanyContext, GapResponse, JobPosting

# Shared model config applied to every model in this file.
_CFG = ConfigDict(populate_by_name=True, extra='ignore', alias_generator=to_camel)


# ---------------------------------------------------------------------------
# Preserved models — unchanged (used by CV tailoring, gap analysis, etc.)
# ---------------------------------------------------------------------------


class TokenUsage(BaseModel):
    """LLM token usage and cost tracking."""

    model_config = _CFG

    input_tokens: Annotated[int, Field(description='Number of input tokens')]
    output_tokens: Annotated[int, Field(description='Number of output tokens')]
    cost_usd: Annotated[float, Field(description='Total cost in USD')]
    model: Annotated[str, Field(description='Model ID used')]


class Achievement(BaseModel):
    """Structured achievement statement used in value proposition narratives."""

    model_config = _CFG

    description: Annotated[str, Field(description='Achievement description')]
    impact: Annotated[str | None, Field(description='Business impact of the achievement')] = None
    metric: Annotated[str | None, Field(description='Quantified metric if available')] = None


class TargetRole(BaseModel):
    """Target role context for value proposition framing."""

    model_config = _CFG

    title: Annotated[str, Field(description='Target role title')]
    company: Annotated[str | None, Field(description='Target company')] = None
    industry: Annotated[str | None, Field(description='Target industry')] = None
    level: Annotated[str | None, Field(description='Target role seniority level')] = None


# ---------------------------------------------------------------------------
# Deprecated helper models — kept for backward compatibility with
# vpr_generator.py (spec 03) and fvs_validator.py (spec 04).
# These will be removed once those logic files are updated.
# ---------------------------------------------------------------------------


class EvidenceItem(BaseModel):
    """Single item in the Evidence & Alignment Matrix.
    Deprecated: use VPRRoleAlignment / VPRRequirementBreakdown instead.
    """

    model_config = _CFG

    requirement: Annotated[str, Field(description='Job requirement being addressed')]
    evidence: Annotated[str, Field(description='CV fact or gap response supporting this requirement')]
    alignment_score: Annotated[
        Literal['STRONG', 'MODERATE', 'DEVELOPING'],
        Field(description='How well the evidence matches the requirement'),
    ]
    impact_potential: Annotated[str, Field(description='How this experience translates to role success')]


class GapStrategy(BaseModel):
    """Gap mitigation strategy.
    Deprecated: use VPRConcernsAndMitigations instead.
    """

    model_config = _CFG

    gap: Annotated[str, Field(description='The missing or weak requirement')]
    mitigation_approach: Annotated[str, Field(description='Suggested talking points or reframing approach')]
    transferable_skills: Annotated[list[str], Field(default_factory=list, description='Related skills that partially address the gap')]


class ValueProposition(BaseModel):
    """High-level value proposition summary.
    Deprecated: use VPRValueProposition instead.
    """

    model_config = _CFG

    headline: Annotated[str, Field(description='Primary value proposition headline')]
    summary: Annotated[str, Field(description='Narrative summary of candidate value')]
    target_role: Annotated[TargetRole | None, Field(description='Target role context')] = None
    achievements: Annotated[
        list[Achievement],
        Field(default_factory=list, description='Supporting achievements'),
    ]
    differentiators: Annotated[
        list[str],
        Field(default_factory=list, description='Strategic differentiators'),
    ]


# ---------------------------------------------------------------------------
# New 10-section VPR schema
# ---------------------------------------------------------------------------

# Section 1 — Metadata


class VPRMetadata(BaseModel):
    """Report identification metadata."""

    model_config = _CFG

    report_date: Annotated[str, Field(description='ISO 8601 date string')]
    candidate_name: Annotated[str, Field(description='Candidate full name')]
    target_role: Annotated[str, Field(description='Target role title')]
    target_company: Annotated[str, Field(description='Target company name')]
    report_version: Annotated[str, Field(default='1.0', pattern=r'^\d+\.\d+$')]
    job_posting_url: Annotated[str | None, Field(default=None, description='Source URL of the job posting')]
    analysis_scope: Annotated[
        Literal['full', 'preliminary', 'targeted'],
        Field(default='full'),
    ]


# Section 2 — Executive Summary


class VPRStrength(BaseModel):
    model_config = _CFG

    strength: Annotated[str, Field(description='10-15 words')]
    evidence: Annotated[str, Field(description='Specific quantified proof')]
    relevance_to_role: str


class VPRConcern(BaseModel):
    model_config = _CFG

    concern: Annotated[str, Field(description='10-15 words')]
    severity: Literal['high', 'medium', 'low']
    mitigation: str


class VPRExecutiveSummary(BaseModel):
    """Overall fit scoring and top-level assessment."""

    model_config = _CFG

    overall_fit_score: Annotated[int, Field(ge=0, le=100)]
    fit_rationale: Annotated[str, Field(min_length=100, max_length=500)]
    top_three_strengths: Annotated[list[VPRStrength], Field(min_length=3, max_length=3)]
    top_three_concerns: Annotated[list[VPRConcern], Field(min_length=3, max_length=3)]
    recommended_approach: Literal[
        'aggressive_apply',
        'apply_with_customization',
        'apply_after_preparation',
        'do_not_apply',
    ]


# Section 3 — Role Alignment


class VPRResponsibility(BaseModel):
    model_config = _CFG

    responsibility: str
    alignment_score: Annotated[int, Field(ge=0, le=100)]
    candidate_evidence: Annotated[list[str], Field(min_length=1)]
    evidence_quality: Literal['direct', 'analogous', 'transferable', 'weak']


class VPRMustHave(BaseModel):
    model_config = _CFG

    requirement: str
    candidate_meets_requirement: bool
    evidence: str
    strength_of_evidence: Literal['strong', 'moderate', 'weak', 'none'] = 'moderate'


class VPRNiceToHave(BaseModel):
    model_config = _CFG

    preference: str
    candidate_has_this: bool
    evidence: str | None = None


class VPRPrerequisite(BaseModel):
    model_config = _CFG

    assumption: str
    candidate_meets_this: bool
    reasoning: str


class VPRRequirementBreakdown(BaseModel):
    model_config = _CFG

    must_have: list[VPRMustHave]
    nice_to_have: list[VPRNiceToHave]
    assumed_prerequisites: list[VPRPrerequisite]


class VPRRoleAlignment(BaseModel):
    """Core responsibility coverage and requirement breakdown."""

    model_config = _CFG

    core_responsibilities: Annotated[list[VPRResponsibility], Field(min_length=1)]
    requirement_breakdown: VPRRequirementBreakdown


# Section 4 — Experience Mapping


class VPRKeyAchievement(BaseModel):
    model_config = _CFG

    achievement: str
    metric: str
    impact: str


class VPRRelevantExperience(BaseModel):
    model_config = _CFG

    role: str
    organization: str
    duration: Annotated[
        str,
        Field(pattern=r'^\d+(\.\d+)? (year|years|month|months)$'),
    ]
    key_achievements: Annotated[list[VPRKeyAchievement], Field(min_length=1)]
    relevance_to_target_role: str
    relevance_score: int | None = None


class VPRExperienceGap(BaseModel):
    model_config = _CFG

    missing_experience: str
    impact_on_candidacy: Literal['critical', 'significant', 'moderate', 'minimal']
    compensating_factors: list[str]
    mitigation_strategy: str | None = None


class VPRExperienceMapping(BaseModel):
    """Relevant experience inventory and gap identification."""

    model_config = _CFG

    relevant_experiences: Annotated[list[VPRRelevantExperience], Field(min_length=1)]
    experience_gaps: list[VPRExperienceGap]


# Section 5 — Skills Analysis


class VPRTechnicalSkill(BaseModel):
    model_config = _CFG

    skill: str
    required_level: Literal['expert', 'advanced', 'intermediate', 'basic']
    candidate_level: Literal['expert', 'advanced', 'intermediate', 'basic', 'none']
    evidence: str
    gap: bool = False
    development_path: str | None = None


class VPRSoftSkill(BaseModel):
    model_config = _CFG

    skill: str
    candidate_demonstrates: bool
    evidence: str
    strength_level: Literal['exceptional', 'strong', 'adequate', 'developing']


class VPRToolProficiency(BaseModel):
    model_config = _CFG

    tool: str
    required_for_role: bool
    candidate_proficiency: Literal['expert', 'proficient', 'familiar', 'none']
    evidence: str
    needs_upskilling: bool = False


class VPRSkillsAnalysis(BaseModel):
    """Technical, soft-skill, and tooling coverage."""

    model_config = _CFG

    technical_skills: list[VPRTechnicalSkill]
    soft_skills: list[VPRSoftSkill]
    tool_proficiency: list[VPRToolProficiency]


# Section 6 — Evidence Gaps


class VPRIdentifiedGap(BaseModel):
    model_config = _CFG

    requirement: str
    current_evidence: str
    gap_severity: Literal['critical', 'high', 'medium', 'low']
    suggested_evidence: list[str]
    can_be_created_quickly: bool = False
    estimated_time_to_create: str | None = None


class VPRPriorityGap(BaseModel):
    model_config = _CFG

    gap: str
    priority: Annotated[int, Field(ge=1, le=5, description='1=highest')]
    action_item: str
    deadline: Literal['before_application', 'before_interview', 'nice_to_have']


class VPREvidenceGaps(BaseModel):
    """Portfolio gaps ranked by priority."""

    model_config = _CFG

    identified_gaps: Annotated[list[VPRIdentifiedGap], Field(min_length=1)]
    priority_gaps_to_address: Annotated[list[VPRPriorityGap], Field(min_length=1, max_length=5)]


# Section 7 — Differentiators


class VPRUniqueStrength(BaseModel):
    model_config = _CFG

    strength: str
    rarity: Literal['very_rare', 'uncommon', 'somewhat_rare']
    relevance: str
    proof: str


class VPRCompetitiveAdvantage(BaseModel):
    model_config = _CFG

    advantage: str
    vs_typical_candidate: str
    how_to_leverage: str | None = None


class VPRDifferentiators(BaseModel):
    """What sets the candidate apart from the typical applicant pool."""

    model_config = _CFG

    unique_strengths: Annotated[list[VPRUniqueStrength], Field(min_length=1, max_length=5)]
    competitive_advantages: list[VPRCompetitiveAdvantage]
    positioning_statement: Annotated[str, Field(min_length=100, max_length=300)]


# Section 8 — Concerns & Mitigations


class VPRMitigation(BaseModel):
    model_config = _CFG

    strategy: Literal[
        'reframe',
        'acknowledge_and_address',
        'provide_evidence',
        'show_analogous_experience',
    ]
    messaging: str


class VPRObjection(BaseModel):
    model_config = _CFG

    objection: str
    likelihood: Literal['very_likely', 'likely', 'possible', 'unlikely']
    mitigation: VPRMitigation
    where_to_address: list[Literal['cover_letter', 'cv', 'portfolio', 'interview']]


class VPRPreemptiveResponse(BaseModel):
    model_config = _CFG

    concern: str
    preemptive_action: str


class VPRConcernsAndMitigations(BaseModel):
    """Anticipated objections and preemptive responses."""

    model_config = _CFG

    likely_objections: Annotated[list[VPRObjection], Field(min_length=1)]
    preemptive_responses: list[VPRPreemptiveResponse]


# Section 9 — Value Proposition


class VPRPrimaryValue(BaseModel):
    model_config = _CFG

    statement: str
    evidence: str
    outcome_for_company: str


class VPRSecondaryValue(BaseModel):
    model_config = _CFG

    value: str
    proof: str


class VPRQuantifiedImpact(BaseModel):
    model_config = _CFG

    metric: str
    expected_range: str
    basis_for_projection: str


class VPRValueProposition(BaseModel):
    """Articulated value and projected business impact."""

    model_config = _CFG

    primary_value: VPRPrimaryValue
    secondary_values: Annotated[list[VPRSecondaryValue], Field(min_length=2, max_length=4)]
    quantified_impact: list[VPRQuantifiedImpact]
    elevator_pitch: Annotated[str, Field(min_length=100, max_length=200)]


# Section 10 — Application Strategy


class VPRKeywordGroup(BaseModel):
    model_config = _CFG

    primary: Annotated[list[str], Field(description='Use 2-3x across materials')]
    secondary: Annotated[list[str], Field(description='Use 1-2x across materials')]


class VPRApplicationStrategy(BaseModel):
    """Guidance for positioning the candidate across application materials."""

    model_config = _CFG

    messaging_approach: Annotated[str, Field(description='Recommended communication approach narrative')]
    ats_keywords: VPRKeywordGroup
    cv_lead_differentiator: Annotated[str, Field(description='What to open CV with')]
    sections_to_compress: list[str]


# Additional DOCX sections (not in vpr.json — sourced from VPRRequest)


class VPRCompanyInsight(BaseModel):
    """Company insights sourced from VPRRequest.company_context.
    Rendered as 'Company Insights' section in DOCX.
    """

    model_config = _CFG

    mission_and_position: str
    recent_initiatives: list[str]
    current_challenges: list[str]


class VPRVerificationEntry(BaseModel):
    """Confidence level per evidence category.
    Rendered as 'Verification Summary' in DOCX.
    """

    model_config = _CFG

    category: Annotated[str, Field(description="e.g. 'LMS deployment & management'")]
    confidence: Literal['high', 'medium', 'growth_area']
    basis: Annotated[str, Field(description='What evidence supports this confidence level')]


class VPRVerificationSummary(BaseModel):
    model_config = _CFG

    entries: list[VPRVerificationEntry]
    key_evidence_sources: Annotated[
        list[str],
        Field(description="e.g. 'Master CV', 'Gap Analysis Responses', 'Company Research'"),
    ]


# ---------------------------------------------------------------------------
# Root VPR model — full replacement of the previous flat 9-field model
# ---------------------------------------------------------------------------


_VPR_SECTION_FIELDS: frozenset[str] = frozenset(
    {
        'metadata',
        'executive_summary',
        'role_alignment',
        'experience_mapping',
        'skills_analysis',
        'evidence_gaps',
        'differentiators',
        'concerns_and_mitigations',
        'value_proposition',
        'application_strategy',
    }
)


class VPR(BaseModel):
    """Complete 10-section Value Proposition Report.

    Stored in DynamoDB as snake_case field names.
    Serialized as camelCase for API/frontend consumers via .model_dump(by_alias=True).

    Sections are Optional to support graceful loading of legacy flat DynamoDB items
    that pre-date the 10-section schema.  Freshly generated VPRs always have all
    sections populated; the pipeline and fvs_validator only receive those.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra='ignore',
        alias_generator=to_camel,
    )

    @model_validator(mode='before')
    @classmethod
    def _coerce_legacy_section_types(cls, values: Any) -> Any:
        """Drop section values that are not dicts or model instances.

        Legacy DynamoDB items stored sections as flat strings or lists.
        Replacing them with None allows the model to parse without crashing;
        the section fields will be None for those legacy items.

        Valid types are kept: dict (raw DynamoDB/JSON), BaseModel instance
        (already-parsed section), or None.
        """
        if not isinstance(values, dict):
            return values
        for field_name in _VPR_SECTION_FIELDS:
            if field_name in values and not isinstance(values[field_name], (dict, BaseModel, type(None))):
                values[field_name] = None
        return values

    # Identity
    application_id: str
    user_id: str

    # 10 content sections — Optional to support legacy flat DynamoDB items
    metadata: VPRMetadata | None = None
    executive_summary: VPRExecutiveSummary | None = None
    role_alignment: VPRRoleAlignment | None = None
    experience_mapping: VPRExperienceMapping | None = None
    skills_analysis: VPRSkillsAnalysis | None = None
    evidence_gaps: VPREvidenceGaps | None = None
    differentiators: VPRDifferentiators | None = None
    concerns_and_mitigations: VPRConcernsAndMitigations | None = None
    value_proposition: VPRValueProposition | None = None
    application_strategy: VPRApplicationStrategy | None = None

    # 2 additional DOCX sections (optional)
    company_insights: VPRCompanyInsight | None = None
    verification_summary: VPRVerificationSummary | None = None

    # Record metadata
    version: int = 1
    language: Literal['en', 'he'] = 'en'
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    word_count: int = 0


# ---------------------------------------------------------------------------
# Request / Response — preserved with config added
# ---------------------------------------------------------------------------


class VPRRequest(BaseModel):
    """Request model for VPR generation endpoint."""

    model_config = _CFG

    application_id: Annotated[str, Field(description='Unique application identifier')]
    user_id: Annotated[str, Field(description='User requesting VPR')]
    job_posting: Annotated[JobPosting, Field(description='Structured job posting data')]
    gap_responses: Annotated[
        list[GapResponse],
        Field(default_factory=list, description='Optional gap analysis responses'),
    ]
    company_context: Annotated[CompanyContext | None, Field(description='Optional company research data')] = None
    target_version: Annotated[int, Field(default=1, description='VPR version to write; set by handler before generation')] = 1


class VPRResponse(BaseModel):
    """Response model for VPR generation endpoint."""

    model_config = _CFG

    success: Annotated[bool, Field(description='Whether VPR generation succeeded')]
    vpr: Annotated[VPR | None, Field(description='Generated VPR if successful')] = None
    token_usage: Annotated[TokenUsage | None, Field(description='LLM token usage and cost')] = None
    generation_time_ms: Annotated[int, Field(default=0, description='Time taken in milliseconds')]
    error: Annotated[str | None, Field(description='Error message if failed')] = None
