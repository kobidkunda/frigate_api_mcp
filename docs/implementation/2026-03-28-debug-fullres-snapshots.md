# 2026-03-28 - Debug run and full-resolution snapshots

## Summary
Investigate `./factory-analytics.sh debug` failures and remove snapshot downscaling so only full-resolution evidence is sent to the configured LLM.

## Why
- The current Frigate fetch path is downscaling images before they reach Ollama.
- The user requires full-resolution-only LLM input with no fallback path and no fake data.
- The debug startup flow currently has unresolved runtime errors that must be reproduced and fixed honestly.

## Scope
- Included: debug command investigation, root-cause fixes, full-resolution snapshot capture, tests, and memory updates.
- Not included: feature removal, mock data, alternate low-resolution inference paths, or fallback models.

## Changed files
- `docs/plans/2026-03-28-debug-fullres-snapshots-plan.md` - step-by-step implementation plan
- `task_plan.md` - task phases and constraints
- `findings.md` - root-cause notes
- `progress.md` - session log
- `factory_analytics/integrations/frigate.py` - switched capture source to go2rtc full-resolution frame endpoint before falling back to Frigate preview endpoints
- `factory-analytics.sh` - added debug-mode port preflight so `debug` fails fast if API/MCP ports are already occupied
- `factory_analytics/database.py` - added active-job lookup helper
- `factory_analytics/worker.py` - scheduler now skips cameras that already have a pending/running analysis job
- `tests/test_frigate_integration.py` - regression test for full-resolution frame capture path
- `tests/test_service_script.py` - regression test for debug port collision guard
- `tests/test_worker.py` - regression test for duplicate scheduler job prevention
- `tests/test_ui_ux.py` - smoke test for log tail endpoint payload
- `factory_analytics/templates/history.html` - History page now renders larger inline evidence previews that open the full image on click
- `docs/plans/2026-03-28-history-photo-preview-plan.md` - plan for the History photo preview change
- `docs/plans/2026-03-28-history-llm-and-group-merge-plan.md` - plan for History LLM notes and group merge inclusion behavior
- `factory_analytics/services.py` - group run now continues with available cameras, records included/missing camera names, and appends missing camera notes
- `factory_analytics/services.py` - group run now creates durable group job/segment history records and stores merge metadata in the saved job raw result
- `factory_analytics/static/processed_events.js` - processed segments view now renders LLM notes and merge metadata hooks
- `factory_analytics/static/processed_events.js` - processed segments view now renders explicit Group Result badge/name for persisted group-analysis records
- `tests/test_group_analysis.py` - regression tests for grouped disabled camera inclusion and partial merge continuation
- `tests/test_groups_model.py` - regression test for persisted group job/segment history records
- `tests/test_processed_events_api.py` - regression test ensuring persisted group metadata is exposed in segment pagination
- `factory_analytics/control_center.py` - read-only config inspection, skill inventory, platform install instructions, and API route catalog helpers
- `factory_analytics/templates/control_center.html` - Control Center page for config/MCP/API monitoring
- `factory_analytics/templates/api_explorer.html` - API Explorer page for route catalog and usage notes
- `factory_analytics/static/control_center.js` - client-side Control Center data loading
- `factory_analytics/static/api_explorer.js` - client-side API Explorer catalog rendering
- `tests/test_control_center_api.py` - regression tests for Control Center and API Explorer routes/endpoints

## Decisions
- Keep UI thumbnails visually constrained in the browser only.
- Treat the captured Frigate snapshot as the canonical image for both evidence storage and LLM input.
- Reproduce runtime failures before attempting fixes.
- Use go2rtc `:1984/api/frame.jpeg?src=<camera>` as the primary evidence/LLM input source because Frigate `latest.jpg` currently returns only `320x320` for these cameras.
- Prevent duplicate scheduler jobs at the worker/db layer instead of masking the backlog elsewhere.
- Keep strict Ollama response validation; do not invent fallback labels or fake boxes.
- Group merge uses group membership as the inclusion source of truth, not standalone camera `enabled` state.
- If some grouped cameras fail snapshot capture, continue the merge with available cameras and record missing camera names in the group result notes.

## Verification
- `pytest tests/test_frigate_integration.py::test_fetch_latest_snapshot_requests_full_resolution_image -v`
- `pytest tests/test_service_script.py::test_debug_refuses_to_start_when_ports_are_in_use -v`
- `pytest tests/test_worker.py::test_schedule_due_cameras_skips_when_pending_or_running_job_exists -v`
- `pytest tests/test_ui_ux.py::test_history_page_renders_inline_evidence_preview_hooks -v`
- `pytest tests/test_group_analysis.py::test_group_run_includes_grouped_disabled_cameras -v`
- `pytest tests/test_group_analysis.py::test_group_run_continues_with_missing_camera_note -v`
- `pytest tests/test_ui_ux.py::test_history_page_renders_llm_response_hooks -v`
- `pytest tests/test_groups_model.py::test_group_job_and_segment_are_persisted_for_history -v`
- `pytest tests/test_processed_events_api.py::test_processed_segments_api_exposes_persisted_group_result_metadata -v`
- `pytest tests/test_ui_ux.py::test_history_page_renders_group_result_badge_hooks -v`
- `pytest tests/test_control_center_api.py tests/test_ui_ux.py::test_control_center_page_contains_monitoring_hooks tests/test_ui_ux.py::test_api_explorer_page_contains_catalog_hooks -v`
- `pytest tests/test_ui_ux.py::test_dashboard_page_renders_and_has_accessible_nav -v`
- `pytest tests/test_frigate_integration.py::test_fetch_latest_snapshot_requests_full_resolution_image tests/test_service_script.py::test_debug_refuses_to_start_when_ports_are_in_use tests/test_worker.py::test_schedule_due_cameras_skips_when_pending_or_running_job_exists tests/test_ui_ux.py::test_logs_tail_endpoint_returns_structured_payload tests/test_ollama_integration.py -v`
- Manual: captured a fresh snapshot through `AnalyticsService._capture_snapshot('camera_88_10')` and verified saved size `(1920, 1080)`.
- Manual: ran `./factory-analytics.sh stop` then `./factory-analytics.sh debug`; latest startup completed cleanly and the prior address-in-use failure no longer reproduced.

## Risks / Follow-ups
- Full-resolution images increase transfer and storage cost, but that is the intended behavior.
- Historical failed/pending jobs remain in SQLite from earlier broken runs; they are not deleted automatically.
- Ollama can still return real timeout/500 errors under load; current code reports those honestly rather than fabricating results.
- Group history is now persisted through anchor camera-backed job/segment records; if a later dedicated `groups_history` model is desired, that would be a refinement rather than a blocker.

## Resume point
- If you want even cleaner separation between camera history and group history later, add first-class `group_id`/`group_name` columns on `segments` instead of deriving them from stored job raw result metadata.
