# Task Plan

## Goal
- Fix the current `./factory-analytics.sh debug` failures and ensure the app sends full-resolution snapshots to the LLM with no fallback or mock data.

## Phases
- [completed] Document task context, design, and implementation memory
- [completed] Reproduce `./factory-analytics.sh debug` failures and capture root causes
- [completed] Add failing tests for confirmed defects
- [completed] Implement minimal fixes for snapshot resolution and debug/runtime errors
- [completed] Verify with targeted tests and rerun `./factory-analytics.sh debug`
- [completed] Update project memory docs with final status and resume details

## Constraints
- No mock or fake data for production fixes
- No feature removal
- No fallback inference path
- Full-resolution snapshots must be the source for LLM analysis

## Errors Encountered
- `./factory-analytics.sh debug` starts while API/MCP are already running, producing `[Errno 48] Address already in use` in both `logs/api.log` and `logs/mcp.log`.
- Worker loop logs show `RuntimeError: Model qwen3.5:9b returned invalid label: person` from `factory_analytics/integrations/ollama.py`.
- Existing code still downscales snapshots before sending them to Ollama.

## Resume Point
- Historical jobs remain in the database; if the user wants a fully quiet worker loop, decide whether to drain old pending jobs or add bounded retry/queue controls for upstream Ollama failures.
