# Multi-Frame Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update single-camera and group analysis so the LLM consumes time-sequenced evidence frames, returns only `working|not_working|no_person|uncertain`, removes bounding boxes entirely, and exposes all evidence images in jobs/photos/reports.

**Architecture:** Keep the existing FastAPI + service-layer pipeline, but simplify the LLM contract and evidence model. Single-camera jobs will send raw captured frames directly; group jobs will send one labeled collage per second; backend logic will normalize outputs and enforce the `any working wins` group rule while UI/API surfaces move from single-image assumptions to `evidence_frames` arrays.

**Tech Stack:** Python, FastAPI, Jinja templates, vanilla JS, sqlite JSON storage, Pillow, pytest

---

## File structure and responsibilities

- `factory_analytics/integrations/ollama.py`
  - Own the prompt text, response schema, label normalization, and OpenAI-compatible request payloads.
  - Remove `boxes` parsing and add optional per-frame/group observations needed for deterministic backend aggregation.
- `factory_analytics/services.py`
  - Own job processing, evidence capture/storage, single-camera/group result assembly, and group rule enforcement.
  - Remove annotation generation and canonicalize `evidence_frames` / `primary_evidence_path`.
- `factory_analytics/main.py`
  - Own lightweight API payload shaping, especially `/api/evidence/{segment_id}`.
- `factory_analytics/static/photos.js`
  - Own gallery card rendering and modal rendering for all evidence frames.
- `factory_analytics/static/app.js`
  - Own dashboard/history/evidence previews that currently assume one image path.
- `factory_analytics/static/efficiency.js`
  - Own evidence popovers and “view evidence” actions.
- `factory_analytics/image_annotations.py`
  - No longer needed after migration; remove usage first, then delete file.
- `tests/test_ollama_test_api.py`
  - Add/adjust API-level checks for test endpoint and label model assumptions.
- `tests/test_worker.py`
  - Add/adjust worker/service integration tests for single and group job processing.
- `tests/test_ui_ux.py` or a more focused new UI test file if one already covers photo/history HTML/API wiring
  - Verify evidence API payload shape and multi-image rendering assumptions.

---

### Task 1: Simplify the LLM contract to the 4-label schema

**Files:**
- Modify: `factory_analytics/integrations/ollama.py`
- Test: `tests/test_worker.py`

- [ ] **Step 1: Write the failing tests for label normalization and response parsing**

```python
from factory_analytics.integrations.ollama import normalize_label, OpenAIClient


def test_normalize_label_maps_new_public_labels_only():
    assert normalize_label("working") == "working"
    assert normalize_label("not working") == "not_working"
    assert normalize_label("no person") == "no_person"
    assert normalize_label("uncertain") == "uncertain"


def test_parse_classification_content_accepts_schema_without_boxes():
    client = OpenAIClient(
        {
            "llm_url": "http://127.0.0.1:11434",
            "llm_vision_model": "gemma4:e4b",
            "llm_timeout_sec": 120,
            "llm_enabled": True,
        }
    )

    payload = client._parse_classification_content(
        '{"label":"working","confidence":0.88,"notes":"activity seen in frames 2-3"}',
        group_mode=False,
    )

    assert payload == {
        "label": "working",
        "confidence": 0.88,
        "notes": "activity seen in frames 2-3",
    }
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
pytest tests/test_worker.py -k "normalize_label or schema_without_boxes" -v
```

Expected:
- FAIL because `normalize_label()` still returns legacy values like `idle` / `operator_missing`
- FAIL because `_parse_classification_content()` still expects or emits `boxes`

- [ ] **Step 3: Replace the legacy prompts and label set with the 4-label schema**

Update `factory_analytics/integrations/ollama.py` so the constants and valid labels look like this:

```python
SINGLE_CAMERA_PROMPT = (
    "You are a strict factory work-state auditor. Analyze the provided images conservatively and only report what is directly visible. "
    "These images are sequential frames from the SAME camera and SAME place. "
    "Each frame is approximately {seconds}s apart.\n"
    "Rules:\n"
    "1. Only use directly visible evidence.\n"
    "2. Do not infer a worker from machine motion, shadows, cloth, sacks, chairs, reflections, or hidden areas.\n"
    "3. If a person is clearly visible and actively engaged in productive physical work, use 'working'.\n"
    "4. If a person is visible but inactive or not productively engaged, use 'not_working'.\n"
    "5. If no person is clearly visible across the sequence, use 'no_person'.\n"
    "6. If evidence is weak, blocked, blurred, or ambiguous, use 'uncertain'.\n"
    "Return STRICT JSON ONLY with these exact keys:\n"
    '{"label":"working|not_working|no_person|uncertain","confidence":0.0,"notes":"short reason"}'
)

GROUP_PROMPT = (
    "You are a strict factory work-state auditor. Analyze the provided images conservatively and only report what is directly visible. "
    "Each image is a merged collage for one second in time, and each collage contains multiple labeled camera views. "
    "These collages are sequential and approximately {seconds}s apart.\n"
    "Rules:\n"
    "1. Only use directly visible evidence.\n"
    "2. If any camera clearly shows productive work in any collage, the correct final label is 'working'.\n"
    "3. If people are visible but not productively engaged, use 'not_working'.\n"
    "4. If no person is clearly visible across all collages, use 'no_person'.\n"
    "5. If evidence is weak or ambiguous, use 'uncertain'.\n"
    "Return STRICT JSON ONLY with these exact keys:\n"
    '{"label":"working|not_working|no_person|uncertain","confidence":0.0,"notes":"short reason"}'
)

VALID_LABELS = {"working", "not_working", "no_person", "uncertain"}
```

- [ ] **Step 4: Replace the label aliases and parser output to remove boxes**

In `factory_analytics/integrations/ollama.py`, change `normalize_label()` and `_parse_classification_content()` to this shape:

```python
def normalize_label(raw_label: str) -> str | None:
    label = (raw_label or "").strip().lower().replace("-", " ")
    aliases = {
        "working": "working",
        "active": "working",
        "productive": "working",
        "not working": "not_working",
        "idle": "not_working",
        "inactive": "not_working",
        "time pass": "not_working",
        "timepass": "not_working",
        "stopped": "not_working",
        "sleeping": "not_working",
        "sleep suspect": "not_working",
        "operator missing": "no_person",
        "no person": "no_person",
        "no people": "no_person",
        "no worker": "no_person",
        "no human": "no_person",
        "uncertain": "uncertain",
        "unknown": "uncertain",
    }
    return aliases.get(label)


def _parse_classification_content(self, content: str, *, group_mode: bool) -> dict[str, Any]:
    text = content.strip()
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError(f"Model {self.model} did not return JSON: {content[:300]}")
        text = text[start : end + 1]

    parsed = json.loads(text)
    raw_label = parsed.get("label", "uncertain")
    label = normalize_label(raw_label)
    if label not in VALID_LABELS:
        raise RuntimeError(f"Model {self.model} returned invalid label: {raw_label}")

    confidence = float(parsed.get("confidence", 0.0))
    if not (0.0 <= confidence <= 1.0):
        raise RuntimeError(f"Model {self.model} returned confidence out of range: {confidence}")

    return {
        "label": label,
        "confidence": confidence,
        "notes": parsed.get("notes", ""),
    }
```

- [ ] **Step 5: Run the focused tests to verify they pass**

Run:
```bash
pytest tests/test_worker.py -k "normalize_label or schema_without_boxes" -v
```

Expected:
- PASS for both new tests

- [ ] **Step 6: Commit**

```bash
git add tests/test_worker.py factory_analytics/integrations/ollama.py
git commit -m "refactor: simplify llm classification schema"
```

---

### Task 2: Add optional per-frame observations for deterministic group aggregation

**Files:**
- Modify: `factory_analytics/integrations/ollama.py`
- Test: `tests/test_worker.py`

- [ ] **Step 1: Write the failing test for optional observations**

```python
from factory_analytics.integrations.ollama import OpenAIClient


def test_parse_classification_content_preserves_optional_observations():
    client = OpenAIClient(
        {
            "llm_url": "http://127.0.0.1:11434",
            "llm_vision_model": "gemma4:e4b",
            "llm_timeout_sec": 120,
            "llm_enabled": True,
        }
    )

    payload = client._parse_classification_content(
        '{"label":"not_working","confidence":0.62,"notes":"person visible but inactive","observations":[{"frame_index":0,"label":"not_working"},{"frame_index":1,"label":"working"}] }',
        group_mode=True,
    )

    assert payload["label"] == "not_working"
    assert payload["observations"] == [
        {"frame_index": 0, "label": "not_working"},
        {"frame_index": 1, "label": "working"},
    ]
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest tests/test_worker.py -k observations -v
```

Expected:
- FAIL because `observations` is ignored or dropped

- [ ] **Step 3: Extend prompts to request optional frame observations**

Append this instruction to both prompt constants in `factory_analytics/integrations/ollama.py`:

```python
"Optional: include an 'observations' array like [{\"frame_index\":0,\"label\":\"working|not_working|no_person|uncertain\",\"notes\":\"optional short note\"}] when useful. "
```

- [ ] **Step 4: Preserve normalized observations in the parser**

In `_parse_classification_content()` add this block before returning:

```python
observations = []
for item in parsed.get("observations", []):
    if not isinstance(item, dict):
        continue
    normalized = normalize_label(str(item.get("label", "")))
    if normalized not in VALID_LABELS:
        continue
    try:
        frame_index = int(item.get("frame_index", 0))
    except (TypeError, ValueError):
        continue
    observations.append(
        {
            "frame_index": frame_index,
            "label": normalized,
            "notes": str(item.get("notes", "") or ""),
        }
    )
```

Return it only when present:

```python
result = {
    "label": label,
    "confidence": confidence,
    "notes": parsed.get("notes", ""),
}
if observations:
    result["observations"] = observations
return result
```

- [ ] **Step 5: Run the focused test to verify it passes**

Run:
```bash
pytest tests/test_worker.py -k observations -v
```

Expected:
- PASS for the new observations test

- [ ] **Step 6: Commit**

```bash
git add tests/test_worker.py factory_analytics/integrations/ollama.py
git commit -m "feat: preserve optional llm frame observations"
```

---

### Task 3: Canonicalize single-camera evidence storage around raw frames

**Files:**
- Modify: `factory_analytics/services.py`
- Test: `tests/test_worker.py`

- [ ] **Step 1: Write the failing single-camera evidence storage test**

```python
from pathlib import Path
from factory_analytics.database import Database
from factory_analytics.services import AnalyticsService


def test_single_job_stores_raw_evidence_frames(tmp_path, monkeypatch):
    db = Database(tmp_path / "app.db")
    service = AnalyticsService(db)
    camera = db.upsert_camera("cam_a", "Cam A")
    db.update_camera(camera["id"], {"enabled": 1, "interval_seconds": 3})
    db.update_settings({"llm_frames_per_process": 3, "llm_seconds_window": 3})

    frame_dir = tmp_path / "frames"
    frame_dir.mkdir()
    frame_paths = []
    for idx in range(3):
        p = frame_dir / f"frame_{idx}.jpg"
        p.write_bytes(b"jpg")
        frame_paths.append(p)

    monkeypatch.setattr(
        service,
        "_process_frame_collection_for_camera",
        lambda camera, settings: {"strip_path": frame_paths[0], "frame_paths": frame_paths},
    )
    monkeypatch.setattr(
        service,
        "ollama_client",
        lambda: type(
            "Client",
            (),
            {
                "classify_images": lambda self, images, seconds_apart=1: {
                    "label": "working",
                    "confidence": 0.9,
                    "notes": "activity seen in frames 2-3",
                }
            },
        )(),
    )

    job = db.schedule_job(camera["id"], payload={})
    result = service._process_single_job(job)
    stored = result["job"]["raw_result"]

    assert stored["evidence_frames"]
    assert stored["primary_evidence_path"] == stored["evidence_frames"][0]
    assert result["segment"]["evidence_path"] == stored["primary_evidence_path"]
    assert "evidence_paths" not in stored
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest tests/test_worker.py -k raw_evidence_frames -v
```

Expected:
- FAIL because the service still writes annotated paths and `evidence_paths`

- [ ] **Step 3: Remove annotation generation from `_process_single_job()`**

Replace the evidence-writing block in `factory_analytics/services.py` with this simpler structure:

```python
frame_result = self._process_frame_collection_for_camera(camera, img_settings)
frame_paths = frame_result["frame_paths"]
images_to_send = frame_paths or [frame_result["strip_path"]]
seconds_apart = img_settings.get("seconds_window", 1)
result = self.ollama_client().classify_images(images_to_send, seconds_apart=seconds_apart)

stored_frames = [str(p.relative_to(DATA_ROOT.parent)) for p in images_to_send]
primary_evidence_path = stored_frames[0]

segment = self.db.create_segment(
    job_id=job["id"],
    camera_id=camera["id"],
    start_ts=start_ts,
    end_ts=end_ts,
    label=result["label"],
    confidence=float(result["confidence"]),
    notes=result.get("notes", ""),
    evidence_path=primary_evidence_path,
)

stored_result = {
    **result,
    "frame_count": len(stored_frames),
    "primary_evidence_path": primary_evidence_path,
    "evidence_frames": stored_frames,
}

self.db.mark_job_finished(
    job["id"],
    "success",
    raw_result=stored_result,
    snapshot_path=primary_evidence_path,
)
```

- [ ] **Step 4: Make `_process_frame_collection_for_camera()` always return concrete frame files**

Adjust `factory_analytics/services.py` so `count <= 1` returns the same evidence model as multi-frame capture:

```python
if count <= 1:
    single = self._capture_snapshot(camera_name)
    return {
        "strip_path": single,
        "frame_paths": [single],
    }
```

- [ ] **Step 5: Run the focused test to verify it passes**

Run:
```bash
pytest tests/test_worker.py -k raw_evidence_frames -v
```

Expected:
- PASS for the new single-job evidence test

- [ ] **Step 6: Commit**

```bash
git add tests/test_worker.py factory_analytics/services.py
git commit -m "refactor: store raw evidence frames for single jobs"
```

---

### Task 4: Canonicalize group evidence storage and enforce “any working wins”

**Files:**
- Modify: `factory_analytics/services.py`
- Test: `tests/test_worker.py`

- [ ] **Step 1: Write the failing group aggregation test**

```python
from factory_analytics.database import Database
from factory_analytics.services import AnalyticsService


def test_group_job_enforces_any_working_wins(tmp_path, monkeypatch):
    db = Database(tmp_path / "app.db")
    service = AnalyticsService(db)

    cam_a = db.upsert_camera("cam_a", "Cam A")
    cam_b = db.upsert_camera("cam_b", "Cam B")
    group = db.create_group("line", "Line 1", 300)
    db.add_camera_to_group(group["id"], cam_a["id"])
    db.add_camera_to_group(group["id"], cam_b["id"])

    collage_dir = tmp_path / "collages"
    collage_dir.mkdir()
    collage_paths = []
    for idx in range(3):
        p = collage_dir / f"frame_{idx}_collage.jpg"
        p.write_bytes(b"jpg")
        collage_paths.append(p)

    monkeypatch.setattr(
        service,
        "_process_frame_collection_for_camera",
        lambda camera, settings: {"strip_path": collage_paths[0], "frame_paths": collage_paths},
    )
    monkeypatch.setattr(
        "factory_analytics.services.build_group_collage",
        lambda frame_cameras, output_path: collage_paths[int(output_path.stem.split('_')[1])],
    )
    monkeypatch.setattr(
        service,
        "ollama_client",
        lambda: type(
            "Client",
            (),
            {
                "classify_group_images": lambda self, images, seconds_apart=1, camera_count=1: {
                    "label": "not_working",
                    "confidence": 0.61,
                    "notes": "mixed activity",
                    "observations": [
                        {"frame_index": 0, "label": "not_working"},
                        {"frame_index": 1, "label": "working"},
                        {"frame_index": 2, "label": "not_working"},
                    ],
                }
            },
        )(),
    )

    job = db.schedule_group_job(cam_a["id"], group["id"], group["group_type"], group["name"])
    result = service._execute_group_analysis(job, group["id"])
    stored = db.get_job(job["id"])["raw_result"]

    assert stored["label"] == "working"
    assert stored["primary_evidence_path"] == stored["evidence_frames"][0]
    assert len(stored["evidence_frames"]) == 3
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest tests/test_worker.py -k any_working_wins -v
```

Expected:
- FAIL because the group job still trusts the LLM final label and stores one annotated image

- [ ] **Step 3: Add a deterministic helper to enforce the group rule**

In `factory_analytics/services.py`, add this helper near the other private helpers:

```python
def _apply_group_label_rule(self, result: dict[str, Any]) -> dict[str, Any]:
    observations = result.get("observations") or []
    if any(item.get("label") == "working" for item in observations):
        return {
            **result,
            "label": "working",
            "notes": result.get("notes") or "working activity visible in at least one collage",
        }
    return result
```

- [ ] **Step 4: Replace annotated group evidence with raw collages and apply the helper**

Update `_execute_group_analysis()` in `factory_analytics/services.py` so the post-LLM block looks like this:

```python
result = self.ollama_client().classify_group_images(
    per_frame_collages,
    seconds_apart=seconds_apart,
    camera_count=len(included_cameras),
)
result = self._apply_group_label_rule(result)

notes = result.get("notes", "")
if missing_cameras:
    suffix = f" Missing cameras: {', '.join(missing_cameras)}."
    notes = f"{notes}{suffix}".strip()

stored_frames = [str(p.relative_to(DATA_ROOT.parent)) for p in per_frame_collages]
primary_evidence_path = stored_frames[0]

segment = self.db.create_segment(
    job_id=job["id"],
    camera_id=anchor_camera["id"],
    start_ts=start_ts,
    end_ts=end_ts,
    label=result["label"],
    confidence=float(result["confidence"]),
    notes=notes,
    evidence_path=primary_evidence_path,
)

stored_result = {
    **result,
    "notes": notes,
    "frame_count": len(stored_frames),
    "primary_evidence_path": primary_evidence_path,
    "evidence_frames": stored_frames,
    "included_cameras": included_cameras,
    "missing_cameras": missing_cameras,
    "group_id": group_id,
    "group_name": group["name"],
    "group_type": group["group_type"],
    "segment_id": segment["id"],
}

self.db.mark_job_finished(
    job["id"],
    "success",
    raw_result=stored_result,
    snapshot_path=primary_evidence_path,
)
```

- [ ] **Step 5: Run the focused test to verify it passes**

Run:
```bash
pytest tests/test_worker.py -k any_working_wins -v
```

Expected:
- PASS for the new group aggregation test

- [ ] **Step 6: Commit**

```bash
git add tests/test_worker.py factory_analytics/services.py
git commit -m "feat: enforce any-working-wins for group analysis"
```

---

### Task 5: Remove dead annotation imports and code paths

**Files:**
- Modify: `factory_analytics/services.py`
- Delete: `factory_analytics/image_annotations.py`
- Test: `tests/test_worker.py`

- [ ] **Step 1: Write the failing regression test that annotation code is no longer referenced**

```python
from pathlib import Path


def test_services_module_no_longer_imports_image_annotations():
    source = Path("factory_analytics/services.py").read_text()
    assert "image_annotations" not in source
    assert "draw_person_boxes" not in source
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest tests/test_worker.py -k image_annotations -v
```

Expected:
- FAIL because `services.py` still imports and references `draw_person_boxes`

- [ ] **Step 3: Remove the import and delete the unused module**

Update `factory_analytics/services.py` imports to remove:

```python
from factory_analytics.image_annotations import draw_person_boxes
```

Then delete `factory_analytics/image_annotations.py` entirely.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
pytest tests/test_worker.py -k image_annotations -v
```

Expected:
- PASS for the no-annotation regression test

- [ ] **Step 5: Commit**

```bash
git add factory_analytics/services.py tests/test_worker.py
git rm factory_analytics/image_annotations.py
git commit -m "refactor: remove bounding box annotation pipeline"
```

---

### Task 6: Expose canonical `evidence_frames` in the evidence API

**Files:**
- Modify: `factory_analytics/main.py`
- Test: `tests/test_api_settings.py` or a new focused API test file if existing evidence tests live elsewhere

- [ ] **Step 1: Write the failing API test**

```python
from fastapi.testclient import TestClient
from factory_analytics.main import app, db

client = TestClient(app)


def test_evidence_endpoint_returns_primary_and_all_frames():
    camera = db.upsert_camera("cam_evidence", "Cam Evidence")
    job = db.schedule_job(camera["id"], payload={})
    segment = db.create_segment(
        job_id=job["id"],
        camera_id=camera["id"],
        start_ts="2026-04-05T00:00:00+00:00",
        end_ts="2026-04-05T00:00:03+00:00",
        label="working",
        confidence=0.9,
        notes="activity seen in frames 2-3",
        evidence_path="data/evidence/frames/cam_evidence/frame_0.jpg",
    )
    db.mark_job_finished(
        job["id"],
        "success",
        raw_result={
            "primary_evidence_path": "data/evidence/frames/cam_evidence/frame_0.jpg",
            "evidence_frames": [
                "data/evidence/frames/cam_evidence/frame_0.jpg",
                "data/evidence/frames/cam_evidence/frame_1.jpg",
            ],
        },
        snapshot_path="data/evidence/frames/cam_evidence/frame_0.jpg",
    )

    response = client.get(f"/api/evidence/{segment['id']}")
    assert response.status_code == 200
    assert response.json() == {
        "segment_id": segment["id"],
        "evidence_path": "data/evidence/frames/cam_evidence/frame_0.jpg",
        "evidence_frames": [
            "data/evidence/frames/cam_evidence/frame_0.jpg",
            "data/evidence/frames/cam_evidence/frame_1.jpg",
        ],
    }
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest tests/test_api_settings.py -k evidence_frames -v
```

Expected:
- FAIL because `/api/evidence/{segment_id}` still returns `frame_paths`

- [ ] **Step 3: Update the endpoint payload**

In `factory_analytics/main.py`, replace the endpoint body with:

```python
raw_result = segment.get("raw_result") or {}
return {
    "segment_id": segment_id,
    "evidence_path": raw_result.get("primary_evidence_path") or segment.get("evidence_path"),
    "evidence_frames": raw_result.get("evidence_frames", []),
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
pytest tests/test_api_settings.py -k evidence_frames -v
```

Expected:
- PASS for the evidence API test

- [ ] **Step 5: Commit**

```bash
git add tests/test_api_settings.py factory_analytics/main.py
git commit -m "feat: expose canonical evidence frames api"
```

---

### Task 7: Update the photos UI to render all evidence frames

**Files:**
- Modify: `factory_analytics/static/photos.js`
- Test: `tests/test_ui_ux.py` or a new focused UI test file

- [ ] **Step 1: Write the failing UI rendering test**

```python
from pathlib import Path


def test_photos_modal_uses_evidence_frames_gallery():
    source = Path("factory_analytics/static/photos.js").read_text()
    assert "evidence_frames" in source
    assert "modalGallery" in source or "modalFrames" in source
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest tests/test_ui_ux.py -k evidence_frames_gallery -v
```

Expected:
- FAIL because `photos.js` still reads only `photo.evidence_path`

- [ ] **Step 3: Add a gallery renderer for evidence frames**

Refactor `factory_analytics/static/photos.js` so modal opening uses a helper like this:

```javascript
function renderEvidenceFrames(photo) {
    const frames = photo.evidence_frames && photo.evidence_frames.length
        ? photo.evidence_frames
        : [photo.evidence_path].filter(Boolean);

    return frames.map((path, index) => `
        <button type="button" class="rounded-lg overflow-hidden border border-outline-variant/20" onclick="document.getElementById('modalImage').src='/${path}'">
            <img src="/${path}" alt="Evidence ${index + 1}" class="w-24 h-16 object-cover" loading="lazy">
        </button>
    `).join('');
}
```

Then update `openPhotoModal()` to use the first frame as the main image and render the gallery into a dedicated container:

```javascript
const frames = photo.evidence_frames && photo.evidence_frames.length
    ? photo.evidence_frames
    : [photo.evidence_path].filter(Boolean);

elements.modalImage.src = '/' + frames[0];
elements.modalFrames.innerHTML = renderEvidenceFrames({ ...photo, evidence_frames: frames });
```

- [ ] **Step 4: Ensure photo cards still use a primary thumbnail**

Update the card render logic to prefer the first evidence frame:

```javascript
const frames = p.evidence_frames && p.evidence_frames.length
    ? p.evidence_frames
    : [p.evidence_path].filter(Boolean);
const primaryImage = frames[0] || '';
```

and use `primaryImage` in the `<img>` tag.

- [ ] **Step 5: Run the UI test to verify it passes**

Run:
```bash
pytest tests/test_ui_ux.py -k evidence_frames_gallery -v
```

Expected:
- PASS for the gallery rendering regression test

- [ ] **Step 6: Commit**

```bash
git add tests/test_ui_ux.py factory_analytics/static/photos.js
 git commit -m "feat: show all evidence frames in photos ui"
```

---

### Task 8: Update dashboard/history evidence consumers to use `evidence_frames`

**Files:**
- Modify: `factory_analytics/static/app.js`
- Modify: `factory_analytics/static/efficiency.js`
- Test: `tests/test_ui_ux.py`

- [ ] **Step 1: Write the failing regression test for JS consumers**

```python
from pathlib import Path


def test_dashboard_and_efficiency_js_use_evidence_frames():
    app_js = Path("factory_analytics/static/app.js").read_text()
    eff_js = Path("factory_analytics/static/efficiency.js").read_text()
    assert "evidence_frames" in app_js
    assert "evidence_frames" in eff_js
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
pytest tests/test_ui_ux.py -k dashboard_and_efficiency_js_use_evidence_frames -v
```

Expected:
- FAIL because those files still assume one `evidence_path`

- [ ] **Step 3: Update `factory_analytics/static/app.js` to read all evidence frames from the evidence API**

Change the evidence consumer code to prefer arrays:

```javascript
const frames = data.evidence_frames && data.evidence_frames.length
  ? data.evidence_frames
  : [data.evidence_path].filter(Boolean);
```

Use `frames[0]` for compact previews and `frames` for any “view evidence” expansion UI.

- [ ] **Step 4: Update `factory_analytics/static/efficiency.js` previews the same way**

When evidence API data is loaded, use:

```javascript
const frames = evData.evidence_frames && evData.evidence_frames.length
  ? evData.evidence_frames
  : [evData.evidence_path].filter(Boolean);
```

Then render:
- one primary preview with `frames[0]`
- a link or mini-gallery for the rest of the frames

- [ ] **Step 5: Run the regression test to verify it passes**

Run:
```bash
pytest tests/test_ui_ux.py -k dashboard_and_efficiency_js_use_evidence_frames -v
```

Expected:
- PASS for the JS regression test

- [ ] **Step 6: Commit**

```bash
git add tests/test_ui_ux.py factory_analytics/static/app.js factory_analytics/static/efficiency.js
git commit -m "feat: update evidence consumers for multi-frame ui"
```

---

### Task 9: Add end-to-end worker tests for single and group evidence payloads

**Files:**
- Modify: `tests/test_worker.py`

- [ ] **Step 1: Write the failing end-to-end single-camera worker test**

```python
def test_single_job_result_contains_canonical_evidence_fields(tmp_path, monkeypatch):
    ...
    assert job["raw_result"]["frame_count"] == 3
    assert job["raw_result"]["primary_evidence_path"] == job["raw_result"]["evidence_frames"][0]
    assert "boxes" not in job["raw_result"]
```
```

- [ ] **Step 2: Write the failing end-to-end group worker test**

```python
def test_group_job_result_contains_canonical_evidence_fields(tmp_path, monkeypatch):
    ...
    assert job["raw_result"]["frame_count"] == 3
    assert len(job["raw_result"]["evidence_frames"]) == 3
    assert job["raw_result"]["label"] in {"working", "not_working", "no_person", "uncertain"}
    assert "boxes" not in job["raw_result"]
```
```

- [ ] **Step 3: Run the tests to verify they fail**

Run:
```bash
pytest tests/test_worker.py -k "canonical_evidence_fields" -v
```

Expected:
- FAIL because old raw result shape and/or label shape still appears somewhere

- [ ] **Step 4: Finish any missing service-level cleanup needed to make both tests pass**

Make sure `factory_analytics/services.py` does all of the following consistently:

```python
stored_result = {
    **result,
    "frame_count": len(stored_frames),
    "primary_evidence_path": primary_evidence_path,
    "evidence_frames": stored_frames,
}
```

and never emits:

```python
"boxes"
"evidence_paths"
```

- [ ] **Step 5: Run the tests to verify they pass**

Run:
```bash
pytest tests/test_worker.py -k "canonical_evidence_fields" -v
```

Expected:
- PASS for both worker regression tests

- [ ] **Step 6: Commit**

```bash
git add tests/test_worker.py factory_analytics/services.py
git commit -m "test: cover canonical multi-frame evidence payloads"
```

---

### Task 10: Run the final verification suite

**Files:**
- Modify: none
- Test: `tests/test_worker.py`
- Test: `tests/test_api_settings.py`
- Test: `tests/test_ui_ux.py`

- [ ] **Step 1: Run the focused worker tests**

Run:
```bash
pytest tests/test_worker.py -v
```

Expected:
- PASS for worker/service tests covering label normalization, observations, evidence frames, and group aggregation

- [ ] **Step 2: Run the focused API tests**

Run:
```bash
pytest tests/test_api_settings.py -v
```

Expected:
- PASS for evidence endpoint payload shape

- [ ] **Step 3: Run the focused UI regression tests**

Run:
```bash
pytest tests/test_ui_ux.py -v
```

Expected:
- PASS for multi-frame gallery and JS evidence consumer coverage

- [ ] **Step 4: Run a grep-based regression check for dead box code**

Run:
```bash
grep -R "boxes\|draw_person_boxes\|image_annotations" factory_analytics tests
```

Expected:
- no matches in active application or test code, except maybe historical fixtures explicitly marked as legacy

- [ ] **Step 5: Commit the final verification-only checkpoint if any file changed during cleanup**

```bash
git add tests/test_worker.py tests/test_api_settings.py tests/test_ui_ux.py factory_analytics
git commit -m "chore: finalize multi-frame analysis verification"
```

---

## Self-review

### Spec coverage
- 4-label schema: covered in Tasks 1 and 9
- remove boxes and annotations: covered in Tasks 1, 3, 5, and 10
- single-camera raw frames as separate evidence: covered in Task 3
- group per-second collages and any-working-wins: covered in Task 4
- canonical `evidence_frames` API output: covered in Task 6
- photos/jobs/reports/history consumers: covered in Tasks 7 and 8
- testing expectations: covered in Tasks 1, 2, 3, 4, 6, 7, 8, 9, and 10

### Placeholder scan
- no `TBD`, `TODO`, or “similar to Task N” shortcuts remain
- each code-changing task contains concrete code blocks
- each verification step includes exact commands and expected outcomes

### Type consistency
- canonical evidence fields used everywhere: `primary_evidence_path`, `evidence_frames`, `frame_count`
- public label set used everywhere: `working`, `not_working`, `no_person`, `uncertain`
- deterministic group rule helper name is consistent: `_apply_group_label_rule`
