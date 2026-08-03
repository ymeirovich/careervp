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
    VPR_ARTIFACT_TYPE,
    TableRegistry,
    canonical_application_condition,
    canonical_artifact_id,
    canonical_item_key,
)
from careervp.models.result import Result, ResultCode


def _error_text(result: Result[Any]) -> str | None:
    """Read a Result's error message defensively.

    ``Result.error`` is both a field and a classmethod (``models/result.py``), so the
    attribute can resolve to a bound method rather than the message.
    """
    error = result.error
    return error if isinstance(error, str) else None


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
        """Resolve one opaque id from an owned application/type, never an alias.

        The canonical artifact is the authority. A VPR jobs repository may supply an
        id when no canonical artifact exists yet, but only ever an id — content
        always comes from the canonical artifact.
        """
        try:
            items = self._canonical_artifacts_of_type(application_id, artifact_type)
        except (ClientError, ValueError) as exc:
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

        candidates = [item for item in items if (user_id is None or self._owner_id(item) == user_id) and canonical_artifact_id(item) is not None]
        if candidates:
            # Highest version wins; timestamps only break ties. The type-index
            # cannot order these (every VPR shares its sort-key value).
            candidates.sort(key=self._recency_key, reverse=True)
            return Result(success=True, data=canonical_artifact_id(candidates[0]), code=ResultCode.SUCCESS)

        if artifact_type == VPR_ARTIFACT_TYPE and user_id and self._vpr_jobs_repository is not None:
            return self._resolve_vpr_job_id(application_id=application_id, user_id=user_id)

        return Result(success=True, data=None, code=ResultCode.SUCCESS)

    def _resolve_vpr_job_id(self, *, application_id: str, user_id: str) -> Result[str | None]:
        assert self._vpr_jobs_repository is not None
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
        matching_jobs.sort(key=lambda job: str(job.get('updated_at') or job.get('created_at') or ''), reverse=True)
        return Result(success=True, data=str(matching_jobs[0]['job_id']).strip(), code=ResultCode.SUCCESS)

    def _canonical_artifacts_of_type(self, application_id: str, artifact_type: str) -> list[dict[str, Any]]:
        """Every canonical item of one type in an application partition."""
        response = self._artifacts_table().query(
            KeyConditionExpression=canonical_application_condition(application_id),
        )
        return [item for item in response.get('Items', []) if isinstance(item, dict) and self._artifact_type(item) == artifact_type]

    @staticmethod
    def _item_version(item: dict[str, Any]) -> int:
        try:
            return int(item.get('version', 0))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _recency_key(item: dict[str, Any]) -> tuple[int, str]:
        return (
            CoreRepository._item_version(item),
            str(item.get('updated_at') or item.get('created_at') or ''),
        )

    def save_vpr_artifact(
        self,
        *,
        application_id: str,
        artifact_id: str,
        user_id: str,
        vpr_payload: dict[str, Any],
        version: int,
        now_iso: str,
    ) -> Result[None]:
        """Write the one canonical VPR artifact (F-DEVX-1).

        ``artifactId`` is the physical sort key; ``artifact_id`` is the logical id
        the D-H4 resolver reads (it accepts that name only). Both carry the same
        opaque VPR job id, which the hub also stores in
        ``artifact_statuses.vpr_artifact_id``.
        """
        clean_application_id = application_id.strip()
        clean_artifact_id = artifact_id.strip()
        clean_user_id = user_id.strip()
        if not clean_application_id or not clean_artifact_id or not clean_user_id:
            return Result(
                success=False,
                error='canonical VPR write requires application_id, artifact_id and user_id',
                code=ResultCode.VALIDATION,
            )

        item: dict[str, Any] = {
            **canonical_item_key(clean_application_id, clean_artifact_id),
            'artifact_id': clean_artifact_id,
            'artifactType': VPR_ARTIFACT_TYPE,
            'user_id': clean_user_id,
            'status': 'completed',
            'version': version,
            'created_at': now_iso,
            'updated_at': now_iso,
            'vpr': vpr_payload,
        }
        try:
            self._artifacts_table().put_item(Item=item)
        except (ClientError, ValueError) as exc:
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)
        return Result(success=True, data=None, code=ResultCode.SUCCESS)

    def next_vpr_version(self, application_id: str) -> int:
        """Version authority for VPRs: highest canonical version + 1 (never the users table)."""
        items = self._canonical_artifacts_of_type(application_id, VPR_ARTIFACT_TYPE)
        versions = [self._item_version(item) for item in items]
        return max(versions) + 1 if versions else 1

    def get_vpr_by_artifact_id(
        self,
        application_id: str,
        artifact_id: str,
        *,
        user_id: str | None = None,
    ) -> Result[Any | None]:
        """Read a VPR only after its opaque id was resolved from owner/application.

        Returns the real stored VPR payload. A jobs-table record is identity and
        status only — it is never VPR content, and there is no legacy users-table
        fallback: an absent canonical artifact is a successful ``None``.
        """
        canonical_result = self._get_canonical_artifact(
            application_id=application_id,
            artifact_id=artifact_id,
            artifact_type=VPR_ARTIFACT_TYPE,
            user_id=user_id,
        )
        if not canonical_result.success or canonical_result.data is None:
            return Result(
                success=canonical_result.success,
                data=None,
                error=_error_text(canonical_result),
                code=canonical_result.code,
            )
        return Result(success=True, data=self._materialize_vpr(canonical_result.data), code=ResultCode.SUCCESS)

    @staticmethod
    def _materialize_vpr(item: dict[str, Any]) -> dict[str, Any]:
        """Flatten a canonical artifact into the VPR payload consumers read."""
        payload = item.get('vpr')
        resolved: dict[str, Any] = dict(payload) if isinstance(payload, dict) else {}
        resolved['artifact_id'] = canonical_artifact_id(item) or str(item.get('artifact_id') or '')
        resolved.setdefault('application_id', str(item.get('applicationId') or ''))
        resolved.setdefault('user_id', CoreRepository._owner_id(item))
        for field_name in ('created_at', 'updated_at', 'version'):
            if field_name in item:
                resolved.setdefault(field_name, item[field_name])
        return resolved

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
