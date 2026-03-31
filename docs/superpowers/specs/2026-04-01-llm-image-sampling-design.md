# LLM Image Sampling & Optimization Design

## Problem
Currently the system sends a single snapshot per camera to Ollama. Users want:
1. Multiple frames sampled over time for better contextual analysis
2. Image resizing to reduce LLM token usage
3. Optional JPEG compression for bandwidth savings
4. Group analysis merges multiple cameras intelligently

## Requirements
- Settings page needs: frames count, seconds window, resize resolution, compression quality
- Frame sampling: 1 photo/second × N seconds = N photos per camera per cycle
- Resize: max-dimension scaling (320p/640p/720p/original), aspect ratio preserved
- Compression: configurable JPEG quality (20-100%)
- Single-camera: vertical strip of frames → classify
- Multi-camera group: each camera gets a vertical strip, all strips merged side-by-side → classify once with GROUP_PROMPT
- Backward compatible: frames=1 behaves identically to current single-snapshot flow

## Architecture
```
worker.py → AnalyticsService.process_one_pending_job()
  └→ FrigateClient.fetch_latest_snapshot() × N (1s apart)
  └→ ImagePipeline: resize + compress each frame
  └→ ImagePipeline: build collage (strip per camera, then merge)
  └→ OllamaClient.classify_image(collage_path)
  └→ Segments, results stored as before

settings.html — new "Image Processing" section with 4 new fields
database.py — DEFAULT_SETTINGS gains 4 new keys
```

## New Settings
| Key | Type | Default | UI |
|-----|------|---------|-----|
| `llm_frames_per_process` | Number | 1 | Number input, min=1, max=10 |
| `llm_seconds_window` | Number | 3 | Number input, min=1, max=60 |
| `image_resize_resolution` | String | `original` | Select: 320p/640p/720p/original |
| `image_compression_quality` | Number | 100 | Select: 20/40/60/80/100 (None) |

## ImagePipeline (`integrations/image_pipeline.py`)
- `fetch_frames(frigate_client, camera_name, count, dest_dir)` → list of PIL Images
- `resize_pil_img(img, resolution)` → resized PIL Image (320/640/720 = max dimension)
- `compress_pil_img(img, quality)` → compressed PIL Image
- `build_vertical_strip(frames, camera_name)` → PIL Image (stacked vertically, labeled strips)
- `build_group_collage(camera_strips)` → PIL Image (side-by-side strips with camera name labels)

## Changed Files
- `database.py` — 4 new DEFAULT_SETTINGS entries
- `settings.html` — new "Image Processing" section
- `integrations/frigate.py` — `fetch_latest_snapshot_to_bytes()` method (returns bytes, not file path)
- `integrations/image_pipeline.py` — NEW module
- `services.py` — `process_one_pending_job()` uses pipeline for frame collection and collage
- `pyproject.toml` — add `Pillow>=10.0.0`

## Migration Plan
No schema changes needed. Settings use the existing key/value system. Default values make existing installs behave identically.
