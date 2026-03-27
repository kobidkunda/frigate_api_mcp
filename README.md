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
- Camera groups (`machine`, `room`, etc.) with many-to-many membership
- Health checks for Frigate / Ollama / app / database / worker
- Manual analysis runs and scheduled recurring runs
- SQLite-backed jobs, segments, rollups, reports, review queue, audit log
- History, processed-events, charts, logs, and daily reports in a simple GUI
- Group-level merged-scene analysis in addition to camera-level analysis
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

## Group analytics
- Cameras can belong to multiple groups, such as:
  - `machine / machine 1`
  - `room / room 1 factory`
- Existing camera analytics remain unchanged.
- Group analysis captures snapshots from all cameras in a group, merges them into one composite image, and runs the configured LLM over the merged scene.
- Duration analysis is intended to support labels such as `working`, `idle`, `sleeping`, `timepass`, and `operator_missing`.

## MCP / OpenClaw guidance
- Keep old camera-level tools and queries.
- Add group-aware tools/queries for:
  - listing groups
  - listing cameras in a group
  - group-level processed events
  - group duration summaries
  - machine/room heatmaps and shift summaries
- OpenClaw instructions should prefer group-level queries when the user asks about machine-wide or room-wide behavior.
