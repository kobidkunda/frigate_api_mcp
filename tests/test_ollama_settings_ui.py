from fastapi.testclient import TestClient

from factory_analytics.main import app


client = TestClient(app)


def test_settings_page_shows_full_ollama_controls():
    response = client.get("/settings")
    assert response.status_code == 200
    html = response.text
    assert 'name="ollama_url"' in html
    assert 'name="ollama_vision_model"' in html
    assert 'name="ollama_timeout_sec"' in html
    assert 'name="ollama_keep_alive"' in html
    assert 'name="ollama_enabled"' in html
    assert "Test Ollama Vision" in html
