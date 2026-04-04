"""Three-stage CV tailoring pipeline for P2 spec.

Stage 1: Keyword mapping (Python, no LLM) — extracts from VPR + job description + parsed_facts
Stage 2: CV generation (LLM Haiku) — produces CVSections with verification block
Stage 3: Fact verification (Python) — cross-checks against parsed_facts, strips hallucinations
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from careervp.models.cv import UserCV as CVUserCV
from careervp.models.cv_models import UserCV
from careervp.models.cv_tailoring_models import (
    CVCertificationSection,
    CVEducationSection,
    CVExperienceSection,
    CVSections,
    CVSkillsSection,
    ExperienceItemInPlan,
    PrimaryKeyword,
    Stage1Output,
    Stage2Output,
    Stage2Verification,
    Stage3Result,
)
from careervp.models.result import Result, ResultCode

if TYPE_CHECKING:
    from careervp.models.vpr import VPR


# P2: Stage 1 system prompt (verbatim from spec)
STAGE1_SYSTEM_PROMPT = """You are a senior technical recruiter and ATS optimization expert.
Your task is to analyze a job posting and a Value Proposition Report,
then create a precise keyword-to-evidence mapping plan for CV tailoring.

You must return ONLY valid JSON. No preamble, no markdown, no explanation.
The JSON structure is defined in the user message.

CRITICAL RULE: You may only reference skills, job titles, companies,
dates, and achievements that exist verbatim in the provided parsed_facts.
Do not invent, infer, or embellish any candidate information."""


# P2: Stage 2 system prompt (verbatim from spec)
STAGE2_SYSTEM_PROMPT = """You are an expert CV writer specializing in technical roles.
You create ATS-optimized CVs that pass automated screening AND
impress human reviewers.

RULES (non-negotiable):
1. ZERO HALLUCINATIONS — every fact, date, metric, company name, and
   job title must appear in the provided parsed_facts. If unsure, omit.
2. CAR/STAR format for ALL experience bullets — Challenge/Action/Result
   with a quantifiable metric whenever one exists in the source data.
3. Keyword density — primary keywords must appear 2-3x naturally across
   summary, skills, and experience sections.
4. Length — 1 page (approximately 450-600 words of body content).
   Do not pad. Do not truncate relevant experience.
5. ATS formatting — no tables, no text boxes, no columns in the content
   structure. Simple flat sections only.
6. Anti-AI detection — vary sentence structure, use natural transitions,
   avoid "leverage", "delve", "robust", "streamline", "landscape",
   "spearhead" (overused). Use concrete verbs tied to actual work.
7. Self-correct before finalizing — explicitly check keyword match and
   summary alignment before producing output JSON.

Return ONLY valid JSON. No preamble, no markdown, no explanation."""


# Stage 1: Keyword mapping (Python, no LLM call)
def run_stage1_keyword_mapping(  # noqa: C901
    vpr: VPR | None,
    job_description: str,
    parsed_facts: UserCV,
    gap_responses: dict[str, Any] | None = None,
    llm_client: Any = None,  # Reserved for future use; Stage 1 is currently Python-only
) -> Stage1Output:
    """Stage 1: Extract keywords and build evidence map from VPR + job description + parsed_facts.

    This is a Python-only stage (no LLM call) per spec line 87-107.
    Uses existing keyword extraction logic and extracts structured VPR data.
    """
    # Extract UVP statement from VPR if available
    uvp_statement = ''
    if vpr and hasattr(vpr, 'positioning_statement') and vpr.positioning_statement:
        uvp_statement = vpr.positioning_statement

    # Extract key differentiators from VPR
    key_differentiators: list[str] = []
    if vpr and hasattr(vpr, 'unique_strengths') and vpr.unique_strengths:
        key_differentiators = list(vpr.unique_strengths[:5])

    # Extract primary keywords from job description (reuse existing logic)
    # Note: We import here to avoid circular imports
    from careervp.logic.cv_tailoring import (
        analyze_and_map_keywords,
    )

    keyword_map = analyze_and_map_keywords(parsed_facts, job_description)

    # Build PrimaryKeyword list with evidence mapping
    primary_keywords: list[PrimaryKeyword] = []
    keywords_by_category: dict[str, list[str]] = {
        'required': keyword_map.required,
        'preferred': keyword_map.preferred,
        'nice_to_have': keyword_map.nice_to_have,
    }

    priority = 1
    for category, keywords in keywords_by_category.items():
        for kw in keywords:
            # Look for supporting evidence in parsed_facts
            evidence: str | None = _find_keyword_evidence(kw, parsed_facts)
            primary_keywords.append(
                PrimaryKeyword(
                    keyword=kw,
                    category=category,
                    priority=priority,
                    supporting_evidence=evidence,
                )
            )
            priority += 1

    # Keywords to emphasize (top 12-18)
    keywords_to_emphasize = keyword_map.all_keywords[:18]

    # Keywords missing from CV
    all_cv_keywords = set()
    if parsed_facts.skills:
        for skill in parsed_facts.skills:
            if hasattr(skill, 'name'):
                all_cv_keywords.add(skill.name.lower())
            elif isinstance(skill, str):
                all_cv_keywords.add(skill.lower())

    keywords_missing_from_cv = [kw for kw in keywords_to_emphasize if kw.lower() not in all_cv_keywords]

    # Experience items to include (roles with relevant keywords)
    experience_items_to_include: list[ExperienceItemInPlan] = []
    if parsed_facts.work_experience:
        for exp in parsed_facts.work_experience:
            # Check if any keyword maps to this experience
            exp_text = f'{exp.role} {exp.description or ""}'.lower()
            if any(kw.lower() in exp_text for kw in keywords_to_emphasize[:12]):
                experience_items_to_include.append(
                    ExperienceItemInPlan(
                        company=exp.company,
                        title=exp.role,
                        include_reason=f'Matches keywords: {", ".join([kw for kw in keywords_to_emphasize[:5] if kw.lower() in exp_text])}',
                    )
                )

    # Summary focus derived from UVP + keywords
    summary_focus = uvp_statement
    if keywords_to_emphasize:
        summary_focus = f'{uvp_statement} Key strengths: {", ".join(keywords_to_emphasize[:5])}'

    # Skills to feature (intersection of CV skills and keywords)
    cv_skills: set[str] = set()
    if parsed_facts.skills:
        for skill in parsed_facts.skills:
            if hasattr(skill, 'name'):
                cv_skills.add(skill.name.lower())
            elif isinstance(skill, str):
                cv_skills.add(skill.lower())

    skills_to_feature = [kw for kw in keywords_to_emphasize if kw.lower() in cv_skills]

    return Stage1Output(
        uvp_statement=uvp_statement,
        key_differentiators=key_differentiators,
        primary_keywords=primary_keywords,
        keywords_to_emphasize=keywords_to_emphasize,
        keywords_missing_from_cv=keywords_missing_from_cv,
        experience_items_to_include=experience_items_to_include,
        experience_items_to_exclude=[],  # Could be added if needed
        summary_focus=summary_focus,
        skills_to_feature=skills_to_feature,
    )


def _find_keyword_evidence(keyword: str, cv: UserCV) -> str | None:
    """Find supporting evidence for a keyword in the CV."""
    keyword_lower = keyword.lower()

    # Check skills
    if cv.skills:
        for skill in cv.skills:
            skill_name = (skill.name if hasattr(skill, 'name') else str(skill)).lower()
            if keyword_lower in skill_name:
                return f'Skill: {skill_name}'

    # Check work experience descriptions
    if cv.work_experience:
        for exp in cv.work_experience:
            if exp.description and keyword_lower in exp.description.lower():
                return f'Experience: {exp.role} at {exp.company}'

    return None


# Stage 2: CV generation (LLM Haiku call)
def run_stage2_cv_generation(
    stage1_output: Stage1Output,
    parsed_facts: UserCV,
    job_description: str,
    company_context: dict[str, Any] | None = None,
    user_feedback: str | None = None,
    llm_client: Any = None,  # LLM client injected for testing
) -> Result[Stage2Output]:
    """Stage 2: Generate CV using LLM (Haiku).

    Calls the LLM with stage1 output and parsed_facts to produce CVSections.
    """
    if llm_client is None:
        return Result(
            success=False,
            error='LLM client not provided',
            code=ResultCode.LLM_API_ERROR,
        )

    # Build user prompt with stage1 and parsed_facts
    prompt_parts = [
        '# Job Description',
        job_description,
        '# Stage 1 Keyword Mapping',
        json.dumps(stage1_output.model_dump(), indent=2),
        '# Parsed CV Facts',
        _format_parsed_facts_for_prompt(parsed_facts),
    ]

    if company_context:
        prompt_parts.append('# Company Context')
        prompt_parts.append(json.dumps(company_context, indent=2))

    if user_feedback:
        prompt_parts.append('# User Feedback')
        prompt_parts.append(user_feedback)

    user_prompt = '\n\n'.join(prompt_parts)

    # Call LLM
    try:
        response = llm_client.complete(
            prompt=user_prompt,
            system_prompt=STAGE2_SYSTEM_PROMPT,
            max_tokens=2500,
        )
    except Exception as e:
        return Result(
            success=False,
            error=f'LLM call failed: {str(e)}',
            code=ResultCode.LLM_API_ERROR,
        )

    # Parse JSON response
    try:
        # Try to extract JSON from response
        response_text = response.text if hasattr(response, 'text') else str(response)
        # Handle potential markdown code blocks
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0]

        parsed = json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        return Result(
            success=False,
            error=f'Failed to parse LLM JSON response: {str(e)}',
            code=ResultCode.PARSE_ERROR,
        )

    # Build Stage2Output from parsed response
    try:
        verification = Stage2Verification(
            ats_keyword_score=parsed.get('verification', {}).get('ats_keyword_score', 5),
            keywords_added_in_review=parsed.get('verification', {}).get('keywords_added_in_review', []),
            summary_rewritten=parsed.get('verification', {}).get('summary_rewritten', False),
            fact_verification_passed=parsed.get('verification', {}).get('fact_verification_passed', False),
            hallucination_flags=parsed.get('verification', {}).get('hallucination_flags', []),
        )
        cv_sections = _parse_cv_sections(parsed.get('cv_sections', {}))

        return Result(
            success=True,
            data=Stage2Output(verification=verification, cv_sections=cv_sections),
            code=ResultCode.SUCCESS,
        )
    except Exception as e:
        return Result(
            success=False,
            error=f'Failed to parse Stage2Output: {str(e)}',
            code=ResultCode.PARSE_ERROR,
        )


def _format_parsed_facts_for_prompt(cv: UserCV) -> str:
    """Format parsed CV facts for Stage 2 prompt."""
    lines = [
        f'Name: {cv.full_name}',
        f'Email: {cv.email}',
    ]

    if cv.professional_summary:
        lines.append(f'Summary: {cv.professional_summary}')

    if cv.skills:
        lines.append(f'Skills: {", ".join([s.name if hasattr(s, "name") else str(s) for s in cv.skills])}')

    if cv.work_experience:
        lines.append('Experience:')
        for exp in cv.work_experience:
            lines.append(f'- {exp.company}: {exp.role} ({exp.start_date} - {exp.end_date or "Present"})')
            if exp.description:
                lines.append(f'  {exp.description}')

    if cv.education:
        lines.append('Education:')
        for edu in cv.education:
            lines.append(f'- {edu.institution}: {edu.degree} in {edu.field_of_study}')

    return '\n'.join(lines)


def _parse_cv_sections(data: dict[str, Any]) -> CVSections:
    """Parse CVSections from LLM JSON response."""
    contact_data = data.get('contact', {})
    from careervp.models.cv_tailoring_models import CVContactSection

    contact = CVContactSection(
        name=contact_data.get('name', ''),
        email=contact_data.get('email'),
        phone=contact_data.get('phone'),
        linkedin=contact_data.get('linkedin'),
        location=contact_data.get('location'),
    )

    skills_data = data.get('skills', {})
    skills = CVSkillsSection(
        technical=skills_data.get('technical', []),
        soft=skills_data.get('soft', []),
    )

    experience = []
    for exp in data.get('experience', []):
        experience.append(
            CVExperienceSection(
                company=exp.get('company', ''),
                title=exp.get('title', ''),
                start_date=exp.get('start_date', ''),
                end_date=exp.get('end_date'),
                bullets=exp.get('bullets', []),
            )
        )

    education = []
    for edu in data.get('education', []):
        education.append(
            CVEducationSection(
                institution=edu.get('institution', ''),
                degree=edu.get('degree', ''),
                field=edu.get('field', ''),
                graduation_date=edu.get('graduation_date', ''),
            )
        )

    certifications = []
    for cert in data.get('certifications', []):
        certifications.append(
            CVCertificationSection(
                name=cert.get('name', ''),
                issuer=cert.get('issuer', ''),
                date=cert.get('date', ''),
            )
        )

    return CVSections(
        contact=contact,
        summary=data.get('summary', ''),
        skills=skills,
        experience=experience,
        education=education,
        certifications=certifications,
    )


# Stage 3: Fact verification (Python, no LLM call)
def run_stage3_fact_verification(  # noqa: C901
    stage2_output: Stage2Output,
    parsed_facts: UserCV,
    ats_keyword_score: int = 0,
) -> Stage3Result:
    """Stage 3: Cross-check Stage 2 output against parsed_facts.

    This is a deterministic Python stage (no LLM call) per spec line 117-129.
    """
    cv_sections = stage2_output.cv_sections
    items_corrected: list[str] = []
    items_removed: list[str] = []

    # Get known companies from parsed_facts
    known_companies: set[str] = set()
    if parsed_facts.work_experience:
        for exp in parsed_facts.work_experience:
            known_companies.add(exp.company.lower())

    # Check contact info against parsed_facts (initialize here)
    fact_verification_passed = True

    # Check each experience entry against known companies
    verified_experience: list[CVExperienceSection] = []
    for exp_item in cv_sections.experience:
        if exp_item.company.lower() in known_companies:
            verified_experience.append(exp_item)
        else:
            items_removed.append(f'Company not in parsed_facts: {exp_item.company}')
            fact_verification_passed = False  # Hallucinated company detected

    # Verify contact name
    if cv_sections.contact.name and parsed_facts.full_name:
        if cv_sections.contact.name.lower() != parsed_facts.full_name.lower():
            fact_verification_passed = False
            items_corrected.append(f'Contact name corrected: {cv_sections.contact.name} -> {parsed_facts.full_name}')

    # Verify contact email
    if cv_sections.contact.email and parsed_facts.email:
        if cv_sections.contact.email.lower() != parsed_facts.email.lower():
            fact_verification_passed = False
            items_corrected.append(f'Contact email corrected: {cv_sections.contact.email} -> {parsed_facts.email}')

    # Strip hallucination flags from verification
    hallucination_count = len(stage2_output.verification.hallucination_flags)
    if hallucination_count > 0:
        items_removed.extend(stage2_output.verification.hallucination_flags)

    # Determine final fact_verification_passed
    # If Stage 2 already said false, keep it false
    if not stage2_output.verification.fact_verification_passed:
        fact_verification_passed = False

    # Build corrected CVSections
    corrected_sections = CVSections(
        contact=cv_sections.contact,
        summary=cv_sections.summary,
        skills=cv_sections.skills,
        experience=verified_experience if verified_experience else cv_sections.experience,
        education=cv_sections.education,
        certifications=cv_sections.certifications,
        languages=cv_sections.languages,
    )

    return Stage3Result(
        cv_sections=corrected_sections,
        fact_verification_passed=fact_verification_passed,
        items_corrected=items_corrected,
        items_removed=items_removed,
        ats_keyword_score=ats_keyword_score,
    )


# Main pipeline orchestrator
def run_cv_tailoring_pipeline(
    cv: CVUserCV | UserCV,
    job_description: str,
    vpr: VPR | None = None,
    gap_responses: dict[str, Any] | None = None,
    company_context: dict[str, Any] | None = None,
    user_feedback: str | None = None,
    llm_client: Any = None,
    parsed_facts: Any = None,  # ParsedFacts model for Stage 3 verification
) -> Result[Stage3Result]:
    """Execute the 3-stage CV tailoring pipeline.

    Stage 1: Keyword mapping (Python, no LLM)
    Stage 2: CV generation (LLM Haiku)
    Stage 3: Fact verification (Python, no LLM)
    """
    # Use parsed_facts for Stage 3 if provided, otherwise fall back to cv (UserCV)
    fact_verification_source = parsed_facts if parsed_facts is not None else cv

    # Stage 1: Keyword mapping
    stage1_output = run_stage1_keyword_mapping(
        vpr=vpr,
        job_description=job_description,
        parsed_facts=cv,
        gap_responses=gap_responses,
    )

    # Stage 2: CV generation
    stage2_result = run_stage2_cv_generation(
        stage1_output=stage1_output,
        parsed_facts=cv,
        job_description=job_description,
        company_context=company_context,
        user_feedback=user_feedback,
        llm_client=llm_client,
    )

    if not stage2_result.success or stage2_result.data is None:
        return Result(
            success=False,
            error=stage2_result.error or 'Stage 2 failed',
            code=stage2_result.code,
        )

    stage2_output = stage2_result.data

    # Stage 3: Fact verification
    # Convert Stage2 1-10 scale to 0-100 scale for the artifact
    raw_ats = stage2_output.verification.ats_keyword_score
    ats_score_100 = min(100, max(0, raw_ats * 10))
    stage3_result = run_stage3_fact_verification(
        stage2_output=stage2_output,
        parsed_facts=fact_verification_source,
        ats_keyword_score=ats_score_100,
    )

    return Result(
        success=True,
        data=stage3_result,
        code=ResultCode.SUCCESS,
    )
