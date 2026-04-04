import pytest
from unittest.mock import MagicMock
from factory_analytics.services import AnalyticsService


@pytest.fixture
def service():
    db = MagicMock()
    db.get_settings.return_value = {
        "llm_url": "http://localhost:11434",
        "llm_vision_model": "qwen3.5:9b",
    }
    return AnalyticsService(db)


def test_test_llm_api_returns_model_status(service):
    mock_client = MagicMock()
    mock_client.health.return_value = {"ok": True, "models": ["qwen3.5:9b", "llama3"]}
    service.ollama_client = MagicMock(return_value=mock_client)

    result = service.test_ollama_api()
    assert result["ok"] is True
    assert result["model_found"] is True
    assert "qwen3.5:9b" in result["message"]
