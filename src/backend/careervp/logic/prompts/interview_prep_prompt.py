"""Interview Preparation LLM prompts."""

from __future__ import annotations

import json
from typing import Any


def build_system_prompt() -> str:
    """Build system prompt for interview preparation generation."""
    return (
        'You are an expert interview coach.\n'
        'Generate personalized interview questions and STAR-method answers.\n'
        'Output valid JSON with this structure:\n'
        '{\n'
        '  "questions": [\n'
        '    {\n'
        '      "question_id": "q1",\n'
        '      "question": "...",\n'
        '      "question_type": "behavioral|technical|situational|gap_focused",\n'
        '      "difficulty": "easy|medium|hard",\n'
        '      "suggested_answer": {\n'
        '        "situation": "...",\n'
        '        "task": "...",\n'
        '        "action": "...",\n'
        '        "result": "...",\n'
        '        "full_text": "..."\n'
        '      },\n'
        '      "why_asked": "...",\n'
        '      "tips": ["..."]\n'
        '    }\n'
        '  ],\n'
        '  "questions_to_ask": [\n'
        '    {"question": "...", "purpose": "..."}\n'
        '  ],\n'
        '  "salary_guidance": "...",\n'
        '  "pre_interview_checklist": ["..."]\n'
        '}\n\n'
        'Rules:\n'
        '- Generate diverse question types (behavioral, technical, situational, gap_focused)\n'
        '- Max 4 questions per type\n'
        '- STAR answers: 150-300 words each\n'
        '- Base answers on actual CV facts provided in the prompt\n'
        '- Address identified gaps with positive framing\n'
        '- Generate 5-7 questions for the candidate to ask\n'
        '- Include salary negotiation guidance\n'
        '- Include pre-interview checklist\n'
        '- Ground all answers in the candidate CV facts and job requirements provided\n'
    )


def build_user_prompt(
    vpr_data: dict[str, Any],
    gap_responses: list[dict[str, Any]] | None = None,
    job_title: str = '',
    company_name: str = '',
    focus_areas: list[str] | None = None,
    question_count: int = 10,
    # Architecture section 3.7 required context inputs
    cv_facts: dict[str, Any] | None = None,
    job_requirements: dict[str, Any] | None = None,
    vpr_differentiators: list[str] | None = None,
    company_research: dict[str, Any] | None = None,
    language: str = 'en',
) -> str:
    """Build user prompt for interview prep generation.

    Includes all architecture-required sections (section 3.7):
    cv_facts, job_requirements, vpr_differentiators, gap_responses,
    company_research, language.
    """
    sections: list[str] = []

    if language and language != 'en':
        sections.append(f'# Language\nRespond in language code: {language}')

    if job_title:
        sections.append(f'# Role\n{job_title}')
    if company_name:
        sections.append(f'# Company\n{company_name}')

    # CV Facts — architecture-required input (section 3.7)
    if cv_facts:
        sections.append('# CV Facts\n' + json.dumps(cv_facts, indent=2, default=str))

    # Job Requirements — architecture-required input (section 3.7)
    if job_requirements:
        sections.append('# Job Requirements\n' + json.dumps(job_requirements, indent=2, default=str))

    # VPR Differentiators — architecture-required input (section 3.7)
    if vpr_differentiators:
        sections.append('# VPR Differentiators\n' + '\n'.join(f'- {d}' for d in vpr_differentiators))

    # VPR Summary (full VPR data)
    sections.append('# VPR Summary\n' + json.dumps(vpr_data, indent=2, default=str))

    # Gap Responses — architecture-required input (section 3.7)
    if gap_responses:
        sections.append('# Gap Responses\n' + json.dumps(gap_responses, indent=2, default=str))

    # Company Research — architecture-required input (section 3.7)
    if company_research:
        sections.append('# Company Research\n' + json.dumps(company_research, indent=2, default=str))

    if focus_areas:
        sections.append('# Focus Areas\n' + ', '.join(focus_areas))

    sections.append(f'# Target\nGenerate {question_count} questions grounded in the CV facts and job context above.')

    return '\n\n'.join(sections)
