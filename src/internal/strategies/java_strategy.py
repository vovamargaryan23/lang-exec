from .base_strategy import BaseStrategy


class JavaStrategy(BaseStrategy):
    async def execute(self, code: str, exec_params: str):
        ...