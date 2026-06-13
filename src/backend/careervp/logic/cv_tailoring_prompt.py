"""Prompt construction utilities for CV tailoring."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Iterable

from careervp.logic.prompts.vpr_prompt import build_vpr_digest
from careervp.models.company import CompanyResearchResult
from careervp.models.cv import UserCV as CVUserCV
from careervp.models.cv_models import UserCV
from careervp.models.cv_tailoring_models import TailoringPreferences
from careervp.models.fvs import FVSBaseline

if TYPE_CHECKING:
    from careervp.models.vpr import VPR


# P1: CVSections JSON output contract
CV_SECTIONS_SCHEMA = {
    'contact': {'name': 'string', 'email': 'string or null', 'phone': 'string or null', 'linkedin': 'string or null', 'location': 'string or null'},
    'summary': 'string (50-600 chars, 3-4 sentences, embedded keywords)',
    'skills': {'technical': ['string'], 'soft': ['string']},
    'experience': [
        {
            'company': 'string',
            'title': 'string',
            'start_date': 'MM/YYYY',
            'end_date': 'MM/YYYY or null',
            'is_current': 'boolean',
            'bullets': ['CAR format: Action + Context + Result with metrics'],
        }
    ],
    'education': [{'institution': 'string', 'degree': 'string', 'field': 'string', 'graduation_date': 'MM/YYYY', 'gpa': 'string or null'}],
    'certifications': [{'name': 'string', 'issuer': 'string', 'date': 'MM/YYYY'}],
}


def build_system_prompt() -> str:
    """Build the system prompt for the LLM.

    P1 spec: Returns structured CVSections JSON instead of free-form text.
    """
    return (
        'You are a CV tailoring assistant.\n'
        'Role: Generate a structured CV optimized for a specific job description.\n\n'
        'CRITICAL: Your response MUST be valid JSON matching this schema:\n'
        f'{json.dumps(CV_SECTIONS_SCHEMA, indent=2)}\n\n'
        'NON-NEGOTIABLE RULES:\n'
        '1. PRESERVE ALL FACTS: Never change names, dates, emails, phone numbers, company names.\n'
        '2. BULLET FORMAT: Use CAR format (Context + Action + Result with quantified metrics).\n'
        '3. NO HALLUCINATION: Only include skills/experience that exist in the source CV.\n'
        '4. KEYWORD PLACEMENT: Embed 5-7 primary job keywords naturally in summary and bullets.\n'
        '5. DATES FORMAT: Use MM/YYYY format, or "Present" for current role.\n'
        '6. SUMMARY: 3-4 sentences, opens with title + years experience.\n'
        '7. ATS OPTIMIZATION: Use standard section headers,_quantified metrics, relevant keywords.\n\n'
        'Before generating JSON, verify:\n'
        '- Contact info matches source CV exactly\n'
        '- All dates are accurate\n'
        '- Skills are from source CV only\n'
        '- Experience bullets are enhanced but factual.\n\n'
        'Respond with valid JSON only — no explanatory text.'
    )


def build_user_prompt(
    cv: CVUserCV | UserCV,
    job_description: str,
    relevance_scores: dict[str, float] | None = None,
    fvs_baseline: FVSBaseline | None = None,
    target_keywords: Iterable[str] | None = None,
    preferences: TailoringPreferences | None = None,
    vpr: 'VPR | None' = None,
    *,
    company_research: CompanyResearchResult | None = None,
) -> str:
    """Build the user prompt with CV, job description, and constraints."""
    sections = [
        '# Job Description',
        format_job_description(job_description),
        '# CV',
        format_cv_for_prompt(cv),
    ]

    if relevance_scores:
        sections.append('# Relevance Scores')
        sections.append(annotate_with_relevance_scores(sections[-2], relevance_scores))

    if fvs_baseline:
        sections.append('# FVS Constraints')
        sections.append(include_fvs_constraints(fvs_baseline))

    if target_keywords:
        sections.append('# Target Keywords')
        sections.append(include_keyword_targets(list(target_keywords)))

    if preferences:
        sections.append('# Preferences')
        sections.append(format_preferences(preferences))

    if company_research is not None:
        sections.append('# Company Signals')
        sections.append(_format_company_signals(company_research))

    # VPR strategic guide injection
    if vpr is not None:
        sections.append('# VPR Strategic Guide')
        sections.append(
            'Use this VPR digest to prioritize CV content. Expand bullet points for roles and '
            'skills that support the top_differentiators. Align the professional_summary '
            'with positioning_statement. Surface ats_keywords_primary into tailored bullet '
            'points naturally.\n\n' + json.dumps(build_vpr_digest(vpr), indent=2)
        )

    return '\n\n'.join(sections)


def format_cv_for_prompt(cv: CVUserCV | UserCV) -> str:
    """Format CV content for prompt consumption."""
    lines = [
        f'Name: {cv.full_name}',
        f'Email: {cv.email}',
        f'Phone: {cv.phone or ""}',
        f'Location: {cv.location or ""}',
    ]

    if cv.professional_summary:
        lines.append(f'Summary: {cv.professional_summary}')

    if cv.work_experience:
        lines.append('Experience:')
        for exp in cv.work_experience:
            lines.append(f'- {exp.company} | {exp.role} | {exp.start_date}-{exp.end_date}')
            if exp.description:
                lines.append(f'  {exp.description}')

    if cv.skills:
        skill_names = []
        for skill in cv.skills:
            if hasattr(skill, 'name'):
                skill_names.append(skill.name)
            else:
                skill_names.append(str(skill))
        lines.append('Skills: ' + ', '.join(skill_names))

    if cv.education:
        lines.append('Education:')
        for edu in cv.education:
            lines.append(f'- {edu.institution} | {edu.degree}')

    return '\n'.join(lines)


def format_job_description(job_description: str) -> str:
    """Format job description for prompt."""
    return job_description.strip()


def annotate_with_relevance_scores(cv_text: str, relevance_scores: dict[str, float]) -> str:
    """Annotate CV text with relevance scores."""
    lines = ['Relevance annotations:']
    for section, score in relevance_scores.items():
        percentage = int(score * 100)
        lines.append(f'- {section.replace("_", " ")}: {percentage}%')
    return '\n'.join(lines)


def include_fvs_constraints(fvs_baseline: FVSBaseline) -> str:
    """Format FVS immutable constraints."""
    immutable_values = [fact.value for fact in fvs_baseline.immutable_facts]
    return 'IMMUTABLE facts - must not change:\n' + '\n'.join(f'- {value}' for value in immutable_values)


def include_keyword_targets(target_keywords: list[str]) -> str:
    """Format target keyword list."""
    return 'Keywords: ' + ', '.join(target_keywords)


def format_preferences(preferences: TailoringPreferences) -> str:
    """Format tailoring preferences as instructions."""
    length = preferences.target_length or preferences.length or 'standard'
    lines = [f'Tone: {preferences.tone}', f'Length: {length.replace("_", " ")}']
    if preferences.emphasis_areas:
        lines.append('Emphasis Areas: ' + ', '.join(preferences.emphasis_areas))
    if preferences.emphasize_skills:
        lines.append('Emphasize Skills: ' + ', '.join(preferences.emphasize_skills))
    return '\n'.join(lines)


def _format_company_signals(company_research: CompanyResearchResult) -> str:
    values = ', '.join(company_research.values[:5]) or 'None'
    priorities = ', '.join(company_research.strategic_priorities[:3]) or 'None'
    return '\n'.join(
        [
            f'Values: {values}',
            f'Strategic Priorities: {priorities}',
        ]
    )


# P2: Stage 1 system prompt (verbatim from spec)
def build_stage1_system_prompt() -> str:
    """Build Stage 1 keyword mapping system prompt.

    Returns spec-verbatim prompt per AC-P2-09.
    """
    return """You are a senior technical recruiter and ATS optimization expert.
Your task is to analyze a job posting and a Value Proposition Report,
then create a precise keyword-to-evidence mapping plan for CV tailoring.

You must return ONLY valid JSON. No preamble, no markdown, no explanation.
The JSON structure is defined in the user message.

CRITICAL RULE: You may only reference skills, job titles, companies,
dates, and achievements that exist verbatim in the provided parsed_facts.
Do not invent, infer, or embellish any candidate information."""


# P2: Stage 2 system prompt (verbatim from spec)
def build_stage2_system_prompt() -> str:
    """Build Stage 2 CV generation system prompt.

    Returns spec-verbatim prompt with 7 non-negotiable rules per AC-P2-09.
    """
    return """You are an expert CV writer specializing in technical roles.
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
