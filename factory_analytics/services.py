from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from factory_analytics.config import DATA_ROOT
from factory_analytics.database import Database
from factory_analytics.image_annotations import draw_person_boxes
from factory_analytics.image_composition import merge_group_snapshots
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

    def create_camera(
        self,
        frigate_name: str,
        name: str | None = None,
        enabled: bool | None = None,
        interval_seconds: int | None = None,
    ) -> dict[str, Any]:
        camera = self.db.upsert_camera(frigate_name, name)
        updates: dict[str, Any] = {}
        if enabled is not None:
            updates["enabled"] = 1 if enabled else 0
        if interval_seconds is not None:
            updates["interval_seconds"] = int(interval_seconds)
        if updates:
            camera = self.db.update_camera(camera["id"], updates) or camera
        self.db.log_audit(
            "api",
            "camera.create",
            "camera",
            str(camera["id"]),
            {
                "frigate_name": frigate_name,
                **({"name": name} if name else {}),
                **updates,
            },
        )
        return camera

    def delete_camera(self, camera_id: int) -> dict[str, Any]:
        # Soft-delete not implemented; perform hard delete via DB cascade
        # Implement as update to enabled=0 if needed later
        existing = self.db.get_camera(camera_id)
        if not existing:
            return {"deleted": False, "error": "not found"}
        with self.db.connect() as conn:
            cur = conn.execute("DELETE FROM cameras WHERE id=?", (camera_id,))
            deleted = cur.rowcount
        self.db.log_audit("api", "camera.delete", "camera", str(camera_id))
        return {"deleted": bool(deleted)}

    def delete_camera_by_name(self, frigate_name: str) -> dict[str, Any]:
        existing = self.db.get_camera_by_frigate_name(frigate_name)
        if not existing:
            return {"deleted": False, "error": "not found"}
        with self.db.connect() as conn:
            cur = conn.execute(
                "DELETE FROM cameras WHERE frigate_name=?", (frigate_name,)
            )
            deleted = cur.rowcount
        self.db.log_audit(
            "api",
            "camera.delete",
            "camera",
            str(existing["id"]),
            {"frigate_name": frigate_name},
        )
        return {"deleted": bool(deleted), "camera_id": existing["id"]}

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

    def get_camera(self, camera_id: int):
        return self.db.get_camera(camera_id)

    def create_group(self, group_type: str, name: str, interval_seconds: int = 300):
        group = self.db.create_group(group_type, name, interval_seconds)
        self.db.log_audit("api", "group.create", "group", str(group["id"]), group)
        return group

    def list_groups(self):
        return self.db.list_groups()

    def update_group(
        self,
        group_id: int,
        group_type: str | None = None,
        name: str | None = None,
        interval_seconds: int | None = None,
    ):
        group = self.db.update_group(group_id, group_type, name, interval_seconds)
        if group:
            self.db.log_audit(
                "api",
                "group.update",
                "group",
                str(group_id),
                {
                    "group_type": group_type,
                    "name": name,
                    "interval_seconds": interval_seconds,
                },
            )
        return group

    def delete_group(self, group_id: int):
        result = self.db.delete_group(group_id)
        self.db.log_audit("api", "group.delete", "group", str(group_id), result)
        return result

    def add_camera_to_group(self, group_id: int, camera_id: int):
        group = self.db.get_group(group_id)
        camera = self.db.get_camera(camera_id)
        if not group or not camera:
            return None
        result = self.db.add_camera_to_group(camera_id, group_id)
        self.db.log_audit(
            "api",
            "group.camera.add",
            "group",
            str(group_id),
            {"camera_id": camera_id},
        )
        return result

    def remove_camera_from_group(self, group_id: int, camera_id: int):
        result = self.db.remove_camera_from_group(camera_id, group_id)
        self.db.log_audit(
            "api",
            "group.camera.remove",
            "group",
            str(group_id),
            {"camera_id": camera_id, "deleted": result.get("deleted")},
        )
        return result

    def camera_groups(self, camera_id: int):
        return self.db.list_camera_groups(camera_id)

    def group_cameras(self, group_id: int):
        return self.db.list_group_cameras(group_id)

    def queue_group_analysis(self, group_id: int):
        group = self.db.get_group(group_id)
        cameras = self.db.list_group_cameras(group_id)
        if not group:
            raise RuntimeError("Group not found")
        if not cameras:
            raise RuntimeError("Group has no cameras")
        anchor_camera = cameras[0]
        snapshots = []
        included_cameras: list[str] = []
        missing_cameras: list[str] = []
        for camera in cameras:
            try:
                snapshot = self._capture_snapshot(camera["frigate_name"])
                snapshots.append((camera["frigate_name"], snapshot))
                included_cameras.append(camera["frigate_name"])
            except Exception:
                missing_cameras.append(camera["frigate_name"])
        if not snapshots:
            raise RuntimeError("All group camera snapshots failed")
        job = self.db.schedule_group_job(
            group_id=group_id,
            anchor_camera_id=anchor_camera["id"],
            payload={
                "included_cameras": included_cameras,
                "missing_cameras": missing_cameras,
                "group_name": group["name"],
                "group_type": group["group_type"],
            },
        )
        self.db.mark_job_running(job["id"])
        try:
            composite = self._group_composite_path(group["group_type"], group["name"])
            composite = merge_group_snapshots(snapshots, composite)
            result = self.ollama_client().classify_group_image(composite)
            annotated = self._group_annotated_path(group["group_type"], group["name"])
            draw_person_boxes(composite, annotated, result.get("boxes", []))
            notes = result.get("notes", "")
            if missing_cameras:
                suffix = f" Missing cameras: {', '.join(missing_cameras)}."
                notes = f"{notes}{suffix}".strip()
            start_ts = datetime.now(timezone.utc).isoformat()
            end_ts = start_ts
            segment = self.db.create_segment(
                job_id=job["id"],
                camera_id=anchor_camera["id"],
                start_ts=start_ts,
                end_ts=end_ts,
                label=result["label"],
                confidence=float(result["confidence"]),
                notes=notes,
                evidence_path=str(annotated.relative_to(DATA_ROOT.parent)),
            )
            stored_result = {
                **result,
                "notes": notes,
                "included_cameras": included_cameras,
                "missing_cameras": missing_cameras,
                "group_id": group_id,
                "group_name": group["name"],
                "group_type": group["group_type"],
                "segment_id": segment["id"],
            }
            self.db.mark_job_finished(
                job["id"],
                "success",
                raw_result=stored_result,
                snapshot_path=str(annotated.relative_to(DATA_ROOT.parent)),
            )
            return {
                "ok": True,
                "group": group,
                "job_id": job["id"],
                "segment_id": segment["id"],
                "camera_count": len(included_cameras),
                "included_cameras": included_cameras,
                "missing_cameras": missing_cameras,
                "label": result["label"],
                "confidence": result["confidence"],
                "notes": notes,
                "evidence_path": str(annotated.relative_to(DATA_ROOT.parent)),
            }
        except Exception as exc:
            self.db.mark_job_finished(job["id"], "failed", error=str(exc))
            raise

    def test_ollama_vision(self):
        settings = self.settings()
        health = self.ollama_client().health()
        if not health.get("ok"):
            return {
                "ok": False,
                "message": f"Ollama health failed: {health.get('message', 'unknown error')}",
            }
        model = settings.get("ollama_vision_model")
        models = set(health.get("models") or [])
        if model not in models:
            return {
                "ok": False,
                "message": f"Configured model not available: {model}",
                "model": model,
            }
        cameras = [c for c in self.db.list_cameras() if c.get("enabled")]
        if not cameras:
            cameras = self.db.list_cameras()
        if not cameras:
            return {
                "ok": False,
                "message": "No cameras available for vision test",
                "model": model,
            }
        camera = cameras[0]
        try:
            snapshot_path = self._capture_snapshot(camera["frigate_name"])
            result = self.ollama_client().classify_image(snapshot_path)
            return {
                "ok": True,
                "message": "Vision test passed",
                "model": model,
                "camera": camera["frigate_name"],
                "label": result.get("label"),
                "confidence": result.get("confidence", 0.0),
            }
        except Exception as exc:
            return {
                "ok": False,
                "message": str(exc),
                "model": model,
                "camera": camera["frigate_name"],
            }

    def test_ollama_api(self) -> dict[str, Any]:
        settings = self.settings()
        health = self.ollama_client().health()
        if not health.get("ok"):
            return {
                "ok": False,
                "message": f"Ollama unreachable: {health.get('message', 'unknown error')}",
            }
        model = settings.get("ollama_vision_model")
        models = set(health.get("models") or [])
        model_found = model in models
        return {
            "ok": True,
            "model_found": model_found,
            "message": "API reachable"
            + (
                f" (Model '{model}' found)"
                if model_found
                else f" (Model '{model}' NOT found)"
            ),
            "available_models": list(models),
        }

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
            annotated_path = self._annotated_snapshot_path(camera["frigate_name"])
            draw_person_boxes(snapshot_path, annotated_path, result.get("boxes", []))
            start_ts, end_ts = self._resolve_job_window(job, camera, settings)
            segment = self.db.create_segment(
                job_id=job["id"],
                camera_id=camera["id"],
                start_ts=start_ts,
                end_ts=end_ts,
                label=result["label"],
                confidence=float(result["confidence"]),
                notes=result.get("notes", ""),
                evidence_path=str(annotated_path.relative_to(DATA_ROOT.parent)),
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
                snapshot_path=str(annotated_path.relative_to(DATA_ROOT.parent)),
            )
            return {"job": self.db.get_job(job["id"]), "segment": segment}
        except Exception as exc:
            logger.exception("Job processing failed")
            self.db.update_camera(
                camera["id"],
                {
                    "last_run_at": datetime.now(timezone.utc).isoformat(),
                    "last_status": f"error: {str(exc)[:180]}",
                },
            )
            self.db.mark_job_finished(job["id"], "failed", error=str(exc))
            return {"job": self.db.get_job(job["id"]), "error": str(exc)}

    def probe_analysis(
        self, camera_id: int | None = None, frigate_name: str | None = None
    ) -> dict[str, Any]:
        # Try snapshot twice: latest.jpg then snapshot.jpg are already attempted by client.
        # Here we add one retry cycle to mitigate transient stalls.
        def _once() -> tuple[bool, dict[str, Any]]:
            try:
                if camera_id is not None:
                    camera = self.db.get_camera(camera_id)
                    if not camera:
                        return False, {"ok": False, "error": "Camera not found"}
                    name = camera["frigate_name"]
                else:
                    assert frigate_name is not None
                    name = frigate_name
                snapshot_path = self._capture_snapshot(name)
                result = self.ollama_client().classify_image(snapshot_path)
                return True, {
                    "ok": True,
                    "label": result.get("label", "uncertain"),
                    "confidence": float(result.get("confidence", 0.0)),
                }
            except Exception as exc:
                return False, {"ok": False, "error": str(exc)}

        ok, res = _once()
        if ok:
            return res
        # Retry once after a short wait
        try:
            import time

            time.sleep(1.0)
        except Exception:
            pass
        ok2, res2 = _once()
        if ok2:
            return res2
        logger.warning("Probe analysis failed twice: %s", res2.get("error"))
        return res2

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

    def _annotated_snapshot_path(self, camera_name: str) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return (
            DATA_ROOT
            / "evidence"
            / "snapshots"
            / f"{camera_name}_{stamp}_annotated.jpg"
        )

    def _group_composite_path(self, group_type: str, group_name: str) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        slug = f"{group_type}_{group_name}".replace(" ", "_").replace("/", "_")
        return DATA_ROOT / "evidence" / "groups" / f"{slug}_{stamp}.jpg"

    def _group_annotated_path(self, group_type: str, group_name: str) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        slug = f"{group_type}_{group_name}".replace(" ", "_").replace("/", "_")
        return DATA_ROOT / "evidence" / "groups" / f"{slug}_{stamp}_annotated.jpg"

    def camera_health(self, camera_id: int):
        return self.db.camera_health(camera_id)

    def all_cameras_health(self):
        return self.db.all_cameras_health()

    def jobs(self, status: str | None = None, camera_id: int | None = None):
        return self.db.list_jobs(status=status, camera_id=camera_id)

    def jobs_paginated(
        self,
        page: int = 1,
        page_size: int = 25,
        status: str | None = None,
        camera_id: int | None = None,
        group_id: int | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        shift: str | None = None,
        sort_by: str = "id",
        sort_dir: str = "desc",
    ):
        tz_name = self.settings().get("timezone") or "UTC"
        return self.db.list_jobs_paginated(
            page,
            page_size,
            status,
            camera_id,
            from_ts,
            to_ts,
            shift,
            sort_by,
            sort_dir,
            tz_name,
            group_id,
        )

    def job(self, job_id: int):
        return self.db.get_job(job_id)

    def segments(
        self,
        camera_id: int | None = None,
        label: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        min_confidence: float | None = None,
        limit: int = 200,
        offset: int = 0,
    ):
        return self.db.list_segments(
            camera_id=camera_id,
            label=label,
            from_ts=from_ts,
            to_ts=to_ts,
            min_confidence=min_confidence,
            limit=limit,
            offset=offset,
        )

    def segments_paginated(
        self,
        page: int = 1,
        page_size: int = 25,
        camera_id: int | None = None,
        group_id: int | None = None,
        label: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        shift: str | None = None,
        sort_by: str = "id",
        sort_dir: str = "desc",
    ):
        tz_name = self.settings().get("timezone") or "UTC"
        return self.db.list_segments_paginated(
            page,
            page_size,
            camera_id,
            label,
            from_ts,
            to_ts,
            shift,
            sort_by,
            sort_dir,
            tz_name,
            group_id,
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

    def chart_heatmap(self):
        return self.db.chart_heatmap()

    def chart_heatmap_by_group(self):
        return self.db.chart_heatmap_by_group()

    def chart_shift_summary(self):
        tz_name = self.settings().get("timezone") or "UTC"
        return self.db.chart_shift_summary(tz_name)

    def chart_camera_summary(self):
        return self.db.chart_camera_summary()

    def chart_job_failures(self):
        return self.db.chart_job_failures()

    def chart_confidence_distribution(self):
        return self.db.chart_confidence_distribution()

    def report_daily(self, day: str):
        day = day or datetime.now(timezone.utc).date().isoformat()
        report = self.db.report_daily(day)
        path = DATA_ROOT / "reports" / "daily" / f"{day}.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
