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


def test_logs_page_renders_and_log_view_present():
    client = TestClient(app)
    r = client.get("/logs")
    assert r.status_code == 200
    html = r.text
    assert "Logs" in html
    assert "logView" in html
