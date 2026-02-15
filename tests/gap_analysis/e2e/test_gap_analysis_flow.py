"""E2E contract checks for gap analysis endpoints.

These tests align with OpenAPI + Phase 10 remediation:
- POST /gap-analysis/questions
- POST /gap-analysis/responses
- GET /gap-analysis/{jobId}/questions

Handler-level E2E remains gated until Step 10.5 introduces concrete handlers.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from careervp.handlers.gap_handler import _error_response

ROOT = Path(__file__).resolve().parents[3]
OPENAPI_PATH = ROOT / "docs" / "swagger" / "careervp-api-v1.yaml"
CONTRACT_SPEC_PATH = ROOT / "docs" / "refactor" / "specs" / "api_contract_spec.yaml"


class TestGapAnalysisE2EFlow:
    """Phase-10 contract alignment tests for Gap Analysis."""

    def test_openapi_declares_gap_analysis_endpoints(self) -> None:
        """OpenAPI must include all three gap-analysis endpoints."""
        openapi = yaml.safe_load(OPENAPI_PATH.read_text())
        paths = openapi["paths"]

        assert "/gap-analysis/questions" in paths
        assert "post" in paths["/gap-analysis/questions"]
        assert "/gap-analysis/responses" in paths
        assert "post" in paths["/gap-analysis/responses"]
        assert "/gap-analysis/{jobId}/questions" in paths
        assert "get" in paths["/gap-analysis/{jobId}/questions"]

    def test_contract_spec_matches_gap_analysis_paths(self) -> None:
        """api_contract_spec.yaml must stay synced with OpenAPI paths."""
        spec = yaml.safe_load(CONTRACT_SPEC_PATH.read_text())
        gap_endpoints = spec["endpoints"]["gap_analysis"]
        paths = {entry["path"] for entry in gap_endpoints}

        assert "/gap-analysis/questions" in paths
        assert "/gap-analysis/responses" in paths
        assert "/gap-analysis/{jobId}/questions" in paths

    def test_gap_handler_error_response_contract(self) -> None:
        """Current gap helper should emit standardized error body + CORS headers."""
        response = _error_response(400, "validation failed", "VALIDATION_ERROR")

        assert response["statusCode"] == 400
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert response["headers"]["Content-Type"] == "application/json"
        assert "VALIDATION_ERROR" in response["body"]

    @pytest.mark.skip(
        reason="Phase 10 Step 10.5 pending: gap submit/status handlers not implemented"
    )
    def test_submit_poll_retrieve_flow_pending_step_10_5(self) -> None:
        """Explicitly track pending async flow replacement from legacy tests."""
        pass
