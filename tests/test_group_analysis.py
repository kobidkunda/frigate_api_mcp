from fastapi.testclient import TestClient

from factory_analytics.main import app
from factory_analytics.services import AnalyticsService


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


def test_group_run_includes_grouped_disabled_cameras(monkeypatch):
    group = client.post(
        "/api/groups", json={"group_type": "machine", "name": "disabled in group"}
    ).json()
    enabled_cam = client.post(
        "/api/cameras",
        json={
            "frigate_name": "group_enabled_cam",
            "name": "group_enabled_cam",
            "enabled": True,
        },
    ).json()
    disabled_cam = client.post(
        "/api/cameras",
        json={
            "frigate_name": "group_disabled_cam",
            "name": "group_disabled_cam",
            "enabled": False,
        },
    ).json()
    client.post(
        f"/api/groups/{group['id']}/cameras", json={"camera_id": enabled_cam["id"]}
    )
    client.post(
        f"/api/groups/{group['id']}/cameras", json={"camera_id": disabled_cam["id"]}
    )

    seen = []

    def fake_capture(self, camera_name):
        seen.append(camera_name)
        return __import__("pathlib").Path("/tmp") / f"{camera_name}.jpg"

    monkeypatch.setattr(AnalyticsService, "_capture_snapshot", fake_capture)
    monkeypatch.setattr(
        "factory_analytics.services.merge_group_snapshots",
        lambda snapshots, output: output,
    )
    monkeypatch.setattr(
        "factory_analytics.services.draw_person_boxes",
        lambda src, dest, boxes: dest,
    )
    monkeypatch.setattr(
        AnalyticsService,
        "ollama_client",
        lambda self: type(
            "Dummy",
            (),
            {
                "classify_image": lambda _self, _img: {
                    "label": "idle",
                    "confidence": 0.8,
                    "notes": "group ok",
                    "boxes": [],
                }
            },
        )(),
    )

    response = client.post(f"/api/groups/{group['id']}/run")
    assert response.status_code == 200
    payload = response.json()
    assert "group_enabled_cam" in seen
    assert "group_disabled_cam" in seen
    assert "group_disabled_cam" in payload["included_cameras"]


def test_group_run_continues_with_missing_camera_note(monkeypatch):
    group = client.post(
        "/api/groups", json={"group_type": "machine", "name": "partial group"}
    ).json()
    cam_ok = client.post(
        "/api/cameras",
        json={"frigate_name": "group_ok_cam", "name": "group_ok_cam", "enabled": False},
    ).json()
    cam_fail = client.post(
        "/api/cameras",
        json={
            "frigate_name": "group_fail_cam",
            "name": "group_fail_cam",
            "enabled": False,
        },
    ).json()
    client.post(f"/api/groups/{group['id']}/cameras", json={"camera_id": cam_ok["id"]})
    client.post(
        f"/api/groups/{group['id']}/cameras", json={"camera_id": cam_fail["id"]}
    )

    def fake_capture(self, camera_name):
        Path = __import__("pathlib").Path
        if camera_name == "group_fail_cam":
            raise RuntimeError("snapshot unavailable")
        return Path("/tmp") / f"{camera_name}.jpg"

    monkeypatch.setattr(AnalyticsService, "_capture_snapshot", fake_capture)
    monkeypatch.setattr(
        "factory_analytics.services.merge_group_snapshots",
        lambda snapshots, output: output,
    )
    monkeypatch.setattr(
        "factory_analytics.services.draw_person_boxes",
        lambda src, dest, boxes: dest,
    )
    monkeypatch.setattr(
        AnalyticsService,
        "ollama_client",
        lambda self: type(
            "Dummy",
            (),
            {
                "classify_image": lambda _self, _img: {
                    "label": "idle",
                    "confidence": 0.8,
                    "notes": "partial merge",
                    "boxes": [],
                }
            },
        )(),
    )

    response = client.post(f"/api/groups/{group['id']}/run")
    assert response.status_code == 200
    payload = response.json()
    assert payload["included_cameras"] == ["group_ok_cam"]
    assert payload["missing_cameras"] == ["group_fail_cam"]
    assert "group_fail_cam" in payload["notes"]


def test_group_run_writes_real_group_evidence_file(monkeypatch):
    group = client.post(
        "/api/groups", json={"group_type": "machine", "name": "group evidence file"}
    ).json()
    cam = client.post(
        "/api/cameras",
        json={
            "frigate_name": "group_file_cam",
            "name": "group_file_cam",
            "enabled": False,
        },
    ).json()
    client.post(f"/api/groups/{group['id']}/cameras", json={"camera_id": cam["id"]})

    def fake_capture(self, camera_name):
        from pathlib import Path
        from PIL import Image

        path = Path("data/evidence/snapshots") / f"{camera_name}_group_source.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (640, 480), color="white").save(path)
        return path

    monkeypatch.setattr(AnalyticsService, "_capture_snapshot", fake_capture)
    monkeypatch.setattr(
        AnalyticsService,
        "ollama_client",
        lambda self: type(
            "Dummy",
            (),
            {
                "classify_image": lambda _self, _img: {
                    "label": "idle",
                    "confidence": 0.8,
                    "notes": "group evidence",
                    "boxes": [],
                }
            },
        )(),
    )

    response = client.post(f"/api/groups/{group['id']}/run")
    assert response.status_code == 200
    payload = response.json()

    from pathlib import Path

    evidence = Path(payload["evidence_path"])
    assert evidence.exists()


def test_group_run_timeout_marks_job_failed(monkeypatch):
    group = client.post(
        "/api/groups", json={"group_type": "machine", "name": "group timeout cleanup"}
    ).json()
    cam = client.post(
        "/api/cameras",
        json={
            "frigate_name": "group_timeout_cam",
            "name": "group_timeout_cam",
            "enabled": False,
        },
    ).json()
    client.post(f"/api/groups/{group['id']}/cameras", json={"camera_id": cam["id"]})

    def fake_capture(self, camera_name):
        from pathlib import Path
        from PIL import Image

        path = Path("data/evidence/snapshots") / f"{camera_name}_timeout_source.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (640, 480), color="white").save(path)
        return path

    monkeypatch.setattr(AnalyticsService, "_capture_snapshot", fake_capture)

    def raise_timeout(self, image_path):
        raise RuntimeError("group analysis timeout")

    monkeypatch.setattr(
        "factory_analytics.integrations.ollama.OpenAIClient.classify_group_image",
        raise_timeout,
    )

    response = client.post(f"/api/groups/{group['id']}/run")
    assert response.status_code == 400

    jobs = client.get("/api/jobs").json()
    timeout_jobs = [j for j in jobs if j.get("job_type") == "group_analysis"]
    assert timeout_jobs
    assert timeout_jobs[0]["status"] == "failed"
    assert "timeout" in (timeout_jobs[0].get("error") or "")
