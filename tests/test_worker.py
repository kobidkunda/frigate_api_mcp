from __future__ import annotations

from pathlib import Path

from factory_analytics.database import Database
from factory_analytics.worker import WorkerLoop


def test_schedule_due_cameras_skips_when_pending_or_running_job_exists(tmp_path: Path):
    db = Database(path=tmp_path / "worker.db")
    camera = db.upsert_camera("camera_88_10")
    db.update_camera(camera["id"], {"enabled": True})
    db.schedule_job(camera["id"], payload={"source": "scheduler"})

    worker = WorkerLoop(db)
    worker._schedule_due_cameras()

    jobs = db.list_jobs(limit=20, camera_id=camera["id"])
    assert len(jobs) == 1


def test_schedule_due_groups(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    worker = WorkerLoop(db)

    # Create group with short interval
    group = db.create_group("machine", "test_group", interval_seconds=1)
    camera = db.upsert_camera("test_cam", "Test Camera")
    db.update_camera(camera["id"], {"enabled": True})
    db.add_camera_to_group(camera["id"], group["id"])

    # Update last_run_at to be old
    db.update_group(group["id"], last_run_at="2020-01-01T00:00:00+00:00")

    # Schedule due groups
    worker._schedule_due_groups()

    # Should have scheduled a job
    assert db.has_active_group_jobs(group["id"])


def test_worker_continues_after_exception():
    db = Database()
    worker = WorkerLoop(db)

    # Mock a method to raise exception
    original_method = worker._schedule_due_groups
    call_count = 0

    def mock_method():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Test error")
        original_method()

    worker._schedule_due_groups = mock_method

    # Mock wait to be very short for test
    worker.stop_event.wait = lambda x: __import__("time").sleep(0.01)

    # Run worker loop briefly
    import threading
    import time

    worker.start()
    time.sleep(0.1)
    worker.stop()

    # Should have called method twice (recovered from error)
    assert call_count >= 2
