from fastapi.testclient import TestClient

from factory_analytics.main import app, db, service

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


def test_history_segment_detail_includes_model_and_evidence_fields():
    camera = db.upsert_camera("cam_history_detail", "Camera History Detail")
    job = db.schedule_job(camera["id"], payload={"model": "llava:13b"})
    segment = db.create_segment(
        job_id=job["id"],
        camera_id=camera["id"],
        start_ts="2026-04-06T10:00:00+00:00",
        end_ts="2026-04-06T10:01:00+00:00",
        label="working",
        confidence=0.92,
        notes="Operator present",
        evidence_path="data/evidence/history/primary.jpg",
    )
    db.mark_job_finished(
        job["id"],
        "success",
        raw_result={
            "model": "llava:13b",
            "group_name": "Line 1",
            "group_type": "line",
            "group_id": 4,
            "primary_evidence_path": "data/evidence/history/primary.jpg",
            "evidence_frames": [
                "data/evidence/history/frame-1.jpg",
                "data/evidence/history/frame-2.jpg",
            ],
            "raw": {"detail": "kept"},
        },
        snapshot_path="data/evidence/history/primary.jpg",
    )
    service.review_segment(segment["id"], "working", "looks correct", "qa-user")

    payload = service.segment(segment["id"])
    response = client.get(f"/api/history/segments/{segment['id']}")

    assert payload["model_used"] == "llava:13b"
    assert payload["evidence_frames"] == [
        "data/evidence/history/frame-1.jpg",
        "data/evidence/history/frame-2.jpg",
    ]
    assert payload["primary_evidence_path"] == "data/evidence/history/primary.jpg"
    assert payload["group_name"] == "Line 1"
    assert payload["review_by"] == "qa-user"
    assert payload["raw_result"]["raw"]["detail"] == "kept"

    assert response.status_code == 200
    response_payload = response.json()
    assert response_payload["model_used"] == "llava:13b"
    assert response_payload["evidence_frames"] == [
        "data/evidence/history/frame-1.jpg",
        "data/evidence/history/frame-2.jpg",
    ]
    assert response_payload["primary_evidence_path"] == "data/evidence/history/primary.jpg"
    assert response_payload["group_name"] == "Line 1"
    assert response_payload["review_by"] == "qa-user"
