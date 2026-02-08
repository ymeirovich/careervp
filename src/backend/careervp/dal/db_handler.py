from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from typing import Any

from careervp.models.cv import UserCV
from careervp.models.cv_tailoring_models import TailoredCV
from careervp.models.job import GapResponse
from careervp.models.result import Result
from careervp.models.vpr import VPR

# Storage contract per docs/specs/03-vpr-generator.md:14 defines PK/SK for VPR artifacts.


class _SingletonMeta(ABCMeta):
    _instances: dict[type, DalHandler] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> DalHandler:
        if cls not in cls._instances:
            cls._instances[cls] = super(_SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DalHandler(ABC, metaclass=_SingletonMeta):
    @classmethod
    def reset_instance(cls) -> None:
        """Testing hook to drop the cached singleton instance."""
        if cls in _SingletonMeta._instances:
            del _SingletonMeta._instances[cls]

    @abstractmethod
    def save_cv(self, user_cv: UserCV) -> None: ...  # pragma: no cover

    @abstractmethod
    def get_cv(self, user_id: str) -> UserCV | None: ...  # pragma: no cover

    @abstractmethod
    def save_vpr(self, vpr: VPR) -> Result[None]: ...  # pragma: no cover

    @abstractmethod
    def get_vpr(self, application_id: str, version: int | None = None) -> Result[VPR | None]: ...  # pragma: no cover

    @abstractmethod
    def get_latest_vpr(self, application_id: str) -> Result[VPR | None]: ...  # pragma: no cover

    @abstractmethod
    def list_vprs(self, user_id: str) -> Result[list[VPR]]: ...  # pragma: no cover

    @abstractmethod
    def save_tailored_cv(self, tailored_cv: TailoredCV, job_id: str | None = None, version: int = 1) -> Result[None]: ...  # pragma: no cover

    @abstractmethod
    def get_tailored_cv(
        self,
        user_id: str,
        cv_id: str,
        job_id: str,
        version: int | None = None,
    ) -> Result[TailoredCV | None]: ...  # pragma: no cover

    @abstractmethod
    def list_tailored_cvs(self, user_id: str) -> Result[list[TailoredCV]]: ...  # pragma: no cover

    @abstractmethod
    def save_cover_letter(
        self,
        cover_letter: dict[str, Any],
        user_id: str,
        cv_id: str,
        job_id: str,
        version: int = 1,
    ) -> Result[None]: ...  # pragma: no cover

    @abstractmethod
    def get_cover_letter(
        self,
        user_id: str,
        cv_id: str,
        job_id: str,
        version: int | None = None,
    ) -> Result[dict[str, Any] | None]: ...  # pragma: no cover

    @abstractmethod
    def list_cover_letters(self, user_id: str) -> Result[list[dict[str, Any]]]: ...  # pragma: no cover

    @abstractmethod
    def save_gap_questions(
        self,
        user_id: str,
        cv_id: str,
        job_id: str,
        questions: list[dict[str, Any]],
    ) -> Result[None]: ...  # pragma: no cover

    @abstractmethod
    def get_gap_questions(
        self,
        user_id: str,
        cv_id: str,
        job_id: str,
    ) -> Result[list[dict[str, Any]] | None]: ...  # pragma: no cover

    @abstractmethod
    def save_gap_responses(
        self,
        user_id: str,
        responses: list[GapResponse],
        version: int = 1,
    ) -> Result[None]: ...  # pragma: no cover

    @abstractmethod
    def get_gap_responses(self, user_id: str, version: int | None = None) -> Result[list[GapResponse]]: ...  # pragma: no cover
