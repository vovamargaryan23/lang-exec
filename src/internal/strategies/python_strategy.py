import asyncio
from .base_strategy import BaseStrategy


class PythonStrategy(BaseStrategy):
    async def execute(self, code: str, exec_params: str):
        ...