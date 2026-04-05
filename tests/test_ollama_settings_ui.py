from fastapi.testclient import TestClient

from factory_analytics.main import app


client = TestClient(app)


def test_settings_page_shows_full_llm_controls():
    response = client.get("/settings")
    assert response.status_code == 200
    html = response.text
    assert 'name="llm_url"' in html
    assert 'name="llm_vision_model"' in html
    assert 'name="llm_timeout_sec"' in html
    assert 'name="llm_enabled"' in html
    assert "Test Connection" in html


def test_settings_page_has_single_llm_api_key_field_and_tests_current_settings():
    response = client.get("/settings")
    assert response.status_code == 200
    html = response.text
    assert html.count('name="llm_api_key"') == 1
    assert "fetch('/api/settings'" in html
    assert "fetch('/api/settings/ollama/test')" in html
    assert "fetch('/api/health')" not in html
