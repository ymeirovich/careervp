"""Unit tests for spec 08 VPR guidance and schema ordering."""

from __future__ import annotations

import pytest

from careervp.logic.prompts.vpr_prompt import PHASE2_OUTPUT_SCHEMA, PHASE2_PROMPT_2_1_TEMPLATE, build_phase2_system_prompt


def _first_schema_position(template: str, section_key: str) -> int:
    """Return the character position of a top-level schema key in the OUTPUT SCHEMA block.

    Searches for `"key":` as it appears in the JSON skeleton. Asserts the key exists
    so failures produce a clear message rather than a silent -1 comparison.
    """
    marker = f'"{section_key}":'
    pos = template.find(marker)
    assert pos != -1, f'Schema key "{section_key}" not found in PHASE2_PROMPT_2_1_TEMPLATE'
    return pos


@pytest.mark.unit
class TestSectionOrdering:
    """differentiators and value_proposition must appear before role_alignment in the schema."""

    def test_differentiators_before_role_alignment(self) -> None:
        diff_pos = _first_schema_position(PHASE2_OUTPUT_SCHEMA, 'differentiators')
        role_pos = _first_schema_position(PHASE2_OUTPUT_SCHEMA, 'role_alignment')
        assert diff_pos < role_pos, f'"differentiators" (pos {diff_pos}) must appear before "role_alignment" (pos {role_pos}) in the OUTPUT SCHEMA'

    def test_value_proposition_before_role_alignment(self) -> None:
        vp_pos = _first_schema_position(PHASE2_OUTPUT_SCHEMA, 'value_proposition')
        role_pos = _first_schema_position(PHASE2_OUTPUT_SCHEMA, 'role_alignment')
        assert vp_pos < role_pos, f'"value_proposition" (pos {vp_pos}) must appear before "role_alignment" (pos {role_pos}) in the OUTPUT SCHEMA'

    def test_differentiators_before_value_proposition(self) -> None:
        diff_pos = _first_schema_position(PHASE2_OUTPUT_SCHEMA, 'differentiators')
        vp_pos = _first_schema_position(PHASE2_OUTPUT_SCHEMA, 'value_proposition')
        assert diff_pos < vp_pos, f'"differentiators" (pos {diff_pos}) must appear before "value_proposition" (pos {vp_pos})'

    def test_executive_summary_before_differentiators(self) -> None:
        exec_pos = _first_schema_position(PHASE2_OUTPUT_SCHEMA, 'executive_summary')
        diff_pos = _first_schema_position(PHASE2_OUTPUT_SCHEMA, 'differentiators')
        assert exec_pos < diff_pos

    def test_metadata_before_executive_summary(self) -> None:
        meta_pos = _first_schema_position(PHASE2_OUTPUT_SCHEMA, 'metadata')
        exec_pos = _first_schema_position(PHASE2_OUTPUT_SCHEMA, 'executive_summary')
        assert meta_pos < exec_pos

    def test_all_10_required_sections_present(self) -> None:
        required = [
            'metadata',
            'executive_summary',
            'differentiators',
            'value_proposition',
            'role_alignment',
            'experience_mapping',
            'skills_analysis',
            'evidence_gaps',
            'concerns_and_mitigations',
            'application_strategy',
        ]
        for section in required:
            assert f'"{section}"' in PHASE2_OUTPUT_SCHEMA, f'Required section "{section}" missing from PHASE2_OUTPUT_SCHEMA'


@pytest.mark.unit
class TestGenerationGuidanceBlock:
    """Generation guidance block must be present and positioned before the OUTPUT SCHEMA."""

    def _guidance_block(self) -> str:
        """Extract the text between the guidance header and the OUTPUT SCHEMA header."""
        guidance_start = PHASE2_PROMPT_2_1_TEMPLATE.find('GENERATION GUIDANCE')
        schema_start = build_phase2_system_prompt().find('OUTPUT SCHEMA')
        assert guidance_start != -1, "'GENERATION GUIDANCE' header not found in PHASE2_PROMPT_2_1_TEMPLATE"
        assert schema_start != -1, "'OUTPUT SCHEMA' header not found in build_phase2_system_prompt()"
        return PHASE2_PROMPT_2_1_TEMPLATE[guidance_start:]

    def test_guidance_header_present(self) -> None:
        assert 'GENERATION GUIDANCE' in PHASE2_PROMPT_2_1_TEMPLATE

    def test_schema_moved_to_system_prompt(self) -> None:
        assert 'OUTPUT SCHEMA' not in PHASE2_PROMPT_2_1_TEMPLATE
        assert 'OUTPUT SCHEMA' in build_phase2_system_prompt()

    def test_five_percent_rarity_test_present(self) -> None:
        block = self._guidance_block()
        assert '5%' in block, 'The "5% test" rarity rule must be stated in the guidance block'

    def test_proof_citation_requirement_present(self) -> None:
        block = self._guidance_block().lower()
        assert any(
            phrase in block
            for phrase in [
                'specific metric',
                'named outcome',
                'quantified fact',
                'cite a specific',
            ]
        ), 'Proof citation requirement not found in generation guidance block'

    def test_positioning_statement_guidance_with_company_mention(self) -> None:
        block = self._guidance_block()
        assert 'positioning_statement' in block, 'positioning_statement guidance must appear in the guidance block, not only in the schema'
        assert 'company' in block.lower() or 'TargetCompany' in block, 'positioning_statement guidance must mention naming the target company'

    def test_elevator_pitch_guidance_in_block(self) -> None:
        block = self._guidance_block()
        assert 'elevator_pitch' in block, 'elevator_pitch guidance must appear in the guidance block, not only in the schema'

    def test_primary_value_forward_looking_guidance(self) -> None:
        block = self._guidance_block().lower()
        # Must instruct on forward-looking primary_value.statement
        assert any(
            phrase in block
            for phrase in [
                'forward-looking',
                'forward looking',
                'reduce',
                'scale',
                'build',
                'drive',
                'accelerate',
            ]
        ), 'primary_value forward-looking instruction not found in guidance block'
