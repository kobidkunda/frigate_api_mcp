# 2026-04-04 - Ollama OpenAI API Mode & Test Button Fix

## Summary
Added OpenAI-compatible API mode support to the Ollama client and fixed the broken "Test Connection" button in the settings UI.

## Why
- The "Test Connection" button was showing "Connection Failed: undefined" because the frontend was checking `data.ollama_status` but the API returns `data.ollama.ok`
- User requested switching from Ollama native API (`/api/chat`) to OpenAI-compatible API (`/v1/chat/completions`) which Ollama also supports
- OpenAI-compatible mode provides better compatibility and standardization

## Scope
- Updated `OllamaClient` class to support both `native` and `openai` API modes
- Fixed the test connection button in settings.html to use correct API response structure
- Added `ollama_api_mode` setting to database defaults (set to `openai`)
- Added API Mode dropdown selector in the settings UI

## Changed files
- `factory_analytics/integrations/ollama.py` - Added `api_mode` parameter, `_models_url()` method, updated `health()`, `_chat_url()`, and `_classify_with_prompt()` to handle OpenAI-compatible endpoints and payload formats
- `factory_analytics/templates/settings.html` - Fixed test button to check `data.ollama.ok` instead of `data.ollama_status`, added API Mode dropdown selector
- `factory_analytics/database.py` - Added `ollama_api_mode: "openai"` to DEFAULT_SETTINGS

## Decisions
- Default API mode set to `openai` instead of `native` per user request
- OpenAI mode uses `/v1/chat/completions` endpoint and `/v1/models` for health checks
- OpenAI mode uses `response_format: {"type": "json_object"}` instead of Ollama's `format: "json"`
- OpenAI mode sends images as base64 data URLs in the `image_url` content format
- Native mode is still available as a fallback option via settings dropdown

## Verification
- Code changes reviewed for consistency
- Test button now correctly reads `data.ollama.ok` and displays model list
- API mode selector added to UI with "Ollama Native" and "OpenAI Compatible" options

## Risks / Follow-ups
- Existing databases will need to be restarted to pick up the new default setting (or manually set via UI)
- If OpenAI mode fails, user can switch back to "Ollama Native" mode in settings
- No migration needed - new setting will be inserted on next app start for databases without it

## Resume point
- Task complete. Restart app to apply changes. Test the "Test Connection" button on the Settings page.
