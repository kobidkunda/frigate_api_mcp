import re
from fastapi.testclient import TestClient

from factory_analytics.main import app


def test_dashboard_page_renders_and_has_accessible_nav():
    client = TestClient(app)
    r = client.get("/dashboard")
    assert r.status_code == 200
    html = r.text
    # Basic smoke checks for UI/UX baselines
    assert "Factory Analytics" in html
    # Skip link for keyboard users
    assert 'class="skip-link"' in html
    # Navigation landmark
    assert re.search(r"<nav[^>]*role=\"navigation\"", html)


def test_settings_page_renders_and_form_present():
    client = TestClient(app)
    r = client.get("/settings")
    assert r.status_code == 200
    html = r.text
    assert "Settings" in html
    # Ensure settings form and key inputs exist
    assert "settingsForm" in html
    assert "frigate_url" in html
    assert "ollama_url" in html


def test_history_page_renders_and_has_filters():
    client = TestClient(app)
    r = client.get("/history")
    assert r.status_code == 200
    html = r.text
    assert "Filters" in html
    # Camera filter select present
    assert 'name="camera_id"' in html


def test_history_page_renders_inline_evidence_preview_hooks():
    client = TestClient(app)
    r = client.get("/history")
    assert r.status_code == 200
    html = r.text
    assert 'class="history-evidence-link"' in html
    assert 'class="history-evidence-image"' in html


def test_history_page_renders_llm_response_hooks():
    client = TestClient(app)
    r = client.get("/history")
    assert r.status_code == 200
    html = r.text
    assert 'class="history-llm-notes"' in html
    assert 'class="history-merge-meta"' in html


def test_history_page_renders_group_result_badge_hooks():
    client = TestClient(app)
    r = client.get("/history")
    assert r.status_code == 200
    html = r.text
    assert 'class="history-group-badge"' in html
    assert 'class="history-group-name"' in html


def test_logs_page_renders_and_log_view_present():
    client = TestClient(app)
    r = client.get("/logs")
    assert r.status_code == 200
    html = r.text
    assert "Logs" in html
    assert "logView" in html


def test_logs_tail_endpoint_returns_structured_payload():
    client = TestClient(app)
    r = client.get("/api/logs/tail?name=api&lines=5")
    assert r.status_code == 200
    payload = r.json()
    assert payload["name"] == "api"
    assert "content" in payload


def test_control_center_page_contains_monitoring_hooks():
    client = TestClient(app)
    r = client.get("/control-center")
    assert r.status_code == 200
    html = r.text
    assert 'id="config-files"' in html
    assert 'id="mcp-status"' in html


def test_api_explorer_page_contains_catalog_hooks():
    client = TestClient(app)
    r = client.get("/api-explorer")
    assert r.status_code == 200
    html = r.text
    assert 'id="api-catalog"' in html
    assert 'id="skill-usage-notes"' in html
