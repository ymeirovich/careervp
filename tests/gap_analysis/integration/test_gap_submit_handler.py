"""Integration-level contract checks for gap analysis submission.

Legacy tests targeted /api/gap-analysis/submit and non-existent handlers.
This suite now tracks OpenAPI contract and runbook gating.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
OPENAPI_PATH = ROOT / "docs" / "swagger" / "careervp-api-v1.yaml"
RUNBOOK_PATH = ROOT / "docs" / "refactor" / "EXECUTION_RUNBOOK.md"


def test_gap_questions_operation_id_matches_contract() -> None:
    """POST /gap-analysis/questions must map to generateGapQuestions."""
    openapi = yaml.safe_load(OPENAPI_PATH.read_text())
    operation = openapi["paths"]["/gap-analysis/questions"]["post"]

    assert operation["operationId"] == "generateGapQuestions"
    assert operation["security"] == [{"BearerAuth": []}]


def test_gap_responses_operation_id_matches_contract() -> None:
    """POST /gap-analysis/responses must map to submitGapResponses."""
    openapi = yaml.safe_load(OPENAPI_PATH.read_text())
    operation = openapi["paths"]["/gap-analysis/responses"]["post"]

    assert operation["operationId"] == "submitGapResponses"
    assert operation["security"] == [{"BearerAuth": []}]


def test_runbook_tracks_gap_handler_as_phase_10_remediation() -> None:
    """Runbook should explicitly include gap-analysis remediation step."""
    content = RUNBOOK_PATH.read_text()

    assert "Step 10.5" in content
    assert "Gap Analysis Handler Completion" in content
    assert "/gap-analysis/questions" in content
    assert "/gap-analysis/responses" in content


@pytest.mark.skip(
    reason="Phase 10 Step 10.5 pending: gap submit/status handlers not implemented"
)
def test_submit_handler_runtime_integration_pending() -> None:
    """Runtime handler integration remains pending until handlers are implemented."""
    pass
