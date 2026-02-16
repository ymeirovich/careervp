"""Unit tests for ApiStorageAdapter (Phase 10 Step 10.0e)."""

from __future__ import annotations

from careervp.dal.api_storage_adapter import ApiStorageAdapter


class TestApiStorageAdapter:
    def test_jobs_mapping_uses_job_id(self) -> None:
        adapter = ApiStorageAdapter()

        mapping = adapter.map_logical_to_physical_keys(
            "jobs",
            {"job_id": "job-123"},
        )

        assert mapping == {"jobs_table": {"pk": "job-123"}}

    def test_jobs_mapping_accepts_legacy_application_id(self) -> None:
        adapter = ApiStorageAdapter()

        mapping = adapter.map_logical_to_physical_keys(
            "jobs",
            {"application_id": "job-legacy-123"},
        )

        assert mapping == {"jobs_table": {"pk": "job-legacy-123"}}

    def test_cv_upload_maps_to_users_table_cv_item(self) -> None:
        adapter = ApiStorageAdapter()

        mapping = adapter.map_logical_to_physical_keys(
            "cv_upload",
            {"user_id": "user-123", "cv_id": "cv-123"},
        )

        assert mapping == {"users_table": {"pk": "user-123", "sk": "CV"}}

    def test_vpr_mapping_builds_artifact_sk(self) -> None:
        adapter = ApiStorageAdapter()

        mapping = adapter.map_logical_to_physical_keys(
            "vpr_async",
            {
                "user_id": "user-123",
                "job_id": "job-123",
                "vpr_id": "vpr-123",
            },
        )

        assert mapping["users_table"]["pk"] == "user-123"
        assert mapping["users_table"]["sk"] == "ARTIFACT#VPR#vpr-123"

    def test_tailoring_mapping_builds_cv_job_key(self) -> None:
        adapter = ApiStorageAdapter()

        mapping = adapter.build_users_table_pk_sk(
            "cv_tailoring_async",
            "user-123",
            {"cv_id": "cv-123", "job_id": "job-123"},
        )

        assert mapping == {
            "pk": "user-123",
            "sk": "ARTIFACT#CV_TAILORED#cv-123#job-123#v1",
        }

    def test_map_physical_vpr_item_back_to_logical_ids(self) -> None:
        adapter = ApiStorageAdapter()

        logical = adapter.map_physical_to_logical_ids(
            "vpr_async",
            {
                "pk": "user-123",
                "sk": "ARTIFACT#VPR#vpr-123",
                "vpr_id": "vpr-123",
                "job_id": "job-123",
            },
        )

        assert logical["user_id"] == "user-123"
        assert logical["vpr_id"] == "vpr-123"
        assert logical["job_id"] == "job-123"
        assert logical["application_id"] == "job-123"

    def test_requires_user_id_for_users_table_mappings(self) -> None:
        adapter = ApiStorageAdapter()

        try:
            adapter.map_logical_to_physical_keys("vpr_async", {"job_id": "job-123"})
            raised = False
        except ValueError as exc:
            raised = True
            assert str(exc) == "user_id is required"

        assert raised
