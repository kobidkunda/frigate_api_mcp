from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from factory_analytics.config import BASE_DIR, LOG_ROOT
from factory_analytics.database import Database
from factory_analytics.services import AnalyticsService
from factory_analytics.worker import WorkerLoop

app = FastAPI(title='Factory Analytics App', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
app.mount('/static', StaticFiles(directory=str(BASE_DIR / 'factory_analytics' / 'static')), name='static')
templates = Jinja2Templates(directory=str(BASE_DIR / 'factory_analytics' / 'templates'))

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
    review_note: str = ''
    review_by: str = 'operator'


class BackfillPayload(BaseModel):
    camera_id: int
    start_ts: str
    end_ts: str


@app.on_event('startup')
def startup_event():
    worker.start()


@app.on_event('shutdown')
def shutdown_event():
    worker.stop()


@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.get('/api/health')
def api_health():
    return service.system_health()


@app.get('/api/health/frigate')
def frigate_health():
    return service.frigate_client().health()


@app.get('/api/health/ollama')
def ollama_health():
    return service.ollama_client().health()


@app.get('/api/system/status')
def system_status():
    return {'now_utc': datetime.now(timezone.utc).isoformat(), 'settings': service.settings(), 'camera_count': len(service.list_cameras()), 'job_count': len(service.jobs()), 'segment_count': len(service.segments())}


@app.get('/api/settings')
def get_settings():
    return service.settings()


@app.put('/api/settings')
def put_settings(payload: SettingsUpdate):
    return service.update_settings(payload.values)


@app.get('/api/frigate/cameras/sync')
def sync_cameras():
    return service.sync_cameras_from_frigate()


@app.get('/api/cameras')
def list_cameras():
    return service.list_cameras()


@app.put('/api/cameras/{camera_id}')
def update_camera(camera_id: int, payload: CameraUpdate):
    camera = service.update_camera(camera_id, payload.model_dump(exclude_none=True))
    if not camera:
        raise HTTPException(status_code=404, detail='Camera not found')
    return camera


@app.post('/api/cameras/{camera_id}/run')
def run_camera(camera_id: int):
    return service.queue_analysis(camera_id, {'source': 'manual'})


@app.post('/api/jobs/backfill')
def backfill(payload: BackfillPayload):
    return service.queue_analysis(payload.camera_id, payload.model_dump())


@app.get('/api/jobs')
def list_jobs():
    return service.jobs()


@app.get('/api/jobs/{job_id}')
def get_job(job_id: int):
    job = service.job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    return job


@app.get('/api/history/segments')
def list_segments():
    return service.segments()


@app.get('/api/history/segments/{segment_id}')
def get_segment(segment_id: int):
    segment = service.segment(segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail='Segment not found')
    return segment


@app.post('/api/review/{segment_id}')
def review_segment(segment_id: int, payload: ReviewPayload):
    segment = service.review_segment(segment_id, payload.reviewed_label, payload.review_note, payload.review_by)
    if not segment:
        raise HTTPException(status_code=404, detail='Segment not found')
    return segment


@app.get('/api/charts/daily')
def chart_daily(days: int = 7):
    return service.chart_daily(days)


@app.get('/api/reports/daily')
def report_daily(day: str | None = None):
    return service.report_daily(day)


@app.get('/api/logs/tail')
def logs_tail(name: str = 'api', lines: int = 200):
    mapping = {'api': LOG_ROOT / 'api.log', 'mcp': LOG_ROOT / 'mcp.log', 'worker': LOG_ROOT / 'worker.log'}
    path = mapping.get(name)
    if not path:
        raise HTTPException(status_code=404, detail='Unknown log')
    if not path.exists():
        return {'name': name, 'content': ''}
    content = path.read_text(encoding='utf-8', errors='ignore').splitlines()[-lines:]
    __PLACEHOLDER__


@app.get('/api/evidence/{segment_id}')
def evidence(segment_id: int):
    segment = service.segment(segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail='Segment not found')
    return {'segment_id': segment_id, 'evidence_path': segment.get('evidence_path')}


@app.get('/{file_path:path}')
def get_file(file_path: str):
    path = BASE_DIR / file_path
    if path.exists() and path.is_file() and 'data/evidence/' in str(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail='File not found')
