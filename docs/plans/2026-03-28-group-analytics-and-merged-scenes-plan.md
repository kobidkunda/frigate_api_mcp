# Group Analytics And Merged Scenes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Preserve existing camera analytics while adding group-based analytics (machine/room), merged multi-camera scene analysis, richer worker-state duration metrics, and matching MCP/OpenClaw documentation updates.

**Architecture:** Keep per-camera jobs/segments/rollups intact, then add group entities and many-to-many camera membership. For each group analysis run, capture current snapshots from all member cameras, merge them into a single full-resolution composite image, run the configured LLM over that composite, and save annotated evidence plus group-level rollups. Expose new group-aware APIs/UI while preserving all existing camera endpoints and pages.

**Tech Stack:** FastAPI, SQLite, Jinja2, vanilla JS, Pillow/PIL image composition + annotation, timezone-aware datetime logic, existing MCP server docs and OpenClaw markdown docs.

---

## Things To Do Before

- Confirm the new labels to support in rollups: `working`, `idle`, `sleeping`, `stopped`, `uncertain`, `timepass`, `operator_missing`
- Confirm groups are many-to-many and camera analytics must remain enabled by default
- Confirm merged group images should use full-resolution source snapshots, with only UI thumbnails reduced for display
- Confirm the current saved timezone in `/api/settings` because shift bucketing and group reports must use it
- Identify the current MCP/OpenClaw docs files to update so the new group tools are documented alongside old camera tools
- Verify there are enough real cameras to form at least one `machine` group and one `room` group for manual verification

### Task 1: Add group data model and camera-group mapping

**Files:**
- Modify: `factory_analytics/database.py`
- Test: `tests/test_groups_model.py`

**Step 1: Write the failing test**

```python
def test_camera_can_belong_to_multiple_groups(tmp_path):
    db = Database(tmp_path / 'test.db')
    cam = db.upsert_camera('camera_1')
    machine = db.create_group('machine', 'machine 1')
    room = db.create_group('room', 'room 1 factory')
    db.add_camera_to_group(cam['id'], machine['id'])
    db.add_camera_to_group(cam['id'], room['id'])
    groups = db.list_camera_groups(cam['id'])
    assert len(groups) == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_groups_model.py -v`
Expected: FAIL because group tables/helpers do not exist.

**Step 3: Write minimal implementation**

- Add tables:
  - `groups`
  - `camera_groups`
- Add DB helpers:
  - `create_group(group_type, name)`
  - `list_groups()`
  - `add_camera_to_group(camera_id, group_id)`
  - `remove_camera_from_group(camera_id, group_id)`
  - `list_group_cameras(group_id)`
  - `list_camera_groups(camera_id)`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_groups_model.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_groups_model.py factory_analytics/database.py
git commit -m "feat(groups): add camera group model and many-to-many mapping"
```

### Task 2: Add group CRUD and membership APIs

**Files:**
- Modify: `factory_analytics/main.py`
- Modify: `factory_analytics/services.py`
- Test: `tests/test_api.py`

**Step 1: Write the failing tests**

```python
def test_create_group_api(client):
    response = client.post('/api/groups', json={'group_type': 'machine', 'name': 'machine 1'})
    assert response.status_code == 200

def test_add_camera_to_group_api(client):
    response = client.post('/api/groups/1/cameras', json={'camera_id': 2})
    assert response.status_code in (200, 404)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api.py::test_create_group_api tests/test_api.py::test_add_camera_to_group_api -v`
Expected: FAIL because endpoints do not exist.

**Step 3: Write minimal implementation**

- Add APIs:
  - `GET /api/groups`
  - `POST /api/groups`
  - `POST /api/groups/{group_id}/cameras`
  - `DELETE /api/groups/{group_id}/cameras/{camera_id}`
  - `GET /api/cameras/{camera_id}/groups`

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api.py::test_create_group_api tests/test_api.py::test_add_camera_to_group_api -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_api.py factory_analytics/main.py factory_analytics/services.py
git commit -m "feat(api): add group and camera membership endpoints"
```

### Task 3: Extend LLM response contract for richer worker-state labels and person boxes

**Files:**
- Modify: `factory_analytics/integrations/ollama.py`
- Test: `tests/test_ollama_integration.py`

**Step 1: Write the failing tests**

```python
def test_classify_image_accepts_group_labels_and_boxes():
    ...

def test_classify_image_fails_on_invalid_boxes_or_label():
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ollama_integration.py -v`
Expected: FAIL until the parser supports the new label set and required boxes.

**Step 3: Write minimal implementation**

- Extend valid labels to include:
  - `timepass`
  - `operator_missing`
- Update prompt so the model must return JSON with:
  - `label`
  - `confidence`
  - `notes`
  - `boxes`
- Keep strict failure behavior: if invalid output, fail honestly.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ollama_integration.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_ollama_integration.py factory_analytics/integrations/ollama.py
git commit -m "feat(ollama): support richer worker-state labels and required person boxes"
```

### Task 4: Add full-resolution merged scene composition helper

**Files:**
- Create: `factory_analytics/image_composition.py`
- Test: `tests/test_image_composition.py`

**Step 1: Write the failing test**

```python
def test_merge_group_snapshots_creates_full_resolution_composite(tmp_path):
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_image_composition.py -v`
Expected: FAIL because helper does not exist.

**Step 3: Write minimal implementation**

- Merge multiple snapshots into a composite grid image
- Preserve full source detail as much as possible
- Add optional panel labels using camera names
- Save composite as full-resolution evidence input image

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_image_composition.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_image_composition.py factory_analytics/image_composition.py
git commit -m "feat(images): add full-resolution merged scene composition for groups"
```

### Task 5: Add annotated evidence saving for both camera and group analysis

**Files:**
- Modify: `factory_analytics/services.py`
- Create or modify: `factory_analytics/image_annotations.py`
- Test: `tests/test_image_annotations.py`

**Step 1: Write the failing tests**

```python
def test_camera_analysis_saves_annotated_full_res_evidence():
    ...

def test_group_analysis_saves_annotated_composite_evidence():
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_image_annotations.py -v`
Expected: FAIL until annotation/save path supports both camera and group images.

**Step 3: Write minimal implementation**

- Draw person rectangles on full-resolution images
- Save annotated image as canonical `evidence_path`
- Keep raw image optional/internal only
- Use full-resolution source for LLM input and full-resolution annotated output on disk

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_image_annotations.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_image_annotations.py factory_analytics/services.py factory_analytics/image_annotations.py
git commit -m "feat(evidence): save full-resolution annotated evidence for camera and group analysis"
```

### Task 6: Add group analysis jobs, segments, and rollups

**Files:**
- Modify: `factory_analytics/database.py`
- Modify: `factory_analytics/services.py`
- Modify: `factory_analytics/main.py`
- Test: `tests/test_group_analysis.py`

**Step 1: Write the failing tests**

```python
def test_group_analysis_creates_group_segment_and_rollup():
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_group_analysis.py -v`
Expected: FAIL because group analysis path does not exist.

**Step 3: Write minimal implementation**

- Add group jobs/segments support, or add entity discriminator if reusing tables
- Add `queue_group_analysis(group_id)`
- Capture member camera snapshots, merge to composite, classify, annotate, save
- Persist group-level segment and update rollups for labels:
  - `working`
  - `idle`
  - `sleeping`
  - `stopped`
  - `uncertain`
  - `timepass`
  - `operator_missing`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_group_analysis.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_group_analysis.py factory_analytics/database.py factory_analytics/services.py factory_analytics/main.py
git commit -m "feat(groups): add merged-scene group analysis and rollups"
```

### Task 7: Add duration metrics queries for cameras and groups

**Files:**
- Modify: `factory_analytics/database.py`
- Modify: `factory_analytics/services.py`
- Modify: `factory_analytics/main.py`
- Test: `tests/test_metrics_queries.py`

**Step 1: Write the failing tests**

```python
def test_group_duration_metrics_query_returns_timepass_and_operator_missing():
    ...

def test_camera_duration_metrics_query_still_works():
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_metrics_queries.py -v`
Expected: FAIL until metrics query APIs exist.

**Step 3: Write minimal implementation**

- Add API/query methods for duration summaries by:
  - camera
  - group
  - date range
  - shift
- Support future questions like:
  - “machine 1 operator missing time”
  - “room 1 factory timepass time”

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_metrics_queries.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_metrics_queries.py factory_analytics/database.py factory_analytics/services.py factory_analytics/main.py
git commit -m "feat(metrics): add camera and group duration summaries"
```

### Task 8: Add group management UI while keeping old camera UI

**Files:**
- Modify: `factory_analytics/templates/dashboard.html`
- Modify: `factory_analytics/static/app.js`
- Possibly create: `factory_analytics/templates/groups.html`
- Test: `tests/test_ui_ux.py`

**Step 1: Write the failing test**

```python
def test_group_management_ui_renders_without_removing_camera_ui(client):
    html = client.get('/dashboard').text
    assert 'Cameras' in html
    assert 'Groups' in html or client.get('/groups').status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_ux.py::test_group_management_ui_renders_without_removing_camera_ui -v`
Expected: FAIL until group UI exists.

**Step 3: Write minimal implementation**

- Add group CRUD UI
- Add camera-to-group membership UI
- Keep existing camera add/edit/test/delete intact

### Task 8a: Add dedicated Groups management page

**Files:**
- Create: `factory_analytics/templates/groups.html`
- Create: `factory_analytics/static/groups.js`
- Modify: `factory_analytics/main.py`
- Modify: `factory_analytics/templates/partials/nav.html` or current nav template used in repo
- Modify: `factory_analytics/services.py`
- Modify: `factory_analytics/database.py`
- Test: `tests/test_groups_ui.py`

**Step 1: Write the failing test**

```python
def test_groups_page_renders_full_group_management(client):
    response = client.get('/groups')
    assert response.status_code == 200
    html = response.text
    assert 'Groups' in html
    assert 'Create Group' in html
    assert 'Remove Camera' in html
```
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_groups_ui.py -v`
Expected: FAIL because dedicated page does not exist.

**Step 3: Write minimal implementation**

- Add `/groups` page route
- Add full UI for:
  - create group
  - rename group
  - delete group
  - list current members
  - add camera to group
  - remove camera from group
- Add missing backend endpoints if needed:
  - `PUT /api/groups/{group_id}`
  - `DELETE /api/groups/{group_id}`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_groups_ui.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_groups_ui.py factory_analytics/templates/groups.html factory_analytics/static/groups.js factory_analytics/main.py factory_analytics/services.py factory_analytics/database.py
git commit -m "feat(groups): add dedicated groups management page"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui_ux.py::test_group_management_ui_renders_without_removing_camera_ui -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_ui_ux.py factory_analytics/templates/dashboard.html factory_analytics/static/app.js
git commit -m "feat(ui): add group management while preserving camera workflows"
```

### Task 9: Extend processed events and charts plans to support groups

**Files:**
- Modify: `factory_analytics/database.py`
- Modify: `factory_analytics/services.py`
- Modify: `factory_analytics/main.py`
- Modify: `factory_analytics/templates/processed_events.html`
- Modify: `factory_analytics/static/processed_events.js`
- Modify: `factory_analytics/templates/charts.html`
- Modify: `factory_analytics/static/charts.js`

**Step 1: Add group filters to processed events**

- Allow filters by:
  - camera
  - group
  - entity type (camera/group)

**Step 2: Add group-aware charts**

- Heatmap by camera or by group
- Shift summary by camera or group
- Duration comparison for `timepass` and `operator_missing`

**Step 3: Verify manually**

- Existing camera pages still work
- New processed events/charts can analyze by group or camera

**Step 4: Commit**

```bash
git add factory_analytics/database.py factory_analytics/services.py factory_analytics/main.py factory_analytics/templates/processed_events.html factory_analytics/static/processed_events.js factory_analytics/templates/charts.html factory_analytics/static/charts.js
git commit -m "feat(analytics): extend processed events and charts with group-aware views"
```

### Task 10: Update MCP and OpenClaw docs while keeping old docs valid

**Files:**
- Modify: `README.md`
- Modify: `docs/features.md`
- Modify: `docs/todos.md`
- Create or modify: relevant MCP/OpenClaw docs discovered in repo (for example `data/features/mainaplication.md` and any OpenClaw skill/docs files in workspace)
- Create: `docs/implementation/2026-03-28-group-analytics.md`

**Step 1: Write/update docs**

- Keep old camera-based docs
- Add group-based analytics docs:
  - machine/room groups
  - many-to-many camera membership
  - merged-scene analysis
  - duration metrics
  - MCP tools for groups and summaries
  - OpenClaw instructions for group queries

**Step 2: Verify docs mention both old and new behavior**

- camera analytics still supported
- group analytics added on top

**Step 3: Commit**

```bash
git add README.md docs data/features
git commit -m "docs: add group analytics, MCP, and OpenClaw guidance"
```

### Task 11: Full verification

**Files:**
- Test suite and manual verification only

**Step 1: Run focused tests**

Run:

```bash
pytest tests/test_groups_model.py tests/test_group_analysis.py tests/test_image_composition.py tests/test_image_annotations.py tests/test_metrics_queries.py tests/test_ui_ux.py tests/test_api.py -v
```

Expected: PASS

**Step 2: Run full test suite**

Run: `pytest -q`
Expected: PASS

**Step 3: Manual verification**

- Create groups of type `machine` and `room`
- Attach one camera to multiple groups
- Run camera analysis and group analysis together
- Confirm merged full-resolution composite evidence is saved with person rectangles
- Confirm processed events and charts support both camera and group views
- Confirm old camera-only flows still work unchanged

**Step 4: Commit**

```bash
git add .
git commit -m "feat(groups): add multi-camera group analytics and merged-scene reporting"
```
