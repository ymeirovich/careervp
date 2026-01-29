# Task 9.2: CV Tailoring - Logic Layer

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Task 9.1 (Models)

## Overview

Implement the CV tailoring orchestration logic and prompt templates using Claude Haiku 4.5 (Template Strategy). This includes the main tailoring engine, few-shot prompt construction, 8-pattern avoidance framework integration, and FVS validation pass.

## Todo

### Logic Implementation

- [ ] Create `src/backend/careervp/logic/cv_tailor.py`
- [ ] Implement `tailor_cv()` main orchestration function
- [ ] Implement `_aggregate_inputs()` to combine CV, JD, and company research
- [ ] Implement `_extract_immutable_facts()` for fact preservation
- [ ] Implement `_identify_keyword_alignments()` for JD matching
- [ ] Implement `_apply_anti_detection_rules()` for 8-pattern avoidance
- [ ] Implement `_validate_tailored_output()` for FVS validation
- [ ] Implement retry logic with exponential backoff (1s, 2s, 4s)

### Prompt Implementation

- [ ] Create `src/backend/careervp/logic/prompts/cv_tailor_prompt.py`
- [ ] Implement `CV_TAILOR_SYSTEM_PROMPT` with anti-detection rules
- [ ] Implement `CV_TAILOR_FEW_SHOT_EXAMPLES` (3 examples)
- [ ] Implement `build_tailor_prompt()` function for dynamic prompt construction
- [ ] Implement `ANTI_DETECTION_RULES` constant with 8 patterns

### Validation

- [ ] Run `uv run ruff format src/backend/careervp/logic/`
- [ ] Run `uv run ruff check --fix src/backend/careervp/logic/`
- [ ] Run `uv run mypy src/backend/careervp/logic/ --strict`

### Commit

- [ ] Commit with message: `feat(logic): implement CV tailoring engine with anti-detection`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/logic/cv_tailor.py` | Main tailoring orchestration |
| `src/backend/careervp/logic/prompts/cv_tailor_prompt.py` | Prompt templates and few-shot examples |
| `src/backend/careervp/logic/utils/llm_client.py` | LLM client (already exists) |

### Key Implementation Details

#### cv_tailor.py

```python
"""
CV Tailoring Logic - Transforms base CV to job-optimized document.
Per docs/specs/04-cv-tailoring.md.

Uses Claude Haiku 4.5 (Template Strategy) for cost-efficient processing.
Implements 8-pattern avoidance framework for anti-AI-detection.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.prompts.cv_tailor_prompt import build_tailor_prompt
from careervp.logic.utils.llm_client import LLMClient, TaskMode
from careervp.models.result import Result, ResultCode
from careervp.models.tailor import (
    TailoredCV,
    TailoredCVData,
    TailoredWorkExperience,
    TailoringMetadata,
    TokenUsage,
)

if TYPE_CHECKING:
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler
    from careervp.models.cv import UserCV
    from careervp.models.job import CompanyContext, JobPosting
    from careervp.models.tailor import StylePreferences, TailorCVRequest

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1.0, 2.0, 4.0]  # Exponential backoff


@tracer.capture_method(capture_response=False)
def tailor_cv(
    request: TailorCVRequest,
    user_cv: UserCV,
    job_posting: JobPosting,
    company_research: CompanyContext,
    dal: DynamoDalHandler,
    gap_analysis: dict | None = None,  # Phase 11 extensibility
) -> Result[TailoredCVData]:
    """
    Transform a user's CV to match a specific job posting.

    Flow:
        1. Aggregate inputs (CV, JD, company research, optional gap analysis)
        2. Extract immutable facts for preservation
        3. Build tailoring prompt with few-shot examples
        4. Call Haiku 4.5 for content generation
        5. Validate output against FVS rules
        6. Retry if validation fails (up to 3 times)
        7. Persist artifact and return result

    Args:
        request: The tailoring request with preferences
        user_cv: Source CV to tailor
        job_posting: Target job description
        company_research: Company context from Phase 8
        dal: Data access layer for persistence
        gap_analysis: Optional gap analysis for Phase 11 integration

    Returns:
        Result[TailoredCVData] with tailored CV on success or error details on failure.
    """
    start_time = time.perf_counter()
    logger.append_keys(
        user_id=request.user_id,
        application_id=request.application_id,
        job_id=request.job_id,
    )
    logger.info('starting CV tailoring')

    # Step 1: Aggregate inputs
    aggregated_context = _aggregate_inputs(
        user_cv=user_cv,
        job_posting=job_posting,
        company_research=company_research,
        gap_analysis=gap_analysis,
    )

    # Step 2: Extract immutable facts
    immutable_facts = _extract_immutable_facts(user_cv)
    logger.info('extracted immutable facts', fact_count=len(immutable_facts))

    # Step 3: Build prompt
    prompt = build_tailor_prompt(
        aggregated_context=aggregated_context,
        style_preferences=request.style_preferences,
        include_gap_analysis=request.include_gap_analysis,
    )

    # Step 4-6: Call LLM with retry logic
    llm_client = LLMClient(task_mode=TaskMode.TEMPLATE)  # Haiku 4.5
    tailored_result: Result[TailoredCV] | None = None
    token_usage: TokenUsage | None = None
    last_error: str = ''

    for attempt in range(MAX_RETRIES):
        try:
            llm_response = llm_client.generate(
                prompt=prompt,
                response_model=TailoredCV,
            )

            if not llm_response.success:
                last_error = llm_response.error or 'LLM generation failed'
                logger.warning(
                    'LLM generation failed',
                    attempt=attempt + 1,
                    error=last_error,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                continue

            # Step 5: Validate against FVS rules
            validation_result = _validate_tailored_output(
                tailored_cv=llm_response.data,
                immutable_facts=immutable_facts,
                user_cv=user_cv,
            )

            if not validation_result.success:
                last_error = validation_result.error or 'FVS validation failed'
                logger.warning(
                    'FVS validation failed',
                    attempt=attempt + 1,
                    error=last_error,
                )
                # Add validation feedback to prompt for retry
                prompt = _add_validation_feedback(prompt, validation_result.error)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                continue

            tailored_result = llm_response
            token_usage = TokenUsage(
                input_tokens=llm_response.metadata.get('input_tokens', 0),
                output_tokens=llm_response.metadata.get('output_tokens', 0),
                model='claude-haiku-4-5-20250315',
            )
            break

        except Exception as exc:
            last_error = str(exc)
            logger.exception('unexpected error during tailoring', attempt=attempt + 1)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])

    if tailored_result is None or not tailored_result.success:
        logger.error('CV tailoring failed after all retries', error=last_error)
        metrics.add_metric(name='CVTailoringErrors', unit='Count', value=1)
        return Result(
            success=False,
            error=last_error,
            code=ResultCode.CV_TAILORING_FAILED,
        )

    # Step 7: Build metadata and persist
    keyword_matches = _count_keyword_matches(
        tailored_cv=tailored_result.data,
        job_posting=job_posting,
    )
    sections_modified = _identify_modified_sections(tailored_result.data, user_cv)

    metadata = TailoringMetadata(
        application_id=request.application_id,
        version=1,
        created_at=datetime.utcnow(),
        keyword_matches=keyword_matches,
        sections_modified=sections_modified,
        fvs_validation_passed=True,
    )

    tailored_data = TailoredCVData(
        tailored_cv=tailored_result.data,
        metadata=metadata,
        token_usage=token_usage,
    )

    # Persist to DynamoDB
    persist_result = dal.save_tailored_cv(
        application_id=request.application_id,
        tailored_cv=tailored_data,
    )
    if not persist_result.success:
        logger.error('failed to persist tailored CV', error=persist_result.error)
        # Still return success since tailoring worked
        logger.warning('returning tailored CV without persistence')

    # Emit metrics
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    metrics.add_metric(name='CVTailoringRequests', unit='Count', value=1)
    metrics.add_metric(name='CVTailoringLatency', unit='Milliseconds', value=elapsed_ms)
    metrics.add_metric(name='CVTailoringKeywordMatches', unit='Count', value=keyword_matches)

    logger.info(
        'CV tailoring completed successfully',
        elapsed_ms=elapsed_ms,
        keyword_matches=keyword_matches,
    )

    return Result(
        success=True,
        data=tailored_data,
        code=ResultCode.CV_TAILORED,
    )


@tracer.capture_method(capture_response=False)
def _aggregate_inputs(
    user_cv: UserCV,
    job_posting: JobPosting,
    company_research: CompanyContext,
    gap_analysis: dict | None = None,
) -> dict:
    """Combine all inputs into unified context for prompt."""
    context = {
        'user_cv': user_cv.model_dump(mode='json'),
        'job_posting': job_posting.model_dump(mode='json'),
        'company_research': company_research.model_dump(mode='json'),
    }
    if gap_analysis:
        context['gap_analysis'] = gap_analysis
    return context


@tracer.capture_method(capture_response=False)
def _extract_immutable_facts(user_cv: UserCV) -> dict:
    """
    Extract facts that cannot be altered during tailoring.

    FVS IMMUTABLE tier: dates, titles, company names, degrees, certifications.
    """
    facts = {
        'contact_info': user_cv.contact_info.model_dump() if user_cv.contact_info else {},
        'work_experiences': [],
        'education': [],
        'certifications': [],
    }

    for exp in user_cv.work_experience or []:
        facts['work_experiences'].append({
            'company_name': exp.company_name,
            'job_title': exp.job_title,
            'start_date': exp.start_date,
            'end_date': exp.end_date,
            'location': exp.location,
        })

    for edu in user_cv.education or []:
        facts['education'].append({
            'institution': edu.institution,
            'degree': edu.degree,
            'field_of_study': edu.field_of_study,
            'graduation_date': edu.graduation_date,
        })

    for cert in user_cv.certifications or []:
        facts['certifications'].append({
            'name': cert.name,
            'issuer': cert.issuer,
            'date_obtained': cert.date_obtained,
        })

    return facts


@tracer.capture_method(capture_response=False)
def _validate_tailored_output(
    tailored_cv: TailoredCV,
    immutable_facts: dict,
    user_cv: UserCV,
) -> Result[None]:
    """
    Validate tailored CV against FVS rules.

    Checks:
    1. All IMMUTABLE facts preserved exactly
    2. No hallucinated skills or certifications
    3. Dates not fabricated or altered
    """
    errors = []

    # Validate work experience immutable facts
    for i, exp in enumerate(tailored_cv.work_experience):
        if i >= len(immutable_facts['work_experiences']):
            errors.append(f'Hallucinated work experience at index {i}')
            continue

        source = immutable_facts['work_experiences'][i]
        if exp.company_name != source['company_name']:
            errors.append(f"Company name mismatch: '{exp.company_name}' vs '{source['company_name']}'")
        if exp.job_title != source['job_title']:
            errors.append(f"Job title mismatch: '{exp.job_title}' vs '{source['job_title']}'")
        if exp.start_date != source['start_date']:
            errors.append(f"Start date mismatch: '{exp.start_date}' vs '{source['start_date']}'")

    # Validate skills exist in source CV
    source_skills = {s.lower() for s in (user_cv.skills or [])}
    for skill in tailored_cv.skills:
        if skill.skill_name.lower() not in source_skills:
            errors.append(f"Hallucinated skill: '{skill.skill_name}'")

    # Validate certifications exist in source CV
    source_certs = {c.name.lower() for c in (user_cv.certifications or [])}
    for cert in tailored_cv.certifications:
        cert_name = cert.get('name', '').lower()
        if cert_name and cert_name not in source_certs:
            errors.append(f"Hallucinated certification: '{cert.get('name')}'")

    if errors:
        error_msg = '; '.join(errors[:5])  # Limit error message length
        logger.warning('FVS validation errors', errors=errors)
        return Result(
            success=False,
            error=error_msg,
            code=ResultCode.FVS_HALLUCINATION_DETECTED,
        )

    return Result(success=True, data=None, code=ResultCode.SUCCESS)


def _add_validation_feedback(prompt: str, error: str) -> str:
    """Add validation error feedback to prompt for retry."""
    feedback = f"""

CRITICAL: Your previous response had validation errors. Fix these issues:
{error}

Remember:
- Do NOT change company names, job titles, or dates
- Do NOT add skills or certifications not in the source CV
- Only reframe FLEXIBLE content (summaries, bullet descriptions)
"""
    return prompt + feedback


def _count_keyword_matches(tailored_cv: TailoredCV, job_posting: JobPosting) -> int:
    """Count how many job keywords appear in tailored CV."""
    # Extract keywords from job posting (simplified)
    job_text = f"{job_posting.title} {job_posting.description} {' '.join(job_posting.requirements or [])}"
    job_words = set(job_text.lower().split())

    # Count matches in tailored CV
    cv_text = f"{tailored_cv.executive_summary} "
    for exp in tailored_cv.work_experience:
        cv_text += ' '.join(exp.description_bullets) + ' '
    for skill in tailored_cv.skills:
        cv_text += skill.skill_name + ' '

    cv_words = set(cv_text.lower().split())
    return len(job_words.intersection(cv_words))


def _identify_modified_sections(tailored_cv: TailoredCV, user_cv: UserCV) -> list[str]:
    """Identify which sections were modified during tailoring."""
    modified = []

    # Executive summary is always modified
    if tailored_cv.executive_summary:
        modified.append('executive_summary')

    # Check work experience bullets
    for i, exp in enumerate(tailored_cv.work_experience):
        if exp.description_bullets != exp.original_bullets:
            modified.append(f'work_experience_{i}')

    # Skills with relevance scores are considered modified
    if tailored_cv.skills:
        modified.append('skills')

    return modified
```

#### cv_tailor_prompt.py

```python
"""
CV Tailoring Prompt Templates.
Per docs/specs/04-cv-tailoring.md Prompt Strategy section.

Implements few-shot prompting for Haiku 4.5 with 8-pattern avoidance framework.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from careervp.models.tailor import StylePreferences

# 8-Pattern Avoidance Framework
# Per CLAUDE.md Decision 1.6
ANTI_DETECTION_RULES = """
ANTI-DETECTION REQUIREMENTS (Apply these to ALL generated content):
1. AVOID AI CLICHÉS: Never use "leverage", "utilize", "spearheaded", "synergy", "cutting-edge", "passionate about", "proven track record"
2. VARY SENTENCE LENGTH: Mix short sentences (8 words) with longer ones (20+ words)
3. INCLUDE IMPERFECTIONS: Add one minor stylistic variation per section (e.g., starting a bullet with "Also" or using a dash)
4. AVOID PERFECT PARALLELISM: Bullet points should NOT all follow the exact same grammatical pattern
5. CONVERSATIONAL TONE: Match the candidate's apparent experience level - don't make a junior sound like a CEO
6. USE DOMAIN TERMINOLOGY: Naturally incorporate jargon from the job posting without forcing it
7. USE CONTRACTIONS: Write "I've managed" not "I have managed" where it sounds natural
8. MIRROR USER STYLE: If the source CV uses certain phrases or patterns, maintain them
"""

CV_TAILOR_SYSTEM_PROMPT = f"""You are a professional CV optimization specialist. Your task is to tailor a candidate's CV to match a specific job description while maintaining COMPLETE FACTUAL ACCURACY.

CRITICAL CONSTRAINTS - VIOLATION MEANS FAILURE:
- NEVER fabricate dates, job titles, company names, degrees, or certifications
- NEVER add skills, tools, or technologies not mentioned in the source CV
- NEVER invent metrics or achievements not evidenced in the source
- ONLY reframe and rephrase existing content to match job requirements
- PRESERVE the candidate's authentic voice and experience level

{ANTI_DETECTION_RULES}

OUTPUT RULES:
- Return valid JSON matching the TailoredCV schema
- Include original_bullets in each work experience for validation
- Set relevance_score (0.0-1.0) for each skill based on job match
- List keyword_alignments for each work experience showing matched JD terms
"""

CV_TAILOR_FEW_SHOT_EXAMPLES = """
EXAMPLE 1: Software Engineer → Senior Backend Role

SOURCE CV BULLET:
"Built REST APIs using Python and Flask for internal tools"

TARGET JOB REQUIREMENT:
"Design and implement scalable microservices architecture"

TAILORED OUTPUT:
"Developed RESTful microservices in Python/Flask that supported internal tooling across 3 teams"

WHY THIS WORKS:
- Preserved: Python, Flask, REST APIs, internal tools (all from source)
- Reframed: "Built" → "Developed", added "microservices" context that matches JD
- Added scope: "across 3 teams" - ONLY if evidenced elsewhere in CV
- Anti-detection: Natural flow, no buzzwords, specific detail

---

EXAMPLE 2: Marketing Manager → Product Marketing

SOURCE CV BULLET:
"Managed social media accounts and created content calendars"

TARGET JOB REQUIREMENT:
"Drive product positioning and go-to-market strategies"

TAILORED OUTPUT:
"Created and executed content strategies that aligned brand messaging with product launches"

WHY THIS WORKS:
- Preserved: Content creation, strategy elements (from source)
- Reframed: Connected to product context without fabricating PMM experience
- NOT SAID: "Led go-to-market" - would be hallucination if not in source
- Anti-detection: Conversational, avoids "spearheaded" or "drove"

---

EXAMPLE 3: Data Analyst → Business Intelligence

SOURCE CV BULLET:
"Created weekly reports in Excel for sales team"

TARGET JOB REQUIREMENT:
"Build dashboards and automate reporting workflows"

TAILORED OUTPUT:
"Delivered weekly sales performance reports, streamlining data delivery for stakeholder decision-making"

WHY THIS WORKS:
- Preserved: Weekly reports, sales focus, Excel-based work
- Reframed: Emphasized business impact without claiming dashboard/automation skills
- NOT SAID: "Built dashboards" - would be fabrication
- Anti-detection: Professional but not over-polished, natural phrasing
"""


def build_tailor_prompt(
    aggregated_context: dict,
    style_preferences: StylePreferences | None = None,
    include_gap_analysis: bool = False,
) -> str:
    """
    Build the complete tailoring prompt with context and examples.

    Args:
        aggregated_context: Combined CV, JD, company research
        style_preferences: Optional styling preferences
        include_gap_analysis: Whether gap analysis is included

    Returns:
        Complete prompt string for LLM
    """
    style_section = ''
    if style_preferences:
        style_section = f"""
STYLE PREFERENCES:
- Tone: {style_preferences.tone}
- Formality: {style_preferences.formality_level}
- Include Summary: {style_preferences.include_summary}
"""

    gap_section = ''
    if include_gap_analysis and aggregated_context.get('gap_analysis'):
        gap_section = f"""
GAP ANALYSIS CONTEXT (Use to emphasize transferable skills):
{json.dumps(aggregated_context['gap_analysis'], indent=2)}
"""

    prompt = f"""{CV_TAILOR_SYSTEM_PROMPT}

{CV_TAILOR_FEW_SHOT_EXAMPLES}

---

NOW TAILOR THE FOLLOWING CV:

SOURCE CV:
{json.dumps(aggregated_context['user_cv'], indent=2)}

TARGET JOB POSTING:
{json.dumps(aggregated_context['job_posting'], indent=2)}

COMPANY CONTEXT:
{json.dumps(aggregated_context['company_research'], indent=2)}
{style_section}{gap_section}
RESPOND WITH VALID JSON ONLY. No explanations or markdown.
"""

    return prompt
```

### LLM Client Integration

The logic assumes `LLMClient` from `logic/utils/llm_client.py` supports:

```python
class TaskMode(Enum):
    STRATEGIC = "strategic"  # Sonnet 4.5
    TEMPLATE = "template"    # Haiku 4.5

class LLMClient:
    def __init__(self, task_mode: TaskMode = TaskMode.STRATEGIC):
        self.task_mode = task_mode
        self.model = self._select_model()

    def _select_model(self) -> str:
        if self.task_mode == TaskMode.TEMPLATE:
            return "claude-haiku-4-5-20250315"
        return "claude-sonnet-4-5-20250315"

    def generate(self, prompt: str, response_model: type[T]) -> Result[T]:
        """Generate structured output from LLM."""
        ...
```

### Result Pattern Enforcement

All functions return `Result[T]`:
- Success: `Result(success=True, data=..., code=ResultCode.SUCCESS)`
- Failure: `Result(success=False, error='...', code=ResultCode.ERROR_CODE)`

Never raise exceptions from logic layer - always wrap in Result.

### Zero-Hallucination Checklist

- [ ] `_extract_immutable_facts()` captures all FVS IMMUTABLE fields
- [ ] `_validate_tailored_output()` checks all immutable facts are preserved
- [ ] Few-shot examples demonstrate correct vs incorrect tailoring
- [ ] Prompt includes explicit "NEVER fabricate" instructions
- [ ] Retry logic adds validation feedback for subsequent attempts
- [ ] All 8 anti-detection patterns documented in prompt

### Acceptance Criteria

- [ ] `tailor_cv()` returns `Result[TailoredCVData]` in all cases
- [ ] FVS validation catches hallucinated facts
- [ ] Retry logic works with exponential backoff
- [ ] Metrics emitted: `CVTailoringRequests`, `CVTailoringLatency`, `CVTailoringErrors`
- [ ] Optional `gap_analysis` parameter accepted for Phase 11
- [ ] Anti-detection rules embedded in system prompt

---

### Verification & Compliance

1. Run `python src/backend/scripts/validate_naming.py --path infra --strict`
2. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
3. If any path or class signature is missing, report a **BLOCKING ISSUE** and exit.
