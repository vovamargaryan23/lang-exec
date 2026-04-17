from fastapi import APIRouter
from fastapi.responses import JSONResponse

health_router = APIRouter()


@health_router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
