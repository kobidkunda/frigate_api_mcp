from fastapi.testclient import TestClient

from factory_analytics.main import app


client = TestClient(app)


def test_control_center_page_renders():
    response = client.get("/control-center")
    assert response.status_code == 200
    assert "Control Center" in response.text


def test_api_explorer_page_renders():
    response = client.get("/api-explorer")
    assert response.status_code == 200
    assert "API Explorer" in response.text


def test_control_center_config_endpoint_returns_sections():
    response = client.get("/api/control-center/config")
    assert response.status_code == 200
    payload = response.json()
    assert "config_files" in payload
    assert "skills" in payload
    assert "platform_instructions" in payload


def test_api_explorer_catalog_endpoint_returns_routes():
    response = client.get("/api/api-explorer/catalog")
    assert response.status_code == 200
    payload = response.json()
    assert "groups" in payload
    assert any(group.get("routes") for group in payload["groups"])
