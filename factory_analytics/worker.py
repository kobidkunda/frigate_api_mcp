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
        self.thread = threading.Thread(target=self.run, name='factory-worker', daemon=True)
        self.thread.start()
        logger.info('Worker loop started')

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
        logger.info('Worker loop stopped')

    def run(self):
        while not self.stop_event.is_set():
            try:
                self._schedule_due_cameras()
                processed = self.service.process_one_pending_job()
                if processed:
                    logger.info('Processed job %s', processed.get('job', {}).get('id'))
            except Exception:
                logger.exception('Worker loop error')
            self.stop_event.wait(5)

    def _schedule_due_cameras(self):
        settings = self.db.get_settings()
        if not settings.get('scheduler_enabled', True):
            return
        now = datetime.now(timezone.utc)
        for camera in self.db.list_cameras():
            if not camera.get('enabled'):
                continue
            interval = int(camera.get('interval_seconds') or settings.get('analysis_interval_seconds') or 300)
            last_run = camera.get('last_run_at')
            due = True
            if last_run:
                try:
                    last_dt = datetime.fromisoformat(last_run)
                    due = (now - last_dt).total_seconds() >= interval
                except Exception:
                    due = True
            if due:
                self.db.schedule_job(camera['id'], payload={'source': 'scheduler'})
