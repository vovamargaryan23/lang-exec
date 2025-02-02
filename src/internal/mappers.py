from typing import Dict

from src.internal.languages import LangEnum


LANGUAGE_TO_IMAGE_NAME_MAP: Dict[LangEnum, str] = {
    LangEnum.PYTHON : "lang-exec-python-executor:latest"
}