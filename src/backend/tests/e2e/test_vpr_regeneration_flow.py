"""E2E tests — VPR regeneration: version increment and idempotency.

Skipped unless RUN_E2E=true is set in environment.
"""

from __future__ import annotations

import os
import time
from typing import Any

import pytest
import requests

E2E_ENABLED = os.getenv('RUN_E2E', 'false').lower() == 'true'
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:3000')
ID_TOKEN = os.getenv('COGNITO_ID_TOKEN', 'test-token')

# Dedicated application ID for regeneration tests — safe to overwrite
REGEN_APP_ID = 'e2e-regen-test-001'

pytestmark = pytest.mark.skipif(not E2E_ENABLED, reason='Set RUN_E2E=true to run E2E tests')


def _regen_request_payload(application_id: str = REGEN_APP_ID) -> dict[str, Any]:
    return {
        'applicationId': application_id,
        'jobPosting': {
            'title': 'Senior DevOps Engineer',
            'company': 'TestCo',
            'description': 'Own CI/CD pipeline and infrastructure automation.',
            'requirements': ['Terraform', 'AWS', 'Python', 'Kubernetes'],
            'language': 'en',
        },
        'gapResponses': [
            {
                'question': 'Describe your IaC experience.',
                'response': 'Managed 200+ Terraform modules at Acme Corp for 2 years.',
            }
        ],
    }


def _generate_vpr(payload: dict[str, Any]) -> dict[str, Any]:
    """Helper: call POST /api/vpr and return parsed response body."""
    response = requests.post(
        f'{API_BASE_URL}/api/vpr',
        json=payload,
        headers={'Authorization': f'Bearer {ID_TOKEN}'},
        timeout=120,
    )
    assert response.status_code == 200, f'Generation failed: {response.text[:300]}'
    return response.json()


@pytest.mark.e2e
@pytest.mark.slow
class TestVPRRegenerationE2E:
    def test_e2e_regeneration_increments_version(self) -> None:
        """Calling generate twice for the same applicationId must produce v1 then v2."""
        payload = _regen_request_payload()

        # First generation
        body1 = _generate_vpr(payload)
        vpr1 = body1.get('vpr', body1)
        version1 = vpr1.get('version', 0)

        # Brief pause to avoid race conditions
        time.sleep(2)

        # Second generation (same applicationId)
        body2 = _generate_vpr(payload)
        vpr2 = body2.get('vpr', body2)
        version2 = vpr2.get('version', 0)

        assert version2 > version1, f'Expected version to increment. v1={version1}, v2={version2}'

    def test_e2e_application_id_consistent_across_versions(self) -> None:
        """applicationId must be the same value in both v1 and v2 responses."""
        payload = _regen_request_payload()

        body1 = _generate_vpr(payload)
        vpr1 = body1.get('vpr', body1)

        body2 = _generate_vpr(payload)
        vpr2 = body2.get('vpr', body2)

        app_id_1 = vpr1.get('applicationId')
        app_id_2 = vpr2.get('applicationId')

        assert app_id_1 == REGEN_APP_ID, f'applicationId mismatch: {app_id_1}'
        assert app_id_2 == REGEN_APP_ID, f'applicationId mismatch on regen: {app_id_2}'
        assert app_id_1 == app_id_2

    def test_e2e_word_count_populated(self) -> None:
        """word_count must be a positive integer in the response."""
        payload = _regen_request_payload()
        body = _generate_vpr(payload)
        vpr = body.get('vpr', body)

        word_count = vpr.get('wordCount') or vpr.get('word_count')
        assert word_count is not None, 'wordCount missing from response'
        assert isinstance(word_count, int)
        assert word_count > 100, f'wordCount too low: {word_count}'

    def test_e2e_regenerated_vpr_has_all_10_sections(self) -> None:
        """Regenerated VPR must still have all 10 required sections."""
        payload = _regen_request_payload()
        # Generate twice to get a v2
        _generate_vpr(payload)
        time.sleep(1)
        body = _generate_vpr(payload)
        vpr = body.get('vpr', body)

        required_sections = [
            'metadata',
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
        for section in required_sections:
            assert section in vpr and vpr[section] is not None, f"Section '{section}' missing in regenerated VPR"
