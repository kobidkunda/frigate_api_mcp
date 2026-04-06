import re
from pathlib import Path
from fastapi.testclient import TestClient

import factory_analytics.main as main_module
from factory_analytics.database import Database
from factory_analytics.services import AnalyticsService

app = main_module.app


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


def test_history_page_renders_all_evidence_thumbnail_hooks():
    source = Path("factory_analytics/templates/history.html").read_text()
    assert "evidenceFrames.map" in source
    assert "frame ${i+1}" in source
    assert "flex gap-1 items-center" in source


def test_history_page_links_rows_to_segment_detail_route():
    source = Path("factory_analytics/templates/history.html").read_text()
    assert "const detailHref = `/history/${s.id}`;" in source
    assert 'href="${detailHref}"' in source
    assert "Open Details" in source


def test_history_detail_page_renders_existing_segment_or_404_until_seeded(tmp_path, monkeypatch):
    db = Database(tmp_path / "history-ui.db")
    service = AnalyticsService(db)
    monkeypatch.setattr(main_module, "db", db)
    monkeypatch.setattr(main_module, "service", service)

    camera = db.upsert_camera("cam_history_route", "Camera History Route")
    job = db.schedule_job(camera["id"], payload={"model": "llava:13b"})
    segment = db.create_segment(
        job_id=job["id"],
        camera_id=camera["id"],
        start_ts="2026-04-06T11:00:00+00:00",
        end_ts="2026-04-06T11:01:00+00:00",
        label="working",
        confidence=0.95,
        notes="History route seed",
        evidence_path="data/evidence/history-route/primary.jpg",
    )
    db.mark_job_finished(
        job["id"],
        "success",
        raw_result={
            "model": "llava:13b",
            "primary_evidence_path": "data/evidence/history-route/primary.jpg",
            "evidence_frames": [
                "data/evidence/history-route/primary.jpg",
                "data/evidence/history-route/frame-2.jpg",
            ],
            "raw": {"detail": "seeded raw detail"},
        },
        snapshot_path="data/evidence/history-route/primary.jpg",
    )
    db.review_segment(segment["id"], "working", "seed review note", "qa-user")

    client = TestClient(app)
    response = client.get(f"/history/{segment['id']}")
    assert response.status_code == 200
    assert "Capture Event Details" in response.text
    assert "Camera History Route" in response.text
    assert "llava:13b" in response.text
    assert "History route seed" in response.text
    assert "seed review note" in response.text
    assert "data/evidence/history-route/primary.jpg" in response.text
    assert "data/evidence/history-route/frame-2.jpg" in response.text
    assert "seeded raw detail" in response.text


def test_history_detail_page_returns_404_for_missing_segment(tmp_path, monkeypatch):
    db = Database(tmp_path / "history-ui-404.db")
    service = AnalyticsService(db)
    monkeypatch.setattr(main_module, "db", db)
    monkeypatch.setattr(main_module, "service", service)

    client = TestClient(app)
    response = client.get("/history/1")
    assert response.status_code == 404


def test_history_detail_template_contains_required_sections():
    source = Path("factory_analytics/templates/history_detail.html").read_text()
    assert "Capture Event Details" in source
    assert "Evidence Frames" in source
    assert "Model" in source
    assert "Raw Result" in source
    assert "Primary Evidence" in source
    assert "Review" in source


def test_history_page_renders_llm_response_hooks():
    source = Path("factory_analytics/templates/history.html").read_text()
    assert "No extended analysis available." in source
    assert "safeNotes" in source
    assert "escapeHtml(s.notes || 'No extended analysis available.')" in source


def test_history_page_renders_group_result_badge_hooks():
    source = Path("factory_analytics/templates/history.html").read_text()
    assert "Group: ${escapeHtml(s.group_name)}" in source
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


def test_jobs_page_reads_job_query_param_for_single_job_filter():
    jobs_html = Path("factory_analytics/templates/jobs.html").read_text()
    main_source = Path("factory_analytics/main.py").read_text()
    db_source = Path("factory_analytics/database.py").read_text()

    assert "new URLSearchParams(window.location.search)" in jobs_html
    assert ".get('job')" in jobs_html or '.get("job")' in jobs_html
    assert "job_id: requestedJobId" in jobs_html
    assert "job_id: int | None = None" in main_source
    assert "job_id: int | None = None" in db_source
    assert "j.id = ?" in db_source


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


def test_job_details_modal_surface_renders_model_metadata_card():
    """Job details modal info block must render model_used in a dedicated card.

    Asserts on the exact infoHtml fragment that showJobDetails() injects into
    #modal-job-info -- something the parent commit's infoHtml did NOT contain.
    """
    jobs_html = Path("factory_analytics/templates/jobs.html").read_text()

    # The modal model card lives inside showJobDetails()'s infoHtml template.
    # The parent commit's infoHtml only had Camera / Status / Type / Duration.
    # The combined label+value fragment below is unique to that modal card:
    #   uppercase mb-1">Model</div> ... font-mono">${job.model_used
    assert 'uppercase mb-1">Model</div>' in jobs_html, (
        "modal info block should have Model label card"
    )
    assert 'font-mono">' in jobs_html and '${job.model_used' in jobs_html, (
        "modal info block should render model_used value"
    )


def test_jobs_modal_uses_evidence_frames_gallery_hooks():
    jobs_html = Path("factory_analytics/templates/jobs.html").read_text()
    assert "evidence_frames" in jobs_html
    assert "modal-snapshot-gallery" in jobs_html
    assert "jobFrames.map" in jobs_html


def test_jobs_modal_sanitizes_evidence_paths_and_preserves_job_filter():
    jobs_html = Path("factory_analytics/templates/jobs.html").read_text()
    assert "function safeJobPath" in jobs_html
    assert "/^(?:[a-z]+:|\\/\\/)/i.test(trimmed)" in jobs_html
    assert "segments[0] !== 'data' || segments[1] !== 'evidence'" in jobs_html
    assert "currentFilters = requestedJobId ? { job_id: requestedJobId } : {};" in jobs_html
    assert "if (requestedJobId) currentFilters.job_id = requestedJobId;" in jobs_html


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
