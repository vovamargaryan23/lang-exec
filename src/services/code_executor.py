from typing import Dict

from src.exceptions import LanguageNotFoundException
from src.internal.languages import LangEnum
from src.internal.strategies.base_strategy import BaseStrategy, PreparedExecution
from src.schemas import CodeExecRequestData


class CodeExecutorService:
    def __init__(self, strategies: Dict[LangEnum, BaseStrategy]) -> None:
        self._strategies = strategies

    async def prepare_stream(self, data: CodeExecRequestData) -> PreparedExecution:
        strategy = self._get_strategy(data.language)
        return await strategy.prepare_execution(data.code)

    def _get_strategy(self, language: str) -> BaseStrategy:
        try:
            lang_enum = LangEnum(language)
        except ValueError:
            raise LanguageNotFoundException(language)
        strategy = self._strategies.get(lang_enum)
        if strategy is None:
            raise LanguageNotFoundException(language)
        return strategy
