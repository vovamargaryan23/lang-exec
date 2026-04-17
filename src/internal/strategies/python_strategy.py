from typing import AsyncGenerator

import aiofiles
import aiofiles.os

from .base_strategy import BaseStrategy
from src.internal.settings import settings


class PythonStrategy(BaseStrategy):
    async def stream_execute(self, code: str) -> AsyncGenerator[dict, None]:
        file_name = self._generate_file_name() + ".py"
        full_file_path = settings.volume_path / file_name

        async with aiofiles.open(full_file_path, mode="w+") as f:
            await f.write(code)

        try:
            async for chunk in self._container_manager.stream_execute(str(full_file_path)):
                yield chunk
        finally:
            await aiofiles.os.remove(full_file_path)
