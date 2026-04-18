import pytest
from unittest.mock import AsyncMock, MagicMock

from src.exceptions import LanguageNotFoundException
from src.internal.languages import LangEnum
from src.internal.strategies.base_strategy import BaseStrategy, PreparedExecution
from src.services.code_executor import CodeExecutorService


@pytest.fixture
def mock_prepared():
    return MagicMock(spec=PreparedExecution)


@pytest.fixture
def mock_strategy(mock_prepared):
    strategy = MagicMock(spec=BaseStrategy)
    strategy.prepare_execution = AsyncMock(return_value=mock_prepared)
    return strategy


@pytest.fixture
def service(mock_strategy):
    return CodeExecutorService(strategies={LangEnum.PYTHON: mock_strategy})


class TestPrepareStream:
    async def test_valid_language_calls_strategy_and_returns_execution(
        self, service, mock_strategy, mock_prepared
    ):
        data = MagicMock()
        data.language = "python"
        data.code = "print(1)"

        result = await service.prepare_stream(data)

        mock_strategy.prepare_execution.assert_called_once_with(data.code)
        assert result is mock_prepared

    async def test_unknown_language_string_raises(self, service):
        data = MagicMock()
        data.language = "cobol"

        with pytest.raises(LanguageNotFoundException) as exc_info:
            await service.prepare_stream(data)

        assert exc_info.value.status_code == 400
        assert "cobol" in exc_info.value.detail

    async def test_language_in_enum_but_missing_strategy_raises(self):
        service_no_python = CodeExecutorService(strategies={})
        data = MagicMock()
        data.language = "python"

        with pytest.raises(LanguageNotFoundException) as exc_info:
            await service_no_python.prepare_stream(data)

        assert exc_info.value.status_code == 400
        assert "python" in exc_info.value.detail

    async def test_empty_language_string_raises(self, service):
        data = MagicMock()
        data.language = ""

        with pytest.raises(LanguageNotFoundException):
            await service.prepare_stream(data)

    async def test_java_language_routes_to_java_strategy(self):
        java_strategy = MagicMock(spec=BaseStrategy)
        java_strategy.prepare_execution = AsyncMock(return_value=MagicMock())
        svc = CodeExecutorService(strategies={LangEnum.JAVA: java_strategy})
        data = MagicMock()
        data.language = "java"
        data.code = "class Main { public static void main(String[] a) {} }"

        await svc.prepare_stream(data)

        java_strategy.prepare_execution.assert_called_once_with(data.code)
