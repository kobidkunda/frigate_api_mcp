# 2026-03-28 - Fix app.js extra closing brace causing syntax error

## Summary
Browser console showed `Uncaught SyntaxError: Unexpected token '}'` in `app.js`, which prevented global functions like `loadHealth` and `syncCameras` from being defined. Fixed by removing an extra stray closing brace.

## Why
- The stray `}` after `pollJob()` made the script fail to parse, so none of the subsequent functions were registered on `window`.
- This led to follow-on errors: `loadHealth is not defined`, `syncCameras is not defined` when inline handlers ran.

## Scope
- Only `factory_analytics/static/app.js` edited to remove the extraneous `}`.
- No functional changes to logic.

## Changed files
- `factory_analytics/static/app.js` - removed a single extra `}` after `pollJob()`.

## Decisions
- Minimal change: fix syntax only, do not refactor surrounding code.

## Verification
- Static check: file now balances braces; script loads.
- Expected runtime result: dashboard loads without `Unexpected token '}'`; `loadHealth`, `syncCameras` available; inline `DOMContentLoaded` and button `onclick` handlers work.

## Risks / Follow-ups
- None; recommend quick smoke test of `/dashboard` to confirm no further console errors.

## Resume point
- If any additional console errors appear, capture them and revisit `factory_analytics/static/app.js` init paths.
