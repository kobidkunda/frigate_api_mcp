# LLM Image Sampling & Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-frame sampling, image resize, and compression settings to the LLM image processing pipeline.

**Architecture:** Approach A — minimal extension. Add frame sampling to FrigateClient, build ImagePipeline for resize/compression/collage, update Settings page and services to use them.

**Tech Stack:** Python 3.x, FastAPI, Pillow (PIL), Jinja2, SQLite, HTML forms

---

## File Structure

| Responsibility | File | Action |
|---|---|---|
| New settings defaults | `database.py:22-44` | Modify DEFAULT_SETTINGS |
| Settings UI | `templates/settings.html` | Add "Image Processing" section before "Analysis Settings" |
| Frame sampling | `integrations/frigate.py` | Add `fetch_latest_snapshot_to_bytes()` method |
| Pipeline (resize, compress, collage) | `integrations/image_pipeline.py` | NEW module |
| Job processing uses pipeline | `services.py:333-493` | Modify `_process_single_job` and `_execute_group_analysis` to use ImagePipeline |
| Dependencies | Check existing venv | Verify Pillow is available |

---

### Task 1: Add New Settings to Database Defaults

**Files:**
- Modify: `database.py:22-44`

- [ ] **Step 1: Add 4 new settings to DEFAULT_SETTINGS dict**

```python
DEFAULT_SETTINGS = {
    # ... existing settings ...
    "group_retry_delay_seconds": 60,
    # NEW:
    "llm_frames_per_process": 1,
    "llm_seconds_window": 3,
    "image_resize_resolution": "original",
    "image_compression_quality": 100,
}
```

- [ ] **Step 2: Commit**

### Task 2: Add Image Processing Settings to Settings UI

**Files:**
- Modify: `templates/settings.html` between Ollama section and Analysis section

### Task 3: Add Raw Bytes Fetch Method to FrigateClient

**Files:**
- Modify: `integrations/frigate.py` — add `fetch_latest_snapshot_to_bytes()`

### Task 4: Create ImagePipeline Module

**Files:**
- Create: `integrations/image_pipeline.py` with: `fetch_frames`, `resize_pil_image`, `compress_pil_image_to_file`, `build_vertical_strip`, `build_group_collage`

### Task 5: Update Services to Use ImagePipeline

**Files:**
- Modify: `services.py` — add `_get_image_settings`, `_process_frame_collection_for_camera`, rewrite `_process_single_job` and `_execute_group_analysis`

### Task 6: Verify and Test
