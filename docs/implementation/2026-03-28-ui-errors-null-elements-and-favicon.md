# 2026-03-28 - UI Errors: Null Elements And Favicon

## Summary
Fix frontend runtime errors caused by querying DOM elements that are not present on all pages and address repeated 403s for `/favicon.ico` by adding a static icon and linking it from the base template. Also tightened the catch-all file route to explicitly allow only evidence files.

## Why
- Errors like `Cannot read properties of null (reading 'addEventListener')` and `Cannot set properties of null (setting 'innerHTML')` occurred because `app.js` unconditionally accessed elements that only exist on certain pages.
- Browser requested `/favicon.ico` and received 403 due to strict catch-all route. This caused noisy console errors on every navigation.
- Make security intent explicit in the file route: only serve `data/evidence/*` via catch-all; everything else forbidden.

## Scope
- Guard DOM access and event attachment in `app.js`; defer init until DOM is ready.
- Add `<link rel="icon">` and a favicon asset.
- Keep `/api/*` and `/static/*` untouched; only adjust the catch-all branch logic for clarity.

## Changed files
- `factory_analytics/static/app.js` - add presence checks, DOMContentLoaded init, selective task loading to avoid null derefs.
- `factory_analytics/templates/partials/base.html` - add `<link rel="icon" href="/static/favicon.ico">`.
- `factory_analytics/static/favicon.ico` - new file.
- `factory_analytics/main.py` - clarify catch-all handler: serve only evidence files; otherwise 403.

## Decisions
- Use lightweight guards around element lookups to avoid coupling pages; no SPA framework introduced.
- Keep alert-based error surfacing for now; console logging preserved.
- Serve favicon from `/static` to avoid expanding catch-all permissions.

## Verification
- Manual: Load `/dashboard`, `/settings`, `/history`, `/logs` and observe no `null` access errors; console free of favicon 403s.
- Confirm charts/tables render when respective containers present; settings form submits.
- Confirm navigating to `/favicon.ico` returns 200; navigating to non-evidence path like `/robots.txt` yields 403; navigating to valid `data/evidence/...` still works.
 - Trigger a job that captures a snapshot; if camera name does not exist on Frigate, error message now lists available cameras for faster diagnosis. Snapshot endpoints tried: `/api/{camera}/latest.jpg` then `/api/{camera}/snapshot.jpg`.

## Risks / Follow-ups
- Some pages have their own inline scripts; ensure no duplication with app.js event handlers (kept guards minimal to avoid double-binding).
- Consider replacing alert() with toast region in future.
- Add unit/e2e smoke tests for page JS init paths.

## Resume point
- If further UI errors arise, search for direct `document.getElementById(...).` chains and add guards or move to an init-per-page pattern.
