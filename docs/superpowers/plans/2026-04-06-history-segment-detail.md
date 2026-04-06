# History Segment Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/history` render all evidence thumbnails inline, keep model names visible, and add a dedicated `/history/{segment_id}` page with full capture-event details.

**Architecture:** Keep the existing FastAPI + Jinja + vanilla-JS History flow. Extend the segment detail backend so the canonical data comes from `factory_analytics/database.py`, keep `/history` as the summary table fed by `/api/history/segments`, and add a new server-rendered route/template for `/history/{segment_id}` for full inspection.

**Tech Stack:** FastAPI, Jinja2 templates, vanilla JavaScript, SQLite, pytest.

---

## File structure

- `factory_analytics/database.py`
  - Source of truth for History list/detail payloads.
  - Needs segment detail normalization aligned with list payloads so `model_used`, `evidence_frames`, and related metadata are consistently available.
- `factory_analytics/main.py`
  - Add the new HTML route for `/history/{segment_id}`.
- `factory_analytics/templates/history.html`
  - Keep the existing list page, but render all evidence thumbnails inline and add a detail navigation affordance.
- `factory_analytics/templates/history_detail.html`
  - New dedicated server-rendered capture-event detail page.
- `tests/test_ui_ux.py`
  - Source-level UI/template assertions and page-route smoke tests.
- `tests/test_evidence_api.py`
  - API/detail payload assertions are best placed here because this file already covers evidence-oriented API behavior.

### Task 1: Lock in History detail payload requirements

**Files:**
- Modify: `tests/test_evidence_api.py`
- Modify: `factory_analytics/database.py:669-690`
- Test: `tests/test_evidence_api.py`

- [ ] **Step 1: Write the failing test**

Add a focused API test that proves `/api/history/segments/{segment_id}` must expose the fields required by the new detail page.

```python
def test_history_segment_detail_includes_model_and_evidence_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTORY_ANALYTICS_DB_PATH", str(tmp_path / "test.db"))

    from factory_analytics.database import Database
    from factory_analytics.services import AnalyticsService

    db = Database(tmp_path / "test.db")
    service = AnalyticsService(db)

    camera = db.create_camera("cam-a", "Camera A", True, 300)
    job = db.create_job(camera["id"], "single_analysis", "done")
    db.finish_job(
        job["id"],
        "done",
        raw_result={
            "model": "llava:13b",
            "group_name": "Line 1",
            "group_type": "line",
            "group_id": 4,
            "primary_evidence_path": "data/evidence/primary.jpg",
            "evidence_frames": [
                "data/evidence/frame-1.jpg",
                "data/evidence/frame-2.jpg",
            ],
            "raw": {"detail": "kept"},
        },
        snapshot_path="data/evidence/primary.jpg",
    )
    segment = db.create_segment(
        job["id"],
        camera["id"],
        "2026-04-06T10:00:00+00:00",
        "2026-04-06T10:01:00+00:00",
        "working",
        0.92,
        "Operator present",
        "data/evidence/primary.jpg",
    )
    db.review_segment(segment["id"], "working", "looks correct", "qa-user")

    payload = service.segment(segment["id"])

    assert payload["model_used"] == "llava:13b"
    assert payload["evidence_frames"] == [
        "data/evidence/frame-1.jpg",
        "data/evidence/frame-2.jpg",
    ]
    assert payload["primary_evidence_path"] == "data/evidence/primary.jpg"
    assert payload["group_name"] == "Line 1"
    assert payload["review_by"] == "qa-user"
    assert payload["raw_result"]["raw"]["detail"] == "kept"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_evidence_api.py::test_history_segment_detail_includes_model_and_evidence_fields -v`
Expected: FAIL because `Database.get_segment()` currently does not include `MODEL_USED_SQL`, `evidence_frames`, or `primary_evidence_path` in the normalized detail payload.

- [ ] **Step 3: Write minimal implementation**

Update `Database.get_segment()` so the detail query matches the list/detail normalization pattern already used elsewhere.

```python
row = conn.execute(
    f"""SELECT s.*, c.name AS camera_name, c.frigate_name AS camera_frigate_name,
              j.job_type, j.raw_result, j.payload_json,
              {MODEL_USED_SQL}
       FROM segments s
       JOIN cameras c ON c.id = s.camera_id
       LEFT JOIN jobs j ON j.id = s.job_id
       WHERE s.id=?""",
    (segment_id,),
).fetchone()
```

And normalize the extra fields before returning:

```python
item["evidence_frames"] = item["raw_result"].get("evidence_frames", [])
item["primary_evidence_path"] = item["raw_result"].get(
    "primary_evidence_path"
) or item.get("evidence_path")
item["group_name"] = item["raw_result"].get("group_name")
item["group_type"] = item["raw_result"].get("group_type")
item["group_id"] = item["raw_result"].get("group_id")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_evidence_api.py::test_history_segment_detail_includes_model_and_evidence_fields -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_evidence_api.py factory_analytics/database.py
git commit -m "test(history): require complete segment detail payload"
```

### Task 2: Lock in the new History detail page route

**Files:**
- Modify: `tests/test_ui_ux.py`
- Modify: `factory_analytics/main.py:124-127`
- Create: `factory_analytics/templates/history_detail.html`
- Test: `tests/test_ui_ux.py`

- [ ] **Step 1: Write the failing tests**

Add one route smoke test and one template source test.

```python
def test_history_detail_page_renders_existing_segment():
    client = TestClient(app)
    response = client.get("/history/1")
    assert response.status_code in {200, 404}


def test_history_detail_template_contains_required_sections():
    source = Path("factory_analytics/templates/history_detail.html").read_text()
    assert "Capture Event Details" in source
    assert "Evidence Frames" in source
    assert "Model" in source
    assert "Raw Result" in source
```

Immediately tighten the route test after route creation to assert `200` against a seeded segment fixture or direct database setup. If no fixture exists, create the segment inline in the test before issuing the request.

Use this final test shape once the route exists:

```python
def test_history_detail_page_renders_existing_segment():
    client = TestClient(app)
    response = client.get("/history/1")
    assert response.status_code == 200
    assert "Capture Event Details" in response.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ui_ux.py::test_history_detail_template_contains_required_sections tests/test_ui_ux.py::test_history_detail_page_renders_existing_segment -v`
Expected: FAIL because the template file and route do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add the HTML route in `factory_analytics/main.py` near `history_page()`:

```python
@app.get("/history/{segment_id}", response_class=HTMLResponse)
def history_detail_page(request: Request, segment_id: int):
    segment = service.segment(segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return templates.TemplateResponse(
        "history_detail.html",
        {"request": request, "segment": segment},
    )
```

Create `factory_analytics/templates/history_detail.html` with server-rendered sections for:
- title/header
- core metadata cards
- notes / review block
- primary evidence image
- full evidence frame gallery
- raw result / payload details

Use this skeleton as the starting structure:

```html
{% extends "partials/base.html" %}
{% block title %}Capture Event Details{% endblock %}
{% block content %}
<header class="mb-8">
  <h1 class="text-3xl font-headline font-extrabold text-on-surface tracking-tight mb-2">Capture Event Details</h1>
  <p class="text-on-surface-variant font-body">Segment #{{ segment.id }}</p>
</header>

<section class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
  <article class="bg-surface-container-low p-4 rounded-xl border border-outline-variant/10">
    <div class="text-xs uppercase tracking-widest text-outline mb-1">Model</div>
    <div class="font-mono text-sm text-on-surface">{{ segment.model_used or '-' }}</div>
  </article>
</section>

<section class="bg-surface-container-low p-6 rounded-xl border border-outline-variant/10 mb-8">
  <h2 class="text-lg font-bold mb-4">Evidence Frames</h2>
</section>

<section class="bg-surface-container-low p-6 rounded-xl border border-outline-variant/10">
  <h2 class="text-lg font-bold mb-4">Raw Result</h2>
  <pre class="text-xs overflow-x-auto">{{ segment.raw_result | tojson(indent=2) }}</pre>
</section>
{% endblock %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ui_ux.py::test_history_detail_template_contains_required_sections tests/test_ui_ux.py::test_history_detail_page_renders_existing_segment -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_ui_ux.py factory_analytics/main.py factory_analytics/templates/history_detail.html
git commit -m "feat(history): add segment detail page"
```

### Task 3: Lock in all-thumbnail rendering and detail navigation on `/history`

**Files:**
- Modify: `tests/test_ui_ux.py`
- Modify: `factory_analytics/templates/history.html:182-245`
- Test: `tests/test_ui_ux.py`

- [ ] **Step 1: Write the failing tests**

Add assertions that specifically require multi-thumbnail rendering and a detail-route hook.

```python
def test_history_page_renders_all_evidence_thumbnail_hooks():
    source = Path("factory_analytics/templates/history.html").read_text()
    assert "evidenceFrames.map" in source
    assert "frame ${i+1}" in source
    assert "flex gap-1 items-center" in source


def test_history_page_links_rows_to_segment_detail_route():
    source = Path("factory_analytics/templates/history.html").read_text()
    assert 'href="/history/${s.id}"' in source or "window.location.href='/history/' + s.id" in source
```

- [ ] **Step 2: Run tests to verify current behavior**

Run: `pytest tests/test_ui_ux.py::test_history_page_renders_all_evidence_thumbnail_hooks tests/test_ui_ux.py::test_history_page_links_rows_to_segment_detail_route -v`
Expected: the thumbnail test may already PASS if the multi-frame branch exists, but the detail-route test should FAIL because the current row markup has no path into `/history/{segment_id}`.

- [ ] **Step 3: Write minimal implementation**

Keep the existing `evidenceFrames` logic, but make the detail route explicit in the UI.

Recommended minimal change inside `renderSegments()`:

```javascript
const detailHref = `/history/${s.id}`;
```

Then render a dedicated action link in the Review column or add a separate link block in the metadata cell:

```javascript
<div class="mt-2">
  <a href="${detailHref}" class="inline-flex items-center gap-1 text-xs font-label uppercase tracking-widest text-primary hover:underline">
    Open Details
  </a>
</div>
```

If you choose clickable rows, preserve button behavior and avoid nesting interactive controls incorrectly. A dedicated link is the safer minimal implementation.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ui_ux.py::test_history_page_renders_all_evidence_thumbnail_hooks tests/test_ui_ux.py::test_history_page_links_rows_to_segment_detail_route -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_ui_ux.py factory_analytics/templates/history.html
git commit -m "feat(history): add detail navigation from history list"
```

### Task 4: Fill out the detail template with all required capture-event sections

**Files:**
- Modify: `tests/test_ui_ux.py`
- Modify: `factory_analytics/templates/history_detail.html`
- Test: `tests/test_ui_ux.py`

- [ ] **Step 1: Write the failing template test**

Add a source-level test that verifies all requested sections are present.

```python
def test_history_detail_template_surfaces_all_capture_sections():
    source = Path("factory_analytics/templates/history_detail.html").read_text()
    assert "Segment Identity" in source
    assert "Camera & Group" in source
    assert "Review" in source
    assert "Primary Evidence" in source
    assert "Evidence Frames" in source
    assert "Raw Result" in source
    assert "Review Note" in source
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_ux.py::test_history_detail_template_surfaces_all_capture_sections -v`
Expected: FAIL until the detail template is expanded beyond the initial skeleton.

- [ ] **Step 3: Write minimal implementation**

Expand `factory_analytics/templates/history_detail.html` into focused sections.

Use this structure:

```html
<section class="bg-surface-container-low p-6 rounded-xl border border-outline-variant/10 mb-8">
  <h2 class="text-lg font-bold mb-4">Segment Identity</h2>
  <dl class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 text-sm">
    <div><dt class="text-xs uppercase tracking-widest text-outline mb-1">Segment ID</dt><dd>#SEG-{{ segment.id }}</dd></div>
    <div><dt class="text-xs uppercase tracking-widest text-outline mb-1">Job ID</dt><dd>{{ segment.job_id }}</dd></div>
    <div><dt class="text-xs uppercase tracking-widest text-outline mb-1">Job Type</dt><dd>{{ segment.job_type or '-' }}</dd></div>
    <div><dt class="text-xs uppercase tracking-widest text-outline mb-1">Model</dt><dd>{{ segment.model_used or '-' }}</dd></div>
  </dl>
</section>

<section class="bg-surface-container-low p-6 rounded-xl border border-outline-variant/10 mb-8">
  <h2 class="text-lg font-bold mb-4">Camera &amp; Group</h2>
</section>

<section class="bg-surface-container-low p-6 rounded-xl border border-outline-variant/10 mb-8">
  <h2 class="text-lg font-bold mb-4">Review</h2>
  <div class="text-sm">Review Note</div>
</section>

<section class="bg-surface-container-low p-6 rounded-xl border border-outline-variant/10 mb-8">
  <h2 class="text-lg font-bold mb-4">Primary Evidence</h2>
</section>
```

For evidence rendering, use Jinja conditions instead of client-side JSON manipulation:

```html
{% set primary_path = segment.primary_evidence_path or segment.evidence_path %}
{% if primary_path %}
  <a href="/{{ primary_path }}" target="_blank">
    <img src="/{{ primary_path }}" alt="Primary evidence" class="w-full max-h-[28rem] object-contain rounded-lg border border-outline-variant/10">
  </a>
{% else %}
  <div class="text-sm text-outline">-</div>
{% endif %}
```

For the gallery:

```html
{% if segment.evidence_frames %}
  <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
    {% for frame in segment.evidence_frames %}
      <a href="/{{ frame }}" target="_blank" class="block rounded-lg overflow-hidden border border-outline-variant/10">
        <img src="/{{ frame }}" alt="Evidence frame {{ loop.index }}" class="w-full h-40 object-cover">
      </a>
    {% endfor %}
  </div>
{% else %}
  <div class="text-sm text-outline">-</div>
{% endif %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui_ux.py::test_history_detail_template_surfaces_all_capture_sections -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_ui_ux.py factory_analytics/templates/history_detail.html
git commit -m "feat(history): expand segment detail template"
```

### Task 5: Verify HTTP behavior for list/detail surfaces

**Files:**
- Modify: `tests/test_evidence_api.py`
- Modify: `tests/test_ui_ux.py`
- Test: `tests/test_evidence_api.py`
- Test: `tests/test_ui_ux.py`

- [ ] **Step 1: Write the failing route/API tests**

Add one API test for list behavior and one route test for 404 behavior.

```python
def test_history_segments_list_preserves_multi_frame_evidence(client):
    response = client.get("/api/history/segments")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert "evidence_frames" in payload[0]


def test_history_detail_page_returns_404_for_missing_segment():
    client = TestClient(app)
    response = client.get("/history/999999")
    assert response.status_code == 404
```

If `client` fixture does not exist in this repo, inline `TestClient(app)` and seed one segment before calling the list endpoint so the evidence assertion targets a known payload.

- [ ] **Step 2: Run tests to verify current behavior**

Run: `pytest tests/test_evidence_api.py::test_history_segments_list_preserves_multi_frame_evidence tests/test_ui_ux.py::test_history_detail_page_returns_404_for_missing_segment -v`
Expected: the 404 test should PASS once the route exists; the list evidence test should reveal whether list payloads are already correct or need tightening.

- [ ] **Step 3: Write minimal implementation**

Only make code changes if the list evidence test fails. If it does, align `list_segments_paginated()` with `list_segments()` by normalizing `evidence_frames` there too:

```python
item["evidence_frames"] = item["raw_result"].get("evidence_frames", [])
item["primary_evidence_path"] = item["raw_result"].get(
    "primary_evidence_path"
) or item.get("evidence_path")
```

Do not change unrelated APIs.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `pytest tests/test_evidence_api.py::test_history_segments_list_preserves_multi_frame_evidence tests/test_ui_ux.py::test_history_detail_page_returns_404_for_missing_segment -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_evidence_api.py tests/test_ui_ux.py factory_analytics/database.py
git commit -m "test(history): verify detail and evidence route behavior"
```

### Task 6: Final verification for the History feature slice

**Files:**
- Modify: none unless test fixes are required
- Test: `tests/test_ui_ux.py`
- Test: `tests/test_evidence_api.py`

- [ ] **Step 1: Run the focused History/UI/API test set**

Run: `pytest tests/test_ui_ux.py tests/test_evidence_api.py -v`
Expected: PASS

- [ ] **Step 2: Run targeted route smoke checks manually if needed**

Run: `pytest tests/test_ui_ux.py::test_history_page_renders_and_has_filters tests/test_ui_ux.py::test_history_detail_page_renders_existing_segment tests/test_ui_ux.py::test_history_detail_page_returns_404_for_missing_segment -v`
Expected: PASS

- [ ] **Step 3: Review changed files for scope drift**

Inspect only these files for final scope confirmation:
- `factory_analytics/database.py`
- `factory_analytics/main.py`
- `factory_analytics/templates/history.html`
- `factory_analytics/templates/history_detail.html`
- `tests/test_ui_ux.py`
- `tests/test_evidence_api.py`

Confirm the changes are limited to:
- segment detail payload completeness
- history detail route
- history thumbnail/detail navigation rendering
- detail-page template sections

- [ ] **Step 4: Commit**

```bash
git add factory_analytics/database.py factory_analytics/main.py factory_analytics/templates/history.html factory_analytics/templates/history_detail.html tests/test_ui_ux.py tests/test_evidence_api.py
git commit -m "feat(history): add detailed capture event inspection"
```
