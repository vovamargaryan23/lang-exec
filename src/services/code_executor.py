from typing import AsyncGenerator, Dict

from src.schemas import CodeExecRequestData
from src.exceptions import LanguageNotFoundException
from src.internal.languages import LangEnum
from src.internal.strategies import BaseStrategy, PythonStrategy


LANGUAGE_TO_STRATEGY_MAP: Dict[LangEnum, BaseStrategy] = {
    LangEnum.PYTHON: PythonStrategy()
}


class CodeExecutorService:
    def get_stream(self, data: CodeExecRequestData) -> AsyncGenerator[dict, None]:
        strategy = self._get_strategy(data.language)
        return strategy.stream_execute(data.code, data.execution_params)

    def _get_strategy(self, language: str) -> BaseStrategy:
        try:
            lang_enum = LangEnum(language)
        except ValueError:
            raise LanguageNotFoundException(language)
        strategy = LANGUAGE_TO_STRATEGY_MAP.get(lang_enum)
        if strategy is None:
            raise LanguageNotFoundException(language)
        return strategy
