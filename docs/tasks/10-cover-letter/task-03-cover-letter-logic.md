# Task 10.3: Cover Letter Generation Logic

**Status:** Pending
**Spec Reference:** [docs/specs/cover-letter/COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md)
**Depends On:** Task 10.1 (Validation), Task 10.8 (Models), Task 10.4 (Prompt)
**Blocking:** Task 10.6 (Handler)
**Complexity:** High
**Duration:** 3 hours
**Test File:** `tests/cover-letter/unit/test_cover_letter_logic.py` (25-30 tests)

## Overview

Implement core cover letter generation logic using Claude Haiku 4.5. This is the HIGH COMPLEXITY task that synthesizes VPR, tailored CV, and gap responses into a personalized cover letter with quality scoring.

## Todo

### Logic Implementation

- [ ] Create `src/backend/careervp/logic/cover_letter_generator.py`
- [ ] Implement `generate_cover_letter()` main function
- [ ] Implement `calculate_quality_score()` with 40% personalization + 35% relevance + 25% tone
- [ ] Implement `extract_vpr_context()` to synthesize VPR data
- [ ] Implement `build_personalization_context()` for accomplishment highlighting
- [ ] Implement quality score thresholds and Sonnet fallback logic
- [ ] Add timeout handling with asyncio.wait_for (300s)
- [ ] Add retry logic with exponential backoff

### Test Implementation

- [ ] Create `tests/cover-letter/unit/test_cover_letter_logic.py`
- [ ] Test `generate_cover_letter` success path
- [ ] Test `generate_cover_letter` with CV not found
- [ ] Test `generate_cover_letter` with VPR not found
- [ ] Test `calculate_quality_score` with various inputs
- [ ] Test quality score thresholds
- [ ] Test LLM timeout handling
- [ ] Test Sonnet fallback when quality < 0.70

### Validation & Formatting

- [ ] Run `uv run ruff format careervp/logic/cover_letter_generator.py`
- [ ] Run `uv run ruff check --fix careervp/logic/`
- [ ] Run `uv run mypy careervp/logic/cover_letter_generator.py --strict`
- [ ] Run `uv run pytest tests/cover-letter/unit/test_cover_letter_logic.py -v`

---

## Codex Implementation Guide

### File Path

`src/backend/careervp/logic/cover_letter_generator.py`

### Constants

```python
"""Constants for cover letter generation."""

# Quality score weights (must sum to 1.0)
PERSONALIZATION_WEIGHT = 0.40
RELEVANCE_WEIGHT = 0.35
TONE_WEIGHT = 0.25

# Quality thresholds
QUALITY_EXCELLENT = 0.80  # Feature prominently
QUALITY_GOOD = 0.70       # Acceptable, no retry
QUALITY_ACCEPTABLE = 0.60 # Borderline, may retry
QUALITY_RETRY_THRESHOLD = 0.70  # Below this, retry with Sonnet

# LLM configuration
DEFAULT_TIMEOUT_SECONDS = 300
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0

# Word count
TARGET_WORD_COUNT_MIN = 250
TARGET_WORD_COUNT_MAX = 400
```

### Key Implementation

```python
"""
Cover letter generation logic.

Synthesizes VPR, tailored CV, and gap responses into personalized cover letters
using Claude Haiku 4.5 with quality scoring and Sonnet fallback.
"""

import asyncio
from typing import Optional
from datetime import datetime

from aws_lambda_powertools import Logger, Tracer

from careervp.models.result import Result, ResultCode
from careervp.models.cover_letter_models import (
    GenerateCoverLetterRequest,
    TailoredCoverLetter,
    CoverLetterPreferences,
)
from careervp.logic.prompts.cover_letter_prompt import (
    build_system_prompt,
    build_user_prompt,
)
from careervp.llm.llm_client import LLMClient, TaskMode
from careervp.dal.dynamo_dal_handler import DynamoDalHandler

logger = Logger()
tracer = Tracer()


@tracer.capture_method
async def generate_cover_letter(
    request: GenerateCoverLetterRequest,
    user_id: str,
    llm_client: LLMClient,
    dal: DynamoDalHandler,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Result[TailoredCoverLetter]:
    """Generate personalized cover letter using LLM.

    Args:
        request: Cover letter generation request
        user_id: Authenticated user ID
        llm_client: LLM client for generation
        dal: DAL handler for data retrieval
        timeout: Max seconds for LLM call

    Returns:
        Result with TailoredCoverLetter or error
    """
    try:
        # Step 1: Retrieve master CV
        logger.info("Retrieving master CV", cv_id=request.cv_id)
        cv_result = await dal.get_cv_by_id(request.cv_id, user_id)
        if not cv_result.success:
            return Result.failure(
                error=f"CV not found: {request.cv_id}",
                code=ResultCode.CV_NOT_FOUND,
            )

        # Step 2: Retrieve VPR (required for personalization)
        logger.info("Retrieving VPR", cv_id=request.cv_id, job_id=request.job_id)
        vpr_result = await dal.get_vpr_artifact(request.cv_id, request.job_id)
        if not vpr_result.success:
            return Result.failure(
                error="VPR not found - generate VPR first before cover letter",
                code=ResultCode.VPR_NOT_FOUND,
            )

        # Step 3: Retrieve tailored CV (optional but recommended)
        tailored_cv_result = await dal.get_tailored_cv_artifact(
            request.cv_id, request.job_id
        )
        tailored_cv = tailored_cv_result.data if tailored_cv_result.success else None

        # Step 4: Retrieve gap responses (optional)
        gap_responses_result = await dal.get_gap_responses(
            request.cv_id, request.job_id
        )
        gap_responses = gap_responses_result.data if gap_responses_result.success else []

        # Step 5: Build personalization context
        context = build_personalization_context(
            cv=cv_result.data,
            vpr=vpr_result.data,
            tailored_cv=tailored_cv,
            gap_responses=gap_responses,
        )

        # Step 6: Build prompts
        preferences = request.preferences or CoverLetterPreferences()
        system_prompt = build_system_prompt(preferences)
        user_prompt = build_user_prompt(
            context=context,
            company_name=request.company_name,
            job_title=request.job_title,
            preferences=preferences,
        )

        # Step 7: Generate with Haiku first
        logger.info("Generating cover letter with Haiku")
        llm_response = await asyncio.wait_for(
            llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                task_mode=TaskMode.TEMPLATE,
                model="claude-haiku-4-5",
            ),
            timeout=timeout,
        )

        # Step 8: Calculate quality score
        quality_scores = calculate_quality_score(
            content=llm_response.content,
            context=context,
            preferences=preferences,
        )
        overall_score = (
            PERSONALIZATION_WEIGHT * quality_scores["personalization"] +
            RELEVANCE_WEIGHT * quality_scores["relevance"] +
            TONE_WEIGHT * quality_scores["tone"]
        )

        # Step 9: Retry with Sonnet if quality too low
        if overall_score < QUALITY_RETRY_THRESHOLD:
            logger.warning(
                "Quality score below threshold, retrying with Sonnet",
                score=overall_score,
            )
            llm_response = await asyncio.wait_for(
                llm_client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    task_mode=TaskMode.TEMPLATE,
                    model="claude-sonnet-4-5",
                ),
                timeout=timeout,
            )
            # Recalculate quality score
            quality_scores = calculate_quality_score(
                content=llm_response.content,
                context=context,
                preferences=preferences,
            )
            overall_score = (
                PERSONALIZATION_WEIGHT * quality_scores["personalization"] +
                RELEVANCE_WEIGHT * quality_scores["relevance"] +
                TONE_WEIGHT * quality_scores["tone"]
            )

        # Step 10: Create TailoredCoverLetter
        cover_letter = TailoredCoverLetter(
            cover_letter_id=f"cl_{request.cv_id}_{request.job_id}_{int(datetime.now().timestamp())}",
            cv_id=request.cv_id,
            job_id=request.job_id,
            user_id=user_id,
            company_name=request.company_name,
            job_title=request.job_title,
            content=llm_response.content,
            word_count=len(llm_response.content.split()),
            personalization_score=quality_scores["personalization"],
            relevance_score=quality_scores["relevance"],
            tone_score=quality_scores["tone"],
            generated_at=datetime.now(),
        )

        logger.info(
            "Cover letter generated successfully",
            quality_score=overall_score,
            word_count=cover_letter.word_count,
        )

        return Result.success(
            data=cover_letter,
            code=ResultCode.COVER_LETTER_GENERATED_SUCCESS,
        )

    except asyncio.TimeoutError:
        logger.error("LLM request timed out", timeout=timeout)
        return Result.failure(
            error=f"Cover letter generation timed out after {timeout}s",
            code=ResultCode.CV_LETTER_GENERATION_TIMEOUT,
        )
    except Exception as e:
        logger.exception("Unexpected error in cover letter generation")
        return Result.failure(
            error=str(e),
            code=ResultCode.INTERNAL_ERROR,
        )


def calculate_quality_score(
    content: str,
    context: dict,
    preferences: CoverLetterPreferences,
) -> dict[str, float]:
    """Calculate quality scores for generated cover letter.

    Args:
        content: Generated cover letter text
        context: Personalization context
        preferences: User preferences

    Returns:
        Dict with personalization, relevance, and tone scores (0.0-1.0)
    """
    return {
        "personalization": _calculate_personalization_score(content, context),
        "relevance": _calculate_relevance_score(content, context),
        "tone": _calculate_tone_score(content, preferences),
    }


def _calculate_personalization_score(content: str, context: dict) -> float:
    """Score based on specific accomplishments cited from VPR."""
    # Check for VPR accomplishments mentioned in content
    accomplishments = context.get("accomplishments", [])
    if not accomplishments:
        return 0.5  # Neutral if no accomplishments available

    mentioned = sum(
        1 for acc in accomplishments
        if any(keyword in content.lower() for keyword in acc.get("keywords", []))
    )
    return min(1.0, mentioned / max(len(accomplishments), 1) * 1.5)


def _calculate_relevance_score(content: str, context: dict) -> float:
    """Score based on job requirements addressed."""
    requirements = context.get("job_requirements", [])
    if not requirements:
        return 0.5

    addressed = sum(
        1 for req in requirements
        if req.lower() in content.lower()
    )
    return min(1.0, addressed / max(len(requirements), 1))


def _calculate_tone_score(content: str, preferences: CoverLetterPreferences) -> float:
    """Score based on tone matching preferences."""
    tone = preferences.tone

    # Tone indicators
    professional_indicators = ["experience", "expertise", "professional", "proven"]
    enthusiastic_indicators = ["excited", "passionate", "eager", "thrilled"]
    technical_indicators = ["implemented", "architected", "designed", "engineered"]

    content_lower = content.lower()

    if tone == "professional":
        matches = sum(1 for ind in professional_indicators if ind in content_lower)
        return min(1.0, matches / len(professional_indicators) * 2)
    elif tone == "enthusiastic":
        matches = sum(1 for ind in enthusiastic_indicators if ind in content_lower)
        return min(1.0, matches / len(enthusiastic_indicators) * 2)
    elif tone == "technical":
        matches = sum(1 for ind in technical_indicators if ind in content_lower)
        return min(1.0, matches / len(technical_indicators) * 2)

    return 0.7  # Default


def build_personalization_context(
    cv: "UserCV",
    vpr: "VPRResponse",
    tailored_cv: Optional["TailoredCV"],
    gap_responses: list,
) -> dict:
    """Build context dict for prompt personalization.

    Args:
        cv: Master CV
        vpr: Value Proposition Report
        tailored_cv: Tailored CV (optional)
        gap_responses: Gap analysis responses (optional)

    Returns:
        Context dict with accomplishments, requirements, skills
    """
    context = {
        "accomplishments": [],
        "job_requirements": [],
        "skills": [],
        "experience_highlights": [],
    }

    # Extract from VPR
    if vpr:
        context["accomplishments"] = [
            {"text": acc.text, "keywords": acc.keywords}
            for acc in getattr(vpr, "accomplishments", [])
        ]
        context["job_requirements"] = getattr(vpr, "job_requirements", [])

    # Extract from CV
    if cv:
        context["skills"] = getattr(cv, "skills", [])
        context["experience_highlights"] = [
            exp.highlights for exp in getattr(cv, "experience", [])
        ]

    # Add gap response context
    if gap_responses:
        context["gap_responses"] = [
            {"question": gr.question, "response": gr.response}
            for gr in gap_responses
        ]

    return context
```

---

## Test Implementation

### test_cover_letter_logic.py

```python
"""Unit tests for cover letter generation logic."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from careervp.logic.cover_letter_generator import (
    generate_cover_letter,
    calculate_quality_score,
    build_personalization_context,
    QUALITY_RETRY_THRESHOLD,
)
from careervp.models.result import Result, ResultCode
from careervp.models.cover_letter_models import (
    GenerateCoverLetterRequest,
    CoverLetterPreferences,
)


class TestGenerateCoverLetter:
    """Tests for generate_cover_letter function."""

    @pytest.fixture
    def mock_dal(self):
        """Mock DAL handler."""
        dal = Mock()
        dal.get_cv_by_id = AsyncMock()
        dal.get_vpr_artifact = AsyncMock()
        dal.get_tailored_cv_artifact = AsyncMock()
        dal.get_gap_responses = AsyncMock()
        return dal

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client."""
        client = Mock()
        client.generate = AsyncMock()
        return client

    @pytest.fixture
    def sample_request(self):
        """Sample cover letter request."""
        return GenerateCoverLetterRequest(
            cv_id="cv_123",
            job_id="job_456",
            company_name="TechCorp",
            job_title="Senior Engineer",
        )

    @pytest.mark.asyncio
    async def test_generate_cover_letter_success(
        self, mock_dal, mock_llm_client, sample_request
    ):
        """Test successful cover letter generation."""
        # Arrange
        mock_dal.get_cv_by_id.return_value = Result.success(data=Mock())
        mock_dal.get_vpr_artifact.return_value = Result.success(data=Mock())
        mock_dal.get_tailored_cv_artifact.return_value = Result.success(data=Mock())
        mock_dal.get_gap_responses.return_value = Result.success(data=[])
        mock_llm_client.generate.return_value = Mock(
            content="I am excited to apply for the Senior Engineer position at TechCorp..."
        )

        # Act
        result = await generate_cover_letter(
            request=sample_request,
            user_id="user_789",
            llm_client=mock_llm_client,
            dal=mock_dal,
        )

        # Assert
        assert result.success is True
        assert result.code == ResultCode.COVER_LETTER_GENERATED_SUCCESS
        assert result.data.company_name == "TechCorp"
        assert result.data.job_title == "Senior Engineer"

    @pytest.mark.asyncio
    async def test_generate_cover_letter_cv_not_found(
        self, mock_dal, mock_llm_client, sample_request
    ):
        """Test cover letter generation with CV not found."""
        mock_dal.get_cv_by_id.return_value = Result.failure(
            error="Not found", code=ResultCode.CV_NOT_FOUND
        )

        result = await generate_cover_letter(
            request=sample_request,
            user_id="user_789",
            llm_client=mock_llm_client,
            dal=mock_dal,
        )

        assert result.success is False
        assert result.code == ResultCode.CV_NOT_FOUND

    @pytest.mark.asyncio
    async def test_generate_cover_letter_vpr_not_found(
        self, mock_dal, mock_llm_client, sample_request
    ):
        """Test cover letter generation with VPR not found."""
        mock_dal.get_cv_by_id.return_value = Result.success(data=Mock())
        mock_dal.get_vpr_artifact.return_value = Result.failure(
            error="Not found", code=ResultCode.VPR_NOT_FOUND
        )

        result = await generate_cover_letter(
            request=sample_request,
            user_id="user_789",
            llm_client=mock_llm_client,
            dal=mock_dal,
        )

        assert result.success is False
        assert result.code == ResultCode.VPR_NOT_FOUND

    @pytest.mark.asyncio
    async def test_generate_cover_letter_timeout(
        self, mock_dal, mock_llm_client, sample_request
    ):
        """Test cover letter generation timeout."""
        mock_dal.get_cv_by_id.return_value = Result.success(data=Mock())
        mock_dal.get_vpr_artifact.return_value = Result.success(data=Mock())
        mock_dal.get_tailored_cv_artifact.return_value = Result.success(data=Mock())
        mock_dal.get_gap_responses.return_value = Result.success(data=[])
        mock_llm_client.generate.side_effect = asyncio.TimeoutError()

        result = await generate_cover_letter(
            request=sample_request,
            user_id="user_789",
            llm_client=mock_llm_client,
            dal=mock_dal,
            timeout=1,
        )

        assert result.success is False
        assert result.code == ResultCode.CV_LETTER_GENERATION_TIMEOUT

    @pytest.mark.asyncio
    async def test_generate_cover_letter_sonnet_fallback(
        self, mock_dal, mock_llm_client, sample_request
    ):
        """Test fallback to Sonnet when quality score is low."""
        mock_dal.get_cv_by_id.return_value = Result.success(data=Mock())
        mock_dal.get_vpr_artifact.return_value = Result.success(data=Mock(
            accomplishments=[], job_requirements=[]
        ))
        mock_dal.get_tailored_cv_artifact.return_value = Result.failure(
            error="Not found", code=ResultCode.NOT_FOUND
        )
        mock_dal.get_gap_responses.return_value = Result.success(data=[])

        # First call returns low quality, second returns better
        mock_llm_client.generate.side_effect = [
            Mock(content="Generic letter"),  # Low quality
            Mock(content="I am excited to apply with my proven experience..."),  # Better
        ]

        with patch(
            "careervp.logic.cover_letter_generator.calculate_quality_score"
        ) as mock_score:
            mock_score.side_effect = [
                {"personalization": 0.3, "relevance": 0.3, "tone": 0.3},  # Below threshold
                {"personalization": 0.8, "relevance": 0.8, "tone": 0.8},  # Above threshold
            ]

            result = await generate_cover_letter(
                request=sample_request,
                user_id="user_789",
                llm_client=mock_llm_client,
                dal=mock_dal,
            )

        assert result.success is True
        assert mock_llm_client.generate.call_count == 2


class TestCalculateQualityScore:
    """Tests for quality score calculation."""

    def test_quality_score_high_personalization(self):
        """Test high personalization score when accomplishments mentioned."""
        content = "Led team of 10 engineers to deliver project on time."
        context = {
            "accomplishments": [
                {"text": "Led team", "keywords": ["led", "team", "engineers"]},
            ],
            "job_requirements": ["leadership"],
        }
        preferences = CoverLetterPreferences(tone="professional")

        scores = calculate_quality_score(content, context, preferences)

        assert scores["personalization"] > 0.7

    def test_quality_score_low_personalization(self):
        """Test low personalization score when no accomplishments mentioned."""
        content = "I am writing to apply for this position."
        context = {
            "accomplishments": [
                {"text": "Built ML pipeline", "keywords": ["ml", "pipeline", "data"]},
            ],
            "job_requirements": ["machine learning"],
        }
        preferences = CoverLetterPreferences(tone="professional")

        scores = calculate_quality_score(content, context, preferences)

        assert scores["personalization"] < 0.5

    def test_quality_score_professional_tone(self):
        """Test tone score for professional tone."""
        content = "With my proven expertise and professional experience..."
        context = {"accomplishments": [], "job_requirements": []}
        preferences = CoverLetterPreferences(tone="professional")

        scores = calculate_quality_score(content, context, preferences)

        assert scores["tone"] > 0.5

    def test_quality_score_enthusiastic_tone(self):
        """Test tone score for enthusiastic tone."""
        content = "I am excited and passionate about this opportunity!"
        context = {"accomplishments": [], "job_requirements": []}
        preferences = CoverLetterPreferences(tone="enthusiastic")

        scores = calculate_quality_score(content, context, preferences)

        assert scores["tone"] > 0.5

    def test_quality_score_technical_tone(self):
        """Test tone score for technical tone."""
        content = "I implemented and architected distributed systems..."
        context = {"accomplishments": [], "job_requirements": []}
        preferences = CoverLetterPreferences(tone="technical")

        scores = calculate_quality_score(content, context, preferences)

        assert scores["tone"] > 0.5


class TestBuildPersonalizationContext:
    """Tests for context building."""

    def test_build_context_with_all_inputs(self):
        """Test context building with all inputs present."""
        cv = Mock(skills=["Python", "AWS"], experience=[Mock(highlights=["Led team"])])
        vpr = Mock(accomplishments=[Mock(text="Built API", keywords=["api"])], job_requirements=["Python"])
        tailored_cv = Mock()
        gap_responses = [Mock(question="Q1", response="R1")]

        context = build_personalization_context(cv, vpr, tailored_cv, gap_responses)

        assert "accomplishments" in context
        assert "job_requirements" in context
        assert "skills" in context
        assert "gap_responses" in context

    def test_build_context_with_minimal_inputs(self):
        """Test context building with minimal inputs."""
        cv = Mock(skills=[], experience=[])
        vpr = Mock(accomplishments=[], job_requirements=[])

        context = build_personalization_context(cv, vpr, None, [])

        assert context["accomplishments"] == []
        assert context["job_requirements"] == []
```

---

## Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Format
uv run ruff format careervp/logic/cover_letter_generator.py

# Lint
uv run ruff check --fix careervp/logic/cover_letter_generator.py

# Type check
uv run mypy careervp/logic/cover_letter_generator.py --strict

# Run tests
uv run pytest tests/cover-letter/unit/test_cover_letter_logic.py -v

# Expected: 27 tests PASSED
```

---

## Completion Criteria

- [ ] `generate_cover_letter()` function implemented
- [ ] `calculate_quality_score()` implemented with correct weights
- [ ] `build_personalization_context()` implemented
- [ ] Sonnet fallback logic working
- [ ] Timeout handling working
- [ ] All 27 tests passing
- [ ] ruff format passes
- [ ] mypy --strict passes

---

## Common Pitfalls

### Pitfall 1: Missing VPR Check
**Problem:** Generating cover letter without VPR results in generic content.
**Solution:** Always return VPR_NOT_FOUND if VPR doesn't exist.

### Pitfall 2: Quality Score Weights Don't Sum to 1.0
**Problem:** Incorrect weighting produces invalid overall scores.
**Solution:** Verify 0.40 + 0.35 + 0.25 = 1.0 exactly.

### Pitfall 3: Not Handling Optional Tailored CV
**Problem:** Crashing when tailored CV is None.
**Solution:** Check `if tailored_cv_result.success` before accessing data.

---

## References

- [COVER_LETTER_DESIGN.md](../../architecture/COVER_LETTER_DESIGN.md) - Quality scoring algorithm
- [vpr_generator.py](../../../src/backend/careervp/logic/vpr_generator.py) - Pattern reference
