from enum import Enum
from typing import Dict

from src.internal.strategies import BaseStrategy, JavaStrategy, PythonStrategy


class LangEnum(str, Enum):
    JAVA = 'java'
    PYTHON = 'python'
    
LANGUAGE_TO_STRATEGY_MAP: Dict[str, BaseStrategy]  = {
    LangEnum.JAVA : JavaStrategy(),
    LangEnum.PYTHON : PythonStrategy()
}