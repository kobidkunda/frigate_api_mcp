from pathlib import Path

from factory_analytics.database import Database


def test_camera_can_belong_to_multiple_groups(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    cam = db.upsert_camera("camera_1")
    machine = db.create_group("machine", "machine 1")
    room = db.create_group("room", "room 1 factory")

    db.add_camera_to_group(cam["id"], machine["id"])
    db.add_camera_to_group(cam["id"], room["id"])

    groups = db.list_camera_groups(cam["id"])
    assert len(groups) == 2
    assert {g["group_type"] for g in groups} == {"machine", "room"}


def test_group_job_and_segment_are_persisted_for_history(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    cam = db.upsert_camera("camera_group_anchor")
    group = db.create_group("machine", "machine history")

    job = db.schedule_group_job(
        camera_id=cam["id"],
        group_id=group["id"],
        group_type=group["group_type"],
        group_name=group["name"],
    )
    db.mark_job_running(job["id"])
    db.mark_job_finished(
        job["id"],
        "success",
        raw_result={
            "label": "idle",
            "confidence": 0.9,
            "notes": "Merged group result. Missing cameras: camera_missing.",
            "included_cameras": ["camera_group_anchor"],
            "missing_cameras": ["camera_missing"],
        },
        snapshot_path="data/evidence/groups/history.jpg",
    )
    seg = db.create_segment(
        job_id=job["id"],
        camera_id=cam["id"],
        start_ts="2026-03-28T00:00:00+00:00",
        end_ts="2026-03-28T00:05:00+00:00",
        label="idle",
        confidence=0.9,
        notes="Merged group result. Missing cameras: camera_missing.",
        evidence_path="data/evidence/groups/history.jpg",
    )

    persisted = db.get_segment(seg["id"])
    assert persisted is not None
    assert persisted["notes"] == "Merged group result. Missing cameras: camera_missing."

    jobs = db.list_jobs(limit=10)
    assert jobs[0]["job_type"] == "group_analysis"
    assert jobs[0]["raw_result"]

def test_schedule_group_job_with_metadata(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    group = db.create_group("machine", "test_group")
    camera = db.upsert_camera("test_cam", "Test Camera")
    
    job = db.schedule_group_job(
        camera_id=camera["id"],
        group_id=group["id"],
        group_type=group["group_type"],
        group_name=group["name"]
    )
    
    import json
    payload = json.loads(job["payload_json"])
    assert payload["source"] == "group_scheduler"
    assert payload["group_id"] == group["id"]
    assert payload["group_type"] == "machine"

def test_has_active_group_jobs(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    group = db.create_group("machine", "test_group")
    camera = db.upsert_camera("test_cam", "Test Camera")
    
    # No active jobs initially
    assert not db.has_active_group_jobs(group["id"])
    
    # Schedule a group job
    db.schedule_group_job(
        camera_id=camera["id"],
        group_id=group["id"],
        group_type=group["group_type"],
        group_name=group["name"]
    )
    
    # Should have active jobs now
    assert db.has_active_group_jobs(group["id"])

def test_create_group_with_interval(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    group = db.create_group("machine", "test_group", interval_seconds=600)
    assert group["interval_seconds"] == 600

def test_update_group_interval(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    group = db.create_group("machine", "test_group")
    updated = db.update_group(group["id"], interval_seconds=900)
    assert updated["interval_seconds"] == 900
