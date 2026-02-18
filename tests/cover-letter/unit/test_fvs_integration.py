"""Integration tests for FVS checks inside the cover-letter pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from careervp.logic.cover_letter import generate_cover_letter
from careervp.logic.fvs_validator import AntiAIPatternResult
from careervp.models.cover_letter import CoverLetterRequest, CoverLetterResponse
from careervp.models.cv import ContactInfo, UserCV, WorkExperience
from careervp.models.result import ResultCode
from careervp.models.vpr import VPRResponse


def _build_request() -> CoverLetterRequest:
    return CoverLetterRequest(
        user_id="user-1",
        cv_id="cv-1",
        job_id="job-1",
        vpr_id="vpr-1",
        company_name="Acme Corp",
        job_title="Senior Software Engineer",
        job_description="Lead backend systems, mentor engineers, and drive delivery quality.",
    )


def _build_user_cv() -> UserCV:
    return UserCV(
        user_id="user-1",
        cv_id="cv-1",
        full_name="Alex Candidate",
        language="en",
        contact_info=ContactInfo(email="alex@example.com", phone="555-101-2020"),
        experience=[
            WorkExperience(
                company="Acme Corp",
                role="Software Engineer",
                dates="2021-2024",
                achievements=["Improved service uptime by 35%"],
                technologies=["Python", "AWS"],
            )
        ],
        education=[],
        certifications=[],
        skills=["Python", "AWS", "Leadership"],
        top_achievements=["Reduced incident volume by 22%"],
        created_at=datetime.now(timezone.utc),
    )


def _build_vpr_response() -> VPRResponse:
    return VPRResponse(success=True)


@pytest.mark.asyncio
async def test_fvs_integrates_with_cover_letter_pipeline() -> None:
    request = _build_request()
    user_cv = _build_user_cv()
    vpr = _build_vpr_response()
    llm_text = (
        "Dear Hiring Manager,\n\n"
        "I am excited to apply for the Senior Software Engineer role at Acme Corp.\n\n"
        "In my recent role, I led reliability improvements that increased uptime and delivery speed.\n\n"
        "Thank you for your time and consideration."
    )

    with (
        patch("careervp.logic.cover_letter.LLMClient") as mock_llm_cls,
        patch("careervp.logic.cover_letter.check_anti_ai_patterns") as mock_anti_ai,
    ):
        mock_llm_instance = Mock()
        mock_llm_instance.generate = AsyncMock(return_value={"text": llm_text})
        mock_llm_cls.return_value = mock_llm_instance
        mock_anti_ai.return_value = AntiAIPatternResult(score=9.4, issues=[])

        result = await generate_cover_letter(request=request, user_cv=user_cv, vpr=vpr)

    assert result.success is True
    assert result.code == ResultCode.COVER_LETTER_GENERATED
    assert isinstance(result.data, CoverLetterResponse)
    mock_anti_ai.assert_called_once()


@pytest.mark.asyncio
async def test_rejects_cover_letter_below_thresholds() -> None:
    request = _build_request()
    user_cv = _build_user_cv()
    vpr = _build_vpr_response()
    llm_text = (
        "I leverage robust synergy to streamline outcomes at scale. "
        "I leverage robust synergy to streamline outcomes at scale. "
        "I leverage robust synergy to streamline outcomes at scale."
    )

    with (
        patch("careervp.logic.cover_letter.LLMClient") as mock_llm_cls,
        patch("careervp.logic.cover_letter.check_anti_ai_patterns") as mock_anti_ai,
    ):
        mock_llm_instance = Mock()
        mock_llm_instance.generate = AsyncMock(return_value={"text": llm_text})
        mock_llm_cls.return_value = mock_llm_instance
        mock_anti_ai.return_value = AntiAIPatternResult(
            score=8.2,
            issues=["Pattern 1 - banned terms detected: leverage, robust, synergy"],
        )

        result = await generate_cover_letter(request=request, user_cv=user_cv, vpr=vpr)

    assert result.success is False
    assert result.code == ResultCode.FVS_VALIDATION_FAILED
    assert result.error is not None
    assert "Regenerate cover letter" in result.error
