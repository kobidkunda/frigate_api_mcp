Best design now is:

**one core analytics app + one HTTP MCP server + one GUI + one SQLite DB + one OpenClaw skill package.**

I would **not** build separate integrations three different ways. Build **one shared MCP server** for your factory analytics app, then connect that same MCP server to **Claude Code**, **Codex**, and **OpenClaw**. That is the lowest-maintenance route. Claude Code recommends remote **HTTP** MCP servers and marks SSE as deprecated, while Codex supports both **STDIO** and **streamable HTTP** MCP servers with bearer/OAuth support. OpenClaw supports MCP through **mcporter**, and OpenClaw skills are separate `SKILL.md`-based packages that can live in workspace or user skill directories. ([Claude API Docs][1])

## Recommended product shape

### Core services

1. **App API**

   * serves the GUI
   * exposes REST API
   * stores settings in SQLite
   * stores analysis history
   * exposes chart/report endpoints

2. **Analysis worker**

   * polls Frigate
   * fetches review items/events/recording snapshots
   * calls Ollama vision model
   * writes results into SQLite
   * builds rollups

3. **MCP server**

   * exposes tools for agents
   * read-only tools for reports/history
   * admin tools for reruns/backfills/settings
   * used by Claude Code, Codex, OpenClaw

4. **SQLite**

   * source of truth for settings, jobs, rollups, logs index, audit, human corrections

5. **File storage**

   * evidence snapshots
   * clip references
   * generated reports
   * exported CSV/JSON/markdown

6. **Optional notifier**

   * Telegram / email / webhook / MQTT publishing

Frigate gives you the upstream camera/event/media/auth surface you need: authenticated API on port `8971`, HTTP API sections for Auth, Review, App, Logs, Preview, Export, Events, Media, and metrics at `/api/metrics`. Frigate recordings are stored in UTC, so your app should keep UTC internally and apply timezone only in display/reporting. Ollama’s default API base is `http://localhost:11434/api`, and model enumeration is via `GET /api/tags`. ([Frigate][2])

## Complete feature list

### 1) System module

* app health
* Frigate health
* Ollama health
* SQLite health
* worker heartbeat
* MCP server health
* disk usage
* queue depth
* last successful analysis time
* version info
* uptime
* environment summary
* timezone
* current shift

### 2) Frigate integration module

* Frigate base URL
* auth mode
* login test
* token refresh test
* fetch cameras
* fetch review items
* fetch events
* fetch latest frame
* fetch recording snapshot by timestamp
* fetch event snapshot
* preview/clip links
* Frigate logs passthrough
* Frigate metrics passthrough
* Frigate config snapshot import view
* per-camera online/offline state
* camera detect/record state
* MQTT topic visibility

Frigate supports review/history, event listing, event snapshots, recording snapshots, saved snapshots, logs, and Prometheus metrics. MQTT can also publish object counts and other state topics. ([Frigate][3])

### 3) Ollama/model module

* Ollama base URL
* list installed models
* vision model name
* optional report-summary model name
* optional embeddings model name later
* model connection test
* image prompt test
* JSON output test
* timeout
* temperature
* context window
* max frames per segment
* fallback model
* retry rules
* model warmup button

Ollama’s HTTP API is stable and model discovery is built in through `/api/tags`. ([Ollama Documentation][4])

### 4) Camera module

* list cameras from Frigate
* enable/disable analytics per camera
* camera nickname
* camera tags
* per-camera schedule
* per-camera timezone override
* camera health badge
* last detection time
* last analysis time
* current live preview
* manual analyze now
* pause camera
* maintenance mode
* camera role:

  * worker monitoring
  * machine state
  * entry/exit
  * mixed

### 5) Zone module

* work zones
* rest zones
* sleep-suspect zones
* machine zones
* sealing/stopped zones
* ignore zones
* zone masks
* zone notes
* per-zone alert thresholds

### 6) Analysis rules module

* global run interval
* per-camera run interval
* use review items only
* use events only
* use scheduled snapshot sampling
* segment merge gap
* minimum duration to classify
* sleep threshold
* idle threshold
* uncertain threshold
* max retries
* confidence threshold
* human-review-required threshold
* ignore short segments
* day shift/night shift split

### 7) History module

* all runs
* all classified segments
* filter by date
* filter by camera
* filter by label
* filter by confidence
* filter by shift
* filter by operator zone
* filter by uncertain/failed
* raw model result
* corrected label
* evidence paths
* rerun incident
* exclude incident
* notes/comments

### 8) Charts/analytics module

* daily working minutes
* daily idle minutes
* daily sleeping minutes
* daily presence minutes
* daily sealed/stopped minutes
* camera-wise comparison
* shift-wise comparison
* hourly heatmap
* weekly trend
* monthly trend
* top problem cameras
* longest idle segment
* longest sleeping segment
* uncertainty trend
* failure trend
* processing-time trend

### 9) Reports module

* daily report
* weekly report
* monthly report
* per-camera report
* per-shift report
* exception-only report
* markdown output
* JSON output
* CSV export
* evidence bundle export
* API delivery
* Telegram/email/webhook delivery
* report template versions

### 10) Logs module

* app logs
* worker logs
* scheduler logs
* MCP logs
* Frigate API request logs
* Ollama request logs
* report logs
* notification logs
* cleanup logs
* audit logs
* searchable logs
* tail/live view
* download logs

### 11) Human review module

* uncertain queue
* low-confidence sleep queue
* approve/reject label
* relabel segment
* add note
* mark false positive
* exclude from rollup
* lock segment
* reviewer name/time
* export corrected dataset

### 12) Settings module

* app host
* app port
* MCP host
* MCP port
* public base URL
* timezone
* storage paths
* retention days
* log level
* secret values
* auth policy
* default schedule
* default prompt
* SMTP/webhook/Telegram config
* backup path
* startup mode

### 13) Security/admin module

* local login
* API keys
* MCP bearer token
* read-only vs admin tools
* audit trail
* secret masking
* token rotation
* role-based access
* backup/restore
* maintenance mode
* IP allowlist later

## API groups you should expose

Make the GUI consume only these APIs.

* `/api/health/*`
* `/api/settings/*`
* `/api/system/*`
* `/api/frigate/*`
* `/api/ollama/*`
* `/api/cameras/*`
* `/api/zones/*`
* `/api/rules/*`
* `/api/runs/*`
* `/api/history/*`
* `/api/charts/*`
* `/api/reports/*`
* `/api/evidence/*`
* `/api/logs/*`
* `/api/review/*`
* `/api/notifications/*`
* `/api/mcp/*`
* `/api/admin/*`

## MCP layer design

### Why one MCP server

Use one **remote HTTP MCP server** for everything. Claude Code explicitly recommends HTTP for remote servers, and Codex supports streamable HTTP servers with auth headers/bearer env vars. ([Claude API Docs][1])

### MCP tool groups

Create these MCP tools:

**Read-only**

* `system_health`
* `camera_list`
* `camera_status`
* `run_list`
* `run_get`
* `history_search`
* `segment_get`
* `chart_daily`
* `chart_weekly`
* `report_get_daily`
* `report_get_weekly`
* `report_get_monthly`
* `evidence_get`
* `logs_tail`
* `frigate_health`
* `ollama_health`

**Operator**

* `run_analysis_now`
* `run_backfill`
* `rerun_segment`
* `generate_report`
* `acknowledge_alert`
* `mark_false_positive`
* `set_camera_enabled`

**Admin**

* `settings_get`
* `settings_update`
* `prompt_get`
* `prompt_update`
* `retention_run_cleanup`
* `system_restart_worker`
* `system_pause_scheduler`
* `system_resume_scheduler`

### MCP security

* one read-only token
* one operator token
* one admin token
* tool allowlists per token
* per-tool audit log
* per-client rate limit
* redact secrets in tool outputs

## Claude Code integration

Claude Code supports HTTP, SSE, and stdio MCP, but recommends **HTTP** for remote servers; project-scoped MCP lives in `.mcp.json`, while user/local scope lives in `~/.claude.json`. ([Claude API Docs][1])

Use this project-level config:

```json
{
  "mcpServers": {
    "factory-analytics": {
      "url": "http://127.0.0.1:8099/mcp",
      "headers": {
        "Authorization": "Bearer ${FACTORY_ANALYTICS_MCP_TOKEN}"
      }
    }
  }
}
```

Or add it with CLI:

```bash
claude mcp add --transport http factory-analytics --scope project \
  http://127.0.0.1:8099/mcp \
  --header "Authorization: Bearer ${FACTORY_ANALYTICS_MCP_TOKEN}"
```

### Claude Code feature fit

* code against your analytics API
* inspect logs
* request daily report
* debug bad classifications
* generate migration-free schema changes
* review prompt changes
* verify worker logic

## Codex integration

Codex supports MCP in both CLI and IDE extension, stores config in `~/.codex/config.toml` or project `.codex/config.toml`, and supports both stdio and streamable HTTP servers with bearer tokens and OAuth. ([OpenAI Developers][5])

Use this config:

```toml
[mcp_servers.factoryAnalytics]
url = "http://127.0.0.1:8099/mcp"
bearer_token_env_var = "FACTORY_ANALYTICS_MCP_TOKEN"
startup_timeout_sec = 20
tool_timeout_sec = 120
enabled = true
required = false
```

### Codex feature fit

* inspect API schema
* review implementation tasks
* build report templates
* troubleshoot analysis failures
* write tests against real endpoints
* run codebase changes using the same analytics tools

Optional later: Codex itself can also run as an MCP server via `codex mcp-server`, but that is a separate advanced workflow and not needed for your first version. ([OpenAI Developers][6])

## OpenClaw integration

OpenClaw skills are `SKILL.md`-based folders, loaded from bundled skills, `~/.openclaw/skills`, and `<workspace>/skills`, with workspace skills taking precedence. OpenClaw plugins extend tools, model providers, channels, skills, speech, image generation, and more. OpenClaw’s current MCP direction is through **mcporter**, specifically to keep MCP flexible and decoupled from core. ([GitHub][7])

### What to add for OpenClaw

Add **two things**:

#### A) one OpenClaw skill

Create a workspace skill, for example:

`<workspace>/skills/factory-analytics/SKILL.md`

Purpose:

* teach OpenClaw when to call the MCP tools
* define slash commands
* define preferred report flows
* define escalation format
* define incident-summary format

Suggested slash commands:

* `/factory-report today`
* `/factory-report week`
* `/factory-camera-health`
* `/factory-idle-top`
* `/factory-sleep-alerts`
* `/factory-rerun <segment_id>`
* `/factory-backfill <camera> <from> <to>`

#### B) one OpenClaw MCP bridge entry

Use your MCP server through mcporter/OpenClaw MCP config so the agent can call the analytics tools without custom logic in every workflow. That keeps the data plane centralized. ([GitHub][8])

### Optional OpenClaw plugin

Only build a plugin if you want:

* channel posting
* scheduled Telegram pushes from OpenClaw itself
* richer in-gateway UI
* custom channel tools
* tight auth/session handling in OpenClaw

Plugins are installable from npm or local archives and typically require gateway restart after install/config change. ([OpenClaw][9])

## What connects to what

### Upstream

* **Frigate** → cameras, review items, events, snapshots, media, metrics, logs
* **Ollama** → image classification and summaries

### Core

* **Analysis worker** pulls from Frigate, calls Ollama, writes SQLite
* **App API** reads SQLite and file storage, serves GUI and REST
* **MCP server** calls the same internal service layer as the REST API
* **Scheduler** triggers analysis/backfills/reports
* **Report engine** creates JSON/markdown/CSV

### Agent side

* **Claude Code** → remote HTTP MCP
* **Codex** → remote HTTP MCP
* **OpenClaw** → mcporter/MCP bridge + skill instructions

This is the key rule:

**REST API and MCP tools must hit the same internal service methods.**
No duplicate business logic.

## Detailed implementation plan

### Phase 1 — foundation

1. create repo structure
2. add `.env`
3. add SQLite schema
4. add file storage folders
5. add backend app
6. add settings endpoints
7. add health endpoints
8. add Frigate connection test
9. add Ollama connection test
10. add camera sync

### Phase 2 — analysis core

11. add job table
12. add segment table
13. add daily/weekly/monthly rollups
14. add worker process
15. add scheduler
16. add Frigate review/event fetcher
17. add recording snapshot fetch
18. add Ollama classifier call
19. add structured JSON parser
20. add evidence storage
21. add retry/failure handling

### Phase 3 — GUI

22. add dashboard
23. add settings screen
24. add camera screen
25. add rules screen
26. add history screen
27. add logs screen
28. add charts screen
29. add report screen
30. add human review queue

### Phase 4 — MCP

31. add MCP server
32. expose read-only tools
33. expose operator tools
34. add bearer auth
35. add per-tool audit log
36. add tool allowlists
37. test with Claude Code
38. test with Codex
39. test with OpenClaw

### Phase 5 — OpenClaw package

40. create `factory-analytics` skill
41. add slash commands
42. add skill instructions for reports/incidents
43. add optional plugin only if needed
44. add workspace install docs

### Phase 6 — reporting

45. add daily/weekly/monthly report generation
46. add markdown + JSON + CSV export
47. add webhook/Telegram/email adapters
48. add evidence bundle export
49. add timezone-aware report windows

### Phase 7 — hardening

50. add backup/restore
51. add retention cleanup
52. add config export/import
53. add rate limits
54. add audit views
55. add low-confidence review queue
56. add camera maintenance mode
57. add shift calendars
58. add role-based auth

## Suggested repo layout

```text
factory-analytics/
  app/
    api/
    services/
    workers/
    mcp/
    db/
    models/
    reports/
    integrations/
      frigate/
      ollama/
    web/                # built frontend assets
  frontend/             # source frontend
  skills/
    factory-analytics/
      SKILL.md
  data/
    db/
      factory_analytics.db
    evidence/
      snapshots/
      clips/
    reports/
      daily/
      weekly/
      monthly/
    backups/
  logs/
  run/
  scripts/
  .env
  factory-analytics.sh
```

## Suggested SQLite tables

* `settings`
* `cameras`
* `zones`
* `rules`
* `jobs`
* `job_logs`
* `segments`
* `segment_evidence`
* `segment_reviews`
* `daily_rollups`
* `weekly_rollups`
* `monthly_rollups`
* `reports`
* `alerts`
* `audit_log`
* `mcp_clients`
* `mcp_audit`

## Environment variables

```bash
APP_HOST=0.0.0.0
APP_PORT=8090
MCP_HOST=0.0.0.0
MCP_PORT=8099
PUBLIC_BASE_URL=http://127.0.0.1:8090

SQLITE_PATH=./data/db/factory_analytics.db
DATA_ROOT=./data
LOG_ROOT=./logs
RUN_ROOT=./run
TIMEZONE=Asia/Kolkata

FRIGATE_URL=https://frigate.local:8971
FRIGATE_USERNAME=admin
FRIGATE_PASSWORD=change_me
FRIGATE_VERIFY_TLS=false

OLLAMA_URL=http://127.0.0.1:11434/api
OLLAMA_VISION_MODEL=qwen2.5-vl:7b
OLLAMA_SUMMARY_MODEL=qwen3:8b
OLLAMA_TIMEOUT_SEC=120

FACTORY_ANALYTICS_MCP_TOKEN=change_this_long_secret
APP_LOG_LEVEL=INFO
```

## Single-file start/stop/restart script

I recommend production mode where the backend serves the built GUI statically. Then one script only has to manage:

* API
* worker
* MCP server

Run it like:

* `./factory-analytics.sh start`
* `./factory-analytics.sh stop`
* `./factory-analytics.sh restart`
* `./factory-analytics.sh status`
* `./factory-analytics.sh logs`

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${BASE_DIR}/run"
LOG_DIR="${BASE_DIR}/logs"

API_PID_FILE="${RUN_DIR}/api.pid"
WORKER_PID_FILE="${RUN_DIR}/worker.pid"
MCP_PID_FILE="${RUN_DIR}/mcp.pid"

mkdir -p "${RUN_DIR}" "${LOG_DIR}"

load_env() {
  if [ -f "${BASE_DIR}/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "${BASE_DIR}/.env"
    set +a
  fi

  : "${APP_HOST:=0.0.0.0}"
  : "${APP_PORT:=8090}"
  : "${MCP_HOST:=0.0.0.0}"
  : "${MCP_PORT:=8099}"
  : "${APP_LOG_LEVEL:=INFO}"
}

is_running() {
  local pid_file="$1"
  if [ -f "${pid_file}" ]; then
    local pid
    pid="$(cat "${pid_file}")"
    if kill -0 "${pid}" >/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

start_api() {
  if is_running "${API_PID_FILE}"; then
    echo "API already running"
    return
  fi

  nohup bash -lc "
    cd '${BASE_DIR}' &&
    ./.venv/bin/uvicorn app.main:app \
      --host '${APP_HOST}' \
      --port '${APP_PORT}' \
      --log-level '$(echo "${APP_LOG_LEVEL}" | tr '[:upper:]' '[:lower:]')'
  " >> "${LOG_DIR}/api.log" 2>&1 &

  echo $! > "${API_PID_FILE}"
  echo "Started API on ${APP_HOST}:${APP_PORT}"
}

start_worker() {
  if is_running "${WORKER_PID_FILE}"; then
    echo "Worker already running"
    return
  fi

  nohup bash -lc "
    cd '${BASE_DIR}' &&
    ./.venv/bin/python -m app.workers.main
  " >> "${LOG_DIR}/worker.log" 2>&1 &

  echo $! > "${WORKER_PID_FILE}"
  echo "Started worker"
}

start_mcp() {
  if is_running "${MCP_PID_FILE}"; then
    echo "MCP already running"
    return
  fi

  nohup bash -lc "
    cd '${BASE_DIR}' &&
    ./.venv/bin/python -m app.mcp.server \
      --host '${MCP_HOST}' \
      --port '${MCP_PORT}'
  " >> "${LOG_DIR}/mcp.log" 2>&1 &

  echo $! > "${MCP_PID_FILE}"
  echo "Started MCP on ${MCP_HOST}:${MCP_PORT}"
}

stop_one() {
  local pid_file="$1"
  local name="$2"

  if is_running "${pid_file}"; then
    local pid
    pid="$(cat "${pid_file}")"
    kill "${pid}" >/dev/null 2>&1 || true

    for _ in {1..20}; do
      if kill -0 "${pid}" >/dev/null 2>&1; then
        sleep 0.5
      else
        break
      fi
    done

    if kill -0 "${pid}" >/dev/null 2>&1; then
      kill -9 "${pid}" >/dev/null 2>&1 || true
    fi

    rm -f "${pid_file}"
    echo "Stopped ${name}"
  else
    rm -f "${pid_file}"
    echo "${name} not running"
  fi
}

status_one() {
  local pid_file="$1"
  local name="$2"
  if is_running "${pid_file}"; then
    echo "${name}: RUNNING (pid $(cat "${pid_file}"))"
  else
    echo "${name}: STOPPED"
  fi
}

logs() {
  touch "${LOG_DIR}/api.log" "${LOG_DIR}/worker.log" "${LOG_DIR}/mcp.log"
  tail -n 100 -f "${LOG_DIR}/api.log" "${LOG_DIR}/worker.log" "${LOG_DIR}/mcp.log"
}

main() {
  load_env

  case "${1:-}" in
    start)
      start_api
      start_worker
      start_mcp
      ;;
    stop)
      stop_mcp
      stop_worker
      stop_api
      ;;
    restart)
      stop_mcp || true
      stop_worker || true
      stop_api || true
      start_api
      start_worker
      start_mcp
      ;;
    status)
      status_one "${API_PID_FILE}" "API"
      status_one "${WORKER_PID_FILE}" "WORKER"
      status_one "${MCP_PID_FILE}" "MCP"
      ;;
    logs)
      logs
      ;;
    *)
      echo "Usage: $0 {start|stop|restart|status|logs}"
      exit 1
      ;;
  esac
}

stop_api() { stop_one "${API_PID_FILE}" "API"; }
stop_worker() { stop_one "${WORKER_PID_FILE}" "WORKER"; }
stop_mcp() { stop_one "${MCP_PID_FILE}" "MCP"; }

main "$@"
```

After saving it:

```bash
chmod +x factory-analytics.sh
./factory-analytics.sh start
```

## Final recommendation

Build these three integration layers from day one:

1. **REST API**
2. **HTTP MCP server**
3. **OpenClaw skill**

Do **not** start with an OpenClaw plugin unless you specifically need channel-native posting or deep gateway behavior.
Do **not** build separate Codex and Claude-specific backends.
Use **one MCP server** and **one service layer** behind it.

The most important additions beyond what you asked for are:

* human review queue
* per-tool MCP permissions
* audit logging
* backfill jobs
* prompt versioning
* shift/calendar support
* evidence export
* config backup/restore

## UI/UX Baseline (Added)

### Navigation
- Top-level sections mirror APIs: Dashboard, Settings, Cameras, Zones, Rules, History, Charts, Reports, Logs, Review, System, Admin.
- Left rail for section navigation; contextual secondary tabs within each section.
- Global header: app switcher (future), search, timezone badge, current shift, user menu.

### Layout Patterns
- Dashboard: responsive card grid (2-4 columns desktop, 1 column mobile), cards with headline metric, sparkline, trend delta.
- Data explorers (History/Logs): left filter panel (collapsible on mobile), right results pane with sticky table header, infinite scroll + server-side pagination.
- Forms (Settings/Rules): two-column forms on desktop, single column on mobile; inline validation with helper text.
- Panels: slide-over drawer for detail views (segment details, camera status) to preserve context.

### States & Feedback
- States: loading skeletons, empty (explain + CTA), error (actionable retry), partial (badge + tooltip), success (subtle toast).
- Long tasks: non-blocking toasts with progress and background job id; link to job detail in Logs.

### Visual Tokens
- Typography: `--font-sans` (workhorse, readable), `--font-mono` for data; 14/16/20/24 scale with 1.4 line-height.
- Color: `--bg`, `--surface`, `--text`, `--muted`, `--primary`, `--success`, `--warning`, `--danger`; WCAG AA contrast min.
- Spacing: 4px base grid; container max width 1280px.

### Components
- Core: AppShell, NavRail, PageHeader (title, actions, breadcrumbs).
- Inputs: Select, Combobox (async), Toggle, Range, DateRangePicker (TZ-aware), KeyValue editor (for env-like lists).
- Data: Table (resizable columns, column presets), StatCard, TrendChart, Heatmap, Badge, Tag, LogViewer (virtualized).
- Review: SegmentTimeline, EvidenceGallery (image/clip), LabelConfidenceBar, ActionBar (approve/relabel/exclude/note).

### Accessibility
- Keyboard-first navigation; visible focus; skip-to-content.
- ARIA roles for navigation, tables, dialogs; announce live updates for long tasks.
- Color-contrast AA; avoid color-only status; size min 44x44 targets.

### Performance
- Performance budgets: first meaningful paint <1.5s on desktop; <2.5s on mobile; bundle split by route.
- Lazy-load heavy charts; virtualize long lists; cache filters in URL.

### Internationalization & Time
- Keep UTC internally; display with user TZ badge; per-camera TZ override reflected in UI labels/tooltips.

### Empty State Templates
- History empty: "No segments match your filters" + Clear Filters + Learn Filters link.
- Reports empty: explain schedule and include "Generate now" button.

### Error Handling
- Friendly messages mapped from API error codes; include correlation id; copy-to-clipboard for support.

### Admin Safeguards
- Destructive actions require typed confirmation; role badges in header; secrets masked with reveal on press + audit.

### Charts Defaults
- Daily/weekly/monthly rollups default to stacked presence/idle/sleep; camera comparison uses ordered bar chart; uncertainty trend as area with threshold line.

### Mobile
- Bottom tab bar mirrors top sections; drawers replace side panels; sticky action bar for Review flows.
