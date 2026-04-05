import re
from pathlib import Path
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
    source = Path("factory_analytics/templates/history.html").read_text()
    assert "evidenceHtml" in source
    assert "object-cover" in source


def test_history_page_renders_llm_response_hooks():
    source = Path("factory_analytics/templates/history.html").read_text()
    assert "No extended analysis available." in source
    assert "s.notes ||" in source


def test_history_page_renders_group_result_badge_hooks():
    source = Path("factory_analytics/templates/history.html").read_text()
    assert "Group: ${s.group_name}" in source
    assert "group_name" in source


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


def test_photos_modal_uses_evidence_frames_gallery():
    source = Path("factory_analytics/static/photos.js").read_text()
    assert "evidence_frames" in source
    assert "modalFrames" in source


def test_dashboard_and_efficiency_js_use_evidence_frames():
    app_js = Path("factory_analytics/static/app.js").read_text()
    eff_js = Path("factory_analytics/static/efficiency.js").read_text()
    assert "evidence_frames" in app_js
    assert "evidence_frames" in eff_js


def test_ui_javascript_uses_new_label_set():
    app_js = Path("factory_analytics/static/app.js").read_text()
    eff_js = Path("factory_analytics/static/efficiency.js").read_text()
    photos_js = Path("factory_analytics/static/photos.js").read_text()
    photos_html = Path("factory_analytics/templates/photos.html").read_text()
    history_html = Path("factory_analytics/templates/history.html").read_text()

    assert "not_working" in app_js
    assert "no_person" in app_js
    assert "not_working" in eff_js
    assert "no_person" in eff_js
    assert "not_working" in photos_js
    assert "no_person" in photos_js
    assert 'option value="not_working"' in photos_html
    assert 'option value="no_person"' in photos_html
    assert 'option value="not_working"' in history_html
    assert 'option value="no_person"' in history_html


def test_jobs_ui_shows_model_column_and_value():
    jobs_html = Path("factory_analytics/templates/jobs.html").read_text()
    db_source = Path("factory_analytics/database.py").read_text()

    assert "Model" in jobs_html
    assert "job.model_used" in jobs_html
    assert "AS model_used" in db_source


def test_history_template_uses_evidence_frames_and_single_init_hook():
    source = Path("factory_analytics/templates/history.html").read_text()
    assert "evidence_frames" in source
    assert source.count("DOMContentLoaded") == 1
    assert "window.addEventListener('load'" not in source


def test_photos_js_avoids_inline_segment_json_onclick():
    source = Path("factory_analytics/static/photos.js").read_text()
    assert "JSON.stringify(p).replace" not in source


def test_photos_cards_and_modal_show_model_name():
    photos_js = Path("factory_analytics/static/photos.js").read_text()
    photos_html = Path("factory_analytics/templates/photos.html").read_text()
    assert "Model:" in photos_js
    assert "p.model_used" in photos_js
    assert "modalModel" in photos_html


def test_efficiency_drilldown_markup_includes_model_and_job_detail_hooks():
    eff_html = Path("factory_analytics/templates/efficiency.html").read_text()
    eff_js = Path("factory_analytics/static/efficiency.js").read_text()
    assert "popoverSegments" in eff_html
    assert "Open Job Details" in eff_js
    assert "model_used" in eff_js
    assert "No image" in eff_js


def test_daily_grid_popover_uses_per_cell_camera():
    """Popover must show the clicked cell's camera, not the first camera."""
    eff_js = Path("factory_analytics/static/efficiency.js").read_text()
    # Must NOT hardcode the first camera via cameraData[camIds[0]]
    assert "cameraData[camIds[0]]" not in eff_js
    # Should derive camera_id from the cell's own segment data
    assert "segs[0].camera_id" in eff_js


def test_job_details_surface_shows_model_metadata():
    """Job details modal must surface model_used in the info block."""
    jobs_html = Path("factory_analytics/templates/jobs.html").read_text()
    assert "Model" in jobs_html
    assert "modal-job-info" in jobs_html
    assert "job.model_used" in jobs_html or "model_used" in jobs_html


def test_report_surfaces_show_model_name():
    history_html = Path("factory_analytics/templates/history.html").read_text()
    app_js = Path("factory_analytics/static/app.js").read_text()
    dashboard_html = Path("factory_analytics/templates/dashboard.html").read_text()
    assert "Model" in history_html
    assert "model_used" in history_html
    assert "model_used" in app_js
    assert "reportView" in dashboard_html
    # Verify dashboard report surface renders model name
    assert "reportView" in app_js
    assert "Model:" in app_js
