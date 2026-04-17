import pytest
from pydantic import ValidationError

from src.schemas import CodeExecRequestData

_VALID_PAYLOAD = {"language": "python", "code": "print(1)"}


def _make(**overrides):
    return {**_VALID_PAYLOAD, **overrides}


class TestCodeSizeValidation:
    def test_valid_code_passes(self):
        CodeExecRequestData(**_make(code="print(1)"))

    def test_code_at_exact_limit_passes(self):
        code = "a" * (64 * 1024)
        CodeExecRequestData(**_make(code=code))

    def test_code_one_byte_over_limit_fails(self):
        code = "a" * (64 * 1024 + 1)
        with pytest.raises(ValidationError, match="64 KB limit"):
            CodeExecRequestData(**_make(code=code))

    def test_empty_code_passes(self):
        CodeExecRequestData(**_make(code=""))


class TestMissingFields:
    @pytest.mark.parametrize("missing_field", ["language", "code"])
    def test_missing_required_field_fails(self, missing_field: str):
        payload = dict(_VALID_PAYLOAD)
        del payload[missing_field]
        with pytest.raises(ValidationError):
            CodeExecRequestData(**payload)
