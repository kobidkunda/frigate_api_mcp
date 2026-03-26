from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from factory_analytics.config import MCP_TOKEN
from factory_analytics.database import Database
from factory_analytics.services import AnalyticsService

app = FastAPI(title='Factory Analytics MCP Bridge', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

db = Database()
service = AnalyticsService(db)


class MCPRequest(BaseModel):
    method: str
    params: dict = {}
    id: str | int | None = None


def authorize(auth_header: str | None):
    if not MCP_TOKEN:
        return
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing bearer token')
    token = auth_header.split(' ', 1)[1].strip()
    if token != MCP_TOKEN:
        raise HTTPException(status_code=403, detail='Invalid token')


TOOLS = {
    'system_health': {'description': 'Get app, Frigate, Ollama, and DB health'},
    'camera_list': {'description': 'List configured cameras'},
    'camera_status': {'description': 'Get one camera by id; param: camera_id'},
    'run_list': {'description': 'List jobs'},
    'run_get': {'description': 'Get one job; param: job_id'},
    'history_search': {'description': 'List recent segments'},
    'segment_get': {'description': 'Get one segment; param: segment_id'},
    'chart_daily': {'description': 'Get daily rollup chart; param: days'},
    'report_get_daily': {'description': 'Get daily report; param: day'},
    'frigate_health': {'description': 'Get Frigate health'},
    'ollama_health': {'description': 'Get Ollama health'},
    'run_analysis_now': {'description': 'Queue analysis for a camera; param: camera_id'},
    'run_backfill': {'description': 'Queue a backfill job; params: camera_id, start_ts, end_ts'},
    'review_segment': {'description': 'Review/override one segment; params: segment_id, reviewed_label, review_note, review_by'},
}


@app.get('/mcp/tools')
def tools(authorization: str | None = Header(default=None)):
    authorize(authorization)
    return TOOLS


@app.post('/mcp')
def call(req: MCPRequest, authorization: str | None = Header(default=None)):
    authorize(authorization)
    method = req.method
    params = req.params or {}
    if method == 'ping':
        result = {'ok': True}
    elif method == 'tools/list':
        result = TOOLS
    elif method == 'tools/call':
        result = dispatch(params.get('name'), params.get('arguments', {}))
    else:
        result = dispatch(method, params)
    return {'jsonrpc': '2.0', 'id': req.id, 'result': result}


@app.get('/health')
def health():
    return {'ok': True}


def dispatch(name: str, args: dict):
    if name == 'system_health':
        return service.system_health()
    if name == 'camera_list':
        return service.list_cameras()
    if name == 'camera_status':
        return service.db.get_camera(int(args['camera_id']))
    if name == 'run_list':
        return service.jobs()
    if name == 'run_get':
        return service.job(int(args['job_id']))
    if name == 'history_search':
        return service.segments()
    if name == 'segment_get':
        return service.segment(int(args['segment_id']))
    if name == 'chart_daily':
        return service.chart_daily(int(args.get('days', 7)))
    if name == 'report_get_daily':
        return service.report_daily(args.get('day'))
    if name == 'frigate_health':
        return service.frigate_client().health()
    if name == 'ollama_health':
        return service.ollama_client().health()
    if name == 'run_analysis_now':
        return service.queue_analysis(int(args['camera_id']), {'source': 'mcp'})
    if name == 'run_backfill':
        return service.queue_analysis(int(args['camera_id']), args)
    if name == 'review_segment':
        return service.review_segment(int(args['segment_id']), args['reviewed_label'], args.get('review_note', ''), args.get('review_by', 'mcp'))
    raise HTTPException(status_code=404, detail=f'Unknown tool: {name}')
