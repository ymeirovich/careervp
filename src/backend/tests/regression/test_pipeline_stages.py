"""Regression tests — VPR pipeline stage contracts must not change."""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.vpr_generator import (
    MAX_STAGE6_RETRIES,
    VPRSixStagePipeline,
    generate_vpr,
)


@pytest.mark.regression
class TestPipelineStageContracts:
    def test_pipeline_has_analyze_input_method(self) -> None:
        """Stage 1 (_analyze_input) must remain a method on VPRSixStagePipeline."""
        assert hasattr(VPRSixStagePipeline, '_analyze_input'), (
            '_analyze_input removed from VPRSixStagePipeline. Stage 1 is the rule-based CV analysis step — it must stay.'
        )
        assert callable(VPRSixStagePipeline._analyze_input)

    def test_pipeline_has_extract_evidence_method(self) -> None:
        """Stage 2 (_extract_evidence) must remain on VPRSixStagePipeline."""
        assert hasattr(VPRSixStagePipeline, '_extract_evidence'), (
            '_extract_evidence removed from VPRSixStagePipeline. Stage 2 is the rule-based evidence matching step — it must stay.'
        )
        assert callable(VPRSixStagePipeline._extract_evidence)

    def test_stage1_analyze_input_does_not_call_llm(
        self,
        minimal_vpr_request: Any,
        minimal_user_cv: Any,
    ) -> None:
        """Stage 1 is rule-based — it must never call LLMClient."""
        pipeline = VPRSixStagePipeline(
            request=minimal_vpr_request,
            user_cv=minimal_user_cv,
            llm_client=MagicMock(),
        )

        with patch('careervp.logic.vpr_generator.LLMClient') as mock_llm_cls:
            # Run Stage 1 only
            analysis_result = pipeline._analyze_input(minimal_user_cv, minimal_vpr_request.job_posting)

        # LLMClient must NOT have been instantiated or called
        mock_llm_cls.assert_not_called()
        assert analysis_result is not None

    def test_stage2_extract_evidence_does_not_call_llm(
        self,
        minimal_vpr_request: Any,
        minimal_user_cv: Any,
    ) -> None:
        """Stage 2 is rule-based — it must never call LLMClient."""
        pipeline = VPRSixStagePipeline(
            request=minimal_vpr_request,
            user_cv=minimal_user_cv,
            llm_client=MagicMock(),
        )
        # First run Stage 1 to get its output
        analysis_result = pipeline._analyze_input(minimal_user_cv, minimal_vpr_request.job_posting)

        with patch('careervp.logic.vpr_generator.LLMClient') as mock_llm_cls:
            evidence_result = pipeline._extract_evidence(analysis_result)

        mock_llm_cls.assert_not_called()
        assert evidence_result is not None

    def test_generate_vpr_function_signature_unchanged(self) -> None:
        """generate_vpr() public function must accept (request, user_cv, dal) in that order."""
        sig = inspect.signature(generate_vpr)
        params = list(sig.parameters.keys())
        # Must have these 3 parameters (in some order, positional)
        assert 'request' in params, "generate_vpr() missing 'request' parameter"
        assert 'user_cv' in params, "generate_vpr() missing 'user_cv' parameter"
        assert 'dal' in params, "generate_vpr() missing 'dal' parameter"
        # No more than 3 required positional parameters
        required_params = [
            p
            for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        assert len(required_params) == 3, (
            f'generate_vpr() has {len(required_params)} required params, expected 3. Params: {[p.name for p in required_params]}'
        )

    def test_max_stage6_retries_is_3(self) -> None:
        """MAX_STAGE6_RETRIES must remain 1 after the quality-warning fallback change."""
        assert MAX_STAGE6_RETRIES == 1, (
            f'MAX_STAGE6_RETRIES changed to {MAX_STAGE6_RETRIES}. Increasing retries multiplies LLM cost; decreasing reduces quality assurance.'
        )
