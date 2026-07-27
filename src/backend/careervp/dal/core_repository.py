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

from typing import Any

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.dal.table_registry import TableRegistry
from careervp.models.result import Result


class CoreRepository:
    """Sole repository entry point for artifacts/core table operations."""

    def __init__(
        self,
        table_registry: TableRegistry | None = None,
        dal: DynamoDalHandler | None = None,
    ) -> None:
        self._registry = table_registry if table_registry is not None else TableRegistry()
        self._dal = dal

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

    def list_cover_letters(self, application_id: str) -> Result[list[dict[str, Any]]]:
        """Canonical cover-letter listing for an application."""
        return self.dal.list_cover_letters_canonical(application_id)

    def list_tailored_cvs(self, user_id: str) -> Result[list[dict[str, Any]]]:
        return self.dal.list_tailored_cvs(user_id)

    def get_company_research(self, user_id: str, job_id: str) -> Result[dict[str, Any] | None]:
        return self.dal.get_company_research(user_id, job_id)
