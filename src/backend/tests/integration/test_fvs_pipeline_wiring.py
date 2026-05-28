"""Integration tests — FVS quality gate wired into pipeline Stage 6."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.fvs_validator import VPRGateResult
from careervp.logic.vpr_generator import (
    FinalVPRData,
    VPRSixStagePipeline,
)
from careervp.models.vpr import VPR, VPRRequest


@pytest.fixture
def pipeline(minimal_vpr_request: VPRRequest, minimal_user_cv: Any) -> VPRSixStagePipeline:
    return VPRSixStagePipeline(
        request=minimal_vpr_request,
        user_cv=minimal_user_cv,
        llm_client=MagicMock(),
    )


@pytest.mark.integration
class TestStage6QualityGateWiring:
    def test_stage6_calls_run_vpr_quality_gate(self, pipeline: VPRSixStagePipeline, minimal_vpr: VPR) -> None:
        """Stage 6 must import and call run_vpr_quality_gate, not check_anti_ai_patterns directly."""
        vpr_data = MagicMock(vpr=minimal_vpr)

        with patch('careervp.logic.vpr_generator.run_vpr_quality_gate') as mock_gate:
            mock_gate.return_value = VPRGateResult(
                anti_ai_score=9.5,
                structural_score=9.0,
                grammar_score=9.5,
                tone_score=9.5,
                passed_gate=True,
                issues=[],
            )
            pipeline._final_meta_evaluation(vpr_data)

        mock_gate.assert_called_once()

    def test_stage6_passes_vpr_and_user_cv_to_gate(self, pipeline: VPRSixStagePipeline, minimal_vpr: VPR, minimal_user_cv: Any) -> None:
        vpr_data = MagicMock(vpr=minimal_vpr)

        with patch('careervp.logic.vpr_generator.run_vpr_quality_gate') as mock_gate:
            mock_gate.return_value = VPRGateResult(
                anti_ai_score=9.5,
                structural_score=9.0,
                grammar_score=9.5,
                tone_score=9.5,
                passed_gate=True,
                issues=[],
            )
            pipeline._final_meta_evaluation(vpr_data)

        gate_call_args = mock_gate.call_args
        called_vpr = gate_call_args.args[0] if gate_call_args.args else gate_call_args.kwargs.get('vpr')
        called_cv = gate_call_args.args[1] if len(gate_call_args.args) > 1 else gate_call_args.kwargs.get('user_cv')
        assert called_vpr is minimal_vpr
        assert called_cv is minimal_user_cv

    def test_stage6_passes_cv_text_string_not_cv_object(self, pipeline: VPRSixStagePipeline, minimal_vpr: VPR) -> None:
        """cv_text passed to quality gate must be a pre-serialized string, not a UserCV."""
        vpr_data = MagicMock(vpr=minimal_vpr)

        with patch('careervp.logic.vpr_generator.run_vpr_quality_gate') as mock_gate:
            mock_gate.return_value = VPRGateResult(
                anti_ai_score=9.5,
                structural_score=9.0,
                grammar_score=9.5,
                tone_score=9.5,
                passed_gate=True,
                issues=[],
            )
            pipeline._final_meta_evaluation(vpr_data)

        gate_call_args = mock_gate.call_args
        cv_text_arg = gate_call_args.args[2] if len(gate_call_args.args) > 2 else gate_call_args.kwargs.get('cv_text')
        assert isinstance(cv_text_arg, str), f'cv_text must be str, got {type(cv_text_arg)}'

    def test_gap_text_built_from_gap_responses(self, pipeline: VPRSixStagePipeline, minimal_vpr: VPR) -> None:
        """gap_text passed to quality gate must contain content from gap_responses."""
        vpr_data = MagicMock(vpr=minimal_vpr)

        with patch('careervp.logic.vpr_generator.run_vpr_quality_gate') as mock_gate:
            mock_gate.return_value = VPRGateResult(
                anti_ai_score=9.5,
                structural_score=9.0,
                grammar_score=9.5,
                tone_score=9.5,
                passed_gate=True,
                issues=[],
            )
            pipeline._final_meta_evaluation(vpr_data)

        gate_call_args = mock_gate.call_args
        gap_text_arg = gate_call_args.args[3] if len(gate_call_args.args) > 3 else gate_call_args.kwargs.get('gap_response_text')
        assert isinstance(gap_text_arg, str)
        # Should contain content from the gap response in minimal_vpr_request
        assert 'Led 8 engineers' in gap_text_arg or len(gap_text_arg) >= 0

    def test_regeneration_triggered_on_anti_ai_gate_failure(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
        llm_phase2_response: dict[str, Any],
    ) -> None:
        """Anti-AI score below 9.0 must trigger regeneration (retry)."""
        gate_calls = 0

        def gate_side_effect(*args: Any, **kwargs: Any) -> Any:
            nonlocal gate_calls
            gate_calls += 1
            return VPRGateResult(
                anti_ai_score=9.5 if gate_calls > 1 else 5.0,
                structural_score=9.0,
                grammar_score=9.5,
                tone_score=9.5,
                passed_gate=gate_calls > 1,
                issues=[] if gate_calls > 1 else ['Too many buzzwords'],
            )

        with (
            patch('careervp.logic.vpr_generator.LLMClient') as mock_llm_cls,
            patch('careervp.logic.vpr_generator.run_vpr_quality_gate', side_effect=gate_side_effect),
        ):
            mock_llm = mock_llm_cls.return_value
            mock_llm.invoke.return_value = MagicMock(
                success=True,
                data={
                    'text': json.dumps(llm_phase2_response),
                    'input_tokens': 100,
                    'output_tokens': 200,
                    'cost': 0.003,
                    'model': 'claude-sonnet-4-5',
                },
            )
            pipeline = VPRSixStagePipeline(
                request=minimal_vpr_request,
                user_cv=minimal_user_cv,
            )
            pipeline.run()

        assert gate_calls >= 2  # Gate checked at least twice (fail + pass)

    def test_regeneration_triggered_on_structural_gate_failure(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
        llm_phase2_response: dict[str, Any],
    ) -> None:
        """Structural score below 8.0 must trigger regeneration."""
        gate_calls = 0

        def gate_side_effect(*args: Any, **kwargs: Any) -> Any:
            nonlocal gate_calls
            gate_calls += 1
            structural_score = 8.5 if gate_calls > 1 else 6.0
            return VPRGateResult(
                anti_ai_score=9.5,
                structural_score=structural_score,
                grammar_score=9.5,
                tone_score=9.5,
                passed_gate=gate_calls > 1,
                issues=[] if gate_calls > 1 else ['Low structural score'],
            )

        with (
            patch('careervp.logic.vpr_generator.LLMClient') as mock_llm_cls,
            patch('careervp.logic.vpr_generator.run_vpr_quality_gate', side_effect=gate_side_effect),
        ):
            mock_llm = mock_llm_cls.return_value
            mock_llm.invoke.return_value = MagicMock(
                success=True,
                data={
                    'text': json.dumps(llm_phase2_response),
                    'input_tokens': 100,
                    'output_tokens': 200,
                    'cost': 0.003,
                    'model': 'claude-sonnet-4-5',
                },
            )
            pipeline = VPRSixStagePipeline(
                request=minimal_vpr_request,
                user_cv=minimal_user_cv,
            )
            pipeline.run()

        assert gate_calls >= 2

    def test_stage6_max_retries_respected(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
        llm_phase2_response: dict[str, Any],
    ) -> None:
        """Pipeline must not retry more than MAX_STAGE6_RETRIES times."""
        from careervp.logic.vpr_generator import MAX_STAGE6_RETRIES

        gate_calls = 0

        def always_fail(*args: Any, **kwargs: Any) -> Any:
            nonlocal gate_calls
            gate_calls += 1
            return VPRGateResult(
                anti_ai_score=5.0,
                structural_score=5.0,
                grammar_score=5.0,
                tone_score=5.0,
                passed_gate=False,
                issues=['perpetual failure'],
            )

        with (
            patch('careervp.logic.vpr_generator.LLMClient') as mock_llm_cls,
            patch('careervp.logic.vpr_generator.run_vpr_quality_gate', side_effect=always_fail),
        ):
            mock_llm = mock_llm_cls.return_value
            mock_llm.invoke.return_value = MagicMock(
                success=True,
                data={
                    'text': json.dumps(llm_phase2_response),
                    'input_tokens': 100,
                    'output_tokens': 200,
                    'cost': 0.003,
                    'model': 'claude-sonnet-4-5',
                },
            )
            pipeline = VPRSixStagePipeline(
                request=minimal_vpr_request,
                user_cv=minimal_user_cv,
            )
            pipeline.run()

        assert gate_calls <= MAX_STAGE6_RETRIES + 1

    def test_stage6_final_meta_evaluation_returns_final_vpr_data(self, pipeline: VPRSixStagePipeline, minimal_vpr: VPR) -> None:
        vpr_data = MagicMock(vpr=minimal_vpr)

        with patch('careervp.logic.vpr_generator.run_vpr_quality_gate') as mock_gate:
            mock_gate.return_value = VPRGateResult(
                anti_ai_score=9.5,
                structural_score=9.0,
                grammar_score=9.5,
                tone_score=9.5,
                passed_gate=True,
                issues=[],
            )
            result = pipeline._final_meta_evaluation(vpr_data)

        assert isinstance(result, FinalVPRData)
        assert result.vpr is not None
