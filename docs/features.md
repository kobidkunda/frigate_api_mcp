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
  - Notes: Keyboard skip link and ARIA roles in place; high-contrast theme; initial charts and tables; resilient per-page JS init; favicon configured
  - Last updated: 2026-03-28

## Health API
- Feature: System/Frigate/Ollama health endpoints
  - Status: active
  - Paths: `factory_analytics/main.py`, `factory_analytics/services.py`, `factory_analytics/integrations/*`
  - Notes: Used by dashboard; db/audit wired
  - Last updated: 2026-03-28

## History
- Feature: Segment listing and review
  - Status: active
  - Paths: `factory_analytics/main.py`, `factory_analytics/database.py`, templates
  - Notes: Filters available; basic review actions
  - Last updated: 2026-03-28

## Cameras
- Feature: Camera management (add/edit/test/save)
  - Status: partial
  - Paths: `factory_analytics/main.py`, `factory_analytics/services.py`, `factory_analytics/static/app.js`, `factory_analytics/templates/dashboard.html`
  - Notes: Add from Frigate list with manual override; pre-save probe test and scheduled test; delete not yet implemented
  - Last updated: 2026-03-28

## Operations
- Feature: Service management script (API + MCP)
  - Status: active
  - Paths: `factory-analytics.sh`, `logs/*`, `run/*`
  - Notes: start/stop/restart/status/logs; debug-all writes pid files and cleans up; stop/status fall back to port scan if pid files missing
  - Last updated: 2026-03-28
