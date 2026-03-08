"""Gap Analysis LLM prompts per GAP_ANALYSIS_DESIGN.md:371-467."""

from __future__ import annotations

import json
from typing import Any

from careervp.models.cv import UserCV
from careervp.models.job import JobPosting


def build_system_prompt() -> str:
    """Build system prompt for gap analysis."""
    return (
        'You are a career coach performing gap analysis for job applications.\n'
        'Generate exactly 10 context-aware questions that expose missing evidence between CV and job requirements.\n'
        'Emphasize quantification for CV-ready outcomes (metrics, ownership scope, business impact).\n'
        'Use only these tags in a tags array per question: [CV IMPACT], [TECHNICAL], [BEHAVIORAL], [INTERVIEW/MVP ONLY].\n'
        'Target distribution across the 10 questions: 4 [CV IMPACT], 2 [TECHNICAL], 2 [BEHAVIORAL], 2 [INTERVIEW/MVP ONLY].\n'
        'Do not generate generic placeholders; each question must map to a concrete job requirement.\n'
        'Output valid JSON only with this shape: {"questions":[...]}\n'
        'Each JSON question must include: question_id, question, requirement, strategic_intent, evidence_gap, '
        'priority, destination, impact, probability, tags.\n'
        'priority must be one of CRITICAL, IMPORTANT, OPTIONAL.\n'
        'destination must be one of CV IMPACT or INTERVIEW/MVP ONLY.\n'
        'impact/probability must be one of HIGH, MEDIUM, LOW.\n'
    )


def build_user_prompt(user_cv: UserCV, job_posting: JobPosting) -> str:
    """Build user prompt for gap analysis."""
    sections = [
        '# Job Posting',
        json.dumps(job_posting.model_dump(mode='json'), indent=2),
        '# Candidate CV',
        json.dumps(user_cv.model_dump(mode='json'), indent=2),
    ]
    return '\n\n'.join(sections)


def create_gap_analysis_system_prompt() -> str:
    """Compatibility wrapper for tests expecting legacy function name."""
    return build_system_prompt()


def create_gap_analysis_user_prompt(user_cv: dict[str, Any], job_posting: dict[str, Any]) -> str:
    """Build a human-readable prompt from raw dict inputs (test harness)."""
    personal = user_cv.get('personal_info', {})
    full_name = personal.get('full_name', 'Unknown Candidate')
    work_experience = user_cv.get('work_experience', [])
    skills = user_cv.get('skills', [])
    education = user_cv.get('education', [])
    recurring_themes = job_posting.get('recurring_themes', [])
    company_research = job_posting.get('company_research')
    previous_gap_responses = job_posting.get('previous_gap_responses', [])

    sections = [
        '# Candidate CV',
        f'Name: {full_name}',
        '## Work Experience',
    ]
    sections.append(_format_work_experience(work_experience))

    sections.append('## Skills')
    if skills:
        sections.append(', '.join(skills))

    sections.append('## Education')
    sections.append(_format_education(education))

    sections.extend(
        [
            '# Target Job',
            f'Company: {job_posting.get("company_name", "")}',
            f'Role: {job_posting.get("role_title", "")}',
            '## Requirements',
            _format_requirements(job_posting.get('requirements', [])),
            '## Responsibilities',
            _format_responsibilities(job_posting.get('responsibilities', [])),
        ]
    )

    if recurring_themes:
        sections.extend(
            [
                '# Recurring Themes To Avoid Repeating',
                _format_string_list(recurring_themes),
            ]
        )

    if isinstance(company_research, dict) and company_research:
        sections.extend(
            [
                '# Company Research Context',
                json.dumps(company_research, indent=2),
            ]
        )

    if previous_gap_responses:
        sections.extend(
            [
                '# Previous Gap Responses Context',
                _format_json_list(previous_gap_responses),
            ]
        )

    sections.extend(
        [
            '# Output Requirements',
            '- Focus on missing evidence, not covered strengths.',
            '- Make [CV IMPACT] questions quantifiable and resume-ready.',
            '- Include requirement, strategic_intent, evidence_gap, priority, and destination for each question.',
        ]
    )

    return '\n'.join(sections)


def _format_work_experience(work_experience: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for exp in work_experience:
        company = exp.get('company', '')
        role = exp.get('role', '')
        start_date = exp.get('start_date', '')
        end_date = exp.get('end_date', '')
        dates = f'{start_date} - {end_date}'.strip(' -')
        header = f'- {company} | {role}'
        if dates:
            header = f'{header} | {dates}'
        lines.append(header)
        for resp in exp.get('responsibilities', []):
            lines.append(f'  * {resp}')
    return '\n'.join(lines)


def _format_requirements(requirements: list[str]) -> str:
    return '\n'.join(f'- {req}' for req in requirements)


def _format_responsibilities(responsibilities: list[str]) -> str:
    return '\n'.join(f'- {resp}' for resp in responsibilities)


def _format_education(education: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for edu in education:
        institution = edu.get('institution', '')
        degree = edu.get('degree', '')
        field = edu.get('field', '')
        details = ' | '.join(part for part in [institution, degree, field] if part)
        lines.append(f'- {details}')
    return '\n'.join(lines)


def _format_string_list(values: list[Any]) -> str:
    lines = [f'- {str(value).strip()}' for value in values if str(value).strip()]
    return '\n'.join(lines)


def _format_json_list(values: list[Any]) -> str:
    lines: list[str] = []
    for value in values:
        if isinstance(value, dict):
            lines.append(f'- {json.dumps(value, ensure_ascii=True)}')
        elif isinstance(value, str) and value.strip():
            lines.append(f'- {value.strip()}')
    return '\n'.join(lines)
