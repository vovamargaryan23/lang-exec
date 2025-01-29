from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.exceptions import LanguageNotFoundException
from src.schemas import CodeExecRequestData, CodeExecResponseData
from src.services import CodeExecutorService


code_exec_router = APIRouter()
CODE_EXECUTOR_SERVICE = CodeExecutorService()

@code_exec_router.post("/execute")
async def execute_code(data: CodeExecRequestData) -> JSONResponse:
    res_data: CodeExecResponseData = await CODE_EXECUTOR_SERVICE.execute(data)
    return JSONResponse(content=jsonable_encoder(res_data))