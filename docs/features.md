# Features

## Frontend
- Feature: Dashboard JS bootstrap and utilities
  - Status: active
  - Paths: `factory_analytics/static/app.js`, `factory_analytics/templates/*`
  - Notes: Fixed stray brace causing script parse failure; global functions restored (`loadHealth`, `syncCameras`, etc.)
  - Last updated: 2026-03-28

## UI/UX
- Feature: Baseline pages (Dashboard, Settings, History, Logs)
  - Status: active
  - Paths: `factory_analytics/templates/*`, `factory_analytics/static/*`
  - Notes: Updated using Stitch design system "Industrial Sentinel" with Tailwind CSS; Keyboard skip link and ARIA roles in place; high-contrast theme; initial charts and tables; resilient per-page JS init; favicon configured; Control Center and API Explorer pages added for config inspection and API catalog browsing
  - Last updated: 2026-03-29

## Health API
- Feature: System/Frigate/Ollama health endpoints
  - Status: active
  - Paths: `factory_analytics/main.py`, `factory_analytics/services.py`, `factory_analytics/integrations/*`
  - Notes: Used by dashboard and Control Center; db/audit wired
  - Last updated: 2026-03-28

## Control Center
- Feature: Read-only config and MCP/API monitoring page
  - Status: active
  - Paths: `factory_analytics/main.py`, `factory_analytics/control_center.py`, `factory_analytics/templates/control_center.html`, `factory_analytics/static/control_center.js`
  - Notes: Shows detected local config paths, masked previews, skill inventory, platform install instructions, and live API/Frigate/Ollama status
  - Last updated: 2026-03-28

## API Explorer
- Feature: Endpoint catalog and usage guidance page
  - Status: active
  - Paths: `factory_analytics/main.py`, `factory_analytics/control_center.py`, `factory_analytics/templates/api_explorer.html`, `factory_analytics/static/api_explorer.js`
  - Notes: Lists routes by group, exposes method/path/name metadata, and includes skill-usage guidance for safe endpoint interaction
  - Last updated: 2026-03-28

## History
- Feature: Segment listing and review
  - Status: active
  - Paths: `factory_analytics/main.py`, `factory_analytics/database.py`, templates
  - Notes: Filters available; basic review actions; History page shows larger inline evidence photos that open the full saved image on click; UI now includes LLM notes, merge metadata, and an explicit Group Result badge/name for persisted merged group records
  - Last updated: 2026-03-28

## Cameras
- Feature: Camera management (CRUD + health)
  - Status: active
  - Paths: `factory_analytics/main.py`, `factory_analytics/services.py`, `factory_analytics/database.py`, `factory_analytics/static/app.js`, `factory_analytics/templates/dashboard.html`
  - Notes: Full CRUD (list/get/create/update/delete); health endpoints (all + per-camera); Frigate sync and discovery; probe test and scheduled analysis; LLM/evidence capture uses go2rtc full-resolution frames
  - Last updated: 2026-03-28

## Operations
- Feature: Service management script (API + MCP)
  - Status: active
  - Paths: `factory-analytics.sh`, `logs/*`, `run/*`
  - Notes: start/stop/restart/status/logs; debug-all writes pid files and cleans up; stop/status fall back to port scan if pid files missing; debug now refuses to start if API/MCP ports are already occupied

## Worker
- Feature: Scheduler and analysis queue
  - Status: active
  - Paths: `factory_analytics/worker.py`, `factory_analytics/database.py`, `factory_analytics/services.py`
  - Notes: Scheduler now skips cameras that already have pending/running analysis jobs, preventing duplicate queue buildup during long-running or failing inference
  - Last updated: 2026-03-28

## Groups
- Feature: Camera groups and many-to-many membership
  - Status: partial
  - Paths: `factory_analytics/database.py`, `factory_analytics/services.py`, `factory_analytics/main.py`, `factory_analytics/static/app.js`, `factory_analytics/image_composition.py`
  - Notes: Supports group types such as machine and room; cameras can belong to multiple groups; preserves existing camera analytics; merged-scene group analysis available via API and dashboard actions; group merge includes grouped cameras even if standalone analysis is disabled, continues with available cameras when some snapshots fail, and persists group results into durable job/segment history records
  - Last updated: 2026-03-28

- Feature: Serial group processing with configurable intervals
  - Status: active
  - Paths: `factory_analytics/worker.py`, `factory_analytics/database.py`
  - Notes: Groups process serially (1 completely done → next starts); configurable interval_seconds per group; continuous loop with error recovery
  - Last updated: 2026-03-29

## Analytics Pages
- Feature: Processed Events and Charts pages
  - Status: partial
  - Paths: `factory_analytics/templates/processed_events.html`, `factory_analytics/static/processed_events.js`, `factory_analytics/templates/charts.html`, `factory_analytics/static/charts.js`, `factory_analytics/main.py`, `factory_analytics/database.py`
  - Notes: Server-side jobs/segments pagination with shift/date filters; processed segments UI now includes LLM notes, merge metadata, and explicit Group Result badge/name for persisted merged group records; charts include heatmap, shift summary, camera summary, failures, confidence distribution; group-aware extensions started
  - Last updated: 2026-03-28

  - Last updated: 2026-03-28
