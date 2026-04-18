from src.internal.settings import settings
from .base_strategy import BaseStrategy, PreparedExecution


class JavaStrategy(BaseStrategy):
    async def prepare_execution(self, code: str) -> PreparedExecution:
        # Java 11+ single-file source launcher: `java file.java` compiles and runs
        # in one step with no class-name/filename constraint. The first class in the
        # file is used as the entry point.
        file_path = settings.volume_path / (self._generate_file_name() + ".java")
        return await self._write_and_prepare(code, file_path)
