"""Unit tests for Phase 2 VPR prompt templates (spec 02)."""

from __future__ import annotations

from typing import Any

import pytest

from careervp.logic.prompts.vpr_prompt import (
    BANNED_WORDS,
    PHASE2_SYSTEM_PROMPT,
    PHASE2_VALIDATION_SYSTEM_PROMPT,
    build_phase2_prompt,
    build_phase2_validation_prompt,
    # Existing builders — must still exist
    build_stage_3_prompt,
    build_stage_4_prompt,
    build_vpr_prompt,
)


@pytest.mark.unit
class TestPhase2SystemPrompts:
    def test_phase2_system_prompt_is_non_empty_string(self) -> None:
        assert isinstance(PHASE2_SYSTEM_PROMPT, str)
        assert len(PHASE2_SYSTEM_PROMPT.strip()) > 50

    def test_phase2_validation_system_prompt_is_non_empty_string(self) -> None:
        assert isinstance(PHASE2_VALIDATION_SYSTEM_PROMPT, str)
        assert len(PHASE2_VALIDATION_SYSTEM_PROMPT.strip()) > 50

    def test_phase2_system_prompt_mentions_json(self) -> None:
        assert 'JSON' in PHASE2_SYSTEM_PROMPT

    def test_phase2_validation_prompt_mentions_validation(self) -> None:
        assert 'validation' in PHASE2_VALIDATION_SYSTEM_PROMPT.lower()


@pytest.mark.unit
class TestBuildPhase2Prompt:
    def test_returns_non_empty_string(
        self,
        minimal_vpr_request: Any,
        minimal_user_cv: Any,
        llm_phase2_response: dict[str, Any],
    ) -> None:
        evidence_payload = {
            'matches': [{'requirement': 'Python', 'evidence': '5 years', 'alignment_score': 90}],
            'uncovered_requirements': [],
            'key_skills': ['Python', 'AWS'],
            'experience_level': 'senior',
        }
        prompt = build_phase2_prompt(
            evidence_payload=evidence_payload,
            user_cv=minimal_user_cv,
            request=minimal_vpr_request,
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 200

    def test_contains_10_section_skeleton_keys(
        self,
        minimal_vpr_request: Any,
        minimal_user_cv: Any,
    ) -> None:
        evidence_payload: dict[str, Any] = {'matches': [], 'uncovered_requirements': [], 'key_skills': [], 'experience_level': 'mid'}
        prompt = build_phase2_prompt(
            evidence_payload=evidence_payload,
            user_cv=minimal_user_cv,
            request=minimal_vpr_request,
        )
        required_sections = [
            'metadata',
            'executive_summary',
            'role_alignment',
            'experience_mapping',
            'skills_analysis',
            'evidence_gaps',
            'differentiators',
            'concerns_and_mitigations',
            'value_proposition',
            'application_strategy',
        ]
        for section in required_sections:
            assert section in prompt, f"Section '{section}' missing from prompt skeleton"

    def test_contains_banned_words_list(
        self,
        minimal_vpr_request: Any,
        minimal_user_cv: Any,
    ) -> None:
        evidence_payload: dict[str, Any] = {'matches': [], 'uncovered_requirements': [], 'key_skills': [], 'experience_level': 'mid'}
        prompt = build_phase2_prompt(
            evidence_payload=evidence_payload,
            user_cv=minimal_user_cv,
            request=minimal_vpr_request,
        )
        # At least some of the core banned words must appear in the prompt
        banned_subset = ['leverage', 'utilize', 'synergy', 'robust']
        found = [word for word in banned_subset if word in prompt.lower()]
        assert len(found) >= 2, f'Expected banned words in prompt, found: {found}'

    def test_contains_immutable_fact_rules(
        self,
        minimal_vpr_request: Any,
        minimal_user_cv: Any,
    ) -> None:
        evidence_payload: dict[str, Any] = {'matches': [], 'uncovered_requirements': [], 'key_skills': [], 'experience_level': 'mid'}
        prompt = build_phase2_prompt(
            evidence_payload=evidence_payload,
            user_cv=minimal_user_cv,
            request=minimal_vpr_request,
        )
        # Fact rules: must not invent companies/dates
        assert 'invent' in prompt.lower() or 'hallucinate' in prompt.lower() or 'never' in prompt.lower()

    def test_feedback_block_injected_when_provided(
        self,
        minimal_vpr_request: Any,
        minimal_user_cv: Any,
    ) -> None:
        evidence_payload: dict[str, Any] = {'matches': [], 'uncovered_requirements': [], 'key_skills': [], 'experience_level': 'mid'}
        feedback = 'Too many AI buzzwords in executive_summary.'
        prompt = build_phase2_prompt(
            evidence_payload=evidence_payload,
            user_cv=minimal_user_cv,
            request=minimal_vpr_request,
            feedback=feedback,
        )
        assert feedback in prompt

    def test_no_feedback_block_when_feedback_is_none(
        self,
        minimal_vpr_request: Any,
        minimal_user_cv: Any,
    ) -> None:
        evidence_payload: dict[str, Any] = {'matches': [], 'uncovered_requirements': [], 'key_skills': [], 'experience_level': 'mid'}
        prompt = build_phase2_prompt(
            evidence_payload=evidence_payload,
            user_cv=minimal_user_cv,
            request=minimal_vpr_request,
            feedback=None,
        )
        assert 'REGENERATION FEEDBACK' not in prompt

    def test_cv_facts_serialized_into_prompt(
        self,
        minimal_vpr_request: Any,
        minimal_user_cv: Any,
    ) -> None:
        evidence_payload: dict[str, Any] = {'matches': [], 'uncovered_requirements': [], 'key_skills': [], 'experience_level': 'mid'}
        prompt = build_phase2_prompt(
            evidence_payload=evidence_payload,
            user_cv=minimal_user_cv,
            request=minimal_vpr_request,
        )
        # CV content (Acme Corp) should appear in prompt
        assert 'Acme Corp' in prompt or 'Jane Smith' in prompt


@pytest.mark.unit
class TestBuildPhase2ValidationPrompt:
    def test_returns_non_empty_string(self, minimal_user_cv: Any, llm_phase2_response: dict[str, Any]) -> None:
        prompt = build_phase2_validation_prompt(
            vpr_payload=llm_phase2_response,
            user_cv=minimal_user_cv,
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 200

    def test_contains_vpr_json_in_prompt(self, minimal_user_cv: Any, llm_phase2_response: dict[str, Any]) -> None:
        prompt = build_phase2_validation_prompt(
            vpr_payload=llm_phase2_response,
            user_cv=minimal_user_cv,
        )
        # The VPR payload should be serialized into the prompt
        assert 'Staff Engineer' in prompt or 'SysAid' in prompt

    def test_contains_all_6_validation_rules(self, minimal_user_cv: Any, llm_phase2_response: dict[str, Any]) -> None:
        prompt = build_phase2_validation_prompt(
            vpr_payload=llm_phase2_response,
            user_cv=minimal_user_cv,
        )
        # Each rule keyword must appear in the prompt
        rule_keywords = [
            'traceability',  # Rule 1 — Evidence Traceability
            'consistency',  # Rule 2 — Quantification Consistency
            'alignment',  # Rule 3 — Alignment Score Justification
            'severity',  # Rule 4 — Gap Severity Calibration
            'rarity',  # Rule 5 — Differentiator Rarity
            'substance',  # Rule 6 — Mitigation Substance
        ]
        for keyword in rule_keywords:
            assert keyword in prompt.lower(), f"Rule keyword '{keyword}' missing from validation prompt"

    def test_validation_feedback_injected_when_provided(self, minimal_user_cv: Any, llm_phase2_response: dict[str, Any]) -> None:
        feedback = 'Fix alignment scores in role_alignment section.'
        prompt = build_phase2_validation_prompt(
            vpr_payload=llm_phase2_response,
            user_cv=minimal_user_cv,
            feedback=feedback,
        )
        assert feedback in prompt

    def test_validation_notes_field_mentioned(self, minimal_user_cv: Any, llm_phase2_response: dict[str, Any]) -> None:
        prompt = build_phase2_validation_prompt(
            vpr_payload=llm_phase2_response,
            user_cv=minimal_user_cv,
        )
        assert 'validation_notes' in prompt


@pytest.mark.unit
class TestExistingPromptsPreserved:
    def test_build_stage_3_prompt_still_callable(self) -> None:
        assert callable(build_stage_3_prompt)

    def test_build_stage_4_prompt_still_callable(self) -> None:
        assert callable(build_stage_4_prompt)

    def test_build_vpr_prompt_still_callable(self) -> None:
        assert callable(build_vpr_prompt)

    def test_banned_words_list_still_present(self) -> None:
        assert isinstance(BANNED_WORDS, (list, set, frozenset))
        assert len(BANNED_WORDS) >= 10
