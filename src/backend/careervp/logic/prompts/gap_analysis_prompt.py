"""Gap Analysis LLM prompts per GAP_ANALYSIS_DESIGN.md:371-467."""

from __future__ import annotations

import json
from typing import Any

from careervp.models.cv import UserCV
from careervp.models.job import JobPosting


def build_system_prompt() -> str:
    """Build system prompt for gap analysis."""
    return (
        'You are a career coach performing gap analysis.\n'
        'Generate 3-5 targeted questions to surface missing skills or experiences.\n'
        'Prioritize high-impact gaps and output JSON.\n'
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
