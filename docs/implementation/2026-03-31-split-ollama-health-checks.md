# 2026-03-31 - Split Ollama Health Checks

## Summary
Split the "Test Connection" functionality into two distinct checks: API/Model connectivity and full Vision Inference. This clarifies failure reasons when cameras are down but Ollama is healthy.

## Why
- Avoid confusion when snapshots fail during a connection test.
- Provide more granular diagnostic information for the Ollama integration.

## Scope
- New API endpoint `GET /api/settings/ollama/status`.
- Refactored `AnalyticsService.test_ollama_vision()` with better snapshot error reporting.
- Updated Settings UI with two test buttons.

## Changed files
- `factory_analytics/main.py` - added status endpoint
- `factory_analytics/services.py` - added API test and improved vision test error handling
- `factory_analytics/templates/settings.html` - updated UI buttons and results

## Decisions
- Used `GET` for the status check as it's a read-only health probe.
- Kept `POST` for the vision test as it involves active capture and potentially long-running inference.

## Resume point
- Create detailed implementation plan using `writing-plans` skill.
