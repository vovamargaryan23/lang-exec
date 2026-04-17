import asyncio
import contextlib
import logging
from typing import AsyncGenerator

import aiodocker.exceptions
from async_timeout import timeout as async_timeout

from src.internal.container_pool import ContainerPool
from src.internal.settings import settings

logger = logging.getLogger(__name__)


class ContainerManager:
    def __init__(self, pool: ContainerPool) -> None:
        self._pool = pool

    async def stream_execute(self, file_path: str) -> AsyncGenerator[dict, None]:
        container = await self._pool.acquire()
        try:
            exec_instance = await container.exec(
                cmd=self._pool.build_exec_cmd(file_path),
                stdout=True,
                stderr=True,
            )
            try:
                async with async_timeout(settings.exec_timeout):
                    async with exec_instance.start(detach=False) as stream:
                        while True:
                            msg = await stream.read_out()
                            if msg is None:
                                break
                            yield {"type": "output", "content": msg.data.decode()}
            except asyncio.TimeoutError:
                with contextlib.suppress(Exception):
                    await container.kill()
                yield {"type": "timeout"}
                return

            inspect = await exec_instance.inspect()
            yield {"type": "exit", "return_code": inspect["ExitCode"]}

        except aiodocker.exceptions.DockerError as e:
            logger.error("Docker error during execution: %s", e)
            yield {"type": "error", "message": str(e)}
        finally:
            await self._pool.release(container)
