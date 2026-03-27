# 2026-03-28 - Group Analytics

## Summary
Add camera groups with many-to-many membership while preserving existing camera analytics and workflows.

## Why
- Users need analytics at machine and room level, not only per camera.
- A worker may move across multiple cameras in the same room or machine area.

## Scope
- Included: group model, camera-group membership, API endpoints, merged-scene group inference endpoint, dashboard group actions, processed-events/charts groundwork, initial docs updates.
- Not included yet: full group rollups, final MCP bridge tool surface, full OpenClaw skill updates outside repo docs.

## Changed files
- `factory_analytics/database.py` - add groups and camera_groups tables plus helpers
- `factory_analytics/services.py` - add group service methods
- `factory_analytics/main.py` - add groups API endpoints
- `factory_analytics/image_composition.py` - merge multi-camera snapshots into one scene
- `factory_analytics/static/app.js` - add group management and run-group UI actions
- `factory_analytics/templates/dashboard.html` - add Groups section
- `factory_analytics/templates/processed_events.html` - add processed events page shell
- `factory_analytics/static/processed_events.js` - add server-side processed events loader
- `factory_analytics/templates/charts.html` - add charts page shell
- `factory_analytics/static/charts.js` - add heatmap and analytics renderers
- `docs/todos.md` - update in-progress task
- `docs/features.md` - record group analytics capability
- `README.md` - add group analytics and MCP/OpenClaw guidance

## Decisions
- Keep existing camera analytics unchanged.
- Use many-to-many mapping so one camera can belong to multiple groups.

## Verification
- Focused API and DB tests for group create/list/membership.

## Risks / Follow-ups
- Group-level inference currently returns direct analysis output but is not yet persisted into dedicated group segments/rollups.
- Group-aware metrics and charts are partially wired and need final rollup integration.
- MCP/OpenClaw docs are updated in README, but repo-specific skill/docs files may need more detailed follow-up.

## Resume point
- Next: persist group analysis into dedicated entities/rollups and expand processed-events/charts to first-class group summaries.
