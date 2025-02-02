import random
import string

from abc import ABC, abstractmethod

from src.internal import ContainerManager
from src.internal.languages import LangEnum


class BaseStrategy(ABC):
    def __init__(self):
        self._lang_enum = self._get_self_enum()
        self._container_manager = ContainerManager()
    
    def _generate_file_name(self) -> str:
        length = 16
        random_string = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(length)])
        return random_string
    
    @abstractmethod
    def _get_self_enum(self) -> LangEnum:
        ...
    
    @abstractmethod
    async def execute(self, code: str, exec_params: str):
        ...
    
