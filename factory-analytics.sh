#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${BASE_DIR}/run"
LOG_DIR="${BASE_DIR}/logs"

API_PID_FILE="${RUN_DIR}/api.pid"
MCP_PID_FILE="${RUN_DIR}/mcp.pid"

mkdir -p "${RUN_DIR}" "${LOG_DIR}"

load_env() {
  if [ -f "${BASE_DIR}/.env" ]; then
    set -a
    source "${BASE_DIR}/.env"
    set +a
  fi
  : "${APP_HOST:=0.0.0.0}"
  : "${APP_PORT:=8090}"
  : "${MCP_HOST:=0.0.0.0}"
  : "${MCP_PORT:=8099}"
  : "${LOG_LEVEL:=INFO}"
}

is_running() {
  local pid_file="$1"
  if [ -f "$pid_file" ]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" >/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

start_api() {
  if is_running "$API_PID_FILE"; then
    echo "API already running"
    return
  fi
  nohup bash -lc "cd '${BASE_DIR}' && ./.venv/bin/uvicorn factory_analytics.main:app --host '${APP_HOST}' --port '${APP_PORT}' --log-level '$(echo "${LOG_LEVEL}" | tr '[:upper:]' '[:lower:]')'" >> "${LOG_DIR}/api.log" 2>&1 &
  echo $! > "$API_PID_FILE"
  echo "Started API on ${APP_HOST}:${APP_PORT}"
}

start_mcp() {
  if is_running "$MCP_PID_FILE"; then
    echo "MCP already running"
    return
  fi
  nohup bash -lc "cd '${BASE_DIR}' && ./.venv/bin/uvicorn factory_analytics.mcp_server:app --host '${MCP_HOST}' --port '${MCP_PORT}' --log-level '$(echo "${LOG_LEVEL}" | tr '[:upper:]' '[:lower:]')'" >> "${LOG_DIR}/mcp.log" 2>&1 &
  echo $! > "$MCP_PID_FILE"
  echo "Started MCP on ${MCP_HOST}:${MCP_PORT}"
}

stop_one() {
  local pid_file="$1"
  local name="$2"
  if is_running "$pid_file"; then
    local pid
    pid="$(cat "$pid_file")"
    kill "$pid" >/dev/null 2>&1 || true
    for _ in {1..20}; do
      if kill -0 "$pid" >/dev/null 2>&1; then
        sleep 0.5
      else
        break
      fi
    done
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
    rm -f "$pid_file"
    echo "Stopped ${name}"
  else
    rm -f "$pid_file"
    echo "${name} not running"
  fi
}

status_one() {
  local pid_file="$1"
  local name="$2"
  if is_running "$pid_file"; then
    echo "${name}: RUNNING (pid $(cat "$pid_file"))"
  else
    echo "${name}: STOPPED"
  fi
}

logs_follow() {
  touch "${LOG_DIR}/api.log" "${LOG_DIR}/mcp.log" "${LOG_DIR}/worker.log"
  tail -n 100 -f "${LOG_DIR}/api.log" "${LOG_DIR}/mcp.log" "${LOG_DIR}/worker.log"
}

start_debug() {
  echo "Starting DEBUG mode with auto-reload..."
  echo "API: ${APP_HOST}:${APP_PORT}, MCP: ${MCP_HOST}:${MCP_PORT}"
  echo "Press Ctrl+C to stop"
  echo "---"
  cd "${BASE_DIR}" && ./.venv/bin/uvicorn factory_analytics.main:app --host "${APP_HOST}" --port "${APP_PORT}" --reload --log-level "$(echo "${LOG_LEVEL}" | tr '[:upper:]' '[:lower:]')"
}

start_debug_mcp() {
  echo "Starting MCP DEBUG mode with auto-reload..."
  echo "MCP: ${MCP_HOST}:${MCP_PORT}"
  echo "Press Ctrl+C to stop"
  echo "---"
  cd "${BASE_DIR}" && ./.venv/bin/uvicorn factory_analytics.mcp_server:app --host "${MCP_HOST}" --port "${MCP_PORT}" --reload --log-level "$(echo "${LOG_LEVEL}" | tr '[:upper:]' '[:lower:]')"
}

start_debug_all() {
  echo "Starting ALL services in DEBUG mode with auto-reload..."
  echo "API: ${APP_HOST}:${APP_PORT}"
  echo "MCP: ${MCP_HOST}:${MCP_PORT}"
  echo "Press Ctrl+C to stop"
  echo "---"
  
  cd "${BASE_DIR}"
  
  ./.venv/bin/uvicorn factory_analytics.main:app --host "${APP_HOST}" --port "${APP_PORT}" --reload --log-level "$(echo "${LOG_LEVEL}" | tr '[:upper:]' '[:lower:]')" >> "${LOG_DIR}/api.log" 2>&1 &
  API_PID=$!
  
  ./.venv/bin/uvicorn factory_analytics.mcp_server:app --host "${MCP_HOST}" --port "${MCP_PORT}" --reload --log-level "$(echo "${LOG_LEVEL}" | tr '[:upper:]' '[:lower:]')" >> "${LOG_DIR}/mcp.log" 2>&1 &
  MCP_PID=$!
  
  trap "echo 'Stopping...'; kill $API_PID $MCP_PID 2>/dev/null; exit 0" INT TERM
  
  wait $API_PID $MCP_PID
}

main() {
  load_env
  case "${1:-}" in
    start)
      start_api
      start_mcp
      ;;
    stop)
      stop_one "$MCP_PID_FILE" "MCP"
      stop_one "$API_PID_FILE" "API"
      ;;
    restart)
      stop_one "$MCP_PID_FILE" "MCP" || true
      stop_one "$API_PID_FILE" "API" || true
      start_api
      start_mcp
      ;;
    status)
      status_one "$API_PID_FILE" "API"
      status_one "$MCP_PID_FILE" "MCP"
      ;;
    logs)
      logs_follow
      ;;
    debug)
      start_debug_all
      ;;
    debug-api)
      start_debug
      ;;
    debug-mcp)
      start_debug_mcp
      ;;
    *)
      echo "Usage: $0 {start|stop|restart|status|logs|debug|debug-api|debug-mcp}"
      exit 1
      ;;
  esac
}

main "$@"
