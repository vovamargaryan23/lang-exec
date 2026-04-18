import asyncio
import logging
from typing import Dict, Type

import aiodocker

from src.internal.container_manager import ContainerManager
from src.internal.container_pool import ContainerPool
from src.internal.languages import LangEnum
from src.internal.mappers import LANGUAGE_TO_IMAGE_NAME_MAP
from src.internal.strategies.base_strategy import BaseStrategy
from src.internal.strategies.java_strategy import JavaStrategy
from src.internal.strategies.python_strategy import PythonStrategy

logger = logging.getLogger(__name__)

LANGUAGE_TO_STRATEGY_CLASS: Dict[LangEnum, Type[BaseStrategy]] = {
    LangEnum.PYTHON: PythonStrategy,
    LangEnum.JAVA: JavaStrategy,
}


async def create_pools(docker: aiodocker.Docker) -> Dict[LangEnum, ContainerPool]:
    pools = {lang: ContainerPool(docker=docker, image=image) for lang, image in LANGUAGE_TO_IMAGE_NAME_MAP.items()}
    await asyncio.gather(*[pool.startup() for pool in pools.values()])
    return pools


def create_strategies(pools: Dict[LangEnum, ContainerPool]) -> Dict[LangEnum, BaseStrategy]:
    return {
        lang: LANGUAGE_TO_STRATEGY_CLASS[lang](container_manager=ContainerManager(pool=pool))
        for lang, pool in pools.items()
        if lang in LANGUAGE_TO_STRATEGY_CLASS
    }


async def shutdown_pools(pools: Dict[LangEnum, ContainerPool]) -> None:
    await asyncio.gather(
        *[pool.shutdown() for pool in pools.values()],
        return_exceptions=True,
    )
    logger.info("All container pools shut down")
