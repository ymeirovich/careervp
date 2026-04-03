"""Unit tests for spec 10: optional VPR integration in CV tailoring.

Tests confirm:
  - TailorCVRequest.vpr_id field exists and accepts None or a string
  - build_user_prompt() injects '# VPR Strategic Guide' when vpr is present
  - build_user_prompt() output is unchanged when vpr=None (no regression)
  - VPR JSON content appears in the prompt when injected
  - CVTailoringLogic.tailor_cv() calls dal.get_vpr() when vpr_id is set
  - Failed VPR fetch logs a warning but does not propagate as a VPR error
  - vpr_id absent → dal.get_vpr() is never called

Expected state: RED until spec 10 is implemented. Specifically:
  - TailorCVRequest tests: RED (no vpr_id field yet)
  - build_user_prompt tests: RED (no vpr parameter yet)
  - CVTailoringLogic tests: RED (no VPR fetch in tailor_cv yet)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from careervp.models.cv_tailoring_models import TailorCVRequest
from careervp.models.result import Result, ResultCode

# ── Group 1: TailorCVRequest model ───────────────────────────────────────────


@pytest.mark.unit
class TestTailorCVRequestModel:
    """TailorCVRequest must accept an optional vpr_id field."""

    _JOB = 'Lead platform engineering team for enterprise SaaS product. Minimum 20 chars.'

    def test_vpr_id_field_exists_and_is_accepted(self) -> None:
        req = TailorCVRequest(cv_id='cv-001', job_description=self._JOB, vpr_id='app-001')
        assert req.vpr_id == 'app-001'

    def test_vpr_id_defaults_to_none(self) -> None:
        """Existing callers without vpr_id must not break."""
        req = TailorCVRequest(cv_id='cv-001', job_description=self._JOB)
        assert req.vpr_id is None

    def test_vpr_id_accepts_none_explicitly(self) -> None:
        req = TailorCVRequest(cv_id='cv-001', job_description=self._JOB, vpr_id=None)
        assert req.vpr_id is None


# ── Group 2: build_user_prompt VPR injection ─────────────────────────────────


@pytest.mark.unit
class TestBuildUserPromptVprInjection:
    """build_user_prompt() must inject a VPR Strategic Guide section when vpr is given."""

    def test_vpr_section_header_injected_when_vpr_present(self, minimal_user_cv: Any, minimal_vpr: Any) -> None:
        from careervp.logic.cv_tailoring_prompt import build_user_prompt

        prompt = build_user_prompt(
            cv=minimal_user_cv,
            job_description='Lead platform engineering team for enterprise SaaS.',
            vpr=minimal_vpr,
        )
        assert '# VPR Strategic Guide' in prompt

    def test_vpr_content_serialized_in_prompt(self, minimal_user_cv: Any, minimal_vpr: Any) -> None:
        """A distinctive VPR field must appear in the prompt when vpr is given."""
        from careervp.logic.cv_tailoring_prompt import build_user_prompt

        prompt = build_user_prompt(
            cv=minimal_user_cv,
            job_description='Lead platform engineering team for enterprise SaaS.',
            vpr=minimal_vpr,
        )
        # positioning_statement from conftest minimal_vpr
        assert 'commercial scale' in prompt or 'positioning_statement' in prompt

    def test_no_vpr_section_when_vpr_is_none(self, minimal_user_cv: Any) -> None:
        """No VPR section must appear when vpr=None — no regression for existing callers."""
        from careervp.logic.cv_tailoring_prompt import build_user_prompt

        prompt = build_user_prompt(
            cv=minimal_user_cv,
            job_description='Lead platform engineering team for enterprise SaaS.',
            vpr=None,
        )
        assert '# VPR Strategic Guide' not in prompt

    def test_prompt_identical_with_and_without_none_vpr(self, minimal_user_cv: Any) -> None:
        """Calling with vpr=None must produce the same output as omitting vpr."""
        from careervp.logic.cv_tailoring_prompt import build_user_prompt

        job = 'Lead platform engineering team for enterprise SaaS product systems.'
        prompt_omitted = build_user_prompt(cv=minimal_user_cv, job_description=job)
        prompt_explicit_none = build_user_prompt(cv=minimal_user_cv, job_description=job, vpr=None)
        assert prompt_omitted == prompt_explicit_none


# ── Group 3: CVTailoringLogic VPR fetch behaviour ────────────────────────────


@pytest.mark.unit
class TestCVTailoringLogicVprFetch:
    """CVTailoringLogic.tailor_cv() VPR fetch call contract."""

    _JOB = 'Lead platform engineering team for enterprise SaaS product. 50+ chars of description here.'

    def _make_logic(self, mock_dal: Any) -> Any:
        from careervp.logic.cv_tailoring_logic import CVTailoringLogic

        mock_llm = MagicMock()
        # generate() returns a non-dict so parse_llm_response returns PARSE_ERROR — acceptable
        mock_llm.generate.return_value = None
        return CVTailoringLogic(dal=mock_dal, llm_client=mock_llm)

    def _make_dal(
        self,
        cv: Any,
        *,
        vpr: Any | None = None,
        vpr_fetch_success: bool = True,
    ) -> MagicMock:
        mock_dal = MagicMock()
        mock_dal.get_cv.return_value = cv
        # No cached tailored CV → forces generation path
        mock_dal.get_tailored_cv.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)
        if vpr_fetch_success and vpr is not None:
            mock_dal.get_vpr.return_value = Result(success=True, data=vpr, code=ResultCode.SUCCESS)
        else:
            mock_dal.get_vpr.return_value = Result(
                success=False,
                data=None,
                code='VPR_NOT_FOUND',
                error='VPR not found',
            )
        return mock_dal

    def test_get_vpr_called_with_vpr_id(self, minimal_user_cv: Any, minimal_vpr: Any) -> None:
        """dal.get_vpr() must be called with the request's vpr_id when set."""
        mock_dal = self._make_dal(minimal_user_cv, vpr=minimal_vpr, vpr_fetch_success=True)
        logic = self._make_logic(mock_dal)

        req = TailorCVRequest(cv_id='cv-001', job_description=self._JOB, vpr_id='app-001')
        logic.tailor_cv(req, user_id='user-123')

        mock_dal.get_vpr.assert_called_once_with('app-001')

    def test_get_vpr_not_called_when_vpr_id_absent(self, minimal_user_cv: Any) -> None:
        """dal.get_vpr() must NOT be called when request.vpr_id is None."""
        mock_dal = self._make_dal(minimal_user_cv, vpr_fetch_success=False)
        logic = self._make_logic(mock_dal)

        req = TailorCVRequest(cv_id='cv-001', job_description=self._JOB)
        logic.tailor_cv(req, user_id='user-123')

        mock_dal.get_vpr.assert_not_called()

    def test_vpr_fetch_failure_does_not_produce_vpr_error(self, minimal_user_cv: Any) -> None:
        """A failed VPR fetch must not surface as a VPR-specific error in the result."""
        mock_dal = self._make_dal(minimal_user_cv, vpr=None, vpr_fetch_success=False)
        logic = self._make_logic(mock_dal)

        req = TailorCVRequest(cv_id='cv-001', job_description=self._JOB, vpr_id='app-001')
        result = logic.tailor_cv(req, user_id='user-123')

        # Result may fail (e.g. LLM mock returns None → PARSE_ERROR) but
        # must NOT fail because of the VPR fetch — error must not mention VPR fetch
        if not result.success:
            error_upper = (result.error or '').upper()
            assert 'VPR NOT FOUND' not in error_upper
            assert error_upper != 'VPR_NOT_FOUND'
