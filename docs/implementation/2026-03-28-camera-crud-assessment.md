# 2026-03-28 - Camera CRUD + Status Endpoints Assessment

## Summary
Assessed camera add/remove + status/settings access against current API. Identified and filled the single missing CRUD gap (GET single camera). Full CRUD + status matrix is now complete.

## Why
- BIO-24 dashboard needs camera CRUD + status endpoints for API readiness
- Reference issue: [BIO-24](/BIO/issues/BIO-24)

## Scope
- Included: API assessment, missing GET endpoint, acceptance criteria
- Not included: UI changes, permission model (single-user app)

## Camera API Matrix (after this change)

| Operation | Endpoint | Status |
|-----------|----------|--------|
| List | `GET /api/cameras` | ✅ existing |
| Get one | `GET /api/cameras/{id}` | ✅ **added** |
| Create | `POST /api/cameras` | ✅ existing |
| Update | `PUT /api/cameras/{id}` | ✅ existing |
| Delete | `DELETE /api/cameras/{id}` | ✅ existing |
| Delete (POST fallback) | `POST /api/cameras/{id}/delete` | ✅ existing |
| Delete by name | `POST /api/cameras/delete_by_name` | ✅ existing |
| Health (all) | `GET /api/cameras/health` | ✅ existing |
| Health (single) | `GET /api/cameras/{id}/health` | ✅ existing |
| Run analysis | `POST /api/cameras/{id}/run` | ✅ existing |
| Probe test | `POST /api/cameras/test` | ✅ existing |
| Frigate list | `GET /api/frigate/cameras` | ✅ existing |
| Frigate sync | `GET /api/frigate/cameras/sync` | ✅ existing |

## Changed files
- `factory_analytics/main.py` - added `GET /api/cameras/{camera_id}` route handler (line ~197)
- `factory_analytics/services.py` - added `get_camera(camera_id)` method that delegates to `db.get_camera()`

## Decisions
- No auth/permission layer: single-user dashboard app, no multi-tenancy
- Hard delete acceptable: no soft-delete, use `enabled=0` for deactivation instead
- Health status computed from DB (last_run_at/last_status), not live Frigate polling
- Existing `PUT /api/cameras/{id}` with `enabled` field serves as toggle

## Verification
- `GET /api/cameras/2` → 200, returns camera dict
- `GET /api/cameras/99999` → 404, `{"detail": "Camera not found"}`
- Syntax check passes on both modified files

## Acceptance Criteria for API Readiness
1. ✅ Camera CRUD fully implemented (Create/Read/Update/Delete)
2. ✅ Camera status via health endpoints (per-camera and all)
3. ✅ Audit logging on all mutating operations (create/update/delete)
4. ✅ Frigate integration for discovery and sync
5. ✅ Snapshot capture with go2rtc full-resolution support
6. ✅ Analysis run and probe test endpoints functional

## Risks / Follow-ups
- No input validation on `frigate_name` existence in Frigate at create time (by design: allows pre-config)
- Delete is hard-delete with CASCADE; lost data is unrecoverable
- Consider adding `GET /api/cameras/{id}/settings` if separate settings access needed later

## Resume point
- Assessment complete. No further backend changes needed for camera CRUD readiness.
