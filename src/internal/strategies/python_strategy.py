from typing import AsyncGenerator

import aiofiles
import aiofiles.os

from .base_strategy import BaseStrategy
from src.internal.languages import LangEnum
from src.internal.mappers import LANGUAGE_TO_IMAGE_NAME_MAP
from src.internal.settings import VOLUME_PATH


class PythonStrategy(BaseStrategy):
    def _get_self_enum(self) -> LangEnum:
        return LangEnum.PYTHON

    async def stream_execute(self, code: str, exec_params: str) -> AsyncGenerator[dict, None]:
        file_name = self._generate_file_name() + ".py"
        full_file_path = VOLUME_PATH / file_name

        async with aiofiles.open(full_file_path, mode="w+") as f:
            await f.write(code)

        try:
            async for chunk in self._container_manager.stream_container(
                LANGUAGE_TO_IMAGE_NAME_MAP[self._lang_enum],
                str(full_file_path)
            ):
                yield chunk
        finally:
            await aiofiles.os.remove(full_file_path)
