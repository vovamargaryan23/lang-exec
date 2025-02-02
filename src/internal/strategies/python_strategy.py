import asyncio
import aiofiles

import aiofiles.os
import aiofiles.ospath

from .base_strategy import BaseStrategy
from src.internal.languages import LangEnum
from src.internal.mappers import LANGUAGE_TO_IMAGE_NAME_MAP
from src.internal.settings import VOLUME_PATH


class PythonStrategy(BaseStrategy):
    def _get_self_enum(self):
        return LangEnum.PYTHON
    
    async def execute(self, code: str, exec_params: str):
        file_name = self._generate_file_name() + ".py"
        full_file_path = VOLUME_PATH / file_name
        
        async with aiofiles.open(full_file_path, mode="w+") as f:
            await f.write(code)
        
        stdout, stderr, return_code = await asyncio.to_thread(self._container_manager.run_container, LANGUAGE_TO_IMAGE_NAME_MAP[self._lang_enum], full_file_path)
        
        # await aiofiles.os.remove(full_file_path)
        return stdout, stderr, return_code

        
        
        