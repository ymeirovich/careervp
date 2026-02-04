# Task 04: Gap Analysis Prompts

## Overview

Create LLM prompts for gap analysis question generation.

**Files to create:**
- `src/backend/careervp/logic/prompts/gap_analysis_prompt.py`

**Dependencies:** None
**Estimated time:** 2 hours
**Unit Tests:** `tests/gap-analysis/unit/test_gap_prompt.py`

---

## Implementation

### File: `src/backend/careervp/logic/prompts/gap_analysis_prompt.py`

```python
"""
Gap analysis prompts for Claude API.
Per docs/architecture/GAP_ANALYSIS_DESIGN.md.
"""

from careervp.models.cv import UserCV, WorkExperience, Education
from careervp.models.job import JobPosting


def create_gap_analysis_system_prompt() -> str:
    """
    System prompt for gap analysis.

    Returns:
        System prompt string instructing LLM behavior
    """
    return """You are a career coach specializing in identifying skill and experience gaps between candidates and job requirements. Your goal is to help candidates articulate hidden strengths that may not be obvious from their CV.

**Guidelines:**
1. Generate 3-5 targeted questions that help the candidate showcase relevant experience
2. Focus on gaps where the candidate LIKELY has experience but hasn't explicitly stated it
3. Prioritize high-impact requirements (technical skills, key qualifications)
4. Make questions specific and actionable (include company names, role titles from CV)
5. Avoid questions about obviously missing qualifications (e.g., if CV shows 2 years experience, don't ask about 10 years)

**Question Format:**
- Start with context from their CV (e.g., "You worked as X at Y...")
- Ask specifically about the missing requirement
- Keep questions concise (1-2 sentences)
- Make answers easy to provide (2-3 sentence responses)

**Output Format:** JSON array of objects with:
- question_id: Unique identifier (use UUID format)
- question: The question text
- impact: "HIGH" | "MEDIUM" | "LOW" - How critical is this gap?
- probability: "HIGH" | "MEDIUM" | "LOW" - Likelihood user has this experience

Example:
[
  {
    "question_id": "550e8400-e29b-41d4-a716-446655440000",
    "question": "You worked as a Cloud Engineer at Tech Corp. Can you describe your hands-on experience with AWS services, particularly EC2, S3, and Lambda?",
    "impact": "HIGH",
    "probability": "HIGH"
  }
]"""


def create_gap_analysis_user_prompt(
    user_cv: UserCV,
    job_posting: JobPosting
) -> str:
    """
    User prompt with CV and job posting context.

    Args:
        user_cv: Parsed user CV
        job_posting: Target job posting

    Returns:
        User prompt string with formatted CV and job data
    """
    prompt = f"""Analyze the gap between this candidate's CV and the target job requirements.

**Candidate CV:**
Name: {user_cv.personal_info.full_name}

Work Experience:
{_format_work_experience(user_cv.work_experience)}

Skills: {', '.join(user_cv.skills) if user_cv.skills else 'None listed'}

Education:
{_format_education(user_cv.education)}

**Target Job:**
Company: {job_posting.company_name}
Role: {job_posting.role_title}

{f"Description: {job_posting.description}" if job_posting.description else ""}

Requirements:
{_format_requirements(job_posting.requirements)}

Responsibilities:
{_format_responsibilities(job_posting.responsibilities)}

{f"Nice to Have:\\n{_format_nice_to_have(job_posting.nice_to_have)}" if job_posting.nice_to_have else ""}

**Task:**
Identify 3-5 high-value gaps where the candidate likely has relevant experience but hasn't explicitly stated it. Generate targeted questions to help them articulate this experience.

Focus on:
1. Technical skills mentioned in requirements but not in CV
2. Experience depth for responsibilities that align with their roles
3. Transferable skills from their background

Return JSON array with question_id, question, impact, and probability for each."""

    return prompt


def _format_work_experience(work_experience: list[WorkExperience]) -> str:
    """Format work experience for prompt."""
    if not work_experience:
        return "No work experience listed"

    lines = []
    for exp in work_experience:
        lines.append(f"- {exp.role} at {exp.company} ({exp.start_date} to {exp.end_date or 'Present'})")
        if exp.responsibilities:
            for resp in exp.responsibilities[:3]:  # Top 3 responsibilities
                lines.append(f"  • {resp}")
    return "\n".join(lines)


def _format_education(education: list[Education]) -> str:
    """Format education for prompt."""
    if not education:
        return "No education listed"

    lines = []
    for edu in education:
        degree_field = f"{edu.degree} in {edu.field}" if edu.field else edu.degree
        lines.append(f"- {degree_field} from {edu.institution} ({edu.graduation_year})")
    return "\n".join(lines)


def _format_requirements(requirements: list[str]) -> str:
    """Format job requirements for prompt."""
    if not requirements:
        return "No specific requirements listed"

    return "\n".join(f"- {req}" for req in requirements)


def _format_responsibilities(responsibilities: list[str]) -> str:
    """Format job responsibilities for prompt."""
    if not responsibilities:
        return "No specific responsibilities listed"

    return "\n".join(f"- {resp}" for resp in responsibilities)


def _format_nice_to_have(nice_to_have: list[str]) -> str:
    """Format nice-to-have qualifications for prompt."""
    return "\n".join(f"- {item}" for item in nice_to_have)
```

---

## Verification Commands

```bash
cd src/backend

# Format
uv run ruff format careervp/logic/prompts/gap_analysis_prompt.py

# Lint
uv run ruff check careervp/logic/prompts/gap_analysis_prompt.py --fix

# Type check
uv run mypy careervp/logic/prompts/gap_analysis_prompt.py --strict

# Unit tests
uv run pytest tests/gap-analysis/unit/test_gap_prompt.py -v

# Expected: All tests pass
```

---

## Acceptance Criteria

- [ ] `create_gap_analysis_system_prompt()` returns career coach prompt
- [ ] System prompt specifies 3-5 questions
- [ ] System prompt includes JSON output format
- [ ] `create_gap_analysis_user_prompt()` formats CV and job posting
- [ ] User prompt includes name, work experience, skills, education
- [ ] User prompt includes job company, role, requirements
- [ ] Formatting helpers implemented
- [ ] Prompt length reasonable (<40K characters)
- [ ] All unit tests pass
- [ ] Type checking passes

---

## Commit Message

```bash
git add src/backend/careervp/logic/prompts/gap_analysis_prompt.py
git commit -m "feat(gap-analysis): add LLM prompts for question generation

- Add create_gap_analysis_system_prompt() (career coach instructions)
- Add create_gap_analysis_user_prompt() (CV + job formatting)
- Add formatting helpers for work experience, education, requirements
- All prompt tests pass (15/15)

Per docs/architecture/GAP_ANALYSIS_DESIGN.md.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```
