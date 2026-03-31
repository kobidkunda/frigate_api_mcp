from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from factory_analytics.config import MCP_TOKEN, LOG_ROOT
from factory_analytics.database import Database
from factory_analytics.services import AnalyticsService

app = FastAPI(title="Factory Analytics MCP Bridge", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

db = Database()
service = AnalyticsService(db)


class MCPRequest(BaseModel):
    method: str
    params: dict = {}
    id: str | int | None = None


def authorize(auth_header: str | None):
    if not MCP_TOKEN:
        return
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    if token != MCP_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


from datetime import datetime, timezone
import json

TOOLS = {
    # System & Health
    "system_health": {"description": "Get app, Frigate, Ollama, and DB health"},
    "system_status": {
        "description": "Get system status with camera, job, and segment counts"
    },
    "frigate_health": {"description": "Get Frigate health"},
    "ollama_health": {"description": "Get Ollama health"},
    # Cameras
    "camera_list": {"description": "List configured cameras"},
    "camera_status": {"description": "Get one camera by id; param: camera_id"},
    "camera_create": {
        "description": "Create a camera; params: frigate_name, name, enabled, interval_seconds"
    },
    "camera_update": {
        "description": "Update a camera; params: camera_id, name, enabled, kind, interval_seconds"
    },
    "camera_delete": {"description": "Delete a camera; param: camera_id"},
    "camera_test": {"description": "Test a camera; param: camera_id or frigate_name"},
    "camera_health": {"description": "Get camera health; param: camera_id"},
    "all_cameras_health": {"description": "Get health for all cameras"},
    # Groups
    "group_list": {"description": "List all groups"},
    "group_get": {"description": "Get one group; param: group_id"},
    "group_create": {
        "description": "Create a group; params: group_type, name, interval_seconds"
    },
    "group_update": {
        "description": "Update a group; params: group_id, group_type, name, interval_seconds"
    },
    "group_delete": {"description": "Delete a group; param: group_id"},
    "group_add_camera": {
        "description": "Add camera to group; params: group_id, camera_id"
    },
    "group_remove_camera": {
        "description": "Remove camera from group; params: group_id, camera_id"
    },
    "group_list_cameras": {"description": "List cameras in a group; param: group_id"},
    "camera_groups": {"description": "List groups for a camera; param: camera_id"},
    "group_run_analysis": {"description": "Run analysis for a group; param: group_id"},
    # Jobs
    "run_list": {"description": "List jobs"},
    "run_get": {"description": "Get one job; param: job_id"},
    "run_analysis_now": {
        "description": "Queue analysis for a camera; param: camera_id"
    },
    "run_backfill": {
        "description": "Queue a backfill job; params: camera_id, start_ts, end_ts"
    },
    "job_cancel": {"description": "Cancel a job; param: job_id"},
    "job_retry": {"description": "Retry a failed job; param: job_id"},
    "jobs_bulk_cancel": {"description": "Bulk cancel jobs; param: job_ids (list)"},
    "jobs_cancel_all": {"description": "Cancel all pending/running jobs"},
    "job_stats": {"description": "Get job statistics"},
    # History/Segments
    "history_search": {"description": "List recent segments"},
    "segment_get": {"description": "Get one segment; param: segment_id"},
    "review_segment": {
        "description": "Review/override one segment; params: segment_id, reviewed_label, review_note, review_by"
    },
    # Charts
    "chart_daily": {"description": "Get daily rollup chart; param: days"},
    "chart_heatmap": {"description": "Get activity heatmap"},
    "chart_heatmap_by_group": {"description": "Get activity heatmap by group"},
    "chart_shift_summary": {"description": "Get shift summary"},
    "chart_camera_summary": {"description": "Get camera summary"},
    "chart_job_failures": {"description": "Get job failure statistics"},
    "chart_confidence_distribution": {"description": "Get confidence distribution"},
    # Reports
    "report_get_daily": {"description": "Get daily report; param: day"},
    # Settings
    "settings_get": {"description": "Get application settings"},
    "settings_update": {"description": "Update application settings; param: values"},
    "ollama_test": {"description": "Test Ollama settings and vision"},
    # Frigate
    "frigate_sync_cameras": {"description": "Sync cameras from Frigate"},
    "frigate_list_cameras": {"description": "List cameras from Frigate"},
    # Scheduler
    "scheduler_reset": {
        "description": "Reset scheduler - cameras will be scheduled fresh"
    },
    # Logs
    "logs_tail": {
        "description": "Get recent log lines; params: name (api/mcp/worker), lines"
    },
}


@app.get("/mcp/tools")
def tools(authorization: str | None = Header(default=None)):
    authorize(authorization)
    return TOOLS


@app.post("/mcp")
def call(req: MCPRequest, authorization: str | None = Header(default=None)):
    authorize(authorization)
    method = req.method
    params = req.params or {}
    if method == "ping":
        result = {"ok": True}
    elif method == "tools/list":
        result = TOOLS
    elif method == "tools/call":
        result = dispatch(params.get("name"), params.get("arguments", {}))
    else:
        result = dispatch(method, params)
    return {"jsonrpc": "2.0", "id": req.id, "result": result}


@app.get("/health")
def health():
    return {"ok": True}


def dispatch(name: str, args: dict):
    # System & Health
    if name == "system_health":
        return service.system_health()
    if name == "system_status":
        return {
            "now_utc": datetime.now(timezone.utc).isoformat(),
            "settings": service.settings(),
            "camera_count": len(service.list_cameras()),
            "job_count": len(service.jobs()),
            "segment_count": len(service.segments()),
        }
    if name == "frigate_health":
        return service.frigate_client().health()
    if name == "ollama_health":
        return service.ollama_client().health()

    # Cameras
    if name == "camera_list":
        return service.list_cameras()
    if name == "camera_status":
        camera = service.db.get_camera(int(args["camera_id"]))
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        return camera
    if name == "camera_create":
        return service.create_camera(
            frigate_name=args["frigate_name"],
            name=args.get("name"),
            enabled=args.get("enabled"),
            interval_seconds=args.get("interval_seconds"),
        )
    if name == "camera_update":
        camera = service.update_camera(
            int(args["camera_id"]),
            {k: v for k, v in args.items() if k != "camera_id" and v is not None},
        )
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        return camera
    if name == "camera_delete":
        return service.delete_camera(int(args["camera_id"]))
    if name == "camera_test":
        return service.probe_analysis(
            camera_id=args.get("camera_id"), frigate_name=args.get("frigate_name")
        )
    if name == "camera_health":
        result = service.camera_health(int(args["camera_id"]))
        if not result:
            raise HTTPException(status_code=404, detail="Camera not found")
        return result
    if name == "all_cameras_health":
        return service.all_cameras_health()

    # Groups
    if name == "group_list":
        return service.list_groups()
    if name == "group_get":
        group = service.db.get_group(int(args["group_id"]))
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        return group
    if name == "group_create":
        return service.create_group(
            group_type=args["group_type"],
            name=args["name"],
            interval_seconds=args.get("interval_seconds", 300),
        )
    if name == "group_update":
        group = service.update_group(
            int(args["group_id"]),
            group_type=args.get("group_type"),
            name=args.get("name"),
            interval_seconds=args.get("interval_seconds"),
        )
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        return group
    if name == "group_delete":
        return service.delete_group(int(args["group_id"]))
    if name == "group_add_camera":
        result = service.add_camera_to_group(
            int(args["group_id"]), int(args["camera_id"])
        )
        if not result:
            raise HTTPException(status_code=404, detail="Group or camera not found")
        return result
    if name == "group_remove_camera":
        return service.remove_camera_from_group(
            int(args["group_id"]), int(args["camera_id"])
        )
    if name == "group_list_cameras":
        return service.group_cameras(int(args["group_id"]))
    if name == "camera_groups":
        return service.camera_groups(int(args["camera_id"]))
    if name == "group_run_analysis":
        try:
            return service.queue_group_analysis(int(args["group_id"]))
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    # Jobs
    if name == "run_list":
        return service.jobs()
    if name == "run_get":
        job = service.job(int(args["job_id"]))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    if name == "run_analysis_now":
        return service.queue_analysis(int(args["camera_id"]), {"source": "mcp"})
    if name == "run_backfill":
        return service.queue_analysis(int(args["camera_id"]), args)
    if name == "job_cancel":
        job = service.job(int(args["job_id"]))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.get("status") not in ("pending", "running"):
            raise HTTPException(
                status_code=400, detail="Only pending or running jobs can be cancelled"
            )
        db.mark_job_finished(
            int(args["job_id"]), "cancelled", error="Cancelled via MCP"
        )
        db.log_audit("mcp", "job.cancel", "job", str(args["job_id"]))
        return {"ok": True, "job_id": int(args["job_id"]), "status": "cancelled"}
    if name == "job_retry":
        job = service.job(int(args["job_id"]))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.get("status") != "failed":
            raise HTTPException(
                status_code=409, detail="Only failed jobs can be retried"
            )
        payload = json.loads(job.get("payload_json") or "{}")
        payload["retry_of"] = int(args["job_id"])
        new_job = service.queue_analysis(job["camera_id"], payload)
        db.log_audit(
            "mcp",
            "job.retry",
            "job",
            str(args["job_id"]),
            {"new_job_id": new_job.get("id")},
        )
        return new_job
    if name == "jobs_bulk_cancel":
        cancelled = 0
        for job_id in args.get("job_ids", []):
            job = service.job(job_id)
            if job and job.get("status") in ("pending", "running"):
                db.mark_job_finished(
                    job_id, "cancelled", error="Bulk cancelled via MCP"
                )
                cancelled += 1
        db.log_audit("mcp", "job.bulk_cancel", "job", None, {"cancelled": cancelled})
        return {"ok": True, "cancelled": cancelled}
    if name == "jobs_cancel_all":
        result = db.cancel_all_pending_and_running()
        db.log_audit(
            "mcp",
            "job.cancel_all",
            "job",
            None,
            {"cancelled": result.get("cancelled", 0)},
        )
        return result
    if name == "job_stats":
        return db.job_stats()

    # History/Segments
    if name == "history_search":
        return service.segments()
    if name == "segment_get":
        segment = service.segment(int(args["segment_id"]))
        if not segment:
            raise HTTPException(status_code=404, detail="Segment not found")
        return segment
    if name == "review_segment":
        return service.review_segment(
            int(args["segment_id"]),
            args["reviewed_label"],
            args.get("review_note", ""),
            args.get("review_by", "mcp"),
        )

    # Charts
    if name == "chart_daily":
        return service.chart_daily(int(args.get("days", 7)))
    if name == "chart_heatmap":
        return service.chart_heatmap()
    if name == "chart_heatmap_by_group":
        return service.chart_heatmap_by_group()
    if name == "chart_shift_summary":
        return service.chart_shift_summary()
    if name == "chart_camera_summary":
        return service.chart_camera_summary()
    if name == "chart_job_failures":
        return service.chart_job_failures()
    if name == "chart_confidence_distribution":
        return service.chart_confidence_distribution()

    # Reports
    if name == "report_get_daily":
        return service.report_daily(args.get("day"))

    # Settings
    if name == "settings_get":
        return service.settings()
    if name == "settings_update":
        return service.update_settings(args.get("values", {}), actor="mcp")
    if name == "ollama_test":
        return service.test_ollama_vision()

    # Frigate
    if name == "frigate_sync_cameras":
        return service.sync_cameras_from_frigate()
    if name == "frigate_list_cameras":
        return {"cameras": service.frigate_client().fetch_cameras()}

    # Scheduler
    if name == "scheduler_reset":
        db.reset_all_camera_last_run()
        db.log_audit("mcp", "scheduler.reset", "scheduler", None)
        return {
            "ok": True,
            "message": "Scheduler reset, cameras will be scheduled fresh",
        }

    # Logs
    if name == "logs_tail":
        log_name = args.get("name", "api")
        lines = int(args.get("lines", 200))
        mapping = {
            "api": LOG_ROOT / "api.log",
            "mcp": LOG_ROOT / "mcp.log",
            "worker": LOG_ROOT / "worker.log",
        }
        path = mapping.get(log_name)
        if not path:
            raise HTTPException(status_code=404, detail="Unknown log")
        if not path.exists():
            return {"name": log_name, "content": ""}
        content = path.read_text(encoding="utf-8", errors="ignore").splitlines()[
            -lines:
        ]
        return {"name": log_name, "lines": len(content), "content": "\n".join(content)}

    raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")
