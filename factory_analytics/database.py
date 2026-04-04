from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from factory_analytics.config import (
    SQLITE_PATH,
    ANALYSIS_INTERVAL_SECONDS,
    TIMEZONE,
    FRIGATE_URL,
    LLM_URL,
    LLM_VISION_MODEL,
    SCHEDULER_ENABLED,
    PUBLIC_BASE_URL,
)

# Reusable SQL snippet for extracting the model used from a job (alias j).
MODEL_USED_SQL = (
    "COALESCE(json_extract(j.raw_result, '$.raw.model'),"
    " json_extract(j.raw_result, '$.model'),"
    " json_extract(j.payload_json, '$.model'),"
    " json_extract(j.payload_json, '$.llm_vision_model')) AS model_used"
)
from factory_analytics.logging_setup import setup_logging

logger = setup_logging()

DEFAULT_SETTINGS = {
    "timezone": TIMEZONE,
    "frigate_url": FRIGATE_URL,
    "frigate_auth_mode": "none",
    "frigate_username": "",
    "frigate_password": "",
    "frigate_bearer_token": "",
    "frigate_verify_tls": False,
    "llm_url": LLM_URL,
    "llm_vision_model": LLM_VISION_MODEL,
    "llm_timeout_sec": 120,
    "llm_api_key": "",
    "llm_enabled": True,
    "analysis_interval_seconds": ANALYSIS_INTERVAL_SECONDS,
    "scheduler_enabled": SCHEDULER_ENABLED,
    "public_base_url": PUBLIC_BASE_URL,
    "host_bind": "0.0.0.0",
    "frigate_snapshot_timeout_sec": 30,
    "group_scheduler_enabled": True,
    "group_analysis_interval_seconds": 300,
    "group_retry_attempts": 3,
    "group_retry_delay_seconds": 60,
    # NEW: LLM image sampling & optimization settings
    "llm_frames_per_process": 1,
    "llm_seconds_window": 3,
    "image_resize_resolution": "original",
    "image_compression_quality": 100,
    # NEW: Job timeout
    "job_timeout_seconds": 600,
    "evidence_retention_days": 30,
}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def shift_for_iso(ts: str, tz_name: str) -> str:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(ZoneInfo(tz_name))
    hour = local.hour
    return "day" if 9 <= hour < 21 else "night"


class Database:
    def __init__(self, path: Path = SQLITE_PATH):
        self.path = path
        self.initialize()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self):
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cameras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    frigate_name TEXT NOT NULL UNIQUE,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    kind TEXT NOT NULL DEFAULT 'worker_monitoring',
                    interval_seconds INTEGER NOT NULL DEFAULT 300,
                    last_run_at TEXT,
                    last_status TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    interval_seconds INTEGER DEFAULT 300,
                    last_run_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(group_type, name)
                );
                CREATE TABLE IF NOT EXISTS camera_groups (
                    camera_id INTEGER NOT NULL,
                    group_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(camera_id, group_id),
                    FOREIGN KEY(camera_id) REFERENCES cameras(id) ON DELETE CASCADE,
                    FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    camera_id INTEGER NOT NULL,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    scheduled_for TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    snapshot_path TEXT,
                    raw_result TEXT,
                    error TEXT,
                    payload_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(camera_id) REFERENCES cameras(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    camera_id INTEGER NOT NULL,
                    start_ts TEXT NOT NULL,
                    end_ts TEXT NOT NULL,
                    label TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    notes TEXT,
                    evidence_path TEXT,
                    reviewed_label TEXT,
                    review_note TEXT,
                    review_by TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
                    FOREIGN KEY(camera_id) REFERENCES cameras(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS daily_rollups (
                    day TEXT NOT NULL,
                    camera_id INTEGER NOT NULL,
                    working_seconds INTEGER NOT NULL DEFAULT 0,
                    idle_seconds INTEGER NOT NULL DEFAULT 0,
                    sleeping_seconds INTEGER NOT NULL DEFAULT 0,
                    uncertain_seconds INTEGER NOT NULL DEFAULT 0,
                    stopped_seconds INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(day, camera_id),
                    FOREIGN KEY(camera_id) REFERENCES cameras(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT,
                    payload_json TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            now = utcnow()
            key_map = {
                "ollama_url": "llm_url",
                "ollama_vision_model": "llm_vision_model",
                "ollama_timeout_sec": "llm_timeout_sec",
                "ollama_keep_alive": None,
                "ollama_enabled": "llm_enabled",
                "ollama_fallback_to_vision": None,
            }
            for old_key, new_key in key_map.items():
                row = conn.execute(
                    "SELECT key, value FROM settings WHERE key = ?", (old_key,)
                ).fetchone()
                if row:
                    if new_key:
                        existing_new = conn.execute(
                            "SELECT key FROM settings WHERE key = ?", (new_key,)
                        ).fetchone()
                        if not existing_new:
                            conn.execute(
                                "INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?)",
                                (new_key, row["value"], now),
                            )
                    conn.execute("DELETE FROM settings WHERE key = ?", (old_key,))
            existing = {
                row["key"]
                for row in conn.execute("SELECT key FROM settings").fetchall()
            }
            for key, value in DEFAULT_SETTINGS.items():
                if key not in existing:
                    conn.execute(
                        "INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?)",
                        (key, json.dumps(value), now),
                    )

    def get_settings(self) -> dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            return {row["key"]: json.loads(row["value"]) for row in rows}

    def update_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utcnow()
        with self.connect() as conn:
            for key, value in payload.items():
                if key == "llm_api_key" and value == "":
                    continue
                conn.execute(
                    """INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                    (key, json.dumps(value), now),
                )
        return self.get_settings()

    def log_audit(
        self,
        actor: str,
        action: str,
        target_type: str,
        target_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO audit_log(actor, action, target_type, target_id, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    actor,
                    action,
                    target_type,
                    target_id,
                    json.dumps(payload or {}),
                    utcnow(),
                ),
            )

    def upsert_camera(
        self, frigate_name: str, name: str | None = None
    ) -> dict[str, Any]:
        now = utcnow()
        display = name or frigate_name
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO cameras(name, frigate_name, enabled, kind, interval_seconds, created_at, updated_at)
                   VALUES (?, ?, 0, 'worker_monitoring', 300, ?, ?)
                   ON CONFLICT(frigate_name) DO UPDATE SET name=excluded.name, updated_at=excluded.updated_at""",
                (display, frigate_name, now, now),
            )
        return self.get_camera_by_frigate_name(frigate_name)

    def list_cameras(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM cameras ORDER BY id").fetchall()
            return [dict(row) for row in rows]

    def create_group(
        self, group_type: str, name: str, interval_seconds: int = 300
    ) -> dict[str, Any]:
        now = utcnow()
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO groups(group_type, name, interval_seconds, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(group_type, name) DO UPDATE SET updated_at=excluded.updated_at, interval_seconds=excluded.interval_seconds""",
                (group_type, name, interval_seconds, now, now),
            )
        return self.get_group_by_type_name(group_type, name)

    def list_groups(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM groups ORDER BY group_type, name, id"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_group(self, group_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM groups WHERE id=?", (group_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_group_by_type_name(
        self, group_type: str, name: str
    ) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM groups WHERE group_type=? AND name=?",
                (group_type, name),
            ).fetchone()
            return dict(row) if row else None

    def update_group(
        self,
        group_id: int,
        group_type: str | None = None,
        name: str | None = None,
        interval_seconds: int | None = None,
        last_run_at: str | None = None,
    ) -> dict[str, Any] | None:
        group = self.get_group(group_id)
        if not group:
            return None
        next_type = group_type or group["group_type"]
        next_name = name or group["name"]
        next_interval = (
            interval_seconds
            if interval_seconds is not None
            else group["interval_seconds"]
        )
        next_last_run = last_run_at if last_run_at is not None else group["last_run_at"]
        with self.connect() as conn:
            conn.execute(
                "UPDATE groups SET group_type=?, name=?, interval_seconds=?, last_run_at=?, updated_at=? WHERE id=?",
                (
                    next_type,
                    next_name,
                    next_interval,
                    next_last_run,
                    utcnow(),
                    group_id,
                ),
            )
        return self.get_group(group_id)

    def delete_group(self, group_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM groups WHERE id=?", (group_id,))
        return {"deleted": bool(cur.rowcount), "group_id": group_id}

    def add_camera_to_group(self, camera_id: int, group_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO camera_groups(camera_id, group_id, created_at) VALUES (?, ?, ?)",
                (camera_id, group_id, utcnow()),
            )
        return {"camera_id": camera_id, "group_id": group_id}

    def remove_camera_from_group(self, camera_id: int, group_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            cur = conn.execute(
                "DELETE FROM camera_groups WHERE camera_id=? AND group_id=?",
                (camera_id, group_id),
            )
        return {
            "deleted": bool(cur.rowcount),
            "camera_id": camera_id,
            "group_id": group_id,
        }

    def list_group_cameras(self, group_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT c.* FROM camera_groups cg
                   JOIN cameras c ON c.id = cg.camera_id
                   WHERE cg.group_id=? ORDER BY c.id""",
                (group_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_camera_groups(self, camera_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT g.* FROM camera_groups cg
                   JOIN groups g ON g.id = cg.group_id
                   WHERE cg.camera_id=? ORDER BY g.group_type, g.name, g.id""",
                (camera_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_camera(self, camera_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM cameras WHERE id=?", (camera_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_camera_by_frigate_name(self, frigate_name: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM cameras WHERE frigate_name=?", (frigate_name,)
            ).fetchone()
            return dict(row) if row else None

    def update_camera(
        self, camera_id: int, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        allowed = {
            "name",
            "enabled",
            "kind",
            "interval_seconds",
            "last_status",
            "last_run_at",
        }
        fields = [(k, payload[k]) for k in payload if k in allowed]
        if not fields:
            return self.get_camera(camera_id)
        setters = ", ".join(f"{k}=?" for k, _ in fields)
        values = [v for _, v in fields]
        values += [utcnow(), camera_id]
        with self.connect() as conn:
            conn.execute(
                f"UPDATE cameras SET {setters}, updated_at=? WHERE id=?", values
            )
        return self.get_camera(camera_id)

    def schedule_job(
        self,
        camera_id: int,
        job_type: str = "analysis",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = utcnow()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO jobs(camera_id, job_type, status, scheduled_for, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (camera_id, job_type, "pending", now, json.dumps(payload or {}), now),
            )
            job_id = cur.lastrowid
        return self.get_job(job_id)

    def schedule_group_job(
        self, camera_id: int, group_id: int, group_type: str, group_name: str
    ) -> dict[str, Any]:
        with self.connect() as conn:
            now = datetime.now(timezone.utc).isoformat()
            cur = conn.execute(
                """
                INSERT INTO jobs 
                (camera_id, job_type, status, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                RETURNING id, camera_id, status, created_at, payload_json
                """,
                (
                    camera_id,
                    "group_analysis",
                    "pending",
                    now,
                    json.dumps(
                        {
                            "source": "group_scheduler",
                            "group_id": group_id,
                            "group_type": group_type,
                            "group_name": group_name,
                        }
                    ),
                ),
            )
            row = cur.fetchone()
            return dict(row) if row else {}

    def next_pending_job(self) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                'SELECT * FROM jobs WHERE status="pending" ORDER BY id LIMIT 1'
            ).fetchone()
            return dict(row) if row else None

    def has_active_job(self, camera_id: int, job_type: str = "analysis") -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM jobs WHERE camera_id=? AND job_type=? AND status IN ('pending','running') LIMIT 1",
                (camera_id, job_type),
            ).fetchone()
            return row is not None

    def has_active_group_jobs(self, group_id: int) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                """
                SELECT COUNT(*) FROM jobs 
                WHERE status IN ('pending', 'running')
                AND json_extract(payload_json, '$.group_id') = ?
                """,
                (group_id,),
            )
            count = cur.fetchone()[0]
            return count > 0

    def mark_job_running(self, job_id: int):
        with self.connect() as conn:
            conn.execute(
                "UPDATE jobs SET status=?, started_at=? WHERE id=?",
                ("running", utcnow(), job_id),
            )

    def mark_job_finished(
        self,
        job_id: int,
        status: str,
        raw_result: dict[str, Any] | None = None,
        error: str | None = None,
        snapshot_path: str | None = None,
    ):
        with self.connect() as conn:
            conn.execute(
                "UPDATE jobs SET status=?, finished_at=?, raw_result=?, error=?, snapshot_path=? WHERE id=?",
                (
                    status,
                    utcnow(),
                    json.dumps(raw_result or {}),
                    error,
                    snapshot_path,
                    job_id,
                ),
            )

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            return dict(row) if row else None

    def list_jobs(
        self, limit: int = 100, status: str | None = None, camera_id: int | None = None
    ) -> list[dict[str, Any]]:
        conditions = []
        params: list[Any] = []
        if status is not None:
            conditions.append("j.status = ?")
            params.append(status)
        if camera_id is not None:
            conditions.append("j.camera_id = ?")
            params.append(camera_id)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        with self.connect() as conn:
            rows = conn.execute(
                f"""SELECT j.*, c.name AS camera_name, c.frigate_name AS camera_frigate_name
                   FROM jobs j JOIN cameras c ON c.id = j.camera_id{where}
                   ORDER BY j.id DESC LIMIT ?""",
                (*params, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_jobs_paginated(
        self,
        page: int = 1,
        page_size: int = 25,
        status: str | None = None,
        camera_id: int | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        shift: str | None = None,
        sort_by: str = "id",
        sort_dir: str = "desc",
        tz_name: str = "UTC",
        group_id: int | None = None,
        job_type: str | None = None,
    ) -> dict[str, Any]:
        conditions = []
        params: list[Any] = []
        if status is not None:
            conditions.append("j.status = ?")
            params.append(status)
        if camera_id is not None:
            conditions.append("j.camera_id = ?")
            params.append(camera_id)
        if group_id is not None:
            conditions.append(
                "EXISTS (SELECT 1 FROM camera_groups cg WHERE cg.camera_id = j.camera_id AND cg.group_id = ?)"
            )
            params.append(group_id)
        if job_type is not None:
            conditions.append("j.job_type = ?")
            params.append(job_type)
        if from_ts is not None:
            conditions.append(
                "COALESCE(j.finished_at, j.started_at, j.scheduled_for, j.created_at) >= ?"
            )
            params.append(from_ts)
        if to_ts is not None:
            conditions.append(
                "COALESCE(j.finished_at, j.started_at, j.scheduled_for, j.created_at) <= ?"
            )
            params.append(to_ts)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        order_col = {
            "id": "j.id",
            "status": "j.status",
            "camera": "c.name",
            "time": "COALESCE(j.finished_at, j.started_at, j.scheduled_for, j.created_at)",
        }.get(sort_by, "j.id")
        order_dir = "ASC" if sort_dir.lower() == "asc" else "DESC"
        offset = (max(page, 1) - 1) * page_size
        with self.connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM jobs j JOIN cameras c ON c.id = j.camera_id{where}",
                params,
            ).fetchone()[0]
            rows = conn.execute(
                f"""SELECT j.*, c.name AS camera_name, c.frigate_name AS camera_frigate_name,
                          {MODEL_USED_SQL}
                   FROM jobs j JOIN cameras c ON c.id = j.camera_id{where}
                   ORDER BY {order_col} {order_dir} LIMIT ? OFFSET ?""",
                (*params, page_size, offset),
            ).fetchall()
        items = [dict(row) for row in rows]
        if shift in {"day", "night"}:
            items = [
                item
                for item in items
                if shift_for_iso(
                    item.get("finished_at")
                    or item.get("started_at")
                    or item.get("scheduled_for")
                    or item.get("created_at"),
                    tz_name,
                )
                == shift
            ]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def create_segment(
        self,
        job_id: int,
        camera_id: int,
        start_ts: str,
        end_ts: str,
        label: str,
        confidence: float,
        notes: str = "",
        evidence_path: str | None = None,
    ) -> dict[str, Any]:
        with self.connect() as conn:
            cur = conn.execute(
                """INSERT INTO segments(job_id, camera_id, start_ts, end_ts, label, confidence, notes, evidence_path, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job_id,
                    camera_id,
                    start_ts,
                    end_ts,
                    label,
                    confidence,
                    notes,
                    evidence_path,
                    utcnow(),
                ),
            )
            segment_id = cur.lastrowid
        return self.get_segment(segment_id)

    def get_segment(self, segment_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """SELECT s.*, c.name AS camera_name, c.frigate_name AS camera_frigate_name,
                          j.job_type, j.raw_result, j.payload_json
                   FROM segments s
                   JOIN cameras c ON c.id = s.camera_id
                   JOIN jobs j ON j.id = s.job_id
                   WHERE s.id=?""",
                (segment_id,),
            ).fetchone()
            if not row:
                return None
            item = dict(row)
            raw_result = item.get("raw_result")
            item["raw_result"] = json.loads(raw_result) if raw_result else {}
            payload_json = item.get("payload_json")
            item["payload_json"] = json.loads(payload_json) if payload_json else {}
            item["group_name"] = item["raw_result"].get("group_name")
            item["group_type"] = item["raw_result"].get("group_type")
            item["group_id"] = item["raw_result"].get("group_id")
            return item

    def list_segments(
        self,
        limit: int = 200,
        offset: int = 0,
        camera_id: int | None = None,
        label: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        min_confidence: float | None = None,
    ) -> list[dict[str, Any]]:
        conditions = []
        params: list[Any] = []
        if camera_id is not None:
            conditions.append("s.camera_id = ?")
            params.append(camera_id)
        if label is not None:
            conditions.append("s.label = ?")
            params.append(label)
        if from_ts is not None:
            conditions.append("s.start_ts >= ?")
            params.append(from_ts)
        if to_ts is not None:
            conditions.append("s.end_ts <= ?")
            params.append(to_ts)
        if min_confidence is not None:
            conditions.append("s.confidence >= ?")
            params.append(min_confidence)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        with self.connect() as conn:
            rows = conn.execute(
                f"""SELECT s.*, c.name AS camera_name, c.frigate_name AS camera_frigate_name,
                          j.job_type, j.raw_result, j.payload_json
                   FROM segments s
                   JOIN cameras c ON c.id = s.camera_id
                   LEFT JOIN jobs j ON j.id = s.job_id{where} ORDER BY s.id DESC LIMIT ? OFFSET ?""",
                (*params, limit, offset),
            ).fetchall()
            items = []
            for row in rows:
                item = dict(row)
                raw_result = item.get("raw_result")
                item["raw_result"] = json.loads(raw_result) if raw_result else {}
                payload_json = item.get("payload_json")
                item["payload_json"] = json.loads(payload_json) if payload_json else {}
                item["group_name"] = item["raw_result"].get("group_name")
                item["group_type"] = item["raw_result"].get("group_type")
                item["group_id"] = item["raw_result"].get("group_id")
                items.append(item)
            return items

    def list_segments_paginated(
        self,
        page: int = 1,
        page_size: int = 25,
        camera_id: int | None = None,
        label: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        shift: str | None = None,
        sort_by: str = "id",
        sort_dir: str = "desc",
        tz_name: str = "UTC",
        group_id: int | None = None,
    ) -> dict[str, Any]:
        conditions = []
        params: list[Any] = []
        if camera_id is not None:
            conditions.append("s.camera_id = ?")
            params.append(camera_id)
        if group_id is not None:
            conditions.append(
                "EXISTS (SELECT 1 FROM camera_groups cg WHERE cg.camera_id = s.camera_id AND cg.group_id = ?)"
            )
            params.append(group_id)
        if label is not None:
            conditions.append("s.label = ?")
            params.append(label)
        if from_ts is not None:
            conditions.append("s.start_ts >= ?")
            params.append(from_ts)
        if to_ts is not None:
            conditions.append("s.end_ts <= ?")
            params.append(to_ts)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        order_col = {
            "id": "s.id",
            "confidence": "s.confidence",
            "camera": "c.name",
            "label": "s.label",
            "time": "s.start_ts",
        }.get(sort_by, "s.id")
        order_dir = "ASC" if sort_dir.lower() == "asc" else "DESC"
        offset = (max(page, 1) - 1) * page_size
        with self.connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM segments s JOIN cameras c ON c.id = s.camera_id{where}",
                params,
            ).fetchone()[0]
            rows = conn.execute(
                f"""SELECT s.*, c.name AS camera_name, c.frigate_name AS camera_frigate_name,
                          j.job_type, j.raw_result, j.payload_json,
                          {MODEL_USED_SQL}
                   FROM segments s
                   JOIN cameras c ON c.id = s.camera_id
                   LEFT JOIN jobs j ON j.id = s.job_id{where}
                   ORDER BY {order_col} {order_dir} LIMIT ? OFFSET ?""",
                (*params, page_size, offset),
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            raw_result = item.get("raw_result")
            item["raw_result"] = json.loads(raw_result) if raw_result else {}
            payload_json = item.get("payload_json")
            item["payload_json"] = json.loads(payload_json) if payload_json else {}
            item["group_name"] = item["raw_result"].get("group_name")
            item["group_type"] = item["raw_result"].get("group_type")
            item["group_id"] = item["raw_result"].get("group_id")
            items.append(item)
        if shift in {"day", "night"}:
            items = [
                item
                for item in items
                if shift_for_iso(item.get("start_ts"), tz_name) == shift
            ]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def list_photos_paginated(
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
        tz_name: str = "UTC",
    ) -> dict[str, Any]:
        conditions = ["s.evidence_path IS NOT NULL", "s.evidence_path != ''"]
        params: list[Any] = []

        if date_from is not None:
            conditions.append("DATE(s.start_ts) >= DATE(?)")
            params.append(date_from)
        if date_to is not None:
            conditions.append("DATE(s.start_ts) <= DATE(?)")
            params.append(date_to)

        if days is not None and len(days) > 0:
            placeholders = ",".join("?" * len(days))
            conditions.append(
                f"CAST(STRFTIME('%w', s.start_ts) AS INTEGER) IN ({placeholders})"
            )
            params.extend(days)

        if time_from is not None and time_to is not None:
            conditions.append(
                "CAST(STRFTIME('%H', s.start_ts) AS INTEGER) BETWEEN ? AND ?"
            )
            params.append(time_from)
            params.append(time_to)

        if cameras is not None and len(cameras) > 0:
            placeholders = ",".join("?" * len(cameras))
            conditions.append(f"s.camera_id IN ({placeholders})")
            params.extend(cameras)

        if groups is not None and len(groups) > 0:
            placeholders = ",".join("?" * len(groups))
            conditions.append(
                f"EXISTS (SELECT 1 FROM camera_groups cg WHERE cg.camera_id = s.camera_id AND cg.group_id IN ({placeholders}))"
            )
            params.extend(groups)

        if labels is not None and len(labels) > 0:
            placeholders = ",".join("?" * len(labels))
            conditions.append(f"s.label IN ({placeholders})")
            params.extend(labels)

        where = " WHERE " + " AND ".join(conditions)
        offset = (max(page, 1) - 1) * page_size

        with self.connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM segments s{where}",
                params,
            ).fetchone()[0]

            rows = conn.execute(
                f"""SELECT s.id, s.camera_id, s.start_ts, s.end_ts, s.label, s.confidence, s.notes, s.evidence_path, s.reviewed_label,
                    c.name AS camera_name,
                    j.raw_result,
                    COALESCE(
                        (SELECT GROUP_CONCAT(g.name, ', ')
                         FROM groups g
                         JOIN camera_groups cg ON cg.group_id = g.id
                         WHERE cg.camera_id = s.camera_id), ''
                    ) AS group_names
                    FROM segments s
                    JOIN cameras c ON c.id = s.camera_id
                    LEFT JOIN jobs j ON j.id = s.job_id{where}
                    ORDER BY s.created_at DESC
                    LIMIT ? OFFSET ?""",
                (*params, page_size, offset),
            ).fetchall()

            items = []
            for row in rows:
                item = dict(row)
                raw_result = item.get("raw_result")
                item["raw_result"] = json.loads(raw_result) if raw_result else {}
                item["evidence_frames"] = item["raw_result"].get("evidence_frames", [])
                item["primary_evidence_path"] = item["raw_result"].get("primary_evidence_path")
                if item.get("start_ts") and item.get("end_ts"):
                    try:
                        start = datetime.fromisoformat(item["start_ts"])
                        end = datetime.fromisoformat(item["end_ts"])
                        item["duration_seconds"] = int((end - start).total_seconds())
                    except Exception:
                        item["duration_seconds"] = 0
                else:
                    item["duration_seconds"] = 0
                items.append(item)

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    def review_segment(
        self,
        segment_id: int,
        reviewed_label: str,
        review_note: str,
        review_by: str = "operator",
    ) -> dict[str, Any] | None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE segments SET reviewed_label=?, review_note=?, review_by=? WHERE id=?",
                (reviewed_label, review_note, review_by, segment_id),
            )
        return self.get_segment(segment_id)

    def update_daily_rollup(self, day: str, camera_id: int, label: str, seconds: int):
        col_map = {
            "working": "working_seconds",
            "not_working": "idle_seconds",
            "idle": "idle_seconds",
            "no_person": "stopped_seconds",
            "sleeping": "sleeping_seconds",
            "uncertain": "uncertain_seconds",
            "stopped": "stopped_seconds",
            "sleep-suspect": "sleeping_seconds",
        }
        column = col_map.get(label, "uncertain_seconds")
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO daily_rollups(day, camera_id) VALUES (?, ?)",
                (day, camera_id),
            )
            conn.execute(
                f"UPDATE daily_rollups SET {column} = {column} + ? WHERE day=? AND camera_id=?",
                (seconds, day, camera_id),
            )

    def chart_daily(self, days: int = 7) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT r.day,
                          SUM(r.working_seconds) AS working_seconds,
                          SUM(r.idle_seconds) AS idle_seconds,
                          SUM(r.sleeping_seconds) AS sleeping_seconds,
                          SUM(r.uncertain_seconds) AS uncertain_seconds,
                          SUM(r.stopped_seconds) AS stopped_seconds
                   FROM daily_rollups r
                   GROUP BY r.day
                   ORDER BY r.day DESC
                   LIMIT ?""",
                (days,),
            ).fetchall()
            return [dict(row) for row in rows][::-1]

    def chart_heatmap(self) -> dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT c.name AS camera_name,
                CAST(strftime('%H', datetime(s.start_ts, '+5 hours', '+30 minutes')) AS INTEGER) AS hour_bucket,
                COUNT(*) AS count
                FROM segments s JOIN cameras c ON c.id = s.camera_id
                GROUP BY c.name, hour_bucket
                ORDER BY c.name, hour_bucket"""
            ).fetchall()
            return {"rows": [dict(row) for row in rows]}

    def chart_heatmap_by_group(self) -> dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT g.group_type, g.name AS group_name,
                CAST(strftime('%H', datetime(s.start_ts, '+5 hours', '+30 minutes')) AS INTEGER) AS hour_bucket,
                COUNT(*) AS count
                FROM segments s
                JOIN camera_groups cg ON cg.camera_id = s.camera_id
                JOIN groups g ON g.id = cg.group_id
                GROUP BY g.group_type, g.name, hour_bucket
                ORDER BY g.group_type, g.name, hour_bucket"""
            ).fetchall()
            return {"rows": [dict(row) for row in rows]}

    def chart_shift_summary(self, tz_name: str = "UTC") -> dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT s.start_ts, s.label, s.confidence, c.name AS camera_name
                   FROM segments s JOIN cameras c ON c.id = s.camera_id"""
            ).fetchall()
        series = {"day": 0, "night": 0}
        for row in rows:
            shift = shift_for_iso(row["start_ts"], tz_name)
            series[shift] += 1
        return {"series": series}

    def chart_camera_summary(self) -> dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT c.name AS camera_name, s.label, COUNT(*) AS count
                   FROM segments s JOIN cameras c ON c.id = s.camera_id
                   GROUP BY c.name, s.label
                   ORDER BY c.name, s.label"""
            ).fetchall()
        return {"rows": [dict(row) for row in rows]}

    def chart_job_failures(self) -> dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT substr(COALESCE(j.finished_at, j.started_at, j.created_at), 1, 10) AS day,
                          COUNT(*) AS failures
                   FROM jobs j
                   WHERE j.status = 'failed'
                   GROUP BY substr(COALESCE(j.finished_at, j.started_at, j.created_at), 1, 10)
                   ORDER BY day"""
            ).fetchall()
        return {"rows": [dict(row) for row in rows]}

    def chart_confidence_distribution(self) -> dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT
                        CASE
                          WHEN confidence < 0.2 THEN '0.0-0.2'
                          WHEN confidence < 0.4 THEN '0.2-0.4'
                          WHEN confidence < 0.6 THEN '0.4-0.6'
                          WHEN confidence < 0.8 THEN '0.6-0.8'
                          ELSE '0.8-1.0'
                        END AS bucket,
                        COUNT(*) AS count
                   FROM segments
                   GROUP BY bucket
                   ORDER BY bucket"""
            ).fetchall()
        return {"rows": [dict(row) for row in rows]}

    def camera_health(self, camera_id: int) -> dict[str, Any] | None:
        camera = self.get_camera(camera_id)
        if not camera:
            return None
        return self._compute_health(camera)

    def all_cameras_health(self) -> list[dict[str, Any]]:
        cameras = self.list_cameras()
        return [self._compute_health(c) for c in cameras]

    def _compute_health(self, camera: dict[str, Any]) -> dict[str, Any]:
        last_run = camera.get("last_run_at")
        last_status = camera.get("last_status", "never")
        interval = camera.get("interval_seconds", 300)
        threshold = interval * 2
        if not last_run:
            status = "never"
        else:
            try:
                last_dt = datetime.fromisoformat(last_run)
                age = (datetime.now(timezone.utc) - last_dt).total_seconds()
                if age <= threshold and not (last_status or "").startswith("error"):
                    status = "online"
                else:
                    status = "offline"
            except Exception:
                status = "unknown"
        return {
            "camera_id": camera["id"],
            "name": camera["name"],
            "status": status,
            "last_run_at": last_run,
            "last_status": last_status,
        }

    def report_daily(self, day: str) -> dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT c.name AS camera_name, c.frigate_name,
                          r.working_seconds, r.idle_seconds, r.sleeping_seconds, r.uncertain_seconds, r.stopped_seconds
                   FROM daily_rollups r JOIN cameras c ON c.id = r.camera_id WHERE r.day=? ORDER BY c.id""",
                (day,),
            ).fetchall()
            segments = conn.execute(
                f"""SELECT s.*, c.name AS camera_name,
                          {MODEL_USED_SQL}
                   FROM segments s
                   JOIN cameras c ON c.id=s.camera_id
                   LEFT JOIN jobs j ON j.id = s.job_id
                   WHERE substr(s.start_ts,1,10)=? ORDER BY s.id DESC LIMIT 20""",
                (day,),
            ).fetchall()
        totals = {
            "working_seconds": 0,
            "idle_seconds": 0,
            "sleeping_seconds": 0,
            "uncertain_seconds": 0,
            "stopped_seconds": 0,
        }
        per_camera = []
        for row in rows:
            item = dict(row)
            per_camera.append(item)
            for k in totals:
                totals[k] += item[k]
        return {
            "day": day,
            "totals": totals,
            "per_camera": per_camera,
            "recent_segments": [dict(row) for row in segments],
        }

    def efficiency_heatmap_minute(
        self, date: str, camera_id: int | None = None
    ) -> dict[str, Any]:
        """Get per-minute efficiency data for a specific date (active cameras only)."""
        with self.connect() as conn:
            # Build query conditions - only include active cameras
            # Use timezone-converted date to match local day boundaries
            conditions = [
                "DATE(datetime(s.start_ts, '+5 hours', '+30 minutes')) = ?",
                "c.enabled = 1",
            ]
            params = [date]

            if camera_id is not None:
                conditions.append("s.camera_id = ?")
                params.append(camera_id)

            where_clause = " AND ".join(conditions)

            # Get segments with minute-level granularity
            # Convert UTC to local timezone for hour display
            rows = conn.execute(
                f"""SELECT
                s.id AS segment_id,
                c.name AS camera_name,
                c.id AS camera_id,
                strftime('%H', datetime(s.start_ts, '+5 hours', '+30 minutes')) AS hour,
                s.label,
                s.confidence,
                s.start_ts,
                s.end_ts,
                ROUND((julianday(s.end_ts) - julianday(s.start_ts)) * 24 * 60) AS duration_minutes
                FROM segments s
                JOIN cameras c ON c.id = s.camera_id
                WHERE {where_clause}
                ORDER BY c.name, s.start_ts""",
                params,
            ).fetchall()

            return {"rows": [dict(row) for row in rows], "date": date}

    def efficiency_summary(
        self, from_date: str, to_date: str, camera_id: int | None = None
    ) -> dict[str, Any]:
        """Get efficiency summary for a date range."""
        with self.connect() as conn:
            conditions = ["DATE(s.start_ts) >= ? AND DATE(s.start_ts) <= ?"]
            params = [from_date, to_date]

            if camera_id is not None:
                conditions.append("s.camera_id = ?")
                params.append(camera_id)

            where_clause = " AND ".join(conditions)

            # Overall summary
            summary = conn.execute(
                f"""SELECT 
                    COUNT(*) AS total_segments,
                    SUM(CASE WHEN s.label = 'working' THEN 1 ELSE 0 END) AS working_count,
                    SUM(CASE WHEN s.label = 'idle' THEN 1 ELSE 0 END) AS idle_count,
                    SUM(CASE WHEN s.label = 'stopped' THEN 1 ELSE 0 END) AS stopped_count,
                    SUM(CASE WHEN s.label = 'uncertain' THEN 1 ELSE 0 END) AS uncertain_count,
                    AVG(CASE WHEN s.label = 'working' THEN s.confidence ELSE NULL END) AS avg_working_confidence,
                    COUNT(DISTINCT s.camera_id) AS active_cameras,
                    ROUND(SUM(
                        CASE 
                            WHEN s.label = 'working' THEN (julianday(s.end_ts) - julianday(s.start_ts)) * 24 * 60
                            ELSE 0 
                        END
                    ), 2) AS total_working_minutes,
                    ROUND(SUM(
                        CASE 
                            WHEN s.label = 'idle' THEN (julianday(s.end_ts) - julianday(s.start_ts)) * 24 * 60
                            ELSE 0 
                        END
                    ), 2) AS total_idle_minutes
                FROM segments s
                WHERE {where_clause}""",
                params,
            ).fetchone()

            # Per-camera breakdown
            camera_breakdown = conn.execute(
                f"""SELECT 
                    c.name AS camera_name,
                    c.id AS camera_id,
                    COUNT(*) AS total_segments,
                    SUM(CASE WHEN s.label = 'working' THEN 1 ELSE 0 END) AS working_count,
                    SUM(CASE WHEN s.label = 'idle' THEN 1 ELSE 0 END) AS idle_count,
                    SUM(CASE WHEN s.label = 'stopped' THEN 1 ELSE 0 END) AS stopped_count,
                    ROUND(AVG(CASE WHEN s.label = 'working' THEN s.confidence ELSE NULL END) * 100, 1) AS efficiency_pct
                FROM segments s
                JOIN cameras c ON c.id = s.camera_id
                WHERE {where_clause}
                GROUP BY c.id, c.name
                ORDER BY efficiency_pct DESC""",
                params,
            ).fetchall()

            # Shift breakdown (day: 09:00-21:00, night: 21:00-09:00) in local timezone
            shift_data = conn.execute(
                f"""SELECT
                CASE
                WHEN CAST(strftime('%H', datetime(s.start_ts, '+5 hours', '+30 minutes')) AS INTEGER) BETWEEN 9 AND 20 THEN 'day'
                ELSE 'night'
                END AS shift,
                COUNT(*) AS total_segments,
                SUM(CASE WHEN s.label = 'working' THEN 1 ELSE 0 END) AS working_count,
                ROUND(AVG(CASE WHEN s.label = 'working' THEN s.confidence ELSE NULL END) * 100, 1) AS efficiency_pct
                FROM segments s
                WHERE {where_clause}
                GROUP BY shift""",
                params,
            ).fetchall()

            return {
                "summary": dict(summary) if summary else {},
                "camera_breakdown": [dict(row) for row in camera_breakdown],
                "shift_breakdown": [dict(row) for row in shift_data],
                "date_range": {"from": from_date, "to": to_date},
            }

    def efficiency_heatmap_daily(
        self, from_date: str, to_date: str, camera_id: int | None = None
    ) -> dict[str, Any]:
        """Get daily aggregated efficiency data for heatmap visualization."""
        with self.connect() as conn:
            conditions = ["DATE(s.start_ts) >= ? AND DATE(s.start_ts) <= ?"]
            params = [from_date, to_date]

            if camera_id is not None:
                conditions.append("s.camera_id = ?")
                params.append(camera_id)

            where_clause = " AND ".join(conditions)

            rows = conn.execute(
                f"""SELECT
                DATE(s.start_ts) AS date,
                c.name AS camera_name,
                c.id AS camera_id,
                strftime('%H', datetime(s.start_ts, '+5 hours', '+30 minutes')) AS hour,
                s.label,
                COUNT(*) AS count,
                ROUND(AVG(s.confidence) * 100, 1) AS avg_confidence,
                ROUND(SUM(
                (julianday(s.end_ts) - julianday(s.start_ts)) * 24 * 60
                ), 2) AS total_minutes
                FROM segments s
                JOIN cameras c ON c.id = s.camera_id
                WHERE {where_clause}
                GROUP BY date, c.id, hour, s.label
                ORDER BY date, c.name, hour""",
                params,
            ).fetchall()

            return {"rows": [dict(row) for row in rows]}

    def efficiency_timeline(
        self,
        date: str,
        camera_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Get timeline of activity for a specific date."""
        with self.connect() as conn:
            conditions = ["DATE(s.start_ts) = ?"]
            params = [date]

            if camera_id is not None:
                conditions.append("s.camera_id = ?")
                params.append(camera_id)

            where_clause = " AND ".join(conditions)
            offset = (page - 1) * page_size

            # Count total
            total = conn.execute(
                f"SELECT COUNT(*) FROM segments s WHERE {where_clause}", params
            ).fetchone()[0]

            # Get paginated results
            rows = conn.execute(
                f"""SELECT 
                    s.id,
                    s.start_ts,
                    s.end_ts,
                    s.label,
                    s.confidence,
                    ROUND((julianday(s.end_ts) - julianday(s.start_ts)) * 24 * 60, 1) AS duration_minutes,
                    c.name AS camera_name,
                    c.id AS camera_id
                FROM segments s
                JOIN cameras c ON c.id = s.camera_id
                WHERE {where_clause}
                ORDER BY s.start_ts DESC
                LIMIT ? OFFSET ?""",
                params + [page_size, offset],
            ).fetchall()

            return {
                "items": [dict(row) for row in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": max(1, (total + page_size - 1) // page_size),
            }

    def efficiency_heatmap_chart(
        self,
        from_date: str,
        to_date: str,
        view: str = "daily",
    ) -> dict[str, Any]:
        """Get heatmap chart data for enabled cameras in groups, formatted for ApexCharts."""
        with self.connect() as conn:
            # Get enabled cameras in groups
            group_cameras = conn.execute(
                """SELECT DISTINCT c.id, c.name, g.name AS group_name, g.id AS group_id
                   FROM cameras c
                   JOIN camera_groups cg ON cg.camera_id = c.id
                   JOIN groups g ON g.id = cg.group_id
                   WHERE c.enabled = 1
                   ORDER BY g.name, c.name"""
            ).fetchall()

            if not group_cameras:
                return {"series": [], "categories": [], "segments": {}}

            camera_ids = [row["id"] for row in group_cameras]
            camera_labels = {}
            for row in group_cameras:
                camera_labels[row["id"]] = f"{row['name']} ({row['group_name']})"

            if view == "daily":
                # Per-hour data for the given date
                placeholders = ",".join("?" * len(camera_ids))
                rows = conn.execute(
                    f"""SELECT s.camera_id,
                    strftime('%H', datetime(s.start_ts, '+5 hours', '+30 minutes')) AS hour,
                    s.label,
                    COUNT(*) AS count,
                    AVG(s.confidence) AS avg_confidence,
                    SUM(ROUND((julianday(s.end_ts) - julianday(s.start_ts)) * 24 * 60, 1)) AS total_minutes,
                    GROUP_CONCAT(s.id) AS segment_ids
                    FROM segments s
                    WHERE DATE(s.start_ts) = ?
                    AND s.camera_id IN ({placeholders})
                    GROUP BY s.camera_id, hour, s.label
                    ORDER BY s.camera_id, hour""",
                    [from_date] + camera_ids,
                ).fetchall()

                categories = [f"{h:02d}:00" for h in range(24)]
                # Build series data: per camera, per hour, with dominant label and score
                series_data = {}
                segment_refs = {}
                for cam_id in camera_ids:
                    label = camera_labels[cam_id]
                    series_data[label] = {
                        h: {
                            "score": 0,
                            "label": "stopped",
                            "confidence": 0,
                            "count": 0,
                            "minutes": 0,
                            "segment_ids": "",
                        }
                        for h in range(24)
                    }
                    segment_refs[label] = {h: [] for h in range(24)}

                label_scores = {
                    "working": 5,
                    "idle": 3,
                    "operator_missing": 2,
                    "stopped": 1,
                    "uncertain": 0,
                    "error": 0,
                }

                for row in rows:
                    cam_label = camera_labels[row["camera_id"]]
                    hour = int(row["hour"])
                    row_score = label_scores.get(row["label"], 0)
                    existing = series_data[cam_label][hour]
                    if row_score > existing["score"]:
                        series_data[cam_label][hour] = {
                            "score": row_score,
                            "label": row["label"],
                            "confidence": round((row["avg_confidence"] or 0) * 100, 1),
                            "count": row["count"],
                            "minutes": round(row["total_minutes"] or 0, 1),
                            "segment_ids": row["segment_ids"] or "",
                        }
                    segment_refs[cam_label][hour] = (
                        row["segment_ids"].split(",") if row["segment_ids"] else []
                    )

                series = []
                for cam_label, hours_data in series_data.items():
                    data_points = []
                    for h in range(24):
                        cell = hours_data[h]
                        data_points.append(
                            {
                                "x": categories[h],
                                "y": cell["score"],
                                "meta": {
                                    "label": cell["label"],
                                    "confidence": cell["confidence"],
                                    "count": cell["count"],
                                    "minutes": cell["minutes"],
                                    "segment_ids": segment_refs[cam_label][h],
                                    "camera": cam_label,
                                    "time": categories[h],
                                },
                            }
                        )
                    series.append({"name": cam_label, "data": data_points})

                return {
                    "series": series,
                    "categories": categories,
                    "shift_markers": [9, 21],
                }

            else:
                # Weekly or monthly: per-day data
                placeholders = ",".join("?" * len(camera_ids))
                rows = conn.execute(
                    f"""SELECT s.camera_id,
                               DATE(s.start_ts) AS date,
                               s.label,
                               COUNT(*) AS count,
                               AVG(s.confidence) AS avg_confidence,
                               SUM(ROUND((julianday(s.end_ts) - julianday(s.start_ts)) * 24 * 60, 1)) AS total_minutes,
                               GROUP_CONCAT(s.id) AS segment_ids
                        FROM segments s
                        WHERE DATE(s.start_ts) >= ? AND DATE(s.start_ts) <= ?
                          AND s.camera_id IN ({placeholders})
                        GROUP BY s.camera_id, date, s.label
                        ORDER BY s.camera_id, date""",
                    [from_date, to_date] + camera_ids,
                ).fetchall()

                # Build date range
                from datetime import datetime as dt, timedelta

                start = dt.strptime(from_date, "%Y-%m-%d")
                end = dt.strptime(to_date, "%Y-%m-%d")
                dates = []
                d = start
                while d <= end:
                    dates.append(d.strftime("%Y-%m-%d"))
                    d += timedelta(days=1)

                categories = [
                    dt.strptime(ds, "%Y-%m-%d").strftime("%b %d") for ds in dates
                ]

                label_scores = {
                    "working": 5,
                    "idle": 3,
                    "operator_missing": 2,
                    "stopped": 1,
                    "uncertain": 0,
                    "error": 0,
                }

                series_data = {}
                segment_refs = {}
                for cam_id in camera_ids:
                    label = camera_labels[cam_id]
                    series_data[label] = {
                        ds: {
                            "score": 0,
                            "label": "stopped",
                            "confidence": 0,
                            "count": 0,
                            "minutes": 0,
                            "segment_ids": "",
                        }
                        for ds in dates
                    }
                    segment_refs[label] = {ds: [] for ds in dates}

                for row in rows:
                    cam_label = camera_labels[row["camera_id"]]
                    date = row["date"]
                    if date not in series_data[cam_label]:
                        continue
                    row_score = label_scores.get(row["label"], 0)
                    existing = series_data[cam_label][date]
                    if row_score > existing["score"]:
                        series_data[cam_label][date] = {
                            "score": row_score,
                            "label": row["label"],
                            "confidence": round((row["avg_confidence"] or 0) * 100, 1),
                            "count": row["count"],
                            "minutes": round(row["total_minutes"] or 0, 1),
                            "segment_ids": row["segment_ids"] or "",
                        }
                    segment_refs[cam_label][date] = (
                        row["segment_ids"].split(",") if row["segment_ids"] else []
                    )

                series = []
                for cam_label, dates_data in series_data.items():
                    data_points = []
                    for ds in dates:
                        cell = dates_data[ds]
                        cat_label = dt.strptime(ds, "%Y-%m-%d").strftime("%b %d")
                        data_points.append(
                            {
                                "x": cat_label,
                                "y": cell["score"],
                                "meta": {
                                    "label": cell["label"],
                                    "confidence": cell["confidence"],
                                    "count": cell["count"],
                                    "minutes": cell["minutes"],
                                    "segment_ids": segment_refs[cam_label][ds],
                                    "camera": cam_label,
                                    "time": ds,
                                },
                            }
                        )
                    series.append({"name": cam_label, "data": data_points})

                return {"series": series, "categories": categories, "shift_markers": []}

    def cancel_all_pending_and_running(self) -> dict[str, Any]:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE jobs SET status='cancelled', error='Cancelled by user', finished_at=? WHERE status IN ('pending', 'running')",
                (utcnow(),),
            )
            return {"ok": True, "cancelled": cur.rowcount}

    def expire_timed_out_jobs(self, timeout_seconds: int) -> int:
        """Cancel running jobs that have been running longer than timeout_seconds.

        Returns number of expired jobs cancelled.
        """
        with self.connect() as conn:
            cur = conn.execute(
                """UPDATE jobs 
                   SET status='cancelled', 
                       error='Timed out (exceeded ' || ? || 's)', 
                       finished_at=? 
                   WHERE status='running' 
                     AND started_at IS NOT NULL 
                     AND (julianday(?) - julianday(started_at)) * 86400 > ?""",
                (
                    timeout_seconds,
                    utcnow(),
                    utcnow(),
                    timeout_seconds,
                ),
            )
            expired = cur.rowcount
        if expired:
            logger.info(
                "Expired %d timed-out job(s) (timeout=%ds)", expired, timeout_seconds
            )
        return expired

    def job_stats(self) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                """SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS running,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled
                FROM jobs"""
            ).fetchone()
            if not row:
                return {
                    "total": 0,
                    "pending": 0,
                    "running": 0,
                    "success": 0,
                    "failed": 0,
                    "cancelled": 0,
                }
            return {
                "total": row["total"] or 0,
                "pending": row["pending"] or 0,
                "running": row["running"] or 0,
                "success": row["success"] or 0,
                "failed": row["failed"] or 0,
                "cancelled": row["cancelled"] or 0,
            }

    def get_expired_evidence_paths(self, retention_days: int) -> list[str]:
        """Get evidence paths for segments older than retention_days.

        Returns list of evidence_path values that should be cleaned up.
        Does NOT delete from DB - only returns paths for file cleanup.
        """
        cutoff = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - __import__("datetime").timedelta(days=retention_days)
        cutoff_str = cutoff.isoformat()

        with self.connect() as conn:
            rows = conn.execute(
                """SELECT DISTINCT evidence_path
                FROM segments
                WHERE evidence_path IS NOT NULL
                AND evidence_path != ''
                AND created_at < ?""",
                (cutoff_str,),
            ).fetchall()
            return [row["evidence_path"] for row in rows]

    def clear_segment_evidence_refs(self, retention_days: int) -> int:
        """Clear evidence_path references for old segments.

        Sets evidence_path to NULL for segments older than retention_days.
        Returns count of updated rows.
        """
        cutoff = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - __import__("datetime").timedelta(days=retention_days)
        cutoff_str = cutoff.isoformat()

        with self.connect() as conn:
            cur = conn.execute(
                """UPDATE segments
                SET evidence_path = NULL
                WHERE evidence_path IS NOT NULL
                AND evidence_path != ''
                AND created_at < ?""",
                (cutoff_str,),
            )
            return cur.rowcount
