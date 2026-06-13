"""
VPR Prompt builder per docs/features/CareerVP Prompt Library.md lines 128-259.
Provides the canonical template and helpers for VPR generation.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from careervp.models.cv import UserCV
from careervp.models.vpr import VPRRequest

if TYPE_CHECKING:
    from careervp.models.vpr import VPR

# VPR_GENERATION_PROMPT removed per spec 09 (superseded by PHASE2_PROMPT_2_1_TEMPLATE)
# build_vpr_prompt, PHASE2_VALIDATION_SYSTEM_PROMPT, and build_phase2_validation_prompt also removed.


# Anti-AI detection list from docs/specs/03-vpr-generator.md lines 80-84.
BANNED_WORDS: list[str] = [
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
]

# Stage-specific system prompts for 6-stage VPR pipeline.
STAGE_1_SYSTEM_PROMPT = 'You are Stage 1 Analyzer. Extract only facts from CV/job inputs and return strict JSON. Do not invent facts.'
STAGE_2_SYSTEM_PROMPT = 'You are Stage 2 Evidence Mapper. Map explicit CV achievements to job requirements and return strict JSON.'
STAGE_3_SYSTEM_PROMPT = 'You are Stage 3 Synthesizer. Build a natural, evidence-grounded draft VPR in strict JSON.'
STAGE_4_SYSTEM_PROMPT = 'You are Stage 4 Self-Corrector. Improve clarity, factual grounding, and anti-AI style in strict JSON.'
STAGE_5_SYSTEM_PROMPT = 'You are Stage 5 Formatter. Convert corrected content into the final VPR JSON schema exactly.'
STAGE_6_SYSTEM_PROMPT = 'You are Stage 6 Meta Evaluator. Evaluate quality and anti-AI readiness, and return strict JSON diagnostics.'

STAGE_3_FEW_SHOT_EXAMPLE = """Few-shot example:
Input evidence:
{
  "matches": [
    {
      "requirement": "Lead cross-functional teams",
      "evidence": "Managed a 9-person team to launch two products"
    }
  ]
}
Output draft:
{
  "executive_summary": "The candidate has repeatedly led cross-functional teams and shipped outcomes under deadlines.",
  "evidence_matrix": [
    {
      "requirement": "Lead cross-functional teams",
      "evidence": "Managed a 9-person team to launch two products",
      "alignment_score": "STRONG",
      "impact_potential": "Can coordinate roadmap execution with engineering, design, and operations."
    }
  ],
  "differentiators": ["Execution leadership with measurable launches"],
  "gap_strategies": [],
  "cultural_fit": "Collaborative and delivery-focused operating style.",
  "talking_points": ["Share how cross-functional planning reduced launch risk."],
  "keywords": ["Cross-functional leadership", "Product delivery"]
}
"""

STAGE_4_FEW_SHOT_EXAMPLE = """Few-shot example:
Input draft:
{
  "executive_summary": "I leverage robust strategies to streamline outcomes across the organization."
}
Output corrected:
{
  "executive_summary": "I help teams focus on the few moves that improve outcomes and keep delivery steady.",
  "corrections_applied": ["Removed banned terms", "Reduced formulaic language"]
}
"""

STAGE_1_USER_PROMPT_TEMPLATE = """Analyze the CV and job posting and return JSON with:
- key_skills: list[str]
- experience_level: str
- job_requirements: list[str]
- cv_achievements: list[str]

CV:
{cv_json}

JOB:
{job_json}
"""

STAGE_2_USER_PROMPT_TEMPLATE = """From this analysis JSON, map evidence to requirements and return:
- matches: list[{{requirement, evidence, alignment_score, impact_potential}}]
- uncovered_requirements: list[str]

ANALYSIS:
{analysis_json}
"""

STAGE_3_USER_PROMPT_TEMPLATE = """Create a draft value proposition JSON with fields:
executive_summary, evidence_matrix, differentiators, gap_strategies, cultural_fit, talking_points, keywords.
Stay factual and natural.

{few_shot_example}

EVIDENCE:
{evidence_json}
{feedback_block}
"""

STAGE_4_USER_PROMPT_TEMPLATE = """Self-correct this draft JSON for clarity, factual grounding, and anti-AI writing.
Return same VPR fields plus corrections_applied: list[str].

{few_shot_example}

DRAFT:
{draft_json}
{feedback_block}
"""

STAGE_5_USER_PROMPT_TEMPLATE = """Format corrected proposition into final VPR schema JSON with:
executive_summary, evidence_matrix, differentiators, gap_strategies, cultural_fit,
talking_points, keywords, language, version.

CORRECTED:
{corrected_json}

REQUEST_CONTEXT:
{request_context_json}
"""

STAGE_6_USER_PROMPT_TEMPLATE = """Evaluate this VPR JSON and return diagnostics JSON:
- anti_ai_score: float
- issues: list[str]
- passed_gate: bool

VPR:
{vpr_json}
"""


def build_stage_1_prompt(user_cv: UserCV, request: VPRRequest) -> str:
    """Build Stage 1 analysis prompt."""
    cv_payload = _serialize_cv_for_prompt(user_cv)
    job_payload = request.job_posting.model_dump(mode='json')
    return STAGE_1_USER_PROMPT_TEMPLATE.format(
        cv_json=json.dumps(cv_payload, indent=2),
        job_json=json.dumps(job_payload, indent=2),
    )


def build_stage_2_prompt(analysis_payload: dict[str, Any]) -> str:
    """Build Stage 2 evidence extraction prompt."""
    return STAGE_2_USER_PROMPT_TEMPLATE.format(analysis_json=json.dumps(analysis_payload, indent=2))


def build_stage_3_prompt(evidence_payload: dict[str, Any], feedback: str | None = None) -> str:
    """Build Stage 3 synthesis prompt with few-shot guidance."""
    feedback_block = f'\nFEEDBACK:\n{feedback}\n' if feedback else ''
    return STAGE_3_USER_PROMPT_TEMPLATE.format(
        few_shot_example=STAGE_3_FEW_SHOT_EXAMPLE,
        evidence_json=json.dumps(evidence_payload, indent=2),
        feedback_block=feedback_block,
    )


def build_stage_4_prompt(draft_payload: dict[str, Any], feedback: str | None = None) -> str:
    """Build Stage 4 self-correction prompt with few-shot guidance."""
    feedback_block = f'\nFEEDBACK:\n{feedback}\n' if feedback else ''
    return STAGE_4_USER_PROMPT_TEMPLATE.format(
        few_shot_example=STAGE_4_FEW_SHOT_EXAMPLE,
        draft_json=json.dumps(draft_payload, indent=2),
        feedback_block=feedback_block,
    )


def build_stage_5_prompt(corrected_payload: dict[str, Any], request: VPRRequest) -> str:
    """Build Stage 5 final formatting prompt."""
    request_context = {
        'application_id': request.application_id,
        'user_id': request.user_id,
        'language': request.job_posting.language,
    }
    return STAGE_5_USER_PROMPT_TEMPLATE.format(
        corrected_json=json.dumps(corrected_payload, indent=2),
        request_context_json=json.dumps(request_context, indent=2),
    )


def build_stage_6_prompt(vpr_payload: dict[str, Any]) -> str:
    """Build Stage 6 meta-evaluation prompt."""
    return STAGE_6_USER_PROMPT_TEMPLATE.format(vpr_json=json.dumps(vpr_payload, indent=2))


# build_vpr_prompt removed per spec 09 (replaced by build_phase2_prompt)


def check_anti_ai_patterns(content: str) -> list[str]:
    """
    Return banned words detected in generated content.
    """
    content_lower = content.lower()
    return [word for word in BANNED_WORDS if word in content_lower]


def _serialize_cv_for_prompt(user_cv: UserCV) -> dict[str, Any]:
    """
    Serialize UserCV while preserving IMMUTABLE facts (FVS requirement).
    """
    data = user_cv.model_dump(mode='json')
    # Remove unused bulk fields.
    data.pop('raw_text', None)
    data.pop('file_content', None)
    data.pop('source_file_key', None)
    for field in ['email', 'phone', 'location', 'linkedin']:
        data.pop(field, None)
    contact_info = data.get('contact_info')
    if isinstance(contact_info, dict):
        # Strip contact identifiers before sharing with the LLM.
        for field in ['email', 'phone']:
            contact_info.pop(field, None)
        if not any(value for value in contact_info.values()):
            data.pop('contact_info', None)
    return data


# ── Phase 2 system prompts ────────────────────────────────────────────────────

PHASE2_SYSTEM_PROMPT = (
    'You are CareerVP VPR Generator Phase 2. Your task is to produce a complete,\n'
    'evidence-based Value Proposition Report in strict JSON. Every claim must be\n'
    'verifiable from the CV and gap response inputs. Return only valid JSON — no\n'
    'markdown, no code fences.\n'
    '\n'
    '=== SELF-VALIDATION RULES (apply before returning) ===\n'
    '\n'
    'Before returning your JSON, verify ALL of the following. If any rule fails,\n'
    'correct it inline — do NOT return a separate validation_notes field.\n'
    '\n'
    '1. BANNED WORDS: confirm none of these appear anywhere in string values:\n'
    '   leverage, delve into, landscape, robust, streamline, utilize, facilitate,\n'
    '   implement, cutting-edge, best-practices, industry-leading, game-changer,\n'
    '   paradigm shift, synergy\n'
    '   If found: replace with plain direct language.\n'
    '\n'
    '2. EVIDENCE GROUNDING: every field named "evidence" or "proof" must quote\n'
    '   a specific metric, project name, or outcome from the CV or gap responses.\n'
    '   Vague phrases like "extensive experience" are not evidence — replace with\n'
    '   the nearest quantified fact.\n'
    '\n'
    '3. SECTION COMPLETENESS: all 10 top-level keys must be present and non-empty:\n'
    '   metadata, executive_summary, role_alignment, experience_mapping,\n'
    '   skills_analysis, evidence_gaps, differentiators, concerns_and_mitigations,\n'
    '   value_proposition, application_strategy.\n'
    '   company_insights and verification_summary are optional.\n'
    '\n'
    '4. ARRAY MINIMUMS:\n'
    '   executive_summary.top_three_strengths: exactly 3 items\n'
    '   executive_summary.top_three_concerns: exactly 3 items\n'
    '   role_alignment.core_responsibilities: at least 3 items\n'
    '   role_alignment.requirement_breakdown.must_have: at least 3 items\n'
    '   differentiators.unique_strengths: at least 2 items\n'
    '   concerns_and_mitigations.likely_objections: at least 2 items\n'
    '   value_proposition.secondary_values: at least 2 items\n'
    '\n'
    '5. SCORE RANGES:\n'
    '   executive_summary.overall_fit_score: integer 1–100\n'
    '   role_alignment.core_responsibilities[].alignment_score: integer 1–10\n'
    '   experience_mapping.relevant_experiences[].relevance_score: integer 1–10\n'
    '\n'
    '6. ENUM VALUES: verify all enum fields use only the allowed values listed\n'
    '   in the schema. Replace any free-text variants with the nearest valid enum.\n'
)

PHASE2_OUTPUT_SCHEMA = """{
  "metadata": {
    "report_date": "YYYY-MM-DD",
    "candidate_name": "...",
    "target_role": "...",
    "target_company": "...",
    "report_version": "1.0",
    "analysis_scope": "full"
  },
  "executive_summary": {
    "overall_fit_score": 0,
    "fit_rationale": "2-3 sentence explanation (100-500 chars)",
    "top_three_strengths": [
      {"strength": "10-15 words", "evidence": "quantified proof", "relevance_to_role": "direct connection"}
    ],
    "top_three_concerns": [
      {"concern": "10-15 words", "severity": "high|medium|low", "mitigation": "strategy"}
    ],
    "recommended_approach": "aggressive_apply|apply_with_customization|apply_after_preparation|do_not_apply"
  },
  "differentiators": {
    "top_differentiators": [
      {
        "differentiator": "15-25 words describing unique value",
        "evidence": "specific metric or named outcome",
        "rarity": "top_1%|top_5%|top_10%|common",
        "relevance_to_target_role": "direct connection"
      }
    ],
    "competitive_advantages": [
      {
        "advantage": "...",
        "evidence": "...",
        "impact": "..."
      }
    ]
  },
  "value_proposition": {
    "primary_value_statement": "forward-looking promise: impact you will reduce, scale, build, or drive",
    "secondary_value_points": [
      {
        "value_point": "...",
        "supporting_evidence": "..."
      }
    ],
    "target_company_fit": "why this role specifically"
  },
  "role_alignment": {
    "core_responsibilities": [
      {
        "responsibility": "...",
        "alignment_score": 0,
        "candidate_evidence": ["..."],
        "evidence_quality": "direct|analogous|transferable|weak"
      }
    ],
    "requirement_breakdown": {
      "must_have": [
        {
          "requirement": "...",
          "candidate_meets_requirement": true,
          "evidence": "...",
          "strength_of_evidence": "strong|moderate|weak|none"
        }
      ],
      "nice_to_have": [
        {"preference": "...", "candidate_has_this": true, "evidence": "..."}
      ],
      "assumed_prerequisites": [
        {"assumption": "...", "candidate_meets_this": true, "reasoning": "..."}
      ]
    }
  },
  "experience_mapping": {
    "relevant_experiences": [
      {
        "role": "...",
        "organization": "...",
        "duration": "N years",
        "key_achievements": [
          {"achievement": "...", "metric": "...", "impact": "..."}
        ],
        "relevance_to_target_role": "...",
        "relevance_score": 0
      }
    ],
    "experience_gaps": [
      {
        "missing_experience": "...",
        "impact_on_candidacy": "critical|significant|moderate|minimal",
        "compensating_factors": ["..."],
        "mitigation_strategy": "..."
      }
    ]
  },
  "skills_analysis": {
    "technical_skills": [
      {
        "skill": "...",
        "required_level": "expert|advanced|intermediate|basic",
        "candidate_level": "expert|advanced|intermediate|basic|none",
        "evidence": "...",
        "gap": false
      }
    ],
    "soft_skills": [
      {
        "skill": "...",
        "candidate_demonstrates": true,
        "evidence": "...",
        "strength_level": "exceptional|strong|adequate|developing"
      }
    ],
    "tool_proficiency": [
      {
        "tool": "...",
        "required_for_role": true,
        "candidate_proficiency": "expert|proficient|familiar|none",
        "evidence": "...",
        "needs_upskilling": false
      }
    ]
  },
  "evidence_gaps": {
    "identified_gaps": [
      {
        "requirement": "...",
        "current_evidence": "...",
        "gap_severity": "critical|high|medium|low",
        "suggested_evidence": ["..."],
        "can_be_created_quickly": false
      }
    ],
    "priority_gaps_to_address": [
      {
        "gap": "...",
        "priority": 1,
        "action_item": "...",
        "deadline": "before_application|before_interview|nice_to_have"
      }
    ]
  },
  "differentiators": {
    "unique_strengths": [
      {
        "strength": "...",
        "rarity": "very_rare|uncommon|somewhat_rare",
        "relevance": "...",
        "proof": "..."
      }
    ],
    "competitive_advantages": [
      {"advantage": "...", "vs_typical_candidate": "..."}
    ],
    "positioning_statement": "100-300 char paragraph"
  },
  "concerns_and_mitigations": {
    "likely_objections": [
      {
        "objection": "...",
        "likelihood": "very_likely|likely|possible|unlikely",
        "mitigation": {
          "strategy": "reframe|acknowledge_and_address|provide_evidence|show_analogous_experience",
          "messaging": "..."
        },
        "where_to_address": ["cover_letter|cv|portfolio|interview"]
      }
    ],
    "preemptive_responses": [
      {"concern": "...", "preemptive_action": "..."}
    ]
  },
  "value_proposition": {
    "primary_value": {"statement": "...", "evidence": "...", "outcome_for_company": "..."},
    "secondary_values": [{"value": "...", "proof": "..."}],
    "quantified_impact": [
      {"metric": "...", "expected_range": "...", "basis_for_projection": "..."}
    ],
    "elevator_pitch": "100-200 char 30-second pitch"
  },
  "application_strategy": {
    "messaging_approach": "narrative of recommended communication approach",
    "ats_keywords": {"primary": ["keyword"], "secondary": ["keyword"]},
    "cv_lead_differentiator": "what to open CV with",
    "sections_to_compress": ["which CV sections to minimize"]
  },
  "company_insights": {
    "mission_and_position": "...",
    "recent_initiatives": ["..."],
    "current_challenges": ["..."]
  },
  "verification_summary": {
    "entries": [
      {"category": "...", "confidence": "high|medium|growth_area", "basis": "..."}
    ],
    "key_evidence_sources": ["Master CV", "Gap Analysis Responses", "Company Research"]
  }
}"""

# PHASE2_VALIDATION_SYSTEM_PROMPT removed per spec 09 (Stage 4 LLM call removed in spec 07)

# ── Phase 2 Prompt 2.1 — full VPR generation (replaces Stage 3 as primary) ───

PHASE2_PROMPT_2_1_TEMPLATE = """Generate a complete, evidence-based Value Proposition Report (VPR) in strict JSON.

=== INPUT DATA ===

EVIDENCE MATCHES (from Stages 1-2):
{evidence_json}

CV FACTS (immutable — do not invent):
{cv_facts_json}

JOB REQUIREMENTS:
{job_requirements_json}

COMPANY RESEARCH:
{company_research_json}

GAP ANALYSIS RESPONSES:
{gap_responses_json}
{feedback_block}
=== GENERATION GUIDANCE FOR HIGH-IMPACT SECTIONS ===

- DIFFERENTIATORS & VALUE_POSITION: Prioritize claims that are rare — your differentiator should be in the top 5% of what candidates offer. If a strength is common among applicants, it is NOT a differentiator. Cite specific metrics or named outcomes.
- PROOF CITATION: Every claim must cite a specific metric, quantified fact, or named outcome from the CV or gap analysis. Vague assertions fail.
- POSITIONING_STATEMENT: Name the target company in your positioning_statement — "for CompanyName" rather than generic language.
- elevator_pitch: Summarize value in 1-2 sentences that a hiring manager would remember.
- PRIMARY_VALUE.STATEMENT: Make forward-looking commitments — describe impact you will reduce, scale, build, or drive.

=== OUTPUT REQUIREMENTS ===

Return only valid JSON matching the schema in the system prompt — no markdown, no code fences.
Every field must be populated from the provided inputs.
Required top-level sections: metadata, executive_summary, role_alignment, experience_mapping,
skills_analysis, evidence_gaps, differentiators, concerns_and_mitigations, value_proposition,
application_strategy, company_insights, verification_summary.

=== ANTI-AI WRITING RULES ===

BANNED WORDS (automatic failure if present):
leverage, delve into, landscape, robust, streamline, utilize, facilitate, implement,
cutting-edge, best practices, industry-leading, game-changer, paradigm shift, synergy

WRITING STYLE REQUIREMENTS:
- Sentence length: 8-25 words average (vary, do not exceed 26 word average)
- No repeated sentence openings (same 2-word start >= 3 times = failure)
- Lexical diversity: unique/total word ratio >= 0.42
- No formulaic transitions: furthermore, moreover, additionally, in conclusion, in summary
- No filler phrases: "in today's fast-paced", "across the organization", "in order to"
- Nominalization ratio: -tion/-ment/-ness endings <= 18% of total words
- Use approximations: "nearly 40%" not "39.7%"

=== IMMUTABLE FACT RULES (violations = generation failure) ===

- NEVER invent companies, roles, dates, or metrics not in the CV input
- NEVER state the candidate worked at the target company
- Use exact company names and role titles from CV (e.g., "AllCloud", "Director of AWS Training")
- All years and company names must appear in the provided CV facts

Generate the VPR JSON now:"""

# ── Phase 2 Prompt 2.2 — validation/refinement (replaces Stage 4 as primary) ─

PHASE2_PROMPT_2_2_TEMPLATE = """Review and correct the following VPR JSON against the 6 validation rules below.
Return the corrected VPR JSON with an added validation_notes field (list of strings) describing every change made.

=== INPUT VPR ===
{vpr_json}

=== CV FACTS (source of truth) ===
{cv_facts_json}
{validation_feedback_block}
=== VALIDATION CHECKLIST — review each rule and correct violations ===

Rule 1 — Evidence Traceability:
  Every factual claim in executive_summary, differentiators, value_proposition,
  and experience_mapping must trace to either cv_facts_json or gap_responses_json.
  If you cannot find the source, remove or soften the claim.

Rule 2 — Quantification Consistency:
  If a metric appears in one section (e.g. "$1M+ revenue" in experience_mapping),
  it must use identical wording wherever repeated. No paraphrasing of numbers.

Rule 3 — Alignment Score Justification:
  role_alignment.core_responsibilities[].alignment_score must follow:
    direct evidence   -> 80-100
    analogous evidence -> 60-79
    transferable evidence -> 40-59
    weak/no evidence -> 0-39
  evidence_quality field must match the score band.

Rule 4 — Gap Severity Calibration:
  evidence_gaps.identified_gaps[].gap_severity definitions:
    critical -> role cannot be filled without this; application likely rejected
    high -> significant concern; must address in cover letter
    medium -> concern but not disqualifying; address if possible
    low -> minor gap; addressable in interview

Rule 5 — Differentiator Rarity:
  differentiators.unique_strengths[].rarity must be defensible:
    very_rare -> <5% of comparable candidates have this
    uncommon -> 5-20% of comparable candidates have this
    somewhat_rare -> 20-40% of comparable candidates have this
  If a strength is common (>40%), it should be in competitive_advantages instead.

Rule 6 — Mitigation Substance:
  concerns_and_mitigations.likely_objections[].mitigation.messaging must be:
    STRONG: specific to candidate's actual experience, addresses the concern directly
    WEAK (rewrite): generic, could apply to any candidate, or repeats the concern

Return only valid JSON — the corrected VPR with validation_notes added."""


# ── Phase 2 builder functions ─────────────────────────────────────────────────


def build_phase2_prompt(
    evidence_payload: dict[str, Any],
    user_cv: UserCV,
    request: VPRRequest,
    feedback: str | None = None,
) -> str:
    """Build Phase 2 generation prompt (primary replacement for Stage 3)."""
    cv_facts = _serialize_cv_for_prompt(user_cv)
    job_requirements = request.job_posting.model_dump(mode='json')
    gap_responses = [gr.model_dump(mode='json') for gr in request.gap_responses]
    company_research = request.company_context.model_dump(mode='json') if request.company_context else {}
    feedback_block = f'\nREGENERATION FEEDBACK:\n{feedback}\n' if feedback else ''
    return PHASE2_PROMPT_2_1_TEMPLATE.format(
        evidence_json=json.dumps(evidence_payload, indent=2),
        cv_facts_json=json.dumps(cv_facts, indent=2),
        job_requirements_json=json.dumps(job_requirements, indent=2),
        company_research_json=json.dumps(company_research, indent=2),
        gap_responses_json=json.dumps(gap_responses, indent=2),
        feedback_block=feedback_block,
    )


def build_phase2_system_prompt() -> str:
    """Build the cached Phase 2 system prompt including the output schema."""
    return f'{PHASE2_SYSTEM_PROMPT}\n\n=== OUTPUT SCHEMA ===\n{PHASE2_OUTPUT_SCHEMA}'


def build_vpr_digest(vpr: 'VPR') -> dict[str, Any]:
    """Build a compact VPR digest for downstream prompt consumers."""
    executive_summary = vpr.executive_summary
    differentiators = vpr.differentiators
    application_strategy = vpr.application_strategy

    return {
        'positioning_statement': differentiators.positioning_statement if differentiators else None,
        'top_differentiators': [item.strength for item in differentiators.unique_strengths[:3]] if differentiators else [],
        'ats_keywords_primary': application_strategy.ats_keywords.primary if application_strategy else [],
        'overall_fit_score': executive_summary.overall_fit_score if executive_summary else None,
        'recommended_approach': executive_summary.recommended_approach if executive_summary else None,
    }


# build_phase2_validation_prompt removed per spec 09 (Stage 4 LLM call removed in spec 07)
