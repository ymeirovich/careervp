"""Prompt construction utilities for CV tailoring."""

from __future__ import annotations

from typing import Iterable

from careervp.models.cv import Skill, UserCV
from careervp.models.cv_tailoring_models import TailoringPreferences
from careervp.models.fvs import FVSBaseline


def build_system_prompt() -> str:
    """Build the system prompt for the LLM."""
    return (
        'You are a CV tailoring assistant.\n'
        'Role: Optimize a candidate CV for a specific job description.\n'
        'Instructions:\n'
        '- Preserve IMMUTABLE facts (names, dates, companies, roles).\n'
        '- Do not change employment dates or factual details.\n'
        '- Focus on relevance and ATS-friendly wording.\n'
    )


def build_user_prompt(
    cv: UserCV,
    job_description: str,
    relevance_scores: dict[str, float] | None = None,
    fvs_baseline: FVSBaseline | None = None,
    target_keywords: Iterable[str] | None = None,
    preferences: TailoringPreferences | None = None,
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

    return '\n\n'.join(sections)


def format_cv_for_prompt(cv: UserCV) -> str:
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
        skills = [skill.name if isinstance(skill, Skill) else str(skill) for skill in cv.skills]
        lines.append('Skills: ' + ', '.join(skills))

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
    immutable = fvs_baseline.immutable_facts
    if isinstance(immutable, list):
        immutable_values = [fact.value for fact in immutable]
    else:
        immutable_values = []
        contact = immutable.contact_info
        if contact.name:
            immutable_values.append(f'Name: {contact.name}')
        if contact.email:
            immutable_values.append(f'Email: {contact.email}')
        if contact.phone:
            immutable_values.append(f'Phone: {contact.phone}')
        if contact.location:
            immutable_values.append(f'Location: {contact.location}')
        for exp in immutable.work_history:
            if exp.dates:
                immutable_values.append(f'{exp.company} | {exp.role} | {exp.dates}')
            else:
                immutable_values.append(f'{exp.company} | {exp.role}')
        for edu in immutable.education:
            immutable_values.append(f'{edu.institution} | {edu.degree}')
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
