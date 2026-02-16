"""Storage contract integration checks (spec <-> adapter)."""

from __future__ import annotations

from pathlib import Path

import yaml

from careervp.dal.api_storage_adapter import ApiStorageAdapter

ROOT = Path(__file__).resolve().parents[2]
STORAGE_CONTRACT_PATH = (
    ROOT / "docs" / "refactor" / "specs" / "storage_contract_spec.yaml"
)


def test_storage_contract_defines_required_logical_ids() -> None:
    spec = yaml.safe_load(STORAGE_CONTRACT_PATH.read_text())

    logical_ids = set(spec["logical_identifiers"])
    assert "cv_id" in logical_ids
    assert "job_id" in logical_ids
    assert "vpr_id" in logical_ids
    assert "company_research_id" in logical_ids


def test_adapter_covers_all_entity_mappings() -> None:
    spec = yaml.safe_load(STORAGE_CONTRACT_PATH.read_text())
    adapter = ApiStorageAdapter()

    entity_mapping = spec["entity_mapping"]

    assert "cv_upload" in entity_mapping
    assert "vpr_async" in entity_mapping
    assert "cv_tailoring_async" in entity_mapping
    assert "cover_letter_async" in entity_mapping
    assert "interview_prep_async" in entity_mapping
    assert "company_research_async" in entity_mapping
    assert "gap_analysis" in entity_mapping

    # Smoke-check mapping generation for each mapped entity.
    base = {"user_id": "user-123", "cv_id": "cv-123", "job_id": "job-123"}

    assert "users_table" in adapter.map_logical_to_physical_keys("cv_upload", base)
    assert "users_table" in adapter.map_logical_to_physical_keys(
        "vpr_async",
        {**base, "vpr_id": "vpr-123"},
    )
    assert "users_table" in adapter.map_logical_to_physical_keys(
        "cv_tailoring_async",
        {**base, "cvTailoringId": "ct-123"},
    )
    assert "users_table" in adapter.map_logical_to_physical_keys(
        "cover_letter_async",
        {**base, "coverLetterId": "cl-123"},
    )
    assert "users_table" in adapter.map_logical_to_physical_keys(
        "interview_prep_async",
        {**base, "interviewPrepId": "ip-123"},
    )
    assert "users_table" in adapter.map_logical_to_physical_keys(
        "company_research_async",
        {**base, "company_research_id": "cr-123"},
    )
    assert "users_table" in adapter.map_logical_to_physical_keys("gap_analysis", base)


def test_adapter_keeps_legacy_alias_for_application_id() -> None:
    adapter = ApiStorageAdapter()

    mapping = adapter.map_logical_to_physical_keys(
        "jobs",
        {"application_id": "legacy-job-123"},
    )

    assert mapping["jobs_table"]["pk"] == "legacy-job-123"
