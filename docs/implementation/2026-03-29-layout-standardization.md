# Implementation Plan - Layout Architecture Standardization

Fix viewport overflow issues by standardizing layout classes in `base.html` and removing redundant layout logic from child templates.

## User Requirements
- Review layout architecture in `base.html`, `sidebar.html`, and `top_nav.html`.
- Standardize margins and widths for the main content area.
- Ensure child templates don't specify their own side margins.
- Ensure "History" table handles horizontal overflow gracefully.

## Proposed Changes

### 1. `factory_analytics/templates/partials/base.html`
- Maintain the authoritative layout definition.
- Current: `<main id="main" class="flex-1 p-4 md:p-8 space-y-8 md:ml-64" role="main">`
- This is the source of truth for margins/padding.

### 2. `factory_analytics/templates/history.html`
- Remove redundant `<main class="flex-1 ml-64 p-8 bg-surface-dim">`.
- Move `bg-surface-dim` to a wrapper if needed, or apply to `base.html` main if appropriate.
- Verify `overflow-x-auto` on the table container.

### 3. `factory_analytics/templates/logs.html`
- Remove redundant `<main class="flex-1 p-8 bg-surface-dim">`.

### 4. `factory_analytics/templates/dashboard.html`
- Ensure it relies on `base.html` for layout.

### 5. `factory_analytics/templates/settings.html`
- Ensure it relies on `base.html` for layout.

### 6. `factory_analytics/templates/control_center.html` & `api_explorer.html`
- Check for similar redundant tags.

## Verification Plan
- Manual inspection of templates.
- (In a real scenario, I'd use the browser tool to verify layout, but here I'll rely on code analysis).
