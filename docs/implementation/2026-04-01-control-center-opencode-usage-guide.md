# 2026-04-01 - Control Center & OpenCode Usage Guide

## Summary
Created comprehensive guide for using OpenCode with the Factory Analytics Control Center, covering MCP server integration, skills inventory, and detailed usage instructions.

## Why
- User requested detailed documentation on how to use OpenCode/OpenClaw/Claude with the Control Center
- Need to document MCP server integration points
- Clarify skills inventory and how to use them
- Provide step-by-step integration instructions

## Scope
- Control Center page overview
- MCP server setup and configuration
- Skills system documentation
- OpenCode/Claude Code integration examples
- API usage patterns
- Best practices and troubleshooting

## Control Center Overview

The Control Center at `http://192.168.88.81:8090/control-center` provides:

### 1. Config Files Section
- Displays repository configuration files
- Shows `.opencode/package.json`, `AGENTS.md`, `.env` files
- Previews file contents (with sensitive data masked)
- Read-only inspection for system understanding

### 2. MCP/API Status Section
- Real-time monitoring of MCP server status
- Health checks for Frigate and Ollama connections
- API endpoint availability verification
- Connection testing capabilities

### 3. Skills Inventory Section
- Lists all available skills from three locations:
  - `~/.agents/skills/` (global skills)
  - `~/.config/opencode/skills/` (OpenCode skills)
  - `.opencode/skills/` (project skills)
- Shows skill names and availability

### 4. Install Instructions Section
- Platform-specific setup guidance
- Configuration path recommendations
- Dependency installation steps

## MCP Server Setup

### Configuration

**Environment Variables (.env):**
```bash
MCP_HOST=0.0.0.0
MCP_PORT=8099
MCP_TOKEN=change-me-to-secure-value
```

**Key Settings:**
- `MCP_HOST`: Bind address (default: 0.0.0.0)
- `MCP_PORT`: Port for MCP server (default: 8099)
- `MCP_TOKEN`: Bearer token for authentication

### Starting the Server

```bash
# Start all services
./factory-analytics.sh start

# Check MCP server status
./factory-analytics.sh status

# View MCP logs
./factory-analytics.sh logs | grep mcp
```

### MCP Server Endpoints

**Health Check:**
```http
GET http://127.0.0.1:8099/health
```

**List Available Tools:**
```http
GET http://127.0.0.1:8099/mcp/tools
Authorization: Bearer <your-mcp-token>
```

**Execute Tool:**
```http
POST http://127.0.0.1:8099/mcp
Content-Type: application/json
Authorization: Bearer <your-mcp-token>

{
  "method": "system_health",
  "params": {},
  "id": 1
}
```

## Skills System

### Available Skills

**Project Skill (`.opencode/skills/`):**
- `ui-ux-pro-max`: UI/UX design intelligence with searchable database

**Global Skills (`~/.agents/skills/`):**
- Multiple specialized skills for different workflows
- See Control Center for complete inventory

### Using Skills

Skills can be invoked through:
1. **OpenCode**: Automatic skill loading based on context
2. **Claude Code**: Via `Skill` tool
3. **Manual**: Reading SKILL.md files directly

### Factory Analytics Skill

**Location:** `skills/factory-analytics/SKILL.md`

**Purpose:**
- Factory activity reporting
- Idle time and sleep-suspect monitoring
- Camera health checks
- Frigate/Ollama connectivity verification
- Analysis job management
- Evidence lookup
- Daily/weekly/monthly summaries

**Recommended MCP Tools:**
- `system_health`: Overall system status
- `camera_list`: List all cameras
- `run_list`: View job queue
- `history_search`: Browse analysis segments
- `chart_daily`: Daily activity charts
- `report_get_daily`: Daily reports
- `frigate_health`: Frigate connection status
- `ollama_health`: Ollama model availability
- `run_analysis_now`: Trigger immediate analysis
- `review_segment`: Review/override classifications

## OpenCode Integration

### Configuration

**Create `.opencode/package.json` in project root:**
```json
{
  "name": "factory-analytics",
  "version": "1.0.0",
  "skills": [
    ".opencode/skills/ui-ux-pro-max"
  ],
  "mcp": {
    "servers": {
      "factory-analytics": {
        "url": "http://127.0.0.1:8099/mcp",
        "token_env": "MCP_TOKEN"
      }
    }
  }
}
```

**Environment Setup:**
```bash
# Copy example environment
cp .env.example .env

# Edit and configure
nano .env

# Set secure MCP token
export MCP_TOKEN=$(openssl rand -hex 32)
echo "MCP_TOKEN=$MCP_TOKEN" >> .env
```

### Using MCP Tools in OpenCode

```python
# Example: Check system health
import requests

MCP_URL = "http://127.0.0.1:8099/mcp"
TOKEN = "your-mcp-token"
headers = {"Authorization": f"Bearer {TOKEN}"}

# Get system health
response = requests.post(
    MCP_URL,
    headers=headers,
    json={
        "method": "system_health",
        "params": {},
        "id": 1
    }
)
health = response.json()["result"]
print(health)

# List cameras
response = requests.post(
    MCP_URL,
    headers=headers,
    json={
        "method": "camera_list",
        "params": {},
        "id": 2
    }
)
cameras = response.json()["result"]
for cam in cameras:
    print(f"Camera: {cam['name']} - {cam['frigate_name']}")

# Run analysis for specific camera
response = requests.post(
    MCP_URL,
    headers=headers,
    json={
        "method": "run_analysis_now",
        "params": {"camera_id": 1},
        "id": 3
    }
)
job = response.json()["result"]
print(f"Queued job: {job['id']}")
```

## Claude Code Integration

### MCP Configuration

**Create `.mcp.json` in project root:**
```json
{
  "mcpServers": {
    "factory-analytics": {
      "url": "http://127.0.0.1:8099/mcp",
      "headers": {
        "Authorization": "Bearer ${MCP_TOKEN}"
      }
    }
  }
}
```

**Alternative with explicit token:**
```json
{
  "mcpServers": {
    "factory-analytics": {
      "url": "http://127.0.0.1:8099/mcp",
      "headers": {
        "Authorization": "Bearer your-secure-token-here"
      }
    }
  }
}
```

### Using in Claude Code

Once configured, Claude Code will automatically:
1. Discover available MCP tools
2. List tools in the tools panel
3. Execute tools via natural language requests

**Example Prompts:**
- "Check system health"
- "List all cameras"
- "Run analysis for camera 1"
- "Show daily chart for last 7 days"
- "Get yesterday's report"

## Codex Integration

### Configuration

**Create `.codex/config.toml` in project root:**
```toml
[mcp_servers.factoryAnalytics]
url = "http://127.0.0.1:8099/mcp"
bearer_token_env_var = "MCP_TOKEN"
startup_timeout_sec = 20
tool_timeout_sec = 120
enabled = true
required = false
```

**Global configuration (`~/.codex/config.toml`):**
```toml
[mcp_servers.factoryAnalytics]
url = "http://127.0.0.1:8099/mcp"
bearer_token_env_var = "MCP_TOKEN"
enabled = true
```

## API Usage Patterns

### Direct REST API Access

**Base URL:** `http://127.0.0.1:8090`

**Key Endpoints:**
- `/api/health`: System health check
- `/api/cameras`: Camera CRUD operations
- `/api/groups`: Group management
- `/api/jobs`: Job queue management
- `/api/history/segments`: Analysis history
- `/api/charts/*`: Chart data endpoints
- `/api/settings`: Application settings

**Example:**
```bash
# Get cameras
curl http://127.0.0.1:8090/api/cameras

# Trigger analysis
curl -X POST http://127.0.0.1:8090/api/cameras/1/run

# Get daily chart
curl "http://127.0.0.1:8090/api/charts/daily?days=7"
```

### MCP vs REST API

| Aspect | REST API | MCP |
|--------|----------|-----|
| Protocol | HTTP/REST | JSON-RPC 2.0 |
| Port | 8090 | 8099 |
| Auth | Session/Cookie | Bearer Token |
| Use Case | Web UI, scripts | AI agents, tools |
| Coverage | 100% | 100% (43 tools) |

## Best Practices

### Security

1. **Always set MCP_TOKEN:**
   ```bash
   # Generate secure token
   export MCP_TOKEN=$(openssl rand -hex 32)
   ```

2. **Never commit .env file:**
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   ```

3. **Use environment variables:**
   ```json
   "headers": {
     "Authorization": "Bearer ${MCP_TOKEN}"
   }
   ```

### Error Handling

```python
import requests
from requests.exceptions import RequestException

def call_mcp(method, params, token):
    try:
        response = requests.post(
            "http://127.0.0.1:8099/mcp",
            headers={"Authorization": f"Bearer {token}"},
            json={"method": method, "params": params, "id": 1},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        if "error" in result:
            raise Exception(f"MCP error: {result['error']}")
        return result.get("result")
    except RequestException as e:
        print(f"Connection error: {e}")
        raise
```

### Rate Limiting

- MCP server has no built-in rate limiting
- Respect system resources when queuing jobs
- Use `job_stats` to monitor queue depth
- Cancel unnecessary jobs with `job_cancel`

## Troubleshooting

### Common Issues

**MCP Server Not Responding:**
```bash
# Check if running
curl http://127.0.0.1:8099/health

# Check logs
./factory-analytics.sh logs | grep -i mcp

# Restart if needed
./factory-analytics.sh restart
```

**Authentication Errors:**
```bash
# Verify token is set
echo $MCP_TOKEN

# Check .env file
grep MCP_TOKEN .env

# Test with curl
curl -H "Authorization: Bearer $MCP_TOKEN" \
  http://127.0.0.1:8099/mcp/tools
```

**Tool Not Found:**
```bash
# List available tools
curl -H "Authorization: Bearer $MCP_TOKEN" \
  http://127.0.0.1:8099/mcp/tools | jq

# Check tool name spelling (case-sensitive)
```

**Camera Not Found:**
```bash
# List cameras to find ID
curl http://127.0.0.1:8090/api/cameras | jq

# Check Frigate sync
curl -X POST http://127.0.0.1:8090/api/frigate/cameras/sync
```

### Logs

**View logs:**
```bash
# All logs
./factory-analytics.sh logs

# MCP specific
tail -f logs/mcp.log

# API specific
tail -f logs/api.log

# Worker specific
tail -f logs/worker.log
```

**Via MCP:**
```json
{
  "method": "logs_tail",
  "params": {"name": "mcp", "lines": 100},
  "id": 1
}
```

## Verification

**Commands Run:**
- Analyzed Control Center page structure
- Reviewed MCP server implementation
- Checked skills inventory
- Verified configuration examples

**Tests Available:**
```bash
# Run MCP tool tests
python3 tests/test_mcp_tools.py

# Run API tests
python3 tests/test_control_center_api.py
```

## Risks / Follow-ups

**Known Limitations:**
- MCP bridge is lightweight (not full MCP protocol implementation)
- No WebSocket support (HTTP only)
- No built-in rate limiting
- Token must be manually rotated

**Next Recommended Steps:**
1. Add WebSocket support for real-time updates
2. Implement token rotation mechanism
3. Add rate limiting for MCP endpoints
4. Create OpenCode-specific skill for analytics workflows

## Resume Point
- All documentation complete
- Ready to test integration with actual OpenCode instance
- Consider adding example Python client library for easier integration
