# MCP Server Documentation

## Overview

The Factory Analytics MCP (Model Context Protocol) Bridge provides programmatic access to all REST API functionality through a standardized JSON-RPC 2.0 interface. This allows AI agents and external tools to interact with the system using a consistent protocol.

**Current Version:** 0.1.0
**Base URL:** `http://localhost:8001`
**Total Tools:** 43

## Authentication

If `MCP_TOKEN` is configured in the environment, all endpoints require Bearer token authentication:

```http
Authorization: Bearer <your-mcp-token>
```

## Endpoints

### Health Check
```http
GET /health
```
Returns basic health status of the MCP server.

### List Tools
```http
GET /mcp/tools
```
Returns the complete catalog of available tools with descriptions.

### Execute Tool
```http
POST /mcp
Content-Type: application/json

{
  "method": "<tool_name>",
  "params": {
    "<param_name>": <value>
  },
  "id": <request_id>
}
```

## Tools Reference

### System & Health (4 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `system_health` | Get app, Frigate, Ollama, and DB health | None |
| `system_status` | Get system status with camera/job/segment counts | None |
| `frigate_health` | Get Frigate health status | None |
| `ollama_health` | Get Ollama health and available models | None |

**Example:**
```json
{
  "method": "system_health",
  "params": {},
  "id": 1
}
```

### Cameras (9 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `camera_list` | List all configured cameras | None |
| `camera_status` | Get specific camera details | `camera_id` (int) |
| `camera_create` | Create a new camera | `frigate_name` (str), `name` (opt), `enabled` (opt), `interval_seconds` (opt) |
| `camera_update` | Update camera settings | `camera_id` (int), plus fields to update |
| `camera_delete` | Delete a camera | `camera_id` (int) |
| `camera_test` | Test camera snapshot | `camera_id` (int) OR `frigate_name` (str) |
| `camera_health` | Get camera health status | `camera_id` (int) |
| `all_cameras_health` | Get health for all cameras | None |

**Example - Create Camera:**
```json
{
  "method": "camera_create",
  "params": {
    "frigate_name": "camera_01",
    "name": "Front Door",
    "enabled": true,
    "interval_seconds": 300
  },
  "id": 2
}
```

### Groups (10 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `group_list` | List all groups | None |
| `group_get` | Get specific group | `group_id` (int) |
| `group_create` | Create a new group | `group_type` (str), `name` (str), `interval_seconds` (opt) |
| `group_update` | Update group | `group_id` (int), plus fields to update |
| `group_delete` | Delete a group | `group_id` (int) |
| `group_add_camera` | Add camera to group | `group_id` (int), `camera_id` (int) |
| `group_remove_camera` | Remove camera from group | `group_id` (int), `camera_id` (int) |
| `group_list_cameras` | List cameras in group | `group_id` (int) |
| `camera_groups` | List groups for camera | `camera_id` (int) |
| `group_run_analysis` | Run analysis for all cameras in group | `group_id` (int) |

### Jobs (9 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `run_list` | List all jobs | None |
| `run_get` | Get specific job | `job_id` (int) |
| `run_analysis_now` | Queue analysis for camera | `camera_id` (int) |
| `run_backfill` | Queue backfill job | `camera_id` (int), `start_ts` (str), `end_ts` (str) |
| `job_cancel` | Cancel a pending/running job | `job_id` (int) |
| `job_retry` | Retry a failed job | `job_id` (int) |
| `jobs_bulk_cancel` | Cancel multiple jobs | `job_ids` (list[int]) |
| `jobs_cancel_all` | Cancel all pending/running | None |
| `job_stats` | Get job statistics | None |

### History & Segments (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `history_search` | List recent segments | None |
| `segment_get` | Get specific segment | `segment_id` (int) |
| `review_segment` | Review/override classification | `segment_id` (int), `reviewed_label` (str), `review_note` (opt), `review_by` (opt) |

### Charts (7 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `chart_daily` | Daily rollup chart | `days` (int, default=7) |
| `chart_heatmap` | Activity heatmap | None |
| `chart_heatmap_by_group` | Heatmap by group | None |
| `chart_shift_summary` | Shift summary | None |
| `chart_camera_summary` | Camera summary | None |
| `chart_job_failures` | Job failure stats | None |
| `chart_confidence_distribution` | Confidence distribution | None |

### Settings (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `settings_get` | Get application settings | None |
| `settings_update` | Update settings | `values` (dict) |
| `ollama_test` | Test Ollama connection | None |

**Example - Update Settings:**
```json
{
  "method": "settings_update",
  "params": {
    "values": {
      "ollama_vision_model": "llama3.2-vision",
      "analysis_interval_seconds": 300
    }
  },
  "id": 3
}
```

### Frigate Integration (2 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `frigate_sync_cameras` | Sync cameras from Frigate | None |
| `frigate_list_cameras` | List Frigate cameras | None |

### Reports (1 tool)

| Tool | Description | Parameters |
|------|-------------|------------|
| `report_get_daily` | Get daily report | `day` (str, optional) |

### Scheduler (1 tool)

| Tool | Description | Parameters |
|------|-------------|------------|
| `scheduler_reset` | Reset scheduler state | None |

### Logs (1 tool)

| Tool | Description | Parameters |
|------|-------------|------------|
| `logs_tail` | Get recent log lines | `name` (str: api/mcp/worker), `lines` (int, default=200) |

## Response Format

All responses follow JSON-RPC 2.0 specification:

**Success:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    // Tool-specific result
  }
}
```

**Error:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32600,
    "message": "Invalid request"
  }
}
```

## Error Codes

- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing token)
- `403` - Forbidden (invalid token)
- `404` - Not Found (resource doesn't exist or unknown tool)
- `409` - Conflict (e.g., trying to retry non-failed job)

## Testing

A comprehensive test suite is available:

```bash
python3 tests/test_mcp_tools.py
```

This tests all 43 tools with a temporary database.

## Comparison with REST API

MCP tools provide **100% feature parity** with REST API endpoints:

| Category | REST Endpoints | MCP Tools | Coverage |
|----------|----------------|-----------|----------|
| Health & Status | 6 | 4 | 100%* |
| Cameras | 9 | 9 | 100% |
| Groups | 8 | 10 | 100%* |
| Jobs | 9 | 9 | 100% |
| History/Segments | 5 | 3 | 100%* |
| Charts | 7 | 7 | 100% |
| Reports | 1 | 1 | 100% |
| Settings | 3 | 3 | 100% |
| Frigate | 2 | 2 | 100% |
| Scheduler | 1 | 1 | 100% |
| Logs | 1 | 1 | 100% |

*Note: Some MCP tools combine multiple related REST endpoints for convenience.

## Usage Examples

### Python Client
```python
import requests

MCP_URL = "http://localhost:8001"
headers = {"Authorization": "Bearer your-token"}  # if MCP_TOKEN is set

# List cameras
response = requests.post(
    f"{MCP_URL}/mcp",
    headers=headers,
    json={
        "method": "camera_list",
        "params": {},
        "id": 1
    }
)
cameras = response.json()["result"]

# Create group
response = requests.post(
    f"{MCP_URL}/mcp",
    headers=headers,
    json={
        "method": "group_create",
        "params": {
            "group_type": "machine",
            "name": "Assembly Line A",
            "interval_seconds": 300
        },
        "id": 2
    }
)
group = response.json()["result"]
```

### cURL Examples
```bash
# Get system health
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "system_health", "params": {}, "id": 1}'

# Create camera
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "camera_create",
    "params": {
      "frigate_name": "cam_01",
      "name": "Front Door",
      "enabled": true
    },
    "id": 2
  }'

# Run group analysis
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "group_run_analysis",
    "params": {"group_id": 1},
    "id": 3
  }'
```

## Configuration

The MCP server is configured via environment variables:

- `MCP_PORT` - Port for MCP server (default: 8001)
- `MCP_TOKEN` - Optional Bearer token for authentication
- `LOG_ROOT` - Path for log files

## Architecture

The MCP server is built on FastAPI and shares the same database and service layer as the main REST API:

```
┌─────────────────┐
│   MCP Client    │
└────────┬────────┘
         │ JSON-RPC 2.0
         ▼
┌─────────────────┐
│  MCP Server     │
│  (FastAPI)      │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│Dispatch│ │Analytics│
│ Logic  │ │Service  │
└────────┘ └────┬───┘
                │
           ┌────┴────┐
           ▼         ▼
      ┌────────┐ ┌────────┐
      │Database│ │External│
      │(SQLite)│ │Services│
      └────────┘ └────────┘
```

## Version History

- **2026-03-31**: Added 29 new tools (43 total), 100% REST API coverage
- **2026-03-28**: Initial MCP server with 14 tools

## See Also

- [API Explorer](/api-explorer) - Interactive API documentation
- [Control Center](/control-center) - System monitoring dashboard
- [REST API Documentation](api-explorer.html) - Full REST endpoint reference
