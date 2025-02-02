from typing import Dict

from src.schemas import CodeExecRequestData, CodeExecResponseData

from src.exceptions import LanguageNotFoundException
from src.internal.languages import LangEnum


from src.internal.strategies import BaseStrategy, PythonStrategy


LANGUAGE_TO_STRATEGY_MAP: Dict[LangEnum, BaseStrategy]  = {
    LangEnum.PYTHON : PythonStrategy()
}

class CodeExecutorService:
    async def execute(self, data: CodeExecRequestData) -> CodeExecResponseData:
        try:
            lang_enum = LangEnum(data.language)
        except ValueError:
            raise LanguageNotFoundException(data.language)
        
        language_strategy = LANGUAGE_TO_STRATEGY_MAP.get(lang_enum)
        stdout, stderr, return_code = await language_strategy.execute(data.code, data.execution_params)
        
        return CodeExecResponseData(stdout=stdout, stderr=stderr, return_code=return_code)
        
            