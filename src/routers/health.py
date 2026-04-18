from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

health_router = APIRouter()


@health_router.get("/health")
async def health(request: Request) -> JSONResponse:
    pools = request.app.state.pools
    return JSONResponse({
        "status": "ok",
        "pools": {lang.value: pool.stats for lang, pool in pools.items()},
    })
