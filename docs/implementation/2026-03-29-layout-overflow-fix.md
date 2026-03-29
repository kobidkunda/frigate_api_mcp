# 2026-03-29 - Layout and Viewport Overflow Fix

## Summary
Audit and fix layout issues where redundant `<main>` tags and conflicting margin classes in templates were causing viewport overflow.

## Why
- Redundant `<main>` tags nested inside the primary `<main>` in `base.html` were doubling padding/margins.
- Hardcoded `ml-64` in sub-templates conflicted with `md:ml-64` in `base.html`, leading to layout breakage on smaller viewports and double offsetting on desktop.
- User reported "History" and "Groups" pages are overflowing to the right.

## Scope
- Audit templates: `dashboard.html`, `settings.html`, `history.html`, `groups.html`, `logs.html`, `control_center.html`, `api_explorer.html`, `charts.html`, `processed_events.html`.
- Remove redundant `<main>` tags in `{% block content %}`.
- Remove redundant margin classes like `ml-64` or `md:ml-64`.
- Ensure consistency with "Industrial Sentinel" design system.
- Verify table responsiveness.

## Changed files
- `factory_analytics/templates/history.html`
- `factory_analytics/templates/groups.html`
- `factory_analytics/templates/api_explorer.html`
- `factory_analytics/templates/charts.html`
- `factory_analytics/templates/control_center.html`
- `factory_analytics/templates/logs.html`
- `factory_analytics/templates/processed_events.html`

## Decisions
- Keep `base.html` as the single source of truth for the primary `<main>` layout container.
- Sub-templates should only contain the internal content structure.
- Use `overflow-x-auto` on table wrappers to handle wide tables gracefully.

## Verification
- Manual audit of all templates.
- Check for nested `<main>` tags.
- Check for viewport overflow indicators.

## Risks / Follow-ups
- Some pages might rely on the extra padding/bg-color from the redundant `<main>`. These will be moved to a wrapping `div` if needed, but preferably integrated into the design.

## Resume point
- Apply edits to all identified templates.
