# Processed Events And Charts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a new server-side paginated Processed Events page with Jobs and Segments views, plus a new Charts page with heatmap and additional analytics charts using timezone-aware fixed shifts.

**Architecture:** Keep `/logs` as raw system logs and introduce `/processed-events` for business/operational event records. Add dedicated paginated/filterable API endpoints for Jobs and Segments, compute `day`/`night` shift windows using the current saved timezone, and add `/charts` with dedicated analytics endpoints rather than overloading dashboard endpoints.

**Tech Stack:** FastAPI, SQLite, Jinja2, vanilla JS, timezone-aware Python datetime handling, canvas-based charts or lightweight table-rendered heatmap.

---

## Things To Do Before

- Confirm current saved app timezone in `/api/settings`
- Confirm whether all timestamps are stored in UTC (they should be)
- Verify current `jobs` and `segments` tables contain enough records for pagination testing
- Decide default page size (recommended: 25)
- Decide whether chart rendering stays canvas-based or moves to lightweight SVG/HTML heatmap (recommended: mixed - HTML heatmap + canvas charts)
- Verify no existing `/charts` route conflicts beyond API endpoints

### Task 1: Add Processed Events page route and template shell

**Files:**
- Create: `factory_analytics/templates/processed_events.html`
- Modify: `factory_analytics/main.py`
- Modify: `factory_analytics/templates/partials/nav.html`
- Test: `tests/test_ui_ux.py`

**Step 1: Write the failing test**

```python
def test_processed_events_page_renders(client):
    response = client.get('/processed-events')
    assert response.status_code == 200
    assert 'Processed Events' in response.text
    assert 'Jobs' in response.text
    assert 'Segments' in response.text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_ux.py::test_processed_events_page_renders -v`
Expected: FAIL because route/template do not exist.

**Step 3: Write minimal implementation**

- Add `/processed-events` page route
- Add nav link
- Add page shell with two tabs/toggles: `Jobs` and `Segments`
- Add filter area and results container

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui_ux.py::test_processed_events_page_renders -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_ui_ux.py factory_analytics/main.py factory_analytics/templates/processed_events.html factory_analytics/templates/partials/nav.html
git commit -m "feat(ui): add processed events page shell"
```

### Task 2: Add server-side paginated jobs API

**Files:**
- Modify: `factory_analytics/database.py`
- Modify: `factory_analytics/services.py`
- Modify: `factory_analytics/main.py`
- Test: `tests/test_api.py`

**Step 1: Write the failing test**

```python
def test_processed_jobs_api_returns_paginated_payload(client):
    response = client.get('/api/processed-events/jobs?page=1&page_size=25')
    assert response.status_code == 200
    payload = response.json()
    assert 'items' in payload
    assert 'total' in payload
    assert 'page' in payload
```
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py::test_processed_jobs_api_returns_paginated_payload -v`
Expected: FAIL because endpoint does not exist.

**Step 3: Write minimal implementation**

- Add DB query returning:
  - `items`
  - `total`
  - filtered/sorted results
- Filters:
  - `camera_id`
  - `status`
  - `from`
  - `to`
  - `shift` (`day`, `night`)
- Sorting:
  - processed/scheduled time
  - status
  - camera
- Compute shift using saved timezone and fixed windows:
  - `day`: 09:00-20:59:59
  - `night`: 21:00-08:59:59

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py::test_processed_jobs_api_returns_paginated_payload -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_api.py factory_analytics/database.py factory_analytics/services.py factory_analytics/main.py
git commit -m "feat(api): add paginated processed jobs endpoint"
```

### Task 3: Add server-side paginated segments API

**Files:**
- Modify: `factory_analytics/database.py`
- Modify: `factory_analytics/services.py`
- Modify: `factory_analytics/main.py`
- Test: `tests/test_api.py`

**Step 1: Write the failing test**

```python
def test_processed_segments_api_returns_paginated_payload(client):
    response = client.get('/api/processed-events/segments?page=1&page_size=25')
    assert response.status_code == 200
    payload = response.json()
    assert 'items' in payload
    assert 'total' in payload
```
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py::test_processed_segments_api_returns_paginated_payload -v`
Expected: FAIL because endpoint does not exist.

**Step 3: Write minimal implementation**

- Add DB query returning paginated segment rows
- Filters:
  - `camera_id`
  - `label`
  - `from`
  - `to`
  - `shift`
- Sorting:
  - `start_ts`
  - `confidence`
  - `camera`
  - `label`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py::test_processed_segments_api_returns_paginated_payload -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_api.py factory_analytics/database.py factory_analytics/services.py factory_analytics/main.py
git commit -m "feat(api): add paginated processed segments endpoint"
```

### Task 4: Build Processed Events page client UI

**Files:**
- Modify: `factory_analytics/templates/processed_events.html`
- Create: `factory_analytics/static/processed_events.js`
- Test: `tests/test_ui_ux.py`

**Step 1: Write the failing test**

```python
def test_processed_events_page_has_filters_and_pagination(client):
    html = client.get('/processed-events').text
    assert 'name="shift"' in html
    assert 'name="from"' in html
    assert 'name="to"' in html
    assert 'page-prev' in html
    assert 'page-next' in html
```
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_ux.py::test_processed_events_page_has_filters_and_pagination -v`
Expected: FAIL until UI is wired.

**Step 3: Write minimal implementation**

- Render filters for date, shift, camera, status/label
- Add Jobs/Segments toggle
- Add server-driven sort controls
- Add page navigation with total count and page info

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui_ux.py::test_processed_events_page_has_filters_and_pagination -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_ui_ux.py factory_analytics/templates/processed_events.html factory_analytics/static/processed_events.js
git commit -m "feat(ui): wire processed events filters sorting and pagination"
```

### Task 5: Add Charts page route and shell

**Files:**
- Create: `factory_analytics/templates/charts.html`
- Create: `factory_analytics/static/charts.js`
- Modify: `factory_analytics/main.py`
- Modify: `factory_analytics/templates/partials/nav.html`
- Test: `tests/test_ui_ux.py`

**Step 1: Write the failing test**

```python
def test_charts_page_renders(client):
    response = client.get('/charts')
    assert response.status_code == 200
    assert 'Charts' in response.text
    assert 'Heatmap' in response.text
```
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_ux.py::test_charts_page_renders -v`
Expected: FAIL because route/template do not exist.

**Step 3: Write minimal implementation**

- Add `/charts` route
- Add nav link
- Add chart containers for:
  - heatmap
  - camera summary
  - shift summary
  - job failures
  - confidence distribution

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui_ux.py::test_charts_page_renders -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_ui_ux.py factory_analytics/main.py factory_analytics/templates/charts.html factory_analytics/static/charts.js factory_analytics/templates/partials/nav.html
git commit -m "feat(ui): add charts page shell"
```

### Task 6: Add heatmap and chart APIs

**Files:**
- Modify: `factory_analytics/database.py`
- Modify: `factory_analytics/services.py`
- Modify: `factory_analytics/main.py`
- Test: `tests/test_api.py`

**Step 1: Write the failing tests**

```python
def test_heatmap_api_returns_matrix(client):
    response = client.get('/api/charts/heatmap')
    assert response.status_code == 200
    payload = response.json()
    assert 'rows' in payload

def test_shift_summary_api_returns_series(client):
    response = client.get('/api/charts/shift-summary')
    assert response.status_code == 200
```
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api.py::test_heatmap_api_returns_matrix tests/test_api.py::test_shift_summary_api_returns_series -v`
Expected: FAIL because endpoints do not exist.

**Step 3: Write minimal implementation**

- `/api/charts/heatmap`
  - camera x hour/day intensity matrix
- `/api/charts/camera-summary`
  - stacked label totals by camera
- `/api/charts/shift-summary`
  - day vs night totals
- `/api/charts/job-failures`
  - failure counts over time by camera/status
- `/api/charts/confidence-distribution`
  - binned confidence ranges

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api.py::test_heatmap_api_returns_matrix tests/test_api.py::test_shift_summary_api_returns_series -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_api.py factory_analytics/database.py factory_analytics/services.py factory_analytics/main.py
git commit -m "feat(api): add charts analytics endpoints"
```

### Task 7: Render heatmap and additional charts on the Charts page

**Files:**
- Modify: `factory_analytics/static/charts.js`
- Modify: `factory_analytics/templates/charts.html`

**Step 1: Write minimal rendering expectations**

- Heatmap renders grid labels and cells
- Additional charts render non-empty states from API responses

**Step 2: Implement rendering**

- Use HTML/CSS grid or table for heatmap (recommended for accessibility)
- Use canvas/SVG for bar/line distributions
- Add filters for date range and shift where useful

**Step 3: Verify manually**

- `/charts` shows heatmap, camera summary, shift summary, failure trend, confidence distribution

**Step 4: Commit**

```bash
git add factory_analytics/static/charts.js factory_analytics/templates/charts.html
git commit -m "feat(charts): render heatmap and operational analytics"
```

### Task 8: Timezone-aware shift logic verification

**Files:**
- Test: `tests/test_shift_filters.py`

**Step 1: Write the failing test**

```python
def test_shift_filter_uses_saved_timezone_for_day_and_night():
    # assert 09:00-20:59 maps to day and 21:00-08:59 maps to night in saved tz
    ...
```
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_shift_filters.py -v`
Expected: FAIL until shift utility exists.

**Step 3: Write minimal implementation**

- Add shift utility reused by jobs, segments, and charts APIs
- Ensure timestamps are converted from UTC to saved timezone before shift bucketing

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_shift_filters.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_shift_filters.py factory_analytics/database.py factory_analytics/services.py
git commit -m "test(timezone): verify shift bucketing in saved timezone"
```

### Task 9: Memory docs and final verification

**Files:**
- Modify: `docs/implementation/2026-03-28-camera-management.md` or create a new implementation note if scope is large
- Modify: `docs/features.md`
- Modify: `docs/todos.md`

**Step 1: Update durable docs**

- Add a new implementation note if needed for processed events and charts
- Update features map with:
  - Processed Events page
  - Charts page
  - shift-aware filtering

**Step 2: Run full verification**

Run: `pytest -q`
Expected: PASS

**Step 3: Manual verification**

- `/processed-events` loads
- Jobs and Segments views paginate server-side
- Date and shift filters work in saved timezone
- `/charts` renders heatmap + other charts
- Raw `/logs` page still works independently

**Step 4: Commit**

```bash
git add docs
git commit -m "docs: record processed events and charts features"
```
