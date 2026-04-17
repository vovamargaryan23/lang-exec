from pydantic import BaseModel, field_validator

_MAX_CODE_BYTES = 64 * 1024  # 64 KB


class CodeExecRequestData(BaseModel):
    language: str
    code: str

    @field_validator("code")
    @classmethod
    def validate_code_size(cls, v: str) -> str:
        if len(v.encode()) > _MAX_CODE_BYTES:
            raise ValueError(f"Code exceeds the {_MAX_CODE_BYTES // 1024} KB limit")
        return v
