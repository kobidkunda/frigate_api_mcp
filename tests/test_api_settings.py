from fastapi.testclient import TestClient
from factory_analytics.main import app

client = TestClient(app)


def test_ollama_status_endpoint():
    response = client.get("/api/settings/ollama/status")
    assert response.status_code == 200
    payload = response.json()
    assert "ok" in payload
    assert "model_found" in payload
