from fastapi.testclient import TestClient

from factory_analytics.main import app
from factory_analytics.database import Database


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


def test_processed_segments_api_exposes_persisted_group_result_metadata(tmp_path):
    db = Database(tmp_path / "processed.db")
    cam = db.upsert_camera("camera_group_display")
    group = db.create_group("machine", "display machine")
    job = db.schedule_group_job(
        group_id=group["id"],
        anchor_camera_id=cam["id"],
        payload={"group_name": group["name"], "group_type": group["group_type"]},
    )
    db.mark_job_running(job["id"])
    db.mark_job_finished(
        job["id"],
        "success",
        raw_result={
            "group_id": group["id"],
            "group_name": group["name"],
            "group_type": group["group_type"],
            "included_cameras": ["camera_group_display"],
            "missing_cameras": [],
            "notes": "Merged group result",
        },
        snapshot_path="data/evidence/groups/display.jpg",
    )
    db.create_segment(
        job_id=job["id"],
        camera_id=cam["id"],
        start_ts="2026-03-28T00:00:00+00:00",
        end_ts="2026-03-28T00:05:00+00:00",
        label="idle",
        confidence=0.8,
        notes="Merged group result",
        evidence_path="data/evidence/groups/display.jpg",
    )

    payload = db.list_segments_paginated(page=1, page_size=25)
    assert payload["items"]
    item = payload["items"][0]
    assert item["job_type"] == "group_analysis"
    assert item["group_name"] == "display machine"
    assert item["group_type"] == "machine"
