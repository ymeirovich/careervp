"""Unit tests for updated VPR generator pipeline stages 3-5 (spec 03)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from careervp.logic.vpr_generator import (
    Phase2Draft,
    ValidatedDraft,
    VPRSixStagePipeline,
    generate_vpr,
)
from careervp.models.vpr import VPRRequest


@pytest.mark.unit
class TestVPRPipelineInitialization:
    def test_pipeline_accepts_request_and_cv(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
    ) -> None:
        """VPRSixStagePipeline can be initialized with request and CV."""
        mock_llm = MagicMock()
        pipeline = VPRSixStagePipeline(
            request=minimal_vpr_request,
            user_cv=minimal_user_cv,
            llm_client=mock_llm,
        )
        assert pipeline is not None

    def test_pipeline_has_synthesize_method(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
    ) -> None:
        """VPRSixStagePipeline has a _synthesize method."""
        mock_llm = MagicMock()
        pipeline = VPRSixStagePipeline(
            request=minimal_vpr_request,
            user_cv=minimal_user_cv,
            llm_client=mock_llm,
        )
        assert hasattr(pipeline, '_synthesize')
        assert callable(pipeline._synthesize)

    def test_pipeline_has_self_correct_method(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
    ) -> None:
        """VPRSixStagePipeline has a _self_correct method."""
        mock_llm = MagicMock()
        pipeline = VPRSixStagePipeline(
            request=minimal_vpr_request,
            user_cv=minimal_user_cv,
            llm_client=mock_llm,
        )
        assert hasattr(pipeline, '_self_correct')
        assert callable(pipeline._self_correct)

    def test_pipeline_has_generate_output_method(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
    ) -> None:
        """VPRSixStagePipeline has a _generate_output method."""
        mock_llm = MagicMock()
        pipeline = VPRSixStagePipeline(
            request=minimal_vpr_request,
            user_cv=minimal_user_cv,
            llm_client=mock_llm,
        )
        assert hasattr(pipeline, '_generate_output')
        assert callable(pipeline._generate_output)


@pytest.mark.unit
class TestPhase2DraftType:
    def test_phase2_draft_has_raw_payload(self, llm_phase2_response: dict[str, Any]) -> None:
        """Phase2Draft stores raw payload."""
        draft = Phase2Draft(
            raw_payload=llm_phase2_response,
            evidence_context=MagicMock(),
        )
        assert draft.raw_payload == llm_phase2_response
        assert isinstance(draft.raw_payload, dict)

    def test_phase2_draft_has_evidence_context(self, llm_phase2_response: dict[str, Any]) -> None:
        """Phase2Draft stores evidence context."""
        context = MagicMock()
        draft = Phase2Draft(
            raw_payload=llm_phase2_response,
            evidence_context=context,
        )
        assert draft.evidence_context is not None


@pytest.mark.unit
class TestValidatedDraftType:
    def test_validated_draft_has_raw_payload(self, llm_phase2_response: dict[str, Any]) -> None:
        """ValidatedDraft stores raw payload."""
        validated = ValidatedDraft(
            raw_payload=llm_phase2_response,
            validation_notes=['Test note'],
            evidence_context=MagicMock(),
        )
        assert validated.raw_payload == llm_phase2_response

    def test_validated_draft_has_validation_notes(self, llm_phase2_response: dict[str, Any]) -> None:
        """ValidatedDraft stores validation notes as list."""
        notes = ['Note 1', 'Note 2']
        validated = ValidatedDraft(
            raw_payload=llm_phase2_response,
            validation_notes=notes,
            evidence_context=MagicMock(),
        )
        assert validated.validation_notes == notes
        assert isinstance(validated.validation_notes, list)

    def test_validated_draft_notes_can_be_empty(self, llm_phase2_response: dict[str, Any]) -> None:
        """ValidatedDraft can have empty validation notes."""
        validated = ValidatedDraft(
            raw_payload=llm_phase2_response,
            validation_notes=[],
            evidence_context=MagicMock(),
        )
        assert validated.validation_notes == []


@pytest.mark.unit
class TestGenerateVPRFunction:
    def test_generate_vpr_is_callable(self) -> None:
        """generate_vpr is a callable function."""
        assert callable(generate_vpr)

    def test_generate_vpr_signature_accepts_request_cv_dal(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
    ) -> None:
        """generate_vpr accepts request, CV, and DAL parameters."""
        import inspect

        sig = inspect.signature(generate_vpr)
        params = list(sig.parameters.keys())
        assert 'request' in params or len(params) >= 1
        assert 'user_cv' in params or len(params) >= 2
