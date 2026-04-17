import re

from pydantic import BaseModel, field_validator

_MAX_CODE_BYTES = 64 * 1024  # 64 KB
_SAFE_EXEC_PARAMS = re.compile(r'^[\w\s\-\.]*$')


class CodeExecRequestData(BaseModel):
    language: str
    execution_params: str
    code: str

    @field_validator("code")
    @classmethod
    def validate_code_size(cls, v: str) -> str:
        if len(v.encode()) > _MAX_CODE_BYTES:
            raise ValueError(f"Code exceeds the {_MAX_CODE_BYTES // 1024} KB limit")
        return v

    @field_validator("execution_params")
    @classmethod
    def validate_exec_params(cls, v: str) -> str:
        if v and not _SAFE_EXEC_PARAMS.match(v):
            raise ValueError("execution_params may only contain alphanumeric characters, spaces, hyphens, dots, and underscores")
        return v
