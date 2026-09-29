import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.endpoints.generate_team_insight import get_llm_client
from tests.core import fixtures


@pytest.fixture
def client():
    return TestClient(app)


class MockAPILLMClient:
    def __init__(self, response_json):
        self.response_json = response_json

    def complete(self, prompt, timeout_seconds=10):
        return self.response_json


def test_health_check_endpoint(client):
    """Garante que o endpoint de health check responde 200 OK."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_team_insight_endpoint_success(client):
    """Garante que a requisição POST ao endpoint gera as métricas e o insight corretamente."""
    mock_response = json.dumps({
        "summary": "The team merged one pull request with an average cycle time of 24 hours.",
        "recommendations": ["Continue monitoring pull request cycle time."]
    })
    app.dependency_overrides[get_llm_client] = lambda: MockAPILLMClient(mock_response)

    try:
        response = client.post(
            "/api/v1/generate_team_insight",
            json={
                "team_id": fixtures.team_id,
                "events": fixtures.test_events,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data == fixtures.expected_complete_result
    finally:
        app.dependency_overrides.clear()


def test_generate_team_insight_endpoint_validation_error(client):
    """Garante que eventos malformados retornam status 400 Bad Request."""
    mock_response = json.dumps({"summary": "ok", "recommendations": ["ok"]})
    app.dependency_overrides[get_llm_client] = lambda: MockAPILLMClient(mock_response)

    try:
        response = client.post(
            "/api/v1/generate_team_insight",
            json={
                "team_id": "platform",
                "events": [{"type": "pr_opened"}],  # Sem id e sem timestamp
            }
        )
        assert response.status_code == 400
        assert "Timestamp" in response.json()["detail"] or "timestamp" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_generate_team_insight_endpoint_llm_failure(client):
    """Garante que falhas no LLM retornam status 502 Bad Gateway."""
    class FailingLLMClient:
        def complete(self, prompt, timeout_seconds=10):
            raise TimeoutError("LLM upstream timeout")

    app.dependency_overrides[get_llm_client] = lambda: FailingLLMClient()

    try:
        response = client.post(
            "/api/v1/generate_team_insight",
            json={
                "team_id": fixtures.team_id,
                "events": fixtures.test_events,
            }
        )
        assert response.status_code == 502
        assert "Falha no processamento pelo serviço LLM" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_get_llm_client_default_returns_dev_client():
    """Valida que o provedor padrão de dependência do LLM client retorna um cliente funcional."""
    client = get_llm_client()
    response = client.complete("test prompt", timeout_seconds=10)
    data = json.loads(response)
    assert "summary" in data
    assert "recommendations" in data


def test_lambda_handler_invocation():
    """Valida que o handler AWS Lambda via Mangum processa requisições HTTP."""
    from app.main import handler

    event = {
        "version": "2.0",
        "routeKey": "GET /api/v1/health",
        "rawPath": "/api/v1/health",
        "rawQueryString": "",
        "headers": {
            "accept": "application/json",
            "host": "test.lambda-url.us-east-1.on.aws"
        },
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/api/v1/health",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest"
            }
        },
        "isBase64Encoded": False
    }

    context = {}
    response = handler(event, context)
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"status": "ok"}
