import asyncio
import logging
from typing import Dict, NamedTuple, Type

import aiodocker

from src.internal.container_manager import ContainerManager
from src.internal.container_pool import ContainerPool
from src.internal.languages import LangEnum
from src.internal.strategies.base_strategy import BaseStrategy
from src.internal.strategies.java_strategy import JavaStrategy
from src.internal.strategies.python_strategy import PythonStrategy

logger = logging.getLogger(__name__)


class _LangConfig(NamedTuple):
    image: str
    strategy_class: Type[BaseStrategy]


LANGUAGE_REGISTRY: Dict[LangEnum, _LangConfig] = {
    LangEnum.PYTHON: _LangConfig("lang-exec-python-executor:latest", PythonStrategy),
    LangEnum.JAVA: _LangConfig("lang-exec-java-executor:latest", JavaStrategy),
}


async def create_pools(docker: aiodocker.Docker) -> Dict[LangEnum, ContainerPool]:
    pools = {
        lang: ContainerPool(docker=docker, image=cfg.image)
        for lang, cfg in LANGUAGE_REGISTRY.items()
    }
    await asyncio.gather(*[pool.startup() for pool in pools.values()])
    return pools


def create_strategies(pools: Dict[LangEnum, ContainerPool]) -> Dict[LangEnum, BaseStrategy]:
    return {
        lang: cfg.strategy_class(container_manager=ContainerManager(pool=pools[lang]))
        for lang, cfg in LANGUAGE_REGISTRY.items()
        if lang in pools
    }


async def shutdown_pools(pools: Dict[LangEnum, ContainerPool]) -> None:
    await asyncio.gather(
        *[pool.shutdown() for pool in pools.values()],
        return_exceptions=True,
    )
    logger.info("All container pools shut down")
