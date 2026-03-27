from fastapi.testclient import TestClient

from factory_analytics.main import app


client = TestClient(app)


def test_ollama_test_endpoint_returns_structured_payload():
    response = client.post("/api/settings/ollama/test")
    assert response.status_code in (200, 503, 500)
    payload = response.json()
    assert "ok" in payload
    assert "message" in payload
