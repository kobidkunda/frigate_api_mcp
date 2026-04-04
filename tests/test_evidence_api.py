from fastapi.testclient import TestClient

from factory_analytics.main import app, db

client = TestClient(app)


def test_evidence_endpoint_returns_primary_and_all_frames():
    camera = db.upsert_camera("cam_evidence", "Cam Evidence")
    job = db.schedule_job(camera["id"], payload={})
    segment = db.create_segment(
        job_id=job["id"],
        camera_id=camera["id"],
        start_ts="2026-04-05T00:00:00+00:00",
        end_ts="2026-04-05T00:00:03+00:00",
        label="working",
        confidence=0.9,
        notes="activity seen in frames 2-3",
        evidence_path="data/evidence/frames/cam_evidence/frame_0.jpg",
    )
    db.mark_job_finished(
        job["id"],
        "success",
        raw_result={
            "primary_evidence_path": "data/evidence/frames/cam_evidence/frame_0.jpg",
            "evidence_frames": [
                "data/evidence/frames/cam_evidence/frame_0.jpg",
                "data/evidence/frames/cam_evidence/frame_1.jpg",
            ],
        },
        snapshot_path="data/evidence/frames/cam_evidence/frame_0.jpg",
    )

    response = client.get(f"/api/evidence/{segment['id']}")
    assert response.status_code == 200
    assert response.json() == {
        "segment_id": segment["id"],
        "evidence_path": "data/evidence/frames/cam_evidence/frame_0.jpg",
        "evidence_frames": [
            "data/evidence/frames/cam_evidence/frame_0.jpg",
            "data/evidence/frames/cam_evidence/frame_1.jpg",
        ],
    }
