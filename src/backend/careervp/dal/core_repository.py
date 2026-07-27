"""Repository entry point for the artifacts/core table (scope-lock D-H2).

``CoreRepository`` is the approved way for handlers and logic to reach
artifacts/core items. It owns no key grammar itself — that lives in
``careervp.dal.table_registry`` — but every read it performs goes through
the canonical key convention first, with the DAL's guarded legacy fallback
behind it (D-H3: a key-schema mismatch surfaces as
``ResultCode.TABLE_SCHEMA_MISMATCH``, never as a false not-found).

Wave-3 consumers: D-H4 (3.2), D-M2/D-M5 (3.4), and the D-H9 demolition gate
(3.5) extend this class rather than adding key construction elsewhere.
"""

from __future__ import annotations

from typing import Any, Protocol

from botocore.exceptions import ClientError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.dal.table_registry import (
    TableRegistry,
    canonical_application_condition,
    canonical_artifact_id,
    canonical_item_key,
)
from careervp.models.result import Result, ResultCode


class VPRJobsRepository(Protocol):
    """Jobs-repository surface needed for owned VPR artifact resolution."""

    def get_vpr_jobs_by_user(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """List VPR jobs already scoped to the authenticated user."""

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Read one VPR job by its repository-resolved opaque artifact id."""


class CoreRepository:
    """Sole repository entry point for artifacts/core table operations."""

    def __init__(
        self,
        table_registry: TableRegistry | None = None,
        dal: DynamoDalHandler | None = None,
        vpr_jobs_repository: VPRJobsRepository | None = None,
    ) -> None:
        self._registry = table_registry if table_registry is not None else TableRegistry()
        self._dal = dal
        self._vpr_jobs_repository = vpr_jobs_repository

    @property
    def registry(self) -> TableRegistry:
        return self._registry

    @property
    def dal(self) -> DynamoDalHandler:
        if self._dal is None:
            self._dal = DynamoDalHandler(self._registry.artifacts_table_name)
        return self._dal

    def get_cover_letter_by_artifact_id(
        self,
        application_id: str,
        artifact_id: str,
    ) -> Result[dict[str, Any] | None]:
        """Canonical cover-letter read by applicationId + artifactId."""
        return self.dal.read_cover_letter_by_artifact_id(application_id, artifact_id)

    def resolve_artifact_id(
        self,
        application_id: str,
        artifact_type: str,
        *,
        user_id: str | None = None,
    ) -> Result[str | None]:
        """Resolve one opaque id from an owned application/type, never an alias."""
        if artifact_type == 'vpr' and user_id and self._vpr_jobs_repository is not None:
            try:
                jobs = self._vpr_jobs_repository.get_vpr_jobs_by_user(user_id, limit=100)
            except Exception as exc:
                return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

            matching_jobs = [
                job
                for job in jobs
                if str(job.get('application_id') or '').strip() == application_id
                and str(job.get('user_id') or '').strip() == user_id
                and isinstance(job.get('job_id'), str)
                and str(job['job_id']).strip()
            ]
            if not matching_jobs:
                return Result(success=True, data=None, code=ResultCode.SUCCESS)
            matching_jobs.sort(
                key=lambda job: str(job.get('updated_at') or job.get('created_at') or ''),
                reverse=True,
            )
            return Result(success=True, data=str(matching_jobs[0]['job_id']).strip(), code=ResultCode.SUCCESS)

        try:
            response = self._artifacts_table().query(
                KeyConditionExpression=canonical_application_condition(application_id),
            )
        except (ClientError, ValueError) as exc:
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

        items = response.get('Items', [])
        candidates = [
            item
            for item in items
            if isinstance(item, dict)
            and self._artifact_type(item) == artifact_type
            and (user_id is None or self._owner_id(item) == user_id)
            and canonical_artifact_id(item) is not None
        ]
        if not candidates:
            return Result(success=True, data=None, code=ResultCode.SUCCESS)
        candidates.sort(
            key=lambda item: str(item.get('updated_at') or item.get('created_at') or ''),
            reverse=True,
        )
        return Result(success=True, data=canonical_artifact_id(candidates[0]), code=ResultCode.SUCCESS)

    def get_vpr_by_artifact_id(
        self,
        application_id: str,
        artifact_id: str,
        *,
        user_id: str | None = None,
    ) -> Result[Any | None]:
        """Read a VPR only after its opaque id was resolved from owner/application."""
        if self._vpr_jobs_repository is not None:
            return self._get_vpr_job(
                application_id=application_id,
                artifact_id=artifact_id,
                user_id=user_id,
            )

        canonical_result = self._get_canonical_artifact(
            application_id=application_id,
            artifact_id=artifact_id,
            artifact_type='vpr',
            user_id=user_id,
        )
        if not canonical_result.success or canonical_result.data is not None:
            return canonical_result
        return self._get_vpr_from_dal(application_id=application_id, user_id=user_id)

    def _get_vpr_from_dal(
        self,
        *,
        application_id: str,
        user_id: str | None,
    ) -> Result[Any | None]:
        try:
            vpr_result = self.dal.get_vpr(application_id=application_id)
        except Exception as exc:
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)
        if not vpr_result.success or vpr_result.data is None:
            error = vpr_result.error if isinstance(vpr_result.error, str) else None
            return Result(
                success=vpr_result.success,
                data=None,
                error=error,
                code=vpr_result.code,
            )
        owner_id = str(getattr(vpr_result.data, 'user_id', '') or '').strip()
        if user_id is not None and owner_id != user_id:
            return Result(success=False, data=None, error='VPR ownership mismatch', code=ResultCode.FORBIDDEN)
        return Result(success=True, data=vpr_result.data, code=ResultCode.SUCCESS)

    def _get_vpr_job(
        self,
        *,
        application_id: str,
        artifact_id: str,
        user_id: str | None,
    ) -> Result[dict[str, Any] | None]:
        assert self._vpr_jobs_repository is not None
        try:
            job = self._vpr_jobs_repository.get_job(artifact_id)
        except Exception as exc:
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)
        if not isinstance(job, dict):
            return Result(success=True, data=None, code=ResultCode.SUCCESS)
        if application_id and str(job.get('application_id') or '').strip() != application_id:
            return Result(success=True, data=None, code=ResultCode.SUCCESS)
        if user_id is not None and self._owner_id(job) != user_id:
            return Result(success=False, data=None, error='VPR ownership mismatch', code=ResultCode.FORBIDDEN)
        payload = job.get('result')
        resolved = dict(payload) if isinstance(payload, dict) else {}
        resolved.setdefault('artifact_id', artifact_id)
        resolved.setdefault('application_id', str(job.get('application_id') or application_id))
        if user_id is not None:
            resolved.setdefault('user_id', user_id)
        input_data = job.get('input_data')
        if isinstance(input_data, dict) and isinstance(input_data.get('language'), str):
            resolved.setdefault('language', str(input_data['language']).strip())
        return Result(success=True, data=resolved, code=ResultCode.SUCCESS)

    def get_interview_prep_by_artifact_id(
        self,
        application_id: str,
        artifact_id: str,
        *,
        user_id: str | None = None,
    ) -> Result[dict[str, Any] | None]:
        """Read canonical interview prep by application and opaque artifact id."""
        return self._get_canonical_artifact(
            application_id=application_id,
            artifact_id=artifact_id,
            artifact_type='interview_prep',
            user_id=user_id,
        )

    def list_cover_letters(self, application_id: str) -> Result[list[dict[str, Any]]]:
        """Canonical cover-letter listing for an application."""
        return self.dal.list_cover_letters_canonical(application_id)

    def list_tailored_cvs(self, user_id: str) -> Result[list[dict[str, Any]]]:
        return self.dal.list_tailored_cvs(user_id)

    def get_company_research(self, user_id: str, job_id: str) -> Result[dict[str, Any] | None]:
        return self.dal.get_company_research(user_id, job_id)

    def _get_canonical_artifact(
        self,
        *,
        application_id: str,
        artifact_id: str,
        artifact_type: str,
        user_id: str | None,
    ) -> Result[dict[str, Any] | None]:
        try:
            response = self._artifacts_table().get_item(
                Key=canonical_item_key(application_id, artifact_id),
            )
        except (ClientError, ValueError) as exc:
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

        item = response.get('Item')
        if not isinstance(item, dict):
            return Result(success=True, data=None, code=ResultCode.SUCCESS)
        if self._artifact_type(item) != artifact_type:
            return Result(success=True, data=None, code=ResultCode.SUCCESS)
        if user_id is not None and self._owner_id(item) != user_id:
            return Result(success=False, data=None, error='Artifact ownership mismatch', code=ResultCode.FORBIDDEN)
        return Result(success=True, data=item, code=ResultCode.SUCCESS)

    @staticmethod
    def _artifact_type(item: dict[str, Any]) -> str:
        return str(item.get('artifact_type') or item.get('artifactType') or '').strip()

    @staticmethod
    def _owner_id(item: dict[str, Any]) -> str:
        return str(item.get('user_id') or item.get('userId') or '').strip()

    def _artifacts_table(self) -> Any:
        if self._dal is not None:
            return self._dal._get_db_handler(self._dal.table_name)
        return self.registry.artifacts_table()
