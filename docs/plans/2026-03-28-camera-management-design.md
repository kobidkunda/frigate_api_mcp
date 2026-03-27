# 2026-03-28 - Camera Management (Add/Edit/Test/Save) Design

## Summary
Introduce explicit camera management in the UI and API: add new cameras (from Frigate list with manual override), edit existing, and test connectivity/inference before or after saving.

## UX
- Add Camera form above the Cameras table:
  - Fields: Frigate Camera (dropdown from discovery), Manual Frigate Name (optional), Display Name (optional), Enabled (default true), Interval (sec).
  - Buttons: Test (pre-save probe) and Add Camera.
- In table rows rename actions: `Save` → `Save Camera`, `Run now` → `Test`.
- Helper text: “Use Test to verify connectivity before saving.”

## API
- GET `/api/frigate/cameras` → list of frigate camera names; no DB writes.
- POST `/api/cameras` → create/upsert camera from provided fields; returns camera.
- POST `/api/cameras/test` → probe by `camera_id` or `frigate_name`; returns `{ ok, label, confidence }` without DB side effects.
- Keep POST `/api/cameras/{id}/run` for scheduled test.

## Services/DB
- `create_camera` wraps `db.upsert_camera` + `db.update_camera` for optional fields.
- `probe_analysis` runs snapshot + vision classify and returns result only.

## Error Handling
- Bubble Frigate/Ollama failures to UI; disable add if no frigate_name.

## Out of Scope
- Advanced camera metadata, deletion, bulk operations.

## Verification
- Manual: add via dropdown and via manual override; test both probe and scheduled.
- Check audit logs for create/update.

---

# Camera Management Implementation Plan

> For Claude: REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add explicit camera add/edit/test/save capabilities per design.

**Architecture:** Extend FastAPI with three endpoints, extend AnalyticsService with two helpers, add UI form and adjust labels. Reuse existing Frigate/Ollama clients.

**Tech Stack:** FastAPI, Jinja2, vanilla JS, SQLite.

### Task 1: API - list Frigate cameras

**Files:**
- Modify: factory_analytics/main.py
- Reuse: factory_analytics/integrations/frigate.py

**Steps:**
1) Add GET `/api/frigate/cameras` that returns `service.frigate_client().fetch_cameras()`
2) Return `{"cameras": [...]}`

### Task 2: Service create_camera

**Files:**
- Modify: factory_analytics/services.py
- Reuse: factory_analytics/database.py

**Steps:**
1) Add `def create_camera(self, frigate_name: str, name: str|None=None, enabled: bool|None=None, interval_seconds: int|None=None)`
2) Call `db.upsert_camera(frigate_name, name)` then `db.update_camera(id, {enabled, interval_seconds})` for provided values
3) Log audit `camera.create`

### Task 3: API - create camera

**Files:**
- Modify: factory_analytics/main.py

**Steps:**
1) Pydantic model `CameraCreate` with fields above
2) POST `/api/cameras` calls `service.create_camera(...)` and returns camera

### Task 4: Service probe_analysis

**Files:**
- Modify: factory_analytics/services.py

**Steps:**
1) `def probe_analysis(self, camera_id: int|None=None, frigate_name: str|None=None)`
2) Resolve `frigate_name` from DB if `camera_id` given
3) Fetch snapshot and classify; return `{ok,label,confidence}` without writes
4) Handle exceptions and return `{ok:false,error}`

### Task 5: API - cameras test

**Files:**
- Modify: factory_analytics/main.py

**Steps:**
1) Pydantic model `CameraTestPayload` with optional `camera_id` or `frigate_name`
2) Validate exactly one is provided
3) POST `/api/cameras/test` returns `service.probe_analysis(...)`

### Task 6: UI - add camera form and labels

**Files:**
- Modify: factory_analytics/templates/dashboard.html
- Modify: factory_analytics/static/app.js

**Steps:**
1) Insert a small form above camera table per design
2) Add JS: loadFrigateCameras, handle Add Camera, handle Test probe
3) Rename row buttons to `Save Camera` and `Test`
4) Wire alerts and refresh flows

### Task 7: Smoke tests (minimal)

**Files:**
- Modify: tests/test_ui_ux.py

**Steps:**
1) Assert presence of Add Camera form elements and buttons

### Task 8: Docs

**Files:**
- Create: docs/implementation/2026-03-28-camera-management.md
- Update: docs/todos.md (progress), docs/features.md (camera management note)

### Task 9: Verify

**Steps:**
1) Run app; test probe and creation end-to-end
2) Confirm logs and DB row
