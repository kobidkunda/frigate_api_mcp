from pathlib import Path
from fastapi.testclient import TestClient

from factory_analytics.main import app


client = TestClient(app)


def test_processed_events_page_renders():
    response = client.get("/processed-events")
    assert response.status_code == 200
    html = response.text
    assert "Processed Events" in html
    assert "Jobs" in html
    assert "Segments" in html


def test_processed_events_page_has_filters_and_pagination():
    response = client.get("/processed-events")
    html = response.text
    assert 'name="shift"' in html
    assert 'name="from"' in html
    assert 'name="to"' in html
    assert "page-prev" in html
    assert "page-next" in html


def test_processed_events_segments_use_evidence_frames_gallery_hooks():
    source = Path("factory_analytics/static/processed_events.js").read_text()
    assert "evidence_frames" in source
    assert "frames.map" in source
    assert "Evidence ${index + 1}" in source


def test_processed_events_segments_sanitize_evidence_paths():
    source = Path("factory_analytics/static/processed_events.js").read_text()
    assert "function safeProcessedPath" in source
    assert "/^(?:[a-z]+:|\\/\\/)/i.test(trimmed)" in source
    assert "segments[0] !== 'data' || segments[1] !== 'evidence'" in source
