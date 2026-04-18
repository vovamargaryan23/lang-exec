import logging
from contextlib import asynccontextmanager

import aiodocker
from fastapi import FastAPI

from src.config import APP_NAME, APP_DESCRIPTION
from src.exception_handlers import http_exception_handler
from src.exceptions import DockerInfrastructureError, LanguageNotFoundException
from src.internal.factories import create_pools, create_strategies, shutdown_pools
from src.internal.settings import settings
from src.logging_config import setup_logging
from src.routers import code_exec_router, health_router
from src.services.code_executor import CodeExecutorService

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    docker = aiodocker.Docker(url=settings.docker_sock_path)
    pools = await create_pools(docker)
    app.state.pools = pools
    app.state.executor_service = CodeExecutorService(strategies=create_strategies(pools))
    logger.info("Application started")

    yield

    await shutdown_pools(pools)
    await docker.close()
    logger.info("Application stopped")


app = FastAPI(title=APP_NAME, description=APP_DESCRIPTION, lifespan=lifespan)

app.include_router(code_exec_router)
app.include_router(health_router)
app.add_exception_handler(LanguageNotFoundException, http_exception_handler)
app.add_exception_handler(DockerInfrastructureError, http_exception_handler)
