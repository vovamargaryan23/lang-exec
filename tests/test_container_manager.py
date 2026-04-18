import asyncio
import contextlib
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import aiodocker.exceptions
import pytest

from src.exceptions import DockerInfrastructureError
from src.internal.container_manager import ActiveExecution, ContainerManager
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


def _make_active(container, mock_pool) -> ActiveExecution:
    return ActiveExecution(
        container=container,
        pool=mock_pool,
        cmd=["python3", "/media/code/script.py"],
    )


class TestContainerManagerPrepare:
    async def test_returns_active_execution(self, manager, mock_pool):
        container = make_mock_container()
        mock_pool.acquire.return_value = container

        result = await manager.prepare("/media/code/script.py")

        assert isinstance(result, ActiveExecution)
        mock_pool.acquire.assert_called_once()

    async def test_builds_cmd_from_pool(self, manager, mock_pool):
        mock_pool.acquire.return_value = make_mock_container()
        mock_pool.build_exec_cmd.return_value = ["python3", "-B", "/media/code/script.py"]

        result = await manager.prepare("/media/code/script.py")

        mock_pool.build_exec_cmd.assert_called_once_with("/media/code/script.py")
        assert result._cmd == ["python3", "-B", "/media/code/script.py"]

    async def test_raises_docker_infrastructure_error_when_acquire_fails(self, manager, mock_pool):
        mock_pool.acquire.side_effect = aiodocker.exceptions.DockerError(500, "no containers")

        with pytest.raises(DockerInfrastructureError) as exc_info:
            await manager.prepare("/media/code/script.py")

        assert exc_info.value.status_code == 503

    async def test_wraps_generic_exception_as_infrastructure_error(self, manager, mock_pool):
        mock_pool.acquire.side_effect = RuntimeError("pool broken")

        with pytest.raises(DockerInfrastructureError):
            await manager.prepare("/media/code/script.py")


class TestActiveExecutionSuccess:
    async def test_yields_output_chunks_then_exit(self, mock_pool):
        container = make_mock_container()
        container.exec = AsyncMock(
            return_value=_make_exec_instance(
                make_mock_message("Hello\n"),
                make_mock_message("World\n"),
                exit_code=0,
            )
        )
        active = _make_active(container, mock_pool)

        results = [chunk async for chunk in active.stream()]

        assert results == [
            {"type": "output", "content": "Hello\n"},
            {"type": "output", "content": "World\n"},
            {"type": "exit", "return_code": 0},
        ]

    async def test_no_output_yields_only_exit(self, mock_pool):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance(exit_code=0))
        active = _make_active(container, mock_pool)

        results = [chunk async for chunk in active.stream()]

        assert results == [{"type": "exit", "return_code": 0}]

    async def test_non_zero_exit_code_is_propagated(self, mock_pool):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance(exit_code=2))
        active = _make_active(container, mock_pool)

        results = [chunk async for chunk in active.stream()]

        assert results[-1] == {"type": "exit", "return_code": 2}

    async def test_releases_container_after_streaming(self, mock_pool):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance(exit_code=0))
        active = _make_active(container, mock_pool)

        async for _ in active.stream():
            pass

        mock_pool.release.assert_called_once_with(container)


class TestActiveExecutionTimeout:
    @pytest.fixture
    def timeout_ctx(self):
        @asynccontextmanager
        async def _ctx(_delay):
            raise asyncio.TimeoutError()
            yield  # noqa: unreachable

        return _ctx

    async def test_yields_timeout_chunk(self, mock_pool, timeout_ctx, monkeypatch):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance())
        active = _make_active(container, mock_pool)
        monkeypatch.setattr("src.internal.container_manager.async_timeout", timeout_ctx)

        results = [chunk async for chunk in active.stream()]

        assert results == [{"type": "timeout"}]

    async def test_kills_container_on_timeout(self, mock_pool, timeout_ctx, monkeypatch):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance())
        active = _make_active(container, mock_pool)
        monkeypatch.setattr("src.internal.container_manager.async_timeout", timeout_ctx)

        async for _ in active.stream():
            pass

        container.kill.assert_called_once()

    async def test_releases_container_after_timeout(self, mock_pool, timeout_ctx, monkeypatch):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance())
        active = _make_active(container, mock_pool)
        monkeypatch.setattr("src.internal.container_manager.async_timeout", timeout_ctx)

        async for _ in active.stream():
            pass

        mock_pool.release.assert_called_once_with(container)

    async def test_kill_failure_is_suppressed_on_timeout(self, mock_pool, timeout_ctx, monkeypatch):
        container = make_mock_container()
        container.exec = AsyncMock(return_value=_make_exec_instance())
        container.kill.side_effect = Exception("already dead")
        active = _make_active(container, mock_pool)
        monkeypatch.setattr("src.internal.container_manager.async_timeout", timeout_ctx)

        results = [chunk async for chunk in active.stream()]

        assert results == [{"type": "timeout"}]


class TestActiveExecutionDockerError:
    async def test_docker_error_on_exec_yields_infrastructure_error_chunk(self, mock_pool):
        container = make_mock_container()
        container.exec = AsyncMock(
            side_effect=aiodocker.exceptions.DockerError(500, "container exec failed")
        )
        active = _make_active(container, mock_pool)

        results = [chunk async for chunk in active.stream()]

        assert len(results) == 1
        assert results[0]["type"] == "infrastructure_error"
        assert "container exec failed" in results[0]["message"]

    async def test_docker_error_releases_container(self, mock_pool):
        container = make_mock_container()
        container.exec = AsyncMock(
            side_effect=aiodocker.exceptions.DockerError(500, "exec failed")
        )
        active = _make_active(container, mock_pool)

        async for _ in active.stream():
            pass

        mock_pool.release.assert_called_once_with(container)

    async def test_docker_error_during_stream_read_yields_infrastructure_error(self, mock_pool):
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
        active = _make_active(container, mock_pool)

        results = [chunk async for chunk in active.stream()]

        assert results[0]["type"] == "infrastructure_error"
        mock_pool.release.assert_called_once_with(container)

    async def test_container_released_even_when_inspect_raises(self, mock_pool):
        container = make_mock_container()
        exec_instance = _make_exec_instance()
        exec_instance.inspect = AsyncMock(
            side_effect=aiodocker.exceptions.DockerError(500, "inspect failed")
        )
        container.exec = AsyncMock(return_value=exec_instance)
        active = _make_active(container, mock_pool)

        async for _ in active.stream():
            pass

        mock_pool.release.assert_called_once_with(container)
