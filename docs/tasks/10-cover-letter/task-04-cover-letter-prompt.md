# Task 10.4: Cover Letter Prompt Engineering

**Status:** Pending
**Spec Reference:** [docs/specs/cover-letter/COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md)
**Depends On:** Task 10.8 (Models)
**Blocking:** Task 10.3 (Logic)
**Complexity:** Medium
**Duration:** 2 hours
**Test File:** `tests/cover-letter/unit/test_cover_letter_prompt.py` (15-20 tests)

## Overview

Implement prompt engineering for cover letter generation, including system prompts with anti-AI detection patterns, user prompts with VPR context, and tone calibration for professional/enthusiastic/technical modes.

## Todo

### Prompt Implementation

- [ ] Create `src/backend/careervp/logic/prompts/cover_letter_prompt.py`
- [ ] Implement `build_system_prompt()` with tone and anti-AI guidelines
- [ ] Implement `build_user_prompt()` with VPR context injection
- [ ] Implement word count guidance (250-400 words)
- [ ] Add anti-AI detection patterns (sentence variation, natural transitions)
- [ ] Add FVS rules injection (company name, job title must match)

### Test Implementation

- [ ] Create `tests/cover-letter/unit/test_cover_letter_prompt.py`
- [ ] Test system prompt for each tone (professional, enthusiastic, technical)
- [ ] Test user prompt with VPR context
- [ ] Test user prompt with gap responses
- [ ] Test word count guidance
- [ ] Test FVS rules inclusion

---

## Codex Implementation Guide

### File Path

`src/backend/careervp/logic/prompts/cover_letter_prompt.py`

### Key Implementation

```python
"""
Prompt engineering for cover letter generation.

Builds system and user prompts with:
- Tone calibration (professional/enthusiastic/technical)
- Anti-AI detection patterns
- VPR context injection
- FVS rules for fact verification
"""

from typing import Optional
from careervp.models.cover_letter_models import CoverLetterPreferences


# Anti-AI detection guidelines
ANTI_AI_GUIDELINES = """
CRITICAL WRITING GUIDELINES (Anti-AI Detection):
1. VARY sentence structure - mix short punchy sentences with longer ones
2. USE natural transitions - avoid "Furthermore", "Moreover", "Additionally"
3. AVOID buzzwords - no "synergy", "leverage", "innovative solutions"
4. INCLUDE specific details - numbers, dates, project names where possible
5. WRITE conversationally - use contractions occasionally ("I'm", "I've")
6. START sentences differently - don't begin multiple sentences with "I"
7. USE active voice predominantly
8. AVOID lists in cover letters - use flowing paragraphs
"""

# Tone-specific guidelines
TONE_GUIDELINES = {
    "professional": """
TONE: Professional and confident
- Use formal language but remain approachable
- Emphasize expertise and proven track record
- Focus on results and achievements
- Maintain measured enthusiasm
- Example phrases: "demonstrated expertise", "proven ability", "track record of"
""",
    "enthusiastic": """
TONE: Enthusiastic and energetic
- Express genuine excitement about the opportunity
- Show passion for the industry/company
- Use dynamic, engaging language
- Balance energy with professionalism
- Example phrases: "excited to", "passionate about", "eager to contribute"
""",
    "technical": """
TONE: Technical and precise
- Lead with technical accomplishments
- Use industry-specific terminology appropriately
- Focus on systems, architectures, and methodologies
- Quantify technical achievements
- Example phrases: "architected", "implemented", "engineered", "optimized"
""",
}


def build_system_prompt(preferences: CoverLetterPreferences) -> str:
    """Build system prompt for cover letter generation.

    Args:
        preferences: User preferences including tone

    Returns:
        System prompt string
    """
    tone_guide = TONE_GUIDELINES.get(preferences.tone, TONE_GUIDELINES["professional"])
    word_count = preferences.word_count_target

    return f"""You are an expert cover letter writer helping job seekers craft compelling, personalized cover letters.

{ANTI_AI_GUIDELINES}

{tone_guide}

WORD COUNT: Target {word_count} words (acceptable range: {word_count - 50} to {word_count + 50})

STRUCTURE:
1. Opening paragraph: Hook + specific interest in THIS company/role
2. Body paragraph 1: Most relevant accomplishment with specific results
3. Body paragraph 2: Skills/experience alignment with job requirements
4. Closing paragraph: Call to action + appreciation

FVS RULES (CRITICAL - DO NOT VIOLATE):
- Company name MUST match exactly as provided
- Job title MUST match exactly as provided
- Do NOT invent company details, products, or initiatives
- Do NOT claim accomplishments not in the provided context

OUTPUT FORMAT:
- Return ONLY the cover letter text
- No salutation/greeting (will be added separately)
- No signature (will be added separately)
- No meta-commentary about the letter
"""


def build_user_prompt(
    context: dict,
    company_name: str,
    job_title: str,
    preferences: CoverLetterPreferences,
) -> str:
    """Build user prompt with VPR context.

    Args:
        context: Personalization context from VPR, CV, gap responses
        company_name: Target company name
        job_title: Target job title
        preferences: User preferences

    Returns:
        User prompt string
    """
    # Extract context components
    accomplishments = context.get("accomplishments", [])
    job_requirements = context.get("job_requirements", [])
    skills = context.get("skills", [])
    experience_highlights = context.get("experience_highlights", [])
    gap_responses = context.get("gap_responses", [])

    # Build accomplishments section
    accomplishments_text = ""
    if accomplishments:
        accomplishments_text = "KEY ACCOMPLISHMENTS (use 1-2 in letter):\n"
        for acc in accomplishments[:5]:  # Limit to top 5
            accomplishments_text += f"- {acc.get('text', '')}\n"

    # Build requirements section
    requirements_text = ""
    if job_requirements:
        requirements_text = "JOB REQUIREMENTS TO ADDRESS:\n"
        for req in job_requirements[:5]:
            requirements_text += f"- {req}\n"

    # Build skills section
    skills_text = ""
    if skills:
        skills_text = f"RELEVANT SKILLS: {', '.join(skills[:10])}\n"

    # Build gap responses section
    gap_text = ""
    if gap_responses:
        gap_text = "GAP ANALYSIS RESPONSES (incorporate where relevant):\n"
        for gr in gap_responses[:3]:
            gap_text += f"Q: {gr.get('question', '')}\nA: {gr.get('response', '')}\n\n"

    # Build emphasis areas if specified
    emphasis_text = ""
    if preferences.emphasis_areas:
        emphasis_text = f"EMPHASIS AREAS (prioritize these): {', '.join(preferences.emphasis_areas)}\n"

    return f"""Write a cover letter for the following position:

COMPANY: {company_name}
POSITION: {job_title}

{accomplishments_text}
{requirements_text}
{skills_text}
{emphasis_text}
{gap_text}

Remember:
- Target word count: {preferences.word_count_target} words
- Use SPECIFIC accomplishments from the list above
- Address the job requirements naturally
- Company name must be exactly: {company_name}
- Job title must be exactly: {job_title}
"""


def inject_fvs_rules(prompt: str, company_name: str, job_title: str) -> str:
    """Inject FVS verification rules into prompt.

    Args:
        prompt: Base prompt
        company_name: Company name that must match
        job_title: Job title that must match

    Returns:
        Prompt with FVS rules injected
    """
    fvs_rules = f"""
[FVS VERIFICATION - CRITICAL]
The following facts MUST appear exactly as written:
- Company: "{company_name}"
- Position: "{job_title}"
Any deviation will cause validation failure.
"""
    return prompt + fvs_rules
```

---

## Test Implementation

### test_cover_letter_prompt.py

```python
"""Unit tests for cover letter prompt engineering."""

import pytest
from careervp.logic.prompts.cover_letter_prompt import (
    build_system_prompt,
    build_user_prompt,
    inject_fvs_rules,
    ANTI_AI_GUIDELINES,
    TONE_GUIDELINES,
)
from careervp.models.cover_letter_models import CoverLetterPreferences


class TestBuildSystemPrompt:
    """Tests for system prompt building."""

    def test_system_prompt_professional_tone(self):
        """Test system prompt includes professional tone guidelines."""
        preferences = CoverLetterPreferences(tone="professional")
        prompt = build_system_prompt(preferences)

        assert "Professional and confident" in prompt
        assert "proven ability" in prompt

    def test_system_prompt_enthusiastic_tone(self):
        """Test system prompt includes enthusiastic tone guidelines."""
        preferences = CoverLetterPreferences(tone="enthusiastic")
        prompt = build_system_prompt(preferences)

        assert "Enthusiastic and energetic" in prompt
        assert "excited to" in prompt

    def test_system_prompt_technical_tone(self):
        """Test system prompt includes technical tone guidelines."""
        preferences = CoverLetterPreferences(tone="technical")
        prompt = build_system_prompt(preferences)

        assert "Technical and precise" in prompt
        assert "architected" in prompt

    def test_system_prompt_includes_anti_ai_guidelines(self):
        """Test system prompt includes anti-AI detection guidelines."""
        preferences = CoverLetterPreferences()
        prompt = build_system_prompt(preferences)

        assert "VARY sentence structure" in prompt
        assert "natural transitions" in prompt
        assert "AVOID buzzwords" in prompt

    def test_system_prompt_includes_word_count(self):
        """Test system prompt includes word count guidance."""
        preferences = CoverLetterPreferences(word_count_target=350)
        prompt = build_system_prompt(preferences)

        assert "350 words" in prompt
        assert "300 to 400" in prompt  # ±50 range

    def test_system_prompt_includes_fvs_rules(self):
        """Test system prompt includes FVS verification rules."""
        preferences = CoverLetterPreferences()
        prompt = build_system_prompt(preferences)

        assert "FVS RULES" in prompt
        assert "Company name MUST match" in prompt
        assert "Job title MUST match" in prompt

    def test_system_prompt_includes_structure(self):
        """Test system prompt includes letter structure guidance."""
        preferences = CoverLetterPreferences()
        prompt = build_system_prompt(preferences)

        assert "Opening paragraph" in prompt
        assert "Body paragraph" in prompt
        assert "Closing paragraph" in prompt


class TestBuildUserPrompt:
    """Tests for user prompt building."""

    def test_user_prompt_includes_company_and_title(self):
        """Test user prompt includes company name and job title."""
        context = {"accomplishments": [], "job_requirements": []}
        preferences = CoverLetterPreferences()

        prompt = build_user_prompt(
            context=context,
            company_name="TechCorp",
            job_title="Senior Engineer",
            preferences=preferences,
        )

        assert "COMPANY: TechCorp" in prompt
        assert "POSITION: Senior Engineer" in prompt

    def test_user_prompt_includes_accomplishments(self):
        """Test user prompt includes accomplishments from VPR."""
        context = {
            "accomplishments": [
                {"text": "Led team of 10 engineers"},
                {"text": "Reduced latency by 50%"},
            ],
            "job_requirements": [],
        }
        preferences = CoverLetterPreferences()

        prompt = build_user_prompt(
            context=context,
            company_name="TechCorp",
            job_title="Engineer",
            preferences=preferences,
        )

        assert "Led team of 10 engineers" in prompt
        assert "Reduced latency by 50%" in prompt

    def test_user_prompt_includes_job_requirements(self):
        """Test user prompt includes job requirements."""
        context = {
            "accomplishments": [],
            "job_requirements": ["Python", "AWS", "Leadership"],
        }
        preferences = CoverLetterPreferences()

        prompt = build_user_prompt(
            context=context,
            company_name="TechCorp",
            job_title="Engineer",
            preferences=preferences,
        )

        assert "Python" in prompt
        assert "AWS" in prompt
        assert "Leadership" in prompt

    def test_user_prompt_includes_gap_responses(self):
        """Test user prompt includes gap analysis responses."""
        context = {
            "accomplishments": [],
            "job_requirements": [],
            "gap_responses": [
                {"question": "Why this role?", "response": "Passion for AI"},
            ],
        }
        preferences = CoverLetterPreferences()

        prompt = build_user_prompt(
            context=context,
            company_name="TechCorp",
            job_title="Engineer",
            preferences=preferences,
        )

        assert "Why this role?" in prompt
        assert "Passion for AI" in prompt

    def test_user_prompt_includes_emphasis_areas(self):
        """Test user prompt includes emphasis areas from preferences."""
        context = {"accomplishments": [], "job_requirements": []}
        preferences = CoverLetterPreferences(
            emphasis_areas=["leadership", "python", "aws"]
        )

        prompt = build_user_prompt(
            context=context,
            company_name="TechCorp",
            job_title="Engineer",
            preferences=preferences,
        )

        assert "leadership" in prompt
        assert "python" in prompt


class TestInjectFvsRules:
    """Tests for FVS rules injection."""

    def test_inject_fvs_rules_adds_company(self):
        """Test FVS rules include company name."""
        prompt = "Base prompt"
        result = inject_fvs_rules(prompt, "TechCorp", "Engineer")

        assert 'Company: "TechCorp"' in result

    def test_inject_fvs_rules_adds_title(self):
        """Test FVS rules include job title."""
        prompt = "Base prompt"
        result = inject_fvs_rules(prompt, "TechCorp", "Senior Engineer")

        assert 'Position: "Senior Engineer"' in result

    def test_inject_fvs_rules_preserves_original(self):
        """Test FVS rules preserve original prompt."""
        prompt = "Original content here"
        result = inject_fvs_rules(prompt, "TechCorp", "Engineer")

        assert "Original content here" in result
```

---

## Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Format
uv run ruff format careervp/logic/prompts/cover_letter_prompt.py

# Lint
uv run ruff check --fix careervp/logic/prompts/

# Type check
uv run mypy careervp/logic/prompts/cover_letter_prompt.py --strict

# Run tests
uv run pytest tests/cover-letter/unit/test_cover_letter_prompt.py -v

# Expected: 16 tests PASSED
```

---

## Completion Criteria

- [ ] `build_system_prompt()` implemented with all tones
- [ ] `build_user_prompt()` implemented with context injection
- [ ] Anti-AI detection guidelines included
- [ ] FVS rules injection working
- [ ] All 16 tests passing
- [ ] ruff format passes
- [ ] mypy --strict passes

---

## Common Pitfalls

### Pitfall 1: Missing Tone in System Prompt
**Problem:** Default to wrong tone when invalid tone provided.
**Solution:** Use `TONE_GUIDELINES.get(tone, TONE_GUIDELINES["professional"])`.

### Pitfall 2: Not Limiting Context Size
**Problem:** Prompt too long with all accomplishments.
**Solution:** Limit to top 5 accomplishments, top 5 requirements.

---

## References

- [COVER_LETTER_DESIGN.md](../../architecture/COVER_LETTER_DESIGN.md) - Anti-AI detection patterns
- [cv_tailoring_prompt.py](../../../src/backend/careervp/logic/prompts/) - Pattern reference
