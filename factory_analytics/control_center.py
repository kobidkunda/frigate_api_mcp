from __future__ import annotations

import json
from pathlib import Path

from factory_analytics.config import BASE_DIR


def _mask_text(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["token", "password", "secret", "api_key"]):
        return "[masked]"
    return text


def get_config_file_inventory() -> list[dict]:
    candidates = [
        ("OpenCode package", BASE_DIR / ".opencode" / "package.json"),
        ("AGENTS", BASE_DIR / "AGENTS.md"),
        ("Env example", BASE_DIR / ".env.example"),
        ("Env", BASE_DIR / ".env"),
        ("Claude config", Path.home() / ".claude"),
        ("OpenCode config", Path.home() / ".config" / "opencode"),
    ]
    items = []
    for label, path in candidates:
        exists = path.exists()
        preview = ""
        kind = "dir" if exists and path.is_dir() else "file"
        if exists and path.is_file():
            try:
                preview = _mask_text(path.read_text(errors="ignore")[:400])
            except Exception:
                preview = "[unreadable]"
        items.append(
            {
                "label": label,
                "path": str(path),
                "exists": exists,
                "kind": kind,
                "preview": preview,
            }
        )
    return items


def get_skill_inventory() -> dict:
    roots = [
        Path.home() / ".agents" / "skills",
        Path.home() / ".config" / "opencode" / "skills",
        BASE_DIR / ".opencode" / "skills",
    ]
    entries = []
    for root in roots:
        if not root.exists():
            entries.append({"root": str(root), "exists": False, "items": []})
            continue
        items = sorted(p.name for p in root.iterdir())[:100]
        entries.append({"root": str(root), "exists": True, "items": items})
    return {"roots": entries}


def get_platform_install_instructions() -> dict:
    return {
        "macos": [
            "Install dependencies with the existing repo setup.",
            "Use OpenCode/Claude config paths shown in Control Center.",
            "Verify API and MCP status from the monitoring section.",
        ],
        "linux": [
            "Install Python and required repo dependencies.",
            "Copy config paths from the detected file inventory.",
            "Verify MCP/API reachability using the test actions.",
        ],
        "windows": [
            "Use the Windows-compatible config path shown in Control Center.",
            "Install the repo dependencies in your supported shell environment.",
            "Use API/MCP test actions to validate the setup.",
        ],
    }


def build_api_catalog(app) -> dict:
    groups: dict[str, list[dict]] = {}

    # Skill-aware guidance for each endpoint
    SKILL_GUIDANCE = {
        # Health & Status
        "/api/health": "Use for quick system health checks",
        "/api/health/frigate": "Check Frigate connectivity",
        "/api/health/ollama": "Check Ollama connectivity and model availability",
        "/api/system/status": "Get full system status with counts",
        "/api/cameras/health": "Get health status for all cameras",
        # Cameras
        "/api/cameras": "List all cameras (GET) or create new camera (POST)",
        "/api/cameras/{camera_id}": "Get, update, or delete a specific camera",
        "/api/cameras/{camera_id}/delete": "POST fallback for deleting cameras",
        "/api/cameras/delete_by_name": "Delete camera by Frigate name",
        "/api/cameras/{camera_id}/run": "Trigger immediate analysis for a camera",
        "/api/cameras/test": "Test camera snapshot and vision analysis",
        "/api/cameras/{camera_id}/health": "Get health status for specific camera",
        # Groups
        "/api/groups": "List all groups (GET) or create new group (POST)",
        "/api/groups/{group_id}": "Get, update, or delete a specific group",
        "/api/groups/{group_id}/cameras": "Add camera to group (POST)",
        "/api/groups/{group_id}/cameras/{camera_id}": "Remove camera from group (DELETE)",
        "/api/cameras/{camera_id}/groups": "List groups that contain this camera",
        "/api/groups/{group_id}/cameras": "List all cameras in a group",
        "/api/groups/{group_id}/run": "Run analysis for all cameras in group",
        # Jobs
        "/api/jobs": "List jobs with pagination and filtering",
        "/api/processed-events/jobs": "List jobs for processed events view",
        "/api/jobs/{job_id}": "Get specific job details",
        "/api/jobs/stats": "Get job statistics summary",
        "/api/jobs/{job_id}/retry": "Retry a failed job",
        "/api/jobs/{job_id}/cancel": "Cancel a pending/running job",
        "/api/jobs/bulk-cancel": "Cancel multiple jobs at once",
        "/api/jobs/cancel-all": "Cancel all pending and running jobs",
        "/api/jobs/backfill": "Schedule backfill analysis for time range",
        # History/Segments
        "/api/history/segments": "List analysis segments with filters",
        "/api/history/segments/{segment_id}": "Get specific segment details",
        "/api/processed-events/segments": "List segments for processed events view",
        "/api/review/{segment_id}": "Review/override segment classification",
        "/api/evidence/{segment_id}": "Get evidence path for a segment",
        # Charts
        "/api/charts/daily": "Get daily rollup chart data",
        "/api/charts/heatmap": "Get activity heatmap data",
        "/api/charts/heatmap-by-group": "Get heatmap grouped by camera groups",
        "/api/charts/shift-summary": "Get summary by shift",
        "/api/charts/camera-summary": "Get summary by camera",
        "/api/charts/job-failures": "Get job failure statistics",
        "/api/charts/confidence-distribution": "Get confidence distribution",
        # Reports
        "/api/reports/daily": "Get daily report data",
        # Settings
        "/api/settings": "Get (GET) or update (PUT) application settings",
        "/api/settings/ollama/test": "Test Ollama connection and vision model",
        # Frigate
        "/api/frigate/cameras/sync": "Sync cameras from Frigate",
        "/api/frigate/cameras": "List cameras available in Frigate",
        # Scheduler
        "/api/scheduler/reset": "Reset scheduler - clears last_run timestamps",
        # Logs
        "/api/logs/tail": "Get recent log lines (api, mcp, worker)",
        # Control Center
        "/api/control-center/config": "Get Control Center configuration",
        "/api/api-explorer/catalog": "Get this API catalog",
    }

    for route in app.routes:
        path = getattr(route, "path", None)
        methods = sorted(getattr(route, "methods", []) or [])
        if not path or not methods or path.startswith("/{file_path:path}"):
            continue
        if path.startswith("/api/"):
            group = path.split("/")[2] if len(path.split("/")) > 2 else "api"
        else:
            group = "pages"

        # Get skill notes from guidance or generate generic ones
        skill_notes = SKILL_GUIDANCE.get(path, f"HTTP {', '.join(methods)} endpoint")

        groups.setdefault(group, []).append(
            {
                "path": path,
                "methods": methods,
                "name": getattr(route.endpoint, "__name__", "route"),
                "skill_notes": skill_notes,
            }
        )
    return {
        "groups": [
            {"name": name, "routes": sorted(routes, key=lambda r: r["path"])}
            for name, routes in sorted(groups.items())
        ]
    }
