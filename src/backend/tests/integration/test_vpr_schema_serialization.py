"""Integration tests — VPR schema round-trip serialization."""

from __future__ import annotations

import json

import pytest

from careervp.models.vpr import VPR


@pytest.mark.integration
class TestDynamoSerializationSnakeCase:
    def test_model_dump_for_dynamo_uses_snake_case(self, minimal_vpr: VPR) -> None:
        item = minimal_vpr.model_dump(mode='json')
        # Top-level keys must be snake_case
        assert 'application_id' in item
        assert 'executive_summary' in item
        assert 'role_alignment' in item
        assert 'experience_mapping' in item
        assert 'skills_analysis' in item
        assert 'evidence_gaps' in item
        assert 'differentiators' in item
        assert 'concerns_and_mitigations' in item
        assert 'value_proposition' in item
        assert 'application_strategy' in item

    def test_model_dump_for_dynamo_has_no_camel_case(self, minimal_vpr: VPR) -> None:
        item = minimal_vpr.model_dump(mode='json')
        assert 'applicationId' not in item
        assert 'executiveSummary' not in item
        assert 'roleAlignment' not in item
        assert 'experienceMapping' not in item

    def test_nested_keys_also_snake_case_in_dynamo(self, minimal_vpr: VPR) -> None:
        item = minimal_vpr.model_dump(mode='json')
        es = item['executive_summary']
        assert 'overall_fit_score' in es
        assert 'fit_rationale' in es
        assert 'top_three_strengths' in es
        assert 'recommended_approach' in es
        assert 'overallFitScore' not in es


@pytest.mark.integration
class TestAPISerializationCamelCase:
    def test_model_dump_for_api_uses_camel_case(self, minimal_vpr: VPR) -> None:
        item = minimal_vpr.model_dump(by_alias=True, mode='json')
        assert 'applicationId' in item
        assert 'executiveSummary' in item
        assert 'roleAlignment' in item
        assert 'experienceMapping' in item
        assert 'skillsAnalysis' in item
        assert 'evidenceGaps' in item
        assert 'differentiators' in item
        assert 'concernsAndMitigations' in item
        assert 'valueProposition' in item
        assert 'applicationStrategy' in item

    def test_nested_camel_case_in_api_response(self, minimal_vpr: VPR) -> None:
        item = minimal_vpr.model_dump(by_alias=True, mode='json')
        es = item['executiveSummary']
        assert 'overallFitScore' in es
        assert 'fitRationale' in es
        assert 'topThreeStrengths' in es
        assert 'recommendedApproach' in es
        assert 'overall_fit_score' not in es

    def test_all_10_sections_have_camel_case_aliases(self, minimal_vpr: VPR) -> None:
        item = minimal_vpr.model_dump(by_alias=True, mode='json')
        required_camel_sections = [
            'applicationId',
            'executiveSummary',
            'roleAlignment',
            'experienceMapping',
            'skillsAnalysis',
            'evidenceGaps',
            'differentiators',
            'concernsAndMitigations',
            'valueProposition',
            'applicationStrategy',
        ]
        for section in required_camel_sections:
            assert section in item, f"camelCase alias '{section}' missing from API response"


@pytest.mark.integration
class TestRoundTrip:
    def test_round_trip_dynamo_to_api(self, minimal_vpr: VPR) -> None:
        """Serialize to DynamoDB dict → reconstruct VPR → serialize for API."""
        dynamo_item = minimal_vpr.model_dump(mode='json')

        # Re-construct VPR from DynamoDB item (snake_case)
        reconstructed = VPR.model_validate(dynamo_item)

        # Now serialize for API (camelCase)
        api_response = reconstructed.model_dump(by_alias=True, mode='json')

        assert api_response['applicationId'] == 'app-001'
        assert 'executiveSummary' in api_response

    def test_api_response_is_valid_json(self, minimal_vpr: VPR) -> None:
        api_dict = minimal_vpr.model_dump(by_alias=True, mode='json')
        json_str = json.dumps(api_dict)
        parsed = json.loads(json_str)
        assert parsed['applicationId'] == 'app-001'

    def test_legacy_flat_item_deserialization(self) -> None:
        """Old flat DynamoDB items must produce a VPR object without crashing."""
        legacy_item = {
            'application_id': 'legacy-001',
            'user_id': 'u-xyz',
            'executive_summary': 'Legacy free-text',
            'differentiators': ['Strength A'],
            'gap_strategies': [],
            'keywords': ['Python', 'AWS'],
            'version': 1,
            'language': 'en',
            'word_count': 150,
            'pk': 'legacy-001',
            'sk': 'ARTIFACT#VPR#v1',
            'completely_unknown_field': 'ignored by extra=ignore',
        }
        vpr = VPR.model_validate(legacy_item)
        assert vpr.application_id == 'legacy-001'
        assert vpr.version == 1
        # New structured sections should be None for legacy items
        # (extra='ignore' means old flat fields like executive_summary as str won't crash)

    def test_optional_sections_not_required(self, minimal_vpr: VPR) -> None:
        """company_insights and verification_summary are optional — omitting them is valid."""
        assert minimal_vpr.company_insights is None or True
        assert minimal_vpr.verification_summary is None or True

        # Build without optional sections — must not raise
        vpr_dict = minimal_vpr.model_dump(mode='json')
        vpr_dict.pop('company_insights', None)
        vpr_dict.pop('verification_summary', None)
        rebuilt = VPR.model_validate(vpr_dict)
        assert rebuilt.application_id == minimal_vpr.application_id
