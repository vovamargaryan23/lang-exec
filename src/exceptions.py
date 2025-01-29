from fastapi import status
from fastapi.exceptions import HTTPException


class LanguageNotFoundException(HTTPException):
    def __init__(self, lang: str, *args):
        self.__lang = lang
        self.status_code = status.HTTP_400_BAD_REQUEST
        self.detail = f"Invalid language specified: {lang}!"
        super().__init__(status_code=self.status_code, detail=self.detail)