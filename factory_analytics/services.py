from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from factory_analytics.config import DATA_ROOT
from factory_analytics.database import Database
from factory_analytics.integrations.frigate import FrigateClient
from factory_analytics.integrations.ollama import OpenAIClient
from factory_analytics.integrations.image_pipeline import (
    fetch_frames,
    resize_pil_image,
    build_vertical_strip,
    build_group_collage,
)
from factory_analytics.logging_setup import setup_logging

logger = setup_logging()

try:
    from PIL import Image
except ImportError:
    Image = None


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

    def ollama_client(self) -> OpenAIClient:
        return OpenAIClient(self.settings())

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
        job = self.db.schedule_group_job(
            camera_id=anchor_camera["id"],
            group_id=group_id,
            group_type=group["group_type"],
            group_name=group["name"],
        )
        self.db.log_audit(
            "api", "job.schedule_group", "job", str(job["id"]), {"group_id": group_id}
        )
        return {"ok": True, "job_id": job["id"], "group_id": group_id}

    def test_ollama_vision(self):
        settings = self.settings()
        health = self.ollama_client().health()
        if not health.get("ok"):
            return {
                "ok": False,
                "message": f"Ollama health failed: {health.get('message', 'unknown error')}",
            }
        model = settings.get("llm_vision_model")
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
        model = settings.get("llm_vision_model")
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

        # Handle group_analysis jobs differently
        if job.get("job_type") == "group_analysis":
            return self._process_group_job(job)

        return self._process_single_job(job)

    def _process_single_job(self, job: dict[str, Any]) -> dict[str, Any]:
        settings = self.settings()
        camera = self.db.get_camera(job["camera_id"])
        try:
            img_settings = self._get_image_settings()
            frame_result = self._process_frame_collection_for_camera(
                camera, img_settings
            )
            frame_paths = frame_result["frame_paths"]
            images_to_send = frame_paths or [frame_result["strip_path"]]
            seconds_apart = img_settings.get("seconds_window", 1)
            result = self.ollama_client().classify_images(
                images_to_send, seconds_apart=seconds_apart
            )
            stored_frames = [
                str(path.relative_to(DATA_ROOT.parent)) for path in images_to_send
            ]
            primary_evidence_path = stored_frames[0]
            start_ts, end_ts = self._resolve_job_window(job, camera, settings)
            segment = self.db.create_segment(
                job_id=job["id"],
                camera_id=camera["id"],
                start_ts=start_ts,
                end_ts=end_ts,
                label=result["label"],
                confidence=float(result["confidence"]),
                notes=result.get("notes", ""),
                evidence_path=primary_evidence_path,
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
            stored_result = {
                **result,
                "frame_count": len(stored_frames),
                "primary_evidence_path": primary_evidence_path,
                "evidence_frames": stored_frames,
            }
            self.db.mark_job_finished(
                job["id"],
                "success",
                raw_result=stored_result,
                snapshot_path=primary_evidence_path,
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

    def _process_group_job(self, job: dict[str, Any]) -> dict[str, Any]:
        payload = json.loads(job.get("payload_json") or "{}")
        group_id = payload.get("group_id")
        if not group_id:
            self.db.mark_job_finished(
                job["id"], "failed", error="Missing group_id in payload"
            )
            return {"job": self.db.get_job(job["id"]), "error": "Missing group_id"}

        try:
            result = self._execute_group_analysis(job, group_id)
            return result
        except Exception as exc:
            logger.exception("Group job processing failed")
            self.db.mark_job_finished(job["id"], "failed", error=str(exc))
            return {"job": self.db.get_job(job["id"]), "error": str(exc)}

    def _execute_group_analysis(
        self, job: dict[str, Any], group_id: int
    ) -> dict[str, Any]:
        group = self.db.get_group(group_id)
        cameras = self.db.list_group_cameras(group_id)
        img_settings = self._get_image_settings()
        if not group:
            raise RuntimeError("Group not found")
        if not cameras:
            raise RuntimeError("Group has no cameras")

        anchor_camera = cameras[0]
        included_cameras: list[str] = []
        missing_cameras: list[str] = []

        camera_frames: list[list[tuple[str, Path]]] = []
        for camera in cameras:
            try:
                frame_result = self._process_frame_collection_for_camera(
                    camera, img_settings
                )
                frames = (
                    frame_result["frame_paths"]
                    if frame_result["frame_paths"]
                    else [frame_result["strip_path"]]
                )
                camera_frames.append([(camera["frigate_name"], f) for f in frames])
                included_cameras.append(camera["frigate_name"])
            except Exception:
                missing_cameras.append(camera["frigate_name"])

        if not camera_frames:
            raise RuntimeError("All group camera snapshots failed")

        frame_count = max(len(cf) for cf in camera_frames)
        camera_frames = [
            cf + [(cf[0][0], cf[0][1])] * (frame_count - len(cf))
            for cf in camera_frames
        ]

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        slug = f"{group['group_type']}_{group['name']}".replace(" ", "_").replace(
            "/", "_"
        )
        collage_dir = DATA_ROOT / "evidence" / "groups" / f"{slug}_{stamp}"
        collage_dir.mkdir(parents=True, exist_ok=True)

        per_frame_collages: list[Path] = []
        for frame_idx in range(frame_count):
            frame_cameras = [
                (cf[frame_idx][0], cf[frame_idx][1]) for cf in camera_frames
            ]
            collage_path = collage_dir / f"frame_{frame_idx}_collage.jpg"
            if len(frame_cameras) == 1:
                import shutil

                shutil.copy2(str(frame_cameras[0][1]), str(collage_path))
            else:
                collage_path = build_group_collage(frame_cameras, collage_path)
            per_frame_collages.append(collage_path)

        seconds_apart = img_settings.get("seconds_window", 1)
        result = self.ollama_client().classify_group_images(
            per_frame_collages,
            seconds_apart=seconds_apart,
            camera_count=len(included_cameras),
        )
        result = self._apply_group_label_rule(result)

        notes = result.get("notes", "")
        if missing_cameras:
            suffix = f" Missing cameras: {', '.join(missing_cameras)}."
            notes = f"{notes}{suffix}".strip()

        stored_frames = [
            str(path.relative_to(DATA_ROOT.parent)) for path in per_frame_collages
        ]
        primary_evidence_path = stored_frames[0]
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
            evidence_path=primary_evidence_path,
        )

        stored_result = {
            **result,
            "notes": notes,
            "frame_count": len(stored_frames),
            "primary_evidence_path": primary_evidence_path,
            "evidence_frames": stored_frames,
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
            snapshot_path=primary_evidence_path,
        )

        return {
            "ok": True,
            "group": group,
            "job_id": job["id"],
            "segment_id": segment["id"],
            "camera_count": len(included_cameras),
            "missing_count": len(missing_cameras),
        }

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

    def _get_image_settings(self) -> dict[str, Any]:
        settings = self.settings()
        resolution_map = {
            "320p": 320,
            "640p": 640,
            "720p": 720,
            "original": 0,
        }
        frames_count = max(1, int(settings.get("llm_frames_per_process", 1)))
        seconds_window = max(1, int(settings.get("llm_seconds_window", 3)))
        return {
            "frames": frames_count,
            "seconds_window": seconds_window,
            "resolution": resolution_map.get(
                settings.get("image_resize_resolution", "original"), 0
            ),
            "quality": int(settings.get("image_compression_quality", 100)),
        }

    def _process_frame_collection_for_camera(
        self, camera: dict[str, Any], img_settings: dict[str, Any]
    ) -> dict[str, Any]:
        """Collect frames for a camera, process them, build a strip.

        Returns dict with:
          - strip_path: Path to the vertical strip (for LLM classification)
          - frame_paths: List of individual frame paths
        """
        frigate = self.frigate_client()
        camera_name = camera["frigate_name"]
        count = img_settings["frames"]

        if count <= 1:
            single = self._capture_snapshot(camera_name)
            return {
                "strip_path": single,
                "frame_paths": [single],
            }

        frames = fetch_frames(frigate, camera_name, count)

        max_dim = img_settings["resolution"]
        if max_dim > 0:
            frames = [resize_pil_image(f, max_dim) for f in frames]

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        frame_dir = DATA_ROOT / "evidence" / "frames" / f"{camera_name}_{stamp}"
        frame_dir.mkdir(parents=True, exist_ok=True)
        quality = img_settings["quality"]
        frame_paths = []
        for i, f in enumerate(frames):
            fp = frame_dir / f"frame_{i}.jpg"
            f.save(str(fp), "JPEG", quality=quality)
            frame_paths.append(fp)

        if len(frame_paths) == 1:
            return {
                "strip_path": frame_paths[0],
                "frame_paths": frame_paths,
            }

        strip_name = f"{camera_name}_{stamp}_strip.jpg"
        strip_path = DATA_ROOT / "evidence" / "snapshots" / strip_name
        strip_path = build_vertical_strip(frames, camera_name, strip_path)

        # Save strip at the same quality
        strip_path.parent.mkdir(parents=True, exist_ok=True)
        # Re-save strip with configured quality
        strip_img = Image.open(str(strip_path)).convert("RGB")
        strip_img.save(str(strip_path), "JPEG", quality=quality)

        return {
            "strip_path": strip_path,
            "frame_paths": frame_paths,
        }

    def _apply_group_label_rule(self, result: dict[str, Any]) -> dict[str, Any]:
        observations = result.get("observations") or []
        if any(item.get("label") == "working" for item in observations):
            return {
                **result,
                "label": "working",
                "notes": result.get("notes")
                or "working activity visible in at least one collage",
            }
        return result

    def _group_composite_path(self, group_type: str, group_name: str) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        slug = f"{group_type}_{group_name}".replace(" ", "_").replace("/", "_")
        return DATA_ROOT / "evidence" / "groups" / f"{slug}_{stamp}.jpg"

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
        job_type: str | None = None,
        job_id: int | None = None,
    ):
        tz_name = self.settings().get("timezone") or "UTC"
        result = self.db.list_jobs_paginated(
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
            job_type,
            job_id,
        )
        return {
            "jobs": result.get("items", []),
            "total": result.get("total", 0),
            "page": page,
            "page_size": page_size,
            "total_pages": max(
                1, (result.get("total", 0) + page_size - 1) // page_size
            ),
        }

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

    def efficiency_heatmap_minute(
        self, date: str, camera_id: int | None = None
    ) -> dict[str, Any]:
        """Get per-minute efficiency data for a specific date."""
        return self.db.efficiency_heatmap_minute(date, camera_id)

    def efficiency_summary(
        self, from_date: str, to_date: str, camera_id: int | None = None
    ) -> dict[str, Any]:
        """Get efficiency summary for a date range."""
        return self.db.efficiency_summary(from_date, to_date, camera_id)

    def efficiency_heatmap_daily(
        self, from_date: str, to_date: str, camera_id: int | None = None
    ) -> dict[str, Any]:
        """Get daily aggregated efficiency data."""
        return self.db.efficiency_heatmap_daily(from_date, to_date, camera_id)

    def efficiency_timeline(
        self,
        date: str,
        camera_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Get timeline of activity for a specific date."""
        return self.db.efficiency_timeline(date, camera_id, page, page_size)

    def efficiency_heatmap_chart(
        self,
        from_date: str,
        to_date: str,
        view: str = "daily",
    ) -> dict[str, Any]:
        """Get heatmap chart data for enabled cameras in groups."""
        return self.db.efficiency_heatmap_chart(from_date, to_date, view)

    def photos_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        date_from: str | None = None,
        date_to: str | None = None,
        days: list[int] | None = None,
        time_from: int | None = None,
        time_to: int | None = None,
        cameras: list[int] | None = None,
        groups: list[int] | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get paginated photos with evidence, with filtering."""
        tz_name = self.settings().get("timezone") or "UTC"
        return self.db.list_photos_paginated(
            page=page,
            page_size=page_size,
            date_from=date_from,
            date_to=date_to,
            days=days,
            time_from=time_from,
            time_to=time_to,
            cameras=cameras,
            groups=groups,
            labels=labels,
            tz_name=tz_name,
        )
