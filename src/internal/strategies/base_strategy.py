import aiofiles as aiof
from abc import ABC, abstractmethod

class BaseStrategy(ABC):    
    @abstractmethod
    async def execute(self, code: str, exec_params: str):
        ...