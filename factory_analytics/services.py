from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from factory_analytics.config import DATA_ROOT
from factory_analytics.database import Database
from factory_analytics.integrations.frigate import FrigateClient
from factory_analytics.integrations.ollama import OllamaClient
from factory_analytics.logging_setup import setup_logging

logger = setup_logging()


class AnalyticsService:
    def __init__(self, db: Database):
        self.db = db

    def settings(self) -> dict[str, Any]:
        return self.db.get_settings()

    def update_settings(
        self, payload: dict[str, Any], actor: str = "api"
    ) -> dict[str, Any]:
        result = self.db.update_settings(payload)
        self.db.log_audit(actor, "settings.update", "settings", payload=payload)
        return result

    def frigate_client(self) -> FrigateClient:
        return FrigateClient(self.settings())

    def ollama_client(self) -> OllamaClient:
        return OllamaClient(self.settings())

    def sync_cameras_from_frigate(self) -> dict[str, Any]:
        cams = self.frigate_client().fetch_cameras()
        synced = []
        for name in cams:
            synced.append(self.db.upsert_camera(name))
        self.db.log_audit(
            "api", "frigate.sync_cameras", "camera", payload={"count": len(synced)}
        )
        return {"count": len(synced), "cameras": synced}

    def system_health(self) -> dict[str, Any]:
        frigate = self.frigate_client().health()
        ollama = self.ollama_client().health()
        db_ok = True
        try:
            self.db.get_settings()
        except Exception as exc:
            db_ok = False
            logger.exception("DB health failed")
            db_msg = str(exc)
        else:
            db_msg = "ok"
        return {
            "ok": db_ok and bool(frigate.get("ok")) and bool(ollama.get("ok")),
            "app": {"ok": True},
            "database": {"ok": db_ok, "message": db_msg},
            "frigate": frigate,
            "ollama": ollama,
        }

    def list_cameras(self):
        return self.db.list_cameras()

    def update_camera(self, camera_id: int, payload: dict[str, Any]):
        camera = self.db.update_camera(camera_id, payload)
        self.db.log_audit("api", "camera.update", "camera", str(camera_id), payload)
        return camera

    def queue_analysis(self, camera_id: int, payload: dict[str, Any] | None = None):
        payload = payload or {}
        start_ts = payload.get("start_ts")
        end_ts = payload.get("end_ts")
        if start_ts and end_ts:
            start_dt = datetime.fromisoformat(start_ts)
            end_dt = datetime.fromisoformat(end_ts)
            interval_seconds = 3600  # 1-hour chunks
            total_seconds = (end_dt - start_dt).total_seconds()
            if total_seconds > interval_seconds:
                jobs = []
                cursor = start_dt
                while cursor < end_dt:
                    chunk_end = min(
                        cursor + timedelta(seconds=interval_seconds), end_dt
                    )
                    chunk_payload = {
                        **payload,
                        "start_ts": cursor.isoformat(),
                        "end_ts": chunk_end.isoformat(),
                    }
                    job = self.db.schedule_job(camera_id, payload=chunk_payload)
                    jobs.append(job)
                    cursor = chunk_end
                self.db.log_audit(
                    "api",
                    "job.schedule_backfill",
                    "camera",
                    str(camera_id),
                    {
                        "segment_count": len(jobs),
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                    },
                )
                return {"segment_count": len(jobs), "jobs": jobs}
        job = self.db.schedule_job(camera_id, payload=payload)
        self.db.log_audit("api", "job.schedule", "job", str(job["id"]), payload)
        return job

    def process_one_pending_job(self) -> dict[str, Any] | None:
        job = self.db.next_pending_job()
        if not job:
            return None
        self.db.mark_job_running(job["id"])
        settings = self.settings()
        camera = self.db.get_camera(job["camera_id"])
        try:
            snapshot_path = self._capture_snapshot(camera["frigate_name"])
            result = self.ollama_client().classify_image(snapshot_path)
            start_ts, end_ts = self._resolve_job_window(job, camera, settings)
            segment = self.db.create_segment(
                job_id=job["id"],
                camera_id=camera["id"],
                start_ts=start_ts,
                end_ts=end_ts,
                label=result.get("label", "uncertain"),
                confidence=float(result.get("confidence", 0.0)),
                notes=result.get("notes", ""),
                evidence_path=str(snapshot_path.relative_to(DATA_ROOT.parent)),
            )
            day = start_ts[:10]
            seconds = max(
                1,
                int(
                    (
                        datetime.fromisoformat(end_ts)
                        - datetime.fromisoformat(start_ts)
                    ).total_seconds()
                ),
            )
            self.db.update_daily_rollup(day, camera["id"], segment["label"], seconds)
            self.db.update_camera(
                camera["id"],
                {
                    "last_run_at": datetime.now(timezone.utc).isoformat(),
                    "last_status": "ok",
                },
            )
            self.db.mark_job_finished(
                job["id"],
                "success",
                raw_result=result,
                snapshot_path=str(snapshot_path.relative_to(DATA_ROOT.parent)),
            )
            return {"job": self.db.get_job(job["id"]), "segment": segment}
        except Exception as exc:
            logger.exception("Job processing failed")
            self.db.update_camera(
                camera["id"],
                {
                    "last_run_at": datetime.now(timezone.utc).isoformat(),
                    "last_status": f"error: {exc}",
                },
            )
            self.db.mark_job_finished(job["id"], "failed", error=str(exc))
            return {"job": self.db.get_job(job["id"]), "error": str(exc)}

    def _resolve_job_window(
        self, job: dict[str, Any], camera: dict[str, Any], settings: dict[str, Any]
    ):
        payload = json.loads(job.get("payload_json") or "{}")
        if payload.get("start_ts") and payload.get("end_ts"):
            return payload["start_ts"], payload["end_ts"]
        end_dt = datetime.now(timezone.utc)
        interval = int(
            camera.get("interval_seconds")
            or settings.get("analysis_interval_seconds")
            or 300
        )
        start_dt = end_dt - timedelta(seconds=interval)
        return start_dt.isoformat(), end_dt.isoformat()

    def _capture_snapshot(self, camera_name: str) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest = DATA_ROOT / "evidence" / "snapshots" / f"{camera_name}_{stamp}.jpg"
        return self.frigate_client().fetch_latest_snapshot(camera_name, dest)

    def camera_health(self, camera_id: int):
        return self.db.camera_health(camera_id)

    def all_cameras_health(self):
        return self.db.all_cameras_health()

    def jobs(self, status: str | None = None, camera_id: int | None = None):
        return self.db.list_jobs(status=status, camera_id=camera_id)

    def job(self, job_id: int):
        return self.db.get_job(job_id)

    def segments(
        self,
        camera_id: int | None = None,
        label: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        min_confidence: float | None = None,
    ):
        return self.db.list_segments(
            camera_id=camera_id,
            label=label,
            from_ts=from_ts,
            to_ts=to_ts,
            min_confidence=min_confidence,
        )

    def segment(self, segment_id: int):
        return self.db.get_segment(segment_id)

    def review_segment(
        self,
        segment_id: int,
        reviewed_label: str,
        review_note: str,
        review_by: str = "operator",
    ):
        result = self.db.review_segment(
            segment_id, reviewed_label, review_note, review_by
        )
        self.db.log_audit(
            review_by,
            "segment.review",
            "segment",
            str(segment_id),
            {"reviewed_label": reviewed_label, "review_note": review_note},
        )
        return result

    def chart_daily(self, days: int = 7):
        return self.db.chart_daily(days)

    def report_daily(self, day: str):
        day = day or datetime.now(timezone.utc).date().isoformat()
        report = self.db.report_daily(day)
        path = DATA_ROOT / "reports" / "daily" / f"{day}.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
