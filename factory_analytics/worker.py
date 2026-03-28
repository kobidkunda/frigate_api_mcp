from __future__ import annotations

import threading
from datetime import datetime, timezone

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
                self._schedule_due_groups()
                self._schedule_due_cameras()
                processed = self.service.process_one_pending_job()
                if processed:
                    logger.info("Processed job %s", processed.get("job", {}).get("id"))

                # Reset error count on successful iteration
                error_count = 0

            except Exception as e:
                error_count += 1
                logger.error(
                    f"Worker loop error ({error_count}/{max_errors}): {e}",
                    exc_info=True,
                )

                # If too many consecutive errors, log warning but continue
                if error_count >= max_errors:
                    logger.warning(
                        f"Worker loop has {error_count} consecutive errors, but continuing..."
                    )
                    error_count = max_errors - 1  # Prevent overflow

                # CRITICAL: Continue loop despite errors

            self.stop_event.wait(5)

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
                # Schedule all enabled cameras in this group
                cameras = self.db.list_group_cameras(group["id"])
                for camera in cameras:
                    if camera.get("enabled"):
                        self.db.schedule_group_job(
                            camera_id=camera["id"],
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
