from .base_strategy import BaseStrategy


class PythonStrategy(BaseStrategy):
    @property
    def file_extension(self) -> str:
        return ".py"
