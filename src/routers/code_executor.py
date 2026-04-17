import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.schemas import CodeExecRequestData
from src.services import CodeExecutorService


code_exec_router = APIRouter()
CODE_EXECUTOR_SERVICE = CodeExecutorService()


@code_exec_router.post("/execute")
async def execute_code(data: CodeExecRequestData) -> StreamingResponse:
    # Validate language before StreamingResponse so HTTPException propagates correctly.
    stream = CODE_EXECUTOR_SERVICE.get_stream(data)

    async def event_generator():
        async for chunk in stream:
            yield f"{json.dumps(chunk)}\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
