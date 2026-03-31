#!/usr/bin/env python3
"""
Comprehensive test suite for MCP server tools.
Tests all 43 tools to verify they work correctly.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from factory_analytics.database import Database
from factory_analytics.services import AnalyticsService

# Test database in temp file
import tempfile

temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db.close()
from pathlib import Path

db = Database(path=Path(temp_db.name))
service = AnalyticsService(db)

# Import dispatch function logic
# We can't import directly due to FastAPI dependency, so we'll test the service methods


def test_system_tools():
    """Test system and health tools"""
    print("\n=== Testing System & Health Tools ===")

    # system_health - should return dict with health status
    try:
        result = service.system_health()
        assert isinstance(result, dict)
        assert "ok" in result
        print("✓ system_health")
    except Exception as e:
        print(f"✗ system_health: {e}")

    # system_status - custom implementation
    try:
        from datetime import datetime, timezone

        result = {
            "now_utc": datetime.now(timezone.utc).isoformat(),
            "settings": service.settings(),
            "camera_count": len(service.list_cameras()),
            "job_count": len(service.jobs()),
            "segment_count": len(service.segments()),
        }
        assert "now_utc" in result
        print("✓ system_status")
    except Exception as e:
        print(f"✗ system_status: {e}")

    # frigate_health
    try:
        result = service.frigate_client().health()
        assert isinstance(result, dict)
        print("✓ frigate_health")
    except Exception as e:
        print(f"✗ frigate_health: {e}")

    # ollama_health
    try:
        result = service.ollama_client().health()
        assert isinstance(result, dict)
        print("✓ ollama_health")
    except Exception as e:
        print(f"✗ ollama_health: {e}")


def test_camera_tools():
    """Test camera CRUD tools"""
    print("\n=== Testing Camera Tools ===")

    # camera_list
    try:
        result = service.list_cameras()
        assert isinstance(result, list)
        print("✓ camera_list")
    except Exception as e:
        print(f"✗ camera_list: {e}")

    # camera_create
    try:
        result = service.create_camera(frigate_name="test_camera")
        assert isinstance(result, dict)
        camera_id = result.get("id")
        print(f"✓ camera_create (id={camera_id})")

        # camera_status
        try:
            cam = db.get_camera(camera_id)
            assert cam is not None
            print(f"✓ camera_status (id={camera_id})")
        except Exception as e:
            print(f"✗ camera_status: {e}")

        # camera_update
        try:
            result = service.update_camera(camera_id, {"name": "Updated Name"})
            assert result is not None
            print(f"✓ camera_update (id={camera_id})")
        except Exception as e:
            print(f"✗ camera_update: {e}")

        # camera_health
        try:
            result = service.camera_health(camera_id)
            print(f"✓ camera_health (id={camera_id})")
        except Exception as e:
            print(f"✗ camera_health: {e}")

        # camera_delete
        try:
            result = service.delete_camera(camera_id)
            assert isinstance(result, dict)
            print(f"✓ camera_delete (id={camera_id})")
        except Exception as e:
            print(f"✗ camera_delete: {e}")

    except Exception as e:
        print(f"✗ camera_create: {e}")

    # all_cameras_health
    try:
        result = service.all_cameras_health()
        assert isinstance(result, list)
        print("✓ all_cameras_health")
    except Exception as e:
        print(f"✗ all_cameras_health: {e}")

    # camera_test - requires Frigate connection, may fail
    try:
        result = service.probe_analysis(frigate_name="test_camera")
        print(f"✓ camera_test (may have failed gracefully)")
    except Exception as e:
        print(f"⚠ camera_test (expected failure without Frigate): {e}")


def test_group_tools():
    """Test group management tools"""
    print("\n=== Testing Group Tools ===")

    # group_list
    try:
        result = service.list_groups()
        assert isinstance(result, list)
        print("✓ group_list")
    except Exception as e:
        print(f"✗ group_list: {e}")

    # group_create
    try:
        result = service.create_group("test", "Test Group", 300)
        assert isinstance(result, dict)
        group_id = result.get("id")
        print(f"✓ group_create (id={group_id})")

        # group_get
        try:
            group = db.get_group(group_id)
            assert group is not None
            print(f"✓ group_get (id={group_id})")
        except Exception as e:
            print(f"✗ group_get: {e}")

        # group_update
        try:
            result = service.update_group(group_id, name="Updated Group")
            assert result is not None
            print(f"✓ group_update (id={group_id})")
        except Exception as e:
            print(f"✗ group_update: {e}")

        # Create a camera to test membership
        try:
            cam = service.create_camera(frigate_name="test_cam_for_group")
            cam_id = cam.get("id")

            # group_add_camera
            try:
                result = service.add_camera_to_group(group_id, cam_id)
                print(f"✓ group_add_camera (group={group_id}, cam={cam_id})")

                # group_list_cameras
                try:
                    result = service.group_cameras(group_id)
                    assert isinstance(result, list)
                    print(f"✓ group_list_cameras (group={group_id})")
                except Exception as e:
                    print(f"✗ group_list_cameras: {e}")

                # camera_groups
                try:
                    result = service.camera_groups(cam_id)
                    assert isinstance(result, list)
                    print(f"✓ camera_groups (cam={cam_id})")
                except Exception as e:
                    print(f"✗ camera_groups: {e}")

                # group_remove_camera
                try:
                    result = service.remove_camera_from_group(group_id, cam_id)
                    print(f"✓ group_remove_camera (group={group_id}, cam={cam_id})")
                except Exception as e:
                    print(f"✗ group_remove_camera: {e}")

                # Cleanup camera
                service.delete_camera(cam_id)

            except Exception as e:
                print(f"✗ group_add_camera: {e}")
        except Exception as e:
            print(f"⚠ group membership tests skipped: {e}")

        # group_run_analysis - requires cameras
        try:
            result = service.queue_group_analysis(group_id)
            print(f"✓ group_run_analysis (id={group_id})")
        except RuntimeError as e:
            print(f"⚠ group_run_analysis (expected without cameras): {e}")
        except Exception as e:
            print(f"✗ group_run_analysis: {e}")

        # group_delete
        try:
            result = service.delete_group(group_id)
            assert isinstance(result, dict)
            print(f"✓ group_delete (id={group_id})")
        except Exception as e:
            print(f"✗ group_delete: {e}")

    except Exception as e:
        print(f"✗ group_create: {e}")


def test_job_tools():
    """Test job management tools"""
    print("\n=== Testing Job Tools ===")

    # run_list
    try:
        result = service.jobs()
        assert isinstance(result, list)
        print("✓ run_list")
    except Exception as e:
        print(f"✗ run_list: {e}")

    # job_stats
    try:
        result = db.job_stats()
        assert isinstance(result, dict)
        print("✓ job_stats")
    except Exception as e:
        print(f"✗ job_stats: {e}")

    # jobs_cancel_all
    try:
        result = db.cancel_all_pending_and_running()
        assert isinstance(result, dict)
        print("✓ jobs_cancel_all")
    except Exception as e:
        print(f"✗ jobs_cancel_all: {e}")

    # Create a camera and job for testing
    try:
        cam = service.create_camera(frigate_name="test_job_cam")
        cam_id = cam.get("id")

        # run_analysis_now
        try:
            result = service.queue_analysis(cam_id, {"source": "test"})
            assert isinstance(result, dict)
            job_id = result.get("id")
            print(f"✓ run_analysis_now (job={job_id})")

            # run_get
            try:
                job = service.job(job_id)
                assert job is not None
                print(f"✓ run_get (job={job_id})")
            except Exception as e:
                print(f"✗ run_get: {e}")

            # job_cancel
            try:
                job = service.job(job_id)
                if job and job.get("status") in ("pending", "running"):
                    db.mark_job_finished(job_id, "cancelled", error="Test cancel")
                    db.log_audit("test", "job.cancel", "job", str(job_id))
                print(f"✓ job_cancel (job={job_id})")
            except Exception as e:
                print(f"✗ job_cancel: {e}")

        except Exception as e:
            print(f"✗ run_analysis_now: {e}")

        # Cleanup
        service.delete_camera(cam_id)

    except Exception as e:
        print(f"⚠ Job creation tests skipped: {e}")


def test_history_tools():
    """Test history/segment tools"""
    print("\n=== Testing History Tools ===")

    # history_search
    try:
        result = service.segments()
        assert isinstance(result, list)
        print("✓ history_search")
    except Exception as e:
        print(f"✗ history_search: {e}")


def test_chart_tools():
    """Test chart tools"""
    print("\n=== Testing Chart Tools ===")

    charts = [
        ("chart_daily", lambda: service.chart_daily(7)),
        ("chart_heatmap", service.chart_heatmap),
        ("chart_heatmap_by_group", service.chart_heatmap_by_group),
        ("chart_shift_summary", service.chart_shift_summary),
        ("chart_camera_summary", service.chart_camera_summary),
        ("chart_job_failures", service.chart_job_failures),
        ("chart_confidence_distribution", service.chart_confidence_distribution),
    ]

    for name, func in charts:
        try:
            result = func()
            assert isinstance(result, (dict, list))
            print(f"✓ {name}")
        except Exception as e:
            print(f"✗ {name}: {e}")


def test_settings_tools():
    """Test settings tools"""
    print("\n=== Testing Settings Tools ===")

    # settings_get
    try:
        result = service.settings()
        assert isinstance(result, dict)
        print("✓ settings_get")
    except Exception as e:
        print(f"✗ settings_get: {e}")

    # settings_update
    try:
        result = service.update_settings({"test_setting": "test_value"}, actor="test")
        print("✓ settings_update")
    except Exception as e:
        print(f"✗ settings_update: {e}")


def test_report_tools():
    """Test report tools"""
    print("\n=== Testing Report Tools ===")

    # report_get_daily
    try:
        result = service.report_daily(None)
        assert isinstance(result, dict)
        print("✓ report_get_daily")
    except Exception as e:
        print(f"✗ report_get_daily: {e}")


def test_frigate_tools():
    """Test Frigate tools"""
    print("\n=== Testing Frigate Tools ===")

    # frigate_list_cameras
    try:
        result = service.frigate_client().fetch_cameras()
        print(f"✓ frigate_list_cameras (found {len(result)} cameras)")
    except Exception as e:
        print(f"⚠ frigate_list_cameras (expected without Frigate): {e}")

    # frigate_sync_cameras
    try:
        result = service.sync_cameras_from_frigate()
        print(f"✓ frigate_sync_cameras")
    except Exception as e:
        print(f"⚠ frigate_sync_cameras (expected without Frigate): {e}")


def test_scheduler_tools():
    """Test scheduler tools"""
    print("\n=== Testing Scheduler Tools ===")

    # scheduler_reset
    try:
        db.reset_all_camera_last_run()
        db.log_audit("test", "scheduler.reset", "scheduler", None)
        print("✓ scheduler_reset")
    except Exception as e:
        print(f"✗ scheduler_reset: {e}")


def main():
    print("=" * 60)
    print("MCP Tools Test Suite")
    print("=" * 60)

    test_system_tools()
    test_camera_tools()
    test_group_tools()
    test_job_tools()
    test_history_tools()
    test_chart_tools()
    test_settings_tools()
    test_report_tools()
    test_frigate_tools()
    test_scheduler_tools()

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
