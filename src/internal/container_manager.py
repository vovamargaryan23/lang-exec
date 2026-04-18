import asyncio
import contextlib
import logging
from typing import AsyncGenerator

import aiodocker.exceptions
from async_timeout import timeout as async_timeout

from src.exceptions import DockerInfrastructureError
from src.internal.container_pool import ContainerPool
from src.internal.settings import settings

logger = logging.getLogger(__name__)


class ActiveExecution:
    """Holds an acquired container and streams its exec output."""

    __slots__ = ("_container", "_pool", "_cmd")

    def __init__(self, container, pool: ContainerPool, cmd: list[str]) -> None:
        self._container = container
        self._pool = pool
        self._cmd = cmd

    async def stream(self) -> AsyncGenerator[dict, None]:
        try:
            exec_instance = await self._container.exec(
                cmd=self._cmd,
                stdout=True,
                stderr=True,
            )
            try:
                async with async_timeout(settings.exec_timeout):
                    async with exec_instance.start(detach=False) as s:
                        while True:
                            msg = await s.read_out()
                            if msg is None:
                                break
                            yield {"type": "output", "content": msg.data.decode()}
            except asyncio.TimeoutError:
                with contextlib.suppress(Exception):
                    await self._container.kill()
                yield {"type": "timeout"}
                return

            inspect = await exec_instance.inspect()
            yield {"type": "exit", "return_code": inspect["ExitCode"]}

        except aiodocker.exceptions.DockerError as e:
            logger.error("Docker error during execution: %s", e)
            yield {"type": "infrastructure_error", "message": str(e)}
        finally:
            await self._pool.release(self._container)


class ContainerManager:
    def __init__(self, pool: ContainerPool) -> None:
        self._pool = pool

    async def prepare(self, file_path: str) -> ActiveExecution:
        """Acquire a container for execution. Raises DockerInfrastructureError on failure."""
        try:
            container = await self._pool.acquire()
        except Exception as e:
            raise DockerInfrastructureError(str(e)) from e
        return ActiveExecution(container, self._pool, self._pool.build_exec_cmd(file_path))
