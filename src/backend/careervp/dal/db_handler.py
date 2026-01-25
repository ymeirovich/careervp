from abc import ABC, ABCMeta, abstractmethod

from careervp.models.cv import UserCV


class _SingletonMeta(ABCMeta):
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DalHandler(ABC, metaclass=_SingletonMeta):
    @abstractmethod
    def save_cv(self, user_cv: UserCV) -> None: ...  # pragma: no cover

    @abstractmethod
    def get_cv(self, user_id: str) -> UserCV | None: ...  # pragma: no cover
