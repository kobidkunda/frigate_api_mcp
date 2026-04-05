# UI Model Visibility and Heatmap Details Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show `model_used` on every required Jobs, Photos, and Reports row/card, and make Efficiency heatmap clicks open a usable per-segment list with thumbnail, model, and a path into full job details.

**Architecture:** Extend existing list APIs so each UI surface receives display-ready `model_used` and first-frame metadata without extra lookup calls per card. Keep the existing Jobs modal as the canonical full-details surface; the Efficiency heatmap drilldown should become a compact list that fetches segment details/evidence for display and routes into the existing job detail flow instead of creating a second full gallery.

**Tech Stack:** Python, FastAPI, SQLite, Jinja templates, vanilla JavaScript, pytest, FastAPI TestClient

---

## File Structure

- Modify: `factory_analytics/database.py`
  - Add `model_used` extraction to segment/photo/report list queries.
  - Add any report helper fields needed by dashboard/report cards.
- Modify: `factory_analytics/static/efficiency.js`
  - Replace single-segment popover assumptions with list-oriented heatmap drilldown rendering.
  - Add per-entry thumbnail/model/button rendering and handoff into existing job details flow.
- Modify: `factory_analytics/templates/efficiency.html`
  - Adjust popover shell so JS can render a segment list instead of a single evidence link.
- Modify: `factory_analytics/static/photos.js`
  - Render model name inline on photo cards and in the modal metadata panel.
- Modify: `factory_analytics/templates/photos.html`
  - Add the visible model metadata slot in the modal/card layout if needed.
- Modify: `factory_analytics/templates/history.html`
  - Render model name in each visible report row/card entry.
- Modify: `factory_analytics/templates/jobs.html`
  - Keep the model column visible in rows and add model to the full job details metadata block.
- Modify: `factory_analytics/templates/dashboard.html`
  - Ensure the report card surface can visibly show recent-segment model metadata if this page is the active report card surface.
- Modify: `factory_analytics/static/app.js`
  - Render model name in the dashboard/report recent segment area if fed by `/api/reports/daily`.
- Modify: `tests/test_ui_ux.py`
  - Add source-level UI assertions for model labels and heatmap drilldown hooks.
- Modify: `tests/test_worker.py`
  - Add database/report payload assertions for `model_used` on relevant list/report payloads.

---

### Task 1: Expose model data in list/report payloads

**Files:**
- Modify: `factory_analytics/database.py:684-915`
- Modify: `factory_analytics/database.py:1083-1114`
- Modify: `tests/test_worker.py`

- [ ] **Step 1: Write the failing tests**

Add these tests to `tests/test_worker.py`:

```python
def test_list_segments_paginated_exposes_model_used(tmp_path: Path):
    db = Database(path=tmp_path / "segments_model.db")
    camera = db.upsert_camera("segments_model_cam", "Segments Model Cam")
    job = db.schedule_job(
        camera["id"],
        payload={"llm_vision_model": "payload-model"},
    )
    db.create_segment(
        job_id=job["id"],
        camera_id=camera["id"],
        start_ts="2026-04-05T10:00:00+00:00",
        end_ts="2026-04-05T10:02:00+00:00",
        label="working",
        confidence=0.93,
        notes="operator present",
        evidence_path="data/evidence/frames/segments_model_cam/frame_0.jpg",
    )
    db.mark_job_finished(
        job["id"],
        "success",
        raw_result={
            "model": "vision-alpha",
            "primary_evidence_path": "data/evidence/frames/segments_model_cam/frame_0.jpg",
            "evidence_frames": ["data/evidence/frames/segments_model_cam/frame_0.jpg"],
        },
        snapshot_path="data/evidence/frames/segments_model_cam/frame_0.jpg",
    )

    payload = db.list_segments_paginated(page=1, page_size=10)

    assert payload["items"][0]["model_used"] == "vision-alpha"
```

```python
def test_report_daily_recent_segments_expose_model_used(tmp_path: Path):
    db = Database(path=tmp_path / "report_model.db")
    camera = db.upsert_camera("report_model_cam", "Report Model Cam")
    job = db.schedule_job(
        camera["id"],
        payload={"llm_vision_model": "payload-model"},
    )
    db.create_segment(
        job_id=job["id"],
        camera_id=camera["id"],
        start_ts="2026-04-05T11:00:00+00:00",
        end_ts="2026-04-05T11:01:00+00:00",
        label="not_working",
        confidence=0.81,
        notes="machine idle",
        evidence_path="data/evidence/frames/report_model_cam/frame_0.jpg",
    )
    db.mark_job_finished(
        job["id"],
        "success",
        raw_result={
            "raw": {"model": "report-model-v2"},
            "primary_evidence_path": "data/evidence/frames/report_model_cam/frame_0.jpg",
            "evidence_frames": ["data/evidence/frames/report_model_cam/frame_0.jpg"],
        },
        snapshot_path="data/evidence/frames/report_model_cam/frame_0.jpg",
    )

    report = db.report_daily("2026-04-05")

    assert report["recent_segments"][0]["model_used"] == "report-model-v2"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_worker.py::test_list_segments_paginated_exposes_model_used tests/test_worker.py::test_report_daily_recent_segments_expose_model_used -v
```

Expected: FAIL because `model_used` is missing from segment/report payload items.

- [ ] **Step 3: Write minimal implementation**

Update the segment/report queries in `factory_analytics/database.py` so they select and preserve `model_used` the same way the jobs query already does.

For `list_segments_paginated`, extend the `SELECT` with:

```python
COALESCE(
    json_extract(j.raw_result, '$.raw.model'),
    json_extract(j.raw_result, '$.model'),
    json_extract(j.payload_json, '$.model'),
    json_extract(j.payload_json, '$.llm_vision_model')
) AS model_used
```

For `report_daily`, change the `segments` query to include both job payload/result data and computed model:

```python
segments = conn.execute(
    """SELECT s.*, c.name AS camera_name,
              j.raw_result,
              COALESCE(
                  json_extract(j.raw_result, '$.raw.model'),
                  json_extract(j.raw_result, '$.model'),
                  json_extract(j.payload_json, '$.model'),
                  json_extract(j.payload_json, '$.llm_vision_model')
              ) AS model_used
       FROM segments s
       JOIN cameras c ON c.id=s.camera_id
       LEFT JOIN jobs j ON j.id = s.job_id
       WHERE substr(s.start_ts,1,10)=?
       ORDER BY s.id DESC LIMIT 20""",
    (day,),
).fetchall()
```

For `list_segments_paginated`, keep the item conversion minimal:

```python
item = dict(row)
raw_result = item.get("raw_result")
item["raw_result"] = json.loads(raw_result) if raw_result else {}
payload_json = item.get("payload_json")
item["payload_json"] = json.loads(payload_json) if payload_json else {}
item["group_name"] = item["raw_result"].get("group_name")
item["group_type"] = item["raw_result"].get("group_type")
item["group_id"] = item["raw_result"].get("group_id")
items.append(item)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_worker.py::test_list_segments_paginated_exposes_model_used tests/test_worker.py::test_report_daily_recent_segments_expose_model_used -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_worker.py factory_analytics/database.py
git commit -m "feat: expose model metadata in segment and report payloads"
```

---

### Task 2: Show model names on report and photo surfaces

**Files:**
- Modify: `factory_analytics/static/photos.js`
- Modify: `factory_analytics/templates/photos.html`
- Modify: `factory_analytics/templates/history.html`
- Modify: `factory_analytics/static/app.js`
- Modify: `factory_analytics/templates/dashboard.html`
- Modify: `tests/test_ui_ux.py`

- [ ] **Step 1: Write the failing tests**

Add these assertions to `tests/test_ui_ux.py`:

```python
def test_photos_cards_and_modal_show_model_name():
    photos_js = Path("factory_analytics/static/photos.js").read_text()
    photos_html = Path("factory_analytics/templates/photos.html").read_text()

    assert "Model:" in photos_js
    assert "p.model_used" in photos_js
    assert "modalModel" in photos_html
```

Add this report/dashboard coverage test:

```python
def test_report_surfaces_show_model_name():
    history_html = Path("factory_analytics/templates/history.html").read_text()
    app_js = Path("factory_analytics/static/app.js").read_text()
    dashboard_html = Path("factory_analytics/templates/dashboard.html").read_text()

    assert "Model" in history_html
    assert "model_used" in history_html
    assert "model_used" in app_js
    assert "reportView" in dashboard_html
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_ui_ux.py::test_photos_cards_and_modal_show_model_name tests/test_ui_ux.py::test_report_surfaces_show_model_name -v
```

Expected: FAIL because the current Photos/Reports surfaces do not render model metadata inline.

- [ ] **Step 3: Write minimal implementation**

In `factory_analytics/static/photos.js`, render model text on the card and in modal metadata:

```javascript
const modelUsed = p.model_used || '-';
```

```javascript
<div class="text-xs text-on-surface-variant">
    Model: <span class="text-on-surface font-medium">${modelUsed}</span>
</div>
```

In the modal setup, populate a dedicated field:

```javascript
elements.modalModel.textContent = photo.model_used || '-';
```

In `factory_analytics/templates/photos.html`, add the modal slot:

```html
<div>
    <span class="text-xs font-label uppercase tracking-widest text-outline">Model</span>
    <p id="modalModel" class="text-sm text-on-surface mt-1"></p>
</div>
```

In `factory_analytics/templates/history.html`, add model text to the visible segment metadata block:

```html
<div class="text-[10px] text-outline uppercase font-label">Model</div>
<div class="text-xs text-on-surface">${s.model_used || '-'}</div>
```

In `factory_analytics/static/app.js`, make the dashboard report/recent-segment area show model names from `report.recent_segments`:

```javascript
const recentSegments = report.recent_segments || [];
```

```javascript
${recentSegments.slice(0, 3).map(s => `
  <div class="mt-2 p-2 bg-surface-container-low rounded">
    <div class="text-[10px] uppercase text-outline font-label">${s.camera_name}</div>
    <div class="text-xs text-on-surface">${s.reviewed_label || s.label}</div>
    <div class="text-[10px] text-on-surface-variant">Model: ${s.model_used || '-'}</div>
  </div>
`).join('')}
```

Append that block inside `loadReport()` beneath the velocity section.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_ui_ux.py::test_photos_cards_and_modal_show_model_name tests/test_ui_ux.py::test_report_surfaces_show_model_name -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_ui_ux.py factory_analytics/static/photos.js factory_analytics/templates/photos.html factory_analytics/templates/history.html factory_analytics/static/app.js factory_analytics/templates/dashboard.html
git commit -m "feat: show model names on photo and report surfaces"
```

---

### Task 3: Turn heatmap click details into a segment list with thumbnails and job-detail actions

**Files:**
- Modify: `factory_analytics/templates/efficiency.html`
- Modify: `factory_analytics/static/efficiency.js`
- Modify: `tests/test_ui_ux.py`

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_ui_ux.py`:

```python
def test_efficiency_drilldown_markup_includes_model_and_job_detail_hooks():
    eff_html = Path("factory_analytics/templates/efficiency.html").read_text()
    eff_js = Path("factory_analytics/static/efficiency.js").read_text()

    assert "popoverSegments" in eff_html
    assert "Open Job Details" in eff_js
    assert "model_used" in eff_js
    assert "No image" in eff_js
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_ui_ux.py::test_efficiency_drilldown_markup_includes_model_and_job_detail_hooks -v
```

Expected: FAIL because the current popover assumes one segment and only renders evidence links.

- [ ] **Step 3: Write minimal implementation**

First, change the popover shell in `factory_analytics/templates/efficiency.html` so JS has a list container instead of a single evidence row:

```html
<div class="space-y-2.5">
  <div id="popoverSummary" class="text-xs text-on-surface-variant"></div>
  <div id="popoverSegments" class="space-y-3"></div>
</div>
```

Then refactor `factory_analytics/static/efficiency.js` so daily grid cells pass the whole segment collection into `showPopover`:

```javascript
showPopover(e, {
  camera: cam.label,
  segments: segments.map(seg => ({
    id: seg.segment_id || seg.id || '',
    label: seg.label,
    confidence: Math.round((seg.confidence || 0) * 100),
    minutes: parseFloat(seg.duration_minutes) || 0,
    start_ts: seg.start_ts,
    end_ts: seg.end_ts,
  })),
});
```

Add a loader helper that enriches each segment row from existing APIs:

```javascript
async function loadSegmentPopoverItems(segments) {
  return Promise.all(segments.map(async (segment) => {
    const [detailResp, evidenceResp] = await Promise.all([
      fetch(`/api/history/segments/${segment.id}`),
      fetch(`/api/evidence/${segment.id}`),
    ]);
    const detail = detailResp.ok ? await detailResp.json() : {};
    const evidence = evidenceResp.ok ? await evidenceResp.json() : {};
    const frames = Array.isArray(evidence.evidence_frames) ? evidence.evidence_frames.filter(Boolean) : [];
    return {
      ...segment,
      camera_name: detail.camera_name || '',
      model_used: detail.model_used || '-',
      notes: detail.notes || '',
      thumbnail: frames[0] || evidence.evidence_path || '',
      job_id: detail.job_id || '',
      start_ts: detail.start_ts || segment.start_ts,
      end_ts: detail.end_ts || segment.end_ts,
    };
  }));
}
```

Render each row as a compact list item with first-frame thumbnail and button:

```javascript
function renderPopoverSegmentItem(item) {
  const labelName = STATUS_LABELS[item.label] || item.label;
  const thumb = item.thumbnail
    ? `<img src="/${item.thumbnail}" alt="${labelName} thumbnail" class="w-16 h-12 object-cover rounded border border-outline-variant/20">`
    : `<div class="w-16 h-12 rounded border border-outline-variant/20 flex items-center justify-center text-[10px] text-on-surface-variant">No image</div>`;

  return `
    <div class="rounded-lg border border-outline-variant/20 p-3 bg-surface-container-lowest">
      <div class="flex gap-3">
        <div class="flex-shrink-0">${thumb}</div>
        <div class="flex-1 min-w-0">
          <div class="text-xs font-bold text-on-surface">${item.camera_name || '-'}</div>
          <div class="text-[11px] text-on-surface-variant">${labelName} · ${item.confidence}% · ${item.minutes} min</div>
          <div class="text-[11px] text-on-surface-variant">Model: ${item.model_used || '-'}</div>
          <div class="text-[11px] text-on-surface-variant">${new Date(item.start_ts).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})} - ${new Date(item.end_ts).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</div>
          <button type="button" class="mt-2 text-xs font-medium text-primary hover:underline" data-job-id="${item.job_id}">Open Job Details</button>
        </div>
      </div>
    </div>`;
}
```

Update `showPopover()` to:

```javascript
document.getElementById('popoverTitle').textContent = meta.camera || 'Activity Details';
document.getElementById('popoverSummary').textContent = `${meta.segments.length} segment${meta.segments.length === 1 ? '' : 's'}`;
const items = await loadSegmentPopoverItems(meta.segments);
document.getElementById('popoverSegments').innerHTML = items.map(renderPopoverSegmentItem).join('');
```

Add delegated click handling for the job-detail button and reuse the existing modal path by segment → job lookup:

```javascript
document.getElementById('popoverSegments').addEventListener('click', (e) => {
  const button = e.target.closest('[data-job-id]');
  if (!button) return;
  hidePopover();
  showJobDetailsFromEfficiency(button.dataset.jobId);
});
```

Add a local helper that opens the existing Jobs page detail surface in a new tab without duplicating the job modal logic in efficiency:

```javascript
function showJobDetailsFromEfficiency(jobId) {
  if (!jobId) return;
  window.open(`/jobs?job=${jobId}`, '_blank');
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_ui_ux.py::test_efficiency_drilldown_markup_includes_model_and_job_detail_hooks -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_ui_ux.py factory_analytics/templates/efficiency.html factory_analytics/static/efficiency.js
git commit -m "feat: add list-based efficiency heatmap drilldown"
```

---

### Task 4: Show model in full job details and run focused regression checks

**Files:**
- Modify: `factory_analytics/templates/jobs.html`
- Modify: `tests/test_ui_ux.py`
- Modify: `tests/test_worker.py`

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_ui_ux.py`:

```python
def test_job_details_surface_shows_model_metadata():
    jobs_html = Path("factory_analytics/templates/jobs.html").read_text()

    assert "Model" in jobs_html
    assert "modal-job-info" in jobs_html
    assert "job.model_used" in jobs_html or "model_used" in jobs_html
```
```

- [ ] **Step 2: Run test to verify it fails for the new requirement**

Run:

```bash
pytest tests/test_ui_ux.py::test_job_details_surface_shows_model_metadata -v
```

Expected: FAIL because the row has model already, but the full job details metadata block does not show it yet.

- [ ] **Step 3: Write minimal implementation**

In `factory_analytics/templates/jobs.html`, extend the modal job info HTML with a model card:

```javascript
<div class="bg-surface-container-lowest p-3 rounded-lg">
    <div class="text-xs text-outline font-label uppercase mb-1">Model</div>
    <div class="text-sm font-medium">${job.model_used || '-'}</div>
</div>
```

Keep the existing details surface canonical by leaving request/response/snapshot sections intact.

Then run the focused regression suite for all touched surfaces:

```bash
pytest tests/test_worker.py::test_list_segments_paginated_exposes_model_used tests/test_worker.py::test_report_daily_recent_segments_expose_model_used tests/test_ui_ux.py::test_photos_cards_and_modal_show_model_name tests/test_ui_ux.py::test_report_surfaces_show_model_name tests/test_ui_ux.py::test_efficiency_drilldown_markup_includes_model_and_job_detail_hooks tests/test_ui_ux.py::test_job_details_surface_shows_model_metadata -v
```

Expected: PASS

- [ ] **Step 4: Run the broader safety suite**

Run:

```bash
pytest tests/test_ui_ux.py tests/test_evidence_api.py -v
```

Expected: PASS, except for any known unrelated pre-existing template-cache failures already documented in this branch. If one of those unrelated failures appears, record it in the task notes and do not change unrelated code.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ui_ux.py tests/test_worker.py factory_analytics/templates/jobs.html
git commit -m "feat: surface model metadata across job details"
```

---

## Self-Review Checklist

- Spec coverage:
  - Efficiency drilldown list with thumbnails/model/action: Task 3
  - Model visible on Reports / Photos / Jobs: Tasks 2 and 4
  - Full job details remain canonical: Task 4
  - Backend list/report payloads expose `model_used`: Task 1
  - Focused API/UI tests: Tasks 1-4
- Placeholder scan:
  - No `TODO`, `TBD`, or “similar to task above” shortcuts remain.
- Type consistency:
  - Use `model_used` consistently across backend payloads and frontend renderers.
  - Use `job_id` for drilldown action handoff.

---

## Notes for the implementer

- Do not redesign navigation or add a global drawer.
- Do not move full evidence galleries into the heatmap drilldown.
- Keep the heatmap drilldown compact; only first-frame thumbnail belongs there.
- If a thumbnail is missing, render a placeholder block instead of leaving empty space.
- If job details later need true in-page modal reuse from Efficiency, do that in a follow-up spec; this plan keeps scope aligned by routing to the existing Jobs detail surface.
