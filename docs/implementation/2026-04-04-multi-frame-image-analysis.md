# 2026-04-04 - Multi-Frame Image Analysis

## Summary
Changed how images are sent to the LLM. Instead of merging all frames into a single vertical strip, individual frames are now sent separately in one request with temporal context. For group analysis, per-frame collages are built (all cameras merged for each moment) and all frame-collages are sent together.

## Why
- Merging frames into a single strip loses temporal information
- Sending individual frames with "X seconds apart" context gives the LLM better understanding of what people are doing over time
- For groups: instead of one merged image of all camera strips, we now build one collage per frame moment, so the LLM sees temporal progression across all cameras

## Scope
- **Single camera**: Each frame sent individually in one request (e.g., 3 frames = 3 images in one call)
- **Group analysis**: For N cameras and M frames, build M collages (each collage has all N cameras for that frame moment), send all M collages in one request
- **Prompts**: Updated to include temporal context ("these frames were captured X seconds apart")
- **API**: Now OpenAI-compatible only (`/v1/chat/completions`), removed native Ollama mode

## Changed files
- `factory_analytics/integrations/ollama.py` - Replaced `OllamaClient` with `OpenAIClient`. Added `classify_images()` and `classify_group_images()` methods that accept multiple image paths. Updated prompts with `{seconds}` and `{count}` placeholders for temporal context.
- `factory_analytics/services.py` - `_process_single_job()` now sends individual frames via `classify_images()`. `_execute_group_analysis()` builds per-frame collages and sends all via `classify_group_images()`.
- `factory_analytics/database.py` - Removed `ollama_api_mode` setting (now always OpenAI-compatible).
- `factory_analytics/templates/settings.html` - Removed API Mode dropdown, fixed test button to use correct response structure.

## Decisions
- OpenAI-compatible API only - no more native Ollama mode toggle
- Single camera: sends all frames individually in one request with temporal prompt
- Group: builds per-frame collages (all cameras merged per frame), sends all collages with temporal prompt
- Backward compatible: `classify_image()` and `classify_group_image()` still work for single-image cases

## Verification
- Code changes reviewed for consistency
- Import updated from `OllamaClient` to `OpenAIClient` in services.py

## Risks / Follow-ups
- Restart app required to apply changes
- Existing database will auto-insert new defaults on next start
- Tests referencing `OllamaClient` need updating to `OpenAIClient`
- Monitor LLM response quality with multi-frame input

## Resume point
- Task complete. Restart app to apply. Monitor analysis results for quality improvement with multi-frame temporal context.
