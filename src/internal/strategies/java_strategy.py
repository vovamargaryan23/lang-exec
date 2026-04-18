from .base_strategy import BaseStrategy


class JavaStrategy(BaseStrategy):
    @property
    def file_extension(self) -> str:
        return ".java"
