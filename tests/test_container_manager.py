import asyncio
import contextlib
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import aiodocker.exceptions
import pytest

from src.internal.container_manager import ContainerManager
from src.internal.container_pool import ContainerPool
from tests.conftest import make_mock_container, make_mock_message, mock_exec_stream


@pytest.fixture
def mock_pool() -> MagicMock:
    pool = MagicMock(spec=ContainerPool)
    pool.acquire = AsyncMock()
    pool.release = AsyncMock()
    pool.build_exec_cmd = MagicMock(return_value=["python3", "/media/code/script.py"])
    return pool


@pytest.fixture
def manager(mock_pool) -> ContainerManager:
    return ContainerManager(pool=mock_pool)


def _make_exec_instance(*messages, exit_code: int = 0) -> MagicMock:
    exec_instance = MagicMock()
    exec_instance.start = MagicMock(return_value=mock_exec_stream(*messages))
    exec_instance.inspect = AsyncMock(return_value={"ExitCode": exit_code})
    return exec_instance


class TestStreamExecuteSuccess:
    @pytest.mark.asyncio
    async def test_yields_output_chunks_then_exit(self, manager, mock_pool):
        container = make_mock_container()
        container.exec = AsyncMock(
            return_value=_make_exec_instance(
                make_mock_message("Hello\n"),
                make_mock_message("World\n"),
                exit_code=0,
            )
        )
        mock_pool.acquire.return_value = container

        results = [chunk async for chunk in manager.stream_execute("/media/code/script.py")]

        assert results == [
            {"type": "output", "content": "Hello\n"},
            {"type": "output", "content": "World\n"},
            {"type": "exit", "return_code": 0},
        ]

    @pytest.mark.asyncio
    async def test_no_output_yields_only_exit(self, manager, mock_pool):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance(exit_code=0))
        mock_pool.acquire.return_value = container

        results = [chunk async for chunk in manager.stream_execute("/media/code/script.py")]

        assert results == [{"type": "exit", "return_code": 0}]

    @pytest.mark.asyncio
    async def test_non_zero_exit_code_is_propagated(self, manager, mock_pool):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance(exit_code=1))
        mock_pool.acquire.return_value = container

        results = [chunk async for chunk in manager.stream_execute("/media/code/script.py")]

        assert results[-1] == {"type": "exit", "return_code": 1}

    @pytest.mark.asyncio
    async def test_releases_container_after_successful_execution(self, manager, mock_pool):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance(exit_code=0))
        mock_pool.acquire.return_value = container

        async for _ in manager.stream_execute("/media/code/script.py"):
            pass

        mock_pool.release.assert_called_once_with(container)


class TestStreamExecuteTimeout:
    @pytest.fixture
    def timeout_ctx(self):
        @asynccontextmanager
        async def _ctx(_delay):
            raise asyncio.TimeoutError()
            yield  # noqa: unreachable – required to make this an async generator

        return _ctx

    @pytest.mark.asyncio
    async def test_yields_timeout_chunk(self, manager, mock_pool, timeout_ctx, monkeypatch):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance())
        mock_pool.acquire.return_value = container
        monkeypatch.setattr("src.internal.container_manager.async_timeout", timeout_ctx)

        results = [chunk async for chunk in manager.stream_execute("/media/code/script.py")]

        assert results == [{"type": "timeout"}]

    @pytest.mark.asyncio
    async def test_kills_container_on_timeout(self, manager, mock_pool, timeout_ctx, monkeypatch):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance())
        mock_pool.acquire.return_value = container
        monkeypatch.setattr("src.internal.container_manager.async_timeout", timeout_ctx)

        async for _ in manager.stream_execute("/media/code/script.py"):
            pass

        container.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_releases_container_after_timeout(self, manager, mock_pool, timeout_ctx, monkeypatch):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance())
        mock_pool.acquire.return_value = container
        monkeypatch.setattr("src.internal.container_manager.async_timeout", timeout_ctx)

        async for _ in manager.stream_execute("/media/code/script.py"):
            pass

        mock_pool.release.assert_called_once_with(container)

    @pytest.mark.asyncio
    async def test_kill_failure_is_suppressed_on_timeout(self, manager, mock_pool, timeout_ctx, monkeypatch):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance())
        container.kill.side_effect = Exception("already dead")
        mock_pool.acquire.return_value = container
        monkeypatch.setattr("src.internal.container_manager.async_timeout", timeout_ctx)

        # Must not raise even if kill() fails
        results = [chunk async for chunk in manager.stream_execute("/media/code/script.py")]

        assert results == [{"type": "timeout"}]


class TestStreamExecuteDockerError:
    @pytest.mark.asyncio
    async def test_docker_error_on_exec_yields_error_chunk(self, manager, mock_pool):
        container = make_mock_container()
        container.exec = AsyncMock(
            side_effect=aiodocker.exceptions.DockerError(500, "container exec failed")
        )
        mock_pool.acquire.return_value = container

        results = [chunk async for chunk in manager.stream_execute("/media/code/script.py")]

        assert len(results) == 1
        assert results[0]["type"] == "error"
        assert "container exec failed" in results[0]["message"]

    @pytest.mark.asyncio
    async def test_docker_error_releases_container(self, manager, mock_pool):
        container = make_mock_container()
        container.exec = AsyncMock(
            side_effect=aiodocker.exceptions.DockerError(500, "exec failed")
        )
        mock_pool.acquire.return_value = container

        async for _ in manager.stream_execute("/media/code/script.py"):
            pass

        mock_pool.release.assert_called_once_with(container)

    @pytest.mark.asyncio
    async def test_docker_error_during_stream_read_yields_error(self, manager, mock_pool):
        container = make_mock_container()
        exec_instance = _make_exec_instance()

        @asynccontextmanager
        async def _error_stream(_delay=None):
            stream = MagicMock()
            stream.read_out = AsyncMock(
                side_effect=aiodocker.exceptions.DockerError(500, "stream broken")
            )
            yield stream

        exec_instance.start = MagicMock(return_value=_error_stream())
        container.exec = AsyncMock(return_value=exec_instance)
        mock_pool.acquire.return_value = container

        results = [chunk async for chunk in manager.stream_execute("/media/code/script.py")]

        assert results[0]["type"] == "error"
        mock_pool.release.assert_called_once_with(container)


class TestReleaseGuarantee:
    @pytest.mark.asyncio
    async def test_container_released_even_when_inspect_raises(self, manager, mock_pool):
        container = make_mock_container()
        exec_instance = _make_exec_instance()
        exec_instance.inspect = AsyncMock(side_effect=aiodocker.exceptions.DockerError(500, "inspect failed"))
        container.exec = AsyncMock(return_value=exec_instance)
        mock_pool.acquire.return_value = container

        async for _ in manager.stream_execute("/media/code/script.py"):
            pass

        mock_pool.release.assert_called_once_with(container)
