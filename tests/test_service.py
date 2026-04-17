import pytest
from unittest.mock import AsyncMock, MagicMock

from src.exceptions import LanguageNotFoundException
from src.internal.languages import LangEnum
from src.internal.strategies.base_strategy import BaseStrategy
from src.services.code_executor import CodeExecutorService


async def _dummy_gen():
    yield {"type": "exit", "return_code": 0}


@pytest.fixture
def mock_strategy():
    strategy = MagicMock(spec=BaseStrategy)
    strategy.stream_execute = MagicMock(return_value=_dummy_gen())
    return strategy


@pytest.fixture
def service(mock_strategy):
    return CodeExecutorService(strategies={LangEnum.PYTHON: mock_strategy})


class TestGetStream:
    def test_valid_language_returns_stream(self, service, mock_strategy):
        data = MagicMock()
        data.language = "python"
        data.code = "print(1)"

        stream = service.get_stream(data)

        mock_strategy.stream_execute.assert_called_once_with(data.code)
        assert stream is mock_strategy.stream_execute.return_value

    def test_unknown_language_string_raises(self, service):
        data = MagicMock()
        data.language = "cobol"

        with pytest.raises(LanguageNotFoundException) as exc_info:
            service.get_stream(data)

        assert exc_info.value.status_code == 400
        assert "cobol" in exc_info.value.detail

    def test_language_in_enum_but_missing_strategy_raises(self):
        service_no_python = CodeExecutorService(strategies={})
        data = MagicMock()
        data.language = "python"

        with pytest.raises(LanguageNotFoundException) as exc_info:
            service_no_python.get_stream(data)

        assert exc_info.value.status_code == 400
        assert "python" in exc_info.value.detail

    def test_empty_language_string_raises(self, service):
        data = MagicMock()
        data.language = ""

        with pytest.raises(LanguageNotFoundException):
            service.get_stream(data)
