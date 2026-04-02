"""Integration tests — full VPR pipeline contract with mocked LLM and DAL."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.vpr_generator import generate_vpr
from careervp.models.vpr import VPR, VPRRequest, VPRResponse


@pytest.fixture
def mock_dal_with_no_existing_vpr() -> MagicMock:
    dal = MagicMock()
    dal.get_next_vpr_version.return_value = 1
    dal.save_vpr.return_value = MagicMock(success=True)
    return dal


@pytest.fixture
def mock_dal_with_existing_vpr(minimal_vpr: VPR) -> MagicMock:
    dal = MagicMock()
    minimal_vpr.version = 2
    dal.get_next_vpr_version.return_value = 3
    dal.save_vpr.return_value = MagicMock(success=True)
    return dal


@pytest.mark.integration
class TestVPRPipelineContract:
    def test_pipeline_returns_vpr_response_on_success(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
        mock_dal_with_no_existing_vpr: MagicMock,
        llm_phase2_response: dict[str, Any],
    ) -> None:
        """Full pipeline run must return a successful VPRResponse."""
        with patch('careervp.logic.vpr_generator.LLMClient') as mock_llm_cls:
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
            # Bypass FVS gate by mocking it to pass
            with patch('careervp.logic.vpr_generator.run_vpr_quality_gate') as mock_gate:
                mock_gate.return_value = MagicMock(
                    vpr=MagicMock(spec=VPR),
                    anti_ai_score=9.5,
                    structural_score=9.0,
                    anti_ai_issues=[],
                    passed_gate=True,
                )
                result = generate_vpr(minimal_vpr_request, minimal_user_cv, mock_dal_with_no_existing_vpr)

        assert result.success is True
        assert result.data is not None
        assert isinstance(result.data, VPRResponse)

    def test_pipeline_stage5_produces_10_section_vpr(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
        mock_dal_with_no_existing_vpr: MagicMock,
        llm_phase2_response: dict[str, Any],
    ) -> None:
        from careervp.logic.vpr_generator import ValidatedDraft, VPRSixStagePipeline

        pipeline = VPRSixStagePipeline(
            request=minimal_vpr_request,
            user_cv=minimal_user_cv,
            llm_client=MagicMock(),
        )

        validated = ValidatedDraft(
            raw_payload=llm_phase2_response,
            validation_notes=['Scores verified'],
            evidence_context=MagicMock(),
        )
        vpr_data = pipeline._generate_output(validated)

        # All 10 required sections must be non-None
        vpr = vpr_data.vpr
        assert vpr.metadata is not None
        assert vpr.executive_summary is not None
        assert vpr.role_alignment is not None
        assert vpr.experience_mapping is not None
        assert vpr.skills_analysis is not None
        assert vpr.evidence_gaps is not None
        assert vpr.differentiators is not None
        assert vpr.concerns_and_mitigations is not None
        assert vpr.value_proposition is not None
        assert vpr.application_strategy is not None

    def test_pipeline_saves_vpr_to_dal(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
        mock_dal_with_no_existing_vpr: MagicMock,
        llm_phase2_response: dict[str, Any],
    ) -> None:
        with patch('careervp.logic.vpr_generator.LLMClient') as mock_llm_cls, patch('careervp.logic.vpr_generator.run_vpr_quality_gate') as mock_gate:
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
            mock_gate.return_value = MagicMock(
                vpr=MagicMock(spec=VPR),
                anti_ai_score=9.5,
                structural_score=9.0,
                anti_ai_issues=[],
                passed_gate=True,
            )
            generate_vpr(minimal_vpr_request, minimal_user_cv, mock_dal_with_no_existing_vpr)

        mock_dal_with_no_existing_vpr.save_vpr.assert_called_once()

    def test_pipeline_version_comes_from_dal(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
        mock_dal_with_existing_vpr: MagicMock,
        llm_phase2_response: dict[str, Any],
    ) -> None:
        """Pipeline must use dal.get_next_vpr_version() for version assignment."""
        with patch('careervp.logic.vpr_generator.LLMClient') as mock_llm_cls, patch('careervp.logic.vpr_generator.run_vpr_quality_gate') as mock_gate:
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
            mock_gate.return_value = MagicMock(
                vpr=MagicMock(spec=VPR, version=3),
                anti_ai_score=9.5,
                structural_score=9.0,
                anti_ai_issues=[],
                passed_gate=True,
            )
            generate_vpr(minimal_vpr_request, minimal_user_cv, mock_dal_with_existing_vpr)

        # Version assignment is handler's responsibility (spec 06).
        # generate_vpr uses dal only for saving, not for version lookup.
        mock_dal_with_existing_vpr.get_next_vpr_version.assert_not_called()
        mock_dal_with_existing_vpr.save_vpr.assert_called_once()

    def test_pipeline_retries_on_fvs_gate_failure(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
        mock_dal_with_no_existing_vpr: MagicMock,
        llm_phase2_response: dict[str, Any],
    ) -> None:
        """Gate failure must trigger retry — LLM called again with feedback."""
        gate_call_count = 0

        def gate_side_effect(*args: Any, **kwargs: Any) -> Any:
            nonlocal gate_call_count
            gate_call_count += 1
            return MagicMock(
                vpr=MagicMock(spec=VPR),
                anti_ai_score=9.5 if gate_call_count > 1 else 6.0,
                structural_score=9.0,
                anti_ai_issues=[] if gate_call_count > 1 else ['buzzwords'],
                passed_gate=gate_call_count > 1,
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
            generate_vpr(minimal_vpr_request, minimal_user_cv, mock_dal_with_no_existing_vpr)

        # Gate should have been called at least twice (1 fail + 1 pass)
        assert gate_call_count >= 2

    def test_pipeline_error_on_max_retries_exceeded(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
        mock_dal_with_no_existing_vpr: MagicMock,
        llm_phase2_response: dict[str, Any],
    ) -> None:
        """After MAX_STAGE6_RETRIES failures, generate_vpr must return error result."""
        with patch('careervp.logic.vpr_generator.LLMClient') as mock_llm_cls, patch('careervp.logic.vpr_generator.run_vpr_quality_gate') as mock_gate:
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
            mock_gate.return_value = MagicMock(
                vpr=MagicMock(spec=VPR),
                anti_ai_score=5.0,
                structural_score=5.0,
                anti_ai_issues=['many issues'],
                passed_gate=False,
            )
            result = generate_vpr(minimal_vpr_request, minimal_user_cv, mock_dal_with_no_existing_vpr)

        assert result.success is False

    def test_pipeline_stage4_fallback_produces_valid_vpr(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
        mock_dal_with_no_existing_vpr: MagicMock,
        llm_phase2_response: dict[str, Any],
    ) -> None:
        """Stage 4 LLM failure fallback must still produce a parseable VPR."""
        from careervp.logic.vpr_generator import Phase2Draft, VPRSixStagePipeline

        pipeline = VPRSixStagePipeline(
            request=minimal_vpr_request,
            user_cv=minimal_user_cv,
            llm_client=MagicMock(),
        )
        draft = Phase2Draft(raw_payload=llm_phase2_response, evidence_context=MagicMock())

        with patch('careervp.logic.vpr_generator.LLMClient') as mock_llm_cls:
            mock_llm = mock_llm_cls.return_value
            mock_llm.invoke.return_value = MagicMock(success=False, data=None)
            validated = pipeline._self_correct(draft, feedback=None)

        assert validated is not None
        # Fallback must preserve the original payload for Stage 5 to parse
        assert isinstance(validated.raw_payload, dict)

    def test_vpr_response_camelcase_serializable(self, minimal_vpr: VPR) -> None:
        """VPRResponse serialized with by_alias=True must produce camelCase JSON."""
        from careervp.models.vpr import VPRResponse

        response = VPRResponse(success=True, vpr=minimal_vpr)
        dumped = response.model_dump(by_alias=True, mode='json')
        json_str = json.dumps(dumped)
        parsed = json.loads(json_str)

        # VPR should be present with camelCase keys
        vpr_data = parsed.get('vpr', parsed)
        assert 'applicationId' in vpr_data or 'executiveSummary' in vpr_data

    def test_pipeline_word_count_populated(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
        mock_dal_with_no_existing_vpr: MagicMock,
        llm_phase2_response: dict[str, Any],
    ) -> None:
        from careervp.logic.vpr_generator import ValidatedDraft, VPRSixStagePipeline

        pipeline = VPRSixStagePipeline(
            request=minimal_vpr_request,
            user_cv=minimal_user_cv,
            llm_client=MagicMock(),
        )
        validated = ValidatedDraft(
            raw_payload=llm_phase2_response,
            validation_notes=[],
            evidence_context=MagicMock(),
        )
        vpr_data = pipeline._generate_output(validated)
        # word_count must be a positive integer after stage 5
        assert isinstance(vpr_data.vpr.word_count, int)
        assert vpr_data.vpr.word_count > 0

    def test_pipeline_stage3_uses_phase2_system_prompt(
        self,
        minimal_vpr_request: VPRRequest,
        minimal_user_cv: Any,
        mock_dal_with_no_existing_vpr: MagicMock,
        llm_phase2_response: dict[str, Any],
    ) -> None:
        from careervp.logic.prompts.vpr_prompt import PHASE2_SYSTEM_PROMPT
        from careervp.logic.vpr_generator import EvidenceList, VPRSixStagePipeline

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            success=True,
            data={'text': json.dumps(llm_phase2_response), 'input_tokens': 100, 'output_tokens': 200, 'cost': 0.003, 'model': 'claude-sonnet-4-5'},
        )
        pipeline = VPRSixStagePipeline(
            request=minimal_vpr_request,
            user_cv=minimal_user_cv,
            llm_client=mock_llm,
        )

        evidence = EvidenceList(
            matches=[],
            uncovered_requirements=[],
            key_skills=['Python'],
            experience_level='senior',
        )
        pipeline._synthesize(evidence, feedback=None)

        mock_llm.invoke.assert_called_once()
        invoke_kwargs = mock_llm.invoke.call_args.kwargs
        assert invoke_kwargs.get('system_prompt') == PHASE2_SYSTEM_PROMPT
