"""Prompt helpers for structuring company research content."""

from __future__ import annotations


def build_structure_system_prompt() -> str:
    """Return the canonical company research system prompt."""
    return 'You are CareerVP company research analyst. Extract structured insights faithfully.'


def build_structure_user_prompt(company_name: str, raw_text: str, context_hint: str) -> str:
    """Return the canonical company research user prompt."""
    return (
        f'Company Name: {company_name}\n'
        f'Source Context: {context_hint}\n\n'
        f'Extract structured company research from the following text. '
        f'Return JSON with keys overview (100-200 words), values (list), mission, strategic_priorities, recent_news, financial_summary.\n'
        f'Text:\n{raw_text}\n'
        'Return ONLY valid JSON.'
    )


__all__ = ['build_structure_system_prompt', 'build_structure_user_prompt']
