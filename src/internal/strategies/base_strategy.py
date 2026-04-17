import secrets
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from src.internal.container_manager import ContainerManager


class BaseStrategy(ABC):
    def __init__(self, container_manager: ContainerManager) -> None:
        self._container_manager = container_manager

    def _generate_file_name(self) -> str:
        return secrets.token_hex(8)

    @abstractmethod
    async def stream_execute(self, code: str) -> AsyncGenerator[dict, None]:
        ...
