"""Cover Letter LLM prompts per COVER_LETTER_DESIGN.md:1301-1457."""

from __future__ import annotations

import json
from typing import Any

from careervp.models.cv import UserCV
from careervp.models.job import GapResponse
from careervp.models.vpr import VPRResponse


def build_system_prompt(tone: str, word_count_target: int) -> str:
    """Build system prompt for cover letter generation."""
    return (
        "You are a cover letter generation assistant.\n"
        "Produce a natural, human-sounding cover letter tailored to the role.\n"
        "Constraints:\n"
        f"- Tone: {tone}\n"
        f"- Target length: ~{word_count_target} words\n"
        "- Preserve factual accuracy (names, dates, roles, companies).\n"
        "- Avoid generic, AI-sounding language.\n"
    )


def build_user_prompt(
    cv: UserCV,
    vpr: VPRResponse,
    company_name: str,
    job_title: str,
    job_description: str,
    gap_responses: list[GapResponse] | None = None,
    emphasis_areas: list[str] | None = None,
) -> str:
    """Build user prompt for cover letter generation."""
    sections: list[str] = [
        "# Company",
        f"{company_name}",
        "# Role",
        f"{job_title}",
        "# Job Description",
        job_description.strip(),
        "# Candidate CV",
        json.dumps(cv.model_dump(mode="json"), indent=2),
        "# VPR Summary",
        json.dumps(vpr.model_dump(mode="json"), indent=2),
    ]

    if gap_responses:
        sections.append("# Gap Responses")
        sections.append(json.dumps([resp.model_dump(mode="json") for resp in gap_responses], indent=2))

    if emphasis_areas:
        sections.append("# Emphasis Areas")
        sections.append(", ".join(emphasis_areas))

    return "\n\n".join(sections)
