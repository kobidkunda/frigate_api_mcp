# Factory Analytics App

A practical starter app for factory camera analytics built around:
- Frigate as the video/event layer
- Ollama as the local vision-model layer
- SQLite as the reporting database
- FastAPI for REST + admin GUI
- a lightweight HTTP MCP bridge for OpenClaw / Codex / Claude Code

## What is included
- Settings UI for Frigate, Ollama, timezone, intervals
- Camera sync from Frigate and camera enable/disable
- Health checks for Frigate / Ollama / app / database / worker
- Manual analysis runs and scheduled recurring runs
- SQLite-backed jobs, segments, rollups, reports, review queue, audit log
- History, charts, logs, and daily reports in a simple GUI
- OpenClaw `SKILL.md`
- single-file `factory-analytics.sh` start/stop/restart/status/logs control
- example Claude Code / Codex MCP configs

## Important note
This is a working starter app designed to be extended in your environment.
It includes real integrations for Frigate and Ollama, but you will likely want to:
- tighten Frigate auth handling for your exact setup
- refine the classification prompt and labels
- adjust snapshot endpoints to your Frigate version if needed
- harden the lightweight MCP bridge into a stricter MCP implementation later if desired

## Quick start
```bash
cp .env.example .env
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
./factory-analytics.sh start
```

Open:
- GUI: `http://127.0.0.1:8090`
- API docs: `http://127.0.0.1:8090/docs`
- MCP bridge: `http://127.0.0.1:8099/mcp`

## Process control
```bash
./factory-analytics.sh start, debug
./factory-analytics.sh stop
./factory-analytics.sh restart
./factory-analytics.sh status
./factory-analytics.sh logs
```

## Claude Code MCP example
Create `.mcp.json` in your project:
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

## Codex MCP example
Add to `~/.codex/config.toml` or `.codex/config.toml`:
```toml
[mcp_servers.factoryAnalytics]
url = "http://127.0.0.1:8099/mcp"
bearer_token_env_var = "MCP_TOKEN"
startup_timeout_sec = 20
tool_timeout_sec = 120
enabled = true
required = false
```

## OpenClaw
Copy `skills/factory-analytics/` into your workspace `skills/` directory or `~/.openclaw/skills/`.
Point OpenClaw's MCP bridge or mcporter config at `http://127.0.0.1:8099/mcp`.
