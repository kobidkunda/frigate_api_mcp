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


@app.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request):
    return templates.TemplateResponse("logs.html", {"request": request})


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


@app.get("/api/settings")
def get_settings():
    return service.settings()


@app.put("/api/settings")
def put_settings(payload: SettingsUpdate):
    return service.update_settings(payload.values)


@app.get("/api/frigate/cameras/sync")
def sync_cameras():
    return service.sync_cameras_from_frigate()


@app.get("/api/frigate/cameras")
def frigate_cameras():
    return {"cameras": service.frigate_client().fetch_cameras()}


@app.get("/api/cameras")
def list_cameras():
    return service.list_cameras()


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


@app.post("/api/jobs/backfill")
def backfill(payload: BackfillPayload):
    return service.queue_analysis(payload.camera_id, payload.model_dump())


@app.get("/api/jobs")
def list_jobs(status: str | None = None, camera_id: int | None = None):
    return service.jobs(status=status, camera_id=camera_id)


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
