# Task 9.4: CV Tailoring - LLM Prompt Engineering

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Task 9.1 (Validation)
**Blocking:** Task 9.3 (Tailoring Logic)

## Overview

Implement LLM prompt engineering for CV tailoring using Claude Haiku 4.5. This includes system prompts with anti-AI-detection rules, few-shot examples demonstrating correct tailoring, and dynamic prompt construction that incorporates FVS rules and relevance scoring.

## Todo

### Prompt Implementation

- [ ] Create `src/backend/careervp/logic/prompts/cv_tailor_prompt.py`
- [ ] Implement `CV_TAILOR_SYSTEM_PROMPT` with anti-detection rules
- [ ] Implement `CV_TAILOR_FEW_SHOT_EXAMPLES` (3-5 examples)
- [ ] Implement `build_tailor_prompt()` for dynamic construction
- [ ] Implement `ANTI_DETECTION_RULES` constant (8 patterns)
- [ ] Implement style preference integration
- [ ] Implement gap analysis integration (Phase 11)

### Test Implementation

- [ ] Create `tests/logic/prompts/test_tailoring_prompt.py`
- [ ] Implement 15-20 test cases covering all prompt functions
- [ ] Test system prompt presence and rules
- [ ] Test few-shot example quality
- [ ] Test dynamic prompt construction
- [ ] Test style preference injection
- [ ] Test edge cases and error handling

### Validation & Formatting

- [ ] Run `uv run ruff format src/backend/careervp/logic/prompts/`
- [ ] Run `uv run ruff check --fix src/backend/careervp/logic/prompts/`
- [ ] Run `uv run mypy src/backend/careervp/logic/prompts/ --strict`
- [ ] Run `uv run pytest tests/logic/prompts/test_tailoring_prompt.py -v`

### Commit

- [ ] Commit with message: `feat(prompts): implement CV tailoring prompt engineering with anti-detection`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/logic/prompts/cv_tailor_prompt.py` | Prompt templates and builders |
| `tests/logic/prompts/test_tailoring_prompt.py` | Prompt validation tests |

### Key Implementation Details

```python
"""
CV Tailoring Prompt Engineering.
Per docs/specs/04-cv-tailoring.md Prompt Strategy section.

Implements few-shot prompting for Haiku 4.5 with:
- System prompt with anti-detection rules
- 3-5 few-shot examples showing correct tailoring
- Dynamic prompt construction from input data
- FVS tier preservation rules
- Style preference integration

All content must:
1. Avoid AI clichés and patterns
2. Preserve IMMUTABLE facts exactly
3. Only reframe FLEXIBLE content
4. Maintain user's authentic voice
5. Include domain terminology naturally
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from careervp.models.tailor import StylePreferences


# 8-Pattern Anti-Detection Framework
# Per docs/specs/04-cv-tailoring.md Decision 1.6
ANTI_DETECTION_RULES = """
ANTI-DETECTION REQUIREMENTS (Apply to ALL generated content):

1. AVOID AI CLICHÉS
   Never use: "leverage", "utilize", "spearheaded", "synergy", 
   "cutting-edge", "passionate about", "proven track record", "drive"
   Instead: Use specific, concrete verbs from the CV itself

2. VARY SENTENCE LENGTH
   Mix short sentences (8 words or less) with longer ones (20+ words)
   Example: "Managed deployments. Also coordinated infrastructure improvements across three regional data centers."

3. INCLUDE IMPERFECTIONS
   Add one minor stylistic variation per section
   Example: Starting a bullet with "Also" or using a dash: "Worked on—and improved—the CI/CD pipeline"

4. AVOID PERFECT PARALLELISM
   Bullet points should NOT all follow the same grammatical pattern
   Wrong: "Managed team", "Managed budget", "Managed projects"
   Right: "Managed team of 5", "Budget responsibility of $2M", "Also oversaw project delivery"

5. CONVERSATIONAL TONE
   Match the candidate's experience level
   Junior: "Helped implement", "Learned to use"
   Senior: "Architected", "Drove adoption of"
   Don't change tone levels within the same bullet

6. USE DOMAIN TERMINOLOGY
   Naturally incorporate jargon from the job posting
   Include context around technical terms
   Example: "Optimized query performance using database indexing strategies"

7. USE CONTRACTIONS
   Write "I've managed" not "I have managed" where it sounds natural
   Write "team's performance" not "team performance"
   Use ~20-30% contractions to sound human

8. MIRROR USER STYLE
   If source CV uses certain phrases or patterns, maintain them
   If candidate says "Developed", keep "Developed" (not "Created")
   Preserve casual language if present in source
"""

CV_TAILOR_SYSTEM_PROMPT = f"""You are a professional CV optimization specialist. Your task is to tailor a candidate's CV to match a specific job description while maintaining COMPLETE FACTUAL ACCURACY.

CRITICAL CONSTRAINTS - VIOLATION MEANS FAILURE:
- NEVER fabricate dates, job titles, company names, degrees, or certifications
- NEVER add skills, tools, or technologies not mentioned in the source CV
- NEVER invent metrics or achievements not evidenced in the source
- ONLY reframe and rephrase existing content to match job requirements
- PRESERVE the candidate's authentic voice and experience level

FVS TIER CLASSIFICATION (MANDATORY):
- IMMUTABLE: Cannot be altered (dates, titles, company names, degrees, certifications)
  Action: Copy exactly as-is from source CV
  
- VERIFIABLE: Must exist in source CV (skills, tools, technologies, certifications)
  Action: Copy, reorder by relevance, highlight in context
  
- FLEXIBLE: Can be creatively reframed (summaries, bullet descriptions, achievement framing)
  Action: Rephrase to match job requirements, add context, optimize language

{ANTI_DETECTION_RULES}

OUTPUT REQUIREMENTS:
- Return VALID JSON only - no markdown, no explanations, no prose
- Include original_bullets in each work experience for FVS comparison
- Set relevance_score (0.0-1.0) for each skill based on job match
- List keyword_alignments for each work experience showing matched JD terms
- Ensure all work experience preserves company_name, job_title, dates exactly
- Match the style preferences if provided

BEFORE GENERATING OUTPUT:
1. Carefully read the source CV
2. Identify IMMUTABLE vs FLEXIBLE content
3. Extract keywords from job description
4. Map CV achievements to job requirements
5. Reframe only FLEXIBLE content, preserve IMMUTABLE facts exactly
6. Apply anti-detection rules to generated content
7. Verify no skills/certifications invented
8. Verify no dates altered
"""

CV_TAILOR_FEW_SHOT_EXAMPLES = """
EXAMPLE 1: Software Engineer → Senior Backend Role

SOURCE CV:
- Job Title: Software Engineer
- Company: StartupXYZ
- Duration: Jan 2020 - Present
- Bullets:
  * "Built REST APIs using Python and Flask for internal tools"
  * "Worked on performance optimization"
  * "Collaborated with product team"

TARGET JOB REQUIREMENTS:
- "Design and implement scalable microservices architecture"
- "Lead backend infrastructure improvements"
- "Experience with distributed systems"

TAILORED OUTPUT:
- Job Title: Software Engineer (IMMUTABLE - preserved exactly)
- Company: StartupXYZ (IMMUTABLE - preserved exactly)
- Duration: Jan 2020 - Present (IMMUTABLE - preserved exactly)
- Bullets:
  * "Developed RESTful microservices in Python/Flask that supported internal tooling across 3 teams" (Added scope context from "internal tools")
  * "Optimized API performance, reducing response latency by ensuring efficient resource utilization" (Reframed performance work without fabricating metrics)
  * "Partnered with product to align backend improvements with roadmap priorities" (Reframed collaboration with relevance)

WHY THIS WORKS:
✓ Python, Flask, REST APIs - all from source
✓ "Built" → "Developed" - natural language variation
✓ Added team context - plausible based on "internal tools"
✓ Performance reframed without specific metrics
✓ Maintained authentic voice (no "leveraged" or "synergy")
✓ Varied sentence structure and length
✓ No hallucinated technologies or skills
✗ Did NOT say: "Architected microservices" - would be hallucination
✗ Did NOT say: "Led distributed systems work" - not in source CV

---

EXAMPLE 2: Marketing Manager → Product Marketing Role

SOURCE CV:
- Job Title: Marketing Manager
- Company: MediaCorp
- Duration: Jun 2019 - Dec 2023
- Bullets:
  * "Managed social media accounts for 4 brands"
  * "Created monthly content calendars"
  * "Analyzed campaign metrics and reported to leadership"

TARGET JOB REQUIREMENTS:
- "Develop and execute go-to-market strategies"
- "Drive product positioning messaging"
- "Measure and optimize campaign performance"

TAILORED OUTPUT:
- Job Title: Marketing Manager (IMMUTABLE)
- Company: MediaCorp (IMMUTABLE)
- Duration: Jun 2019 - Dec 2023 (IMMUTABLE)
- Bullets:
  * "Developed content strategies for multiple brands, aligning messaging with product launch timelines"
  * "Created and executed monthly content calendars, measuring engagement and adjusting strategy based on performance"
  * "Analyzed campaign metrics monthly, presenting insights to leadership to inform marketing strategy refinements"

WHY THIS WORKS:
✓ Content creation and strategy - from source
✓ Metrics analysis - from source
✓ Connected to product without claiming PMM experience
✓ Maintained Manager title (not promoted)
✓ Natural, conversational language
✗ Did NOT say: "Led go-to-market strategy" - not in source
✗ Did NOT say: "Drove product positioning" - would need PMM experience
✗ Did NOT claim: "Launched products" - no evidence

---

EXAMPLE 3: Data Analyst → Business Intelligence Role

SOURCE CV:
- Job Title: Data Analyst
- Company: RetailCo
- Duration: Mar 2021 - Present
- Bullets:
  * "Created weekly reports in Excel for sales team"
  * "Used SQL to query database"
  * "Presented findings to stakeholders"

TARGET JOB REQUIREMENTS:
- "Build dashboards and automate reporting"
- "SQL expertise required"
- "Data visualization and BI tools experience"

TAILORED OUTPUT:
- Job Title: Data Analyst (IMMUTABLE)
- Company: RetailCo (IMMUTABLE)
- Duration: Mar 2021 - Present (IMMUTABLE)
- Bullets:
  * "Created weekly sales performance reports using SQL queries and Excel, streamlining data delivery to stakeholders"
  * "Queried and analyzed sales databases to identify trends, presenting findings to leadership for strategic decision-making"
  * "Built automated report generation processes to reduce manual effort and improve reporting consistency"

WHY THIS WORKS:
✓ SQL and reporting - from source
✓ Excel - from source
✓ "Automated" - implied by "created reports" (not a hallucination, reasonable inference)
✓ Maintained Data Analyst title
✓ Natural progression from manual to automated
✗ Did NOT say: "Built dashboards in Tableau/Power BI" - not in source
✗ Did NOT claim: "Designed data warehouse" - no evidence

---

EXAMPLE 4: Junior Developer → Mid-Level Role

SOURCE CV:
- Job Title: Junior Developer
- Company: TechAgency
- Duration: Jul 2022 - Present
- Bullets:
  * "Built web pages using HTML, CSS, JavaScript"
  * "Fixed bugs reported by QA team"
  * "Helped with code reviews"

TARGET JOB REQUIREMENTS:
- "2+ years development experience"
- "JavaScript and React"
- "Contribute to code quality"

TAILORED OUTPUT:
- Job Title: Junior Developer (IMMUTABLE)
- Company: TechAgency (IMMUTABLE)
- Duration: Jul 2022 - Present (IMMUTABLE)
- Bullets:
  * "Developed web pages using HTML, CSS, and JavaScript, implementing responsive designs for multiple client projects"
  * "Fixed bugs identified during QA testing, also improved code quality through thorough pull request reviews"
  * "Collaborated on code review process, providing constructive feedback to team members"

WHY THIS WORKS:
✓ JavaScript, HTML, CSS - from source
✓ "Built" → "Developed" - natural upgrade
✓ "multiple client projects" - reasonable inference from Agency context
✓ "Also improved" - introduces variation
✓ Maintained "Junior" title (honest)
✗ Did NOT claim: "Led React migration" - not in source
✗ Did NOT say: "Architected" - too senior for Junior level
✗ Did NOT add: "Redux, GraphQL, or other technologies" - not mentioned

---

EXAMPLE 5: Account Executive → Enterprise Sales Role

SOURCE CV:
- Job Title: Account Executive
- Company: SaaS Solutions Inc.
- Duration: Feb 2021 - Present
- Bullets:
  * "Managed sales pipeline for assigned territory"
  * "Closed deals with enterprise clients"
  * "Presented product demos to prospects"

TARGET JOB REQUIREMENTS:
- "Enterprise account management"
- "Complex deal negotiation"
- "Customer success focus"
- "Quota achievement"

TAILORED OUTPUT:
- Job Title: Account Executive (IMMUTABLE)
- Company: SaaS Solutions Inc. (IMMUTABLE)
- Duration: Feb 2021 - Present (IMMUTABLE)
- Bullets:
  * "Managed and grew sales pipeline for assigned territory, closing enterprise deals through strategic account planning"
  * "Negotiated complex multi-year contracts with enterprise customers, ensuring alignment on scope and value delivery"
  * "Delivered product demonstrations tailored to customer requirements, addressing key use cases relevant to their business"

WHY THIS WORKS:
✓ Pipeline management - from source
✓ Enterprise deals - from source
✓ Demos - from source
✓ "Strategic" and "complex" - natural extensions, not hallucinations
✓ Emphasizes enterprise complexity without exaggerating
✓ Varied sentence structure
✗ Did NOT claim: "Exceeded quota by 150%" - no numbers in source
✗ Did NOT say: "Managed $5M+ in ARR" - no evidence
✗ Did NOT add: "Sales methodology experience" - not mentioned
"""


def build_tailor_prompt(
    aggregated_context: dict,
    style_preferences: StylePreferences | None = None,
    include_gap_analysis: bool = False,
) -> str:
    """
    Build complete tailoring prompt with context and examples.

    Constructs:
    1. System prompt with rules and examples
    2. Style preferences section (optional)
    3. Gap analysis section (optional for Phase 11)
    4. Source CV and job posting data
    5. Instructions for JSON output

    Args:
        aggregated_context: Dict with:
            - user_cv: User's CV (dict)
            - job_posting: Job posting (dict)
            - company_research: Company context (dict)
            - gap_analysis: Optional gap analysis (dict)
        style_preferences: Optional StylePreferences model
        include_gap_analysis: Whether to include gap analysis in prompt

    Returns:
        Complete prompt string for LLM (optimized for Haiku 4.5)

    Example:
        >>> context = {
        ...     'user_cv': {...},
        ...     'job_posting': {...},
        ...     'company_research': {...},
        ... }
        >>> prompt = build_tailor_prompt(context)
        >>> assert "ANTI-DETECTION" in prompt
        >>> assert "EXAMPLE 1:" in prompt
    """
    # PSEUDO-CODE:
    # style_section = ""
    # if style_preferences:
    #     style_section = f"""
    # STYLE PREFERENCES:
    # - Tone: {style_preferences.tone}
    #   (professional/conversational/technical)
    # - Formality: {style_preferences.formality_level}
    #   (high/medium/low)
    # - Include Summary: {style_preferences.include_summary}
    # """
    #
    # gap_section = ""
    # if include_gap_analysis and aggregated_context.get('gap_analysis'):
    #     gap_section = f"""
    # PHASE 11 GAP ANALYSIS CONTEXT (Use to emphasize transferable skills):
    # {json.dumps(aggregated_context['gap_analysis'], indent=2)}
    #
    # Instructions for gap analysis:
    # - Use to identify skills that could bridge gaps
    # - Highlight transferable experience
    # - Don't claim skills not in source CV
    # """
    #
    # # Build complete prompt
    # prompt = f"""{CV_TAILOR_SYSTEM_PROMPT}
    #
    # {CV_TAILOR_FEW_SHOT_EXAMPLES}
    #
    # ---
    # NOW TAILOR THE FOLLOWING CV:
    #
    # SOURCE CV:
    # {json.dumps(aggregated_context['user_cv'], indent=2)}
    #
    # TARGET JOB POSTING:
    # {json.dumps(aggregated_context['job_posting'], indent=2)}
    #
    # COMPANY CONTEXT:
    # {json.dumps(aggregated_context['company_research'], indent=2)}
    # {style_section}{gap_section}
    #
    # RESPOND WITH VALID JSON ONLY.
    # No explanations, no markdown, no prose.
    # Return object matching TailoredCV schema.
    # """
    #
    # return prompt

    pass


def build_validation_feedback_prompt(
    original_prompt: str,
    validation_errors: list[str],
) -> str:
    """
    Build retry prompt with validation feedback.

    Used when FVS validation fails to guide LLM toward correct output.

    Args:
        original_prompt: Original tailoring prompt
        validation_errors: List of validation errors (max 5)

    Returns:
        Updated prompt with validation feedback

    Example:
        >>> prompt = build_validation_feedback_prompt(
        ...     original_prompt,
        ...     ["Hallucinated skill: 'Kubernetes'", "Date altered: '2025-01-01'"]
        ... )
        >>> assert "CRITICAL" in prompt
        >>> assert "Hallucinated skill" in prompt
    """
    # PSEUDO-CODE:
    # feedback = f"""
    #
    # CRITICAL VALIDATION FAILURES (Fix these issues):
    # """
    # for i, error in enumerate(validation_errors[:5], 1):
    #     feedback += f"\n{i}. {error}"
    #
    # feedback += f"""
    #
    # REMEMBER:
    # - NEVER change company names, job titles, or dates
    # - NEVER add skills or certifications not in source CV
    # - NEVER invent metrics or achievements
    # - ONLY reframe FLEXIBLE content (summaries, bullet descriptions)
    # - PRESERVE IMMUTABLE facts (dates, titles, names) exactly
    #
    # Try again, fixing these specific issues.
    # """
    #
    # return original_prompt + feedback

    pass


def count_tokens_estimate(prompt: str) -> int:
    """
    Estimate token count for prompt (rough approximation).

    Uses ~4 characters per token (Haiku 4.5 tokenization).

    Args:
        prompt: Complete prompt string

    Returns:
        Estimated token count

    Example:
        >>> prompt = "Hello world" * 100
        >>> tokens = count_tokens_estimate(prompt)
        >>> assert tokens > 0
    """
    # PSEUDO-CODE:
    # # Rough estimate: 1 token ≈ 4 characters
    # # More accurate: use tokenizer if available
    # return len(prompt) // 4

    pass


def validate_prompt_structure(prompt: str) -> tuple[bool, list[str]]:
    """
    Validate that prompt has all required sections.

    Checks for:
    - System prompt presence
    - Few-shot examples (at least 3)
    - Anti-detection rules
    - Source CV section
    - Job posting section
    - Output format instructions

    Args:
        prompt: Complete prompt string

    Returns:
        Tuple of (is_valid: bool, missing_sections: list[str])

    Example:
        >>> prompt = build_tailor_prompt(context)
        >>> is_valid, missing = validate_prompt_structure(prompt)
        >>> assert is_valid, f"Missing: {missing}"
    """
    # PSEUDO-CODE:
    # required_sections = [
    #     "CRITICAL CONSTRAINTS",
    #     "FVS TIER CLASSIFICATION",
    #     "ANTI-DETECTION",
    #     "EXAMPLE 1:",
    #     "EXAMPLE 2:",
    #     "SOURCE CV:",
    #     "TARGET JOB POSTING:",
    #     "RESPOND WITH VALID JSON",
    # ]
    #
    # missing = []
    # for section in required_sections:
    #     if section not in prompt:
    #         missing.append(section)
    #
    # return len(missing) == 0, missing

    pass
```

### Test Implementation Structure

```python
"""
Tests for CV Tailoring Prompt Engineering.
Per tests/logic/prompts/test_tailoring_prompt.py.

Test categories:
- System prompt (3 tests)
- Few-shot examples (4 tests)
- Dynamic prompt construction (4 tests)
- Style preference integration (2 tests)
- Gap analysis integration (2 tests)

Total: 15-20 tests
"""

import pytest

from careervp.logic.prompts.cv_tailor_prompt import (
    CV_TAILOR_SYSTEM_PROMPT,
    CV_TAILOR_FEW_SHOT_EXAMPLES,
    ANTI_DETECTION_RULES,
    build_tailor_prompt,
    build_validation_feedback_prompt,
    count_tokens_estimate,
    validate_prompt_structure,
)


class TestSystemPrompt:
    """Test system prompt requirements."""

    def test_system_prompt_includes_critical_constraints(self):
        """System prompt lists critical constraints."""
        # PSEUDO-CODE:
        # assert "NEVER fabricate" in CV_TAILOR_SYSTEM_PROMPT
        # assert "NEVER add skills" in CV_TAILOR_SYSTEM_PROMPT
        # assert "NEVER invent metrics" in CV_TAILOR_SYSTEM_PROMPT
        pass

    def test_system_prompt_includes_fvs_tiers(self):
        """System prompt explains FVS tier classification."""
        # PSEUDO-CODE:
        # assert "IMMUTABLE" in CV_TAILOR_SYSTEM_PROMPT
        # assert "VERIFIABLE" in CV_TAILOR_SYSTEM_PROMPT
        # assert "FLEXIBLE" in CV_TAILOR_SYSTEM_PROMPT
        pass

    def test_system_prompt_includes_anti_detection_rules(self):
        """System prompt includes anti-detection rules."""
        # PSEUDO-CODE:
        # assert "ANTI-DETECTION" in CV_TAILOR_SYSTEM_PROMPT
        # assert "AI CLICHÉS" in CV_TAILOR_SYSTEM_PROMPT
        pass


class TestFewShotExamples:
    """Test few-shot examples."""

    def test_few_shot_has_multiple_examples(self):
        """Few-shot section includes multiple examples."""
        # PSEUDO-CODE:
        # assert "EXAMPLE 1:" in CV_TAILOR_FEW_SHOT_EXAMPLES
        # assert "EXAMPLE 2:" in CV_TAILOR_FEW_SHOT_EXAMPLES
        # assert "EXAMPLE 3:" in CV_TAILOR_FEW_SHOT_EXAMPLES
        pass

    def test_few_shot_examples_show_immutable_preservation(self):
        """Examples show IMMUTABLE facts preserved."""
        # PSEUDO-CODE:
        # assert "IMMUTABLE - preserved exactly" in CV_TAILOR_FEW_SHOT_EXAMPLES
        pass

    def test_few_shot_examples_show_flexible_reframing(self):
        """Examples show FLEXIBLE content reframed."""
        # PSEUDO-CODE:
        # assert "FLEXIBLE" in CV_TAILOR_FEW_SHOT_EXAMPLES
        # assert "Reframed" in CV_TAILOR_FEW_SHOT_EXAMPLES
        pass

    def test_few_shot_examples_include_anti_detection(self):
        """Examples demonstrate anti-detection in action."""
        # PSEUDO-CODE:
        # assert "no \"leveraged\"" in CV_TAILOR_FEW_SHOT_EXAMPLES.lower()
        # assert "varied sentence" in CV_TAILOR_FEW_SHOT_EXAMPLES.lower()
        pass


class TestAntiDetectionRules:
    """Test anti-detection rules."""

    def test_anti_detection_has_eight_patterns(self):
        """Anti-detection rules cover 8 patterns."""
        # PSEUDO-CODE:
        # lines = ANTI_DETECTION_RULES.split('\n')
        # pattern_lines = [l for l in lines if l.strip().startswith('1.') or l.strip().startswith('2.') ... '8.']
        # assert len(pattern_lines) >= 8
        pass

    def test_anti_detection_lists_cliches(self):
        """Rules list specific AI clichés to avoid."""
        # PSEUDO-CODE:
        # assert "leverage" in ANTI_DETECTION_RULES.lower()
        # assert "synergy" in ANTI_DETECTION_RULES.lower()
        # assert "passionate" in ANTI_DETECTION_RULES.lower()
        pass

    def test_anti_detection_includes_examples(self):
        """Rules include examples of good vs bad content."""
        # PSEUDO-CODE:
        # assert "Example:" in ANTI_DETECTION_RULES
        # assert "Wrong:" in ANTI_DETECTION_RULES or "Bad:" in ANTI_DETECTION_RULES
        pass


class TestDynamicPromptConstruction:
    """Test dynamic prompt building."""

    def test_build_tailor_prompt_includes_all_sections(self):
        """Built prompt includes all required sections."""
        # PSEUDO-CODE:
        # context = {
        #     'user_cv': {...},
        #     'job_posting': {...},
        #     'company_research': {...},
        # }
        # prompt = build_tailor_prompt(context)
        # is_valid, missing = validate_prompt_structure(prompt)
        # assert is_valid, f"Missing: {missing}"
        pass

    def test_build_tailor_prompt_includes_cv_data(self):
        """Built prompt includes CV data."""
        # PSEUDO-CODE:
        # context = {
        #     'user_cv': {'name': 'John Doe'},
        #     'job_posting': {'title': 'Engineer'},
        #     'company_research': {...},
        # }
        # prompt = build_tailor_prompt(context)
        # assert 'John Doe' in prompt
        pass

    def test_build_tailor_prompt_includes_job_data(self):
        """Built prompt includes job posting data."""
        # PSEUDO-CODE:
        # context = {
        #     'user_cv': {...},
        #     'job_posting': {'title': 'Senior Engineer'},
        #     'company_research': {...},
        # }
        # prompt = build_tailor_prompt(context)
        # assert 'Senior Engineer' in prompt
        pass

    def test_build_tailor_prompt_is_valid_json_compatible(self):
        """Built prompt asks for valid JSON output."""
        # PSEUDO-CODE:
        # context = {...}
        # prompt = build_tailor_prompt(context)
        # assert "VALID JSON" in prompt
        # assert "No markdown" in prompt or "JSON only" in prompt
        pass


class TestStylePreferencesIntegration:
    """Test style preference integration."""

    def test_build_tailor_prompt_with_style_preferences(self):
        """Prompt includes style preferences when provided."""
        # PSEUDO-CODE:
        # from careervp.models.tailor import StylePreferences
        # context = {...}
        # prefs = StylePreferences(tone='technical', formality_level='low')
        # prompt = build_tailor_prompt(context, style_preferences=prefs)
        # assert 'technical' in prompt.lower()
        # assert 'formality' in prompt.lower()
        pass

    def test_build_tailor_prompt_without_style_preferences(self):
        """Prompt works without style preferences."""
        # PSEUDO-CODE:
        # context = {...}
        # prompt = build_tailor_prompt(context)
        # assert "STYLE PREFERENCES" not in prompt or prompt.count("STYLE") < 5
        pass


class TestGapAnalysisIntegration:
    """Test gap analysis integration (Phase 11)."""

    def test_build_tailor_prompt_with_gap_analysis(self):
        """Prompt includes gap analysis when provided."""
        # PSEUDO-CODE:
        # context = {
        #     ...,
        #     'gap_analysis': {'missing_skills': ['Kubernetes']},
        # }
        # prompt = build_tailor_prompt(context, include_gap_analysis=True)
        # assert 'gap' in prompt.lower() or 'phase 11' in prompt.lower()
        pass

    def test_build_tailor_prompt_phase_11_instructs_no_hallucination(self):
        """Gap analysis section still enforces no hallucination."""
        # PSEUDO-CODE:
        # context = {...}
        # prompt = build_tailor_prompt(context, include_gap_analysis=True)
        # assert "Don't claim skills not in source CV" in prompt
        pass


class TestValidationFeedback:
    """Test validation feedback prompt."""

    def test_validation_feedback_includes_errors(self):
        """Feedback prompt includes validation errors."""
        # PSEUDO-CODE:
        # original = "build_tailor_prompt(...)"
        # feedback_prompt = build_validation_feedback_prompt(
        #     original,
        #     ["Hallucinated: Kubernetes", "Date altered: 2025"],
        # )
        # assert "Kubernetes" in feedback_prompt
        # assert "Date altered" in feedback_prompt
        pass

    def test_validation_feedback_limits_to_five_errors(self):
        """Feedback prompt limits errors to 5."""
        # PSEUDO-CODE:
        # original = "build_tailor_prompt(...)"
        # errors = [f"Error {i}" for i in range(10)]
        # feedback = build_validation_feedback_prompt(original, errors)
        # # Count error mentions (should be ≤5)
        # error_count = sum(1 for e in errors[:5] if e in feedback)
        # assert error_count <= 5
        pass


class TestTokenEstimation:
    """Test token counting."""

    def test_count_tokens_positive(self):
        """Token count is positive."""
        # PSEUDO-CODE:
        # prompt = "Hello world" * 100
        # tokens = count_tokens_estimate(prompt)
        # assert tokens > 0
        pass

    def test_count_tokens_reasonable(self):
        """Token count is reasonable (rough approximation)."""
        # PSEUDO-CODE:
        # prompt = "x" * 4000  # ~1000 tokens
        # tokens = count_tokens_estimate(prompt)
        # assert 800 < tokens < 1200  # Allow some margin
        pass


class TestPromptValidation:
    """Test prompt structure validation."""

    def test_validate_prompt_structure_valid(self):
        """Valid prompt passes validation."""
        # PSEUDO-CODE:
        # context = {...}
        # prompt = build_tailor_prompt(context)
        # is_valid, missing = validate_prompt_structure(prompt)
        # assert is_valid, f"Missing sections: {missing}"
        pass

    def test_validate_prompt_structure_incomplete(self):
        """Incomplete prompt fails validation."""
        # PSEUDO-CODE:
        # incomplete_prompt = "Just some text"
        # is_valid, missing = validate_prompt_structure(incomplete_prompt)
        # assert not is_valid
        # assert len(missing) > 0
        pass
```

### Verification Commands

```bash
# Format code
uv run ruff format src/backend/careervp/logic/prompts/

# Check for style issues
uv run ruff check --fix src/backend/careervp/logic/prompts/

# Type check with strict mode
uv run mypy src/backend/careervp/logic/prompts/ --strict

# Run prompt tests
uv run pytest tests/logic/prompts/test_tailoring_prompt.py -v

# Expected output:
# ===== test session starts =====
# tests/logic/prompts/test_tailoring_prompt.py::TestSystemPrompt PASSED (3 tests)
# tests/logic/prompts/test_tailoring_prompt.py::TestFewShotExamples PASSED (4 tests)
# ... [15-20 total tests]
# ===== 15-20 passed in X.XXs =====
```

### Expected Test Results

```
tests/logic/prompts/test_tailoring_prompt.py PASSED

System Prompt Tests: 3 PASSED
- Critical constraints present
- FVS tier classification explained
- Anti-detection rules included

Few-Shot Examples Tests: 4 PASSED
- 3+ examples provided
- IMMUTABLE preservation shown
- FLEXIBLE reframing demonstrated
- Anti-detection applied

Dynamic Prompt Construction: 4 PASSED
- All sections included
- CV data integrated
- Job data integrated
- Valid JSON output requested

Style Preferences: 2 PASSED
- With preferences: tone, formality included
- Without preferences: no errors

Gap Analysis (Phase 11): 2 PASSED
- Gap analysis included when requested
- Still enforces no hallucination

Total: 15-20 tests passing
Type checking: 0 errors, 0 warnings
Prompt validation: All sections present
```

### Zero-Hallucination Checklist

- [ ] System prompt explicitly forbids fabrication
- [ ] All 8 anti-detection patterns documented
- [ ] Few-shot examples show correct vs incorrect tailoring
- [ ] Examples preserve IMMUTABLE facts exactly
- [ ] Examples only reframe FLEXIBLE content
- [ ] No examples hallucinate skills, certifications, or dates
- [ ] Validation feedback prompt included for retries
- [ ] FVS tier classification clearly explained
- [ ] Style preferences optional, don't override rules
- [ ] Gap analysis integration for Phase 11 ready

### Acceptance Criteria

- [ ] System prompt includes all critical constraints
- [ ] FVS tier classification documented in prompt
- [ ] 8 anti-detection patterns explicitly listed
- [ ] 3-5 few-shot examples provided and well-explained
- [ ] Examples cover different career levels
- [ ] Dynamic prompt construction works with all inputs
- [ ] Style preferences integrated correctly
- [ ] Gap analysis section ready for Phase 11
- [ ] Prompt structure validation working
- [ ] 15-20 tests all passing
- [ ] Type checking passes with `mypy --strict`
- [ ] Estimated token count <4000 tokens (Haiku 4.5 optimal)

---

### Verification & Compliance

1. Run `python src/backend/scripts/validate_naming.py --path src/backend/careervp/logic/prompts --strict`
2. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
3. Run `uv run pytest tests/logic/prompts/test_tailoring_prompt.py -v --cov`
4. If any prompt is incomplete or test fails, report a **BLOCKING ISSUE** and exit.
