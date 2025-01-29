from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import status

from src.exceptions import LanguageNotFoundException

async def lang_not_found_exception_handler(req: Request, exception: LanguageNotFoundException):
    return JSONResponse(content={"detail":exception.detail},
                        status_code=exception.status_code)