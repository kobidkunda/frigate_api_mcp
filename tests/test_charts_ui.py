from fastapi.testclient import TestClient

from factory_analytics.main import app


client = TestClient(app)


def test_charts_page_renders():
    response = client.get("/charts")
    assert response.status_code == 200
    html = response.text
    assert "Charts" in html
    assert "Heatmap" in html
