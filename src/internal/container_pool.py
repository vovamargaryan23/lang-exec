import asyncio
import contextlib
import logging
import aiodocker

from src.internal.settings import settings

logger = logging.getLogger(__name__)


def _log_task_error(task: asyncio.Task) -> None:
    if not task.cancelled() and (exc := task.exception()):
        logger.error("Background pool task failed: %s", exc)


class ContainerPool:
    def __init__(self, docker: aiodocker.Docker, image: str) -> None:
        self._docker = docker
        self._image = image
        self._exec_prefix: list[str] = []
        self._idle: asyncio.Queue = asyncio.Queue(maxsize=settings.exec_pool_size)
        self._semaphore = asyncio.Semaphore(settings.exec_pool_size + settings.exec_pool_overflow)

    def build_exec_cmd(self, file_path: str) -> list[str]:
        return self._exec_prefix + [file_path]

    async def startup(self) -> None:
        await self._load_exec_prefix()
        results = await asyncio.gather(
            *[self._create() for _ in range(settings.exec_pool_size)],
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.error("Failed to pre-warm container for %s: %s", self._image, result)
            else:
                await self._idle.put(result)
        logger.info(
            "Pool ready: %d/%d containers warmed for %s",
            self._idle.qsize(), settings.exec_pool_size, self._image,
        )

    async def acquire(self):
        await self._semaphore.acquire()
        try:
            return self._idle.get_nowait()
        except asyncio.QueueEmpty:
            return await self._create()

    async def release(self, container) -> None:
        task = asyncio.create_task(self._retire_and_replenish(container))
        task.add_done_callback(_log_task_error)
        self._semaphore.release()

    async def shutdown(self) -> None:
        containers = []
        while not self._idle.empty():
            containers.append(self._idle.get_nowait())
        await asyncio.gather(*[self._delete_safely(c) for c in containers])

    async def _load_exec_prefix(self) -> None:
        image_info = await self._docker.images.get(self._image)
        labels: dict = (image_info.get("Config") or {}).get("Labels") or {}
        raw = labels.get("lang.exec", "")
        self._exec_prefix = raw.split() if raw else []
        logger.info("Exec prefix for %s: %s", self._image, self._exec_prefix)

    async def _create(self):
        container = await self._docker.containers.create({
            "Image": self._image,
            "NetworkDisabled": True,
            "HostConfig": {
                "Binds": [f"{settings.host_volume_path}:{settings.volume_path}:ro"],
                "Memory": settings.exec_mem_limit_bytes,
                "MemorySwap": settings.exec_mem_limit_bytes,
                "NanoCpus": settings.exec_cpu_limit_nanos,
                "PidsLimit": settings.exec_pids_limit,
                "CapDrop": ["ALL"],
                "SecurityOpt": ["no-new-privileges:true"],
                "ReadonlyRootfs": True,
                "Tmpfs": {"/tmp": "size=16m,noexec,nosuid"},
            },
        })
        await container.start()
        return container

    async def _retire_and_replenish(self, container) -> None:
        await self._delete_safely(container)
        if not self._idle.full():
            try:
                new_container = await self._create()
                try:
                    self._idle.put_nowait(new_container)
                except asyncio.QueueFull:
                    await self._delete_safely(new_container)
            except Exception as e:
                logger.error("Failed to replenish pool for %s: %s", self._image, e)

    @staticmethod
    async def _delete_safely(container) -> None:
        with contextlib.suppress(Exception):
            await container.delete(force=True)
