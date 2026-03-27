from __future__ import annotations

from pathlib import Path
from typing import Any
import httpx

from factory_analytics.logging_setup import setup_logging
from factory_analytics.config import FRIGATE_URL as ENV_FRIGATE_URL

logger = setup_logging()


class FrigateClient:
    def __init__(self, settings: dict[str, Any]):
        self.settings = settings
        # Fallback to env if DB/settings value is empty
        self.base_url = (settings.get("frigate_url") or ENV_FRIGATE_URL or "").rstrip(
            "/"
        )
        self.verify_tls = bool(settings.get("frigate_verify_tls", False))
        self.auth_mode = settings.get("frigate_auth_mode", "none")
        self.username = settings.get("frigate_username") or ""
        self.password = settings.get("frigate_password") or ""
        self.token = settings.get("frigate_bearer_token") or ""

    def _headers(self) -> dict[str, str]:
        headers = {}
        if self.auth_mode == "bearer" and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _auth(self):
        if self.auth_mode == "basic" and self.username:
            return (self.username, self.password)
        return None

    def health(self) -> dict[str, Any]:
        if not self.base_url:
            return {"ok": False, "message": "Frigate URL not configured"}
        try:
            with httpx.Client(
                timeout=15,
                verify=self.verify_tls,
                headers=self._headers(),
                auth=self._auth(),
            ) as client:
                r = client.get(f"{self.base_url}/api/version")
                r.raise_for_status()
                return {"ok": True, "version": r.text.strip().strip('"')}
        except Exception as exc:
            logger.exception("Frigate health failed")
            return {"ok": False, "message": str(exc)}

    def fetch_cameras(self) -> list[str]:
        if not self.base_url:
            return []
        try:
            with httpx.Client(
                timeout=20,
                verify=self.verify_tls,
                headers=self._headers(),
                auth=self._auth(),
            ) as client:
                r = client.get(f"{self.base_url}/api/config")
                r.raise_for_status()
                payload = r.json()
                cams = payload.get("cameras", {})
                if isinstance(cams, dict):
                    return sorted(list(cams.keys()))
        except Exception:
            logger.exception("Frigate camera sync failed")
        return []

    def fetch_latest_snapshot(self, camera_name: str, destination: Path) -> Path:
        if not self.base_url:
            raise RuntimeError("Frigate URL not configured")
        # Validate camera exists up front for clearer errors
        available = set(self.fetch_cameras())
        if camera_name not in available:
            raise RuntimeError(
                f"Camera '{camera_name}' not found on Frigate at {self.base_url}. Available: "
                + ", ".join(sorted(available))
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        endpoints = [
            f"{self.base_url}/api/{camera_name}/latest.jpg",
            f"{self.base_url}/api/{camera_name}/snapshot.jpg",
        ]
        last_error: str | None = None
        for endpoint in endpoints:
            try:
                with httpx.Client(
                    timeout=30,
                    verify=self.verify_tls,
                    headers=self._headers(),
                    auth=self._auth(),
                ) as client:
                    r = client.get(endpoint)
                    r.raise_for_status()
                    destination.write_bytes(r.content)
                    return destination
            except httpx.HTTPStatusError as exc:
                last_error = f"{exc.response.status_code} for {exc.request.url}"
            except Exception as exc:
                last_error = str(exc)
        raise RuntimeError(
            f"Failed to fetch latest snapshot for {camera_name}: {last_error}"
        )
