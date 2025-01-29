from fastapi import FastAPI

from src.config import APP_NAME, APP_DESCRIPTION

from src.routers import code_exec_router
from src.exception_handlers import lang_not_found_exception_handler, LanguageNotFoundException


app = FastAPI(title=APP_NAME, 
                  description=APP_DESCRIPTION)

app.include_router(code_exec_router)
app.add_exception_handler(LanguageNotFoundException, lang_not_found_exception_handler)