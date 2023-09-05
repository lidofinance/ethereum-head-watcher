import logging

from abc import ABC, abstractmethod

from enum import Enum

from src.providers.keys_api.typings import LidoNamedKey

logger = logging.getLogger()


class NamedKey(LidoNamedKey):
    pass


class SourceType(Enum):
    KEYS_API = 'keys_api'
    FILE = 'file'


class BaseSource(ABC):
    @abstractmethod
    def update_keys(self) -> dict[str, NamedKey] | None:
        ...
