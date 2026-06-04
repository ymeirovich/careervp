"""Unit tests for spec 07: VPR pipeline timeout fix.

RED phase: these tests FAIL before spec 07 is implemented.

Groups:
  1. _self_correct() makes zero LLM calls after the Stage 3/4 merge
  2. _self_correct() rule-based banned-term cleanup still runs
  3. PHASE2_SYSTEM_PROMPT contains the 6 merged self-validation rules
  4. vpr_dlq_handler marks orphaned jobs FAILED without touching terminal jobs
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.prompts.vpr_prompt import PHASE2_SYSTEM_PROMPT
from careervp.logic.vpr_generator import (
    EvidenceList,
    EvidenceMatch,
    Phase2Draft,
    ValidatedDraft,
    VPRSixStagePipeline,
)
from careervp.models.cv import ContactInfo, UserCV, WorkExperience
from careervp.models.job import JobPosting
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import VPRRequest

# ── Shared fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def sample_cv() -> UserCV:
    return UserCV(
        user_id='user-test-01',
        full_name='Jordan Lee',
        language='en',
        contact_info=ContactInfo(email='jordan@example.com'),
        experience=[
            WorkExperience(
                company='EduTech Co',
                role='Senior Instructional Designer',
                dates='2020 – Present',
                achievements=[
                    'Built LMS for 800 concurrent learners.',
                    'Achieved 89% certification pass rate on first attempt.',
                ],
                technologies=['LMS', 'AWS', 'Python'],
            )
        ],
        education=[],
        certifications=[],
        skills=['LMS implementation', 'Instructional design', 'AWS'],
        top_achievements=['Reduced time-to-competency by 25%.'],
        languages=[],
        is_parsed=True,
    )


@pytest.fixture
def sample_request(sample_cv: UserCV) -> VPRRequest:
    posting = JobPosting(
        company_name='SysAid',
        role_title='Learning Experience Specialist',
        description='Build and launch the SysAid Customer Academy.',
        responsibilities=['Lead LMS setup', 'Define certification frameworks'],
        requirements=['LMS implementation', 'Instructional design experience'],
        nice_to_have=['Revenue-generating certification programs'],
        language='en',
    )
    return VPRRequest(
        application_id='app-sysaid-001',
        user_id='user-test-01',
        job_posting=posting,
        gap_responses=[],
    )


def _make_llm_client(*, fail: bool = False) -> MagicMock:
    """Return a mock LLMClient whose invoke() succeeds or fails."""
    client = MagicMock()
    if fail:
        client.invoke.return_value = Result(success=False, error='LLM unavailable', code=ResultCode.LLM_API_ERROR, data=None)
    else:
        client.invoke.return_value = Result(
            success=True,
            data={
                'text': json.dumps({'note': 'unexpected LLM call in self_correct'}),
                'input_tokens': 10,
                'output_tokens': 10,
                'cost': 0.001,
                'model': 'claude-sonnet-4-6',
            },
            code=ResultCode.SUCCESS,
        )
    return client


def _make_pipeline(
    sample_request: VPRRequest,
    sample_cv: UserCV,
    *,
    llm_fail: bool = False,
) -> tuple[VPRSixStagePipeline, MagicMock]:
    llm = _make_llm_client(fail=llm_fail)
    pipeline = VPRSixStagePipeline(sample_request, sample_cv, llm_client=llm)
    return pipeline, llm


def _make_draft(raw_payload: dict[str, Any] | None = None) -> Phase2Draft:
    """Minimal Phase2Draft with clean payload for testing _self_correct."""
    evidence = EvidenceList(
        matches=[
            EvidenceMatch(
                requirement='LMS implementation',
                evidence='Built LMS for 800 concurrent learners at EduTech Co.',
                alignment_score='STRONG',
                impact_potential='Direct match for SysAid Academy infrastructure.',
            )
        ],
        uncovered_requirements=[],
        key_skills=['LMS implementation', 'Instructional design'],
        experience_level='senior',
    )
    payload: dict[str, Any] = raw_payload or {
        'metadata': {
            'report_date': '2026-04-03',
            'candidate_name': 'Jordan Lee',
            'target_role': 'Learning Experience Specialist',
            'target_company': 'SysAid',
            'report_version': '1.0',
            'analysis_scope': 'full',
        },
        'executive_summary': {
            'overall_fit_score': 80,
            'fit_rationale': 'Strong background in LMS and instructional design.',
            'top_three_strengths': [
                {
                    'strength': 'LMS expertise',
                    'evidence': 'Built platform for 800 concurrent learners.',
                    'relevance_to_role': 'Direct match for academy infrastructure.',
                },
                {
                    'strength': 'Certification design',
                    'evidence': '89% first-attempt pass rate.',
                    'relevance_to_role': 'Certification framework design.',
                },
                {
                    'strength': 'Revenue generation',
                    'evidence': '$180K annual training revenue.',
                    'relevance_to_role': 'Paid certification programs.',
                },
            ],
            'top_three_concerns': [
                {'concern': 'No SysAid product exposure', 'severity': 'medium', 'mitigation': 'Short learning curve.'},
                {'concern': 'CS background absent', 'severity': 'low', 'mitigation': 'Transferable via ID.'},
                {'concern': 'Sales exposure limited', 'severity': 'low', 'mitigation': 'Partner framework demonstrates it.'},
            ],
            'recommended_approach': 'aggressive_apply',
        },
        'role_alignment': {
            'core_responsibilities': [],
            'requirement_breakdown': {'must_have': [], 'nice_to_have': [], 'assumed_prerequisites': []},
        },
        'experience_mapping': {'relevant_experiences': [], 'experience_gaps': []},
        'skills_analysis': {'technical_skills': [], 'soft_skills': [], 'tool_proficiency': []},
        'evidence_gaps': {'identified_gaps': [], 'priority_gaps_to_address': []},
        'differentiators': {
            'unique_strengths': [],
            'competitive_advantages': [],
            'positioning_statement': 'Unique blend of cognitive science and AI platform experience.',
        },
        'concerns_and_mitigations': {'likely_objections': [], 'preemptive_responses': []},
        'value_proposition': {
            'primary_value': {
                'statement': 'Build and scale the SysAid Academy from zero.',
                'evidence': 'PresGen platform — 85% performance improvement over target.',
                'outcome_for_company': 'Faster customer onboarding and new revenue stream.',
            },
            'secondary_values': [],
            'quantified_impact': [],
            'elevator_pitch': '27-year instructional designer with AI platform track record.',
        },
        'application_strategy': {
            'messaging_approach': 'Lead with platform build story.',
            'ats_keywords': {'primary': ['LMS'], 'secondary': ['certification']},
            'cv_lead_differentiator': 'PresGen platform build',
            'sections_to_compress': ['older roles'],
        },
    }
    return Phase2Draft(raw_payload=payload, evidence_context=evidence)


# ── Group 1: Stage 4 makes zero LLM calls ────────────────────────────────────


class TestSelfCorrectMakesNoLLMCall:
    """After spec 07, _self_correct() must never call the LLM.

    These tests FAIL before spec 07 because the current implementation
    attempts an LLM call first and only falls back on failure.
    """

    def test_self_correct_does_not_call_llm_when_llm_available(
        self,
        sample_request: VPRRequest,
        sample_cv: UserCV,
    ) -> None:
        """LLM must not be invoked even when it would succeed."""
        pipeline, llm = _make_pipeline(sample_request, sample_cv, llm_fail=False)
        draft = _make_draft()

        pipeline._self_correct(draft)

        llm.invoke.assert_not_called()

    def test_self_correct_does_not_call_llm_with_feedback(
        self,
        sample_request: VPRRequest,
        sample_cv: UserCV,
    ) -> None:
        """Passing a feedback string must not trigger an LLM call."""
        pipeline, llm = _make_pipeline(sample_request, sample_cv, llm_fail=False)
        draft = _make_draft()

        pipeline._self_correct(draft, feedback='Fix banned words in fit_rationale')

        llm.invoke.assert_not_called()

    def test_self_correct_returns_validated_draft(
        self,
        sample_request: VPRRequest,
        sample_cv: UserCV,
    ) -> None:
        """Return type must be ValidatedDraft regardless of LLM availability."""
        pipeline, _ = _make_pipeline(sample_request, sample_cv)
        draft = _make_draft()

        result = pipeline._self_correct(draft)

        assert isinstance(result, ValidatedDraft)

    def test_self_correct_preserves_payload_keys(
        self,
        sample_request: VPRRequest,
        sample_cv: UserCV,
    ) -> None:
        """All top-level keys from Phase2Draft must be present in ValidatedDraft."""
        pipeline, _ = _make_pipeline(sample_request, sample_cv)
        draft = _make_draft()

        result = pipeline._self_correct(draft)

        for key in draft.raw_payload:
            assert key in result.raw_payload, f'Key {key!r} missing from ValidatedDraft payload'

    def test_self_correct_preserves_evidence_context(
        self,
        sample_request: VPRRequest,
        sample_cv: UserCV,
    ) -> None:
        """evidence_context must pass through to ValidatedDraft unchanged."""
        pipeline, _ = _make_pipeline(sample_request, sample_cv)
        draft = _make_draft()

        result = pipeline._self_correct(draft)

        assert result.evidence_context is draft.evidence_context

    def test_self_correct_returns_list_for_validation_notes(
        self,
        sample_request: VPRRequest,
        sample_cv: UserCV,
    ) -> None:
        """validation_notes must be a list (may be empty)."""
        pipeline, _ = _make_pipeline(sample_request, sample_cv)
        draft = _make_draft()

        result = pipeline._self_correct(draft)

        assert isinstance(result.validation_notes, list)


# ── Group 2: Rule-based banned-term cleanup ───────────────────────────────────


class TestSelfCorrectBannedTermCleanup:
    """_self_correct() must strip banned terms from text fields via rule-based pass.

    These tests pass today (fallback already runs on LLM failure) but must
    continue to pass after spec 07 makes rule-based the only path.
    They are included here to pin the behaviour and catch regressions.
    """

    BANNED = ['leverage', 'robust', 'streamline', 'utilize', 'facilitate', 'synergy']

    def _pipeline(self, sample_request: VPRRequest, sample_cv: UserCV) -> VPRSixStagePipeline:
        pipeline, _ = _make_pipeline(sample_request, sample_cv)
        return pipeline

    def _draft_with_banned_in_field(
        self,
        field_path: str,
        banned_word: str,
    ) -> Phase2Draft:
        """Return a draft with banned_word injected at the given dot-path."""
        base = _make_draft()
        payload: dict[str, Any] = dict(base.raw_payload)

        parts = field_path.split('.')
        node: Any = payload
        for part in parts[:-1]:
            node[part] = dict(node[part])
            node = node[part]
        node[parts[-1]] = f'I {banned_word} instructional design to build academies.'

        return Phase2Draft(raw_payload=payload, evidence_context=base.evidence_context)

    def test_banned_word_removed_from_fit_rationale(
        self,
        sample_request: VPRRequest,
        sample_cv: UserCV,
    ) -> None:
        pipeline = self._pipeline(sample_request, sample_cv)
        draft = self._draft_with_banned_in_field('executive_summary.fit_rationale', 'leverage')

        result = pipeline._self_correct(draft)

        value = result.raw_payload['executive_summary']['fit_rationale']
        assert 'leverage' not in value.lower()

    def test_banned_word_removed_from_positioning_statement(
        self,
        sample_request: VPRRequest,
        sample_cv: UserCV,
    ) -> None:
        pipeline = self._pipeline(sample_request, sample_cv)
        draft = self._draft_with_banned_in_field('differentiators.positioning_statement', 'robust')

        result = pipeline._self_correct(draft)

        value = result.raw_payload['differentiators']['positioning_statement']
        assert 'robust' not in value.lower()

    def test_banned_word_removed_from_elevator_pitch(
        self,
        sample_request: VPRRequest,
        sample_cv: UserCV,
    ) -> None:
        pipeline = self._pipeline(sample_request, sample_cv)
        draft = self._draft_with_banned_in_field('value_proposition.elevator_pitch', 'streamline')

        result = pipeline._self_correct(draft)

        value = result.raw_payload['value_proposition']['elevator_pitch']
        assert 'streamline' not in value.lower()

    def test_banned_word_removed_from_primary_value_statement(
        self,
        sample_request: VPRRequest,
        sample_cv: UserCV,
    ) -> None:
        pipeline = self._pipeline(sample_request, sample_cv)
        draft = self._draft_with_banned_in_field('value_proposition.primary_value.statement', 'utilize')

        result = pipeline._self_correct(draft)

        value = result.raw_payload['value_proposition']['primary_value']['statement']
        assert 'utilize' not in value.lower()


# ── Group 3: PHASE2_SYSTEM_PROMPT contains 6 merged validation rules ──────────


class TestPhase2SystemPromptSelfValidationRules:
    """PHASE2_SYSTEM_PROMPT must contain the 6 validation rules folded in from Stage 4.

    These tests FAIL before spec 07 because the rules are not yet in the prompt.
    """

    def test_prompt_contains_self_validation_header(self) -> None:
        assert 'SELF-VALIDATION RULES' in PHASE2_SYSTEM_PROMPT, 'PHASE2_SYSTEM_PROMPT must contain a SELF-VALIDATION RULES section'

    def test_prompt_contains_banned_words_rule(self) -> None:
        assert 'BANNED WORDS' in PHASE2_SYSTEM_PROMPT
        # At least one concrete banned word must appear so the rule is actionable
        assert 'leverage' in PHASE2_SYSTEM_PROMPT

    def test_prompt_contains_evidence_grounding_rule(self) -> None:
        assert 'EVIDENCE GROUNDING' in PHASE2_SYSTEM_PROMPT

    def test_prompt_contains_section_completeness_rule(self) -> None:
        assert 'SECTION COMPLETENESS' in PHASE2_SYSTEM_PROMPT

    def test_prompt_contains_array_minimums_rule(self) -> None:
        assert 'ARRAY MINIMUMS' in PHASE2_SYSTEM_PROMPT

    def test_prompt_contains_score_ranges_rule(self) -> None:
        assert 'SCORE RANGES' in PHASE2_SYSTEM_PROMPT

    def test_prompt_contains_enum_values_rule(self) -> None:
        assert 'ENUM VALUES' in PHASE2_SYSTEM_PROMPT


# ── Group 4: DLQ Lambda ───────────────────────────────────────────────────────


class TestVprDlqHandler:
    """vpr_dlq_handler.lambda_handler must mark orphaned jobs FAILED.

    These tests FAIL before spec 07 because vpr_dlq_handler.py does not exist.
    """

    @staticmethod
    def _event(job_id: str) -> dict[str, Any]:
        return {'Records': [{'body': json.dumps({'job_id': job_id})}]}

    @staticmethod
    def _context() -> MagicMock:
        ctx = MagicMock()
        ctx.function_name = 'careervp-vpr-dlq-handler-lambda-dev'
        return ctx

    @staticmethod
    def _mock_repo(status: str | None) -> MagicMock:
        repo = MagicMock()
        repo.get_job.return_value = {'job_id': 'some-id', 'status': status} if status is not None else None
        return repo

    @patch('careervp.handlers.vpr_dlq_handler.JobsRepository')
    def test_processing_job_is_marked_failed(self, mock_repo_cls: MagicMock) -> None:
        from careervp.handlers.vpr_dlq_handler import lambda_handler

        mock_repo_cls.return_value = self._mock_repo('PROCESSING')
        lambda_handler(self._event('job-proc-01'), self._context())

        mock_repo_cls.return_value.update_job_status.assert_called_once()
        call_args = mock_repo_cls.return_value.update_job_status.call_args
        # First positional arg is job_id, second is new status
        assert call_args[0][1] == 'FAILED'

    @patch('careervp.handlers.vpr_dlq_handler.JobsRepository')
    def test_pending_job_is_marked_failed(self, mock_repo_cls: MagicMock) -> None:
        from careervp.handlers.vpr_dlq_handler import lambda_handler

        mock_repo_cls.return_value = self._mock_repo('PENDING')
        lambda_handler(self._event('job-pend-02'), self._context())

        mock_repo_cls.return_value.update_job_status.assert_called_once()
        call_args = mock_repo_cls.return_value.update_job_status.call_args
        assert call_args[0][1] == 'FAILED'

    @patch('careervp.handlers.vpr_dlq_handler.JobsRepository')
    def test_completed_job_is_not_updated(self, mock_repo_cls: MagicMock) -> None:
        from careervp.handlers.vpr_dlq_handler import lambda_handler

        mock_repo_cls.return_value = self._mock_repo('COMPLETED')
        lambda_handler(self._event('job-comp-03'), self._context())

        mock_repo_cls.return_value.update_job_status.assert_not_called()

    @patch('careervp.handlers.vpr_dlq_handler.JobsRepository')
    def test_already_failed_job_is_not_updated(self, mock_repo_cls: MagicMock) -> None:
        from careervp.handlers.vpr_dlq_handler import lambda_handler

        mock_repo_cls.return_value = self._mock_repo('FAILED')
        lambda_handler(self._event('job-fail-04'), self._context())

        mock_repo_cls.return_value.update_job_status.assert_not_called()

    @patch('careervp.handlers.vpr_dlq_handler.JobsRepository')
    def test_record_missing_job_id_is_skipped_without_error(self, mock_repo_cls: MagicMock) -> None:
        from careervp.handlers.vpr_dlq_handler import lambda_handler

        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        event = {'Records': [{'body': json.dumps({})}]}

        lambda_handler(event, self._context())  # must not raise

        mock_repo.get_job.assert_not_called()
        mock_repo.update_job_status.assert_not_called()

    @patch('careervp.handlers.vpr_dlq_handler.JobsRepository')
    def test_job_not_in_dynamodb_is_skipped_without_error(self, mock_repo_cls: MagicMock) -> None:
        from careervp.handlers.vpr_dlq_handler import lambda_handler

        mock_repo_cls.return_value = self._mock_repo(None)  # get_job returns None

        lambda_handler(self._event('job-missing-05'), self._context())  # must not raise

        mock_repo_cls.return_value.update_job_status.assert_not_called()

    @patch('careervp.handlers.vpr_dlq_handler.JobsRepository')
    def test_error_message_is_persisted_alongside_failed_status(self, mock_repo_cls: MagicMock) -> None:
        from careervp.handlers.vpr_dlq_handler import lambda_handler

        mock_repo_cls.return_value = self._mock_repo('PROCESSING')
        lambda_handler(self._event('job-err-06'), self._context())

        call_kwargs = mock_repo_cls.return_value.update_job_status.call_args[1]
        # error must be passed as a kwarg so jobs_repository writes it to DynamoDB
        assert 'error' in call_kwargs, 'update_job_status must receive an error= kwarg so the failure reason is persisted'
        assert isinstance(call_kwargs['error'], str)
        assert len(call_kwargs['error']) > 0

    @patch('careervp.handlers.vpr_dlq_handler.JobsRepository')
    def test_multiple_records_processed_independently(self, mock_repo_cls: MagicMock) -> None:
        from careervp.handlers.vpr_dlq_handler import lambda_handler

        mock_repo = MagicMock()
        mock_repo.get_job.side_effect = [
            {'job_id': 'j1', 'status': 'PROCESSING'},
            {'job_id': 'j2', 'status': 'COMPLETED'},
            {'job_id': 'j3', 'status': 'PENDING'},
        ]
        mock_repo_cls.return_value = mock_repo

        event = {
            'Records': [
                {'body': json.dumps({'job_id': 'j1'})},
                {'body': json.dumps({'job_id': 'j2'})},
                {'body': json.dumps({'job_id': 'j3'})},
            ]
        }

        lambda_handler(event, self._context())

        # j1 and j3 are non-terminal → must be marked FAILED; j2 is COMPLETED → skipped
        assert mock_repo.update_job_status.call_count == 2
