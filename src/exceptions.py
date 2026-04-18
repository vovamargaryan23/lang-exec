from fastapi import status
from fastapi.exceptions import HTTPException


class LanguageNotFoundException(HTTPException):
    def __init__(self, lang: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid language specified: {lang}!",
        )


class DockerInfrastructureError(HTTPException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Infrastructure unavailable: {message}",
        )