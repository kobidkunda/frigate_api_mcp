from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from factory_analytics.config import BASE_DIR, LOG_ROOT
from factory_analytics.control_center import (
    build_api_catalog,
    get_config_file_inventory,
    get_platform_install_instructions,
    get_skill_inventory,
)
from factory_analytics.database import Database
from factory_analytics.services import AnalyticsService
from factory_analytics.worker import WorkerLoop

app = FastAPI(title="Factory Analytics App", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "factory_analytics" / "static")),
    name="static",
)
templates = Jinja2Templates(directory=str(BASE_DIR / "factory_analytics" / "templates"))

db = Database()
service = AnalyticsService(db)
worker = WorkerLoop(db)


class SettingsUpdate(BaseModel):
    values: dict


class CameraUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    kind: str | None = None
    interval_seconds: int | None = None


class ReviewPayload(BaseModel):
    reviewed_label: str
    review_note: str = ""
    review_by: str = "operator"


class BackfillPayload(BaseModel):
    camera_id: int
    start_ts: str
    end_ts: str


class CameraCreate(BaseModel):
    frigate_name: str
    name: str | None = None
    enabled: bool | None = None
    interval_seconds: int | None = None


class CameraTestPayload(BaseModel):
    camera_id: int | None = None
    frigate_name: str | None = None


class GroupCreate(BaseModel):
    group_type: str
    name: str
    interval_seconds: int | None = 300


class GroupUpdate(BaseModel):
    group_type: str | None = None
    name: str | None = None
    interval_seconds: int | None = None


class GroupCameraPayload(BaseModel):
    camera_id: int


@app.on_event("startup")
def startup_event():
    worker.start()


@app.on_event("shutdown")
def shutdown_event():
    worker.stop()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/favicon.ico")
def favicon():
    icon_path = BASE_DIR / "factory_analytics" / "static" / "favicon.ico"
    if icon_path.exists():
        return FileResponse(icon_path)
    raise HTTPException(status_code=404, detail="File not found")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})


@app.get("/groups", response_class=HTMLResponse)
def groups_page(request: Request):
    return templates.TemplateResponse("groups.html", {"request": request})


@app.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request):
    return templates.TemplateResponse("logs.html", {"request": request})


@app.get("/control-center", response_class=HTMLResponse)
def control_center_page(request: Request):
    return templates.TemplateResponse("control_center.html", {"request": request})


@app.get("/api-explorer", response_class=HTMLResponse)
def api_explorer_page(request: Request):
    return templates.TemplateResponse("api_explorer.html", {"request": request})


@app.get("/processed-events", response_class=HTMLResponse)
def processed_events_page(request: Request):
    return templates.TemplateResponse("processed_events.html", {"request": request})


@app.get("/charts", response_class=HTMLResponse)
def charts_page(request: Request):
    return templates.TemplateResponse("charts.html", {"request": request})


@app.get("/api/health")
def api_health():
    return service.system_health()


@app.get("/api/health/frigate")
def frigate_health():
    return service.frigate_client().health()


@app.get("/api/health/ollama")
def ollama_health():
    return service.ollama_client().health()


@app.get("/api/system/status")
def system_status():
    return {
        "now_utc": datetime.now(timezone.utc).isoformat(),
        "settings": service.settings(),
        "camera_count": len(service.list_cameras()),
        "job_count": len(service.jobs()),
        "segment_count": len(service.segments()),
    }


@app.get("/api/control-center/config")
def control_center_config():
    return {
        "config_files": get_config_file_inventory(),
        "skills": get_skill_inventory(),
        "platform_instructions": get_platform_install_instructions(),
    }


@app.get("/api/api-explorer/catalog")
def api_explorer_catalog():
    return build_api_catalog(app)


@app.get("/api/settings")
def get_settings():
    return service.settings()


@app.put("/api/settings")
def put_settings(payload: SettingsUpdate):
    return service.update_settings(payload.values)


@app.post("/api/settings/ollama/test")
def test_ollama_settings():
    result = service.test_ollama_vision()
    return result


@app.get("/api/frigate/cameras/sync")
def sync_cameras():
    return service.sync_cameras_from_frigate()


@app.get("/api/frigate/cameras")
def frigate_cameras():
    return {"cameras": service.frigate_client().fetch_cameras()}


@app.get("/api/cameras")
def list_cameras():
    return service.list_cameras()


@app.get("/api/cameras/{camera_id}")
def get_camera(camera_id: int):
    camera = service.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@app.get("/api/groups")
def list_groups():
    return service.list_groups()


@app.post("/api/groups")
def create_group(payload: GroupCreate):
    return service.create_group(
        payload.group_type, payload.name, payload.interval_seconds
    )


@app.put("/api/groups/{group_id}")
def update_group(group_id: int, payload: GroupUpdate):
    group = service.update_group(
        group_id, payload.group_type, payload.name, payload.interval_seconds
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@app.delete("/api/groups/{group_id}")
def delete_group(group_id: int):
    return service.delete_group(group_id)


@app.post("/api/groups/{group_id}/cameras")
def add_camera_to_group(group_id: int, payload: GroupCameraPayload):
    result = service.add_camera_to_group(group_id, payload.camera_id)
    if not result:
        raise HTTPException(status_code=404, detail="Group or camera not found")
    return result


@app.delete("/api/groups/{group_id}/cameras/{camera_id}")
def remove_camera_from_group(group_id: int, camera_id: int):
    return service.remove_camera_from_group(group_id, camera_id)


@app.get("/api/cameras/{camera_id}/groups")
def list_camera_groups(camera_id: int):
    return service.camera_groups(camera_id)


@app.get("/api/groups/{group_id}/cameras")
def list_group_cameras(group_id: int):
    return service.group_cameras(group_id)


@app.post("/api/groups/{group_id}/run")
def run_group_analysis(group_id: int):
    try:
        return service.queue_group_analysis(group_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/cameras")
def create_camera(payload: CameraCreate):
    return service.create_camera(
        payload.frigate_name,
        name=payload.name,
        enabled=payload.enabled,
        interval_seconds=payload.interval_seconds,
    )


@app.put("/api/cameras/{camera_id}")
def update_camera(camera_id: int, payload: CameraUpdate):
    camera = service.update_camera(camera_id, payload.model_dump(exclude_none=True))
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@app.get("/api/cameras/health")
def all_cameras_health():
    return service.all_cameras_health()


@app.get("/api/cameras/{camera_id}/health")
def camera_health(camera_id: int):
    result = service.camera_health(camera_id)
    if not result:
        raise HTTPException(status_code=404, detail="Camera not found")
    return result


@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: int):
    job = service.job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "failed":
        raise HTTPException(status_code=409, detail="Only failed jobs can be retried")
    payload = json.loads(job.get("payload_json") or "{}")
    payload["retry_of"] = job_id
    new_job = service.queue_analysis(job["camera_id"], payload)
    db.log_audit(
        "api",
        "job.retry",
        "job",
        str(job_id),
        {"new_job_id": new_job.get("id") if isinstance(new_job, dict) else None},
    )
    return new_job


@app.post("/api/cameras/{camera_id}/run")
def run_camera(camera_id: int):
    return service.queue_analysis(camera_id, {"source": "manual"})


@app.post("/api/cameras/test")
def test_camera(payload: CameraTestPayload):
    if (payload.camera_id is None) == (payload.frigate_name is None):
        raise HTTPException(
            status_code=400, detail="Provide exactly one of camera_id or frigate_name"
        )
    return service.probe_analysis(
        camera_id=payload.camera_id, frigate_name=payload.frigate_name
    )


@app.delete("/api/cameras/{camera_id}")
def delete_camera(camera_id: int):
    result = service.delete_camera(camera_id)
    return result


@app.post("/api/cameras/{camera_id}/delete")
def delete_camera_post(camera_id: int):
    # Fallback for environments where DELETE is blocked by a proxy
    result = service.delete_camera(camera_id)
    return result


@app.post("/api/cameras/delete_by_name")
def delete_camera_by_name(payload: dict):
    name = (payload or {}).get("frigate_name")
    if not name:
        raise HTTPException(status_code=400, detail="frigate_name required")
    return service.delete_camera_by_name(name)


@app.post("/api/jobs/backfill")
def backfill(payload: BackfillPayload):
    return service.queue_analysis(payload.camera_id, payload.model_dump())


@app.get("/api/jobs")
def list_jobs(status: str | None = None, camera_id: int | None = None):
    return service.jobs(status=status, camera_id=camera_id)


@app.get("/api/processed-events/jobs")
def processed_jobs(
    page: int = 1,
    page_size: int = 25,
    status: str | None = None,
    camera_id: int | None = None,
    group_id: int | None = None,
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
    shift: str | None = None,
    sort_by: str = "time",
    sort_dir: str = "desc",
):
    return service.jobs_paginated(
        page,
        page_size,
        status,
        camera_id,
        group_id,
        from_ts,
        to_ts,
        shift,
        sort_by,
        sort_dir,
    )


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int):
    job = service.job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/history/segments")
def list_segments(
    camera_id: int | None = None,
    label: str | None = None,
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
    min_confidence: float | None = None,
):
    return service.segments(
        camera_id=camera_id,
        label=label,
        from_ts=from_ts,
        to_ts=to_ts,
        min_confidence=min_confidence,
    )


@app.get("/api/processed-events/segments")
def processed_segments(
    page: int = 1,
    page_size: int = 25,
    camera_id: int | None = None,
    group_id: int | None = None,
    label: str | None = None,
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
    shift: str | None = None,
    sort_by: str = "time",
    sort_dir: str = "desc",
):
    return service.segments_paginated(
        page,
        page_size,
        camera_id,
        group_id,
        label,
        from_ts,
        to_ts,
        shift,
        sort_by,
        sort_dir,
    )


@app.get("/api/history/segments/{segment_id}")
def get_segment(segment_id: int):
    segment = service.segment(segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


@app.post("/api/review/{segment_id}")
def review_segment(segment_id: int, payload: ReviewPayload):
    segment = service.review_segment(
        segment_id, payload.reviewed_label, payload.review_note, payload.review_by
    )
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


@app.get("/api/charts/daily")
def chart_daily(days: int = 7):
    return service.chart_daily(days)


@app.get("/api/charts/heatmap")
def chart_heatmap():
    return service.chart_heatmap()


@app.get("/api/charts/heatmap-by-group")
def chart_heatmap_by_group():
    return service.chart_heatmap_by_group()


@app.get("/api/charts/shift-summary")
def chart_shift_summary():
    return service.chart_shift_summary()


@app.get("/api/charts/camera-summary")
def chart_camera_summary():
    return service.chart_camera_summary()


@app.get("/api/charts/job-failures")
def chart_job_failures():
    return service.chart_job_failures()


@app.get("/api/charts/confidence-distribution")
def chart_confidence_distribution():
    return service.chart_confidence_distribution()


@app.get("/api/reports/daily")
def report_daily(day: str | None = None):
    return service.report_daily(day)


@app.get("/api/logs/tail")
def logs_tail(name: str = "api", lines: int = 200):
    mapping = {
        "api": LOG_ROOT / "api.log",
        "mcp": LOG_ROOT / "mcp.log",
        "worker": LOG_ROOT / "worker.log",
    }
    path = mapping.get(name)
    if not path:
        raise HTTPException(status_code=404, detail="Unknown log")
    if not path.exists():
        return {"name": name, "content": ""}
    content = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-lines:]
    return {"name": name, "lines": len(content), "content": "\n".join(content)}


@app.get("/api/evidence/{segment_id}")
def evidence(segment_id: int):
    segment = service.segment(segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return {"segment_id": segment_id, "evidence_path": segment.get("evidence_path")}


@app.get("/{file_path:path}")
def get_file(file_path: str):
    # Allow only evidence files under data/evidence, everything else forbidden
    evidence_root = (BASE_DIR / "data" / "evidence").resolve()
    if file_path.startswith("data/evidence/"):
        path = BASE_DIR / file_path
        resolved = path.resolve()
        if not str(resolved).startswith(str(evidence_root)):
            raise HTTPException(status_code=403, detail="Forbidden")
        if resolved.exists() and resolved.is_file():
            return FileResponse(resolved)
        raise HTTPException(status_code=404, detail="File not found")
    raise HTTPException(status_code=403, detail="Forbidden")
