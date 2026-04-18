from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import FastAPI

from src.exception_handlers import http_exception_handler
from src.exceptions import DockerInfrastructureError, LanguageNotFoundException
from src.internal.container_pool import ContainerPool
from src.internal.languages import LangEnum
from src.routers import code_exec_router, health_router
from src.services.code_executor import CodeExecutorService


def make_test_app(service: CodeExecutorService, pools: dict | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(code_exec_router)
    app.include_router(health_router)
    app.add_exception_handler(LanguageNotFoundException, http_exception_handler)
    app.add_exception_handler(DockerInfrastructureError, http_exception_handler)
    app.state.executor_service = service
    app.state.pools = pools or {}
    return app


def make_mock_container() -> MagicMock:
    container = MagicMock()
    container.start = AsyncMock()
    container.delete = AsyncMock()
    container.kill = AsyncMock()
    container.exec = AsyncMock()
    return container


def make_mock_message(data: str) -> MagicMock:
    msg = MagicMock()
    msg.data = data.encode()
    return msg


@asynccontextmanager
async def mock_exec_stream(*messages):
    stream = AsyncMock()
    stream.read_out = AsyncMock(side_effect=[*messages, None])
    yield stream


@pytest.fixture
def mock_service() -> MagicMock:
    return MagicMock(spec=CodeExecutorService)


@pytest.fixture
def mock_pools() -> dict:
    pool = MagicMock(spec=ContainerPool)
    pool.stats = {"idle": 2, "capacity": 3, "max_concurrent": 8, "in_use": 1}
    return {LangEnum.PYTHON: pool}


@pytest.fixture
def test_app(mock_service: MagicMock, mock_pools: dict) -> FastAPI:
    return make_test_app(mock_service, mock_pools)


@pytest.fixture
async def http_client(test_app: FastAPI) -> httpx.AsyncClient:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def mock_docker() -> MagicMock:
    docker = MagicMock()
    docker.images = MagicMock()
    docker.images.get = AsyncMock(return_value={
        "Config": {"Labels": {"lang.exec": "python3"}}
    })
    docker.containers = MagicMock()
    docker.containers.create = AsyncMock(side_effect=lambda _: make_mock_container())
    return docker


@pytest.fixture
def pool_settings(monkeypatch):
    mock = MagicMock()
    mock.exec_pool_size = 2
    mock.exec_pool_overflow = 1
    mock.host_volume_path = "/tmp/code"
    mock.volume_path = "/media/code"
    mock.exec_mem_limit_bytes = 128 * 1024 * 1024
    mock.exec_cpu_limit_nanos = 1_000_000_000
    mock.exec_pids_limit = 64
    monkeypatch.setattr("src.internal.container_pool.settings", mock)
    return mock


@pytest.fixture
def pool(mock_docker: MagicMock, pool_settings: MagicMock) -> ContainerPool:
    return ContainerPool(docker=mock_docker, image="test-image:latest")
