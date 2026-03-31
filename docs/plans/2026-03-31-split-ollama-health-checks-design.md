# 2026-03-31 - Split Ollama Health Checks Design

## Summary
Refactor the Ollama health and diagnostic flow to separate API/Model verification from full Vision Inference (Snapshot + LLM). This ensures users can verify their Ollama configuration even when camera snapshots are failing.

## Why
- **Debugging Clarity:** Currently, the "Test Connection" fails if a camera snapshot fails, leading users to believe Ollama itself is unreachable.
- **Infrastructure Isolation:** Ollama connectivity and Frigate snapshot availability are separate failure domains.
- **Improved UX:** Provides specific feedback on whether the API is down, the model is missing, or the camera is failing.

## Scope
- **Included:** 
    - New API endpoint for Ollama status check.
    - Refactored Vision Test endpoint.
    - UI updates to `settings.html` with separate test buttons.
    - Service layer logic to distinguish API/Model health from full Vision Inference.
- **Not included:** Changes to the background analysis worker or image composition logic.

## Architecture
### 1. Backend (FastAPI + Python)
- **`AnalyticsService.test_ollama_api()`**: 
    - Calls Ollama `/api/tags`.
    - Verifies configured `ollama_vision_model` exists in the list.
    - Returns `{ok: bool, model_exists: bool, available_models: list}`.
- **`AnalyticsService.test_ollama_vision()`**: 
    - Performs the existing snapshot + `classify_image()` flow.
    - Returns detailed error if snapshot fails vs. if inference fails.

### 2. Frontend (Jinja2 + Vanilla JS)
- **UI:** Two buttons in the "Ollama AI Configuration" section.
    - `btnTestApi`: "Check API & Model"
    - `btnTestVision`: "Run Vision Test"
- **Feedback:** Distinct message areas for each test.

## Data Flow
1. **API Check:** User clicks "Check API & Model" -> `GET /api/settings/ollama/status` -> `AnalyticsService` -> `OllamaClient.health()` -> returns status.
2. **Vision Test:** User clicks "Run Vision Test" -> `POST /api/settings/ollama/test` -> `AnalyticsService` -> `_capture_snapshot()` + `classify_image()` -> returns result.

## Error Handling
- **API Down:** Report connection error (e.g., `Ollama unreachable at http://...`).
- **Model Missing:** Report model error (e.g., `Model 'qwen3.5:9b' not found in Ollama`).
- **Snapshot Fail:** Report camera error (e.g., `Failed to fetch snapshot from camera_88_10`).
- **Inference Fail:** Report LLM error (e.g., `Ollama timed out during inference`).

## Verification
### Automated Tests
- `tests/test_api.py`: Verify new status endpoint and refactored test endpoint.
- `tests/test_ui_ux.py`: Verify both buttons exist and render results.

### Manual Verification
1. Open Settings.
2. Click "Check API & Model" -> Expect "Connection Successful (Model Found)".
3. Click "Run Vision Test" -> Expect either a result or a specific "Snapshot Failed" message if camera 88_10 is down.
