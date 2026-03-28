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
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = sorted(getattr(route, "methods", []) or [])
        if not path or not methods or path.startswith("/{file_path:path}"):
            continue
        if path.startswith("/api/"):
            group = path.split("/")[2] if len(path.split("/")) > 2 else "api"
        else:
            group = "pages"
        groups.setdefault(group, []).append(
            {
                "path": path,
                "methods": methods,
                "name": getattr(route.endpoint, "__name__", "route"),
                "skill_notes": f"Use via HTTP skill-aware workflows for {path}",
            }
        )
    return {
        "groups": [
            {"name": name, "routes": sorted(routes, key=lambda r: r["path"])}
            for name, routes in sorted(groups.items())
        ]
    }
