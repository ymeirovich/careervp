# Source: docs/architecture/careervp_prompts/cv-tailoring/tests/test_P6_cv_tailoring_pipeline_wiring.yaml
# Spec ID: TEST-CVT-P6
#
# IMPORTANT: These tests fail until the corresponding spec is implemented.
# See the YAML spec for acceptance criteria and traceability matrix.
"""
Unit tests: CV Tailoring pipeline wiring — ATS score propagation, error surfacing,
            RetryingLLMClient.complete() delegate.
Spec: CVT-P6 — Pipeline execution fails in production (four-part diagnosis)

These tests fail if CVT-P6 has not been implemented:
  - T-P6-01..02: AttributeError (RetryingLLMClient.complete absent)
  - T-P6-03:     pydantic.ValidationError or AttributeError (Stage3Result.ats_keyword_score absent)
  - T-P6-04:     TypeError or AssertionError (run_stage3_fact_verification ats_keyword_score param absent)
  - T-P6-05:     AssertionError (pipeline does not scale/propagate ATS score)
  - T-P6-06:     AssertionError (error field absent from failed status payload)
  - T-P6-07:     AssertionError (artifact ats_score is always 75)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from careervp.models.cv import ContactInfo, UserCV, WorkExperience
from careervp.models.result import Result, ResultCode

# ─── Shared helpers ────────────────────────────────────────────────────────────


def _make_valid_cv_sections():  # type: ignore[return]
    from careervp.models.cv_tailoring_models import (
        CVContactSection,
        CVExperienceSection,
        CVSections,
        CVSkillsSection,
    )

    return CVSections(
        contact=CVContactSection(name='Test User', email='test@example.com'),
        summary='Senior engineer with 10 years of experience building scalable cloud systems.',
        skills=CVSkillsSection(technical=['Python', 'AWS'], soft=['Communication']),
        experience=[
            CVExperienceSection(
                company='Acme',
                title='Engineer',
                start_date='01/2020',
                bullets=['Built distributed system handling 1M+ events per day.'],
            )
        ],
        education=[],
        certifications=[],
    )


def _make_valid_user_cv(user_id: str = 'u', full_name: str = 'Test User') -> UserCV:
    return UserCV(
        user_id=user_id,
        cv_id='cv-123',
        full_name=full_name,
        language='en',
        contact_info=ContactInfo(email='test@example.com'),
        professional_summary='Senior engineer with 10 years of experience building scalable distributed systems.',
        experience=[
            WorkExperience(
                company='Acme',
                role='Engineer',
                dates='2020 - Present',
                achievements=['Built X'],
                technologies=['Python'],
            )
        ],
        education=[],
        certifications=[],
        skills=['Python', 'AWS'],
        top_achievements=[],
        languages=['English'],
        is_parsed=True,
    )


# ─── T-P6-01: RetryingLLMClient has .complete() ────────────────────────────────


@pytest.mark.unit
def test_retrying_llm_client_has_complete_method() -> None:
    from careervp.logic.cv_tailoring_logic import RetryingLLMClient
    from careervp.logic.llm_client import LLMClient

    mock_client = MagicMock(spec=LLMClient)
    retrying = RetryingLLMClient(client=mock_client)

    assert hasattr(retrying, 'complete'), 'RetryingLLMClient must have a .complete() method — CVT-P6 not implemented'
    assert callable(retrying.complete), 'RetryingLLMClient.complete must be callable — CVT-P6 not implemented'


# ─── T-P6-02: RetryingLLMClient.complete() delegates ──────────────────────────


@pytest.mark.unit
def test_retrying_llm_client_complete_delegates() -> None:
    from careervp.logic.cv_tailoring_logic import RetryingLLMClient
    from careervp.logic.llm_client import LLMClient, _LLMTextResponse

    mock_client = MagicMock(spec=LLMClient)
    mock_client.complete.return_value = _LLMTextResponse(text='{"cv_sections": {}}')

    retrying = RetryingLLMClient(client=mock_client)
    result = retrying.complete(
        prompt='test prompt',
        system_prompt='test system',
        max_tokens=100,
    )

    mock_client.complete.assert_called_once_with(
        prompt='test prompt',
        system_prompt='test system',
        max_tokens=100,
    )
    assert result.text == '{"cv_sections": {}}', f'RetryingLLMClient.complete() must return inner client result, got {result!r}'


# ─── T-P6-03: Stage3Result has ats_keyword_score field ────────────────────────


@pytest.mark.unit
def test_stage3_result_has_ats_keyword_score_field() -> None:
    from careervp.models.cv_tailoring_models import Stage3Result

    cv_sections = _make_valid_cv_sections()

    result = Stage3Result(
        cv_sections=cv_sections,
        fact_verification_passed=True,
        items_corrected=[],
        items_removed=[],
        ats_keyword_score=70,
    )

    assert result.ats_keyword_score == 70, f'Stage3Result.ats_keyword_score must be 70, got {result.ats_keyword_score!r} — CVT-P6 not implemented'

    result_default = Stage3Result(
        cv_sections=cv_sections,
        fact_verification_passed=True,
    )
    assert result_default.ats_keyword_score == 0, f'Stage3Result.ats_keyword_score default must be 0, got {result_default.ats_keyword_score!r}'


# ─── T-P6-04: run_stage3_fact_verification propagates ats_score ───────────────


@pytest.mark.unit
def test_run_stage3_propagates_ats_score() -> None:
    from careervp.logic.cv_tailoring_pipeline import run_stage3_fact_verification
    from careervp.models.cv_tailoring_models import Stage2Output, Stage2Verification

    cv_sections = _make_valid_cv_sections()
    stage2_out = Stage2Output(
        verification=Stage2Verification(
            ats_keyword_score=7,
            keywords_added_in_review=[],
            summary_rewritten=False,
            fact_verification_passed=True,
            hallucination_flags=[],
        ),
        cv_sections=cv_sections,
    )
    parsed_facts = _make_valid_user_cv()

    result = run_stage3_fact_verification(
        stage2_output=stage2_out,
        parsed_facts=parsed_facts,
        ats_keyword_score=70,
    )

    assert result.ats_keyword_score == 70, (
        f'run_stage3_fact_verification must propagate ats_keyword_score=70 to Stage3Result, got {result.ats_keyword_score!r} — CVT-P6 not implemented'
    )


# ─── T-P6-05: run_cv_tailoring_pipeline scales ATS score to 0-100 ─────────────


@pytest.mark.unit
def test_pipeline_ats_score_scaled_to_100() -> None:
    from careervp.logic.cv_tailoring_pipeline import run_cv_tailoring_pipeline
    from careervp.models.cv_tailoring_models import Stage2Output, Stage2Verification

    cv_sections = _make_valid_cv_sections()
    stage2_response = Stage2Output(
        verification=Stage2Verification(
            ats_keyword_score=7,
            keywords_added_in_review=[],
            summary_rewritten=False,
            fact_verification_passed=True,
            hallucination_flags=[],
        ),
        cv_sections=cv_sections,
    )

    mock_llm = MagicMock()
    with patch(
        'careervp.logic.cv_tailoring_pipeline.run_stage2_cv_generation',
        return_value=Result(success=True, data=stage2_response, code=ResultCode.SUCCESS),
    ):
        pipeline_result = run_cv_tailoring_pipeline(
            cv=_make_valid_user_cv(),
            job_description='Senior Python engineer role at a cloud company with distributed systems experience.',
            vpr=None,
            llm_client=mock_llm,
        )

    assert pipeline_result.success is True, f'Pipeline must succeed, got error: {pipeline_result.error!r}'
    assert pipeline_result.data is not None
    assert pipeline_result.data.ats_keyword_score == 70, (
        f'Pipeline must scale ats_keyword_score from 7 (1-10) to 70 (0-100), got {pipeline_result.data.ats_keyword_score!r} — CVT-P6 not implemented'
    )


# ─── T-P6-06: _build_tailored_cv_status_payload surfaces error ────────────────


@pytest.mark.unit
def test_status_payload_surfaces_error_field() -> None:
    from careervp.handlers.cv_tailoring_handler import _build_tailored_cv_status_payload

    item = {
        'request_id': 'cv-tail-123',
        'status': 'failed',
        'error': 'Stage 2 LLM call failed: AccessDeniedException',
    }
    payload = _build_tailored_cv_status_payload(item, 'fallback-id')

    assert payload['status'] == 'failed', f"Expected status='failed', got {payload['status']!r}"
    assert 'result' in payload, "Failed artifact status payload must include 'result' dict with error detail — CVT-P6 not implemented"
    assert 'error' in payload['result'], f"result dict must contain 'error' key, got keys: {list(payload['result'].keys())} — CVT-P6 not implemented"
    assert 'AccessDeniedException' in payload['result']['error'], f'result.error must contain error message, got: {payload["result"]["error"]!r}'


# ─── T-P6-07: handler artifact uses stage3.ats_keyword_score ──────────────────


@pytest.mark.unit
def test_handle_async_generate_artifact_ats_score_from_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import careervp.handlers.cv_tailoring_handler as handler_module
    from careervp.models.cv_tailoring_models import Stage3Result

    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-table')

    cv_sections = _make_valid_cv_sections()
    stage3 = Stage3Result(
        cv_sections=cv_sections,
        fact_verification_passed=True,
        items_corrected=[],
        items_removed=[],
        ats_keyword_score=80,
    )
    pipeline_result = Result(success=True, data=stage3, code=ResultCode.SUCCESS)

    mock_dal = MagicMock()
    mock_dal.get_cv.return_value = _make_valid_user_cv()
    mock_table = MagicMock()
    mock_dal._get_db_handler.return_value = mock_table

    with patch.object(handler_module, 'DynamoDalHandler', return_value=mock_dal):
        with patch.object(handler_module, 'JobsRepository') as mock_jobs_cls:
            mock_jobs_cls.return_value.get_job.return_value = {
                'description': 'Test job description for senior engineer role.',
                'title': 'Senior Engineer',
            }
            with patch.object(handler_module, 'LLMClient'):
                with patch.object(handler_module, 'run_cv_tailoring_pipeline', return_value=pipeline_result):
                    with patch.object(handler_module, '_update_application_artifact'):
                        handler_module._handle_openapi_async_generate(
                            event={},
                            request_data={'cv_id': 'cv-123', 'job_id': 'job-456', 'vpr_id': None},
                            headers={},
                            user_id='user-789',
                        )

    mock_table.put_item.assert_called_once()
    artifact = mock_table.put_item.call_args.kwargs['Item']
    assert artifact.get('ats_score') == 80, (
        f'Artifact ats_score must be 80 (from stage3.ats_keyword_score=80), '
        f'got {artifact.get("ats_score")!r}. '
        'Handler is still using cv_sections_dict fallback to 75 — CVT-P6 not implemented'
    )
