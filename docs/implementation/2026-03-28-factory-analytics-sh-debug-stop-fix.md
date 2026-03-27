# 2026-03-28 - factory-analytics.sh debug/stop robustness

## Summary
Hardened service control script so `stop` reliably terminates processes started in `debug` mode and when pid files are missing. Also ensured debug mode writes pid files and cleans them up.

## Why
- User observed `stop` reporting "MCP not running" / "API not running" while debug processes were active. Root cause: debug path didn’t write pid files; stop relied solely on pid files.
- Occasional orphaned uvicorn processes without pid files caused misleading status and inability to stop.

## Scope
- Update factory-analytics.sh only. No app code changes.

## Changed files
- `factory-analytics.sh`
  - In debug-all: write `$API_PID_FILE` and `$MCP_PID_FILE`; cleanup on exit.
  - Add `find_listener_pid()` using `lsof` to detect listeners by port.
  - Add `stop_api()` and `stop_mcp()` fallbacks: if pid file missing, kill by port.
  - Use `exec` in nohup commands to ensure PID tracks actual uvicorn process.

## Decisions
- Use `lsof -tiTCP:PORT -sTCP:LISTEN` as non-invasive fallback to find PIDs bound to configured ports.
- Keep existing pid-file logic as primary; only fall back when missing.

## Verification
- Ran `./factory-analytics.sh debug`; script starts both services, tails logs live; Ctrl+C detaches but services keep running.
- `./factory-analytics.sh status` shows RUNNING with pids; `./factory-analytics.sh stop` stops both cleanly; `status` shows STOPPED.
- Confirmed `run/api.pid` and `run/mcp.pid` created on start and removed on stop.

## Risks / Follow-ups
- `lsof` must be present (standard on macOS). On minimal systems, add a note if missing.
- Consider adding `status` fallback via `lsof` to show RUNNING without pid files.

## Resume point
- If further issues persist, extend `status_one` to use `find_listener_pid` as secondary check.
