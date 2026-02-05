# Task 9.3: CV Tailoring - Core Tailoring Logic

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Task 9.1 (Validation), Task 9.4 (Prompt Engineering)
**Blocking:** Task 9.5 (FVS Integration), Task 9.6 (Handler)

## Overview

Implement the core CV tailoring logic that orchestrates the transformation of a user's CV to match a specific job posting. This layer uses Claude Haiku 4.5 for cost-efficient processing, implements the 8-pattern anti-AI-detection framework, and validates output against FVS (Fact-Value-Sentiment) rules to prevent hallucinations.

## Todo

### Logic Implementation

- [ ] Create `src/backend/careervp/logic/cv_tailor.py`
- [ ] Implement `tailor_cv()` main orchestration function
- [ ] Implement `_aggregate_inputs()` combining CV, JD, company research
- [ ] Implement `_extract_immutable_facts()` preserving IMMUTABLE tier data
- [ ] Implement `_identify_keyword_alignments()` matching JD keywords
- [ ] Implement `_apply_anti_detection_rules()` for anti-AI-detection
- [ ] Implement `_validate_tailored_output()` for FVS validation
- [ ] Implement retry logic with exponential backoff (1s, 2s, 4s)
- [ ] Implement metrics emission and logging

### Test Implementation

- [ ] Create `tests/logic/test_tailoring_logic.py`
- [ ] Implement 25-30 test cases covering all functions
- [ ] Test aggregation logic (3 tests)
- [ ] Test immutable fact extraction (4 tests)
- [ ] Test keyword alignment (4 tests)
- [ ] Test anti-detection rules (4 tests)
- [ ] Test FVS validation (4 tests)
- [ ] Test retry logic (3 tests)
- [ ] Test error handling (3 tests)

### Validation & Formatting

- [ ] Run `uv run ruff format src/backend/careervp/logic/`
- [ ] Run `uv run ruff check --fix src/backend/careervp/logic/`
- [ ] Run `uv run mypy src/backend/careervp/logic/ --strict`
- [ ] Run `uv run pytest tests/logic/test_tailoring_logic.py -v`

### Commit

- [ ] Commit with message: `feat(logic): implement core CV tailoring engine with FVS validation`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/logic/cv_tailor.py` | Main tailoring orchestration and functions |
| `tests/logic/test_tailoring_logic.py` | Comprehensive test suite |

### Key Implementation Details

```python
"""
Core CV Tailoring Logic.
Per docs/specs/04-cv-tailoring.md.

Orchestrates transformation of base CV to job-optimized document:
1. Aggregate inputs (CV, job description, company research)
2. Extract immutable facts for preservation
3. Identify keyword alignments
4. Build and execute tailoring prompt
5. Validate output against FVS rules
6. Retry if validation fails
7. Persist and return result

Uses Claude Haiku 4.5 (Template Strategy) for cost efficiency.
Implements 8-pattern anti-detection framework.
All functions return Result[T] for error handling.
"""

from __future__ import annotations

import time
from datetime import datetime
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
RETRY_DELAYS = [1.0, 2.0, 4.0]  # Exponential backoff (seconds)


@tracer.capture_method(capture_response=False)
def tailor_cv(
    request: TailorCVRequest,
    user_cv: UserCV,
    job_posting: JobPosting,
    company_research: CompanyContext,
    dal: DynamoDalHandler,
    gap_analysis: dict | None = None,
) -> Result[TailoredCVData]:
    """
    Transform user's CV to match specific job posting.

    Orchestration flow:
        1. Aggregate inputs (CV, JD, company research, optional gap analysis)
        2. Extract immutable facts for preservation
        3. Build tailoring prompt with few-shot examples
        4. Call Haiku 4.5 for content generation
        5. Validate output against FVS rules
        6. Retry if validation fails (up to 3 times)
        7. Persist artifact and return result

    Args:
        request: TailorCVRequest with user preferences
        user_cv: Source CV to tailor (UserCV model)
        job_posting: Target job description (JobPosting model)
        company_research: Company context from Phase 8 (CompanyContext)
        dal: Data access layer for persistence (DynamoDalHandler)
        gap_analysis: Optional gap analysis for Phase 11 integration

    Returns:
        Result[TailoredCVData] containing:
        - success: True if tailoring completed successfully
        - data: TailoredCVData with tailored CV, metadata, token usage
        - error: Human-readable error message on failure
        - code: Machine-readable result code

    Example:
        >>> result = tailor_cv(
        ...     request=TailorCVRequest(...),
        ...     user_cv=cv,
        ...     job_posting=job,
        ...     company_research=research,
        ...     dal=dal_handler,
        ... )
        >>> assert result.success
        >>> assert result.data.tailored_cv.executive_summary
    """
    # PSEUDO-CODE:
    # start_time = record current time
    # logger.append_keys(user_id, application_id, job_id)
    # logger.info("starting CV tailoring")
    #
    # # Step 1: Aggregate inputs
    # aggregated_context = _aggregate_inputs(...)
    #
    # # Step 2: Extract immutable facts
    # immutable_facts = _extract_immutable_facts(user_cv)
    # logger.info("extracted immutable facts", fact_count=len(immutable_facts))
    #
    # # Step 3-6: Call LLM with retry logic
    # tailored_result = None
    # token_usage = None
    # last_error = ""
    #
    # for attempt in range(MAX_RETRIES):
    #     try:
    #         # Build prompt
    #         prompt = build_tailor_prompt(...)
    #
    #         # Call Haiku 4.5
    #         llm_response = LLMClient(TaskMode.TEMPLATE).generate(...)
    #
    #         if not llm_response.success:
    #             last_error = llm_response.error
    #             if attempt < MAX_RETRIES - 1:
    #                 time.sleep(RETRY_DELAYS[attempt])
    #             continue
    #
    #         # Validate against FVS rules
    #         validation = _validate_tailored_output(...)
    #         if not validation.success:
    #             last_error = validation.error
    #             if attempt < MAX_RETRIES - 1:
    #                 time.sleep(RETRY_DELAYS[attempt])
    #             continue
    #
    #         tailored_result = llm_response
    #         token_usage = TokenUsage(...)
    #         break
    #
    #     except Exception as exc:
    #         last_error = str(exc)
    #         logger.exception("unexpected error", attempt=attempt + 1)
    #         if attempt < MAX_RETRIES - 1:
    #             time.sleep(RETRY_DELAYS[attempt])
    #
    # if tailored_result is None:
    #     logger.error("CV tailoring failed after all retries")
    #     metrics.add_metric("CVTailoringErrors", value=1)
    #     return Result(success=False, error=last_error, code=ResultCode.CV_TAILORING_FAILED)
    #
    # # Step 7: Build metadata and persist
    # keyword_matches = _count_keyword_matches(...)
    # sections_modified = _identify_modified_sections(...)
    #
    # metadata = TailoringMetadata(...)
    # tailored_data = TailoredCVData(...)
    #
    # persist_result = dal.save_tailored_cv(...)
    # if not persist_result.success:
    #     logger.warning("persistence failed, returning without persistence")
    #
    # # Emit metrics
    # elapsed_ms = (time.perf_counter() - start_time) * 1000
    # metrics.add_metric("CVTailoringRequests", value=1)
    # metrics.add_metric("CVTailoringLatency", value=elapsed_ms)
    #
    # logger.info("CV tailoring completed successfully", elapsed_ms=elapsed_ms)
    # return Result(success=True, data=tailored_data, code=ResultCode.CV_TAILORED)

    pass


@tracer.capture_method(capture_response=False)
def _aggregate_inputs(
    user_cv: UserCV,
    job_posting: JobPosting,
    company_research: CompanyContext,
    gap_analysis: dict | None = None,
) -> dict:
    """
    Combine all inputs into unified context for LLM prompt.

    Aggregates:
    - User's base CV (all sections)
    - Target job description (title, description, requirements)
    - Company context (industry, size, culture from Phase 8)
    - Optional gap analysis (Phase 11 integration point)

    Args:
        user_cv: Source CV (UserCV model)
        job_posting: Job posting to target (JobPosting model)
        company_research: Company research context (CompanyContext)
        gap_analysis: Optional gap analysis dict for Phase 11

    Returns:
        Dict with aggregated context: 
        {
            'user_cv': dict,
            'job_posting': dict,
            'company_research': dict,
            'gap_analysis': dict (optional),
        }

    Example:
        >>> context = _aggregate_inputs(cv, job, research)
        >>> assert 'user_cv' in context
        >>> assert 'job_posting' in context
    """
    # PSEUDO-CODE:
    # context = {
    #     'user_cv': user_cv.model_dump(mode='json'),
    #     'job_posting': job_posting.model_dump(mode='json'),
    #     'company_research': company_research.model_dump(mode='json'),
    # }
    # if gap_analysis:
    #     context['gap_analysis'] = gap_analysis
    # return context

    pass


@tracer.capture_method(capture_response=False)
def _extract_immutable_facts(user_cv: UserCV) -> dict:
    """
    Extract facts that CANNOT be altered during tailoring.

    FVS IMMUTABLE tier includes:
    - Contact information (name, email, phone, LinkedIn)
    - Work experience (company names, job titles, dates, locations)
    - Education (institution, degree, field, graduation date)
    - Certifications (name, issuer, date obtained)

    These facts must be preserved exactly in tailored output.

    Args:
        user_cv: Source CV (UserCV model)

    Returns:
        Dict with immutable facts for validation:
        {
            'contact_info': {...},
            'work_experiences': [
                {'company_name': str, 'job_title': str, 'dates': ...},
                ...
            ],
            'education': [...],
            'certifications': [...],
        }

    Example:
        >>> facts = _extract_immutable_facts(cv)
        >>> assert facts['contact_info']['email'] == cv.contact_info.email
        >>> assert len(facts['work_experiences']) == len(cv.work_experience)
    """
    # PSEUDO-CODE:
    # facts = {
    #     'contact_info': {
    #         'name': user_cv.contact_info.full_name if user_cv.contact_info else None,
    #         'email': user_cv.contact_info.email if user_cv.contact_info else None,
    #         'phone': user_cv.contact_info.phone if user_cv.contact_info else None,
    #         'linkedin': user_cv.contact_info.linkedin_url if user_cv.contact_info else None,
    #     },
    #     'work_experiences': [],
    #     'education': [],
    #     'certifications': [],
    # }
    #
    # for exp in user_cv.work_experience or []:
    #     facts['work_experiences'].append({
    #         'company_name': exp.company_name,
    #         'job_title': exp.job_title,
    #         'start_date': exp.start_date,
    #         'end_date': exp.end_date,
    #         'location': exp.location,
    #     })
    #
    # for edu in user_cv.education or []:
    #     facts['education'].append({
    #         'institution': edu.institution,
    #         'degree': edu.degree,
    #         'field_of_study': edu.field_of_study,
    #         'graduation_date': edu.graduation_date,
    #     })
    #
    # for cert in user_cv.certifications or []:
    #     facts['certifications'].append({
    #         'name': cert.name,
    #         'issuer': cert.issuer,
    #         'date_obtained': cert.date_obtained,
    #     })
    #
    # return facts

    pass


@tracer.capture_method(capture_response=False)
def _identify_keyword_alignments(
    user_cv: UserCV,
    job_posting: JobPosting,
) -> dict[str, list[str]]:
    """
    Identify keyword matches between CV and job description.

    Extracts keywords from job posting and maps them to CV sections:
    - Skills section (exact matches and related terms)
    - Work experience bullets (context matches)
    - Education/certifications (relevant credentials)

    Args:
        user_cv: Source CV (UserCV model)
        job_posting: Target job posting (JobPosting model)

    Returns:
        Dict mapping CV sections to matched keywords:
        {
            'skills': ['Python', 'AWS', ...],
            'work_experience': ['Project Manager', 'Budget', ...],
            'education': ['MBA', ...],
        }

    Example:
        >>> alignments = _identify_keyword_alignments(cv, job)
        >>> assert 'Python' in alignments.get('skills', [])
    """
    # PSEUDO-CODE:
    # # Extract job keywords (simplified)
    # job_text = f"{job_posting.title} {job_posting.description}"
    # job_keywords = extract_keywords(job_text)
    #
    # alignments = {
    #     'skills': [],
    #     'work_experience': [],
    #     'education': [],
    # }
    #
    # # Match skills
    # cv_skills = {s.lower() for s in (user_cv.skills or [])}
    # for keyword in job_keywords:
    #     if keyword.lower() in cv_skills:
    #         alignments['skills'].append(keyword)
    #
    # # Match work experience keywords
    # for exp in user_cv.work_experience or []:
    #     exp_text = f"{exp.job_title} {' '.join(exp.description or [])}"
    #     for keyword in job_keywords:
    #         if keyword.lower() in exp_text.lower():
    #             alignments['work_experience'].append(keyword)
    #             break
    #
    # return alignments

    pass


@tracer.capture_method(capture_response=False)
def _apply_anti_detection_rules(tailored_cv: TailoredCV) -> Result[None]:
    """
    Apply and verify 8-pattern anti-AI-detection rules.

    Checks that tailored content:
    1. Avoids AI clichés (leverage, synergy, passionate)
    2. Varies sentence length (mix 8-word and 20+ word sentences)
    3. Includes imperfections (natural variations)
    4. Avoids perfect parallelism (bullet point variation)
    5. Uses conversational tone (contractions, natural phrasing)
    6. Incorporates domain terminology naturally
    7. Uses contractions where appropriate
    8. Maintains user's authentic voice

    Args:
        tailored_cv: Tailored CV to check (TailoredCV model)

    Returns:
        Result[None] with success=True if rules applied, error details otherwise.

    Example:
        >>> result = _apply_anti_detection_rules(tailored_cv)
        >>> assert result.success
    """
    # PSEUDO-CODE:
    # issues = []
    #
    # # Pattern 1: Check for AI clichés
    # ai_cliches = ["leverage", "synergy", "passionate about", "proven track record"]
    # for exp in tailored_cv.work_experience:
    #     for bullet in exp.description_bullets:
    #         for cliche in ai_cliches:
    #             if cliche.lower() in bullet.lower():
    #                 issues.append(f"AI cliché found: '{cliche}'")
    #
    # # Pattern 2: Check sentence length variation
    # for exp in tailored_cv.work_experience:
    #     sentence_lengths = [len(b.split()) for b in exp.description_bullets]
    #     if len(set(sentence_lengths)) < 2:  # Less than 2 different lengths
    #         issues.append("Bullet points lack sentence length variation")
    #
    # # Pattern 4: Check for parallel bullet patterns
    # for exp in tailored_cv.work_experience:
    #     patterns = [b.split()[0] if b else "" for b in exp.description_bullets]
    #     if len(set(patterns)) < len(patterns) / 2:
    #         issues.append("Bullets are too parallel in structure")
    #
    # if issues:
    #     logger.warning("anti-detection issues found", issues=issues)
    #     return Result(success=False, error="; ".join(issues[:3]))
    #
    # return Result(success=True, data=None, code=ResultCode.SUCCESS)

    pass


@tracer.capture_method(capture_response=False)
def _validate_tailored_output(
    tailored_cv: TailoredCV,
    immutable_facts: dict,
    user_cv: UserCV,
) -> Result[None]:
    """
    Validate tailored CV against FVS rules to prevent hallucinations.

    Checks:
    1. All IMMUTABLE facts preserved exactly
    2. No hallucinated skills (not in source CV)
    3. No hallucinated certifications
    4. No fabricated dates or metrics
    5. Work experience count matches source

    Args:
        tailored_cv: Tailored CV to validate (TailoredCV model)
        immutable_facts: Extracted immutable facts dict
        user_cv: Source CV for comparison (UserCV model)

    Returns:
        Result[None] with success=True if validation passes, error details if fails.

    Example:
        >>> result = _validate_tailored_output(tailored, facts, cv)
        >>> assert result.success
    """
    # PSEUDO-CODE:
    # errors = []
    #
    # # Check 1: Immutable facts preservation
    # for i, exp in enumerate(tailored_cv.work_experience):
    #     if i >= len(immutable_facts['work_experiences']):
    #         errors.append(f"Hallucinated work experience at index {i}")
    #         continue
    #
    #     source = immutable_facts['work_experiences'][i]
    #     if exp.company_name != source['company_name']:
    #         errors.append(f"Company name altered: '{exp.company_name}'")
    #     if exp.job_title != source['job_title']:
    #         errors.append(f"Job title altered: '{exp.job_title}'")
    #     if exp.start_date != source['start_date']:
    #         errors.append(f"Start date altered: '{exp.start_date}'")
    #
    # # Check 2: Hallucinated skills
    # source_skills = {s.lower() for s in (user_cv.skills or [])}
    # for skill in tailored_cv.skills:
    #     if skill.skill_name.lower() not in source_skills:
    #         errors.append(f"Hallucinated skill: '{skill.skill_name}'")
    #
    # # Check 3: Hallucinated certifications
    # source_certs = {c.name.lower() for c in (user_cv.certifications or [])}
    # for cert in tailored_cv.certifications:
    #     cert_name = cert.get('name', '').lower()
    #     if cert_name and cert_name not in source_certs:
    #         errors.append(f"Hallucinated certification: '{cert.get('name')}'")
    #
    # # Check 4: No fabricated metrics
    # for exp in tailored_cv.work_experience:
    #     for bullet in exp.description_bullets:
    #         # Flag suspicious metrics without source evidence
    #         if "increased" in bullet.lower() or "improved" in bullet.lower():
    #             if "%" not in bullet and "x" not in bullet:
    #                 logger.warning("metric without evidence", bullet=bullet)
    #
    # if errors:
    #     error_msg = "; ".join(errors[:5])
    #     logger.warning("FVS validation errors", errors=errors)
    #     return Result(success=False, error=error_msg, code=ResultCode.FVS_HALLUCINATION_DETECTED)
    #
    # return Result(success=True, data=None, code=ResultCode.SUCCESS)

    pass


def _count_keyword_matches(
    tailored_cv: TailoredCV,
    job_posting: JobPosting,
) -> int:
    """
    Count how many job keywords appear in tailored CV.

    Used for metadata tracking and performance metrics.

    Args:
        tailored_cv: Tailored CV (TailoredCV model)
        job_posting: Job posting (JobPosting model)

    Returns:
        Integer count of matched keywords.

    Example:
        >>> count = _count_keyword_matches(tailored, job)
        >>> assert count > 0
    """
    # PSEUDO-CODE:
    # # Extract keywords from job posting
    # job_text = f"{job_posting.title} {job_posting.description} "
    # job_text += " ".join(job_posting.requirements or [])
    # job_words = set(job_text.lower().split())
    #
    # # Count matches in tailored CV
    # cv_text = f"{tailored_cv.executive_summary} "
    # for exp in tailored_cv.work_experience:
    #     cv_text += " ".join(exp.description_bullets) + " "
    # for skill in tailored_cv.skills:
    #     cv_text += skill.skill_name + " "
    #
    # cv_words = set(cv_text.lower().split())
    # return len(job_words.intersection(cv_words))

    pass


def _identify_modified_sections(
    tailored_cv: TailoredCV,
    user_cv: UserCV,
) -> list[str]:
    """
    Identify which CV sections were modified during tailoring.

    Used for tracking and audit purposes.

    Args:
        tailored_cv: Tailored CV (TailoredCV model)
        user_cv: Source CV (UserCV model)

    Returns:
        List of section names that were modified.

    Example:
        >>> sections = _identify_modified_sections(tailored, cv)
        >>> assert 'executive_summary' in sections
    """
    # PSEUDO-CODE:
    # modified = []
    #
    # # Executive summary is always modified
    # if tailored_cv.executive_summary:
    #     modified.append('executive_summary')
    #
    # # Check work experience bullets
    # for i, exp in enumerate(tailored_cv.work_experience):
    #     if exp.description_bullets != exp.original_bullets:
    #         modified.append(f'work_experience_{i}')
    #
    # # Skills with relevance scores are considered modified
    # if tailored_cv.skills:
    #     modified.append('skills')
    #
    # return modified

    pass
```

### Test Implementation Structure

```python
"""
Tests for CV Tailoring Logic.
Per tests/logic/test_tailoring_logic.py.

Test categories:
- Input aggregation (3 tests)
- Immutable fact extraction (4 tests)
- Keyword alignment (4 tests)
- Anti-detection rules (4 tests)
- FVS validation (4 tests)
- Retry logic (3 tests)
- Error handling (3 tests)

Total: 25-30 tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from careervp.logic.cv_tailor import (
    tailor_cv,
    _aggregate_inputs,
    _extract_immutable_facts,
    _identify_keyword_alignments,
    _apply_anti_detection_rules,
    _validate_tailored_output,
    _count_keyword_matches,
    _identify_modified_sections,
)
from careervp.models.result import ResultCode


class TestInputAggregation:
    """Test input aggregation logic."""

    def test_aggregate_inputs_basic(self):
        """Aggregation combines all inputs."""
        # PSEUDO-CODE:
        # cv = Mock(UserCV)
        # job = Mock(JobPosting)
        # research = Mock(CompanyContext)
        # result = _aggregate_inputs(cv, job, research)
        # assert 'user_cv' in result
        # assert 'job_posting' in result
        # assert 'company_research' in result
        pass

    def test_aggregate_inputs_with_gap_analysis(self):
        """Aggregation includes gap analysis when provided."""
        # PSEUDO-CODE:
        # cv = Mock(UserCV)
        # job = Mock(JobPosting)
        # research = Mock(CompanyContext)
        # gap_data = {"missing_skills": [...]}
        # result = _aggregate_inputs(cv, job, research, gap_data)
        # assert result.get('gap_analysis') == gap_data
        pass

    def test_aggregate_inputs_without_gap_analysis(self):
        """Aggregation works without gap analysis."""
        # PSEUDO-CODE:
        # cv = Mock(UserCV)
        # job = Mock(JobPosting)
        # research = Mock(CompanyContext)
        # result = _aggregate_inputs(cv, job, research)
        # assert 'gap_analysis' not in result
        pass


class TestImmutableFactExtraction:
    """Test immutable fact extraction."""

    def test_extract_immutable_facts_contact_info(self):
        """Extracts contact information."""
        # PSEUDO-CODE:
        # cv = Mock(UserCV)
        # cv.contact_info = Mock(full_name="John Doe", email="john@example.com")
        # facts = _extract_immutable_facts(cv)
        # assert facts['contact_info']['name'] == "John Doe"
        # assert facts['contact_info']['email'] == "john@example.com"
        pass

    def test_extract_immutable_facts_work_experience(self):
        """Extracts work experience facts."""
        # PSEUDO-CODE:
        # cv = Mock(UserCV)
        # exp = Mock(company_name="Acme Corp", job_title="Engineer")
        # cv.work_experience = [exp]
        # facts = _extract_immutable_facts(cv)
        # assert len(facts['work_experiences']) == 1
        # assert facts['work_experiences'][0]['company_name'] == "Acme Corp"
        pass

    def test_extract_immutable_facts_education(self):
        """Extracts education facts."""
        # PSEUDO-CODE:
        # cv = Mock(UserCV)
        # edu = Mock(institution="MIT", degree="BS", field_of_study="CS")
        # cv.education = [edu]
        # facts = _extract_immutable_facts(cv)
        # assert len(facts['education']) == 1
        # assert facts['education'][0]['degree'] == "BS"
        pass

    def test_extract_immutable_facts_certifications(self):
        """Extracts certification facts."""
        # PSEUDO-CODE:
        # cv = Mock(UserCV)
        # cert = Mock(name="AWS Solutions Architect", issuer="AWS")
        # cv.certifications = [cert]
        # facts = _extract_immutable_facts(cv)
        # assert len(facts['certifications']) == 1
        # assert facts['certifications'][0]['name'] == "AWS Solutions Architect"
        pass


class TestKeywordAlignment:
    """Test keyword alignment."""

    def test_identify_keyword_alignments_skills(self):
        """Identifies keyword matches in skills."""
        # PSEUDO-CODE:
        # cv = Mock(UserCV, skills=["Python", "AWS", "Docker"])
        # job = Mock(description="We need Python and Kubernetes")
        # result = _identify_keyword_alignments(cv, job)
        # assert "Python" in result['skills']
        pass

    def test_identify_keyword_alignments_work_experience(self):
        """Identifies keyword matches in work experience."""
        # PSEUDO-CODE:
        # exp = Mock(job_title="Engineering Manager", description=["Led team"])
        # cv = Mock(work_experience=[exp])
        # job = Mock(description="We need an Engineering Manager")
        # result = _identify_keyword_alignments(cv, job)
        # assert len(result['work_experience']) > 0
        pass

    def test_identify_keyword_alignments_no_matches(self):
        """Returns empty when no keywords match."""
        # PSEUDO-CODE:
        # cv = Mock(UserCV, skills=["COBOL"])
        # job = Mock(description="We need Python and Rust")
        # result = _identify_keyword_alignments(cv, job)
        # assert len(result['skills']) == 0
        pass

    def test_identify_keyword_alignments_partial_matches(self):
        """Handles partial keyword matches."""
        # PSEUDO-CODE:
        # cv = Mock(UserCV, skills=["Python", "Java"])
        # job = Mock(description="Python developer needed")
        # result = _identify_keyword_alignments(cv, job)
        # assert "Python" in result['skills']
        pass


class TestAntiDetectionRules:
    """Test anti-AI-detection rules."""

    def test_anti_detection_rejects_cliches(self):
        """Rejects content with AI clichés."""
        # PSEUDO-CODE:
        # cv = Mock(TailoredCV)
        # exp = Mock(description_bullets=["Leveraged synergy to optimize solutions"])
        # cv.work_experience = [exp]
        # result = _apply_anti_detection_rules(cv)
        # assert not result.success
        # assert "cliché" in result.error.lower()
        pass

    def test_anti_detection_allows_natural_content(self):
        """Allows natural, human-like content."""
        # PSEUDO-CODE:
        # cv = Mock(TailoredCV)
        # exp = Mock(description_bullets=[
        #     "Managed a team of 5 engineers for the mobile platform.",
        #     "Also worked on infrastructure improvements.",
        # ])
        # cv.work_experience = [exp]
        # result = _apply_anti_detection_rules(cv)
        # assert result.success
        pass

    def test_anti_detection_checks_sentence_variation(self):
        """Checks for sentence length variation."""
        # PSEUDO-CODE:
        # cv = Mock(TailoredCV)
        # exp = Mock(description_bullets=[
        #     "Managed team.",  # 2 words
        #     "Managed team.",  # 2 words (same)
        #     "Managed team.",  # 2 words (same)
        # ])
        # cv.work_experience = [exp]
        # result = _apply_anti_detection_rules(cv)
        # assert not result.success
        pass

    def test_anti_detection_checks_parallelism(self):
        """Checks for problematic parallelism."""
        # PSEUDO-CODE:
        # cv = Mock(TailoredCV)
        # exp = Mock(description_bullets=[
        #     "Managed team of 5 engineers",
        #     "Managed infrastructure improvements",
        #     "Managed deployment processes",
        # ])
        # cv.work_experience = [exp]
        # result = _apply_anti_detection_rules(cv)
        # assert not result.success
        pass


class TestFVSValidation:
    """Test FVS validation."""

    def test_fvs_validation_preserves_immutable_facts(self):
        """FVS validation checks immutable fact preservation."""
        # PSEUDO-CODE:
        # tailored = Mock(TailoredCV)
        # exp = Mock(company_name="Acme", job_title="Engineer")
        # tailored.work_experience = [exp]
        # facts = {'work_experiences': [{'company_name': "Acme", 'job_title': "Engineer"}]}
        # cv = Mock()
        # result = _validate_tailored_output(tailored, facts, cv)
        # assert result.success
        pass

    def test_fvs_validation_rejects_hallucinated_skills(self):
        """FVS validation detects hallucinated skills."""
        # PSEUDO-CODE:
        # tailored = Mock(TailoredCV)
        # skill = Mock(skill_name="Rust")
        # tailored.skills = [skill]
        # facts = {'skills': []}
        # cv = Mock(skills=["Python"])
        # result = _validate_tailored_output(tailored, facts, cv)
        # assert not result.success
        # assert "hallucinated" in result.error.lower()
        pass

    def test_fvs_validation_rejects_altered_dates(self):
        """FVS validation detects altered dates."""
        # PSEUDO-CODE:
        # tailored = Mock(TailoredCV)
        # exp = Mock(start_date="2025-01-01")
        # tailored.work_experience = [exp]
        # facts = {'work_experiences': [{'start_date': "2020-01-01"}]}
        # cv = Mock()
        # result = _validate_tailored_output(tailored, facts, cv)
        # assert not result.success
        pass

    def test_fvs_validation_rejects_hallucinated_certifications(self):
        """FVS validation detects hallucinated certifications."""
        # PSEUDO-CODE:
        # tailored = Mock(TailoredCV)
        # tailored.certifications = [{'name': 'PhD in CS'}]
        # facts = {'certifications': []}
        # cv = Mock(certifications=[])
        # result = _validate_tailored_output(tailored, facts, cv)
        # assert not result.success
        pass


class TestRetryLogic:
    """Test retry mechanism."""

    def test_retry_logic_succeeds_on_first_attempt(self):
        """Succeeds on first attempt without retries."""
        # PSEUDO-CODE:
        # with patch('careervp.logic.llm_client.LLMClient') as mock_llm:
        #     mock_llm.generate.return_value = Result(success=True, data=Mock())
        #     result = tailor_cv(request, cv, job, research, dal)
        #     assert result.success
        #     assert mock_llm.generate.call_count == 1
        pass

    def test_retry_logic_retries_on_validation_failure(self):
        """Retries if FVS validation fails."""
        # PSEUDO-CODE:
        # with patch as mock_validate:
        #     mock_validate.side_effect = [
        #         Result(success=False, error="hallucination"),
        #         Result(success=True, data=None),
        #     ]
        #     # Should retry once
        pass

    def test_retry_logic_uses_exponential_backoff(self):
        """Uses exponential backoff between retries."""
        # PSEUDO-CODE:
        # with patch('time.sleep') as mock_sleep:
        #     # Trigger retries
        #     # Assert sleep called with [1.0, 2.0]
        #     assert mock_sleep.call_count >= 1
        pass
```

### Verification Commands

```bash
# Format code
uv run ruff format src/backend/careervp/logic/

# Check for style issues
uv run ruff check --fix src/backend/careervp/logic/

# Type check with strict mode
uv run mypy src/backend/careervp/logic/ --strict

# Run logic tests
uv run pytest tests/logic/test_tailoring_logic.py -v

# Expected output:
# ===== test session starts =====
# tests/logic/test_tailoring_logic.py::TestInputAggregation PASSED (3 tests)
# tests/logic/test_tailoring_logic.py::TestImmutableFactExtraction PASSED (4 tests)
# ... [25-30 total tests]
# ===== 25-30 passed in X.XXs =====
```

### Expected Test Results

```
tests/logic/test_tailoring_logic.py PASSED

Input Aggregation: 3 PASSED
Immutable Fact Extraction: 4 PASSED
Keyword Alignment: 4 PASSED
Anti-Detection Rules: 4 PASSED
FVS Validation: 4 PASSED
Retry Logic: 3 PASSED
Error Handling: 3 PASSED

Total: 25-30 tests passing
Type checking: 0 errors, 0 warnings
Code coverage: >90% for logic module
```

### Zero-Hallucination Checklist

- [ ] `_extract_immutable_facts()` captures all IMMUTABLE tier fields
- [ ] `_validate_tailored_output()` checks all immutable facts preserved
- [ ] No hallucinated skills, certifications, or dates allowed
- [ ] All 8 anti-detection patterns checked
- [ ] Retry logic has exponential backoff (1s, 2s, 4s)
- [ ] MAX_RETRIES = 3 enforced
- [ ] Metrics emitted for all paths
- [ ] Logging includes user_id, application_id, job_id
- [ ] Result[T] pattern used throughout
- [ ] All test cases pass without warnings

### Acceptance Criteria

- [ ] `tailor_cv()` returns `Result[TailoredCVData]` in all cases
- [ ] FVS validation catches all hallucinations
- [ ] Retry logic works with exponential backoff
- [ ] Immutable facts preserved exactly
- [ ] Anti-detection rules applied to all content
- [ ] Metrics emitted: CVTailoringRequests, CVTailoringLatency, CVTailoringErrors
- [ ] Optional gap_analysis parameter accepted for Phase 11
- [ ] 25-30 tests all passing
- [ ] Type checking passes with `mypy --strict`
- [ ] Code coverage >90%

---

### Verification & Compliance

1. Run `python src/backend/scripts/validate_naming.py --path src/backend/careervp/logic --strict`
2. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
3. Run `uv run pytest tests/logic/test_tailoring_logic.py -v --cov`
4. If any logic is incorrect or test fails, report a **BLOCKING ISSUE** and exit.
