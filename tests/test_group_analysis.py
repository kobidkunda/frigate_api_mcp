from fastapi.testclient import TestClient

from factory_analytics.main import app


client = TestClient(app)


def test_group_run_endpoint_exists_and_returns_structured_payload():
    group = client.post(
        "/api/groups", json={"group_type": "machine", "name": "machine run test"}
    ).json()
    cameras = client.get("/api/cameras").json()
    if not cameras:
        cam = client.post(
            "/api/cameras",
            json={"frigate_name": "camera_group_run", "name": "camera_group_run"},
        ).json()
    else:
        cam = cameras[0]
    client.post(f"/api/groups/{group['id']}/cameras", json={"camera_id": cam["id"]})
    response = client.post(f"/api/groups/{group['id']}/run")
    assert response.status_code in (200, 400, 500)
    payload = response.json()
    if response.status_code == 200:
        assert "ok" in payload
        assert "label" in payload
    else:
        assert "detail" in payload or "message" in payload or "error" in payload
