from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse


async def http_exception_handler(req: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(content={"detail": exc.detail}, status_code=exc.status_code)
