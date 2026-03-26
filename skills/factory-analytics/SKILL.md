# Factory Analytics

## Purpose
Use this skill to inspect, operate, and report on the factory camera analytics system.

This skill is for:
- factory activity reporting
- idle time and sleep-suspect monitoring
- camera health checks
- Frigate connectivity checks
- Ollama/model connectivity checks
- analysis job history
- evidence lookup
- daily, weekly, and monthly summaries
- reruns, backfills, and operator review flows

This skill assumes there is a connected MCP bridge named `factory-analytics`.

## Recommended MCP tools
- `system_health`
- `camera_list`
- `run_list`
- `run_get`
- `history_search`
- `segment_get`
- `chart_daily`
- `report_get_daily`
- `frigate_health`
- `ollama_health`
- `run_analysis_now`
- `run_backfill`
- `review_segment`
