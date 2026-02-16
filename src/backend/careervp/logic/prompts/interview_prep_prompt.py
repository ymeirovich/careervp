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
        '- Base answers on actual CV facts\n'
        '- Address identified gaps with positive framing\n'
        '- Generate 5-7 questions for the candidate to ask\n'
        '- Include salary negotiation guidance\n'
        '- Include pre-interview checklist\n'
    )


def build_user_prompt(
    vpr_data: dict[str, Any],
    gap_responses: list[dict[str, Any]] | None = None,
    job_title: str = '',
    company_name: str = '',
    focus_areas: list[str] | None = None,
    question_count: int = 5,
) -> str:
    """Build user prompt for interview prep generation."""
    sections: list[str] = [
        '# VPR Summary',
        json.dumps(vpr_data, indent=2, default=str),
    ]

    if job_title:
        sections.insert(0, f'# Role: {job_title}')
    if company_name:
        sections.insert(1, f'# Company: {company_name}')

    if gap_responses:
        sections.append('# Gap Responses')
        sections.append(json.dumps(gap_responses, indent=2, default=str))

    if focus_areas:
        sections.append('# Focus Areas')
        sections.append(', '.join(focus_areas))

    sections.append(f'# Target: Generate {question_count} questions')

    return '\n\n'.join(sections)
