from src.internal.settings import settings
from .base_strategy import BaseStrategy, PreparedExecution


class PythonStrategy(BaseStrategy):
    async def prepare_execution(self, code: str) -> PreparedExecution:
        file_path = settings.volume_path / (self._generate_file_name() + ".py")
        return await self._write_and_prepare(code, file_path)
