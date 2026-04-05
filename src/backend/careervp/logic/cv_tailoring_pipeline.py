"""Three-stage CV tailoring pipeline for P2 spec.

Stage 1: Keyword mapping (Python, no LLM) — extracts from VPR + job description + parsed_facts
Stage 2: CV generation (LLM Haiku) — produces CVSections with verification block
Stage 3: Fact verification (Python) — cross-checks against parsed_facts, strips hallucinations
"""

from __future__ import annotations

import json
import logging
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

logger = logging.getLogger(__name__)


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
   Summary field specifically: 50-500 characters (2-3 sentences). Do not exceed 500 characters.
5. ATS formatting — no tables, no text boxes, no columns in the content
   structure. Simple flat sections only.
6. Anti-AI detection — vary sentence structure, use natural transitions,
   avoid "leverage", "delve", "robust", "streamline", "landscape",
   "spearhead" (overused). Use concrete verbs tied to actual work.
7. Self-correct before finalizing — explicitly check keyword match and
   summary alignment before producing output JSON.

REQUIRED JSON STRUCTURE — you MUST use exactly these top-level keys:
{
  "cv_sections": {
    "contact": {
      "name": "Full Name",
      "email": "email@example.com",
      "phone": "+1-555-0123",
      "location": "City, Country",
      "linkedin": "linkedin.com/in/..."
    },
    "summary": "Professional summary of 50-500 characters (2-3 sentences max)",
    "skills": {
      "technical": ["Skill1", "Skill2"],
      "soft": ["Skill1", "Skill2"]
    },
    "experience": [
      {
        "company": "Company Name",
        "title": "Job Title",
        "start_date": "MM/YYYY",
        "end_date": "MM/YYYY",
        "bullets": ["Achievement with metric", "Achievement 2"]
      }
    ],
    "education": [
      {
        "institution": "University Name",
        "degree": "Degree Type",
        "field": "Field of Study",
        "graduation_date": "MM/YYYY"
      }
    ],
    "certifications": []
  },
  "verification": {
    "ats_keyword_score": 8,
    "keywords_added_in_review": ["keyword1"],
    "summary_rewritten": false,
    "fact_verification_passed": true,
    "hallucination_flags": []
  }
}

Return ONLY valid JSON matching this exact structure. No preamble, no markdown, no explanation.
Do NOT use alternate key names such as cv_output, professional_summary, core_skills, or professional_experience."""


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
        verification_raw = parsed.get('verification', {})
        verification = Stage2Verification(
            ats_keyword_score=verification_raw.get('ats_keyword_score', 5),
            keywords_added_in_review=verification_raw.get('keywords_added_in_review', []),
            summary_rewritten=verification_raw.get('summary_rewritten', False),
            fact_verification_passed=verification_raw.get('fact_verification_passed', False),
            hallucination_flags=verification_raw.get('hallucination_flags', []),
        )
        cv_sections_raw = _normalize_cv_sections(parsed)
        cv_sections = _parse_cv_sections(cv_sections_raw)

        return Result(
            success=True,
            data=Stage2Output(verification=verification, cv_sections=cv_sections),
            code=ResultCode.SUCCESS,
        )
    except Exception as e:
        # Log the raw LLM response so the actual content is visible in CloudWatch
        logger.error(
            'Stage2 parse failed — raw LLM response follows',
            extra={'raw_response': response_text[:2000]},
        )
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


def _find_parsed_experience(
    company: str,
    title: str,
    parsed_facts: UserCV,
) -> Any | None:
    """Return the best-matching WorkExperience from parsed_facts.

    Tries exact company+role match first, then company-only.
    """
    if not parsed_facts.work_experience:
        return None
    company_lower = company.lower()
    title_lower = title.lower()
    # Exact match first
    for exp in parsed_facts.work_experience:
        if exp.company.lower() == company_lower and exp.role.lower() == title_lower:
            return exp
    # Company-only fallback
    for exp in parsed_facts.work_experience:
        if exp.company.lower() == company_lower:
            return exp
    return None


def _parse_dates_string(dates_str: str) -> tuple[str, str | None]:
    """Parse a freeform dates string into (start_date, end_date) in MM/YYYY format.

    Handles formats like:
    - "January 2020 - Present"
    - "2020 - 2023"
    - "01/2020 - 12/2023"
    - "Present"
    """
    import re

    if not dates_str:
        return '', None

    # Normalise dash variants (em dash, en dash)
    normalised = dates_str.replace('\u2014', '-').replace('\u2013', '-')

    # Split on ' - ' or just '-' with surrounding space
    parts = re.split(r'\s*[-]\s*', normalised, maxsplit=1)

    month_map = {
        'january': '01',
        'february': '02',
        'march': '03',
        'april': '04',
        'may': '05',
        'june': '06',
        'july': '07',
        'august': '08',
        'september': '09',
        'october': '10',
        'november': '11',
        'december': '12',
        'jan': '01',
        'feb': '02',
        'mar': '03',
        'apr': '04',
        'jun': '06',
        'jul': '07',
        'aug': '08',
        'sep': '09',
        'oct': '10',
        'nov': '11',
        'dec': '12',
    }

    def _single(s: str) -> str | None:
        s = s.strip()
        if not s or s.lower() == 'present':
            return None
        # Already MM/YYYY
        if re.match(r'^\d{2}/\d{4}$', s):
            return s
        # Month YYYY
        m = re.match(r'^([A-Za-z]+)\s+(\d{4})$', s)
        if m:
            mon = month_map.get(m.group(1).lower(), '01')
            return f'{mon}/{m.group(2)}'
        # YYYY only
        m2 = re.match(r'^(\d{4})$', s)
        if m2:
            return f'01/{m2.group(1)}'
        # Anything containing a 4-digit year
        yr = re.search(r'\d{4}', s)
        if yr:
            return f'01/{yr.group()}'
        return None

    start = _single(parts[0]) or ''
    end = _single(parts[1]) if len(parts) > 1 else None
    return start, end


def _normalize_cv_sections(parsed: dict[str, Any]) -> dict[str, Any]:
    """Return the cv_sections sub-dict regardless of the schema the LLM used.

    Handles three observed response shapes:
      1. {'cv_sections': {...}, 'verification': {...}}  — ideal / spec-compliant
      2. {'cv_output': {'header': ..., 'professional_summary': ..., ...}}  — alternate
      3. {'summary': ..., 'contact': ..., 'experience': [...]}  — unwrapped
    """
    # Shape 1 — ideal
    if 'cv_sections' in parsed:
        cv_sections_val: dict[str, Any] = parsed['cv_sections']
        return cv_sections_val

    # Shape 2 — cv_output wrapper with different field names
    if 'cv_output' in parsed:
        cv_out: dict[str, Any] = parsed['cv_output']
        header: dict[str, Any] = cv_out.get('header', {})

        raw_experience: list[dict[str, Any]] = cv_out.get('professional_experience', [])
        experience: list[dict[str, Any]] = []
        for exp in raw_experience:
            start, end = _parse_dates_string(str(exp.get('dates', '')))
            experience.append(
                {
                    'company': exp.get('company', ''),
                    'title': exp.get('position', exp.get('title', exp.get('role', ''))),
                    'start_date': start,
                    'end_date': end,
                    'bullets': exp.get('bullets', exp.get('responsibilities', [])),
                }
            )

        core_skills: list[str] = cv_out.get('core_skills', [])
        # core_skills may contain dicts if the LLM added categories
        technical_skills: list[str] = [s if isinstance(s, str) else str(s.get('name', s)) for s in core_skills]

        return {
            'contact': {
                'name': header.get('name', ''),
                'email': header.get('email', ''),
                'phone': header.get('phone', ''),
                'location': header.get('location', ''),
                'linkedin': header.get('linkedin', ''),
            },
            'summary': cv_out.get('professional_summary', cv_out.get('summary', '')),
            'skills': {
                'technical': technical_skills,
                'soft': cv_out.get('soft_skills', []),
            },
            'experience': experience,
            'education': cv_out.get('education', []),
            'certifications': cv_out.get('certifications', []),
        }

    # Shape 3 — unwrapped (the dict IS the cv_sections)
    if any(k in parsed for k in ('summary', 'contact', 'experience', 'skills')):
        return parsed

    # Unknown shape — return as-is, _parse_cv_sections will surface validation errors
    return parsed


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

    # Clamp summary to model constraints (50–1000 chars) at a word boundary
    summary_raw: str = data.get('summary', '')
    _SUMMARY_MAX = 1000
    if len(summary_raw) > _SUMMARY_MAX:
        truncated = summary_raw[:_SUMMARY_MAX]
        # Step back to the last complete word
        last_space = truncated.rfind(' ')
        summary_raw = truncated[:last_space].rstrip() if last_space > 50 else truncated[:_SUMMARY_MAX]
        logger.warning(
            'Stage2 summary truncated to fit CVSections.max_length=1000',
            extra={'original_length': len(data.get('summary', '')), 'truncated_length': len(summary_raw)},
        )

    return CVSections(
        contact=contact,
        summary=summary_raw,
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

    # Check each experience entry against known companies; backfill dates from parsed_facts
    verified_experience: list[CVExperienceSection] = []
    for exp_item in cv_sections.experience:
        if exp_item.company.lower() in known_companies:
            # Backfill dates if Stage 2 left them empty
            if not exp_item.start_date and parsed_facts.work_experience:
                pf_exp = _find_parsed_experience(exp_item.company, exp_item.title, parsed_facts)
                if pf_exp is not None:
                    start = getattr(pf_exp, 'start_date', '') or ''
                    if not start and getattr(pf_exp, 'dates', None):
                        start, _end = _parse_dates_string(str(pf_exp.dates))
                    end = exp_item.end_date
                    if end is None:
                        end_from_pf = getattr(pf_exp, 'end_date', None)
                        if not end_from_pf and getattr(pf_exp, 'dates', None):
                            _, end_from_pf = _parse_dates_string(str(pf_exp.dates))
                        end = end_from_pf
                    is_current = bool(getattr(pf_exp, 'current', False)) or end is None
                    exp_item = exp_item.model_copy(
                        update={
                            'start_date': start,
                            'end_date': end,
                            'is_current': is_current,
                        }
                    )
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

    # Enrich contact: backfill phone/location/linkedin from parsed_facts.contact_info
    ci = getattr(parsed_facts, 'contact_info', None)
    if ci is not None:
        updated_contact = corrected_sections.contact.model_copy(
            update={
                'phone': getattr(ci, 'phone', None) or corrected_sections.contact.phone or None,
                'location': getattr(ci, 'location', None) or corrected_sections.contact.location or None,
                'linkedin': getattr(ci, 'linkedin', None) or corrected_sections.contact.linkedin or None,
            }
        )
        corrected_sections = corrected_sections.model_copy(update={'contact': updated_contact})

    # Backfill certifications from parsed_facts when Stage 2 produced an empty list
    if not corrected_sections.certifications and getattr(parsed_facts, 'certifications', None):
        pf_certs: list[CVCertificationSection] = []
        for cert in parsed_facts.certifications:
            name = str(getattr(cert, 'name', '') or '')
            issuer = str(getattr(cert, 'issuer', '') or getattr(cert, 'issuing_organization', '') or '')
            date = str(getattr(cert, 'date', '') or getattr(cert, 'issue_date', '') or '')
            if name:
                pf_certs.append(CVCertificationSection(name=name, issuer=issuer, date=date))
        if pf_certs:
            corrected_sections = corrected_sections.model_copy(update={'certifications': pf_certs})

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

    # Carry Stage 1 keywords forward so the handler can run compute_ats_result
    stage3_result = stage3_result.model_copy(update={'keywords_to_emphasize': stage1_output.keywords_to_emphasize})

    return Result(
        success=True,
        data=stage3_result,
        code=ResultCode.SUCCESS,
    )
