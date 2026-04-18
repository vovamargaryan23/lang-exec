import json

import httpx
import pytest

from src.exceptions import DockerInfrastructureError, LanguageNotFoundException


async def _async_gen(*chunks):
    for chunk in chunks:
        yield chunk


def _parse_ndjson(text: str) -> list[dict]:
    return [json.loads(line) for line in text.strip().splitlines() if line.strip()]


def _mock_execution(*chunks):
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.stream.return_value = _async_gen(*chunks)
    return mock


class TestHealth:
    async def test_health_returns_200(self, http_client: httpx.AsyncClient):
        response = await http_client.get("/health")
        assert response.status_code == 200

    async def test_health_returns_ok_status(self, http_client: httpx.AsyncClient):
        response = await http_client.get("/health")
        assert response.json()["status"] == "ok"

    async def test_health_includes_pool_stats(self, http_client: httpx.AsyncClient):
        response = await http_client.get("/health")
        body = response.json()
        assert "pools" in body
        assert "python" in body["pools"]
        stats = body["pools"]["python"]
        assert stats == {"idle": 2, "capacity": 3, "max_concurrent": 8, "in_use": 1}

    async def test_health_empty_pools_still_returns_ok(self, mock_service, mock_pools):
        from tests.conftest import make_test_app
        app = make_test_app(mock_service, {})
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["pools"] == {}


class TestExecuteSuccess:
    async def test_returns_ndjson_streaming_response(
        self, http_client: httpx.AsyncClient, mock_service
    ):
        chunks = [
            {"type": "output", "content": "Hello, World!\n"},
            {"type": "exit", "return_code": 0},
        ]
        mock_service.prepare_stream.return_value = _mock_execution(*chunks)

        response = await http_client.post(
            "/execute",
            json={"language": "python", "code": "print('Hello')"},
        )

        assert response.status_code == 200
        assert "application/x-ndjson" in response.headers["content-type"]
        assert _parse_ndjson(response.text) == chunks

    async def test_streams_infrastructure_error_chunk(
        self, http_client: httpx.AsyncClient, mock_service
    ):
        chunks = [{"type": "infrastructure_error", "message": "container died"}]
        mock_service.prepare_stream.return_value = _mock_execution(*chunks)

        response = await http_client.post(
            "/execute", json={"language": "python", "code": "pass"}
        )

        assert response.status_code == 200
        assert _parse_ndjson(response.text) == chunks

    async def test_streams_timeout_chunk(
        self, http_client: httpx.AsyncClient, mock_service
    ):
        chunks = [{"type": "timeout"}]
        mock_service.prepare_stream.return_value = _mock_execution(*chunks)

        response = await http_client.post(
            "/execute",
            json={"language": "python", "code": "import time; time.sleep(999)"},
        )

        assert response.status_code == 200
        assert _parse_ndjson(response.text) == chunks

    async def test_multiple_output_chunks_all_streamed(
        self, http_client: httpx.AsyncClient, mock_service
    ):
        chunks = [
            {"type": "output", "content": "line1\n"},
            {"type": "output", "content": "line2\n"},
            {"type": "exit", "return_code": 0},
        ]
        mock_service.prepare_stream.return_value = _mock_execution(*chunks)

        response = await http_client.post(
            "/execute", json={"language": "python", "code": "..."}
        )

        assert _parse_ndjson(response.text) == chunks


class TestExecuteClientErrors:
    async def test_unknown_language_returns_400(
        self, http_client: httpx.AsyncClient, mock_service
    ):
        mock_service.prepare_stream.side_effect = LanguageNotFoundException("ruby")

        response = await http_client.post(
            "/execute", json={"language": "ruby", "code": "puts 'hi'"}
        )

        assert response.status_code == 400
        assert "ruby" in response.json()["detail"]

    async def test_malformed_json_returns_422(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/execute",
            content=b"not json at all",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    async def test_missing_language_field_returns_422(self, http_client: httpx.AsyncClient):
        response = await http_client.post("/execute", json={"code": "print(1)"})
        assert response.status_code == 422

    async def test_missing_code_field_returns_422(self, http_client: httpx.AsyncClient):
        response = await http_client.post("/execute", json={"language": "python"})
        assert response.status_code == 422

    async def test_empty_body_returns_422(self, http_client: httpx.AsyncClient):
        response = await http_client.post("/execute", json={})
        assert response.status_code == 422

    async def test_code_exceeding_64kb_returns_422(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/execute",
            json={"language": "python", "code": "a" * (64 * 1024 + 1)},
        )
        assert response.status_code == 422
        assert "64 KB" in response.text


class TestExecuteServerErrors:
    async def test_docker_infrastructure_error_returns_503(
        self, http_client: httpx.AsyncClient, mock_service
    ):
        mock_service.prepare_stream.side_effect = DockerInfrastructureError("no containers available")

        response = await http_client.post(
            "/execute", json={"language": "python", "code": "pass"}
        )

        assert response.status_code == 503
        assert "Infrastructure unavailable" in response.json()["detail"]

    async def test_infrastructure_error_detail_contains_message(
        self, http_client: httpx.AsyncClient, mock_service
    ):
        mock_service.prepare_stream.side_effect = DockerInfrastructureError("pool exhausted")

        response = await http_client.post(
            "/execute", json={"language": "python", "code": "pass"}
        )

        assert "pool exhausted" in response.json()["detail"]
