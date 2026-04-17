from typing import AsyncGenerator, Dict

from src.exceptions import LanguageNotFoundException
from src.internal.languages import LangEnum
from src.internal.strategies import BaseStrategy
from src.schemas import CodeExecRequestData


class CodeExecutorService:
    def __init__(self, strategies: Dict[LangEnum, BaseStrategy]) -> None:
        self._strategies = strategies

    def get_stream(self, data: CodeExecRequestData) -> AsyncGenerator[dict, None]:
        strategy = self._get_strategy(data.language)
        return strategy.stream_execute(data.code)

    def _get_strategy(self, language: str) -> BaseStrategy:
        try:
            lang_enum = LangEnum(language)
        except ValueError:
            raise LanguageNotFoundException(language)
        strategy = self._strategies.get(lang_enum)
        if strategy is None:
            raise LanguageNotFoundException(language)
        return strategy
