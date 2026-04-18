import json
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.dependencies import get_executor_service
from src.rate_limiter import require_rate_limit
from src.schemas import CodeExecRequestData
from src.services.code_executor import CodeExecutorService


code_exec_router = APIRouter()


@code_exec_router.post("/execute", dependencies=[Depends(require_rate_limit)])
async def execute_code(
    data: CodeExecRequestData,
    service: Annotated[CodeExecutorService, Depends(get_executor_service)],
) -> StreamingResponse:
    # Must raise before StreamingResponse is returned - once streaming starts the status code is committed.
    execution = await service.prepare_stream(data)

    async def event_generator():
        async for chunk in execution.stream():
            yield f"{json.dumps(chunk)}\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
