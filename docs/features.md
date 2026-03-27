# Features

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

## Groups
- Feature: Camera groups and many-to-many membership
  - Status: partial
  - Paths: `factory_analytics/database.py`, `factory_analytics/services.py`, `factory_analytics/main.py`, `factory_analytics/static/app.js`, `factory_analytics/image_composition.py`
  - Notes: Supports group types such as machine and room; cameras can belong to multiple groups; preserves existing camera analytics; merged-scene group analysis available via API and dashboard actions
  - Last updated: 2026-03-28

## Analytics Pages
- Feature: Processed Events and Charts pages
  - Status: partial
  - Paths: `factory_analytics/templates/processed_events.html`, `factory_analytics/static/processed_events.js`, `factory_analytics/templates/charts.html`, `factory_analytics/static/charts.js`, `factory_analytics/main.py`, `factory_analytics/database.py`
  - Notes: Server-side jobs/segments pagination with shift/date filters; charts include heatmap, shift summary, camera summary, failures, confidence distribution; group-aware extensions started
  - Last updated: 2026-03-28
