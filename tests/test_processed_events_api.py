from fastapi.testclient import TestClient

from factory_analytics.main import app


client = TestClient(app)


def test_processed_jobs_api_returns_paginated_payload():
    response = client.get("/api/processed-events/jobs?page=1&page_size=25")
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert "total" in payload
    assert "page" in payload


def test_processed_segments_api_returns_paginated_payload():
    response = client.get("/api/processed-events/segments?page=1&page_size=25")
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert "total" in payload
    assert "page" in payload
