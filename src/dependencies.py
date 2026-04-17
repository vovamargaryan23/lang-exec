from fastapi import Request

from src.services.code_executor import CodeExecutorService


def get_executor_service(request: Request) -> CodeExecutorService:
    return request.app.state.executor_service
