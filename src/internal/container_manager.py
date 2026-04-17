import asyncio
import logging
import threading
from typing import AsyncGenerator

import docker
import docker.errors

from src.internal.settings import (
    DOCKER_SOCK_PATH,
    EXEC_CPU_LIMIT,
    EXEC_MEM_LIMIT,
    EXEC_PIDS_LIMIT,
    EXEC_TIMEOUT,
    HOST_VOLUME_PATH,
    VOLUME_PATH,
)

logger = logging.getLogger(__name__)


class ContainerManager:
    def __init__(self) -> None:
        self.__docker_client = docker.DockerClient(base_url=DOCKER_SOCK_PATH)

    async def stream_container(self, image: str, command) -> AsyncGenerator[dict, None]:
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _run():
            container = None
            timed_out = False
            try:
                container = self.__docker_client.containers.run(
                    image=image,
                    command=command,
                    stdout=True,
                    stderr=True,
                    detach=True,
                    network_disabled=True,
                    read_only=True,
                    tmpfs={"/tmp": "size=16m,noexec,nosuid"},
                    volumes=[f"{HOST_VOLUME_PATH}:{VOLUME_PATH}:ro"],
                    mem_limit=f"{EXEC_MEM_LIMIT}m",
                    memswap_limit=f"{EXEC_MEM_LIMIT}m",
                    nano_cpus=EXEC_CPU_LIMIT * 10**9,
                    pids_limit=EXEC_PIDS_LIMIT,
                    cap_drop=["ALL"],
                    security_opt=["no-new-privileges:true"],
                )

                def _kill_on_timeout():
                    nonlocal timed_out
                    timed_out = True
                    try:
                        container.stop(timeout=0)
                    except Exception:
                        pass

                timer = threading.Timer(EXEC_TIMEOUT, _kill_on_timeout)
                timer.start()
                try:
                    for chunk in container.logs(stream=True, follow=True):
                        content = chunk.decode() if isinstance(chunk, bytes) else chunk
                        asyncio.run_coroutine_threadsafe(
                            queue.put({"type": "output", "content": content}), loop
                        )
                finally:
                    timer.cancel()

                if timed_out:
                    asyncio.run_coroutine_threadsafe(
                        queue.put({"type": "timeout"}), loop
                    )
                else:
                    result = container.wait(timeout=5)
                    asyncio.run_coroutine_threadsafe(
                        queue.put({"type": "exit", "return_code": result["StatusCode"]}), loop
                    )

            except docker.errors.ImageNotFound as e:
                logger.error("Docker image not found: %s", e)
                asyncio.run_coroutine_threadsafe(
                    queue.put({"type": "error", "message": str(e)}), loop
                )
            except docker.errors.APIError as e:
                logger.error("Docker API error: %s", e)
                asyncio.run_coroutine_threadsafe(
                    queue.put({"type": "error", "message": str(e)}), loop
                )
            finally:
                if container:
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        loop.run_in_executor(None, _run)

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
