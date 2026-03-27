# Ollama Settings And Annotated Evidence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose real Ollama runtime settings in the UI, add a true Ollama vision test using current saved settings, remove stale fallback config, and save evidence images with person bounding boxes drawn from the configured `qwen3.5:9b` response.

**Architecture:** Keep the configured Ollama model as the sole inference path. Extend the Ollama response contract to include `boxes`, validate it strictly, and draw rectangles onto the saved evidence image before persisting its path. Use full-resolution Frigate snapshots for LLM input and save full-resolution annotated evidence; only the browser display may be thumbnail-sized. Add a dedicated settings-page test endpoint that runs the real snapshot-to-LLM path using saved settings and reports honest failure reasons.

**Tech Stack:** FastAPI, SQLite, vanilla JS, Jinja2, Pillow/PIL-style image annotation in Python, httpx.

---

### Task 1: Expose real Ollama settings in Settings UI

**Files:**
- Modify: `factory_analytics/templates/settings.html`
- Modify: `factory_analytics/static/app.js`

**Step 1: Write the failing UI expectation**

Add/extend a UI test expectation for visible Ollama fields:

```python
def test_settings_page_shows_ollama_controls(client):
    html = client.get('/settings').text
    assert 'name="ollama_url"' in html
    assert 'name="ollama_vision_model"' in html
    assert 'name="ollama_timeout_sec"' in html
    assert 'name="ollama_keep_alive"' in html
    assert 'name="ollama_enabled"' in html
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_ux.py::test_settings_page_shows_ollama_controls -v`
Expected: FAIL because `ollama_keep_alive` and `ollama_enabled` are not rendered yet.

**Step 3: Write minimal implementation**

- Add visible fields for:
  - `ollama_url`
  - `ollama_vision_model`
  - `ollama_timeout_sec`
  - `ollama_keep_alive`
  - `ollama_enabled`
- Ensure `saveSettings()` serializes booleans and numeric timeout correctly.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui_ux.py::test_settings_page_shows_ollama_controls -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_ui_ux.py factory_analytics/templates/settings.html factory_analytics/static/app.js
git commit -m "feat(settings): expose full ollama runtime controls"
```

### Task 2: Add a true Ollama vision test endpoint

**Files:**
- Modify: `factory_analytics/main.py`
- Modify: `factory_analytics/services.py`
- Modify: `factory_analytics/static/app.js`
- Modify: `factory_analytics/templates/settings.html`

**Step 1: Write the failing backend test**

```python
def test_ollama_test_endpoint_returns_honest_result(client):
    response = client.post('/api/settings/ollama/test')
    assert response.status_code in (200, 503, 500)
    payload = response.json()
    assert 'ok' in payload
    assert 'message' in payload
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py::test_ollama_test_endpoint_returns_honest_result -v`
Expected: FAIL because endpoint does not exist.

**Step 3: Write minimal implementation**

- Add `POST /api/settings/ollama/test`
- Service behavior:
  - load current saved settings from DB
  - verify Ollama `/api/tags`
  - verify configured model exists
  - choose one enabled camera with a real Frigate name
  - capture a fresh snapshot
  - run `classify_image()` with current saved settings
  - return:

```json
{
  "ok": true,
  "model": "qwen3.5:9b",
  "camera": "camera_88_10",
  "label": "idle",
  "confidence": 0.81,
  "message": "Vision test passed"
}
```

or a strict failure payload with exact reason.

**Step 4: Add the settings-page button**

- Add `Test Ollama Vision` button and inline result area.
- Use saved settings only; instruct user to save first if fields changed.

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_api.py::test_ollama_test_endpoint_returns_honest_result -v`
Expected: PASS

**Step 6: Commit**

```bash
git add tests/test_api.py factory_analytics/main.py factory_analytics/services.py factory_analytics/templates/settings.html factory_analytics/static/app.js
git commit -m "feat(settings): add ollama vision diagnostics endpoint and ui"
```

### Task 3: Remove stale fallback config from runtime and docs

**Files:**
- Modify: `factory_analytics/database.py`
- Modify: `docs/implementation/2026-03-28-camera-management.md`
- Modify: `docs/todos.md`
- Modify: `docs/features.md`

**Step 1: Write the failing expectation**

Documented/runtime setting `ollama_fallback_to_vision` should no longer exist.

**Step 2: Run a direct verification command**

Run: `python3 - << 'PY'
import sqlite3
conn = sqlite3.connect('data/db/factory_analytics.db')
print(conn.execute("select count(*) from settings where key='ollama_fallback_to_vision'").fetchone()[0])
PY`
Expected: currently `1`

**Step 3: Write minimal implementation**

- Remove default creation of `ollama_fallback_to_vision`
- If present in DB, ignore it in code and document it as deprecated/cleanup target
- Update docs to state `qwen3.5:9b` only, no fallback.

**Step 4: Run verification**

Run the same python command and app smoke checks.
Expected: either key removed or harmlessly ignored and documented as deprecated.

**Step 5: Commit**

```bash
git add factory_analytics/database.py docs/implementation/2026-03-28-camera-management.md docs/todos.md docs/features.md
git commit -m "chore(settings): remove stale ollama fallback configuration"
```

### Task 4: Extend Ollama response contract with person boxes

**Files:**
- Modify: `factory_analytics/integrations/ollama.py`
- Test: `tests/test_ollama_integration.py`

**Step 1: Write the failing test**

```python
def test_classify_image_requires_boxes_when_people_detected(tmp_path):
    client = OllamaClient({...})
    # mock client.post() to return valid JSON with label/confidence/notes/boxes
    # assert parsed boxes survive
```

Also add an invalid test where non-JSON or invalid boxes raise a failure.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ollama_integration.py -v`
Expected: FAIL because `boxes` are not parsed/validated yet.

**Step 3: Write minimal implementation**

- Update prompt to require JSON keys:
  - `label`
  - `confidence`
  - `notes`
  - `boxes`
- Validate:
  - `boxes` is an array
  - each item has `label="person"` and `box=[x,y,width,height]`
  - coordinates are floats in `0..1`
- If invalid, raise a real failure.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ollama_integration.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_ollama_integration.py factory_analytics/integrations/ollama.py
git commit -m "feat(ollama): require structured person boxes in vision response"
```

### Task 5: Draw rectangles and save full-resolution annotated evidence images

**Files:**
- Modify: `factory_analytics/services.py`
- Create: `factory_analytics/image_annotations.py`
- Test: `tests/test_image_annotations.py`

**Step 1: Write the failing test**

```python
def test_draw_person_boxes_writes_annotated_image(tmp_path):
    input_image = tmp_path / 'in.jpg'
    output_image = tmp_path / 'out.jpg'
    boxes = [{"label": "person", "box": [0.1, 0.2, 0.3, 0.4]}]
    draw_person_boxes(input_image, output_image, boxes)
    assert output_image.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_image_annotations.py -v`
Expected: FAIL because annotation helper does not exist.

**Step 3: Write minimal implementation**

- Add helper that:
  - opens snapshot image
  - converts normalized coords to pixels
  - draws rectangular boxes and optional label text
  - saves annotated output image
- In `process_one_pending_job()`:
  - capture full-resolution raw snapshot
  - classify image and read `boxes`
  - write full-resolution annotated image
  - store annotated image path as `evidence_path`

**Step 3a: Preserve full resolution for inference**

- Remove any Frigate snapshot downscaling query parameters used for LLM input
- Ensure the image passed into `classify_image()` is the original full-resolution snapshot
- Keep thumbnail sizing as a presentation concern in the UI only

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_image_annotations.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_image_annotations.py factory_analytics/image_annotations.py factory_analytics/services.py
git commit -m "feat(evidence): save annotated snapshots with person bounding boxes"
```

### Task 6: Verify end-to-end UI evidence and diagnostics

**Files:**
- Modify: `tests/test_ui_ux.py`

**Step 1: Write the failing smoke test**

```python
def test_history_evidence_renders_image_tag(client):
    html = client.get('/history').text
    assert 'Evidence' in html
```

Add a JS/template-level assertion if the history table is server-rendered or keep as smoke plus manual verification.

**Step 2: Run tests**

Run: `pytest -q`
Expected: all tests pass.

**Step 3: Manual verification**

- Save settings with `qwen3.5:9b`, timeout 600, keep_alive 5m
- Click `Test Ollama Vision` in Settings
- Test a working camera row
- Open History and confirm evidence thumbnails show annotated rectangles while the underlying saved evidence file remains full resolution
- Delete a camera from the app only and confirm it disappears

**Step 4: Commit**

```bash
git add tests/test_ui_ux.py
git commit -m "test(ui): verify ollama diagnostics and annotated evidence flow"
```
