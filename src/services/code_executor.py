from src.schemas import CodeExecRequestData, CodeExecResponseData

from src.exceptions import LanguageNotFoundException
from src.internal.languages import LANGUAGE_TO_STRATEGY_MAP, LangEnum


class CodeExecutorService:
    def __init__(self):
        ...
    async def execute(self, data: CodeExecRequestData) -> CodeExecResponseData:
        try:
            lang_enum = LangEnum(data.language)
        except ValueError:
            raise LanguageNotFoundException(data.language)
        
        language_strategy = LANGUAGE_TO_STRATEGY_MAP.get(lang_enum)
        res_stdout, res_stderr, res_return_code = await language_strategy.execute(data.code, data.execution_params)
        
        return CodeExecResponseData(stdout=res_stdout, stderr=res_stderr, return_code=res_return_code)
        
            