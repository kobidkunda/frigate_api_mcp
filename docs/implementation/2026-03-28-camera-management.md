# 2026-03-28 - Camera Management

## Summary
Add explicit camera add/edit/test/save capabilities. UI form supports Frigate list with manual override. API adds create and probe endpoints.

## Why
- Users need to add cameras without relying solely on bulk sync
- Clear Test action improves setup confidence

## Scope
- Included: endpoints, service helpers, UI form, button label adjustments
- Not included: delete camera, bulk ops, advanced metadata

## Changed files
- `factory_analytics/main.py` - added `/api/frigate/cameras`, POST `/api/cameras`, POST `/api/cameras/test`, models
- `factory_analytics/services.py` - `create_camera`, `probe_analysis`
- `factory_analytics/static/app.js` - add form, load list, add/test camera, rename actions
- `factory_analytics/templates/dashboard.html` - section remains, populated by app.js
- `docs/plans/2026-03-28-camera-management-design.md` - added implementation plan
- `docs/todos.md` - in-progress item

## Decisions
- Provide both discovery dropdown and manual override for resilience
- Non-persistent probe endpoint avoids side effects for quick tests

## Verification
- Manual: add via dropdown; add via manual; run Test (probe) and Test (scheduled)
- Logs show `camera.create` and `camera.update` audit entries

## Risks / Follow-ups
- Frigate availability affects dropdown; handled with fallback option label
- Consider add camera delete endpoint and UI later

## Resume point
- If tests or UI wiring fail, re-run `refreshAll()` and check network console for `/api/cameras/test` and `/api/cameras` responses
