from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from factory_analytics.config import (
    SQLITE_PATH,
    ANALYSIS_INTERVAL_SECONDS,
    TIMEZONE,
    FRIGATE_URL,
    OLLAMA_URL,
    OLLAMA_VISION_MODEL,
    SCHEDULER_ENABLED,
    PUBLIC_BASE_URL,
)

DEFAULT_SETTINGS = {
    "timezone": TIMEZONE,
    "frigate_url": FRIGATE_URL,
    "frigate_auth_mode": "none",
    "frigate_username": "",
    "frigate_password": "",
    "frigate_bearer_token": "",
    "frigate_verify_tls": False,
    "ollama_url": OLLAMA_URL,
    "ollama_vision_model": OLLAMA_VISION_MODEL,
    "ollama_timeout_sec": 120,
    "ollama_keep_alive": "5m",
    "ollama_enabled": True,
    "ollama_fallback_to_vision": True,
    "analysis_interval_seconds": ANALYSIS_INTERVAL_SECONDS,
    "scheduler_enabled": SCHEDULER_ENABLED,
    "public_base_url": PUBLIC_BASE_URL,
    "host_bind": "0.0.0.0",
    "frigate_snapshot_timeout_sec": 30,
}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            existing = {
                row["key"]
                for row in conn.execute("SELECT key FROM settings").fetchall()
            }
            now = utcnow()
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

    def next_pending_job(self) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                'SELECT * FROM jobs WHERE status="pending" ORDER BY id LIMIT 1'
            ).fetchone()
            return dict(row) if row else None

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
                """SELECT s.*, c.name AS camera_name, c.frigate_name AS camera_frigate_name
                   FROM segments s JOIN cameras c ON c.id = s.camera_id WHERE s.id=?""",
                (segment_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_segments(
        self,
        limit: int = 200,
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
                f"""SELECT s.*, c.name AS camera_name, c.frigate_name AS camera_frigate_name
                   FROM segments s JOIN cameras c ON c.id = s.camera_id{where} ORDER BY s.id DESC LIMIT ?""",
                (*params, limit),
            ).fetchall()
            return [dict(row) for row in rows]

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
            "idle": "idle_seconds",
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
                """SELECT s.*, c.name AS camera_name FROM segments s JOIN cameras c ON c.id=s.camera_id
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
