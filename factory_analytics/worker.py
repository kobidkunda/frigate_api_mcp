from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from factory_analytics.config import DATA_ROOT
from factory_analytics.database import Database
from factory_analytics.logging_setup import setup_logging
from factory_analytics.services import AnalyticsService

logger = setup_logging()


class WorkerLoop:
    def __init__(self, db: Database):
        self.db = db
        self.service = AnalyticsService(db)
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self._last_cleanup_day: str | None = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(
            target=self.run, name="factory-worker", daemon=True
        )
        self.thread.start()
        logger.info("Worker loop started")

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Worker loop stopped")

    def run(self):
        error_count = 0
        max_errors = 10
        while not self.stop_event.is_set():
            try:
                settings = self.db.get_settings()

                timeout = int(settings.get("job_timeout_seconds", 600))
                expired = self.db.expire_timed_out_jobs(timeout)
                if expired:
                    logger.info(
                        "Expired %d timed-out job(s) (timeout=%ds)", expired, timeout
                    )

                self._cleanup_old_evidence(settings)

                self._schedule_due_groups()
                self._schedule_due_cameras()
                processed = self.service.process_one_pending_job()
                if processed:
                    logger.info("Processed job %s", processed.get("job", {}).get("id"))

                error_count = 0

            except Exception as e:
                error_count += 1
                logger.error(
                    f"Worker loop error ({error_count}/{max_errors}): {e}",
                    exc_info=True,
                )

                if error_count >= max_errors:
                    logger.warning(
                        f"Worker loop has {error_count} consecutive errors, but continuing..."
                    )
                    error_count = max_errors - 1

            self.stop_event.wait(5)

    def _cleanup_old_evidence(self, settings: dict):
        """Delete evidence files older than retention_days.

        Runs once per day at midnight UTC. Deletes files but keeps DB records.
        """
        retention_days = int(settings.get("evidence_retention_days", 30))
        if retention_days <= 0:
            return

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._last_cleanup_day == today:
            return

        self._last_cleanup_day = today

        paths = self.db.get_expired_evidence_paths(retention_days)
        if not paths:
            logger.debug("No expired evidence to clean up")
            return

        deleted_count = 0
        for rel_path in paths:
            try:
                full_path = DATA_ROOT.parent / rel_path
                if full_path.exists():
                    full_path.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.warning("Failed to delete %s: %s", rel_path, e)

        updated = self.db.clear_segment_evidence_refs(retention_days)

        logger.info(
            "Cleaned up %d evidence files older than %d days, cleared %d DB refs",
            deleted_count,
            retention_days,
            updated,
        )

        self._cleanup_empty_dirs()

    def _cleanup_empty_dirs(self):
        """Remove empty evidence subdirectories."""
        evidence_dir = DATA_ROOT / "evidence"
        if not evidence_dir.exists():
            return

        for subdir in evidence_dir.rglob("*"):
            if subdir.is_dir() and not any(subdir.iterdir()):
                try:
                    subdir.rmdir()
                    logger.debug("Removed empty directory: %s", subdir)
                except Exception:
                    pass

    def _schedule_due_groups(self):
        settings = self.db.get_settings()
        if not settings.get("group_scheduler_enabled", True):
            return

        now = datetime.now(timezone.utc)
        for group in self.db.list_groups():
            # Skip if group already has active jobs
            if self.db.has_active_group_jobs(group["id"]):
                continue

            interval = group.get("interval_seconds") or 300
            last_run = group.get("last_run_at")
            due = True

            if last_run:
                try:
                    last_dt = datetime.fromisoformat(last_run)
                    due = (now - last_dt).total_seconds() >= interval
                except Exception:
                    due = True

            if due:
                # Schedule ONE group analysis job for the entire group
                cameras = self.db.list_group_cameras(group["id"])
                enabled_cameras = [c for c in cameras if c.get("enabled")]
                if enabled_cameras:
                    # Use first enabled camera as anchor
                    anchor_camera = enabled_cameras[0]
                    self.db.schedule_group_job(
                        camera_id=anchor_camera["id"],
                        group_id=group["id"],
                        group_type=group["group_type"],
                        group_name=group["name"],
                    )

                    # Update group last_run_at immediately (even though jobs not complete)
                    # This prevents re-scheduling while jobs are running
                    self.db.update_group(group["id"], last_run_at=now.isoformat())

    def _schedule_due_cameras(self):
        settings = self.db.get_settings()
        if not settings.get("scheduler_enabled", True):
            return
        now = datetime.now(timezone.utc)
        for camera in self.db.list_cameras():
            if not camera.get("enabled"):
                continue
            if self.db.has_active_job(camera["id"]):
                continue
            interval = int(
                camera.get("interval_seconds")
                or settings.get("analysis_interval_seconds")
                or 300
            )
            last_run = camera.get("last_run_at")
            due = True
            if last_run:
                try:
                    last_dt = datetime.fromisoformat(last_run)
                    due = (now - last_dt).total_seconds() >= interval
                except Exception:
                    due = True
            if due:
                self.db.schedule_job(camera["id"], payload={"source": "scheduler"})
