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
