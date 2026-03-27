from fastapi.testclient import TestClient

from factory_analytics.main import app


client = TestClient(app)


def test_create_group_api():
    response = client.post(
        "/api/groups", json={"group_type": "machine", "name": "machine 1"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["group_type"] == "machine"
    assert payload["name"] == "machine 1"


def test_add_camera_to_group_api():
    group = client.post(
        "/api/groups", json={"group_type": "room", "name": "room 1 factory"}
    ).json()
    cameras = client.get("/api/cameras").json()
    if not cameras:
        cam = client.post(
            "/api/cameras",
            json={"frigate_name": "camera_for_group", "name": "camera_for_group"},
        ).json()
    else:
        cam = cameras[0]
    response = client.post(
        f"/api/groups/{group['id']}/cameras", json={"camera_id": cam["id"]}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["group_id"] == group["id"]
    assert payload["camera_id"] == cam["id"]
