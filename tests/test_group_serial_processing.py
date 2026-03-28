import time
import json
from datetime import datetime, timezone
from pathlib import Path
from factory_analytics.database import Database
from factory_analytics.worker import WorkerLoop

def test_serial_group_processing(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    worker = WorkerLoop(db)
    
    # Create two groups with different intervals
    group1 = db.create_group("machine", "Group 1", interval_seconds=2)
    group2 = db.create_group("room", "Group 2", interval_seconds=2)
    
    # Create cameras and add to groups
    cam1 = db.upsert_camera("cam1", "Camera 1")
    cam2 = db.upsert_camera("cam2", "Camera 2")
    cam3 = db.upsert_camera("cam3", "Camera 3")
    
    db.add_camera_to_group(cam1["id"], group1["id"])
    db.add_camera_to_group(cam2["id"], group1["id"])
    db.add_camera_to_group(cam3["id"], group2["id"])
    
    # Enable all cameras
    db.update_camera(cam1["id"], {"enabled": 1})
    db.update_camera(cam2["id"], {"enabled": 1})
    db.update_camera(cam3["id"], {"enabled": 1})
    
    # Set old last_run_at to trigger scheduling
    old_time = "2020-01-01T00:00:00+00:00"
    db.update_group(group1["id"], last_run_at=old_time)
    db.update_group(group2["id"], last_run_at=old_time)
    
    # Start worker
    worker.stop_event.wait = lambda x: time.sleep(0.01)
    worker.start()
    
    try:
        # Wait for jobs to be scheduled
        time.sleep(0.5)
        
        # Both groups should have jobs scheduled
        assert db.has_active_group_jobs(group1["id"])
        assert db.has_active_group_jobs(group2["id"])
        
        # Check jobs have correct metadata
        jobs = db.list_jobs(limit=10)
        group1_jobs = [j for j in jobs if json.loads(j.get("payload_json", "{}")).get("group_id") == group1["id"]]
        group2_jobs = [j for j in jobs if json.loads(j.get("payload_json", "{}")).get("group_id") == group2["id"]]
        
        assert len(group1_jobs) == 2  # cam1 and cam2
        assert len(group2_jobs) == 1  # cam3
        
        # Verify group metadata in payload
        for job in group1_jobs:
            payload = json.loads(job.get("payload_json", "{}"))
            assert payload.get("source") == "group_scheduler"
            assert payload.get("group_id") == group1["id"]
            assert payload.get("group_type") == "machine"
            assert payload.get("group_name") == "Group 1"
        
    finally:
        worker.stop()
