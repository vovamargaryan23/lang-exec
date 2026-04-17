import secrets
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from src.internal import ContainerManager
from src.internal.languages import LangEnum


class BaseStrategy(ABC):
    def __init__(self):
        self._lang_enum = self._get_self_enum()
        self._container_manager = ContainerManager()

    def _generate_file_name(self) -> str:
        return secrets.token_hex(8)

    @abstractmethod
    def _get_self_enum(self) -> LangEnum:
        ...

    @abstractmethod
    async def stream_execute(self, code: str, exec_params: str) -> AsyncGenerator[dict, None]:
        ...
