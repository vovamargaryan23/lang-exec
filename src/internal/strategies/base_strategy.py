import secrets
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncGenerator

import aiofiles
import aiofiles.os

from src.internal.container_manager import ActiveExecution, ContainerManager


class PreparedExecution(ABC):
    @abstractmethod
    async def stream(self) -> AsyncGenerator[dict, None]:
        ...


class _FileBackedExecution(PreparedExecution):
    """Wraps an ActiveExecution and deletes the source file after streaming completes."""

    def __init__(self, active: ActiveExecution, file_path: Path) -> None:
        self._active = active
        self._file_path = file_path

    async def stream(self) -> AsyncGenerator[dict, None]:
        try:
            async for chunk in self._active.stream():
                yield chunk
        finally:
            try:
                await aiofiles.os.remove(self._file_path)
            except FileNotFoundError:
                pass


class BaseStrategy(ABC):
    def __init__(self, container_manager: ContainerManager) -> None:
        self._container_manager = container_manager

    def _generate_file_name(self) -> str:
        return secrets.token_hex(8)

    @abstractmethod
    async def prepare_execution(self, code: str) -> PreparedExecution:
        ...

    async def _write_and_prepare(self, code: str, file_path: Path) -> PreparedExecution:
        async with aiofiles.open(file_path, mode="w") as f:
            await f.write(code)
        try:
            active = await self._container_manager.prepare(str(file_path))
        except Exception:
            await aiofiles.os.remove(file_path)
            raise
        return _FileBackedExecution(active, file_path)
