from unittest.mock import AsyncMock, MagicMock

import pytest

from src.internal.container_manager import ActiveExecution, ContainerManager
from src.internal.strategies.base_strategy import PreparedExecution
from src.internal.strategies.java_strategy import JavaStrategy


@pytest.fixture
def mock_manager() -> MagicMock:
    manager = MagicMock(spec=ContainerManager)
    active = MagicMock(spec=ActiveExecution)
    manager.prepare = AsyncMock(return_value=active)
    return manager


@pytest.fixture
def strategy(mock_manager) -> JavaStrategy:
    return JavaStrategy(container_manager=mock_manager)


@pytest.fixture
def mock_settings(tmp_path, monkeypatch):
    settings = MagicMock()
    settings.volume_path = tmp_path
    monkeypatch.setattr("src.internal.strategies.base_strategy.settings", settings)
    return settings


class TestPrepareExecution:
    async def test_returns_prepared_execution(self, strategy, mock_settings):
        result = await strategy.prepare_execution(
            "class Main { public static void main(String[] a) {} }"
        )
        assert isinstance(result, PreparedExecution)

    async def test_writes_java_extension_file(self, strategy, mock_settings, tmp_path):
        await strategy.prepare_execution("public class Hello {}")

        java_files = list(tmp_path.glob("*.java"))
        assert len(java_files) == 1

    async def test_writes_code_to_file(self, strategy, mock_settings, tmp_path):
        code = "public class Main { public static void main(String[] a) { System.out.println(1); } }"

        await strategy.prepare_execution(code)

        java_files = list(tmp_path.glob("*.java"))
        assert java_files[0].read_text() == code

    async def test_random_file_names_prevent_collisions(self, strategy, mock_settings, tmp_path):
        code = "public class Main { public static void main(String[] a) {} }"
        await strategy.prepare_execution(code)
        await strategy.prepare_execution(code)

        java_files = list(tmp_path.glob("*.java"))
        assert len(java_files) == 2

    async def test_passes_file_path_to_container_manager(
        self, strategy, mock_manager, mock_settings, tmp_path
    ):
        await strategy.prepare_execution("public class X {}")

        java_files = list(tmp_path.glob("*.java"))
        mock_manager.prepare.assert_called_once_with(str(java_files[0]))
