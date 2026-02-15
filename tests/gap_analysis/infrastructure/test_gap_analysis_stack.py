"""Infrastructure alignment tests for Gap Analysis.

These tests validate infra/runbook/spec contracts without requiring CDK synthesis in
restricted environments.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
DEPLOYMENT_SPEC = ROOT / "docs" / "refactor" / "specs" / "deployment_spec.yaml"
OPENAPI_PATH = ROOT / "docs" / "swagger" / "careervp-api-v1.yaml"
RUNBOOK_PATH = ROOT / "docs" / "refactor" / "EXECUTION_RUNBOOK.md"


def test_openapi_gap_paths_exist() -> None:
    """OpenAPI defines all gap-analysis paths used by API Gateway migration."""
    openapi = yaml.safe_load(OPENAPI_PATH.read_text())

    assert "/gap-analysis/questions" in openapi["paths"]
    assert "/gap-analysis/responses" in openapi["paths"]
    assert "/gap-analysis/{jobId}/questions" in openapi["paths"]


def test_deployment_spec_declares_additive_route_migration() -> None:
    """Deployment spec should enforce additive route migration strategy."""
    spec = yaml.safe_load(DEPLOYMENT_SPEC.read_text())

    migration = spec["api_route_migration"]
    assert migration["strategy"] == "additive"
    assert any("/api/*" in rule for rule in migration["rules"])
    assert any("OpenAPI paths" in rule for rule in migration["rules"])


def test_runbook_phase_10_includes_gap_alignment_step() -> None:
    """Runbook must include the gap endpoint remediation step and routes."""
    content = RUNBOOK_PATH.read_text()

    assert "Step 10.5: Gap Analysis Handler Completion" in content
    assert "/gap-analysis/questions" in content
    assert "/gap-analysis/responses" in content
    assert "/gap-analysis/{jobId}/questions" in content
