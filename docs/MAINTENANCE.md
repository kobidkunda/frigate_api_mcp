# Factory Analytics Maintenance Manual

> **Audience:** System administrators and DevOps engineers
> **Last updated:** 2026-04-01
> **Version:** 1.0

---

## Quick Reference Card

### Service Commands

```bash
# Start all services
./factory-analytics.sh start

# Stop all services
./factory-analytics.sh stop

# Restart all services
./factory-analytics.sh restart

# Check service status
./factory-analytics.sh status

# View logs (API)
./factory-analytics.sh logs api

# View logs (MCP)
./factory-analytics.sh logs mcp
```

### Ports & Endpoints

| Service | Port | Purpose |
|---------|------|---------|
| API | 8090 | Main web application and REST API |
| MCP | 8099 | Model Context Protocol server |

### Health Check Endpoints

```bash
# API health (comprehensive)
curl http://localhost:8090/api/health

# Quick API ping
curl http://localhost:8090/api/ping

# MCP health
curl http://localhost:8099/health
```

### Key Directories

| Path | Purpose |
|------|---------|
| `data/db/factory_analytics.db` | SQLite database |
| `logs/` | Application logs |
| `run/` | PID files |
| `data/evidence/snapshots/` | Camera snapshots |
| `data/evidence/frames/` | Multi-frame captures |
| `data/evidence/groups/` | Group analysis collages |

### Critical Files

| File | Purpose |
|------|---------|
| `.env` | Environment configuration |
| `.env.example` | Configuration template |
| `factory-analytics.sh` | Service management script |
| `factory_analytics/config.py` | Application configuration |

---

## Service Management

### Startup Procedure

1. **Verify environment:**
   ```bash
   # Check .env exists
   cat .env

   # Verify Python venv
   ls -la .venv/bin/python
   ```

2. **Start services:**
   ```bash
   ./factory-analytics.sh start
   ```

3. **Verify startup:**
   ```bash
   # Check processes
   ps aux | grep -E 'factory_analytics|uvicorn'

   # Check health
   curl -s http://localhost:8090/api/health | jq .
   ```

### Shutdown Procedure

1. **Graceful stop:**
   ```bash
   ./factory-analytics.sh stop
   ```

2. **Verify shutdown:**
   ```bash
   # Should show no processes
   ps aux | grep -E 'factory_analytics|uvicorn' | grep -v grep

   # Should show port is free
   lsof -i :8090
   lsof -i :8099
   ```

3. **Force kill if needed:**
   ```bash
   # Only if graceful stop fails
   ./factory-analytics.sh stop --force
   # Or manually:
   kill $(cat run/api.pid) 2>/dev/null
   kill $(cat run/mcp.pid) 2>/dev/null
   ```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_HOST` | `0.0.0.0` | API bind address |
| `APP_PORT` | `8090` | API port |
| `MCP_HOST` | `0.0.0.0` | MCP server bind address |
| `MCP_PORT` | `8099` | MCP server port |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `FRIGATE_URL` | Required | Frigate NVR base URL |
| `OLLAMA_URL` | Required | Ollama LLM endpoint |
| `MCP_TOKEN` | Optional | Bearer token for MCP authentication |

### Log Files

| Log File | Content |
|----------|---------|
| `logs/api.log` | API server output |
| `logs/mcp.log` | MCP server output |
| `logs/worker.log` | Worker/scheduler output (in-app) |

**Log rotation:** Logs are appended. Use logrotate or manual rotation for long-running deployments.

**View live logs:**
```bash
# API logs
tail -f logs/api.log

# MCP logs
tail -f logs/mcp.log

# Filter errors
tail -f logs/api.log | grep -i error
```

### Process Management

PID files are stored in `run/`:
- `run/api.pid` - API process ID
- `run/mcp.pid` - MCP process ID

**Check if running:**
```bash
# Using script
./factory-analytics.sh status

# Manual check
if [ -f run/api.pid ]; then
  kill -0 $(cat run/api.pid) 2>/dev/null && echo "API running" || echo "API stopped"
fi
```

---

## Database Maintenance

### Database Location

```
data/db/factory_analytics.db
```

### Backup Procedures

**Manual backup:**
```bash
# Create backup with timestamp
sqlite3 data/db/factory_analytics.db ".backup 'data/db/backup_$(date +%Y%m%d_%H%M%S).db'"

# Or copy directly (ensure no writes in progress)
cp data/db/factory_analytics.db "data/db/backup_$(date +%Y%m%d_%H%M%S).db"
```

**Scheduled backup (cron):**
```bash
# Add to crontab (daily at 2am)
0 2 * * * cd /path/to/frigate && sqlite3 data/db/factory_analytics.db ".backup 'data/db/backup_$(date +\%Y\%m\%d).db'"
```

### Restore Procedures

```bash
# Stop services first
./factory-analytics.sh stop

# Restore from backup
cp data/db/backup_20260401.db data/db/factory_analytics.db

# Verify integrity
sqlite3 data/db/factory_analytics.db "PRAGMA integrity_check;"

# Restart services
./factory-analytics.sh start
```

### Schema Reference

| Table | Purpose |
|-------|---------|
| `cameras` | Camera configurations and metadata |
| `camera_groups` | Group definitions |
| `camera_group_membership` | Many-to-many camera-group relationships |
| `segments` | Analysis results with LLM classifications |
| `jobs` | Job queue and execution history |
| `settings` | Application settings (key-value) |
| `audit_log` | Audit trail for operations |

**View schema:**
```bash
sqlite3 data/db/factory_analytics.db ".schema" | less
```

### Common Maintenance Queries

```sql
-- Check database size
SELECT page_count * page_size / 1024 / 1024 AS size_mb
FROM pragma_page_count(), pragma_page_size();

-- Recent jobs status
SELECT status, COUNT(*) FROM jobs
WHERE created_at > datetime('now', '-1 day')
GROUP BY status;

-- Clear old completed jobs (older than 30 days)
DELETE FROM jobs
WHERE status IN ('completed', 'cancelled', 'failed')
AND created_at < datetime('now', '-30 days');

-- Reset stuck running jobs
UPDATE jobs SET status = 'cancelled'
WHERE status = 'running'
AND created_at < datetime('now', '-1 hour');

-- Check segment storage
SELECT COUNT(*) FROM segments WHERE created_at > datetime('now', '-7 days');
```

### Database Optimization

```bash
# Analyze and optimize
sqlite3 data/db/factory_analytics.db "ANALYZE;"

# Vacuum to reclaim space
sqlite3 data/db/factory_analytics.db "VACUUM;"

# Check integrity
sqlite3 data/db/factory_analytics.db "PRAGMA integrity_check;"
```

---

## External Integrations

### Frigate NVR

**Configuration:**
- URL: Set in `FRIGATE_URL` environment variable
- Purpose: Camera snapshots, camera discovery, live streams

**Test connection:**
```bash
# Check Frigate health via app
curl -s http://localhost:8090/api/health | jq '.frigate'

# Direct Frigate API test
curl -s ${FRIGATE_URL}/api/stats | jq .
```

**Sync cameras:**
```bash
# Via API
curl -X POST http://localhost:8090/api/cameras/sync

# Check synced cameras
curl -s http://localhost:8090/api/cameras | jq '.[] | {id, frigate_name, enabled}'
```

**Snapshot locations:**
- Latest: `data/evidence/snapshots/{camera}_{timestamp}.jpg`
- Multi-frame: `data/evidence/frames/{camera}_{timestamp}/frame_0.jpg`

**Common Frigate issues:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| 404 on snapshot | Camera not found in Frigate | Verify camera name matches Frigate config |
| Connection refused | Frigate not running | Check Frigate service status |
| Timeout on snapshot | Network issue | Check FRIGATE_URL and network connectivity |

### Ollama / LLM

**Configuration:**
- URL: Set in `OLLAMA_URL` environment variable
- Purpose: Image classification, worker detection

**Test connection:**
```bash
# Check Ollama health via app
curl -s http://localhost:8090/api/health | jq '.ollama'

# List available models
curl -s ${OLLAMA_URL}/api/tags | jq '.models[].name'

# Test inference
curl -s http://localhost:8090/api/ollama/test-vision
```

**Model requirements:**
- Vision model required (e.g., `qwen3.5:2b`, `llama3.1:8b`)
- Must support image input

**Pull a model:**
```bash
# Via Ollama CLI
ollama pull qwen3.5:2b

# Check available
ollama list
```

**Configure model in settings:**
```bash
# Get current settings
curl -s http://localhost:8090/api/settings | jq '{ollama_model, ollama_vision_model}'

# Update model
curl -X PATCH http://localhost:8090/api/settings \
  -H "Content-Type: application/json" \
  -d '{"ollama_model": "qwen3.5:2b"}'
```

### Health Check Procedures

**Full system health:**
```bash
curl -s http://localhost:8090/api/health | jq .
```

**Expected response:**
```json
{
  "ok": true,
  "app": {"ok": true},
  "database": {"ok": true, "message": "ok"},
  "frigate": {"ok": true, "version": "0.17.1"},
  "ollama": {"ok": true, "models": ["qwen3.5:2b"]}
}
```

**Individual checks:**
```bash
# Database
curl -s http://localhost:8090/api/health | jq '.database'

# Frigate
curl -s http://localhost:8090/api/health | jq '.frigate'

# Ollama
curl -s http://localhost:8090/api/health | jq '.ollama'
```

---

## Worker & Scheduler

### Job Queue Overview

Jobs are stored in the `jobs` table with states:
- `pending` - Queued for execution
- `running` - Currently executing
- `completed` - Successfully finished
- `failed` - Execution failed
- `cancelled` - Manually cancelled

**View current jobs:**
```bash
curl -s "http://localhost:8090/api/jobs?limit=10" | jq '.items[] | {id, camera_id, status, created_at}'
```

### Job Timeout Configuration

Default timeout: 600 seconds (10 minutes)

**Check current timeout:**
```bash
sqlite3 data/db/factory_analytics.db "SELECT value FROM settings WHERE key='job_timeout_seconds'"
```

**Update timeout:**
```bash
curl -X PATCH http://localhost:8090/api/settings \
  -H "Content-Type: application/json" \
  -d '{"job_timeout_seconds": 900}'
```

### Stuck Job Recovery

Jobs stuck in `running` state are auto-cancelled after timeout.

**Manual recovery:**
```bash
# Check for stuck jobs
sqlite3 data/db/factory_analytics.db \
  "SELECT id, camera_id, created_at FROM jobs WHERE status='running'"

# Cancel stuck jobs via API
curl -X POST http://localhost:8090/api/jobs/{job_id}/cancel

# Or via database
sqlite3 data/db/factory_analytics.db \
  "UPDATE jobs SET status='cancelled' WHERE status='running' AND created_at < datetime('now', '-1 hour')"
```

### Analysis Triggers

**Manual triggers:**

```bash
# Trigger single camera analysis
curl -X POST http://localhost:8090/api/cameras/{camera_id}/analyze

# Trigger group analysis
curl -X POST http://localhost:8090/api/groups/{group_type}/{group_name}/analyze

# Check scheduler status
curl -s http://localhost:8090/api/scheduler/status | jq .
```

### Worker Configuration

Key settings for worker behavior:

| Setting | Default | Description |
|---------|---------|-------------|
| `analysis_interval_seconds` | 60 | Interval between scheduled analyses |
| `job_timeout_seconds` | 600 | Max job duration before auto-cancel |
| `max_retries` | 3 | Retry attempts for failed jobs |
| `group_retry_delay_seconds` | 60 | Delay before group retry |

### Scheduler Management

**Enable/disable scheduling:**
```bash
# Check status
curl -s http://localhost:8090/api/scheduler/status

# Pause scheduler (not implemented - jobs still queue)
# Use camera.enabled = false to disable individual cameras
```

**Configure camera analysis interval:**
```bash
# Update camera interval
curl -X PATCH http://localhost:8090/api/cameras/{camera_id} \
  -H "Content-Type: application/json" \
  -d '{"interval_seconds": 300}'
```

---

## Monitoring & Alerts

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/api/health` | Full system health (database, Frigate, Ollama) |
| `/api/ping` | Quick liveness check |
| `/api/scheduler/status` | Worker/scheduler status |

### Log Patterns to Watch

**Errors:**
```bash
# API errors
grep -i "error\|exception\|failed" logs/api.log

# Ollama inference errors
grep -i "ollama.*error\|inference.*failed" logs/api.log

# Frigate connection errors
grep -i "frigate.*error\|connection.*refused" logs/api.log
```

**Warnings:**
```bash
# Timeout warnings
grep -i "timeout\|timed out" logs/api.log

# Stuck jobs
grep -i "stuck\|cancelled" logs/api.log
```

### Performance Indicators

**Check job throughput:**
```sql
SELECT
  strftime('%Y-%m-%d %H:00', created_at) as hour,
  status,
  COUNT(*) as count
FROM jobs
WHERE created_at > datetime('now', '-24 hours')
GROUP BY hour, status
ORDER BY hour DESC;
```

**Check analysis latency:**
```sql
SELECT
  AVG((julianday(updated_at) - julianday(created_at)) * 86400) as avg_seconds,
  COUNT(*) as count
FROM jobs
WHERE status = 'completed'
AND created_at > datetime('now', '-1 day');
```

### Metrics Collection

**System metrics:**
```bash
# Database size
du -h data/db/factory_analytics.db

# Evidence storage size
du -sh data/evidence/

# Log size
du -h logs/*.log

# Process memory
ps aux | grep uvicorn | awk '{print $6/1024 "MB"}'
```

---

## Troubleshooting Guide

### Quick Diagnostics

```bash
# Full health check
curl -s http://localhost:8090/api/health | jq .

# Check all services running
./factory-analytics.sh status

# Check recent errors
tail -100 logs/api.log | grep -i error

# Check database connectivity
sqlite3 data/db/factory_analytics.db "SELECT 1"
```

### Problem: API Not Responding

**Symptoms:**
- Connection refused on port 8090
- Health check returns nothing

**Diagnostics:**
```bash
# Check if process is running
ps aux | grep factory_analytics

# Check if port is in use
lsof -i :8090

# Check logs
tail -50 logs/api.log
```

**Solutions:**
1. If port in use by another process:
   ```bash
   kill $(lsof -t -i:8090)
   ./factory-analytics.sh start
   ```

2. If venv issue:
   ```bash
   # Recreate venv
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ./factory-analytics.sh start
   ```

### Problem: Database Locked

**Symptoms:**
- "database is locked" errors in logs
- Write operations failing

**Diagnostics:**
```bash
# Check for other connections
lsof data/db/factory_analytics.db

# Check integrity
sqlite3 data/db/factory_analytics.db "PRAGMA integrity_check;"
```

**Solutions:**
1. Stop all services and retry:
   ```bash
   ./factory-analytics.sh stop
   sqlite3 data/db/factory_analytics.db "PRAGMA integrity_check;"
   ./factory-analytics.sh start
   ```

2. If corruption suspected:
   ```bash
   # Restore from backup
   ./factory-analytics.sh stop
   cp data/db/backup_latest.db data/db/factory_analytics.db
   ./factory-analytics.sh start
   ```

### Problem: Frigate Connection Failed

**Symptoms:**
- Health check shows `frigate.ok: false`
- Snapshot fetch returns 404

**Diagnostics:**
```bash
# Check Frigate URL
cat .env | grep FRIGATE_URL

# Test direct connection
curl -v ${FRIGATE_URL}/api/stats

# Check network
ping $(echo $FRIGATE_URL | sed 's|https\?://||' | cut -d: -f1)
```

**Solutions:**
1. Verify FRIGATE_URL in `.env`
2. Check Frigate service is running
3. Check network connectivity and firewall
4. Verify camera names match Frigate config

### Problem: Ollama Inference Failed

**Symptoms:**
- Health check shows `ollama.ok: false`
- Analysis jobs failing
- "model not found" errors

**Diagnostics:**
```bash
# Check Ollama service
curl -s ${OLLAMA_URL}/api/tags | jq .

# Check configured model
sqlite3 data/db/factory_analytics.db "SELECT value FROM settings WHERE key='ollama_model'"

# Test inference
curl -X POST ${OLLAMA_URL}/api/generate \
  -d '{"model": "qwen3.5:2b", "prompt": "test"}'
```

**Solutions:**
1. Pull required model:
   ```bash
   ollama pull qwen3.5:2b
   ```

2. Update model setting:
   ```bash
   curl -X PATCH http://localhost:8090/api/settings \
     -H "Content-Type: application/json" \
     -d '{"ollama_model": "qwen3.5:2b"}'
   ```

### Problem: Stuck Jobs Blocking Queue

**Symptoms:**
- No new jobs being processed
- Jobs stuck in `running` state
- Scheduler shows active job but no progress

**Diagnostics:**
```bash
# Check for running jobs
curl -s "http://localhost:8090/api/jobs?status=running" | jq .

# Check job age
sqlite3 data/db/factory_analytics.db \
  "SELECT id, camera_id, created_at FROM jobs WHERE status='running'"
```

**Solutions:**
1. Jobs auto-cancel after timeout (default 10 min)
2. Manual cancel:
   ```bash
   curl -X POST http://localhost:8090/api/jobs/{job_id}/cancel
   ```
3. Reduce timeout if frequent:
   ```bash
   curl -X PATCH http://localhost:8090/api/settings \
     -H "Content-Type: application/json" \
     -d '{"job_timeout_seconds": 300}'
   ```

### Problem: High Memory Usage

**Symptoms:**
- Process using excessive memory
- System slowdown

**Diagnostics:**
```bash
# Check process memory
ps aux | grep uvicorn

# Check evidence storage size
du -sh data/evidence/

# Check database size
ls -lh data/db/factory_analytics.db
```

**Solutions:**
1. Clean old evidence:
   ```bash
   # Remove evidence older than 30 days
   find data/evidence -type f -mtime +30 -delete
   ```

2. Vacuum database:
   ```bash
   sqlite3 data/db/factory_analytics.db "VACUUM;"
   ```

3. Reduce image quality/resolution:
   ```bash
   curl -X PATCH http://localhost:8090/api/settings \
     -H "Content-Type: application/json" \
     -d '{"image_resize_resolution": "640p", "image_compression_quality": 80}'
   ```

### Problem: Multi-frame Capture Not Working

**Symptoms:**
- Only 1 frame captured instead of multiple
- Frame directories empty

**Diagnostics:**
```bash
# Check frame settings
sqlite3 data/db/factory_analytics.db \
  "SELECT key, value FROM settings WHERE key IN ('llm_frames_per_process', 'llm_seconds_window')"

# Check frame directories
ls -la data/evidence/frames/
```

**Solutions:**
1. Verify settings:
   - `llm_seconds_window`: Total seconds to capture (default: 3)
   - `llm_frames_per_process`: Frames per second (default: 1)
   - Total frames = seconds × fps

2. Update settings:
   ```bash
   curl -X PATCH http://localhost:8090/api/settings \
     -H "Content-Type: application/json" \
     -d '{"llm_seconds_window": 5, "llm_frames_per_process": 2}'
   ```

---

## Appendix: Configuration Reference

### All Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `analysis_interval_seconds` | int | 60 | Default analysis interval for cameras |
| `group_retry_delay_seconds` | int | 60 | Delay before retrying failed group analysis |
| `ollama_model` | string | "qwen3.5:2b" | LLM model for text generation |
| `ollama_vision_model` | string | "qwen3.5:2b" | LLM model for image analysis |
| `llm_frames_per_process` | int | 1 | Frames per second to capture |
| `llm_seconds_window` | int | 3 | Total seconds to capture frames |
| `image_resize_resolution` | string | "original" | Max dimension: 320p, 640p, 720p, original |
| `image_compression_quality` | int | 100 | JPEG quality (1-100) |
| `job_timeout_seconds` | int | 600 | Job timeout in seconds |

### Environment Variables

See `.env.example` for template:

```bash
# Application
APP_HOST=0.0.0.0
APP_PORT=8090
MCP_HOST=0.0.0.0
MCP_PORT=8099
LOG_LEVEL=INFO

# Integrations
FRIGATE_URL=http://192.168.1.100:5000
OLLAMA_URL=http://192.168.1.100:11434

# Security (optional)
MCP_TOKEN=your-secure-token-here
```

### API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | System health check |
| `/api/ping` | GET | Quick liveness check |
| `/api/cameras` | GET/POST | Camera list/create |
| `/api/cameras/{id}` | GET/PATCH/DELETE | Camera CRUD |
| `/api/cameras/{id}/analyze` | POST | Trigger analysis |
| `/api/groups` | GET/POST | Group list/create |
| `/api/groups/{type}/{name}/analyze` | POST | Trigger group analysis |
| `/api/jobs` | GET | Job list |
| `/api/jobs/{id}/cancel` | POST | Cancel job |
| `/api/settings` | GET/PATCH | Application settings |
| `/api/scheduler/status` | GET | Scheduler status |

### MCP Server Tools

The MCP server provides 43 tools covering all API functionality. See `docs/mcp-server.md` for complete reference.

---

## Support

For issues not covered in this manual:

1. Check logs: `logs/api.log`, `logs/mcp.log`
2. Review `docs/features.md` for feature documentation
3. Review `docs/implementation/` for change history
4. Check health endpoints for component status
5. Consult `AGENTS.md` for project structure
