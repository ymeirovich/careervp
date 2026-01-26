from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from typing import Any

from careervp.models.cv import UserCV
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
