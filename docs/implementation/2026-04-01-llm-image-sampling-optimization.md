# 2026-04-01 - LLM Image Sampling & Optimization

## Summary
Added multi-frame capture, image resize/compression settings, and job timeout enforcement. Each analysis cycle now captures N photos (1 per second for N seconds), processes them through resize/compression pipeline, and sends to LLM for classification.

## Why
- Single-frame analysis misses temporal context
- Large images waste bandwidth and slow inference
- Stuck jobs block the scheduler indefinitely
- Users need control over image quality/speed tradeoffs

## Scope
- 5 new settings: `llm_frames_per_process`, `llm_seconds_window`, `image_resize_resolution`, `image_compression_quality`, `job_timeout_seconds`
- Multi-frame capture via FrigateClient
- ImagePipeline module for resize/compression/strip/collage
- Job timeout auto-cancellation in worker
- Visual Evidence modal shows individual frames
- Improved GROUP_PROMPT for multi-camera analysis

## Changed files
- `factory_analytics/database.py` - Added 5 new DEFAULT_SETTINGS, `job_stats()` method, `expire_timed_out_jobs()` method
- `factory_analytics/templates/settings.html` - Added "Image Processing" section with 5 fields and "Job Timeout" field
- `factory_analytics/integrations/frigate.py` - Added `fetch_latest_snapshot_to_bytes()` method
- `factory_analytics/integrations/image_pipeline.py` - NEW module for frame sampling, resize, compression, collage
- `factory_analytics/integrations/ollama.py` - Updated GROUP_PROMPT, added more label aliases
- `factory_analytics/services.py` - Added `_get_image_settings()`, `_process_frame_collection_for_camera()`, updated `_process_single_job` and `_execute_group_analysis` for multi-frame
- `factory_analytics/worker.py` - Added job timeout expiration in worker loop
- `factory_analytics/main.py` - Fixed empty `chart_confidence_distribution()` function body
- `factory_analytics/static/efficiency.js` - Updated popover and segment modal to show multiple frame thumbnails

## Decisions
- Frame count = `llm_seconds_window` × `llm_frames_per_process` (photos per second × seconds)
- Resolution uses max-dimension scaling, preserving aspect ratio
- Multi-camera groups: each camera gets a vertical strip of frames, all strips merged side-by-side
- Visual Evidence modal shows ALL individual captured frame thumbnails
- Job timeout auto-cancels stuck `running` jobs so scheduler isn't blocked

## Verification
- App running on port 8090, health check passing
- Settings UI shows all 5 new fields
- Database has all 5 new settings with defaults

## Risks / Follow-ups
- Monitor Ollama endpoint for intermittent 500 errors
- Consider thumbnail generation for very large evidence photos
- May need retry logic for transient inference errors

## Resume point
Test multi-frame capture by setting `llm_seconds_window: 3` and triggering analysis on a camera.
