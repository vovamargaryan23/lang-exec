import json
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.dependencies import get_executor_service
from src.schemas import CodeExecRequestData
from src.services.code_executor import CodeExecutorService


code_exec_router = APIRouter()


@code_exec_router.post("/execute")
async def execute_code(
    data: CodeExecRequestData,
    service: Annotated[CodeExecutorService, Depends(get_executor_service)],
) -> StreamingResponse:
    stream = service.get_stream(data)

    async def event_generator():
        async for chunk in stream:
            yield f"{json.dumps(chunk)}\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
