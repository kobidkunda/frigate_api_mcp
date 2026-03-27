from fastapi.testclient import TestClient

from factory_analytics.main import app


client = TestClient(app)


def test_heatmap_api_returns_matrix():
    response = client.get("/api/charts/heatmap")
    assert response.status_code == 200
    payload = response.json()
    assert "rows" in payload


def test_shift_summary_api_returns_series():
    response = client.get("/api/charts/shift-summary")
    assert response.status_code == 200
    payload = response.json()
    assert "series" in payload
